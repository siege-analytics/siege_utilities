"""
Format detection and per-format attribute extraction for vector GIS files.

This module provides a small dispatcher that identifies a vector GIS file's
format (shapefile / GeoJSON / KML / KMZ / GeoPackage / DXF / SWMaps / unknown)
and exposes per-format attribute extractors that tolerate missing fields the
way OGR does (return None rather than raise).

Pattern lifted from a third-party tile-server audit
(``common/utils/DataUtils.py:488-563`` — ``_getDataFromSource`` and the
per-format ``_get*DataFromSource`` helpers). Patterns explicitly NOT carried
over from the salvage source:

* Hardcoded Windows binary paths (``osgeo4WBinPath``,
  ``ODA_FILE_CONVERTER_PATH``) — the salvage shell-out via subprocess for
  DWG->DXF conversion is discarded entirely.
* ``osgeo`` Python bindings — the salvage source uses GDAL/OGR directly; SU
  declares ``fiona`` (the high-level OGR wrapper) as the geo dep, so this
  module is fiona-shaped at the attribute-extraction layer.
* Azure Blob fetch coupling around the dispatch.
* Application-schema-specific extractors (``map_job_id``, etc.) — the
  generic extractors here accept candidate field-name lists; consumer code
  supplies the schema.

Optional dependencies are guarded; calling an extractor whose backing
library is not installed raises ``ImportError`` with the install hint.
"""

from __future__ import annotations

import logging
import os
import sqlite3
import zipfile
from typing import Any, Iterable

log = logging.getLogger(__name__)

# Extension -> format token. Extensions match the dispatcher cases in the
# salvage source plus the SWMaps `.swmz` archive form.
_EXTENSION_MAP = {
    ".shp": "shapefile",
    ".geojson": "geojson",
    ".kml": "kml",
    ".kmz": "kmz",
    ".gpkg": "geopackage",
    ".dxf": "dxf",
    ".swmz": "swmaps",
}

# Extensions that need magic-byte / archive-peek disambiguation.
_AMBIGUOUS_EXTENSIONS = {".json", ".sqlite", ".db", ".zip"}

# SWMaps SQLite schema fingerprint — these three tables appear together in
# every SWMaps export (verified against salvage-source query at DataUtils.py:687-692).
_SWMAPS_SQLITE_TABLES = frozenset({"features", "points", "feature_layers"})

# Sentinel values for the `missing=` keyword on the extractors.
MISSING_NONE = "none"
MISSING_RAISE = "raise"
MISSING_WARN = "warn"
_MISSING_VALID = {MISSING_NONE, MISSING_RAISE, MISSING_WARN}


def detect_format(file_path: str) -> str:
    """Return a format token for a vector GIS file.

    Args:
        file_path: Path to a vector GIS file on disk.

    Returns:
        One of: ``"shapefile"``, ``"geojson"``, ``"kml"``, ``"kmz"``,
        ``"geopackage"``, ``"dxf"``, ``"swmaps"``, ``"unknown"``.

    Raises:
        FileNotFoundError: If the file does not exist.

    Detection algorithm:

    1. Extension lookup (case-insensitive) against a small canonical map.
    2. For ambiguous extensions (``.json``, ``.sqlite``, ``.db``, ``.zip``),
       a magic-byte / archive-peek fallback inspects the file body.

    Directories return ``"unknown"`` — walking is the caller's responsibility.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(file_path)
    if os.path.isdir(file_path):
        return "unknown"

    ext = os.path.splitext(file_path)[1].lower()
    if ext in _EXTENSION_MAP:
        return _EXTENSION_MAP[ext]
    if ext not in _AMBIGUOUS_EXTENSIONS:
        return "unknown"

    # Magic-byte / archive-peek disambiguation.
    try:
        if ext == ".json":
            return _peek_json(file_path)
        if ext in {".sqlite", ".db"}:
            return _peek_sqlite(file_path)
        if ext == ".zip":
            return _peek_zip(file_path)
    except (OSError, ValueError, UnicodeDecodeError, RuntimeError) as exc:  # pragma: no cover - corrupt file fallback
        log.warning("detect_format peek failed for %s: %s", file_path, exc)

    return "unknown"


def _peek_json(file_path: str) -> str:
    """Return ``"geojson"`` if file body looks like GeoJSON, else ``"unknown"``."""
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as fh:
            head = fh.read(4096)
    except OSError:
        return "unknown"
    if '"FeatureCollection"' in head or '"Feature"' in head or '"geometry"' in head:
        return "geojson"
    return "unknown"


def _peek_sqlite(file_path: str) -> str:
    """Return ``"swmaps"`` if SQLite has the SWMaps table fingerprint, else ``"unknown"``."""
    try:
        with sqlite3.connect(f"file:{file_path}?mode=ro", uri=True, timeout=5.0) as conn:
            cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = {row[0] for row in cur.fetchall()}
    except sqlite3.DatabaseError:
        return "unknown"
    if _SWMAPS_SQLITE_TABLES.issubset(tables):
        return "swmaps"
    return "unknown"


def _peek_zip(file_path: str) -> str:
    """Inspect a ``.zip`` archive's member names to pick a sub-format."""
    try:
        with zipfile.ZipFile(file_path) as zf:
            names = [n.lower() for n in zf.namelist()]
    except zipfile.BadZipFile:
        return "unknown"
    if any(n.endswith(".kml") for n in names):
        return "kmz"
    if any(n.endswith(".sqlite") or n.endswith(".db") for n in names):
        return "swmaps"
    if any(n.endswith(".shp") for n in names):
        return "shapefile"
    return "unknown"


def _resolve_missing(field_name: str, missing: str) -> Any:
    """Apply the ``missing=`` policy uniformly across extractors."""
    if missing not in _MISSING_VALID:
        raise ValueError(
            f"missing= must be one of {sorted(_MISSING_VALID)}; got {missing!r}"
        )
    if missing == MISSING_RAISE:
        raise KeyError(field_name)
    if missing == MISSING_WARN:
        log.warning("attribute field %r not present on feature", field_name)
    return None


def extract_attributes_ogr(
    feature: Any,
    field_names: Iterable[str],
    missing: str = MISSING_NONE,
) -> Any:
    """Extract one attribute from a fiona-record-shaped feature.

    Mirrors the candidate-list semantics of the salvage-source helper
    ``_getOGRDataFromSource`` (``DataUtils.py:489-513``) which accepts a
    primary plus a fallback field name and returns ``None`` when neither is
    present. The salvage source used the GDAL/OGR Python bindings directly;
    this implementation is fiona-record-shaped (the high-level OGR wrapper
    that SU declares as a geo dep).

    Args:
        feature: A fiona-style record (``{"properties": {...}, ...}``) OR a
            plain ``dict`` (e.g. the property dict directly).
        field_names: Candidate field names, in priority order. First name
            present on the feature wins.
        missing: One of ``"none"`` (default; return ``None``), ``"raise"``
            (``KeyError``), or ``"warn"`` (log + return ``None``).

    Returns:
        The attribute value or ``None``.
    """
    if feature is None:
        return _resolve_missing(next(iter(field_names), ""), missing)

    # fiona record vs bare dict.
    if isinstance(feature, dict) and "properties" in feature and isinstance(
        feature["properties"], dict
    ):
        props = feature["properties"]
    elif isinstance(feature, dict):
        props = feature
    else:
        # Best-effort attribute-style fallback (e.g. an OGR Feature subclass
        # in callers that DO have osgeo installed).
        props = None

    candidates = list(field_names)
    if not candidates:
        return None

    if props is not None:
        for name in candidates:
            if name in props:
                return props[name]
    else:  # pragma: no cover - osgeo fallback path
        for name in candidates:
            if hasattr(feature, name):
                return getattr(feature, name)

    return _resolve_missing(candidates[0], missing)


def extract_attributes_kml(
    kml_extended_data: dict | None,
    field_names: Iterable[str],
    missing: str = MISSING_NONE,
) -> Any:
    """Extract one attribute from a KML extended-data mapping.

    Mirrors the salvage-source helper ``_getKMLDataFromSource``
    (``DataUtils.py:516-520``). The salvage version was a one-liner dict
    lookup with no candidate fallback; this version adds the same
    candidate-list semantics as :func:`extract_attributes_ogr` for
    consistency across the dispatcher.

    Args:
        kml_extended_data: A flat ``{name: value}`` mapping derived from a
            KML ``<ExtendedData>`` block.
        field_names: Candidate field names, in priority order.
        missing: ``"none"`` / ``"raise"`` / ``"warn"``.

    Returns:
        The attribute value or ``None``.
    """
    candidates = list(field_names)
    if not candidates:
        return None
    if kml_extended_data:
        for name in candidates:
            if name in kml_extended_data:
                return kml_extended_data[name]
    return _resolve_missing(candidates[0], missing)


def extract_attributes_swmaps(
    db_path: str,
    feature_id: str,
    field_names: Iterable[str],
    missing: str = MISSING_NONE,
) -> Any:
    """Extract one attribute for a SWMaps feature by attribute-field name.

    Queries the SWMaps SQLite ``attribute_values`` table joined to
    ``attribute_fields`` for the named field, scoped to ``feature_id``.
    This is the same join pattern as the salvage source's
    ``swmapsAttributeQuery`` (``DataUtils.py:693-698``); the
    application-schema-specific mapper (``swMapsAttributeMapper`` dict at
    ``DataUtils.py:672-686``) is NOT lifted — that lives with the consumer.

    For full SWMaps feature iteration (geometry + all attributes), use
    :mod:`siege_utilities.geo.swmaps_reader` instead; this function is the
    thin dispatcher-friendly accessor.

    Args:
        db_path: Path to a SWMaps SQLite file (already extracted from
            ``.swmz`` if needed; archive handling lives in the swmaps_reader
            module).
        feature_id: SWMaps feature UUID.
        field_names: Candidate attribute-field names.
        missing: ``"none"`` / ``"raise"`` / ``"warn"``.

    Returns:
        The attribute value (as stored in ``attribute_values.value``) or
        ``None``.
    """
    candidates = list(field_names)
    if not candidates:
        return None

    query = (
        "SELECT af.field_name, av.value "
        "FROM attribute_values av "
        "INNER JOIN attribute_fields af ON af.uuid = av.field_id "
        "WHERE av.item_id = ?"
    )
    try:
        with sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, timeout=5.0) as conn:
            rows = dict(conn.execute(query, (feature_id,)).fetchall())
    except sqlite3.DatabaseError as exc:
        log.warning("SWMaps query failed for %s: %s", db_path, exc)
        return _resolve_missing(candidates[0], missing)

    for name in candidates:
        if name in rows:
            return rows[name]

    return _resolve_missing(candidates[0], missing)

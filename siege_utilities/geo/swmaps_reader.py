"""
Reader for SWMaps ``.swmz`` archives and raw ``.sqlite`` field-data files.

SWMaps is a field-data-collection tool that exports ``.swmz`` archives
containing a SQLite database with three core tables:

* ``features`` — one row per recorded feature (UUID, name, layer_id).
* ``points`` — one row per coordinate point (``fid``, ``seq``, ``lat``,
  ``lon``, ``elv``); rows share ``fid`` and are ordered by ``seq``.
* ``feature_layers`` — feature-type metadata (geom_type, group_name).

The geometry rule from the salvage source: one point per feature ->
POINT, two or more points -> LINESTRING.

Pattern lifted from a third-party tile-server audit
(``common/utils/DataUtils.py:669-783`` — ``_readSWMapsSqlite``).
Patterns NOT carried over:

* Hardcoded application-schema attribute mapping (``map_job_id``,
  ``map_group_id``, ``map_feature_type_id``, ``workorder_number``). The
  consumer supplies its own attribute mapper.
* The PG-RPC ``_getFeatureGroupAndTypeIdFromNames`` and
  ``_getJobIdFromWorkOrderNumber`` calls (Azure-coupled).
* Manual WKT string concatenation — replaced with shapely.
* ``_siteMapLogger`` macro — replaced with stdlib ``logging``.

Typical usage::

    from siege_utilities.geo.swmaps_reader import open_swmaps, read_features

    with open_swmaps("/path/to/field-export.swmz") as archive:
        for feature in read_features(archive):
            print(feature["feature_type"], feature["geometry_wkt"])
"""

from __future__ import annotations

import logging
import os
import shutil
import sqlite3
import tempfile
import zipfile
from typing import Iterator

log = logging.getLogger(__name__)

# Recognized .swmz container extensions and raw-SQLite extensions.
_ARCHIVE_EXTS = {".swmz", ".zip"}
_SQLITE_EXTS = {".sqlite", ".db"}

# Default join query — SWMaps schema verified against the salvage source
# (DataUtils.py:687-692).
_FEATURE_QUERY = (
    "SELECT f.uuid AS feature_id, f.name AS feature_name, "
    "       p.seq AS seq, p.lat AS lat, p.lon AS lon, p.elv AS elv, "
    "       fl.name AS feature_type, fl.group_name AS feature_group, "
    "       fl.geom_type AS geom_type, fl.uuid AS layer_id "
    "FROM features f "
    "INNER JOIN points p ON p.fid = f.uuid "
    "INNER JOIN feature_layers fl ON fl.uuid = f.layer_id "
    "ORDER BY f.uuid, p.seq"
)

_ATTRIBUTE_QUERY = (
    "SELECT f.uuid AS feature_id, af.field_name AS field_name, "
    "       av.value AS field_value "
    "FROM features f "
    "INNER JOIN attribute_values av ON av.item_id = f.uuid "
    "INNER JOIN attribute_fields af ON af.uuid = av.field_id"
)


class SWMapsArchive:
    """Context-manager handle to an opened SWMaps archive or raw SQLite file.

    Use :func:`open_swmaps` to construct. Call :meth:`close` (or use as
    a ``with`` block) to clean up any extracted-archive temp directory.
    """

    def __init__(self, db_path: str, _temp_dir: str | None = None):
        self._db_path = db_path
        self._temp_dir = _temp_dir
        self._closed = False

    @property
    def db_path(self) -> str:
        """Filesystem path to the readable SQLite database."""
        if self._closed:
            raise ValueError("SWMapsArchive is closed")
        return self._db_path

    def close(self) -> None:
        """Remove the temp directory if this archive owned one."""
        if self._closed:
            return
        self._closed = True
        if self._temp_dir and os.path.isdir(self._temp_dir):
            shutil.rmtree(self._temp_dir, ignore_errors=True)

    def __enter__(self) -> "SWMapsArchive":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()


def open_swmaps(path: str) -> SWMapsArchive:
    """Open a SWMaps archive (``.swmz`` / ``.zip``) or raw SQLite file.

    Args:
        path: Path to a ``.swmz`` archive, a ``.zip`` archive containing
            a ``.sqlite`` member, or a raw ``.sqlite`` / ``.db`` file.

    Returns:
        An :class:`SWMapsArchive` handle. Use it as a context manager so
        any extracted temp directory is cleaned up on exit.

    Raises:
        FileNotFoundError: If ``path`` does not exist.
        ValueError: If an archive contains no SQLite member, or if the
            file extension is not one of the recognized forms.
    """
    if not os.path.exists(path):
        raise FileNotFoundError(path)

    ext = os.path.splitext(path)[1].lower()
    if ext in _SQLITE_EXTS:
        return SWMapsArchive(db_path=path, _temp_dir=None)
    if ext not in _ARCHIVE_EXTS:
        raise ValueError(
            f"Unrecognized SWMaps source extension {ext!r}; "
            f"expected one of {sorted(_SQLITE_EXTS | _ARCHIVE_EXTS)}"
        )

    # Archive form — extract the .sqlite member to a temp dir.
    tmp = tempfile.mkdtemp(prefix="swmaps_")
    try:
        with zipfile.ZipFile(path) as zf:
            sqlite_members = [
                n for n in zf.namelist()
                if os.path.splitext(n)[1].lower() in _SQLITE_EXTS
            ]
            if not sqlite_members:
                raise ValueError(
                    f"SWMaps archive {path!r} contains no .sqlite / .db member"
                )
            # Prefer a top-level member; otherwise take the first.
            member = sqlite_members[0]
            zf.extract(member, tmp)
            db_path = os.path.join(tmp, member)
    except Exception:
        shutil.rmtree(tmp, ignore_errors=True)
        raise

    return SWMapsArchive(db_path=db_path, _temp_dir=tmp)


def read_features(
    archive: SWMapsArchive,
    mapper: dict[str, str] | None = None,
) -> Iterator[dict]:
    """Yield per-feature dicts from a SWMaps archive.

    Each yielded dict has:

    * ``feature_id`` — SWMaps UUID.
    * ``feature_type`` — from ``feature_layers.name``.
    * ``feature_group`` — from ``feature_layers.group_name``.
    * ``layer_id`` — from ``feature_layers.uuid``.
    * ``feature_name`` — from ``features.name``.
    * ``geometry_wkt`` — POINT (single coordinate) or LINESTRING (two or
      more coordinates), built via :mod:`shapely`. Z dimension included
      when every coordinate row carries a non-null ``elv``; dropped
      otherwise.
    * ``attributes`` — ``{field_name: value}`` mapping pulled from
      ``attribute_values`` joined to ``attribute_fields``. Keys can be
      renamed by passing ``mapper``.

    Args:
        archive: An :class:`SWMapsArchive` opened via :func:`open_swmaps`.
        mapper: Optional ``{source_name: consumer_name}`` rename map. When
            ``None``, attribute keys are the verbatim SWMaps field names.
            Unknown source keys are logged and skipped (kept verbatim).

    Yields:
        Dicts as described above. Empty-features (zero coordinate rows)
        are logged at WARNING and skipped.

    Raises:
        ImportError: If ``shapely`` is not installed.

    The geometry rule matches the salvage source (``DataUtils.py:749-768``)
    but uses ``shapely.geometry.Point`` / ``shapely.geometry.LineString``
    with ``.wkt`` rather than manual string concatenation.
    """
    try:
        from shapely.geometry import LineString, Point
    except ImportError as exc:  # pragma: no cover - dep guard
        raise ImportError(
            "shapely is required for SWMaps geometry construction. "
            "Install with: pip install 'siege-utilities[geo]'"
        ) from exc

    db_path = archive.db_path
    with sqlite3.connect(f"file:{db_path}?mode=ro", uri=True) as conn:
        conn.row_factory = sqlite3.Row

        # Group coordinate rows by feature_id; sqlite3 cursor already
        # ORDER BY-s by feature_id then seq.
        feature_rows: dict[str, list[sqlite3.Row]] = {}
        feature_meta: dict[str, dict] = {}
        for row in conn.execute(_FEATURE_QUERY):
            fid = row["feature_id"]
            feature_rows.setdefault(fid, []).append(row)
            feature_meta.setdefault(
                fid,
                {
                    "feature_id": fid,
                    "feature_name": row["feature_name"],
                    "feature_type": row["feature_type"],
                    "feature_group": row["feature_group"],
                    "layer_id": row["layer_id"],
                },
            )

        # Pull per-feature attributes once into a dict-of-dicts. Tables
        # are optional in the schema; tolerate their absence.
        attrs_by_feature: dict[str, dict] = {}
        try:
            for row in conn.execute(_ATTRIBUTE_QUERY):
                attrs_by_feature.setdefault(row["feature_id"], {})[
                    row["field_name"]
                ] = row["field_value"]
        except sqlite3.DatabaseError as exc:
            log.warning("SWMaps attribute join failed: %s", exc)

    for fid, rows in feature_rows.items():
        if not rows:
            log.warning("SWMaps feature %s has no coordinate rows; skipping", fid)
            continue

        # Build geometry. Z included only when every coord carries a
        # non-null elv (the salvage source always emits 3D; we degrade
        # to 2D when elv is missing rather than embed sentinel zeros).
        coords_have_z = all(r["elv"] is not None for r in rows)
        coords: list[tuple] = []
        for r in rows:
            lon = float(r["lon"])
            lat = float(r["lat"])
            if coords_have_z:
                coords.append((lon, lat, float(r["elv"])))
            else:
                coords.append((lon, lat))

        if len(coords) == 1:
            geom = Point(coords[0])
        else:
            geom = LineString(coords)

        # Apply attribute mapper if any.
        raw_attrs = attrs_by_feature.get(fid, {})
        if mapper:
            renamed: dict = {}
            for key, val in raw_attrs.items():
                if key in mapper:
                    renamed[mapper[key]] = val
                else:
                    renamed[key] = val
            # Detect mapper keys that never appeared on the source.
            for src_key in mapper:
                if src_key not in raw_attrs:
                    log.debug(
                        "SWMaps mapper key %r not present on feature %s",
                        src_key,
                        fid,
                    )
            attributes = renamed
        else:
            attributes = dict(raw_attrs)

        record = dict(feature_meta[fid])
        record["geometry_wkt"] = geom.wkt
        record["attributes"] = attributes
        yield record

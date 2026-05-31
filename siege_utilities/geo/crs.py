"""
Configurable default CRS plus geometry-level CRS detection and
axis-order-aware reprojection.

The default-CRS layer (``get_default_crs`` / ``set_default_crs`` /
``reproject_if_needed``) is the existing thin GeoDataFrame-shaped API
that every spatial-returning function in :mod:`siege_utilities.geo`
uses as its default. Call :func:`set_default_crs` once at the top of a
notebook or script to change the default globally::

    import siege_utilities as su
    su.set_default_crs("EPSG:3857")

    # All subsequent calls return Web Mercator unless overridden:
    gdf = su.download_data(2020, "county")  # already in EPSG:3857

:func:`detect_crs` and :func:`reproject_geom` extend the module to
geometry-level work with explicit axis-order control. Pattern lifted
from a third-party tile-server audit (``common/repos/ImportServerRepo.py:150-336``,
specifically the SRS handling at lines 255-274). The salvage source
used the GDAL/OGR Python bindings (``osgeo.osr``) with
``OAMS_TRADITIONAL_GIS_ORDER`` to force lon-first axis order; SU does
not declare ``osgeo`` as a dep, so this module is built on ``pyproj``
(which IS declared). ``pyproj.Transformer.from_crs(..., always_xy=True)``
is the documented modern equivalent of the OGR axis-mapping strategy.

Why the axis-order toggle exists: GeoJSON / Shapefile / KML files store
coordinates lon-first (x, y) but the EPSG authority specifies lat-first
(y, x) for many CRSes including EPSG:4326. The default ``"trad_gis"``
mode honors the file conventions (what most consumers expect). The
``"auth_compliant"`` mode honors the EPSG authority (what GIS
standards-compliant code paths require). Most consumer code expects
``trad_gis``; choosing ``auth_compliant`` without knowing why is a
subtle source of transposed lat/lon bugs.
"""

from __future__ import annotations

import logging
from typing import Any

log = logging.getLogger(__name__)

__all__ = [
    "AXIS_ORDER_TRAD_GIS",
    "AXIS_ORDER_AUTH_COMPLIANT",
    "get_default_crs",
    "set_default_crs",
    "reproject_if_needed",
    "detect_crs",
    "reproject_geom",
]

_DEFAULT_CRS: str = "EPSG:4326"

# Axis-order tokens accepted by reproject_geom.
AXIS_ORDER_TRAD_GIS = "trad_gis"
AXIS_ORDER_AUTH_COMPLIANT = "auth_compliant"
_AXIS_ORDER_VALID = {AXIS_ORDER_TRAD_GIS, AXIS_ORDER_AUTH_COMPLIANT}


def get_default_crs() -> str:
    """Return the current default CRS string (e.g. ``"EPSG:4326"``)."""
    return _DEFAULT_CRS


def set_default_crs(crs: str) -> None:
    """Set the default CRS used by all spatial-returning functions.

    Args:
        crs: Any CRS string accepted by ``pyproj`` (e.g. ``"EPSG:4326"``,
            ``"EPSG:3857"``, ``"ESRI:102003"``).

    Raises:
        pyproj.exceptions.CRSError: If *crs* is not recognized by pyproj.
    """
    from pyproj import CRS as _CRS
    _CRS.from_user_input(crs)
    global _DEFAULT_CRS  # noqa: PLW0603
    _DEFAULT_CRS = crs


def reproject_if_needed(gdf, crs: str | None = None):
    """Reproject *gdf* to *crs* if it differs from the GeoDataFrame's current CRS.

    If *crs* is ``None``, uses :func:`get_default_crs`.
    Returns the GeoDataFrame unchanged if it is already in *crs* or is empty.

    When the GeoDataFrame has no CRS (``gdf.crs is None``) and a target is
    specified, the target CRS is **set** (not reprojected) on the assumption
    that the data is already in the target CRS. A warning is logged because
    this assumption may be wrong.
    """
    if gdf is None:
        return None
    target = crs or get_default_crs()
    if not target or len(gdf) == 0:
        return gdf
    if gdf.crs is None:
        log.warning(
            "GeoDataFrame has no CRS; setting to %s without reprojection. "
            "If the data is in a different CRS, results will be incorrect.",
            target,
        )
        gdf = gdf.set_crs(target)
        return gdf
    from pyproj import CRS as _CRS
    target_crs = _CRS.from_user_input(target)
    if gdf.crs != target_crs:
        return gdf.to_crs(target_crs)
    return gdf


def detect_crs(geom_or_ds: Any) -> str | None:
    """Resolve the source CRS of a spatial object.

    Args:
        geom_or_ds: One of:

            * A GeoDataFrame — reads ``.crs`` and returns an ``EPSG:<n>``
              string when authoritative, otherwise the WKT.
            * A GeoJSON-like ``dict`` — reads
              ``["crs"]["properties"]["name"]`` if present.
            * A fiona ``Collection`` — reads ``.crs`` / ``.crs_wkt``.
            * A bare shapely geometry — bare geometries carry no CRS
              metadata; this returns ``None`` (callers should treat this
              as "consult :func:`get_default_crs`").
            * ``None`` — returns ``None``.

    Returns:
        An EPSG string (``"EPSG:4326"``), a WKT string, or ``None``.

    Mirrors the SRS-detection branch of the salvage source
    (``ImportServerRepo.py:250-253``), which read the spatial reference
    from an OGR DataSource via ``GetGeometryRef().GetSpatialReference()``.
    This implementation reads ``.crs`` / ``.crs_wkt`` from
    GeoDataFrames or fiona collections — same intent, declared-deps
    surface.
    """
    if geom_or_ds is None:
        return None

    # GeoDataFrame
    crs_attr = getattr(geom_or_ds, "crs", None)
    if crs_attr is not None:
        return _normalize_crs(crs_attr)

    # fiona Collection exposes .crs_wkt as well
    crs_wkt = getattr(geom_or_ds, "crs_wkt", None)
    if crs_wkt:
        return _normalize_crs(crs_wkt)

    # GeoJSON-shaped dict
    if isinstance(geom_or_ds, dict):
        crs_block = geom_or_ds.get("crs")
        if isinstance(crs_block, dict):
            name = crs_block.get("properties", {}).get("name")
            if name:
                return _normalize_crs(name)
        return None

    # Bare shapely geometry has no CRS metadata.
    if hasattr(geom_or_ds, "geom_type"):
        return None

    return None


def _normalize_crs(value: Any) -> str:
    """Best-effort normalization of various CRS representations to a string."""
    try:
        from pyproj import CRS
    except ImportError:
        # pyproj is a declared SU geo dep; if it's not present we just
        # stringify and return.
        return str(value)

    try:
        crs = CRS.from_user_input(value)
    except (ValueError, TypeError, RuntimeError) as exc:
        log.debug("Could not parse CRS from %r, falling back to str(): %s", value, exc)
        return str(value)
    epsg = crs.to_epsg()
    if epsg:
        return f"EPSG:{epsg}"
    return crs.to_wkt()


def reproject_geom(
    geom,
    src_crs: Any,
    dst_crs: Any = 4326,
    axis_order: str = AXIS_ORDER_TRAD_GIS,
):
    """Reproject a shapely geometry with explicit axis-order control.

    Args:
        geom: A shapely geometry (``Point``, ``LineString``, ``Polygon``,
            etc.) or ``None``.
        src_crs: The geometry's source CRS, in any form
            :class:`pyproj.CRS.from_user_input` accepts (``"EPSG:4326"``,
            an integer EPSG code, a WKT string, a ``pyproj.CRS`` object).
        dst_crs: Target CRS, in any form :class:`pyproj.CRS.from_user_input`
            accepts. Defaults to ``4326`` (WGS 84).
        axis_order: One of:

            * ``"trad_gis"`` (default) — ``pyproj`` ``always_xy=True``.
              Coordinates are interpreted and emitted as (lon, lat),
              matching GeoJSON, Shapefile, KML, and most consumer
              expectations. This is the modern-pyproj equivalent of
              ``osgeo.osr.OAMS_TRADITIONAL_GIS_ORDER`` used in the
              salvage source (``ImportServerRepo.py:267-268``).
            * ``"auth_compliant"`` — ``always_xy=False``. Coordinates
              follow the CRS authority's declared axis order (lat-first
              for EPSG:4326). Use only if you know your input data is
              lat-first and your consumer expects lat-first.

    Returns:
        A new shapely geometry in the target CRS, or ``None`` if ``geom``
        is ``None``.

    Raises:
        ValueError: If ``axis_order`` is not one of the two accepted
            tokens, or if ``src_crs`` is ``None`` (a CRS-less geometry
            cannot be reprojected without an explicit source).
        ImportError: If ``pyproj`` or ``shapely`` are not installed.

    Round-trip note: 4326 -> 3857 -> 4326 on a Point should return the
    same coordinates within 1e-6 degrees. The test suite verifies this.
    """
    if geom is None:
        return None
    if axis_order not in _AXIS_ORDER_VALID:
        raise ValueError(
            f"axis_order must be one of {sorted(_AXIS_ORDER_VALID)}; "
            f"got {axis_order!r}"
        )
    if src_crs is None:
        raise ValueError(
            "src_crs is required; bare shapely geometries carry no CRS metadata"
        )

    try:
        from pyproj import CRS, Transformer
    except ImportError as exc:  # pragma: no cover - dep guard
        raise ImportError(
            "pyproj is required for reproject_geom. "
            "Install with: pip install 'siege-utilities[geo]'"
        ) from exc

    try:
        from shapely.ops import transform as shapely_transform
    except ImportError as exc:  # pragma: no cover - dep guard
        raise ImportError(
            "shapely is required for reproject_geom. "
            "Install with: pip install 'siege-utilities[geo]'"
        ) from exc

    src = CRS.from_user_input(src_crs)
    dst = CRS.from_user_input(dst_crs)

    # No-op if source equals target.
    if src == dst:
        return geom

    always_xy = axis_order == AXIS_ORDER_TRAD_GIS
    transformer = Transformer.from_crs(src, dst, always_xy=always_xy)
    return shapely_transform(transformer.transform, geom)

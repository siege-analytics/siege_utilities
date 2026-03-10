"""
Configurable default CRS for all spatial-returning functions.

Every function in ``siege_utilities.geo`` that returns spatial data
uses :func:`get_default_crs` as its default ``crs`` argument.  Call
:func:`set_default_crs` once at the top of a notebook or script to
change the default globally::

    import siege_utilities as su
    su.set_default_crs("EPSG:3857")

    # All subsequent calls return Web Mercator unless overridden:
    gdf = su.download_data(2020, "county")  # already in EPSG:3857
"""

from __future__ import annotations

_DEFAULT_CRS: str = "EPSG:4326"


def get_default_crs() -> str:
    """Return the current default CRS string (e.g. ``"EPSG:4326"``)."""
    return _DEFAULT_CRS


def set_default_crs(crs: str) -> None:
    """Set the default CRS used by all spatial-returning functions.

    Args:
        crs: Any CRS string accepted by ``pyproj`` (e.g. ``"EPSG:4326"``,
            ``"EPSG:3857"``, ``"ESRI:102003"``).
    """
    global _DEFAULT_CRS  # noqa: PLW0603
    _DEFAULT_CRS = crs


def reproject_if_needed(gdf, crs: str | None = None):
    """Reproject *gdf* to *crs* if it differs from the GeoDataFrame's current CRS.

    If *crs* is ``None``, uses :func:`get_default_crs`.
    Returns the GeoDataFrame unchanged if it is already in *crs* or is empty.
    """
    if gdf is None:
        return None
    target = crs or get_default_crs()
    if not target or len(gdf) == 0:
        return gdf
    if gdf.crs and str(gdf.crs).upper() != target.upper():
        return gdf.to_crs(target)
    return gdf

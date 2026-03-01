"""
Pure-Python temporal and spatial query helpers.

Uses geopandas.sjoin for spatial queries (no PostGIS required).
"""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import geopandas as gpd


def temporal_filter(
    gdf: "gpd.GeoDataFrame",
    query_date: date,
    valid_from_col: str = "valid_from",
    valid_to_col: str = "valid_to",
    vintage_year_col: str | None = "vintage_year",
) -> "gpd.GeoDataFrame":
    """Filter a GeoDataFrame to rows valid at query_date.

    First tries valid_from/valid_to date range filtering.
    Falls back to vintage_year if date columns are missing or all-null.

    Args:
        gdf: GeoDataFrame with temporal columns
        query_date: Date to query for
        valid_from_col: Column name for validity start date
        valid_to_col: Column name for validity end date
        vintage_year_col: Fallback column for nearest-year matching

    Returns:
        Filtered GeoDataFrame
    """
    import pandas as pd

    has_valid_from = valid_from_col in gdf.columns and gdf[valid_from_col].notna().any()
    has_valid_to = valid_to_col in gdf.columns and gdf[valid_to_col].notna().any()

    if has_valid_from or has_valid_to:
        mask = pd.Series(True, index=gdf.index)

        if has_valid_from:
            from_dates = pd.to_datetime(gdf[valid_from_col]).dt.date
            mask = mask & (from_dates.isna() | (from_dates <= query_date))

        if has_valid_to:
            to_dates = pd.to_datetime(gdf[valid_to_col]).dt.date
            mask = mask & (to_dates.isna() | (to_dates >= query_date))

        result = gdf[mask].copy()
        if len(result) > 0:
            return result

    # Fallback: nearest vintage_year
    if vintage_year_col and vintage_year_col in gdf.columns:
        years = gdf[vintage_year_col].dropna().unique()
        if len(years) > 0:
            candidates = [y for y in years if y <= query_date.year]
            best = max(candidates) if candidates else min(years)
            return gdf[gdf[vintage_year_col] == best].copy()

    return gdf.copy()


def spatial_query(
    boundaries: "gpd.GeoDataFrame",
    points: "gpd.GeoDataFrame",
    predicate: str = "intersects",
) -> "gpd.GeoDataFrame":
    """Spatial join between boundaries and points using geopandas.sjoin.

    Aligns CRS before joining if both GeoDataFrames have a CRS set.

    Args:
        boundaries: GeoDataFrame of boundary polygons (left)
        points: GeoDataFrame of query geometries (right)
        predicate: Spatial predicate (intersects, within, contains, etc.)

    Returns:
        Joined GeoDataFrame with columns from both inputs
    """
    import geopandas as _gpd

    # Align CRS
    if boundaries.crs and points.crs and boundaries.crs != points.crs:
        points = points.to_crs(boundaries.crs)

    return _gpd.sjoin(boundaries, points, how="inner", predicate=predicate)


def point_in_boundary(
    boundaries: "gpd.GeoDataFrame",
    lon: float,
    lat: float,
    predicate: str = "intersects",
) -> "gpd.GeoDataFrame":
    """Find which boundaries contain a single point.

    Convenience wrapper that creates a Point GeoDataFrame and calls
    spatial_query.

    Args:
        boundaries: GeoDataFrame of boundary polygons
        lon: Longitude
        lat: Latitude
        predicate: Spatial predicate

    Returns:
        GeoDataFrame of matching boundaries
    """
    import geopandas as _gpd
    from shapely.geometry import Point

    crs = boundaries.crs or "EPSG:4326"
    pt_gdf = _gpd.GeoDataFrame(
        {"query_lon": [lon], "query_lat": [lat]},
        geometry=[Point(lon, lat)],
        crs=crs,
    )
    result = spatial_query(boundaries, pt_gdf, predicate=predicate)

    # Drop the sjoin index column
    if "index_right" in result.columns:
        result = result.drop(columns=["index_right"])

    return result

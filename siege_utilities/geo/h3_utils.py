"""
H3 hexagonal hierarchical spatial index utilities.

Provides lightweight spatial join approximation using Uber's H3 indexing system.
This serves as a "geo-lite" fallback when full GeoPandas point-in-polygon operations
are too expensive or when an approximate spatial join is acceptable.

Requires: h3>=4.0 (primary), with v3 fallback support.
"""

import logging
import math
from typing import Optional, Union

import pandas as pd

log = logging.getLogger(__name__)

# --- Guard the h3 import ---
try:
    import h3
    H3_AVAILABLE = True

    # Detect h3 API version (v4 vs v3)
    # h3 v4 uses latlng_to_cell; v3 uses geo_to_h3
    _H3_V4 = hasattr(h3, 'latlng_to_cell')
    if _H3_V4:
        log.debug("h3 v4 API detected")
    else:
        log.debug("h3 v3 API detected")
except ImportError:
    h3 = None  # type: ignore[assignment]
    H3_AVAILABLE = False
    _H3_V4 = False
    log.info("h3 not available - H3 spatial index functions will raise ImportError")


def _require_h3():
    """Raise ImportError if h3 is not installed."""
    if not H3_AVAILABLE:
        raise ImportError(
            "h3 is required for H3 spatial index operations. "
            "Install it with: pip install 'siege-utilities[h3]' or pip install 'h3>=4.0'"
        )


# ---------------------------------------------------------------------------
# H3 resolution reference table (approximate hex areas)
# Source: https://h3geo.org/docs/core-library/restable
# ---------------------------------------------------------------------------
_H3_RESOLUTION_AREA_KM2 = {
    0: 4_357_449.416,
    1: 609_788.441,
    2: 86_801.780,
    3: 12_393.434,
    4: 1_770.348,
    5: 252.903,
    6: 36.129,
    7: 5.161,
    8: 0.737,
    9: 0.105,
    10: 0.015,
    11: 0.00215,
    12: 0.000307,
    13: 0.0000439,
    14: 0.00000627,
    15: 0.000000895,
}


def h3_index_points(
    df: pd.DataFrame,
    lat_col: str,
    lon_col: str,
    resolution: int = 8,
) -> pd.Series:
    """
    Compute H3 hex index for each point in a DataFrame.

    Args:
        df: DataFrame with latitude and longitude columns.
        lat_col: Name of the latitude column.
        lon_col: Name of the longitude column.
        resolution: H3 resolution (0-15). Default 8 (~0.74 km^2 hexes).

    Returns:
        pd.Series of H3 hex ID strings, indexed like the input DataFrame.

    Raises:
        ImportError: If h3 is not installed.
        ValueError: If resolution is out of range or columns are missing.
    """
    _require_h3()

    if resolution < 0 or resolution > 15:
        raise ValueError(f"H3 resolution must be 0-15, got {resolution}")

    for col in (lat_col, lon_col):
        if col not in df.columns:
            raise ValueError(f"Column '{col}' not found in DataFrame")

    if _H3_V4:
        hex_ids = df.apply(
            lambda row: h3.latlng_to_cell(row[lat_col], row[lon_col], resolution),
            axis=1,
        )
    else:
        hex_ids = df.apply(
            lambda row: h3.geo_to_h3(row[lat_col], row[lon_col], resolution),
            axis=1,
        )

    hex_ids.name = "h3_index"
    return hex_ids


def h3_index_polygon(
    geometry,
    resolution: int = 8,
) -> set:
    """
    Return the set of H3 hexes covering a polygon geometry.

    Accepts a Shapely Polygon/MultiPolygon or a GeoJSON-like dict.

    Args:
        geometry: A Shapely Polygon/MultiPolygon, or a GeoJSON-like dict with
                  ``type`` and ``coordinates`` keys.
        resolution: H3 resolution (0-15). Default 8.

    Returns:
        set of H3 hex ID strings that cover the polygon.

    Raises:
        ImportError: If h3 is not installed.
        ValueError: If resolution is out of range.
        TypeError: If geometry type is unsupported.
    """
    _require_h3()

    if resolution < 0 or resolution > 15:
        raise ValueError(f"H3 resolution must be 0-15, got {resolution}")

    # Convert Shapely geometry to GeoJSON dict
    geojson = _geometry_to_geojson(geometry)

    geom_type = geojson.get("type", "")

    if geom_type == "Polygon":
        return _polyfill_single(geojson, resolution)
    elif geom_type == "MultiPolygon":
        hexes: set = set()
        for polygon_coords in geojson["coordinates"]:
            single_geojson = {"type": "Polygon", "coordinates": polygon_coords}
            hexes |= _polyfill_single(single_geojson, resolution)
        return hexes
    else:
        raise TypeError(
            f"Unsupported geometry type '{geom_type}'. "
            "Expected Polygon or MultiPolygon."
        )


def _geometry_to_geojson(geometry) -> dict:
    """Convert a Shapely geometry or GeoJSON dict to a GeoJSON dict."""
    if isinstance(geometry, dict):
        return geometry

    # Shapely geometry — use __geo_interface__ (standard protocol)
    if hasattr(geometry, "__geo_interface__"):
        return geometry.__geo_interface__

    raise TypeError(
        f"Cannot convert {type(geometry).__name__} to GeoJSON. "
        "Provide a Shapely geometry or a GeoJSON dict."
    )


def _polyfill_single(geojson: dict, resolution: int) -> set:
    """Polyfill a single GeoJSON Polygon."""
    if _H3_V4:
        # h3 v4: polygon_to_cells expects a LatLngPoly
        # GeoJSON coordinates are (lng, lat); h3 v4 wants (lat, lng)
        outer = geojson["coordinates"][0]
        holes = geojson["coordinates"][1:] if len(geojson["coordinates"]) > 1 else []
        outer_latlng = [(pt[1], pt[0]) for pt in outer]
        holes_latlng = [
            [(pt[1], pt[0]) for pt in hole] for hole in holes
        ]
        poly = h3.LatLngPoly(outer_latlng, *holes_latlng)
        return set(h3.polygon_to_cells(poly, resolution))
    else:
        # h3 v3: polyfill with GeoJSON dict, geo_json_conforming=True
        return h3.polyfill(geojson, resolution, geo_json_conforming=True)


def h3_spatial_join(
    points_df: pd.DataFrame,
    polygons_gdf,
    lat_col: str,
    lon_col: str,
    resolution: int = 8,
    polygon_id_col: Optional[str] = None,
) -> pd.DataFrame:
    """
    Join points to polygons via H3 hex matching (approximate point-in-polygon).

    This is a lightweight alternative to GeoPandas ``sjoin``.  Each polygon is
    decomposed into H3 hexes, and each point is assigned to the hex it falls
    in.  Points and polygons sharing a hex are joined.

    Note: This is an *approximation*. Points near polygon boundaries may be
    misclassified due to hex granularity.

    Args:
        points_df: DataFrame with latitude/longitude columns.
        polygons_gdf: GeoDataFrame (or any object with a ``geometry`` column
                      and an iterable of rows). Each geometry must be a
                      Polygon or MultiPolygon.
        lat_col: Name of the latitude column in ``points_df``.
        lon_col: Name of the longitude column in ``points_df``.
        resolution: H3 resolution (0-15). Default 8.
        polygon_id_col: Optional column in ``polygons_gdf`` to use as the
                        polygon identifier. If None, the index is used.

    Returns:
        pd.DataFrame with the original point columns plus polygon attributes
        for matched rows. Unmatched points are excluded.

    Raises:
        ImportError: If h3 is not installed.
    """
    _require_h3()

    # 1. Index all points
    point_hexes = h3_index_points(points_df, lat_col, lon_col, resolution)
    points_indexed = points_df.copy()
    points_indexed["_h3_index"] = point_hexes

    # 2. Build hex -> polygon mapping
    hex_to_polygon: dict = {}
    polygon_attrs: dict = {}

    for idx, row in polygons_gdf.iterrows():
        poly_id = row[polygon_id_col] if polygon_id_col else idx
        geom = row["geometry"]
        hexes = h3_index_polygon(geom, resolution)
        # Store polygon attributes (excluding geometry)
        attrs = {
            col: row[col]
            for col in polygons_gdf.columns
            if col != "geometry"
        }
        polygon_attrs[poly_id] = attrs
        for hex_id in hexes:
            # First polygon wins for overlapping hexes
            if hex_id not in hex_to_polygon:
                hex_to_polygon[hex_id] = poly_id

    # 3. Join via hex lookup
    points_indexed["_poly_id"] = points_indexed["_h3_index"].map(hex_to_polygon)
    matched = points_indexed.dropna(subset=["_poly_id"]).copy()

    if matched.empty:
        # Return empty DataFrame with expected columns
        extra_cols = [
            col for col in polygons_gdf.columns if col != "geometry"
        ]
        for col in extra_cols:
            matched[col] = pd.Series(dtype="object")
        matched.drop(columns=["_h3_index", "_poly_id"], inplace=True)
        return matched

    # 4. Merge polygon attributes
    poly_attr_df = pd.DataFrame.from_dict(polygon_attrs, orient="index")
    poly_attr_df.index.name = "_poly_id"
    poly_attr_df = poly_attr_df.reset_index()

    matched = matched.merge(poly_attr_df, on="_poly_id", how="left")
    matched.drop(columns=["_h3_index", "_poly_id"], inplace=True)

    return matched.reset_index(drop=True)


def h3_hex_to_boundary(hex_id: str) -> list:
    """
    Return the boundary coordinates for an H3 hex cell.

    Args:
        hex_id: H3 hex ID string.

    Returns:
        list of (lat, lng) tuples forming the hex boundary (closed ring).

    Raises:
        ImportError: If h3 is not installed.
    """
    _require_h3()

    if _H3_V4:
        boundary = h3.cell_to_boundary(hex_id)
    else:
        boundary = h3.h3_to_geo_boundary(hex_id, geo_json=False)

    return list(boundary)


def h3_resolution_for_area(target_area_km2: float) -> int:
    """
    Suggest the H3 resolution whose hex area best matches a target area.

    Args:
        target_area_km2: Target hex area in square kilometres.

    Returns:
        int: H3 resolution (0-15) whose average hex area is closest to the
        target. Comparison is done in log-space for better matching across
        orders of magnitude.

    Raises:
        ImportError: If h3 is not installed.
        ValueError: If target_area_km2 is not positive.
    """
    _require_h3()

    if target_area_km2 <= 0:
        raise ValueError(f"target_area_km2 must be positive, got {target_area_km2}")

    log_target = math.log10(target_area_km2)
    best_res = 0
    best_diff = float("inf")

    for res, area in _H3_RESOLUTION_AREA_KM2.items():
        diff = abs(math.log10(area) - log_target)
        if diff < best_diff:
            best_diff = diff
            best_res = res

    return best_res

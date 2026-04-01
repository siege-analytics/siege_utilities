"""Layer 2: Boundary operations built on Layer 1 spatial primitives.

Source-agnostic operations on polygon boundaries — works with Census TIGER,
GADM, redistricting plans, custom shapefiles, or any polygon source.

Usage::

    from siege_utilities.geo.spark_boundary_ops import (
        assign_boundaries, intersect_boundaries, apportion,
    )
    from siege_utilities.geo.spark_spatial import load_polygons, load_points

    # Load any polygon and point sources
    districts = load_polygons(spark, "s3a://boundaries/tiger/cd/2020/data.parquet")
    addresses = load_points(spark, "s3a://data/addresses.csv")

    # Assign each address to its containing district
    assigned = assign_boundaries(addresses, districts, point_geom="geometry", polygon_geom="geometry")

    # Find overlap between two boundary sets
    overlaps = intersect_boundaries(districts, counties)

    # Apportion population from tracts to districts
    apportioned = apportion(tracts, districts, weight_col="total_population")
"""

from __future__ import annotations

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


def assign_boundaries(
    points: Any,
    polygons: Any,
    *,
    point_geom: str = "geometry",
    polygon_geom: str = "geometry",
    how: str = "left",
    broadcast_polygons: bool = True,
) -> Any:
    """Assign each point to its containing polygon(s).

    This is the core DSTK replacement operation — given addresses (points)
    and boundaries (polygons), determine which boundary contains each address.

    Parameters
    ----------
    points : DataFrame
        Spark DataFrame with point geometries (WKT POINT strings).
    polygons : DataFrame
        Spark DataFrame with polygon geometries (WKT POLYGON/MULTIPOLYGON strings).
    point_geom, polygon_geom : str
        Geometry column names.
    how : str
        Join type: 'left' keeps all points (unmatched get NULL boundary),
        'inner' drops unmatched points.
    broadcast_polygons : bool
        If True, broadcast the polygon DataFrame for efficiency (use when
        polygons are small — e.g., 440 congressional districts — and points
        are large — e.g., 128M addresses).

    Returns
    -------
    DataFrame
        Points enriched with polygon attributes (geoid, name, etc.).
    """
    from siege_utilities.geo.spark_spatial import ensure_sedona

    spark = points.sparkSession
    ensure_sedona(spark)

    if broadcast_polygons:
        from pyspark.sql.functions import broadcast
        polygons = broadcast(polygons)

    points.createOrReplaceTempView("_assign_points")
    polygons.createOrReplaceTempView("_assign_polygons")

    return spark.sql(
        f"SELECT p.*, poly.* "
        f"FROM _assign_points p {how.upper()} JOIN _assign_polygons poly "
        f"ON ST_Contains("
        f"ST_GeomFromText(poly.{polygon_geom}), "
        f"ST_GeomFromText(p.{point_geom}))"
    )


def intersect_boundaries(
    poly_a: Any,
    poly_b: Any,
    *,
    a_geom: str = "geometry",
    b_geom: str = "geometry",
    compute_area: bool = True,
) -> Any:
    """Find overlapping regions between two polygon boundary sets.

    Useful for county-to-district apportionment, boundary change analysis,
    or any overlap computation between two polygon layers.

    Parameters
    ----------
    poly_a, poly_b : DataFrame
        Polygon boundary DataFrames.
    a_geom, b_geom : str
        Geometry column names.
    compute_area : bool
        If True, compute the area of each intersection region.

    Returns
    -------
    DataFrame
        All pairs of overlapping polygons with intersection geometry
        and optionally intersection area.
    """
    from siege_utilities.geo.spark_spatial import ensure_sedona

    spark = poly_a.sparkSession
    ensure_sedona(spark)

    poly_a.createOrReplaceTempView("_isect_a")
    poly_b.createOrReplaceTempView("_isect_b")

    area_col = ""
    if compute_area:
        area_col = (
            ", ST_Area(ST_Intersection("
            f"ST_GeomFromText(a.{a_geom}), ST_GeomFromText(b.{b_geom})"
            ")) AS intersection_area"
        )

    return spark.sql(
        f"SELECT a.*, b.*"
        f", ST_AsText(ST_Intersection("
        f"ST_GeomFromText(a.{a_geom}), ST_GeomFromText(b.{b_geom})"
        f")) AS intersection_geometry"
        f"{area_col} "
        f"FROM _isect_a a, _isect_b b "
        f"WHERE ST_Intersects("
        f"ST_GeomFromText(a.{a_geom}), ST_GeomFromText(b.{b_geom}))"
    )


def apportion(
    source_polys: Any,
    target_polys: Any,
    weight_col: str,
    *,
    source_geom: str = "geometry",
    target_geom: str = "geometry",
    method: str = "area",
) -> Any:
    """Apportion a value from source polygons to target polygons by overlap.

    Example: apportion tract population to congressional districts based on
    the fraction of each tract's area that overlaps each district.

    Parameters
    ----------
    source_polys : DataFrame
        Source polygons with the value to apportion (e.g., tracts with population).
    target_polys : DataFrame
        Target polygons to receive apportioned values (e.g., districts).
    weight_col : str
        Column in source_polys containing the value to apportion.
    source_geom, target_geom : str
        Geometry column names.
    method : str
        'area' — apportion by geographic area overlap fraction.

    Returns
    -------
    DataFrame
        Target polygons with apportioned values. Each target gets the
        sum of (source_value * overlap_fraction) across all overlapping sources.
    """
    from siege_utilities.geo.spark_spatial import ensure_sedona

    spark = source_polys.sparkSession
    ensure_sedona(spark)

    source_polys.createOrReplaceTempView("_apportion_src")
    target_polys.createOrReplaceTempView("_apportion_tgt")

    return spark.sql(f"""
        SELECT
            t.*,
            SUM(s.{weight_col} * (
                ST_Area(ST_Intersection(
                    ST_GeomFromText(s.{source_geom}),
                    ST_GeomFromText(t.{target_geom})
                )) / NULLIF(ST_Area(ST_GeomFromText(s.{source_geom})), 0)
            )) AS apportioned_{weight_col}
        FROM _apportion_tgt t, _apportion_src s
        WHERE ST_Intersects(
            ST_GeomFromText(s.{source_geom}),
            ST_GeomFromText(t.{target_geom})
        )
        GROUP BY t.*
    """)


def multi_assign(
    points: Any,
    boundary_layers: dict,
    *,
    point_geom: str = "geometry",
) -> Any:
    """Assign points to multiple boundary layers simultaneously.

    Convenience method that calls ``assign_boundaries`` for each layer
    and joins the results.

    Parameters
    ----------
    points : DataFrame
        Point DataFrame.
    boundary_layers : dict
        Mapping of {layer_name: polygon_DataFrame}. Each polygon DataFrame
        must have a geometry column and identifying columns (geoid, name).
    point_geom : str
        Point geometry column name.

    Returns
    -------
    DataFrame
        Points enriched with boundary IDs from all layers.
        Columns named as ``{layer_name}_geoid``, ``{layer_name}_name``.

    Example
    -------
    >>> layers = {
    ...     "cd": load_boundaries(spark, "cd", 2020),
    ...     "county": load_boundaries(spark, "county", 2020),
    ...     "state": load_boundaries(spark, "state", 2020),
    ... }
    >>> enriched = multi_assign(addresses, layers)
    >>> # enriched has: cd_geoid, cd_name, county_geoid, county_name, state_geoid, state_name
    """
    from pyspark.sql.functions import col

    result = points
    for layer_name, polygons in boundary_layers.items():
        # Rename polygon columns to avoid collision
        renamed = polygons
        if "geoid" in polygons.columns:
            renamed = renamed.withColumnRenamed("geoid", f"{layer_name}_geoid")
        if "name" in polygons.columns:
            renamed = renamed.withColumnRenamed("name", f"{layer_name}_name")

        # Drop the polygon geometry from the result to avoid column collision
        keep_cols = [c for c in renamed.columns if c != "geometry"]

        assigned = assign_boundaries(
            result, renamed,
            point_geom=point_geom,
            polygon_geom="geometry",
            how="left",
        )

        # Select only the new columns + original columns
        result_cols = [col(c) for c in result.columns]
        new_cols = [col(c) for c in keep_cols if c not in result.columns]
        result = assigned.select(*(result_cols + new_cols))

    return result

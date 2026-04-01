"""Layer 1: Spark Sedona geometry primitives (source-agnostic).

Low-level spatial I/O and operations that work with any geometry source —
Census TIGER, GADM, OpenStreetMap, redistricting plans, custom shapefiles.
These are the building blocks that higher-level functions compose.

Requires Apache Sedona on the Spark cluster::

    spark.sql.extensions: org.apache.sedona.sql.SedonaSqlExtensions
    spark.serializer: org.apache.spark.serializer.KryoSerializer
    spark.kryo.registrator: org.apache.sedona.core.serde.SedonaKryoRegistrator

Usage::

    from siege_utilities.geo.spark_spatial import (
        load_polygons, load_points, spatial_join, buffer, distance,
        ensure_sedona,
    )

    # Load any polygon source
    districts = load_polygons(spark, "s3a://boundaries/tiger/cd/2020/data.parquet")
    custom = load_polygons(spark, "/path/to/redistricting_plan.geojson", format="geojson")

    # Spatial join: which polygon contains each point?
    result = spatial_join(addresses, districts, predicate="contains")

    # Buffer: expand polygons by 5km
    buffered = buffer(districts, distance_m=5000)
"""

from __future__ import annotations

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Sedona initialization
# ---------------------------------------------------------------------------

_sedona_registered = False


def ensure_sedona(spark: Any) -> None:
    """Register Sedona SQL functions with the Spark session.

    Safe to call multiple times — only registers once per process.

    Raises
    ------
    ImportError
        If Sedona is not installed or not available on the cluster.
    """
    global _sedona_registered
    if _sedona_registered:
        return

    try:
        from sedona.register import SedonaRegistrator

        SedonaRegistrator.registerAll(spark)
        _sedona_registered = True
        logger.info("Sedona spatial functions registered")
    except ImportError:
        raise ImportError(
            "Apache Sedona is not available. Add sedona-spark to "
            "spark.jars.packages in the Spark Connect server config."
        ) from None


# ---------------------------------------------------------------------------
# Layer 1: Geometry I/O — load any spatial data into Spark
# ---------------------------------------------------------------------------

def load_polygons(
    spark: Any,
    path: str,
    *,
    geometry_col: str = "geometry",
    format: str = "auto",
    crs: Optional[str] = None,
) -> Any:
    """Load polygon geometries from any supported format.

    Parameters
    ----------
    spark : SparkSession
        Active Spark session.
    path : str
        Path to spatial data — local, S3 (s3a://), or HDFS.
    geometry_col : str
        Name of the geometry column in the output DataFrame.
    format : str
        'auto' (detect from extension), 'geoparquet', 'parquet', 'geojson',
        'shapefile', 'wkt_csv'. For parquet/csv, geometry is expected as WKT string.
    crs : str, optional
        Target CRS to reproject to (e.g., 'EPSG:4326'). None keeps original.

    Returns
    -------
    DataFrame
        Spark DataFrame with a ``geometry`` column (WKT string) and all
        attribute columns from the source.
    """
    if format == "auto":
        format = _detect_format(path)

    if format in ("geoparquet", "parquet"):
        df = spark.read.parquet(path)
        # Ensure geometry column exists and is named correctly
        if geometry_col not in df.columns and "geom" in df.columns:
            from pyspark.sql.functions import col
            df = df.withColumnRenamed("geom", geometry_col)
        return df

    elif format == "geojson":
        return _load_via_geopandas(spark, path, geometry_col, crs)

    elif format == "shapefile":
        return _load_via_geopandas(spark, path, geometry_col, crs)

    elif format == "wkt_csv":
        df = spark.read.option("header", True).csv(path)
        return df

    else:
        raise ValueError(
            f"Unsupported format: {format!r}. "
            f"Use: geoparquet, parquet, geojson, shapefile, wkt_csv"
        )


def load_points(
    spark: Any,
    path: str,
    *,
    lat_col: str = "lat",
    lon_col: str = "lon",
    geometry_col: str = "geometry",
    format: str = "auto",
) -> Any:
    """Load point geometries from tabular data with lat/lon columns.

    Parameters
    ----------
    spark : SparkSession
        Active Spark session.
    path : str
        Path to tabular data (CSV, Parquet).
    lat_col, lon_col : str
        Column names for latitude and longitude.
    geometry_col : str
        Name for the generated geometry column.
    format : str
        'auto', 'csv', or 'parquet'.

    Returns
    -------
    DataFrame
        Spark DataFrame with a ``geometry`` column (WKT POINT string)
        plus all original columns.
    """
    if format == "auto":
        format = "parquet" if path.endswith(".parquet") else "csv"

    if format == "csv":
        df = spark.read.option("header", True).option("inferSchema", True).csv(path)
    else:
        df = spark.read.parquet(path)

    from pyspark.sql.functions import concat, lit, col

    return df.withColumn(
        geometry_col,
        concat(lit("POINT("), col(lon_col).cast("string"), lit(" "), col(lat_col).cast("string"), lit(")")),
    )


def load_lines(
    spark: Any,
    path: str,
    *,
    geometry_col: str = "geometry",
    format: str = "auto",
    crs: Optional[str] = None,
) -> Any:
    """Load line/multiline geometries from any supported format.

    Same interface as ``load_polygons`` — works for roads, rivers, transit routes.
    """
    return load_polygons(spark, path, geometry_col=geometry_col, format=format, crs=crs)


def create_points_from_coords(
    df: Any,
    lat_col: str = "lat",
    lon_col: str = "lon",
    geometry_col: str = "geometry",
) -> Any:
    """Add a WKT POINT geometry column to an existing DataFrame.

    Parameters
    ----------
    df : DataFrame
        Spark DataFrame with latitude and longitude columns.
    lat_col, lon_col : str
        Column names for coordinates.
    geometry_col : str
        Name for the new geometry column.

    Returns
    -------
    DataFrame
        Input DataFrame with geometry column added.
    """
    from pyspark.sql.functions import concat, lit, col

    return df.withColumn(
        geometry_col,
        concat(
            lit("POINT("),
            col(lon_col).cast("string"),
            lit(" "),
            col(lat_col).cast("string"),
            lit(")"),
        ),
    )


# ---------------------------------------------------------------------------
# Layer 1: Spatial operations — predicate-based, source-agnostic
# ---------------------------------------------------------------------------

def spatial_join(
    left: Any,
    right: Any,
    predicate: str = "contains",
    *,
    how: str = "inner",
    left_geom: str = "geometry",
    right_geom: str = "geometry",
) -> Any:
    """Spatial join two DataFrames using a geometric predicate.

    Parameters
    ----------
    left, right : DataFrame
        Spark DataFrames with geometry columns (WKT strings).
    predicate : str
        Spatial predicate: 'contains', 'within', 'intersects', 'touches',
        'crosses', 'overlaps'.
    how : str
        Join type: 'inner', 'left', 'right', 'full'.
    left_geom, right_geom : str
        Geometry column names.

    Returns
    -------
    DataFrame
        Joined result.
    """
    spark = left.sparkSession
    ensure_sedona(spark)

    left.createOrReplaceTempView("_sjoin_left")
    right.createOrReplaceTempView("_sjoin_right")

    st_func = f"ST_{predicate.capitalize()}"

    sql = (
        f"SELECT l.*, r.* "
        f"FROM _sjoin_left l {how.upper()} JOIN _sjoin_right r "
        f"ON {st_func}("
        f"ST_GeomFromText(l.{left_geom}), "
        f"ST_GeomFromText(r.{right_geom}))"
    )
    return spark.sql(sql)


def buffer(
    df: Any,
    distance_m: float,
    geometry_col: str = "geometry",
    output_col: Optional[str] = None,
) -> Any:
    """Buffer geometries by a distance.

    Parameters
    ----------
    df : DataFrame
        Spark DataFrame with geometry column.
    distance_m : float
        Buffer distance in meters (for geographic CRS, uses approximate degrees).
    geometry_col : str
        Input geometry column name.
    output_col : str, optional
        Output column name. Defaults to ``{geometry_col}_buffered``.

    Returns
    -------
    DataFrame
        DataFrame with buffered geometry column added.
    """
    spark = df.sparkSession
    ensure_sedona(spark)

    out = output_col or f"{geometry_col}_buffered"
    # Approximate meters to degrees for WGS84 (1 degree ≈ 111,320 m at equator)
    degrees = distance_m / 111320.0

    df.createOrReplaceTempView("_buf_tbl")
    return spark.sql(
        f"SELECT *, ST_AsText(ST_Buffer(ST_GeomFromText({geometry_col}), {degrees})) "
        f"AS {out} FROM _buf_tbl"
    )


def distance(
    left: Any,
    right: Any,
    *,
    left_geom: str = "geometry",
    right_geom: str = "geometry",
    output_col: str = "distance_degrees",
) -> Any:
    """Calculate pairwise distance between two geometry DataFrames.

    Parameters
    ----------
    left, right : DataFrame
        Spark DataFrames with geometry columns.
    left_geom, right_geom : str
        Geometry column names.
    output_col : str
        Name for the distance column.

    Returns
    -------
    DataFrame
        Cross-joined result with distance column (in CRS units — degrees for WGS84).
    """
    spark = left.sparkSession
    ensure_sedona(spark)

    left.createOrReplaceTempView("_dist_left")
    right.createOrReplaceTempView("_dist_right")

    return spark.sql(
        f"SELECT l.*, r.*, "
        f"ST_Distance(ST_GeomFromText(l.{left_geom}), ST_GeomFromText(r.{right_geom})) "
        f"AS {output_col} "
        f"FROM _dist_left l, _dist_right r"
    )


def nearest(
    points: Any,
    targets: Any,
    *,
    k: int = 1,
    max_distance_degrees: Optional[float] = None,
    point_geom: str = "geometry",
    target_geom: str = "geometry",
) -> Any:
    """Find the k nearest targets for each point.

    Parameters
    ----------
    points, targets : DataFrame
        Point and target geometry DataFrames.
    k : int
        Number of nearest targets per point.
    max_distance_degrees : float, optional
        Maximum search distance in degrees.
    point_geom, target_geom : str
        Geometry column names.

    Returns
    -------
    DataFrame
        Points with nearest target(s) and distance.
    """
    spark = points.sparkSession
    ensure_sedona(spark)

    points.createOrReplaceTempView("_nn_points")
    targets.createOrReplaceTempView("_nn_targets")

    dist_filter = ""
    if max_distance_degrees:
        dist_filter = f"WHERE d < {max_distance_degrees}"

    return spark.sql(f"""
        SELECT * FROM (
            SELECT p.*, t.*,
                ST_Distance(ST_GeomFromText(p.{point_geom}), ST_GeomFromText(t.{target_geom})) AS d,
                ROW_NUMBER() OVER (PARTITION BY p.{point_geom} ORDER BY
                    ST_Distance(ST_GeomFromText(p.{point_geom}), ST_GeomFromText(t.{target_geom}))) AS rn
            FROM _nn_points p, _nn_targets t
            {dist_filter}
        ) WHERE rn <= {k}
    """)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _detect_format(path: str) -> str:
    """Detect spatial format from file extension."""
    path_lower = path.lower()
    if path_lower.endswith(".parquet") or path_lower.endswith(".geoparquet"):
        return "parquet"
    elif path_lower.endswith(".geojson") or path_lower.endswith(".json"):
        return "geojson"
    elif path_lower.endswith(".shp"):
        return "shapefile"
    elif path_lower.endswith(".csv"):
        return "wkt_csv"
    elif "/" in path_lower and not "." in path_lower.split("/")[-1]:
        # Directory path — assume parquet
        return "parquet"
    return "parquet"


def _load_via_geopandas(spark, path, geometry_col, crs):
    """Load spatial file via GeoPandas, convert to Spark DataFrame with WKT."""
    import geopandas as gpd
    import pandas as pd

    gdf = gpd.read_file(path)
    if crs:
        gdf = gdf.to_crs(crs)

    pdf = pd.DataFrame(gdf.drop(columns="geometry"))
    pdf[geometry_col] = gdf.geometry.apply(
        lambda g: g.wkt if g is not None else None
    )
    return spark.createDataFrame(pdf)

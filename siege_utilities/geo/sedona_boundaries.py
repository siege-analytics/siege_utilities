"""Spark Sedona boundary loading utilities.

Load Census TIGER boundaries as Sedona-ready Spark DataFrames for distributed
spatial operations (point-in-polygon, proximity, intersection).

One generic ``load_boundaries()`` function handles all boundary types — pass
the type as an argument, not a separate function per type.

Usage::

    from siege_utilities.geo.sedona_boundaries import load_boundaries, broadcast_boundaries

    # Load congressional districts as Sedona DataFrame
    districts = load_boundaries(spark, "cd", year=2020)

    # Broadcast for efficient point-in-polygon
    districts_bc = broadcast_boundaries(spark, districts)

    # Spatial join: which district contains each address?
    result = spark.sql('''
        SELECT a.*, d.geoid, d.name
        FROM addresses a, districts_bc d
        WHERE ST_Contains(ST_GeomFromText(d.geometry), ST_Point(a.lon, a.lat))
    ''')

Requires Apache Sedona on the Spark cluster (``spark.sql.extensions:
org.apache.sedona.sql.SedonaSqlExtensions``).
"""

from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Canonical boundary type → TIGER file type mapping
# Matches siege_utilities.geo.boundary_providers.CANONICAL_GEOGRAPHIC_LEVELS
BOUNDARY_TYPES = {
    "state": {"tiger_type": "state", "geoid_length": 2},
    "county": {"tiger_type": "county", "geoid_length": 5},
    "tract": {"tiger_type": "tract", "geoid_length": 11},
    "blockgroup": {"tiger_type": "bg", "geoid_length": 12},
    "block": {"tiger_type": "tabblock20", "geoid_length": 15},
    "place": {"tiger_type": "place", "geoid_length": 7},
    "zcta": {"tiger_type": "zcta520", "geoid_length": 5},
    "cd": {"tiger_type": "cd", "geoid_length": 4},
    "sldu": {"tiger_type": "sldu", "geoid_length": 5},
    "sldl": {"tiger_type": "sldl", "geoid_length": 5},
    "vtd": {"tiger_type": "vtd20", "geoid_length": 8},
    "cbsa": {"tiger_type": "cbsa", "geoid_length": 5},
}


def load_boundaries(
    spark,
    boundary_type: str,
    year: int = 2020,
    state_fips: Optional[str] = None,
    source: str = "s3",
    s3_base: str = "s3a://boundaries/tiger",
) -> "DataFrame":
    """Load Census TIGER boundaries as a Sedona-ready Spark DataFrame.

    Parameters
    ----------
    spark : SparkSession
        Active Spark session (with Sedona registered).
    boundary_type : str
        One of: state, county, tract, blockgroup, block, place, zcta,
        cd, sldu, sldl, vtd, cbsa.
    year : int
        Census vintage year (default 2020).
    state_fips : str, optional
        2-digit state FIPS code to filter boundaries (e.g., '06' for CA).
    source : str
        's3' to read pre-staged GeoParquet from S3, 'census' to fetch
        live from Census TIGER API (slower but always current).
    s3_base : str
        Base S3 path for staged boundary files.

    Returns
    -------
    DataFrame
        Spark DataFrame with columns: geoid, name, geometry (WKT string),
        state_fips (if applicable), area_land, area_water.

    Raises
    ------
    ValueError
        If boundary_type is not recognized.
    """
    if boundary_type not in BOUNDARY_TYPES:
        raise ValueError(
            f"Unknown boundary type: {boundary_type!r}. "
            f"Valid types: {sorted(BOUNDARY_TYPES.keys())}"
        )

    config = BOUNDARY_TYPES[boundary_type]

    if source == "s3":
        return _load_from_s3(spark, boundary_type, year, state_fips, s3_base)
    elif source == "census":
        return _load_from_census_api(spark, boundary_type, year, state_fips)
    else:
        raise ValueError(f"Unknown source: {source!r}. Use 's3' or 'census'.")


def broadcast_boundaries(spark, boundary_df) -> "DataFrame":
    """Wrap a boundary DataFrame in Spark broadcast for efficient spatial joins.

    Use this when joining a large DataFrame (millions of points) against
    a smaller boundary set (hundreds to thousands of polygons).

    Parameters
    ----------
    spark : SparkSession
        Active Spark session.
    boundary_df : DataFrame
        Boundary DataFrame from ``load_boundaries()``.

    Returns
    -------
    DataFrame
        Broadcast-wrapped DataFrame. Use in SQL joins or DataFrame joins.
    """
    from pyspark.sql.functions import broadcast

    return broadcast(boundary_df)


def stage_boundaries_to_s3(
    spark,
    boundary_type: str,
    year: int = 2020,
    s3_base: str = "s3a://boundaries/tiger",
) -> str:
    """Stage Census TIGER boundaries to S3 as GeoParquet for fast loading.

    Fetches boundaries from Census API via GeoPandas, converts geometry
    to WKT, and writes as Parquet to S3. Returns the S3 path written.

    This is a Spark-native alternative to the Django management command
    ``stage_boundaries_s3``.

    Parameters
    ----------
    spark : SparkSession
        Active Spark session.
    boundary_type : str
        Boundary type (see ``load_boundaries``).
    year : int
        Census vintage year.
    s3_base : str
        Base S3 path for output.

    Returns
    -------
    str
        S3 path where the boundaries were written.
    """
    s3_path = f"{s3_base}/{boundary_type}/{year}/data.parquet"

    # Fetch via siege_utilities boundary provider (uses Census API)
    from siege_utilities.geo.boundary_providers import CensusTIGERProvider

    provider = CensusTIGERProvider()
    gdf = provider.get_boundary(boundary_type, year=year)

    if gdf is None or len(gdf) == 0:
        logger.warning("No boundaries returned for %s/%s", boundary_type, year)
        return s3_path

    # Convert geometry to WKT for Spark/Sedona compatibility
    import pandas as pd

    pdf = pd.DataFrame(gdf.drop(columns="geometry"))
    pdf["geometry"] = gdf.geometry.apply(lambda g: g.wkt if g is not None else None)

    # Write to S3 via Spark
    sdf = spark.createDataFrame(pdf)
    sdf.write.mode("overwrite").parquet(s3_path)

    logger.info(
        "Staged %d %s boundaries to %s", len(gdf), boundary_type, s3_path
    )
    return s3_path


def _load_from_s3(spark, boundary_type, year, state_fips, s3_base):
    """Load pre-staged boundaries from S3 GeoParquet."""
    s3_path = f"{s3_base}/{boundary_type}/{year}/data.parquet"

    try:
        df = spark.read.parquet(s3_path)
    except Exception as e:
        logger.warning(
            "Boundaries not found at %s — try stage_boundaries_to_s3() first. Error: %s",
            s3_path,
            e,
        )
        raise FileNotFoundError(
            f"No staged boundaries at {s3_path}. "
            f"Run stage_boundaries_to_s3(spark, '{boundary_type}', {year}) first."
        ) from e

    if state_fips and "state_fips" in df.columns:
        df = df.filter(df.state_fips == state_fips)

    return df


def _load_from_census_api(spark, boundary_type, year, state_fips):
    """Load boundaries live from Census TIGER API via GeoPandas."""
    from siege_utilities.geo.boundary_providers import CensusTIGERProvider

    provider = CensusTIGERProvider()
    gdf = provider.get_boundary(
        boundary_type, year=year, state_fips=state_fips
    )

    if gdf is None or len(gdf) == 0:
        raise ValueError(
            f"No boundaries returned from Census API for {boundary_type}/{year}"
        )

    # Convert to Spark DataFrame with WKT geometry
    import pandas as pd

    pdf = pd.DataFrame(gdf.drop(columns="geometry"))
    pdf["geometry"] = gdf.geometry.apply(lambda g: g.wkt if g is not None else None)

    return spark.createDataFrame(pdf)

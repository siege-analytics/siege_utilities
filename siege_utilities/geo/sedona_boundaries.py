"""Layer 3: Census TIGER and GADM boundary convenience functions.

Thin wrappers around Layer 1 (spark_spatial) and Layer 2 (spark_boundary_ops)
that know about specific data sources — Census TIGER, GADM, RDH redistricting
plans. These call ``load_polygons()`` with the correct paths and parameters.

For custom boundary sources, use Layer 1/2 directly.

Usage::

    from siege_utilities.geo.sedona_boundaries import load_census_boundaries

    # Load congressional districts — just a convenience for load_polygons()
    districts = load_census_boundaries(spark, "cd", year=2020)

    # Load GADM international boundaries
    countries = load_gadm_boundaries(spark, level=0)
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from siege_utilities.geo.spark_spatial import load_polygons

logger = logging.getLogger(__name__)

# Census TIGER boundary types → S3 path convention
CENSUS_BOUNDARY_TYPES = {
    "state", "county", "tract", "blockgroup", "block", "place",
    "zcta", "cd", "sldu", "sldl", "vtd", "cbsa",
}


def load_census_boundaries(
    spark: Any,
    boundary_type: str,
    year: int = 2020,
    state_fips: Optional[str] = None,
    s3_base: str = "s3a://boundaries/tiger",
) -> Any:
    """Load Census TIGER boundaries as a Sedona-ready Spark DataFrame.

    Convenience wrapper around ``load_polygons()`` that resolves
    the S3 path from boundary type and year.

    Parameters
    ----------
    spark : SparkSession
    boundary_type : str
        One of: state, county, tract, blockgroup, block, place, zcta,
        cd, sldu, sldl, vtd, cbsa.
    year : int
        Census vintage year (default 2020).
    state_fips : str, optional
        2-digit state FIPS to filter (e.g., '06' for CA).
    s3_base : str
        Base S3 path for staged TIGER GeoParquet.

    Returns
    -------
    DataFrame
        Spark DataFrame with geometry (WKT), geoid, name, and other attributes.
    """
    if boundary_type not in CENSUS_BOUNDARY_TYPES:
        raise ValueError(
            f"Unknown Census boundary type: {boundary_type!r}. "
            f"Valid: {sorted(CENSUS_BOUNDARY_TYPES)}"
        )

    path = f"{s3_base}/{boundary_type}/{year}/data.parquet"

    try:
        df = load_polygons(spark, path)
    except Exception as e:
        raise FileNotFoundError(
            f"Census boundaries not staged at {path}. "
            f"Run stage_census_boundaries(spark, '{boundary_type}', {year}) first."
        ) from e

    if state_fips and "state_fips" in df.columns:
        df = df.filter(df.state_fips == state_fips)

    return df


def load_gadm_boundaries(
    spark: Any,
    level: int = 0,
    country: Optional[str] = None,
    s3_base: str = "s3a://boundaries/gadm",
) -> Any:
    """Load GADM (Global Administrative Areas) boundaries.

    Parameters
    ----------
    spark : SparkSession
    level : int
        Admin level 0-5 (0=countries, 1=states/provinces, etc.)
    country : str, optional
        ISO 3166-1 alpha-3 country code to filter (e.g., 'USA').
    s3_base : str
        Base S3 path for staged GADM data.

    Returns
    -------
    DataFrame
        Spark DataFrame with geometry and GADM attributes.
    """
    path = f"{s3_base}/admin{level}/data.parquet"

    try:
        df = load_polygons(spark, path)
    except Exception:
        # Fallback: load via GADM provider
        return _load_gadm_via_provider(spark, level, country)

    if country and "iso3" in df.columns:
        df = df.filter(df.iso3 == country.upper())

    return df


def load_rdh_boundaries(
    spark: Any,
    state: str,
    plan_type: str = "enacted",
    s3_base: str = "s3a://boundaries/rdh",
) -> Any:
    """Load Redistricting Data Hub plan boundaries.

    Parameters
    ----------
    spark : SparkSession
    state : str
        2-letter state abbreviation.
    plan_type : str
        'enacted', 'proposed', 'alternative'.
    s3_base : str
        Base S3 path for RDH data.

    Returns
    -------
    DataFrame
        Spark DataFrame with redistricting plan district geometries.
    """
    path = f"{s3_base}/{state.lower()}/{plan_type}/data.parquet"
    return load_polygons(spark, path)


def stage_census_boundaries(
    spark: Any,
    boundary_type: str,
    year: int = 2020,
    s3_base: str = "s3a://boundaries/tiger",
) -> str:
    """Stage Census TIGER boundaries to S3 as GeoParquet for fast loading.

    Fetches boundaries from Census API via siege_utilities CensusTIGERProvider,
    converts geometry to WKT, writes as Parquet to S3.

    Parameters
    ----------
    spark : SparkSession
    boundary_type : str
        Census boundary type.
    year : int
        Census vintage year.
    s3_base : str
        Base S3 path for output.

    Returns
    -------
    str
        S3 path where boundaries were written.
    """
    from siege_utilities.geo.boundary_providers import CensusTIGERProvider

    s3_path = f"{s3_base}/{boundary_type}/{year}/data.parquet"

    provider = CensusTIGERProvider()
    gdf = provider.get_boundary(boundary_type, year=year)

    if gdf is None or len(gdf) == 0:
        logger.warning("No boundaries returned for %s/%s", boundary_type, year)
        return s3_path

    import pandas as pd

    pdf = pd.DataFrame(gdf.drop(columns="geometry"))
    pdf["geometry"] = gdf.geometry.apply(lambda g: g.wkt if g is not None else None)

    spark.createDataFrame(pdf).write.mode("overwrite").parquet(s3_path)
    logger.info("Staged %d %s boundaries to %s", len(gdf), boundary_type, s3_path)
    return s3_path


def _load_gadm_via_provider(spark, level, country):
    """Fallback: load GADM via siege_utilities provider."""
    from siege_utilities.geo.boundary_providers import GADMProvider
    import pandas as pd

    provider = GADMProvider()
    gdf = provider.get_boundary(str(level), country=country)

    if gdf is None or len(gdf) == 0:
        raise ValueError(f"No GADM boundaries for level={level}, country={country}")

    pdf = pd.DataFrame(gdf.drop(columns="geometry"))
    pdf["geometry"] = gdf.geometry.apply(lambda g: g.wkt if g is not None else None)
    return spark.createDataFrame(pdf)

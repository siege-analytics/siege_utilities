"""Boundary data source convenience functions (engine-agnostic).

Thin wrappers that know about specific data sources — Census TIGER, GADM,
RDH redistricting plans. These call ``engine.load_polygons()`` with the
correct paths and parameters.

Works with ANY DataFrameEngine (Pandas, DuckDB, Spark, PostGIS).
For custom boundary sources, call ``engine.load_polygons()`` directly.

Usage::

    from siege_utilities.engines.dataframe_engine import get_engine, Engine
    from siege_utilities.geo.boundary_sources import load_census_boundaries

    engine = get_engine(Engine.SPARK, enable_sedona=True)

    # Load congressional districts via the engine
    districts = load_census_boundaries(engine, "cd", year=2020)

    # Assign addresses to districts
    enriched = engine.assign_boundaries(addresses, districts)
"""

from __future__ import annotations

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)

CENSUS_BOUNDARY_TYPES = {
    "state", "county", "tract", "blockgroup", "block", "place",
    "zcta", "cd", "sldu", "sldl", "vtd", "cbsa",
}


def load_census_boundaries(
    engine: Any,
    boundary_type: str,
    year: int = 2020,
    state_fips: Optional[str] = None,
    s3_base: str = "s3a://boundaries/tiger",
) -> Any:
    """Load Census TIGER boundaries via any DataFrameEngine.

    Parameters
    ----------
    engine : DataFrameEngine
        Any engine instance (Pandas, DuckDB, Spark, PostGIS).
    boundary_type : str
        One of: state, county, tract, blockgroup, block, place, zcta,
        cd, sldu, sldl, vtd, cbsa.
    year : int
        Census vintage year (default 2020).
    state_fips : str, optional
        2-digit state FIPS to filter.
    s3_base : str
        Base path for staged GeoParquet.

    Returns
    -------
    Engine-native DataFrame with geometry column.
    """
    if boundary_type not in CENSUS_BOUNDARY_TYPES:
        raise ValueError(
            f"Unknown Census boundary type: {boundary_type!r}. "
            f"Valid: {sorted(CENSUS_BOUNDARY_TYPES)}"
        )

    path = f"{s3_base}/{boundary_type}/{year}/data.parquet"

    try:
        df = engine.load_polygons(path)
    except Exception as e:
        raise FileNotFoundError(
            f"Census boundaries not staged at {path}. "
            f"Run stage_census_boundaries() first."
        ) from e

    # Filter by state if the engine supports it
    if state_fips:
        df = engine.filter(df, df["state_fips"] == state_fips) if hasattr(df, "__getitem__") else df

    return df


def load_gadm_boundaries(
    engine: Any,
    level: int = 0,
    country: Optional[str] = None,
    s3_base: str = "s3a://boundaries/gadm",
) -> Any:
    """Load GADM (Global Administrative Areas) boundaries via any engine.

    Parameters
    ----------
    engine : DataFrameEngine
    level : int
        Admin level 0-5 (0=countries, 1=states/provinces, etc.)
    country : str, optional
        ISO 3166-1 alpha-3 country code to filter.
    s3_base : str
        Base path for staged GADM data.
    """
    path = f"{s3_base}/admin{level}/data.parquet"

    try:
        df = engine.load_polygons(path)
    except Exception:
        # Fallback: load via GADM provider + engine conversion
        return _load_gadm_via_provider(engine, level, country)

    if country and hasattr(df, "__getitem__"):
        df = engine.filter(df, df["iso3"] == country.upper())

    return df


def load_rdh_boundaries(
    engine: Any,
    state: str,
    plan_type: str = "enacted",
    s3_base: str = "s3a://boundaries/rdh",
) -> Any:
    """Load Redistricting Data Hub plan boundaries via any engine.

    Parameters
    ----------
    engine : DataFrameEngine
    state : str
        2-letter state abbreviation.
    plan_type : str
        'enacted', 'proposed', 'alternative'.
    """
    path = f"{s3_base}/{state.lower()}/{plan_type}/data.parquet"
    return engine.load_polygons(path)


def stage_census_boundaries(
    engine: Any,
    boundary_type: str,
    year: int = 2020,
    s3_base: str = "s3a://boundaries/tiger",
) -> str:
    """Stage Census TIGER boundaries for fast loading.

    Fetches from Census API via CensusTIGERProvider, converts geometry
    to the engine's format, writes to the staging path.

    Parameters
    ----------
    engine : DataFrameEngine
    boundary_type : str
    year : int
    s3_base : str

    Returns
    -------
    str : path where boundaries were written.
    """
    from siege_utilities.geo.providers.boundary_providers import CensusTIGERProvider

    s3_path = f"{s3_base}/{boundary_type}/{year}/data.parquet"

    provider = CensusTIGERProvider()
    gdf = provider.get_boundary(boundary_type, year=year)

    if gdf is None or len(gdf) == 0:
        logger.warning("No boundaries returned for %s/%s", boundary_type, year)
        return s3_path

    # Convert geometry to WKT for universal engine compatibility
    import pandas as pd

    pdf = pd.DataFrame(gdf.drop(columns="geometry"))
    pdf["geometry"] = gdf.geometry.apply(lambda g: g.wkt if g is not None else None)

    # Write via engine if it supports parquet write, else via pandas
    if hasattr(engine, "_session"):
        # Spark engine — write via Spark for S3 support
        sdf = engine._session.createDataFrame(pdf)
        sdf.write.mode("overwrite").parquet(s3_path)
    else:
        pdf.to_parquet(s3_path.replace("s3a://", "/tmp/staged_"))
        logger.warning("Non-Spark engine: wrote to local path instead of S3")

    logger.info("Staged %d %s boundaries to %s", len(gdf), boundary_type, s3_path)
    return s3_path


def _load_gadm_via_provider(engine, level, country):
    """Fallback: load GADM via provider, convert to engine format."""
    from siege_utilities.geo.providers.boundary_providers import GADMProvider
    import pandas as pd

    provider = GADMProvider()
    gdf = provider.get_boundary(str(level), country=country)

    if gdf is None or len(gdf) == 0:
        raise ValueError(f"No GADM boundaries for level={level}, country={country}")

    pdf = pd.DataFrame(gdf.drop(columns="geometry"))
    pdf["geometry"] = gdf.geometry.apply(lambda g: g.wkt if g is not None else None)

    # Return as engine-native format
    if hasattr(engine, "_session"):
        return engine._session.createDataFrame(pdf)
    return pdf

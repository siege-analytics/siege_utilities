"""
Census API Client for fetching demographic data from the Census Bureau.

This module provides a client for fetching demographic data (population, income,
education, etc.) from the Census Bureau API. The data can be joined with
existing TIGER/Line geometries for spatial analysis.

Example usage:
    from siege_utilities.geo import CensusAPIClient, get_demographics

    # Convenience function
    df = get_demographics(state='California', geography='county', year=2020)

    # Direct client usage
    client = CensusAPIClient()
    df = client.fetch_data(
        variables='income',
        year=2020,
        dataset='acs5',
        geography='tract',
        state_fips='06',
        county_fips='037',
        include_moe=True
    )

Implementation is split across three focused modules under ``census/``:

- ``census.variable_registry`` — variable groups, descriptions, metadata
- ``census.dataset_selector`` — pure-logic geography/dataset validation
- ``census.api`` — HTTP transport, caching, retry, response processing

This file provides the backward-compatible ``CensusAPIClient`` facade.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Union, Any, TYPE_CHECKING

import pandas as pd

if TYPE_CHECKING:
    import geopandas as gpd

import requests  # noqa: F401 — tests mock this module attribute

from ..config import normalize_state_identifier

# Re-export constants and sub-components for backward compatibility
from .census.variable_registry import VARIABLE_GROUPS, VARIABLE_DESCRIPTIONS  # noqa: F401
from .census.dataset_selector import DatasetSelector
from .census.api import CensusAPI, CENSUS_API_CACHE_TIMEOUT

log = logging.getLogger(__name__)


# =============================================================================
# CUSTOM EXCEPTIONS
# =============================================================================

class CensusAPIError(Exception):
    """Base exception for Census API errors."""


class CensusAPIKeyError(CensusAPIError):
    """Error related to API key authentication."""


class CensusRateLimitError(CensusAPIError):
    """Rate limit exceeded error."""


class CensusVariableError(CensusAPIError):
    """Invalid or unavailable variable error."""


class CensusGeographyError(CensusAPIError):
    """Invalid geography specification error."""


# =============================================================================
# CENSUS API CLIENT (FACADE)
# =============================================================================

class CensusAPIClient:
    """
    Client for fetching demographic data from the Census Bureau API.

    This is a backward-compatible facade that delegates to:

    - ``CensusAPI`` for HTTP, caching, and retry logic
    - ``DatasetSelector`` for geography/dataset validation
    - ``VariableRegistry`` for variable resolution and metadata

    All existing method signatures are preserved.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        timeout: Optional[int] = None,
        cache_dir: Optional[Union[str, Path]] = None,
        cache_backend: str = 'parquet',
        cache_ttl: int = CENSUS_API_CACHE_TIMEOUT,
    ):
        self._api = CensusAPI(
            api_key=api_key,
            timeout=timeout,
            cache_dir=cache_dir,
            cache_backend=cache_backend,
            cache_ttl=cache_ttl,
        )

    # Expose frequently accessed attributes from the inner API object
    @property
    def api_key(self):
        return self._api.api_key

    @property
    def timeout(self):
        return self._api.timeout

    @property
    def base_url(self):
        return self._api.base_url

    @property
    def cache_dir(self):
        return self._api.cache_dir

    @property
    def cache_backend(self):
        return self._api.cache_backend

    @property
    def cache_ttl(self):
        return self._api.cache_ttl

    # ------------------------------------------------------------------
    # Delegated methods
    # ------------------------------------------------------------------

    def fetch_data(
        self,
        variables: Union[str, List[str]],
        year: int,
        dataset: str = 'acs5',
        geography: str = 'county',
        state_fips: Optional[str] = None,
        county_fips: Optional[str] = None,
        include_moe: bool = True,
    ) -> pd.DataFrame:
        """Fetch demographic data from the Census API."""
        # Resolve variables via registry
        var_list = self._resolve_variables(variables)

        if include_moe and dataset.startswith('acs'):
            var_list = self._add_moe_variables(var_list)

        # Validate geography
        geography = self._validate_geography(geography, state_fips, county_fips)

        if state_fips:
            state_fips = self._normalize_state(state_fips)

        # Check cache
        cache_key = self._generate_cache_key(var_list, year, dataset, geography, state_fips, county_fips)
        cached_df = self._get_from_cache(cache_key)
        if cached_df is not None:
            log.info(f"Returning cached data for {geography} ({len(cached_df)} rows)")
            return cached_df

        # Build URL and make request
        url = self._build_url(var_list, year, dataset, geography, state_fips, county_fips)
        df = self._make_request_with_retry(url)

        # Process response
        df = self._process_response(df, geography, state_fips, county_fips)

        # Cache result
        self._save_to_cache(cache_key, df)

        log.info(f"Fetched {len(df)} rows of {geography}-level data for year {year}")
        return df

    def get_variable_metadata(
        self, variable: str, year: int, dataset: str = 'acs5',
    ) -> Dict[str, Any]:
        """Get metadata for a Census variable."""
        return self._api.get_variable_metadata(variable, year, dataset)

    def list_available_variables(
        self, year: int, dataset: str = 'acs5', search: Optional[str] = None,
    ) -> pd.DataFrame:
        """List available variables for a dataset."""
        return self._api.list_available_variables(year, dataset, search)

    def clear_cache(self) -> None:
        """Clear all cached API responses."""
        self._api.clear_cache()

    # ------------------------------------------------------------------
    # Preserved private methods for any subclassers
    # ------------------------------------------------------------------

    def _resolve_variables(self, variables: Union[str, List[str]]) -> List[str]:
        return self._api._registry.resolve_variables(variables)

    def _add_moe_variables(self, variables: List[str]) -> List[str]:
        return self._api._registry.add_moe_variables(variables)

    def _validate_geography(self, geography: str, state_fips: Optional[str],
                            county_fips: Optional[str]) -> str:
        try:
            return DatasetSelector.validate_geography(geography, state_fips, county_fips)
        except ValueError as e:
            raise CensusGeographyError(str(e)) from e

    def _normalize_state(self, state_input: str) -> str:
        try:
            return DatasetSelector.normalize_state(state_input)
        except ValueError as e:
            raise CensusGeographyError(str(e)) from e

    def _get_dataset_path(self, year: int, dataset: str) -> str:
        try:
            return DatasetSelector.get_dataset_path(year, dataset)
        except ValueError as e:
            raise CensusVariableError(str(e)) from e

    def _build_geography_clause(self, geography: str, state_fips: Optional[str],
                                county_fips: Optional[str]) -> str:
        return DatasetSelector.build_geography_clause(geography, state_fips, county_fips)

    def _build_url(self, variables: List[str], year: int, dataset: str,
                   geography: str, state_fips: Optional[str],
                   county_fips: Optional[str]) -> str:
        return self._api._build_url(variables, year, dataset, geography, state_fips, county_fips)

    @staticmethod
    def _construct_geoid(df: 'pd.DataFrame', geography: str) -> 'pd.DataFrame':
        return CensusAPI._construct_geoid(df, geography)

    @staticmethod
    def _convert_numeric_columns(df: 'pd.DataFrame') -> 'pd.DataFrame':
        return CensusAPI._convert_numeric_columns(df)

    def _generate_cache_key(self, variables: List[str], year: int, dataset: str,
                            geography: str, state_fips: Optional[str],
                            county_fips: Optional[str]) -> str:
        return self._api._generate_cache_key(variables, year, dataset, geography, state_fips, county_fips)

    def _get_from_cache(self, cache_key: str) -> Optional[pd.DataFrame]:
        if self._api.cache_backend == 'django':
            return self._api._django_cache_get(cache_key)
        return self._api._parquet_cache_get(cache_key)

    def _save_to_cache(self, cache_key: str, df: pd.DataFrame) -> None:
        if self._api.cache_backend == 'django':
            return self._api._django_cache_set(cache_key, df)
        return self._api._parquet_cache_set(cache_key, df)

    def _django_cache_get(self, cache_key: str) -> Optional[pd.DataFrame]:
        return self._api._django_cache_get(cache_key)

    def _django_cache_set(self, cache_key: str, df: pd.DataFrame) -> None:
        return self._api._django_cache_set(cache_key, df)

    def _parquet_cache_get(self, cache_key: str) -> Optional[pd.DataFrame]:
        return self._api._parquet_cache_get(cache_key)

    def _parquet_cache_set(self, cache_key: str, df: pd.DataFrame) -> None:
        return self._api._parquet_cache_set(cache_key, df)

    def _make_request_with_retry(self, url: str) -> pd.DataFrame:
        return self._api._make_request_with_retry(url)

    def _process_response(self, df: pd.DataFrame, geography: str,
                          state_fips: Optional[str],
                          county_fips: Optional[str]) -> pd.DataFrame:
        return self._api._process_response(df, geography, state_fips, county_fips)

    def _resolve_api_key(self, explicit_key: Optional[str]) -> Optional[str]:
        return CensusAPI._resolve_api_key(explicit_key)


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def get_demographics(
    state: str,
    geography: str = 'county',
    year: Optional[int] = None,
    variables: str = 'demographics_basic',
    include_moe: bool = True,
    dataset: str = 'acs5',
) -> pd.DataFrame:
    """
    Convenience function to get demographic data.

    Args:
        state: State name, abbreviation, or FIPS code
        geography: Geographic level ('county', 'tract', 'block_group')
        year: Census year (defaults to most recent available)
        variables: Variable group name or list of variables
        include_moe: Include margin of error columns
        dataset: Census dataset ('acs5', 'acs1', 'dec')

    Returns:
        DataFrame with demographic data
    """
    if year is None:
        year = datetime.now().year - 1

    state_fips = normalize_state_identifier(state)

    client = CensusAPIClient()
    return client.fetch_data(
        variables=variables,
        year=year,
        dataset=dataset,
        geography=geography,
        state_fips=state_fips,
        include_moe=include_moe,
    )


def get_population(
    state: str,
    geography: str = 'tract',
    year: Optional[int] = None,
    dataset: str = 'acs5',
) -> pd.DataFrame:
    """Convenience function to get population data."""
    if year is None:
        year = datetime.now().year - 1

    state_fips = normalize_state_identifier(state)

    client = CensusAPIClient()
    return client.fetch_data(
        variables='total_population',
        year=year,
        dataset=dataset,
        geography=geography,
        state_fips=state_fips,
        include_moe=True,
    )


def get_income_data(
    state: str,
    geography: str = 'tract',
    year: Optional[int] = None,
    include_moe: bool = True,
    dataset: str = 'acs5',
) -> pd.DataFrame:
    """Convenience function to get income data."""
    if year is None:
        year = datetime.now().year - 1

    state_fips = normalize_state_identifier(state)

    client = CensusAPIClient()
    return client.fetch_data(
        variables='income',
        year=year,
        dataset=dataset,
        geography=geography,
        state_fips=state_fips,
        include_moe=include_moe,
    )


def get_education_data(
    state: str,
    geography: str = 'tract',
    year: Optional[int] = None,
    include_moe: bool = True,
    dataset: str = 'acs5',
) -> pd.DataFrame:
    """Convenience function to get educational attainment data."""
    if year is None:
        year = datetime.now().year - 1

    state_fips = normalize_state_identifier(state)

    client = CensusAPIClient()
    return client.fetch_data(
        variables='education',
        year=year,
        dataset=dataset,
        geography=geography,
        state_fips=state_fips,
        include_moe=include_moe,
    )


def get_housing_data(
    state: str,
    geography: str = 'tract',
    year: Optional[int] = None,
    include_moe: bool = True,
    dataset: str = 'acs5',
) -> pd.DataFrame:
    """Convenience function to get housing data."""
    if year is None:
        year = datetime.now().year - 1

    state_fips = normalize_state_identifier(state)

    client = CensusAPIClient()
    return client.fetch_data(
        variables='housing',
        year=year,
        dataset=dataset,
        geography=geography,
        state_fips=state_fips,
        include_moe=include_moe,
    )


# Module-level client for convenience
_default_client: Optional[CensusAPIClient] = None


def get_census_api_client() -> CensusAPIClient:
    """Get or create the default Census API client."""
    global _default_client
    if _default_client is None:
        _default_client = CensusAPIClient()
    return _default_client


# =============================================================================
# GEOMETRY + DEMOGRAPHICS JOINING FUNCTIONS
# =============================================================================

def get_census_data_with_geometry(
    year: int,
    geography: str,
    variables: Union[str, List[str]],
    state: Optional[str] = None,
    county_fips: Optional[str] = None,
    dataset: str = 'acs5',
    include_moe: bool = True,
) -> 'gpd.GeoDataFrame':
    """
    Fetch Census boundaries AND demographic data, returning a merged GeoDataFrame.

    This is the primary function for getting choropleth-ready data. It:
    1. Fetches TIGER/Line geometry for the specified geography
    2. Fetches demographic variables from the Census API
    3. Joins them on GEOID
    """
    import geopandas as gpd
    from .spatial_data import get_census_boundaries
    from .geoid_utils import find_geoid_column

    state_fips = None
    if state:
        state_fips = normalize_state_identifier(state)

    if geography in ['tract', 'block_group'] and not state_fips:
        raise CensusGeographyError(
            f"State is required for {geography}-level data"
        )

    log.info(f"Fetching {geography}-level data with geometry for year {year}")

    # 1. Fetch geometry
    log.info("Fetching TIGER/Line boundaries...")
    shapes_gdf = get_census_boundaries(
        year=year,
        geographic_level=geography,
        state_fips=state_fips,
    )

    if shapes_gdf is None or shapes_gdf.empty:
        raise CensusAPIError(f"Failed to fetch boundaries for {geography}")

    # Filter geometry to county scope
    if county_fips and geography in ['tract', 'block_group']:
        pre_filter_count = len(shapes_gdf)
        county_col = None
        for col in ['COUNTYFP', 'COUNTYFP20', 'COUNTYFP10', 'countyfp']:
            if col in shapes_gdf.columns:
                county_col = col
                break

        if county_col:
            shapes_gdf = shapes_gdf[shapes_gdf[county_col] == county_fips].copy()
        else:
            geoid_col = find_geoid_column(shapes_gdf) or 'GEOID'
            if geoid_col in shapes_gdf.columns:
                prefix = state_fips + county_fips
                shapes_gdf = shapes_gdf[
                    shapes_gdf[geoid_col].astype(str).str.startswith(prefix)
                ].copy()

        log.info(
            f"Filtered geometry by county {county_fips}: "
            f"{pre_filter_count} → {len(shapes_gdf)} features"
        )

    log.info(f"Retrieved {len(shapes_gdf)} boundary features")

    # 2. Fetch demographics
    log.info("Fetching demographic data...")
    client = CensusAPIClient()
    demographics_df = client.fetch_data(
        variables=variables,
        year=year,
        dataset=dataset,
        geography=geography,
        state_fips=state_fips,
        county_fips=county_fips,
        include_moe=include_moe,
    )

    if demographics_df.empty:
        log.warning("No demographic data returned, returning geometry only")
        return shapes_gdf

    log.info(f"Retrieved {len(demographics_df)} demographic records")

    # 3. Find and normalize GEOID columns for joining
    shapes_geoid_col = find_geoid_column(shapes_gdf)
    if shapes_geoid_col is None:
        for col in ['GEOID', 'GEOID20', 'GEOID10', 'geoid', 'AFFGEOID']:
            if col in shapes_gdf.columns:
                shapes_geoid_col = col
                break

    if shapes_geoid_col is None:
        raise CensusAPIError(
            f"Cannot find GEOID column in geometry data. "
            f"Available columns: {list(shapes_gdf.columns)[:10]}"
        )

    if 'GEOID' not in demographics_df.columns:
        raise CensusAPIError("Demographics data missing GEOID column")

    def extract_numeric_geoid(geoid_val):
        if pd.isna(geoid_val):
            return None
        geoid_str = str(geoid_val)
        if 'US' in geoid_str:
            return geoid_str.split('US')[-1]
        return geoid_str

    shapes_gdf = shapes_gdf.copy()
    shapes_gdf['_join_geoid'] = shapes_gdf[shapes_geoid_col].apply(extract_numeric_geoid)

    demographics_df = demographics_df.copy()
    demographics_df['_join_geoid'] = demographics_df['GEOID'].astype(str)

    # 4. Perform the join
    demo_cols_to_drop = []
    for col in demographics_df.columns:
        if col in shapes_gdf.columns and col not in ['_join_geoid', 'GEOID']:
            demo_cols_to_drop.append(col)

    if demo_cols_to_drop:
        demographics_df = demographics_df.drop(columns=demo_cols_to_drop)

    merged_gdf = shapes_gdf.merge(
        demographics_df,
        on='_join_geoid',
        how='left',
        suffixes=('', '_demo'),
    )

    merged_gdf = merged_gdf.drop(columns=['_join_geoid'])

    if not isinstance(merged_gdf, gpd.GeoDataFrame):
        merged_gdf = gpd.GeoDataFrame(merged_gdf, geometry='geometry')

    matched = merged_gdf[demographics_df.columns[0]].notna().sum()
    total = len(merged_gdf)
    match_rate = (matched / total * 100) if total > 0 else 0
    log.info(f"Joined {matched}/{total} records ({match_rate:.1f}% match rate)")

    if match_rate < 90:
        log.warning(
            f"Low match rate ({match_rate:.1f}%). "
            "Check GEOID formats or year alignment between geometry and data."
        )

    return merged_gdf


def join_demographics_to_shapes(
    shapes_gdf: 'gpd.GeoDataFrame',
    demographics_df: pd.DataFrame,
    shapes_geoid_col: Optional[str] = None,
    demographics_geoid_col: str = 'GEOID',
    how: str = 'left',
) -> 'gpd.GeoDataFrame':
    """
    Join demographic data to existing shapes GeoDataFrame.

    Use this when you already have shapes loaded and want to add demographic data.
    """
    import geopandas as gpd
    from .geoid_utils import find_geoid_column

    if shapes_geoid_col is None:
        shapes_geoid_col = find_geoid_column(shapes_gdf)
        if shapes_geoid_col is None:
            raise ValueError(
                "Cannot find GEOID column in shapes. "
                f"Available columns: {list(shapes_gdf.columns)[:10]}"
            )

    def extract_numeric_geoid(geoid_val):
        if pd.isna(geoid_val):
            return None
        geoid_str = str(geoid_val)
        if 'US' in geoid_str:
            return geoid_str.split('US')[-1]
        return geoid_str

    shapes_gdf = shapes_gdf.copy()
    shapes_gdf['_join_geoid'] = shapes_gdf[shapes_geoid_col].apply(extract_numeric_geoid)

    demographics_df = demographics_df.copy()
    demographics_df['_join_geoid'] = demographics_df[demographics_geoid_col].astype(str)

    demo_cols_to_drop = [
        col for col in demographics_df.columns
        if col in shapes_gdf.columns and col != '_join_geoid'
    ]
    if demo_cols_to_drop:
        demographics_df = demographics_df.drop(columns=demo_cols_to_drop)

    merged = shapes_gdf.merge(
        demographics_df,
        on='_join_geoid',
        how=how,
    )

    merged = merged.drop(columns=['_join_geoid'])

    if not isinstance(merged, gpd.GeoDataFrame):
        merged = gpd.GeoDataFrame(merged, geometry='geometry')

    return merged

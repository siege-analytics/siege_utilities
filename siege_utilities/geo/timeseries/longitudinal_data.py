"""
Longitudinal data fetching for Census time-series analysis.

This module provides functions to fetch Census data across multiple years
and normalize them to a consistent boundary vintage for time-series analysis.

It integrates with:
- CensusAPIClient for fetching demographic data
- Crosswalk module for boundary normalization

Example usage:
    from siege_utilities.geo.timeseries import get_longitudinal_data

    # Fetch median income for California tracts 2010-2020
    df = get_longitudinal_data(
        variables='B19013_001E',
        years=[2010, 2015, 2020],
        geography='tract',
        state='California',
        target_year=2020
    )

    # Result has columns: GEOID, B19013_001E_2010, B19013_001E_2015, B19013_001E_2020
"""

import logging
from typing import Dict, List, Optional, Union, TYPE_CHECKING

import pandas as pd

if TYPE_CHECKING:
    import geopandas as gpd
import numpy as np

log = logging.getLogger(__name__)


# =============================================================================
# CONFIGURATION — imported from canonical source in config.census_constants
# =============================================================================

from ...config.census_constants import (
    ACS5_AVAILABLE_YEARS,
    DECENNIAL_YEARS,
    BOUNDARY_CHANGE_YEARS,
)


# =============================================================================
# LONGITUDINAL DATA FUNCTIONS
# =============================================================================

def get_longitudinal_data(
    variables: Union[str, List[str]],
    years: List[int],
    geography: str = 'tract',
    state: Optional[str] = None,
    county_fips: Optional[str] = None,
    target_year: int = 2020,
    normalize_boundaries: bool = True,
    include_moe: bool = False,
    include_geometry: bool = False,
    dataset: str = 'acs5',
    strict_years: bool = True,
) -> pd.DataFrame:
    """
    Fetch Census data for multiple years and return in wide format.

    This function:
    1. Fetches data for each requested year
    2. Optionally normalizes all data to a consistent boundary year
    3. Merges into a wide-format DataFrame with year-suffixed columns

    Args:
        variables: Census variable code(s) or predefined group name
            (e.g., 'B19013_001E', ['B19013_001E', 'B01001_001E'], or 'income')
        years: List of years to fetch data for
        geography: Geographic level ('state', 'county', 'tract', 'block_group')
        state: State identifier (name, abbreviation, or FIPS code)
        county_fips: County FIPS code (3 digits) for filtering
        target_year: Year to normalize boundaries to (default: 2020)
        normalize_boundaries: If True, apply crosswalks to normalize all years
            to target_year boundaries. Required for accurate comparisons.
        include_moe: Include margin of error columns
        include_geometry: If True, include geometry from target year
        dataset: Census dataset ('acs5', 'acs1')
        strict_years: If True (default), raise ValueError when any requested year
            is unavailable or fails to fetch. If False, log warnings and continue
            with available years.

    Returns:
        Wide-format DataFrame with columns:
        - GEOID: Geography identifier (in target_year vintage if normalized)
        - NAME: Geography name (from most recent year)
        - {variable}_{year}: Variable value for each year

    Example:
        # Get income data for LA County tracts 2015-2020
        df = get_longitudinal_data(
            variables='B19013_001E',
            years=[2015, 2017, 2020],
            geography='tract',
            state='CA',
            county_fips='037'
        )

        # Columns: GEOID, NAME, B19013_001E_2015, B19013_001E_2017, B19013_001E_2020
    """
    # Import here to avoid circular imports
    from ..census_api_client import CensusAPIClient, VARIABLE_GROUPS
    from ...config import normalize_state_identifier

    # Validate inputs
    if not years:
        raise ValueError("Must provide at least one year")

    # Validate requested years against dataset availability
    valid_years = validate_longitudinal_years(years, dataset)
    unavailable_years = set(years) - set(valid_years)
    if unavailable_years and strict_years:
        raise ValueError(
            f"Years {sorted(unavailable_years)} are not available for dataset '{dataset}'. "
            f"Available: {sorted(get_available_years(dataset))}. "
            f"Pass strict_years=False to skip unavailable years."
        )

    years = sorted(valid_years)

    # Resolve variables
    if isinstance(variables, str):
        if variables in VARIABLE_GROUPS:
            var_list = VARIABLE_GROUPS[variables].copy()
        else:
            var_list = [variables]
    else:
        var_list = list(variables)

    # Normalize state
    state_fips = None
    if state:
        state_fips = normalize_state_identifier(state)

    log.info(
        f"Fetching longitudinal data: {len(var_list)} variables, "
        f"{len(years)} years ({min(years)}-{max(years)}), {geography} level"
    )

    # Fetch data for each year
    client = CensusAPIClient()
    yearly_data = {}

    for year in years:
        log.info(f"Fetching data for {year}...")
        try:
            df = client.fetch_data(
                variables=var_list,
                year=year,
                dataset=dataset,
                geography=geography,
                state_fips=state_fips,
                county_fips=county_fips,
                include_moe=include_moe
            )

            if not df.empty:
                yearly_data[year] = df
                log.info(f"  Retrieved {len(df)} rows for {year}")
            else:
                log.warning(f"  No data returned for {year}")

        except Exception as e:
            if strict_years:
                raise ValueError(
                    f"Failed to fetch data for year {year}: {e}. "
                    f"Pass strict_years=False to skip failed years."
                ) from e
            log.warning(f"  Failed to fetch data for {year}: {e}")
            continue

    if not yearly_data:
        raise ValueError("No data could be fetched for any year")

    # Normalize boundaries if requested
    if normalize_boundaries:
        yearly_data = _normalize_boundaries_multi_year(
            yearly_data=yearly_data,
            target_year=target_year,
            geography_level=geography,
            state_fips=state_fips
        )

    # Merge into wide format
    result = _merge_to_wide_format(
        yearly_data=yearly_data,
        var_list=var_list,
        include_moe=include_moe
    )

    # Add geometry if requested
    if include_geometry:
        result = _add_geometry(
            df=result,
            geography=geography,
            state_fips=state_fips,
            year=target_year,
            county_fips=county_fips,
        )

    log.info(f"Longitudinal data complete: {len(result)} rows, {len(result.columns)} columns")
    return result


def _normalize_boundaries_multi_year(
    yearly_data: Dict[int, pd.DataFrame],
    target_year: int,
    geography_level: str,
    state_fips: Optional[str]
) -> Dict[int, pd.DataFrame]:
    """
    Normalize all years' data to target year boundaries.

    Args:
        yearly_data: Dictionary mapping year to DataFrame
        target_year: Year to normalize to
        geography_level: Geographic level
        state_fips: State FIPS code

    Returns:
        Dictionary with normalized DataFrames
    """
    from ..crosswalk.crosswalk_processor import apply_crosswalk

    normalized = {}

    for year, df in yearly_data.items():
        if year == target_year:
            # No transformation needed
            normalized[year] = df
            continue

        # Determine if crosswalk is needed
        # Boundaries change in decennial years
        source_boundary_year = _get_boundary_year(year)
        target_boundary_year = _get_boundary_year(target_year)

        if source_boundary_year == target_boundary_year:
            # Same boundary vintage, no transformation needed
            normalized[year] = df
            continue

        # Apply crosswalk
        log.info(
            f"  Normalizing {year} data from {source_boundary_year} to "
            f"{target_boundary_year} boundaries"
        )

        try:
            normalized_df = apply_crosswalk(
                df=df,
                source_year=source_boundary_year,
                target_year=target_boundary_year,
                geography_level=geography_level,
                state_fips=state_fips,
                geoid_column='GEOID'
            )
            normalized[year] = normalized_df
        except Exception as e:
            log.warning(
                f"  Could not normalize {year} data: {e}. Using original boundaries."
            )
            normalized[year] = df

    return normalized


def _get_boundary_year(data_year: int) -> int:
    """
    Determine which Census boundary vintage a data year uses.

    ACS and other surveys use the boundaries from the most recent decennial:
    - 2010-2019 data uses 2010 boundaries
    - 2020+ data uses 2020 boundaries

    Args:
        data_year: Year of the data

    Returns:
        Boundary vintage year (2010 or 2020)
    """
    if data_year >= 2020:
        return 2020
    elif data_year >= 2010:
        return 2010
    else:
        return 2000


def _merge_to_wide_format(
    yearly_data: Dict[int, pd.DataFrame],
    var_list: List[str],
    include_moe: bool
) -> pd.DataFrame:
    """
    Merge yearly DataFrames into wide format.

    Args:
        yearly_data: Dictionary mapping year to DataFrame
        var_list: List of variable codes
        include_moe: Whether MOE columns are included

    Returns:
        Wide-format DataFrame
    """
    if not yearly_data:
        return pd.DataFrame()

    # Start with the most recent year for base info
    years = sorted(yearly_data.keys())
    base_year = years[-1]
    result = yearly_data[base_year][['GEOID', 'NAME']].copy()

    # Add year-suffixed columns for each variable
    for year in years:
        df = yearly_data[year]

        for var in var_list:
            if var in df.columns:
                col_name = f"{var}_{year}"
                # Merge on GEOID
                result = result.merge(
                    df[['GEOID', var]].rename(columns={var: col_name}),
                    on='GEOID',
                    how='outer'
                )

            # Include MOE if present
            if include_moe:
                moe_var = var[:-1] + 'M' if var.endswith('E') else None
                if moe_var and moe_var in df.columns:
                    moe_col_name = f"{moe_var}_{year}"
                    result = result.merge(
                        df[['GEOID', moe_var]].rename(columns={moe_var: moe_col_name}),
                        on='GEOID',
                        how='outer'
                    )

    return result


def _add_geometry(
    df: pd.DataFrame,
    geography: str,
    state_fips: Optional[str],
    year: int,
    county_fips: Optional[str] = None,
) -> 'gpd.GeoDataFrame':
    """
    Add geometry to the DataFrame.

    Args:
        df: DataFrame with GEOID column
        geography: Geographic level
        state_fips: State FIPS code
        year: Year for geometry
        county_fips: Optional county FIPS code to scope geometry to match
            demographics scope (prevents state-wide geometry with county-filtered data)

    Returns:
        GeoDataFrame with geometry, preserving canonical GEOID from demographics
    """
    import geopandas as gpd
    from ..spatial_data import get_census_boundaries
    from ..geoid_utils import find_geoid_column

    log.info(f"Adding {year} geometry...")

    # Get boundaries
    boundaries = get_census_boundaries(
        year=year,
        geographic_level=geography,
        state_fips=state_fips
    )

    if boundaries is None or boundaries.empty:
        log.warning("Could not fetch geometry, returning DataFrame without geometry")
        return df

    # Filter boundaries by county if provided (TIGER files are per-state)
    if county_fips and geography in ['tract', 'block_group']:
        pre_filter_count = len(boundaries)
        county_col = None
        for col in ['COUNTYFP', 'COUNTYFP20', 'COUNTYFP10', 'countyfp']:
            if col in boundaries.columns:
                county_col = col
                break

        if county_col:
            boundaries = boundaries[boundaries[county_col] == county_fips].copy()
        else:
            geoid_col_temp = find_geoid_column(boundaries) or 'GEOID'
            if geoid_col_temp in boundaries.columns:
                prefix = state_fips + county_fips
                boundaries = boundaries[
                    boundaries[geoid_col_temp].astype(str).str.startswith(prefix)
                ].copy()

        log.info(
            f"Filtered geometry by county {county_fips}: "
            f"{pre_filter_count} → {len(boundaries)} features"
        )

    # Find GEOID column in boundaries
    boundary_geoid_col = find_geoid_column(boundaries)
    if boundary_geoid_col is None:
        for col in ['GEOID', 'GEOID20', 'GEOID10']:
            if col in boundaries.columns:
                boundary_geoid_col = col
                break

    if boundary_geoid_col is None:
        log.warning("Cannot find GEOID in boundaries, returning DataFrame without geometry")
        return df

    # Extract numeric GEOID if needed (TIGER format may include prefix)
    def extract_numeric_geoid(val):
        if pd.isna(val):
            return None
        s = str(val)
        if 'US' in s:
            return s.split('US')[-1]
        return s

    boundaries = boundaries.copy()
    boundaries['_join_geoid'] = boundaries[boundary_geoid_col].apply(extract_numeric_geoid)

    df = df.copy()
    df['_join_geoid'] = df['GEOID'].astype(str)

    # Merge — preserve canonical GEOID from demographics side by renaming
    # boundary GEOID to avoid collision, rather than dropping demographics GEOID
    if boundary_geoid_col == 'GEOID':
        boundaries = boundaries.rename(columns={'GEOID': 'GEOID_boundary'})

    merged = boundaries.merge(
        df,
        on='_join_geoid',
        how='right'
    )

    # Clean up join key and redundant boundary GEOID
    cols_to_drop = ['_join_geoid']
    if 'GEOID_boundary' in merged.columns:
        cols_to_drop.append('GEOID_boundary')
    merged = merged.drop(columns=cols_to_drop)

    if not isinstance(merged, gpd.GeoDataFrame):
        merged = gpd.GeoDataFrame(merged, geometry='geometry')

    return merged


def get_available_years(
    dataset: str = 'acs5',
    variable: Optional[str] = None
) -> List[int]:
    """
    Get list of available years for a Census dataset.

    Args:
        dataset: Census dataset ('acs5', 'acs1', 'dec')
        variable: Optional variable to check availability for

    Returns:
        List of available years
    """
    if dataset == 'acs5':
        return ACS5_AVAILABLE_YEARS.copy()
    elif dataset == 'acs1':
        return list(range(2005, 2024))  # ACS 1-year starts in 2005
    elif dataset == 'dec':
        return DECENNIAL_YEARS.copy()
    else:
        return []


def validate_longitudinal_years(
    years: List[int],
    dataset: str = 'acs5'
) -> List[int]:
    """
    Validate and filter years for longitudinal analysis.

    Args:
        years: Requested years
        dataset: Census dataset

    Returns:
        List of valid years

    Raises:
        ValueError: If no valid years
    """
    available = set(get_available_years(dataset))
    valid = [y for y in years if y in available]

    if not valid:
        raise ValueError(
            f"No valid years in {years}. "
            f"Available years for {dataset}: {sorted(available)}"
        )

    invalid = set(years) - set(valid)
    if invalid:
        log.warning(f"Skipping unavailable years: {sorted(invalid)}")

    return sorted(valid)

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
"""

import logging
import os
import hashlib
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Union, Any, TYPE_CHECKING

import pandas as pd

if TYPE_CHECKING:
    import geopandas as gpd
import requests

from ..config import (
    CENSUS_API_BASE_URL,
    normalize_state_identifier,
    get_service_timeout,
    CENSUS_RETRY_ATTEMPTS,
)
from ..config.user_config import get_user_config

log = logging.getLogger(__name__)


# =============================================================================
# CENSUS API CONSTANTS
# =============================================================================

# Cache timeout for API responses (24 hours, matches geometry cache)
CENSUS_API_CACHE_TIMEOUT = 86400  # seconds

# Default API timeout
CENSUS_API_DEFAULT_TIMEOUT = 30  # seconds

# Rate limit handling
CENSUS_API_RATE_LIMIT_RETRY_DELAY = 60  # seconds to wait after rate limit hit


# =============================================================================
# PREDEFINED VARIABLE GROUPS
# =============================================================================

VARIABLE_GROUPS = {
    # Basic population count
    'total_population': ['B01001_001E'],

    # Basic demographics (age, sex, median age)
    'demographics_basic': [
        'B01001_001E',  # Total population
        'B01001_002E',  # Male
        'B01001_026E',  # Female
        'B01002_001E',  # Median age
    ],

    # Race and ethnicity
    'race_ethnicity': [
        'B02001_001E',  # Total
        'B02001_002E',  # White alone
        'B02001_003E',  # Black/African American alone
        'B02001_004E',  # American Indian/Alaska Native alone
        'B02001_005E',  # Asian alone
        'B02001_006E',  # Native Hawaiian/Pacific Islander alone
        'B02001_007E',  # Some other race alone
        'B02001_008E',  # Two or more races
        'B03001_003E',  # Hispanic or Latino
    ],

    # Income data
    'income': [
        'B19013_001E',  # Median household income
        'B19301_001E',  # Per capita income
        'B19025_001E',  # Aggregate household income
    ],

    # Educational attainment (25+ population)
    'education': [
        'B15003_001E',  # Total population 25+
        'B15003_017E',  # High school graduate
        'B15003_018E',  # GED
        'B15003_021E',  # Associate's degree
        'B15003_022E',  # Bachelor's degree
        'B15003_023E',  # Master's degree
        'B15003_024E',  # Professional school degree
        'B15003_025E',  # Doctorate degree
    ],

    # Poverty status
    'poverty': [
        'B17001_001E',  # Population for poverty determination
        'B17001_002E',  # Below poverty level
    ],

    # Housing units and tenure
    'housing': [
        'B25001_001E',  # Total housing units
        'B25002_002E',  # Occupied housing units
        'B25002_003E',  # Vacant housing units
        'B25003_002E',  # Owner occupied
        'B25003_003E',  # Renter occupied
        'B25077_001E',  # Median home value
        'B25064_001E',  # Median gross rent
    ],

    # Decennial census population (for PL 94-171)
    'decennial_population': [
        'P1_001N',  # Total population
        'P1_003N',  # Population of one race
        'P1_004N',  # White alone
        'P1_005N',  # Black or African American alone
        'P1_006N',  # American Indian and Alaska Native alone
        'P1_007N',  # Asian alone
        'P1_008N',  # Native Hawaiian and Other Pacific Islander alone
    ],

    # ==========================================================================
    # PL 94-171 REDISTRICTING DATA (Complete Variable Sets)
    # ==========================================================================

    # P1: Race (Total Population)
    'pl_p1_race': [
        'P1_001N',  # Total population
        'P1_002N',  # Population of one race
        'P1_003N',  # White alone
        'P1_004N',  # Black or African American alone
        'P1_005N',  # American Indian and Alaska Native alone
        'P1_006N',  # Asian alone
        'P1_007N',  # Native Hawaiian and Other Pacific Islander alone
        'P1_008N',  # Some Other Race alone
        'P1_009N',  # Population of two or more races
        'P1_010N',  # Two races including Some Other Race
        'P1_011N',  # Two races excluding Some Other Race, and three or more races
    ],

    # P2: Hispanic or Latino by Race
    'pl_p2_hispanic': [
        'P2_001N',  # Total population
        'P2_002N',  # Hispanic or Latino
        'P2_003N',  # Not Hispanic or Latino
        'P2_004N',  # Not Hispanic: Population of one race
        'P2_005N',  # Not Hispanic: White alone
        'P2_006N',  # Not Hispanic: Black or African American alone
        'P2_007N',  # Not Hispanic: American Indian and Alaska Native alone
        'P2_008N',  # Not Hispanic: Asian alone
        'P2_009N',  # Not Hispanic: Native Hawaiian and Other Pacific Islander alone
        'P2_010N',  # Not Hispanic: Some Other Race alone
        'P2_011N',  # Not Hispanic: Population of two or more races
    ],

    # P3: Race for Population 18 Years and Over
    'pl_p3_race_18plus': [
        'P3_001N',  # Total population 18 years and over
        'P3_002N',  # Population of one race
        'P3_003N',  # White alone
        'P3_004N',  # Black or African American alone
        'P3_005N',  # American Indian and Alaska Native alone
        'P3_006N',  # Asian alone
        'P3_007N',  # Native Hawaiian and Other Pacific Islander alone
        'P3_008N',  # Some Other Race alone
        'P3_009N',  # Population of two or more races
    ],

    # P4: Hispanic or Latino by Race for Population 18+
    'pl_p4_hispanic_18plus': [
        'P4_001N',  # Total population 18 years and over
        'P4_002N',  # Hispanic or Latino
        'P4_003N',  # Not Hispanic or Latino
        'P4_004N',  # Not Hispanic: Population of one race
        'P4_005N',  # Not Hispanic: White alone
        'P4_006N',  # Not Hispanic: Black or African American alone
        'P4_007N',  # Not Hispanic: American Indian and Alaska Native alone
        'P4_008N',  # Not Hispanic: Asian alone
        'P4_009N',  # Not Hispanic: Native Hawaiian and Other Pacific Islander alone
        'P4_010N',  # Not Hispanic: Some Other Race alone
        'P4_011N',  # Not Hispanic: Population of two or more races
    ],

    # P5: Group Quarters Population by Major Group Quarters Type
    'pl_p5_group_quarters': [
        'P5_001N',  # Total group quarters population
        'P5_002N',  # Institutionalized population
        'P5_003N',  # Correctional facilities for adults
        'P5_004N',  # Juvenile facilities
        'P5_005N',  # Nursing facilities/Skilled-nursing facilities
        'P5_006N',  # Other institutional facilities
        'P5_007N',  # Noninstitutionalized population
        'P5_008N',  # College/University student housing
        'P5_009N',  # Military quarters
        'P5_010N',  # Other noninstitutional facilities
    ],

    # H1: Housing Occupancy
    'pl_h1_housing': [
        'H1_001N',  # Total housing units
        'H1_002N',  # Occupied housing units
        'H1_003N',  # Vacant housing units
    ],

    # Combined: All PL 94-171 core redistricting variables
    'pl_redistricting_core': [
        # Population totals
        'P1_001N',  # Total population
        'P2_002N',  # Hispanic or Latino
        'P2_003N',  # Not Hispanic or Latino
        'P2_005N',  # Not Hispanic: White alone
        'P2_006N',  # Not Hispanic: Black or African American alone
        'P2_007N',  # Not Hispanic: American Indian and Alaska Native alone
        'P2_008N',  # Not Hispanic: Asian alone
        'P2_009N',  # Not Hispanic: Native Hawaiian and Other Pacific Islander alone
        'P2_010N',  # Not Hispanic: Some Other Race alone
        'P2_011N',  # Not Hispanic: Two or more races
        # Voting age population
        'P3_001N',  # Total population 18+
        'P4_002N',  # Hispanic or Latino 18+
        'P4_003N',  # Not Hispanic or Latino 18+
        'P4_005N',  # Not Hispanic: White alone 18+
        'P4_006N',  # Not Hispanic: Black alone 18+
        # Housing
        'H1_001N',  # Total housing units
        'H1_002N',  # Occupied
        'H1_003N',  # Vacant
    ],

    # Voting Age Population (VAP) - commonly used for redistricting
    'pl_voting_age': [
        'P3_001N',  # Total population 18+
        'P4_002N',  # Hispanic or Latino 18+
        'P4_003N',  # Not Hispanic or Latino 18+
        'P4_005N',  # Not Hispanic: White alone 18+
        'P4_006N',  # Not Hispanic: Black alone 18+
        'P4_007N',  # Not Hispanic: AIAN alone 18+
        'P4_008N',  # Not Hispanic: Asian alone 18+
        'P4_009N',  # Not Hispanic: NHPI alone 18+
        'P4_010N',  # Not Hispanic: Some Other Race alone 18+
        'P4_011N',  # Not Hispanic: Two or more races 18+
    ],
}

# Variable descriptions for metadata
VARIABLE_DESCRIPTIONS = {
    'B01001_001E': 'Total Population',
    'B01001_002E': 'Male Population',
    'B01001_026E': 'Female Population',
    'B01002_001E': 'Median Age',
    'B02001_001E': 'Total (Race)',
    'B02001_002E': 'White Alone',
    'B02001_003E': 'Black or African American Alone',
    'B02001_004E': 'American Indian and Alaska Native Alone',
    'B02001_005E': 'Asian Alone',
    'B02001_006E': 'Native Hawaiian and Pacific Islander Alone',
    'B02001_007E': 'Some Other Race Alone',
    'B02001_008E': 'Two or More Races',
    'B03001_003E': 'Hispanic or Latino',
    'B19013_001E': 'Median Household Income',
    'B19301_001E': 'Per Capita Income',
    'B19025_001E': 'Aggregate Household Income',
    'B15003_001E': 'Population 25 Years and Over',
    'B15003_017E': 'High School Graduate',
    'B15003_018E': 'GED or Alternative Credential',
    'B15003_021E': "Associate's Degree",
    'B15003_022E': "Bachelor's Degree",
    'B15003_023E': "Master's Degree",
    'B15003_024E': 'Professional School Degree',
    'B15003_025E': 'Doctorate Degree',
    'B17001_001E': 'Population for Poverty Determination',
    'B17001_002E': 'Below Poverty Level',
    'B25001_001E': 'Total Housing Units',
    'B25002_002E': 'Occupied Housing Units',
    'B25002_003E': 'Vacant Housing Units',
    'B25003_002E': 'Owner Occupied',
    'B25003_003E': 'Renter Occupied',
    'B25077_001E': 'Median Home Value',
    'B25064_001E': 'Median Gross Rent',
    # PL 94-171 P1: Race
    'P1_001N': 'Total Population',
    'P1_002N': 'Population of One Race',
    'P1_003N': 'White Alone',
    'P1_004N': 'Black or African American Alone',
    'P1_005N': 'American Indian and Alaska Native Alone',
    'P1_006N': 'Asian Alone',
    'P1_007N': 'Native Hawaiian and Other Pacific Islander Alone',
    'P1_008N': 'Some Other Race Alone',
    'P1_009N': 'Population of Two or More Races',
    'P1_010N': 'Two Races Including Some Other Race',
    'P1_011N': 'Two Races Excluding Some Other Race, Three+ Races',

    # PL 94-171 P2: Hispanic or Latino by Race
    'P2_001N': 'Total Population (Hispanic Origin)',
    'P2_002N': 'Hispanic or Latino',
    'P2_003N': 'Not Hispanic or Latino',
    'P2_004N': 'Not Hispanic: One Race',
    'P2_005N': 'Not Hispanic: White Alone',
    'P2_006N': 'Not Hispanic: Black or African American Alone',
    'P2_007N': 'Not Hispanic: American Indian and Alaska Native Alone',
    'P2_008N': 'Not Hispanic: Asian Alone',
    'P2_009N': 'Not Hispanic: Native Hawaiian and Other Pacific Islander Alone',
    'P2_010N': 'Not Hispanic: Some Other Race Alone',
    'P2_011N': 'Not Hispanic: Two or More Races',

    # PL 94-171 P3: Race for 18+
    'P3_001N': 'Total Population 18 Years and Over',
    'P3_002N': 'Population 18+: One Race',
    'P3_003N': 'Population 18+: White Alone',
    'P3_004N': 'Population 18+: Black or African American Alone',
    'P3_005N': 'Population 18+: American Indian and Alaska Native Alone',
    'P3_006N': 'Population 18+: Asian Alone',
    'P3_007N': 'Population 18+: Native Hawaiian and Other Pacific Islander Alone',
    'P3_008N': 'Population 18+: Some Other Race Alone',
    'P3_009N': 'Population 18+: Two or More Races',

    # PL 94-171 P4: Hispanic by Race for 18+
    'P4_001N': 'Total Population 18+ (Hispanic Origin)',
    'P4_002N': 'Hispanic or Latino 18+',
    'P4_003N': 'Not Hispanic or Latino 18+',
    'P4_004N': 'Not Hispanic 18+: One Race',
    'P4_005N': 'Not Hispanic 18+: White Alone',
    'P4_006N': 'Not Hispanic 18+: Black or African American Alone',
    'P4_007N': 'Not Hispanic 18+: American Indian and Alaska Native Alone',
    'P4_008N': 'Not Hispanic 18+: Asian Alone',
    'P4_009N': 'Not Hispanic 18+: Native Hawaiian and Other Pacific Islander Alone',
    'P4_010N': 'Not Hispanic 18+: Some Other Race Alone',
    'P4_011N': 'Not Hispanic 18+: Two or More Races',

    # PL 94-171 P5: Group Quarters
    'P5_001N': 'Total Group Quarters Population',
    'P5_002N': 'Institutionalized Population',
    'P5_003N': 'Correctional Facilities for Adults',
    'P5_004N': 'Juvenile Facilities',
    'P5_005N': 'Nursing Facilities/Skilled-Nursing Facilities',
    'P5_006N': 'Other Institutional Facilities',
    'P5_007N': 'Noninstitutionalized Population',
    'P5_008N': 'College/University Student Housing',
    'P5_009N': 'Military Quarters',
    'P5_010N': 'Other Noninstitutional Facilities',

    # PL 94-171 H1: Housing Occupancy
    'H1_001N': 'Total Housing Units',
    'H1_002N': 'Occupied Housing Units',
    'H1_003N': 'Vacant Housing Units',
}


# =============================================================================
# CUSTOM EXCEPTIONS
# =============================================================================

class CensusAPIError(Exception):
    """Base exception for Census API errors."""
    pass


class CensusAPIKeyError(CensusAPIError):
    """Error related to API key authentication."""
    pass


class CensusRateLimitError(CensusAPIError):
    """Rate limit exceeded error."""
    pass


class CensusVariableError(CensusAPIError):
    """Invalid or unavailable variable error."""
    pass


class CensusGeographyError(CensusAPIError):
    """Invalid geography specification error."""
    pass


# =============================================================================
# CENSUS API CLIENT
# =============================================================================

class CensusAPIClient:
    """
    Client for fetching demographic data from the Census Bureau API.

    This client provides methods to:
    - Fetch demographic data for various geographic levels
    - Get variable metadata
    - List available variables
    - Handle caching and rate limiting

    Attributes:
        api_key: Census API key (optional but recommended)
        timeout: Request timeout in seconds
        cache_dir: Directory for caching responses
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        timeout: Optional[int] = None,
        cache_dir: Optional[Union[str, Path]] = None,
        cache_backend: str = 'parquet',
        cache_ttl: int = CENSUS_API_CACHE_TIMEOUT,
    ):
        """
        Initialize the Census API client.

        Args:
            api_key: Census API key. Resolution order:
                1. Explicitly provided key
                2. UserProfile.census_api_key
                3. CENSUS_API_KEY environment variable
                4. None (API works without key but is rate-limited)
            timeout: Request timeout in seconds
            cache_dir: Directory for caching responses (parquet backend only)
            cache_backend: Cache backend — 'parquet' (file-based, default) or
                'django' (uses django.core.cache framework)
            cache_ttl: Cache time-to-live in seconds (default: 86400 = 24h)
        """
        self.api_key = self._resolve_api_key(api_key)
        self.timeout = timeout or get_service_timeout('census_api') or CENSUS_API_DEFAULT_TIMEOUT
        self.base_url = CENSUS_API_BASE_URL
        self.cache_backend = cache_backend
        self.cache_ttl = cache_ttl

        # Setup cache directory (parquet backend only)
        if cache_backend == 'parquet':
            if cache_dir:
                self.cache_dir = Path(cache_dir)
            else:
                self.cache_dir = Path.home() / '.siege_utilities' / 'cache' / 'census_api'
            self.cache_dir.mkdir(parents=True, exist_ok=True)
        else:
            self.cache_dir = None

        log.info(
            f"Initialized CensusAPIClient "
            f"(API key: {'provided' if self.api_key else 'not set'}, "
            f"cache: {cache_backend})"
        )

    def _resolve_api_key(self, explicit_key: Optional[str]) -> Optional[str]:
        """
        Resolve API key from various sources.

        Priority order:
        1. Explicitly provided key
        2. UserProfile.census_api_key
        3. CENSUS_API_KEY environment variable
        4. None
        """
        # 1. Explicit key
        if explicit_key:
            return explicit_key

        # 2. UserProfile
        try:
            user_config = get_user_config()
            profile_key = user_config.get_api_key('census')
            if profile_key:
                return profile_key
        except Exception as e:
            log.debug(f"Could not get API key from user profile: {e}")

        # 3. Environment variable
        env_key = os.environ.get('CENSUS_API_KEY')
        if env_key:
            return env_key

        # 4. None
        return None

    def fetch_data(
        self,
        variables: Union[str, List[str]],
        year: int,
        dataset: str = 'acs5',
        geography: str = 'county',
        state_fips: Optional[str] = None,
        county_fips: Optional[str] = None,
        include_moe: bool = True
    ) -> pd.DataFrame:
        """
        Fetch demographic data from the Census API.

        Args:
            variables: Variable name, list of variable codes, or predefined group name.
                Use predefined groups like 'demographics_basic', 'income', 'education', etc.
            year: Census year (e.g., 2020, 2021, 2022)
            dataset: Dataset identifier. Options:
                - 'acs5': ACS 5-year estimates (default)
                - 'acs1': ACS 1-year estimates
                - 'dec': Decennial census
                - 'pep': Population estimates
            geography: Geographic level. Options:
                - 'state': State level
                - 'county': County level
                - 'tract': Census tract level
                - 'block_group': Block group level
            state_fips: State FIPS code (required for tract/block_group)
            county_fips: County FIPS code (optional, for filtering)
            include_moe: Include margin of error columns for ACS estimates

        Returns:
            DataFrame with columns: GEOID, NAME, and requested variable columns

        Raises:
            CensusVariableError: If variables are invalid
            CensusGeographyError: If geography specification is invalid
            CensusRateLimitError: If rate limit is exceeded
            CensusAPIError: For other API errors
        """
        # Resolve variables
        var_list = self._resolve_variables(variables)

        # Add margin of error variables for ACS
        if include_moe and dataset.startswith('acs'):
            var_list = self._add_moe_variables(var_list)

        # Validate and normalize geography (e.g. 'bg' → 'block_group')
        geography = self._validate_geography(geography, state_fips, county_fips)

        # Normalize state FIPS if provided
        if state_fips:
            state_fips = self._normalize_state(state_fips)

        # Check cache first
        cache_key = self._generate_cache_key(var_list, year, dataset, geography, state_fips, county_fips)
        cached_df = self._get_from_cache(cache_key)
        if cached_df is not None:
            log.info(f"Returning cached data for {geography} ({len(cached_df)} rows)")
            return cached_df

        # Build API URL
        url = self._build_url(var_list, year, dataset, geography, state_fips, county_fips)

        # Make request with retry logic
        df = self._make_request_with_retry(url)

        # Process response
        df = self._process_response(df, geography, state_fips, county_fips)

        # Cache result
        self._save_to_cache(cache_key, df)

        log.info(f"Fetched {len(df)} rows of {geography}-level data for year {year}")
        return df

    def _resolve_variables(self, variables: Union[str, List[str]]) -> List[str]:
        """Resolve variable specification to list of variable codes."""
        if isinstance(variables, str):
            # Check if it's a predefined group
            if variables in VARIABLE_GROUPS:
                return VARIABLE_GROUPS[variables].copy()
            # Otherwise treat as single variable
            return [variables]
        return list(variables)

    def _add_moe_variables(self, variables: List[str]) -> List[str]:
        """Add margin of error variables for ACS estimate variables."""
        result = []
        for var in variables:
            result.append(var)
            # ACS estimate variables end with 'E', add corresponding 'M' for MOE
            if var.endswith('E'):
                moe_var = var[:-1] + 'M'
                result.append(moe_var)
        return result

    def _validate_geography(
        self,
        geography: str,
        state_fips: Optional[str],
        county_fips: Optional[str]
    ) -> str:
        """Validate and normalize geography to canonical form.

        Accepts any alias (e.g., 'bg', 'zip_code') and returns the
        canonical geography string for use in downstream URL/key construction.
        """
        from siege_utilities.config.census_constants import resolve_geographic_level
        try:
            canonical = resolve_geographic_level(geography)
        except ValueError:
            raise CensusGeographyError(
                f"Invalid geography '{geography}'. "
                f"Valid options: {['state', 'county', 'tract', 'block_group', 'place', 'zcta']}"
            )
        # Census API supports these levels
        api_supported = {'state', 'county', 'tract', 'block_group', 'place', 'zcta'}

        if canonical not in api_supported:
            raise CensusGeographyError(
                f"Census API does not support geography '{geography}' "
                f"(resolved to '{canonical}'). "
                f"Supported: {sorted(api_supported)}"
            )

        # Tract and block group require state FIPS
        if canonical in ['tract', 'block_group'] and not state_fips:
            raise CensusGeographyError(
                f"State FIPS code is required for {canonical}-level data"
            )

        # County FIPS only makes sense with state FIPS
        if county_fips and not state_fips:
            raise CensusGeographyError(
                "County FIPS requires state FIPS to be specified"
            )

        return canonical

    def _normalize_state(self, state_input: str) -> str:
        """Normalize state identifier to FIPS code."""
        try:
            return normalize_state_identifier(state_input)
        except ValueError as e:
            raise CensusGeographyError(str(e))

    def _build_url(
        self,
        variables: List[str],
        year: int,
        dataset: str,
        geography: str,
        state_fips: Optional[str],
        county_fips: Optional[str]
    ) -> str:
        """Build Census API URL."""
        # Determine dataset path
        dataset_path = self._get_dataset_path(year, dataset)

        # Build variable list (always include NAME)
        var_str = ','.join(['NAME'] + variables)

        # Build geography clause
        geo_clause = self._build_geography_clause(geography, state_fips, county_fips)

        # Build URL
        url = f"{self.base_url}/{dataset_path}?get={var_str}&{geo_clause}"

        # Add API key if available
        if self.api_key:
            url += f"&key={self.api_key}"

        return url

    def _get_dataset_path(self, year: int, dataset: str) -> str:
        """Get the dataset path for the API URL."""
        dataset_paths = {
            'acs5': f'{year}/acs/acs5',
            'acs1': f'{year}/acs/acs1',
            'dec': f'{year}/dec/pl',  # Decennial PL 94-171
            'pep': f'{year}/pep/population',
        }

        if dataset not in dataset_paths:
            raise CensusVariableError(
                f"Unknown dataset '{dataset}'. Valid options: {list(dataset_paths.keys())}"
            )

        return dataset_paths[dataset]

    def _build_geography_clause(
        self,
        geography: str,
        state_fips: Optional[str],
        county_fips: Optional[str]
    ) -> str:
        """Build the geography clause for the API URL."""
        if geography == 'state':
            if state_fips:
                return f"for=state:{state_fips}"
            return "for=state:*"

        elif geography == 'county':
            if county_fips and state_fips:
                return f"for=county:{county_fips}&in=state:{state_fips}"
            elif state_fips:
                return f"for=county:*&in=state:{state_fips}"
            return "for=county:*"

        elif geography == 'tract':
            if county_fips:
                return f"for=tract:*&in=state:{state_fips}%20county:{county_fips}"
            return f"for=tract:*&in=state:{state_fips}"

        elif geography == 'block_group':
            if county_fips:
                return f"for=block%20group:*&in=state:{state_fips}%20county:{county_fips}"
            return f"for=block%20group:*&in=state:{state_fips}"

        elif geography == 'place':
            if state_fips:
                return f"for=place:*&in=state:{state_fips}"
            return "for=place:*"

        elif geography == 'zcta':
            return "for=zip%20code%20tabulation%20area:*"

        raise CensusGeographyError(f"Unsupported geography: {geography}")

    def _make_request_with_retry(self, url: str) -> pd.DataFrame:
        """Make API request with retry logic."""
        last_exception = None

        for attempt in range(CENSUS_RETRY_ATTEMPTS):
            try:
                log.debug(f"Making Census API request (attempt {attempt + 1})")
                response = requests.get(url, timeout=self.timeout)

                # Check for rate limiting
                if response.status_code == 429:
                    raise CensusRateLimitError("Census API rate limit exceeded")

                # Check for errors
                response.raise_for_status()

                # Parse JSON response
                data = response.json()

                # Census API returns list of lists, first row is headers
                if not data or len(data) < 2:
                    from siege_utilities.exceptions import SiegeAPIError, handle_error
                    return handle_error(
                        SiegeAPIError("Census API returned empty response (< 2 rows)"),
                        on_error=getattr(self, '_on_error', 'skip'),
                        fallback=pd.DataFrame(),
                        context="Census API query",
                    )

                # Convert to DataFrame
                df = pd.DataFrame(data[1:], columns=data[0])
                return df

            except CensusRateLimitError:
                log.warning(f"Rate limit hit, waiting {CENSUS_API_RATE_LIMIT_RETRY_DELAY}s...")
                time.sleep(CENSUS_API_RATE_LIMIT_RETRY_DELAY)
                last_exception = CensusRateLimitError("Census API rate limit exceeded after retries")

            except requests.exceptions.Timeout:
                log.warning(f"Request timeout (attempt {attempt + 1})")
                last_exception = CensusAPIError("Census API request timed out")
                time.sleep(2 ** attempt)  # Exponential backoff

            except requests.exceptions.RequestException as e:
                log.warning(f"Request failed: {e}")
                last_exception = CensusAPIError(f"Census API request failed: {e}")
                time.sleep(2 ** attempt)

            except ValueError as e:
                # JSON decode error
                log.error(f"Failed to parse API response: {e}")
                raise CensusAPIError(f"Invalid API response: {e}")

        if last_exception:
            raise last_exception
        raise CensusAPIError("Census API request failed after all retries")

    def _process_response(
        self,
        df: pd.DataFrame,
        geography: str,
        state_fips: Optional[str],
        county_fips: Optional[str]
    ) -> pd.DataFrame:
        """Process API response to create standardized DataFrame."""
        if df.empty:
            return df

        # Construct GEOID based on geography level
        df = self._construct_geoid(df, geography)

        # Convert numeric columns
        df = self._convert_numeric_columns(df)

        # Reorder columns (GEOID and NAME first)
        cols = df.columns.tolist()
        priority_cols = ['GEOID', 'NAME']
        other_cols = [c for c in cols if c not in priority_cols]
        df = df[priority_cols + other_cols]

        return df

    def _construct_geoid(self, df: pd.DataFrame, geography: str) -> pd.DataFrame:
        """Construct GEOID column based on geography level."""
        if geography == 'state':
            df['GEOID'] = df['state']

        elif geography == 'county':
            df['GEOID'] = df['state'] + df['county']

        elif geography == 'tract':
            df['GEOID'] = df['state'] + df['county'] + df['tract']

        elif geography == 'block_group':
            df['GEOID'] = df['state'] + df['county'] + df['tract'] + df['block group']

        elif geography == 'place':
            df['GEOID'] = df['state'] + df['place']

        elif geography == 'zcta':
            # ZCTA column name varies
            zcta_col = None
            for col in df.columns:
                if 'zip' in col.lower() or 'zcta' in col.lower():
                    zcta_col = col
                    break
            if zcta_col:
                df['GEOID'] = df[zcta_col]
            else:
                df['GEOID'] = ''

        # Drop component columns used for GEOID
        cols_to_drop = ['state', 'county', 'tract', 'block group', 'place']
        cols_to_drop = [c for c in cols_to_drop if c in df.columns]
        df = df.drop(columns=cols_to_drop, errors='ignore')

        return df

    def _convert_numeric_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Convert variable columns to numeric types."""
        skip_cols = {'GEOID', 'NAME'}

        for col in df.columns:
            if col in skip_cols:
                continue

            # Try to convert to numeric
            try:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            except Exception:
                pass

        return df

    def _generate_cache_key(
        self,
        variables: List[str],
        year: int,
        dataset: str,
        geography: str,
        state_fips: Optional[str],
        county_fips: Optional[str]
    ) -> str:
        """Generate a cache key for the request."""
        key_parts = [
            ','.join(sorted(variables)),
            str(year),
            dataset,
            geography,
            state_fips or '',
            county_fips or ''
        ]
        key_str = '|'.join(key_parts)
        return hashlib.md5(key_str.encode()).hexdigest()

    def _get_from_cache(self, cache_key: str) -> Optional[pd.DataFrame]:
        """Get cached data if available and not expired."""
        if self.cache_backend == 'django':
            return self._django_cache_get(cache_key)
        return self._parquet_cache_get(cache_key)

    def _save_to_cache(self, cache_key: str, df: pd.DataFrame) -> None:
        """Save data to cache."""
        if self.cache_backend == 'django':
            return self._django_cache_set(cache_key, df)
        return self._parquet_cache_set(cache_key, df)

    def _parquet_cache_get(self, cache_key: str) -> Optional[pd.DataFrame]:
        """Get cached data from parquet file backend."""
        cache_file = self.cache_dir / f"{cache_key}.parquet"

        if not cache_file.exists():
            return None

        # Check if cache is expired
        file_mtime = datetime.fromtimestamp(cache_file.stat().st_mtime)
        if datetime.now() - file_mtime > timedelta(seconds=self.cache_ttl):
            log.debug(f"Cache expired for {cache_key}")
            cache_file.unlink()  # Delete expired cache
            return None

        try:
            return pd.read_parquet(cache_file)
        except Exception as e:
            log.warning(f"Failed to read cache file: {e}")
            return None

    def _parquet_cache_set(self, cache_key: str, df: pd.DataFrame) -> None:
        """Save data to parquet file backend."""
        cache_file = self.cache_dir / f"{cache_key}.parquet"

        try:
            df.to_parquet(cache_file, index=False)
            log.debug(f"Cached data to {cache_file}")
        except Exception as e:
            log.warning(f"Failed to cache data: {e}")

    def _django_cache_get(self, cache_key: str) -> Optional[pd.DataFrame]:
        """Get cached data from Django cache framework."""
        try:
            from django.core.cache import cache
            data = cache.get(f"census_api:{cache_key}")
            if data is not None:
                log.debug(f"Django cache hit for {cache_key}")
                return pd.DataFrame(data)
            return None
        except Exception as e:
            log.warning(f"Django cache get failed: {e}")
            return None

    def _django_cache_set(self, cache_key: str, df: pd.DataFrame) -> None:
        """Save data to Django cache framework."""
        try:
            from django.core.cache import cache
            cache.set(
                f"census_api:{cache_key}",
                df.to_dict(orient='list'),
                timeout=self.cache_ttl,
            )
            log.debug(f"Django cache set for {cache_key}")
        except Exception as e:
            log.warning(f"Django cache set failed: {e}")

    def get_variable_metadata(
        self,
        variable: str,
        year: int,
        dataset: str = 'acs5'
    ) -> Dict[str, Any]:
        """
        Get metadata for a Census variable.

        Args:
            variable: Variable code (e.g., 'B01001_001E')
            year: Census year
            dataset: Dataset identifier

        Returns:
            Dictionary with variable metadata
        """
        # Check local descriptions first
        if variable in VARIABLE_DESCRIPTIONS:
            return {
                'code': variable,
                'label': VARIABLE_DESCRIPTIONS[variable],
                'source': 'local'
            }

        # Try API endpoint for variable metadata
        dataset_path = self._get_dataset_path(year, dataset)
        url = f"{self.base_url}/{dataset_path}/variables/{variable}.json"

        try:
            response = requests.get(url, timeout=self.timeout)
            if response.ok:
                data = response.json()
                return {
                    'code': variable,
                    'label': data.get('label', 'Unknown'),
                    'concept': data.get('concept', ''),
                    'predicateType': data.get('predicateType', ''),
                    'source': 'api'
                }
        except Exception as e:
            log.debug(f"Could not fetch variable metadata: {e}")

        return {
            'code': variable,
            'label': 'Unknown',
            'source': 'unknown'
        }

    def list_available_variables(
        self,
        year: int,
        dataset: str = 'acs5',
        search: Optional[str] = None
    ) -> pd.DataFrame:
        """
        List available variables for a dataset.

        Args:
            year: Census year
            dataset: Dataset identifier
            search: Optional search term to filter variables

        Returns:
            DataFrame with variable codes and labels
        """
        dataset_path = self._get_dataset_path(year, dataset)
        url = f"{self.base_url}/{dataset_path}/variables.json"

        try:
            response = requests.get(url, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()

            # Parse variables
            variables = data.get('variables', {})
            rows = []
            for code, info in variables.items():
                if code in ['for', 'in', 'ucgid']:  # Skip geography variables
                    continue
                rows.append({
                    'code': code,
                    'label': info.get('label', ''),
                    'concept': info.get('concept', ''),
                    'predicateType': info.get('predicateType', '')
                })

            df = pd.DataFrame(rows)

            # Filter by search term if provided
            if search and not df.empty:
                search_lower = search.lower()
                mask = (
                    df['code'].str.lower().str.contains(search_lower, na=False) |
                    df['label'].str.lower().str.contains(search_lower, na=False) |
                    df['concept'].str.lower().str.contains(search_lower, na=False)
                )
                df = df[mask]

            return df.sort_values('code').reset_index(drop=True)

        except Exception as e:
            log.error(f"Failed to list variables: {e}")
            return pd.DataFrame(columns=['code', 'label', 'concept', 'predicateType'])

    def clear_cache(self) -> None:
        """Clear all cached API responses."""
        try:
            for cache_file in self.cache_dir.glob('*.parquet'):
                cache_file.unlink()
            log.info("Cleared Census API cache")
        except Exception as e:
            log.warning(f"Failed to clear cache: {e}")


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

    Example:
        df = get_demographics(state='California', geography='county', year=2020)
        df = get_demographics(state='TX', geography='county', year=2023, dataset='acs1')
    """
    if year is None:
        year = datetime.now().year - 1  # Most recent complete year

    # Normalize state to FIPS
    state_fips = normalize_state_identifier(state)

    client = CensusAPIClient()
    return client.fetch_data(
        variables=variables,
        year=year,
        dataset=dataset,
        geography=geography,
        state_fips=state_fips,
        include_moe=include_moe
    )


def get_population(
    state: str,
    geography: str = 'tract',
    year: Optional[int] = None,
    dataset: str = 'acs5',
) -> pd.DataFrame:
    """
    Convenience function to get population data.

    Args:
        state: State name, abbreviation, or FIPS code
        geography: Geographic level
        year: Census year
        dataset: Census dataset ('acs5', 'acs1', 'dec')

    Returns:
        DataFrame with GEOID, NAME, and population columns
    """
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
        include_moe=True
    )


def get_income_data(
    state: str,
    geography: str = 'tract',
    year: Optional[int] = None,
    include_moe: bool = True,
    dataset: str = 'acs5',
) -> pd.DataFrame:
    """
    Convenience function to get income data.

    Args:
        state: State name, abbreviation, or FIPS code
        geography: Geographic level
        year: Census year
        include_moe: Include margin of error columns
        dataset: Census dataset ('acs5', 'acs1', 'dec')

    Returns:
        DataFrame with GEOID, NAME, and income variables
    """
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
        include_moe=include_moe
    )


def get_education_data(
    state: str,
    geography: str = 'tract',
    year: Optional[int] = None,
    include_moe: bool = True,
    dataset: str = 'acs5',
) -> pd.DataFrame:
    """
    Convenience function to get educational attainment data.

    Args:
        state: State name, abbreviation, or FIPS code
        geography: Geographic level
        year: Census year
        include_moe: Include margin of error columns
        dataset: Census dataset ('acs5', 'acs1', 'dec')

    Returns:
        DataFrame with GEOID, NAME, and education variables
    """
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
        include_moe=include_moe
    )


def get_housing_data(
    state: str,
    geography: str = 'tract',
    year: Optional[int] = None,
    include_moe: bool = True,
    dataset: str = 'acs5',
) -> pd.DataFrame:
    """
    Convenience function to get housing data.

    Args:
        state: State name, abbreviation, or FIPS code
        geography: Geographic level
        year: Census year
        include_moe: Include margin of error columns
        dataset: Census dataset ('acs5', 'acs1', 'dec')

    Returns:
        DataFrame with GEOID, NAME, and housing variables
    """
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
        include_moe=include_moe
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
    include_moe: bool = True
) -> 'gpd.GeoDataFrame':
    """
    Fetch Census boundaries AND demographic data, returning a merged GeoDataFrame.

    This is the primary function for getting choropleth-ready data. It:
    1. Fetches TIGER/Line geometry for the specified geography
    2. Fetches demographic variables from the Census API
    3. Joins them on GEOID

    Args:
        year: Census year (e.g., 2020, 2021, 2022)
        geography: Geographic level ('state', 'county', 'tract', 'block_group')
        variables: Variable codes, list of codes, or predefined group name
            (e.g., 'income', 'demographics_basic', ['B01001_001E', 'B19013_001E'])
        state: State identifier (name, abbreviation, or FIPS code)
            Required for tract and block_group levels
        county_fips: County FIPS code (3 digits) for filtering
        dataset: Census dataset ('acs5', 'acs1', 'dec')
        include_moe: Include margin of error columns for ACS data

    Returns:
        GeoDataFrame with geometry AND demographic columns, joined on GEOID

    Example:
        # Get California county data with income variables
        gdf = get_census_data_with_geometry(
            year=2020,
            geography='county',
            variables='income',
            state='California'
        )

        # Get LA County tract data with multiple variables
        gdf = get_census_data_with_geometry(
            year=2020,
            geography='tract',
            variables=['B01001_001E', 'B19013_001E'],
            state='CA',
            county_fips='037'
        )

        # Ready for mapping!
        gdf.plot(column='B19013_001E', legend=True)
    """
    import geopandas as gpd
    from .spatial_data import get_census_boundaries
    from .geoid_utils import find_geoid_column

    # Normalize state identifier
    state_fips = None
    if state:
        state_fips = normalize_state_identifier(state)

    # Validate geography requirements
    if geography in ['tract', 'block_group'] and not state_fips:
        raise CensusGeographyError(
            f"State is required for {geography}-level data"
        )

    log.info(f"Fetching {geography}-level data with geometry for year {year}")

    # 1. Fetch geometry (TIGER/Line boundaries)
    log.info("Fetching TIGER/Line boundaries...")
    shapes_gdf = get_census_boundaries(
        year=year,
        geographic_level=geography,
        state_fips=state_fips
    )

    if shapes_gdf is None or shapes_gdf.empty:
        raise CensusAPIError(f"Failed to fetch boundaries for {geography}")

    # Filter geometry to county scope when county_fips is provided.
    # TIGER files are per-state, so we post-filter by COUNTYFP column
    # or by GEOID prefix to match the demographics scope.
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
            # Fallback: filter by GEOID prefix (state_fips + county_fips)
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
        include_moe=include_moe
    )

    if demographics_df.empty:
        log.warning("No demographic data returned, returning geometry only")
        return shapes_gdf

    log.info(f"Retrieved {len(demographics_df)} demographic records")

    # 3. Find and normalize GEOID columns for joining
    # Find GEOID column in shapes
    shapes_geoid_col = find_geoid_column(shapes_gdf)
    if shapes_geoid_col is None:
        # Try common TIGER column names
        for col in ['GEOID', 'GEOID20', 'GEOID10', 'geoid', 'AFFGEOID']:
            if col in shapes_gdf.columns:
                shapes_geoid_col = col
                break

    if shapes_geoid_col is None:
        raise CensusAPIError(
            f"Cannot find GEOID column in geometry data. "
            f"Available columns: {list(shapes_gdf.columns)[:10]}"
        )

    # Demographics should have 'GEOID' from our fetch_data processing
    if 'GEOID' not in demographics_df.columns:
        raise CensusAPIError("Demographics data missing GEOID column")

    # Normalize GEOIDs for consistent joining
    # TIGER files may have different GEOID formats (GEOID20 includes prefix like "1400000US")
    def extract_numeric_geoid(geoid_val):
        """Extract numeric portion of GEOID, handling TIGER prefixes."""
        if pd.isna(geoid_val):
            return None
        geoid_str = str(geoid_val)
        # TIGER GEOIDs may have format like "1400000US06037101100"
        if 'US' in geoid_str:
            return geoid_str.split('US')[-1]
        return geoid_str

    # Normalize both sides
    shapes_gdf = shapes_gdf.copy()
    shapes_gdf['_join_geoid'] = shapes_gdf[shapes_geoid_col].apply(extract_numeric_geoid)

    demographics_df = demographics_df.copy()
    demographics_df['_join_geoid'] = demographics_df['GEOID'].astype(str)

    # 4. Perform the join
    # Drop duplicate columns that would conflict (except geometry)
    demo_cols_to_drop = []
    for col in demographics_df.columns:
        if col in shapes_gdf.columns and col not in ['_join_geoid', 'GEOID']:
            demo_cols_to_drop.append(col)

    if demo_cols_to_drop:
        demographics_df = demographics_df.drop(columns=demo_cols_to_drop)

    # Left join to preserve all geometries
    merged_gdf = shapes_gdf.merge(
        demographics_df,
        on='_join_geoid',
        how='left',
        suffixes=('', '_demo')
    )

    # Clean up join column
    merged_gdf = merged_gdf.drop(columns=['_join_geoid'])

    # Ensure it's still a GeoDataFrame
    if not isinstance(merged_gdf, gpd.GeoDataFrame):
        merged_gdf = gpd.GeoDataFrame(merged_gdf, geometry='geometry')

    # Log join statistics
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
    how: str = 'left'
) -> 'gpd.GeoDataFrame':
    """
    Join demographic data to existing shapes GeoDataFrame.

    Use this when you already have shapes loaded and want to add demographic data.

    Args:
        shapes_gdf: GeoDataFrame with geometry
        demographics_df: DataFrame with demographic data
        shapes_geoid_col: GEOID column name in shapes (auto-detected if None)
        demographics_geoid_col: GEOID column name in demographics
        how: Join type ('left', 'inner', 'outer')

    Returns:
        Merged GeoDataFrame

    Example:
        # Load shapes separately
        shapes = gpd.read_file('my_boundaries.shp')

        # Fetch demographics
        demo = get_demographics(state='CA', geography='county', year=2020)

        # Join them
        merged = join_demographics_to_shapes(shapes, demo)
    """
    import geopandas as gpd
    from .geoid_utils import find_geoid_column

    # Find GEOID column in shapes if not specified
    if shapes_geoid_col is None:
        shapes_geoid_col = find_geoid_column(shapes_gdf)
        if shapes_geoid_col is None:
            raise ValueError(
                "Cannot find GEOID column in shapes. "
                f"Available columns: {list(shapes_gdf.columns)[:10]}"
            )

    # Normalize GEOIDs
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

    # Remove conflicting columns
    demo_cols_to_drop = [
        col for col in demographics_df.columns
        if col in shapes_gdf.columns and col != '_join_geoid'
    ]
    if demo_cols_to_drop:
        demographics_df = demographics_df.drop(columns=demo_cols_to_drop)

    # Merge
    merged = shapes_gdf.merge(
        demographics_df,
        on='_join_geoid',
        how=how
    )

    # Clean up
    merged = merged.drop(columns=['_join_geoid'])

    # Ensure GeoDataFrame
    if not isinstance(merged, gpd.GeoDataFrame):
        merged = gpd.GeoDataFrame(merged, geometry='geometry')

    return merged

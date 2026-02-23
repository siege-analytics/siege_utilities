"""
GEOID utilities for Census data processing.

This module provides functions for constructing, normalizing, and validating
Census GEOIDs (Geographic Identifiers). GEOIDs are hierarchical codes that
uniquely identify geographic areas.

GEOID Structure:
- State: 2 digits (e.g., "06" for California)
- County: 5 digits (state + county, e.g., "06037" for LA County)
- Tract: 11 digits (state + county + tract, e.g., "06037101100")
- Block Group: 12 digits (state + county + tract + block group)
- Block: 15 digits (state + county + tract + block)

Example usage:
    from siege_utilities.geo import normalize_geoid, construct_geoid, validate_geoid, can_normalize_geoid

    # Normalize a GEOID to proper length
    geoid = normalize_geoid("6037", "county")  # Returns "06037"

    # Construct GEOID from components
    geoid = construct_geoid(state="06", county="037", geography="county")

    # Validate GEOID format (strict by default — requires leading zeros)
    is_valid = validate_geoid("06037", "county")  # Returns True
    is_valid = validate_geoid("6037", "county")   # Returns False (missing leading zero)

    # Check if a value can be normalized to a valid GEOID
    can_fix = can_normalize_geoid("6037", "county")  # Returns True
"""

import logging
import re
from typing import Dict, Optional, Union

import pandas as pd

from siege_utilities.config.census_constants import (
    CANONICAL_GEOGRAPHIC_LEVELS,
    resolve_geographic_level,
)

log = logging.getLogger(__name__)


# =============================================================================
# GEOID LENGTH CONSTANTS (derived from canonical geographic levels)
# =============================================================================

GEOID_LENGTHS = {
    name: info['geoid_length']
    for name, info in CANONICAL_GEOGRAPHIC_LEVELS.items()
    if info.get('geoid_length') is not None
}

# Component lengths within GEOID
GEOID_COMPONENT_LENGTHS = {
    'state': 2,
    'county': 3,
    'tract': 6,
    'block_group': 1,
    'block': 4,
    'place': 5,
    'zcta': 5,
}


# =============================================================================
# GEOID NORMALIZATION
# =============================================================================

def normalize_geoid(
    geoid: Union[str, int],
    geography_level: str
) -> str:
    """
    Normalize a GEOID to the standard format with proper zero-padding.

    Args:
        geoid: GEOID value (can be string or int)
        geography_level: Geographic level ('state', 'county', 'tract', etc.)

    Returns:
        Normalized GEOID string with proper zero-padding

    Raises:
        ValueError: If geography level is unknown or GEOID is invalid

    Example:
        >>> normalize_geoid("6037", "county")
        "06037"
        >>> normalize_geoid(6, "state")
        "06"
        >>> normalize_geoid("6037101100", "tract")
        "06037101100"
    """
    # Convert to string
    geoid_str = str(geoid).strip()

    # Resolve to canonical name and get expected length
    geography_lower = resolve_geographic_level(geography_level)
    expected_length = GEOID_LENGTHS.get(geography_lower)

    if expected_length is None:
        raise ValueError(
            f"Unknown geography level: '{geography_level}'. "
            f"Valid levels: {list(GEOID_LENGTHS.keys())}"
        )

    # Zero-pad to expected length
    normalized = geoid_str.zfill(expected_length)

    # Validate result
    if len(normalized) != expected_length:
        log.warning(
            f"GEOID '{geoid}' is longer than expected for {geography_level} "
            f"(expected {expected_length}, got {len(normalized)})"
        )

    return normalized


def normalize_geoid_column(
    df: pd.DataFrame,
    geoid_column: str,
    geography_level: str,
    inplace: bool = False
) -> pd.DataFrame:
    """
    Normalize a GEOID column in a DataFrame.

    Args:
        df: DataFrame containing GEOID column
        geoid_column: Name of the GEOID column
        geography_level: Geographic level for normalization
        inplace: If True, modify DataFrame in place

    Returns:
        DataFrame with normalized GEOID column
    """
    if not inplace:
        df = df.copy()

    df[geoid_column] = df[geoid_column].apply(
        lambda x: normalize_geoid(x, geography_level) if pd.notna(x) else x
    )

    return df


# =============================================================================
# GEOID CONSTRUCTION
# =============================================================================

def construct_geoid(
    geography: str,
    state: Optional[str] = None,
    county: Optional[str] = None,
    tract: Optional[str] = None,
    block_group: Optional[str] = None,
    block: Optional[str] = None,
    place: Optional[str] = None
) -> str:
    """
    Construct a GEOID from component parts.

    Args:
        geography: Target geography level
        state: State FIPS code (2 digits)
        county: County FIPS code (3 digits)
        tract: Census tract code (6 digits)
        block_group: Block group code (1 digit)
        block: Block code (4 digits)
        place: Place code (5 digits)

    Returns:
        Constructed GEOID string

    Raises:
        ValueError: If required components are missing

    Example:
        >>> construct_geoid("county", state="06", county="037")
        "06037"
        >>> construct_geoid("tract", state="06", county="037", tract="101100")
        "06037101100"
    """
    geography_lower = resolve_geographic_level(geography)

    # Normalize components
    def pad(value: Optional[str], length: int) -> str:
        if value is None:
            raise ValueError(f"Missing required component")
        return str(value).zfill(length)

    if geography_lower == 'state':
        return pad(state, 2)

    elif geography_lower == 'county':
        return pad(state, 2) + pad(county, 3)

    elif geography_lower == 'tract':
        return pad(state, 2) + pad(county, 3) + pad(tract, 6)

    elif geography_lower == 'block_group':
        return pad(state, 2) + pad(county, 3) + pad(tract, 6) + pad(block_group, 1)

    elif geography_lower == 'block':
        return pad(state, 2) + pad(county, 3) + pad(tract, 6) + pad(block, 4)

    elif geography_lower == 'place':
        return pad(state, 2) + pad(place, 5)

    else:
        raise ValueError(f"Unsupported geography for GEOID construction: {geography}")


def construct_geoid_from_row(
    row: pd.Series,
    geography_level: str
) -> str:
    """
    Construct a GEOID from a DataFrame row containing Census API response columns.

    This function handles the column names returned by the Census API.

    Args:
        row: DataFrame row with Census columns (state, county, tract, etc.)
        geography_level: Target geography level

    Returns:
        Constructed GEOID string

    Example:
        # For a row from Census API response:
        # {'state': '06', 'county': '037', 'tract': '101100', ...}
        geoid = construct_geoid_from_row(row, 'tract')
        # Returns: '06037101100'
    """
    geography_lower = resolve_geographic_level(geography_level)

    def get_value(col_name: str) -> Optional[str]:
        """Get value from row, handling different column name formats."""
        # Try exact match first
        if col_name in row.index:
            return str(row[col_name])
        # Try lowercase
        if col_name.lower() in row.index:
            return str(row[col_name.lower()])
        # Try with spaces replaced
        col_with_space = col_name.replace('_', ' ')
        if col_with_space in row.index:
            return str(row[col_with_space])
        return None

    state = get_value('state')
    county = get_value('county')
    tract = get_value('tract')
    block_group = get_value('block_group') or get_value('block group')
    block = get_value('block')
    place = get_value('place')

    return construct_geoid(
        geography=geography_level,
        state=state,
        county=county,
        tract=tract,
        block_group=block_group,
        block=block,
        place=place
    )


# =============================================================================
# GEOID PARSING
# =============================================================================

def parse_geoid(
    geoid: str,
    geography_level: str
) -> Dict[str, str]:
    """
    Parse a GEOID into its component parts.

    Args:
        geoid: GEOID string
        geography_level: Geography level of the GEOID

    Returns:
        Dictionary with component parts (state, county, tract, etc.)

    Example:
        >>> parse_geoid("06037101100", "tract")
        {'state': '06', 'county': '037', 'tract': '101100'}
    """
    geography_lower = resolve_geographic_level(geography_level)

    # Normalize first
    geoid = normalize_geoid(geoid, geography_level)

    result = {}

    if geography_lower == 'state':
        result['state'] = geoid[:2]

    elif geography_lower == 'county':
        result['state'] = geoid[:2]
        result['county'] = geoid[2:5]

    elif geography_lower == 'tract':
        result['state'] = geoid[:2]
        result['county'] = geoid[2:5]
        result['tract'] = geoid[5:11]

    elif geography_lower == 'block_group':
        result['state'] = geoid[:2]
        result['county'] = geoid[2:5]
        result['tract'] = geoid[5:11]
        result['block_group'] = geoid[11:12]

    elif geography_lower == 'block':
        result['state'] = geoid[:2]
        result['county'] = geoid[2:5]
        result['tract'] = geoid[5:11]
        result['block'] = geoid[11:15]

    elif geography_lower == 'place':
        result['state'] = geoid[:2]
        result['place'] = geoid[2:7]

    else:
        raise ValueError(f"Unsupported geography for GEOID parsing: {geography_level}")

    return result


def extract_parent_geoid(
    geoid: str,
    child_geography: str,
    parent_geography: str
) -> str:
    """
    Extract a parent GEOID from a child GEOID.

    Args:
        geoid: Child GEOID
        child_geography: Geography level of the input GEOID
        parent_geography: Geography level to extract

    Returns:
        Parent GEOID

    Example:
        >>> extract_parent_geoid("06037101100", "tract", "county")
        "06037"
        >>> extract_parent_geoid("060371011001", "block_group", "state")
        "06"
    """
    components = parse_geoid(geoid, child_geography)

    parent_lower = resolve_geographic_level(parent_geography)

    if parent_lower == 'state':
        return components['state']
    elif parent_lower == 'county':
        return components['state'] + components['county']
    elif parent_lower == 'tract':
        return components['state'] + components['county'] + components['tract']
    else:
        raise ValueError(f"Cannot extract {parent_geography} from {child_geography}")


# =============================================================================
# GEOID VALIDATION
# =============================================================================

def validate_geoid(
    geoid: str,
    geography_level: str,
    strict: bool = True
) -> bool:
    """
    Validate a GEOID format.

    Census GEOIDs are always fixed-width, zero-padded strings. A value missing
    leading zeros (e.g., '6037' instead of '06037') is NOT a valid GEOID — it
    may be normalizable via normalize_geoid(), but it would fail joins against
    Census shapefiles.

    Args:
        geoid: GEOID string to validate
        geography_level: Expected geography level
        strict: If True (default), require exact length match.
                If False, allow shorter values that could be zero-padded.

    Returns:
        True if GEOID is valid, False otherwise

    Example:
        >>> validate_geoid("06037", "county")
        True
        >>> validate_geoid("6037", "county")  # Missing leading zero
        False  # Not a valid GEOID (use can_normalize_geoid to check normalizability)
        >>> validate_geoid("6037", "county", strict=False)
        True  # Non-strict allows shorter values
    """
    if not geoid or not isinstance(geoid, str):
        return False

    # Remove whitespace
    geoid = geoid.strip()

    # Check if all digits
    if not geoid.isdigit():
        return False

    # Resolve to canonical name and get expected length
    try:
        geography_lower = resolve_geographic_level(geography_level)
    except ValueError:
        return False
    expected_length = GEOID_LENGTHS.get(geography_lower)

    if expected_length is None:
        return False

    if strict:
        return len(geoid) == expected_length
    else:
        # Non-strict: allow shorter (can be zero-padded)
        return len(geoid) <= expected_length


def can_normalize_geoid(
    geoid: Union[str, int],
    geography_level: str
) -> bool:
    """
    Check whether a value can be normalized to a valid GEOID.

    Unlike validate_geoid(), this accepts values that are shorter than the
    expected length (e.g., '6037' for county) because they can be zero-padded
    to a valid GEOID via normalize_geoid().

    Args:
        geoid: Value to check (string or integer)
        geography_level: Expected geography level

    Returns:
        True if value can be normalized to a valid GEOID

    Example:
        >>> can_normalize_geoid("6037", "county")
        True  # Can be zero-padded to "06037"
        >>> can_normalize_geoid("06037", "county")
        True  # Already valid
        >>> can_normalize_geoid("CA037", "county")
        False  # Contains non-numeric characters
        >>> can_normalize_geoid("123456", "county")
        False  # Too long (county GEOID is 5 digits)
    """
    geoid_str = str(geoid).strip()

    if not geoid_str or not geoid_str.isdigit():
        return False

    try:
        geography_lower = resolve_geographic_level(geography_level)
    except ValueError:
        return False
    expected_length = GEOID_LENGTHS.get(geography_lower)

    if expected_length is None:
        return False

    return len(geoid_str) <= expected_length


def validate_geoid_column(
    df: pd.DataFrame,
    geoid_column: str,
    geography_level: str,
    strict: bool = True
) -> pd.Series:
    """
    Validate a GEOID column in a DataFrame.

    Args:
        df: DataFrame containing GEOID column
        geoid_column: Name of the GEOID column
        geography_level: Expected geography level
        strict: If True (default), require exact length match

    Returns:
        Boolean Series indicating validity of each GEOID
    """
    return df[geoid_column].apply(
        lambda x: validate_geoid(str(x), geography_level, strict) if pd.notna(x) else False
    )


# =============================================================================
# GEOID MATCHING FOR JOINS
# =============================================================================

def prepare_geoid_for_join(
    df: pd.DataFrame,
    geoid_column: str,
    geography_level: str,
    output_column: Optional[str] = None
) -> pd.DataFrame:
    """
    Prepare a GEOID column for joining with another dataset.

    This function:
    1. Normalizes GEOIDs to standard format
    2. Validates GEOIDs
    3. Optionally creates a new column for the normalized GEOID

    Args:
        df: DataFrame with GEOID column
        geoid_column: Name of the GEOID column
        geography_level: Geography level
        output_column: Name for normalized column (defaults to geoid_column)

    Returns:
        DataFrame with normalized GEOID column
    """
    df = df.copy()
    output_col = output_column or geoid_column

    # Normalize
    df[output_col] = df[geoid_column].apply(
        lambda x: normalize_geoid(x, geography_level) if pd.notna(x) else None
    )

    # Log any invalid GEOIDs
    valid_mask = validate_geoid_column(df, output_col, geography_level, strict=True)
    invalid_count = (~valid_mask).sum()
    if invalid_count > 0:
        log.warning(f"Found {invalid_count} invalid GEOIDs in column '{geoid_column}'")

    return df


def find_geoid_column(df: pd.DataFrame) -> Optional[str]:
    """
    Find the GEOID column in a DataFrame.

    Looks for common GEOID column names used in Census data.

    Args:
        df: DataFrame to search

    Returns:
        Name of GEOID column if found, None otherwise
    """
    common_names = [
        'GEOID', 'geoid', 'GEOID20', 'GEOID10', 'GEOID00',
        'geoid20', 'geoid10', 'geoid00',
        'GEO_ID', 'geo_id', 'GEOCODE', 'geocode',
        'FIPS', 'fips', 'FIPSCODE', 'fipscode'
    ]

    for name in common_names:
        if name in df.columns:
            return name

    # Try case-insensitive search
    for col in df.columns:
        if col.lower() in [n.lower() for n in common_names]:
            return col

    return None

"""
Census constants — backward-compatible re-export shim.

All Census metadata now lives in ``census_registry.py``.  This module
re-exports every public name so that existing ``from census_constants
import …`` statements continue to work without changes.
"""

# Re-export everything from the registry
from .census_registry import (  # noqa: F401
    # Enums
    SurveyType,
    DataReliability,
    GeographyLevel,
    # Geographic levels
    CANONICAL_GEOGRAPHIC_LEVELS,
    resolve_geographic_level,
    GEOGRAPHIC_LEVELS,
    GEOGRAPHIC_HIERARCHY,
    # Dataset types
    DATASET_TYPES,
    RELIABILITY_LEVELS,
    # FIPS codes
    STATE_FIPS_CODES,
    FIPS_TO_STATE,
    STATE_NAMES,
    # URLs
    CENSUS_BASE_URL,
    CENSUS_API_BASE_URL,
    CENSUS_FTP_BASE_URL,
    # Years
    AVAILABLE_CENSUS_YEARS,
    DEFAULT_CENSUS_YEAR,
    DECENNIAL_YEARS,
    ACS_AVAILABLE_YEARS,
    ACS5_AVAILABLE_YEARS,
    BOUNDARY_CHANGE_YEARS,
    # File patterns
    TIGER_FILE_PATTERNS,
    # Operation settings
    CENSUS_CACHE_TIMEOUT,
    CENSUS_MAX_CACHE_SIZE,
    CENSUS_TIMEOUT,
    CENSUS_RETRY_ATTEMPTS,
    CENSUS_API_CACHE_TIMEOUT,
    CENSUS_API_DEFAULT_TIMEOUT,
    CENSUS_API_RATE_LIMIT_RETRY_DELAY,
    # Variable data
    VARIABLE_GROUPS,
    VARIABLE_DESCRIPTIONS,
    # Helper functions
    normalize_state_identifier,
    get_tiger_url,
    validate_geographic_level,
    get_fips_info,
    # Internal (used by tests)
    _ALIAS_TO_CANONICAL,
)

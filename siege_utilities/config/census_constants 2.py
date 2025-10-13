"""
Census-specific constants for siege_utilities.
Centralized configuration for Census Bureau data sources and operations.
"""

from typing import Dict, List, Any

# =============================================================================
# CENSUS BUREAU DATA SOURCES
# =============================================================================

# Primary Census URLs
CENSUS_BASE_URL = "https://www2.census.gov/geo/tiger"
CENSUS_API_BASE_URL = "https://api.census.gov/data"
CENSUS_FTP_BASE_URL = "https://www2.census.gov"

# =============================================================================
# CENSUS GEOGRAPHIC LEVELS
# =============================================================================

GEOGRAPHIC_LEVELS = {
    "NATION": "nation",
    "REGION": "region", 
    "DIVISION": "division",
    "STATE": "state",
    "COUNTY": "county",
    "COUNTY_SUBDIVISION": "county_subdivision",
    "PLACE": "place",
    "CONGRESSIONAL_DISTRICT": "congressional_district",
    "STATE_LEGISLATIVE_DISTRICT": "state_legislative_district",
    "TRACT": "tract",
    "BLOCK_GROUP": "block_group",
    "BLOCK": "block",
    "ZIP_CODE": "zip_code",
    "CBSA": "cbsa",  # Metropolitan/Micropolitan Statistical Areas
    "PUMA": "puma",  # Public Use Microdata Areas
}

# Geographic level hierarchy (for validation)
GEOGRAPHIC_HIERARCHY = [
    "nation", "region", "division", "state", "county", 
    "county_subdivision", "tract", "block_group", "block"
]

# =============================================================================
# CENSUS DATASET TYPES
# =============================================================================

DATASET_TYPES = {
    "ACS": "acs",                           # American Community Survey
    "DECENNIAL": "decennial",               # Every 10 years (2020, 2010, etc.)
    "ECONOMIC": "economic",                 # Economic Census
    "CENSUS_BUSINESS": "census_business",   # Economic Census
    "POPULATION_ESTIMATES": "population_estimates",  # Annual population estimates
    "HOUSING_ESTIMATES": "housing_estimates",        # Annual housing estimates
}

# =============================================================================
# CENSUS DATA RELIABILITY LEVELS
# =============================================================================

RELIABILITY_LEVELS = {
    "HIGH": "high",           # Most reliable (decennial, large geographies)
    "MEDIUM": "medium",       # Moderately reliable (ACS 5-year, medium geographies)
    "LOW": "low",             # Less reliable (ACS 1-year, small geographies)
    "ESTIMATED": "estimated"  # Modeled estimates
}

# =============================================================================
# FIPS CODES (STATE IDENTIFIERS)
# =============================================================================

STATE_FIPS_CODES = {
    'AL': '01', 'AK': '02', 'AZ': '04', 'AR': '05', 'CA': '06', 'CO': '08', 'CT': '09',
    'DE': '10', 'FL': '12', 'GA': '13', 'HI': '15', 'ID': '16', 'IL': '17', 'IN': '18',
    'IA': '19', 'KS': '20', 'KY': '21', 'LA': '22', 'ME': '23', 'MD': '24', 'MA': '25',
    'MI': '26', 'MN': '27', 'MS': '28', 'MO': '29', 'MT': '30', 'NE': '31', 'NV': '32',
    'NH': '33', 'NJ': '34', 'NM': '35', 'NY': '36', 'NC': '37', 'ND': '38', 'OH': '39',
    'OK': '40', 'OR': '41', 'PA': '42', 'RI': '44', 'SC': '45', 'SD': '46', 'TN': '47',
    'TX': '48', 'UT': '49', 'VT': '50', 'VA': '51', 'WA': '53', 'WV': '54', 'WI': '55',
    'WY': '56', 'DC': '11', 'PR': '72', 'VI': '78', 'AS': '60', 'GU': '66', 'MP': '69'
}

# Reverse mapping for FIPS to state abbreviation
FIPS_TO_STATE = {fips: state for state, fips in STATE_FIPS_CODES.items()}

# Full state names mapping
STATE_NAMES = {
    'AL': 'Alabama', 'AK': 'Alaska', 'AZ': 'Arizona', 'AR': 'Arkansas', 'CA': 'California',
    'CO': 'Colorado', 'CT': 'Connecticut', 'DE': 'Delaware', 'FL': 'Florida', 'GA': 'Georgia',
    'HI': 'Hawaii', 'ID': 'Idaho', 'IL': 'Illinois', 'IN': 'Indiana', 'IA': 'Iowa',
    'KS': 'Kansas', 'KY': 'Kentucky', 'LA': 'Louisiana', 'ME': 'Maine', 'MD': 'Maryland',
    'MA': 'Massachusetts', 'MI': 'Michigan', 'MN': 'Minnesota', 'MS': 'Mississippi',
    'MO': 'Missouri', 'MT': 'Montana', 'NE': 'Nebraska', 'NV': 'Nevada', 'NH': 'New Hampshire',
    'NJ': 'New Jersey', 'NM': 'New Mexico', 'NY': 'New York', 'NC': 'North Carolina',
    'ND': 'North Dakota', 'OH': 'Ohio', 'OK': 'Oklahoma', 'OR': 'Oregon', 'PA': 'Pennsylvania',
    'RI': 'Rhode Island', 'SC': 'South Carolina', 'SD': 'South Dakota', 'TN': 'Tennessee',
    'TX': 'Texas', 'UT': 'Utah', 'VT': 'Vermont', 'VA': 'Virginia', 'WA': 'Washington',
    'WV': 'West Virginia', 'WI': 'Wisconsin', 'WY': 'Wyoming', 'DC': 'District of Columbia',
    'PR': 'Puerto Rico', 'VI': 'Virgin Islands', 'AS': 'American Samoa', 'GU': 'Guam',
    'MP': 'Northern Mariana Islands'
}

# =============================================================================
# CENSUS YEARS AND AVAILABILITY
# =============================================================================

# Available Census years (will be updated as new data becomes available)
AVAILABLE_CENSUS_YEARS = [2010, 2020, 2021, 2022, 2023]
DEFAULT_CENSUS_YEAR = 2023

# Year ranges for different data types
DECENNIAL_YEARS = [2000, 2010, 2020]
ACS_AVAILABLE_YEARS = list(range(2009, 2024))  # ACS available from 2009

# =============================================================================
# CENSUS FILE FORMATS AND PATTERNS
# =============================================================================

# File naming patterns for TIGER/Line files
TIGER_FILE_PATTERNS = {
    "county": "tl_{year}_{state_fips}_county.zip",
    "tract": "tl_{year}_{state_fips}_tract.zip", 
    "block_group": "tl_{year}_{state_fips}_bg.zip",
    "place": "tl_{year}_{state_fips}_place.zip",
    "state": "tl_{year}_us_state.zip",
    "nation": "tl_{year}_us_nation.zip"
}

# =============================================================================
# CENSUS OPERATION SETTINGS
# =============================================================================
# Census Bureau services require specific timeout and retry settings due to:
# - Government servers often slower than commercial APIs
# - Large file sizes (TIGER/Line shapefiles can be 10-100MB+)
# - High reliability requirements for data integrity
# - Network congestion during peak usage periods

# Cache settings for Census data
CENSUS_CACHE_TIMEOUT = 86400  # 24 hours - Census data updates infrequently
CENSUS_MAX_CACHE_SIZE = 1000  # Reasonable limit for file-based cache

# Download settings - more generous than general web requests
CENSUS_TIMEOUT = 45           # Longer timeout due to large files and slower servers
CENSUS_RETRY_ATTEMPTS = 5     # More retries - Census reliability is critical

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def normalize_state_identifier(state_input: str) -> str:
    """
    Normalize state identifier to FIPS code.
    
    Args:
        state_input: State abbreviation, name, or FIPS code
        
    Returns:
        FIPS code as string
        
    Raises:
        ValueError: If state identifier is not recognized
    """
    state_input = str(state_input).strip().upper()
    
    # If it's already a FIPS code
    if state_input in FIPS_TO_STATE:
        return state_input
    
    # If it's a state abbreviation
    if state_input in STATE_FIPS_CODES:
        return STATE_FIPS_CODES[state_input]
    
    # If it's a full state name
    for abbrev, name in STATE_NAMES.items():
        if state_input == name.upper():
            return STATE_FIPS_CODES[abbrev]
    
    raise ValueError(f"Unrecognized state identifier: {state_input}")

def get_tiger_url(year: int, state_fips: str, geographic_level: str) -> str:
    """
    Generate TIGER/Line download URL.
    
    Args:
        year: Census year
        state_fips: State FIPS code
        geographic_level: Geographic level (county, tract, etc.)
        
    Returns:
        Complete URL for TIGER/Line file
        
    Raises:
        ValueError: If parameters are invalid
    """
    if geographic_level not in TIGER_FILE_PATTERNS:
        raise ValueError(f"Unsupported geographic level: {geographic_level}")
    
    if year not in AVAILABLE_CENSUS_YEARS:
        raise ValueError(f"Census year {year} not available")
    
    filename = TIGER_FILE_PATTERNS[geographic_level].format(
        year=year, state_fips=state_fips
    )
    
    return f"{CENSUS_BASE_URL}/TIGER{year}/{geographic_level.upper()}/{filename}"

def validate_geographic_level(level: str) -> bool:
    """Validate if geographic level is supported."""
    return level.lower() in GEOGRAPHIC_LEVELS.values()

def get_fips_info(state_identifier: str) -> Dict[str, str]:
    """
    Get comprehensive FIPS information for a state.
    
    Args:
        state_identifier: State abbreviation, name, or FIPS code
        
    Returns:
        Dictionary with FIPS code, abbreviation, and full name
    """
    fips_code = normalize_state_identifier(state_identifier)
    state_abbrev = FIPS_TO_STATE[fips_code]
    state_name = STATE_NAMES[state_abbrev]
    
    return {
        'fips': fips_code,
        'abbreviation': state_abbrev,
        'name': state_name
    }

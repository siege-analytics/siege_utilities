"""
NCES (National Center for Education Statistics) constants for siege_utilities.
Centralized configuration for NCES data sources and urbanicity calculations.

This module supports the planned NCES urbanicity integration described in IMPROVEMENTS.md.
"""

from typing import Dict, List, Tuple, Any

# =============================================================================
# NCES DATA SOURCES
# =============================================================================

# Primary NCES URLs
NCES_BASE_URL = "https://nces.ed.gov/programs/edge/data"
NCES_GEOGRAPHIC_URL = "https://nces.ed.gov/programs/edge/Geographic"
NCES_LOCALE_BOUNDARIES_URL = "https://nces.ed.gov/programs/edge/Geographic/LocaleBoundaries"

# NCES data download endpoints
NCES_DOWNLOAD_ENDPOINTS = {
    "locale_boundaries": f"{NCES_BASE_URL}/EDGE_LOCALE_BOUNDARIES",
    "school_locations": f"{NCES_BASE_URL}/EDGE_GEOCODE_PUBLICSCH",
    "district_boundaries": f"{NCES_BASE_URL}/EDGE_ADMINDATA_PUBLICSCH"
}

# =============================================================================
# NCES LOCALE CLASSIFICATION SYSTEM
# =============================================================================

# NCES Locale Types (4-category system)
LOCALE_CATEGORIES = {
    "CITY": "city",
    "SUBURBAN": "suburban", 
    "TOWN": "town",
    "RURAL": "rural"
}

# NCES Locale Subcategories (12-category system)
LOCALE_SUBCATEGORIES = {
    # City subcategories
    "CITY_LARGE": "city_large",      # Large City
    "CITY_MIDSIZE": "city_midsize",  # Midsize City  
    "CITY_SMALL": "city_small",      # Small City
    
    # Suburban subcategories
    "SUBURB_LARGE": "suburb_large",   # Large Suburb
    "SUBURB_MIDSIZE": "suburb_midsize", # Midsize Suburb
    "SUBURB_SMALL": "suburb_small",   # Small Suburb
    
    # Town subcategories  
    "TOWN_FRINGE": "town_fringe",     # Town: Fringe
    "TOWN_DISTANT": "town_distant",   # Town: Distant
    "TOWN_REMOTE": "town_remote",     # Town: Remote
    
    # Rural subcategories
    "RURAL_FRINGE": "rural_fringe",   # Rural: Fringe
    "RURAL_DISTANT": "rural_distant", # Rural: Distant
    "RURAL_REMOTE": "rural_remote"    # Rural: Remote
}

# Numeric codes used by NCES
LOCALE_NUMERIC_CODES = {
    11: "city_large",
    12: "city_midsize", 
    13: "city_small",
    21: "suburb_large",
    22: "suburb_midsize",
    23: "suburb_small",
    31: "town_fringe",
    32: "town_distant",
    33: "town_remote",
    41: "rural_fringe",
    42: "rural_distant",
    43: "rural_remote"
}

# Reverse mapping
LOCALE_CODE_TO_NUMERIC = {v: k for k, v in LOCALE_NUMERIC_CODES.items()}

# =============================================================================
# URBANICITY DEFINITIONS AND THRESHOLDS
# =============================================================================

# Population thresholds for locale classification (based on NCES methodology)
POPULATION_THRESHOLDS = {
    "large_city": 250000,        # Large city/suburb threshold
    "midsize_city": 100000,      # Midsize city/suburb threshold  
    "small_city": 25000,         # Small city/suburb threshold
    "town_threshold": 2500       # Town vs rural threshold
}

# Distance thresholds (in miles) for fringe/distant/remote classification
DISTANCE_THRESHOLDS = {
    "fringe_max": 5,      # Within 5 miles of urbanized area
    "distant_max": 25,    # 5-25 miles from urbanized area
    "remote_min": 25      # More than 25 miles from urbanized area
}

# =============================================================================
# NCES FILE FORMATS AND PATTERNS
# =============================================================================

# Expected file naming patterns for NCES downloads
NCES_FILE_PATTERNS = {
    "locale_boundaries": "EDGE_LOCALE_BOUNDARIES_{year}.zip",
    "school_locations": "EDGE_GEOCODE_PUBLICSCH_{year}.zip", 
    "district_boundaries": "EDGE_ADMINDATA_PUBLICSCH_{year}.zip"
}

# File formats supported by NCES
NCES_SUPPORTED_FORMATS = ["shp", "csv", "xlsx", "txt"]

# =============================================================================
# NCES DATA YEARS AND AVAILABILITY  
# =============================================================================

# Available NCES data years (updated annually)
AVAILABLE_NCES_YEARS = [2018, 2019, 2020, 2021, 2022, 2023]
DEFAULT_NCES_YEAR = 2023

# =============================================================================
# URBANICITY CALCULATION SETTINGS
# =============================================================================

# Default settings for urbanicity calculations
URBANICITY_SETTINGS = {
    "buffer_distance": 1000,      # meters for geographic buffering
    "population_weight": 0.6,     # weight for population density
    "distance_weight": 0.4,       # weight for distance to urban areas
    "min_sample_size": 100        # minimum sample size for calculations
}

# =============================================================================
# INTEGRATION WITH CENSUS DATA
# =============================================================================

# Fields for joining NCES data with Census data
CENSUS_NCES_JOIN_FIELDS = {
    "state_fips": "STATE",
    "county_fips": "COUNTY", 
    "tract_fips": "TRACT",
    "block_group_fips": "BLKGRP"
}

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_locale_category(locale_code: int) -> str:
    """
    Get the 4-category locale type from numeric code.
    
    Args:
        locale_code: NCES numeric locale code (11-43)
        
    Returns:
        Locale category (city, suburban, town, rural)
        
    Raises:
        ValueError: If locale code is not recognized
    """
    if locale_code not in LOCALE_NUMERIC_CODES:
        raise ValueError(f"Unrecognized NCES locale code: {locale_code}")
    
    subcategory = LOCALE_NUMERIC_CODES[locale_code]
    
    # Map subcategory to main category
    if subcategory.startswith('city'):
        return 'city'
    elif subcategory.startswith('suburb'):
        return 'suburban'
    elif subcategory.startswith('town'):
        return 'town'
    elif subcategory.startswith('rural'):
        return 'rural'
    else:
        raise ValueError(f"Cannot determine category for subcategory: {subcategory}")

def get_locale_subcategory(locale_code: int) -> str:
    """
    Get the 12-category locale subcategory from numeric code.
    
    Args:
        locale_code: NCES numeric locale code (11-43)
        
    Returns:
        Locale subcategory (e.g., 'city_large', 'rural_remote')
    """
    if locale_code not in LOCALE_NUMERIC_CODES:
        raise ValueError(f"Unrecognized NCES locale code: {locale_code}")
    
    return LOCALE_NUMERIC_CODES[locale_code]

def classify_urbanicity(population: int, distance_to_urban: float) -> str:
    """
    Classify urbanicity based on population and distance to urban areas.
    
    Args:
        population: Population of the area
        distance_to_urban: Distance to nearest urbanized area (miles)
        
    Returns:
        Urbanicity classification string
    """
    # Determine base type from population
    if population >= POPULATION_THRESHOLDS["large_city"]:
        base_type = "city_large" if distance_to_urban <= DISTANCE_THRESHOLDS["fringe_max"] else "suburb_large"
    elif population >= POPULATION_THRESHOLDS["midsize_city"]:
        base_type = "city_midsize" if distance_to_urban <= DISTANCE_THRESHOLDS["fringe_max"] else "suburb_midsize"
    elif population >= POPULATION_THRESHOLDS["small_city"]:
        base_type = "city_small" if distance_to_urban <= DISTANCE_THRESHOLDS["fringe_max"] else "suburb_small"
    elif population >= POPULATION_THRESHOLDS["town_threshold"]:
        # Town classification based on distance
        if distance_to_urban <= DISTANCE_THRESHOLDS["fringe_max"]:
            base_type = "town_fringe"
        elif distance_to_urban <= DISTANCE_THRESHOLDS["distant_max"]:
            base_type = "town_distant"
        else:
            base_type = "town_remote"
    else:
        # Rural classification based on distance
        if distance_to_urban <= DISTANCE_THRESHOLDS["fringe_max"]:
            base_type = "rural_fringe"
        elif distance_to_urban <= DISTANCE_THRESHOLDS["distant_max"]:
            base_type = "rural_distant"
        else:
            base_type = "rural_remote"
    
    return base_type

def get_nces_download_url(data_type: str, year: int) -> str:
    """
    Generate NCES download URL.
    
    Args:
        data_type: Type of NCES data (locale_boundaries, school_locations, etc.)
        year: Data year
        
    Returns:
        Complete URL for NCES data download
        
    Raises:
        ValueError: If parameters are invalid
    """
    if data_type not in NCES_FILE_PATTERNS:
        raise ValueError(f"Unsupported NCES data type: {data_type}")
    
    if year not in AVAILABLE_NCES_YEARS:
        raise ValueError(f"NCES year {year} not available")
    
    base_endpoint = NCES_DOWNLOAD_ENDPOINTS[data_type]
    filename = NCES_FILE_PATTERNS[data_type].format(year=year)
    
    return f"{base_endpoint}/{filename}"

def validate_locale_code(code: int) -> bool:
    """Validate if NCES locale code is recognized."""
    return code in LOCALE_NUMERIC_CODES

def get_urbanicity_info(locale_code: int) -> Dict[str, Any]:
    """
    Get comprehensive urbanicity information for a locale code.
    
    Args:
        locale_code: NCES numeric locale code
        
    Returns:
        Dictionary with category, subcategory, and classification info
    """
    if not validate_locale_code(locale_code):
        raise ValueError(f"Invalid NCES locale code: {locale_code}")
    
    subcategory = get_locale_subcategory(locale_code)
    category = get_locale_category(locale_code)
    
    return {
        'numeric_code': locale_code,
        'category': category,
        'subcategory': subcategory,
        'description': subcategory.replace('_', ' ').title()
    }

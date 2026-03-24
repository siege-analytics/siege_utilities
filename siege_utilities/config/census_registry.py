"""
Census Registry — single source of truth for all Census Bureau metadata.

This module consolidates Census geographic levels, variable groups, survey
types, FIPS codes, TIGER URLs, and API constants that were previously
scattered across ``census_constants.py``, ``census_api_client.py``, and
``census_dataset_mapper.py``.

Other modules should import from here (or from the backward-compatible
shim in ``census_constants.py``).
"""

from datetime import datetime
from enum import Enum
from typing import Dict, List

# ============================================================================
# INTERNAL: current year for dynamic range calculation
# ============================================================================
_CURRENT_YEAR = datetime.now().year


# ============================================================================
# SURVEY AND RELIABILITY ENUMS
# ============================================================================

class SurveyType(Enum):
    """Enumeration of Census survey types."""

    DECENNIAL = "decennial"
    ACS_1YR = "acs_1yr"
    ACS_3YR = "acs_3yr"
    ACS_5YR = "acs_5yr"
    CENSUS_BUSINESS = "census_business"
    POPULATION_ESTIMATES = "population_estimates"
    HOUSING_ESTIMATES = "housing_estimates"


class DataReliability(Enum):
    """Enumeration of data reliability levels."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    ESTIMATED = "estimated"


# ============================================================================
# CANONICAL GEOGRAPHIC LEVELS
# ============================================================================
# Keys are canonical names. Every other reference site derives from this dict.

CANONICAL_GEOGRAPHIC_LEVELS: Dict[str, dict] = {
    "nation":      {"aliases": ["us", "national"],                               "geoid_length": 1},
    "region":      {"aliases": [],                                               "geoid_length": 1},
    "division":    {"aliases": [],                                               "geoid_length": 1},
    "state":       {"aliases": [],                                               "geoid_length": 2},
    "county":      {"aliases": [],                                               "geoid_length": 5},
    "cousub":      {"aliases": ["county_subdivision"],                           "geoid_length": 10},
    "place":       {"aliases": [],                                               "geoid_length": 7},
    "cd":          {"aliases": ["congressional_district"],                       "geoid_length": 4},
    "sldu":        {"aliases": ["state_legislative_upper",
                                "state_legislative_district_upper",
                                "state_legislative_district"],                   "geoid_length": 5},
    "sldl":        {"aliases": ["state_legislative_lower",
                                "state_legislative_district_lower"],             "geoid_length": 5},
    "tract":       {"aliases": [],                                               "geoid_length": 11},
    "block_group": {"aliases": ["bg", "blockgroup"],                             "geoid_length": 12},
    "block":       {"aliases": ["tabblock"],                                     "geoid_length": 15},
    "tabblock20":  {"aliases": [],                                               "geoid_length": 15},
    "tabblock10":  {"aliases": [],                                               "geoid_length": 15},
    "zcta":        {"aliases": ["zip_code", "zcta5", "zipcode"],                 "geoid_length": 5},
    "cbsa":        {"aliases": [],                                               "geoid_length": 5},
    "puma":        {"aliases": [],                                               "geoid_length": 7},
    "vtd":         {"aliases": ["voting_district"],                              "geoid_length": 6},
    "vtd20":       {"aliases": [],                                               "geoid_length": 6},
}

# Build reverse lookup: alias → canonical (computed once at import time)
_ALIAS_TO_CANONICAL: Dict[str, str] = {}
for _canonical, _info in CANONICAL_GEOGRAPHIC_LEVELS.items():
    _ALIAS_TO_CANONICAL[_canonical] = _canonical
    for _alias in _info["aliases"]:
        _ALIAS_TO_CANONICAL[_alias] = _canonical


def resolve_geographic_level(level: str) -> str:
    """
    Resolve any geographic level name variant to its canonical form.

    Accepts long forms (congressional_district), short forms (cd),
    Census abbreviations (CD), and common aliases (zip_code → zcta).
    """
    normalized = level.strip().lower()
    canonical = _ALIAS_TO_CANONICAL.get(normalized)
    if canonical is not None:
        return canonical
    raise ValueError(
        f"Unrecognized geographic level: '{level}'. "
        f"Valid levels: {sorted(CANONICAL_GEOGRAPHIC_LEVELS.keys())}"
    )


class GeographyLevel(Enum):
    """Enumeration of Census geography levels (canonical names)."""

    NATION = "nation"
    REGION = "region"
    DIVISION = "division"
    STATE = "state"
    COUNTY = "county"
    COUSUB = "cousub"
    PLACE = "place"
    CD = "cd"
    SLDU = "sldu"
    SLDL = "sldl"
    TRACT = "tract"
    BLOCK_GROUP = "block_group"
    BLOCK = "block"
    ZCTA = "zcta"
    CBSA = "cbsa"
    PUMA = "puma"
    VTD = "vtd"
    VTD20 = "vtd20"
    TABBLOCK20 = "tabblock20"
    TABBLOCK10 = "tabblock10"

    # Backward-compatible aliases (same value → Python Enum alias)
    COUNTY_SUBDIVISION = "cousub"
    CONGRESSIONAL_DISTRICT = "cd"
    STATE_LEGISLATIVE_DISTRICT = "sldu"  # defaults to upper chamber
    ZIP_CODE = "zcta"
    VOTING_DISTRICT = "vtd"

    @classmethod
    def _missing_(cls, value):
        """Resolve aliases like 'congressional_district' → CD."""
        try:
            canonical = resolve_geographic_level(value)
            for member in cls:
                if member.value == canonical:
                    return member
        except ValueError:
            pass
        return None


# ============================================================================
# BACKWARD-COMPATIBLE GEOGRAPHIC LEVELS (derived from canonical)
# ============================================================================

GEOGRAPHIC_LEVELS: Dict[str, str] = {
    "NATION": "nation",
    "REGION": "region",
    "DIVISION": "division",
    "STATE": "state",
    "COUNTY": "county",
    "COUSUB": "cousub",
    "COUNTY_SUBDIVISION": "cousub",
    "PLACE": "place",
    "CD": "cd",
    "CONGRESSIONAL_DISTRICT": "cd",
    "SLDU": "sldu",
    "SLDL": "sldl",
    "STATE_LEGISLATIVE_DISTRICT": "sldu",
    "TRACT": "tract",
    "BLOCK_GROUP": "block_group",
    "BLOCK": "block",
    "ZCTA": "zcta",
    "ZIP_CODE": "zcta",
    "CBSA": "cbsa",
    "PUMA": "puma",
    "VTD": "vtd",
    "VTD20": "vtd20",
    "TABBLOCK20": "tabblock20",
    "TABBLOCK10": "tabblock10",
    "VOTING_DISTRICT": "vtd",
}

GEOGRAPHIC_HIERARCHY: List[str] = [
    "nation", "region", "division", "state", "county",
    "cousub", "tract", "block_group", "block",
]


# ============================================================================
# CENSUS DATASET TYPES (backward-compatible string dicts)
# ============================================================================

DATASET_TYPES: Dict[str, str] = {
    "DECENNIAL": "decennial",
    "ACS_1YR": "acs_1yr",
    "ACS_3YR": "acs_3yr",
    "ACS_5YR": "acs_5yr",
    "ACS": "acs_5yr",
    "CENSUS_BUSINESS": "census_business",
    "ECONOMIC": "census_business",
    "POPULATION_ESTIMATES": "population_estimates",
    "HOUSING_ESTIMATES": "housing_estimates",
}

RELIABILITY_LEVELS: Dict[str, str] = {
    "HIGH": "high",
    "MEDIUM": "medium",
    "LOW": "low",
    "ESTIMATED": "estimated",
}


# ============================================================================
# FIPS CODES (STATE IDENTIFIERS)
# ============================================================================

STATE_FIPS_CODES: Dict[str, str] = {
    "AL": "01", "AK": "02", "AZ": "04", "AR": "05", "CA": "06", "CO": "08",
    "CT": "09", "DE": "10", "FL": "12", "GA": "13", "HI": "15", "ID": "16",
    "IL": "17", "IN": "18", "IA": "19", "KS": "20", "KY": "21", "LA": "22",
    "ME": "23", "MD": "24", "MA": "25", "MI": "26", "MN": "27", "MS": "28",
    "MO": "29", "MT": "30", "NE": "31", "NV": "32", "NH": "33", "NJ": "34",
    "NM": "35", "NY": "36", "NC": "37", "ND": "38", "OH": "39", "OK": "40",
    "OR": "41", "PA": "42", "RI": "44", "SC": "45", "SD": "46", "TN": "47",
    "TX": "48", "UT": "49", "VT": "50", "VA": "51", "WA": "53", "WV": "54",
    "WI": "55", "WY": "56", "DC": "11", "PR": "72", "VI": "78", "AS": "60",
    "GU": "66", "MP": "69", "UM": "74",
}

FIPS_TO_STATE: Dict[str, str] = {fips: st for st, fips in STATE_FIPS_CODES.items()}

# Downstream compatibility alias (used by Social Warehouse, Reverberator)
STATEFIPS_LOOKUP_DICT = STATE_FIPS_CODES

STATE_NAMES: Dict[str, str] = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas",
    "CA": "California", "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware",
    "FL": "Florida", "GA": "Georgia", "HI": "Hawaii", "ID": "Idaho",
    "IL": "Illinois", "IN": "Indiana", "IA": "Iowa", "KS": "Kansas",
    "KY": "Kentucky", "LA": "Louisiana", "ME": "Maine", "MD": "Maryland",
    "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota", "MS": "Mississippi",
    "MO": "Missouri", "MT": "Montana", "NE": "Nebraska", "NV": "Nevada",
    "NH": "New Hampshire", "NJ": "New Jersey", "NM": "New Mexico", "NY": "New York",
    "NC": "North Carolina", "ND": "North Dakota", "OH": "Ohio", "OK": "Oklahoma",
    "OR": "Oregon", "PA": "Pennsylvania", "RI": "Rhode Island", "SC": "South Carolina",
    "SD": "South Dakota", "TN": "Tennessee", "TX": "Texas", "UT": "Utah",
    "VT": "Vermont", "VA": "Virginia", "WA": "Washington", "WV": "West Virginia",
    "WI": "Wisconsin", "WY": "Wyoming", "DC": "District of Columbia",
    "PR": "Puerto Rico", "VI": "Virgin Islands", "AS": "American Samoa",
    "GU": "Guam", "MP": "Northern Mariana Islands",
    "UM": "United States Minor Outlying Islands",
}


# ============================================================================
# CENSUS URLS
# ============================================================================

CENSUS_BASE_URL = "https://www2.census.gov/geo/tiger"
CENSUS_API_BASE_URL = "https://api.census.gov/data"
CENSUS_FTP_BASE_URL = "https://www2.census.gov"


# ============================================================================
# YEARS AND AVAILABILITY
# ============================================================================

AVAILABLE_CENSUS_YEARS: List[int] = list(range(2010, _CURRENT_YEAR + 1))
DEFAULT_CENSUS_YEAR: int = _CURRENT_YEAR
DECENNIAL_YEARS: List[int] = [y for y in [2000, 2010, 2020, 2030] if y <= _CURRENT_YEAR]
ACS_AVAILABLE_YEARS: List[int] = list(range(2009, _CURRENT_YEAR + 1))
ACS5_AVAILABLE_YEARS: List[int] = ACS_AVAILABLE_YEARS  # alias
BOUNDARY_CHANGE_YEARS: List[int] = [2010, 2020]


# ============================================================================
# TIGER FILE PATTERNS
# ============================================================================

TIGER_FILE_PATTERNS: Dict[str, str] = {
    # National-scope
    "nation": "tl_{year}_us_nation.zip",
    "state": "tl_{year}_us_state.zip",
    "county": "tl_{year}_us_county.zip",
    "cbsa": "tl_{year}_us_cbsa.zip",
    "zcta": "tl_{year}_us_zcta520.zip",
    "cd": "tl_{year}_us_cd{congress_number}.zip",
    "uac": "tl_{year}_us_uac20.zip",
    "uac20": "tl_{year}_us_uac20.zip",
    "rails": "tl_{year}_us_rails.zip",
    "aiannh": "tl_{year}_us_aiannh.zip",
    # State-scope
    "cousub": "tl_{year}_{state_fips}_cousub.zip",
    "tract": "tl_{year}_{state_fips}_tract.zip",
    "block_group": "tl_{year}_{state_fips}_bg.zip",
    "block": "tl_{year}_{state_fips}_tabblock20.zip",
    "tabblock20": "tl_{year}_{state_fips}_tabblock20.zip",
    "tabblock10": "tl_{year}_{state_fips}_tabblock10.zip",
    "place": "tl_{year}_{state_fips}_place.zip",
    "sldu": "tl_{year}_{state_fips}_sldu.zip",
    "sldl": "tl_{year}_{state_fips}_sldl.zip",
    "vtd": "tl_{year}_{state_fips}_vtd.zip",
    "vtd20": "tl_{year}_{state_fips}_vtd20.zip",
    "puma": "tl_{year}_{state_fips}_puma20.zip",
    "roads": "tl_{year}_{state_fips}_roads.zip",
    "linear_water": "tl_{year}_{state_fips}_linearwater.zip",
    "area_water": "tl_{year}_{state_fips}_areawater.zip",
    "edges": "tl_{year}_{state_fips}_edges.zip",
    "address_features": "tl_{year}_{state_fips}_addrfeat.zip",
    "pointlm": "tl_{year}_{state_fips}_pointlm.zip",
    "arealm": "tl_{year}_{state_fips}_arealm.zip",
    "elsd": "tl_{year}_{state_fips}_elsd.zip",
    "scsd": "tl_{year}_{state_fips}_scsd.zip",
    "unsd": "tl_{year}_{state_fips}_unsd.zip",
}


# ============================================================================
# OPERATION SETTINGS
# ============================================================================

CENSUS_CACHE_TIMEOUT = 86400
CENSUS_MAX_CACHE_SIZE = 1000
CENSUS_TIMEOUT = 45
CENSUS_RETRY_ATTEMPTS = 5
CENSUS_API_CACHE_TIMEOUT = 86400
CENSUS_API_DEFAULT_TIMEOUT = 30
CENSUS_API_RATE_LIMIT_RETRY_DELAY = 60


# ============================================================================
# VARIABLE GROUPS
# ============================================================================

VARIABLE_GROUPS: Dict[str, List[str]] = {
    # ACS variable groups
    "total_population": ["B01001_001E"],
    "demographics_basic": [
        "B01001_001E", "B01001_002E", "B01001_026E", "B01002_001E",
    ],
    "race_ethnicity": [
        "B02001_001E", "B02001_002E", "B02001_003E", "B02001_004E",
        "B02001_005E", "B02001_006E", "B02001_007E", "B02001_008E",
        "B03001_003E",
    ],
    "income": ["B19013_001E", "B19301_001E", "B19025_001E"],
    "education": [
        "B15003_001E", "B15003_017E", "B15003_018E", "B15003_021E",
        "B15003_022E", "B15003_023E", "B15003_024E", "B15003_025E",
    ],
    "poverty": ["B17001_001E", "B17001_002E"],
    "housing": [
        "B25001_001E", "B25002_002E", "B25002_003E",
        "B25003_002E", "B25003_003E", "B25077_001E", "B25064_001E",
    ],
    "decennial_population": [
        "P1_001N", "P1_003N", "P1_004N", "P1_005N",
        "P1_006N", "P1_007N", "P1_008N",
    ],
    # PL 94-171 groups
    "pl_p1_race": [
        "P1_001N", "P1_002N", "P1_003N", "P1_004N", "P1_005N",
        "P1_006N", "P1_007N", "P1_008N", "P1_009N", "P1_010N", "P1_011N",
    ],
    "pl_p2_hispanic": [
        "P2_001N", "P2_002N", "P2_003N", "P2_004N", "P2_005N",
        "P2_006N", "P2_007N", "P2_008N", "P2_009N", "P2_010N", "P2_011N",
    ],
    "pl_p3_race_18plus": [
        "P3_001N", "P3_002N", "P3_003N", "P3_004N", "P3_005N",
        "P3_006N", "P3_007N", "P3_008N", "P3_009N",
    ],
    "pl_p4_hispanic_18plus": [
        "P4_001N", "P4_002N", "P4_003N", "P4_004N", "P4_005N",
        "P4_006N", "P4_007N", "P4_008N", "P4_009N", "P4_010N", "P4_011N",
    ],
    "pl_p5_group_quarters": [
        "P5_001N", "P5_002N", "P5_003N", "P5_004N", "P5_005N",
        "P5_006N", "P5_007N", "P5_008N", "P5_009N", "P5_010N",
    ],
    "pl_h1_housing": ["H1_001N", "H1_002N", "H1_003N"],
    "pl_redistricting_core": [
        "P1_001N", "P2_002N", "P2_003N", "P2_005N", "P2_006N",
        "P2_007N", "P2_008N", "P2_009N", "P2_010N", "P2_011N",
        "P3_001N", "P4_002N", "P4_003N", "P4_005N", "P4_006N",
        "H1_001N", "H1_002N", "H1_003N",
    ],
    "pl_voting_age": [
        "P3_001N", "P4_002N", "P4_003N", "P4_005N", "P4_006N",
        "P4_007N", "P4_008N", "P4_009N", "P4_010N", "P4_011N",
    ],
}


VARIABLE_DESCRIPTIONS: Dict[str, str] = {
    # ACS
    "B01001_001E": "Total Population",
    "B01001_002E": "Male Population",
    "B01001_026E": "Female Population",
    "B01002_001E": "Median Age",
    "B02001_001E": "Total (Race)",
    "B02001_002E": "White Alone",
    "B02001_003E": "Black or African American Alone",
    "B02001_004E": "American Indian and Alaska Native Alone",
    "B02001_005E": "Asian Alone",
    "B02001_006E": "Native Hawaiian and Pacific Islander Alone",
    "B02001_007E": "Some Other Race Alone",
    "B02001_008E": "Two or More Races",
    "B03001_003E": "Hispanic or Latino",
    "B19013_001E": "Median Household Income",
    "B19301_001E": "Per Capita Income",
    "B19025_001E": "Aggregate Household Income",
    "B15003_001E": "Population 25 Years and Over",
    "B15003_017E": "High School Graduate",
    "B15003_018E": "GED or Alternative Credential",
    "B15003_021E": "Associate's Degree",
    "B15003_022E": "Bachelor's Degree",
    "B15003_023E": "Master's Degree",
    "B15003_024E": "Professional School Degree",
    "B15003_025E": "Doctorate Degree",
    "B17001_001E": "Population for Poverty Determination",
    "B17001_002E": "Below Poverty Level",
    "B25001_001E": "Total Housing Units",
    "B25002_002E": "Occupied Housing Units",
    "B25002_003E": "Vacant Housing Units",
    "B25003_002E": "Owner Occupied",
    "B25003_003E": "Renter Occupied",
    "B25077_001E": "Median Home Value",
    "B25064_001E": "Median Gross Rent",
    # PL 94-171 P1
    "P1_001N": "Total Population",
    "P1_002N": "Population of One Race",
    "P1_003N": "White Alone",
    "P1_004N": "Black or African American Alone",
    "P1_005N": "American Indian and Alaska Native Alone",
    "P1_006N": "Asian Alone",
    "P1_007N": "Native Hawaiian and Other Pacific Islander Alone",
    "P1_008N": "Some Other Race Alone",
    "P1_009N": "Population of Two or More Races",
    "P1_010N": "Two Races Including Some Other Race",
    "P1_011N": "Two Races Excluding Some Other Race, Three+ Races",
    # PL 94-171 P2
    "P2_001N": "Total Population (Hispanic Origin)",
    "P2_002N": "Hispanic or Latino",
    "P2_003N": "Not Hispanic or Latino",
    "P2_004N": "Not Hispanic: One Race",
    "P2_005N": "Not Hispanic: White Alone",
    "P2_006N": "Not Hispanic: Black or African American Alone",
    "P2_007N": "Not Hispanic: American Indian and Alaska Native Alone",
    "P2_008N": "Not Hispanic: Asian Alone",
    "P2_009N": "Not Hispanic: Native Hawaiian and Other Pacific Islander Alone",
    "P2_010N": "Not Hispanic: Some Other Race Alone",
    "P2_011N": "Not Hispanic: Two or More Races",
    # PL 94-171 P3
    "P3_001N": "Total Population 18 Years and Over",
    "P3_002N": "18+: Population of One Race",
    "P3_003N": "18+: White Alone",
    "P3_004N": "18+: Black or African American Alone",
    "P3_005N": "18+: American Indian and Alaska Native Alone",
    "P3_006N": "18+: Asian Alone",
    "P3_007N": "18+: Native Hawaiian and Other Pacific Islander Alone",
    "P3_008N": "18+: Some Other Race Alone",
    "P3_009N": "18+: Population of Two or More Races",
    # PL 94-171 P4
    "P4_001N": "Total Population 18+ (Hispanic Origin)",
    "P4_002N": "18+: Hispanic or Latino",
    "P4_003N": "18+: Not Hispanic or Latino",
    "P4_004N": "18+: Not Hispanic: One Race",
    "P4_005N": "18+: Not Hispanic: White Alone",
    "P4_006N": "18+: Not Hispanic: Black or African American Alone",
    "P4_007N": "18+: Not Hispanic: American Indian and Alaska Native Alone",
    "P4_008N": "18+: Not Hispanic: Asian Alone",
    "P4_009N": "18+: Not Hispanic: Native Hawaiian and Other Pacific Islander Alone",
    "P4_010N": "18+: Not Hispanic: Some Other Race Alone",
    "P4_011N": "18+: Not Hispanic: Two or More Races",
    # PL 94-171 P5
    "P5_001N": "Total Group Quarters Population",
    "P5_002N": "Institutionalized Population",
    "P5_003N": "Correctional Facilities for Adults",
    "P5_004N": "Juvenile Facilities",
    "P5_005N": "Nursing Facilities/Skilled-Nursing Facilities",
    "P5_006N": "Other Institutional Facilities",
    "P5_007N": "Noninstitutionalized Population",
    "P5_008N": "College/University Student Housing",
    "P5_009N": "Military Quarters",
    "P5_010N": "Other Noninstitutional Facilities",
    # PL 94-171 H1
    "H1_001N": "Total Housing Units",
    "H1_002N": "Occupied Housing Units",
    "H1_003N": "Vacant Housing Units",
}


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def normalize_state_identifier(state_input: str) -> str:
    """Normalize a state identifier to its 2-digit zero-padded FIPS code.

    Parameters
    ----------
    state_input : str
        Any of: 2-digit FIPS code (``"48"``), 2-letter abbreviation
        (``"TX"``), or full state name (``"Texas"``). Case-insensitive.

    Returns
    -------
    str
        Zero-padded 2-digit FIPS code (e.g., ``"06"`` for California).

    Raises
    ------
    ValueError
        If *state_input* doesn't match any known state, territory, or DC.

    Examples
    --------
    >>> normalize_state_identifier("TX")
    '48'
    >>> normalize_state_identifier("48")
    '48'
    >>> normalize_state_identifier("Texas")
    '48'
    >>> normalize_state_identifier("DC")
    '11'
    """
    state_input = str(state_input).strip().upper()
    if state_input in FIPS_TO_STATE:
        return state_input
    if state_input in STATE_FIPS_CODES:
        return STATE_FIPS_CODES[state_input]
    for abbrev, name in STATE_NAMES.items():
        if state_input == name.upper():
            return STATE_FIPS_CODES[abbrev]
    raise ValueError(f"Unrecognized state identifier: {state_input}")


def get_tiger_url(year: int, state_fips: str, geographic_level: str) -> str:
    """Generate TIGER/Line download URL."""
    geographic_level = resolve_geographic_level(geographic_level)
    if geographic_level not in TIGER_FILE_PATTERNS:
        raise ValueError(f"Unsupported geographic level: {geographic_level}")
    if year not in AVAILABLE_CENSUS_YEARS:
        raise ValueError(f"Census year {year} not available")
    filename = TIGER_FILE_PATTERNS[geographic_level].format(
        year=year, state_fips=state_fips
    )
    return f"{CENSUS_BASE_URL}/TIGER{year}/{geographic_level.upper()}/{filename}"


def validate_geographic_level(level: str) -> bool:
    """Validate if geographic level is supported. Accepts any alias."""
    try:
        resolve_geographic_level(level)
        return True
    except ValueError:
        return False


def get_fips_info(state_identifier: str) -> Dict[str, str]:
    """Return FIPS code, abbreviation, and full name for a state.

    Parameters
    ----------
    state_identifier : str
        Any form accepted by :func:`normalize_state_identifier`.

    Returns
    -------
    dict
        Keys: ``"fips"`` (zero-padded), ``"abbreviation"``, ``"name"``.

    Examples
    --------
    >>> get_fips_info("CA")
    {'fips': '06', 'abbreviation': 'CA', 'name': 'California'}
    """
    fips_code = normalize_state_identifier(state_identifier)
    state_abbrev = FIPS_TO_STATE[fips_code]
    state_name = STATE_NAMES[state_abbrev]
    return {"fips": fips_code, "abbreviation": state_abbrev, "name": state_name}

"""
Variable registry for Census API variable groups, descriptions, and metadata.

Pure data + lookup logic — no I/O except optional API calls for unknown variables.
"""

import logging
from typing import Dict, List, Optional, Union, Any

import pandas as pd

log = logging.getLogger(__name__)


# =============================================================================
# PREDEFINED VARIABLE GROUPS
# =============================================================================

VARIABLE_GROUPS: Dict[str, List[str]] = {
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
VARIABLE_DESCRIPTIONS: Dict[str, str] = {
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


class VariableRegistry:
    """
    Registry for Census variable groups, descriptions, and metadata lookup.

    Pure data + logic — all methods are stateless except optional API calls
    for unknown variable metadata.
    """

    def __init__(self, groups: Optional[Dict[str, List[str]]] = None,
                 descriptions: Optional[Dict[str, str]] = None):
        self.groups = groups or VARIABLE_GROUPS
        self.descriptions = descriptions or VARIABLE_DESCRIPTIONS

    def resolve_variables(self, variables: Union[str, List[str]]) -> List[str]:
        """Resolve variable specification to list of variable codes."""
        if isinstance(variables, str):
            if variables in self.groups:
                return self.groups[variables].copy()
            return [variables]
        return list(variables)

    def add_moe_variables(self, variables: List[str]) -> List[str]:
        """Add margin of error variables for ACS estimate variables."""
        result = []
        for var in variables:
            result.append(var)
            if var.endswith('E'):
                moe_var = var[:-1] + 'M'
                result.append(moe_var)
        return result

    def get_description(self, variable: str) -> str:
        """Get human-readable description for a variable code."""
        return self.descriptions.get(variable, 'Unknown')

    def get_variable_metadata(
        self,
        variable: str,
        year: int,
        dataset: str = 'acs5',
        base_url: Optional[str] = None,
        timeout: int = 30,
    ) -> Dict[str, Any]:
        """
        Get metadata for a Census variable.

        Checks local descriptions first, falls back to API if needed.
        """
        if variable in self.descriptions:
            return {
                'code': variable,
                'label': self.descriptions[variable],
                'source': 'local',
            }

        if base_url is None:
            from siege_utilities.config import CENSUS_API_BASE_URL
            base_url = CENSUS_API_BASE_URL

        from .dataset_selector import DatasetSelector
        dataset_path = DatasetSelector.get_dataset_path(year, dataset)
        url = f"{base_url}/{dataset_path}/variables/{variable}.json"

        try:
            import requests
            response = requests.get(url, timeout=timeout)
            if response.ok:
                data = response.json()
                return {
                    'code': variable,
                    'label': data.get('label', 'Unknown'),
                    'concept': data.get('concept', ''),
                    'predicateType': data.get('predicateType', ''),
                    'source': 'api',
                }
        except Exception as e:
            log.debug(f"Could not fetch variable metadata: {e}")

        return {'code': variable, 'label': 'Unknown', 'source': 'unknown'}

    def list_available_variables(
        self,
        year: int,
        dataset: str = 'acs5',
        search: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: int = 30,
    ) -> pd.DataFrame:
        """
        List available variables for a dataset from the Census API.
        """
        if base_url is None:
            from siege_utilities.config import CENSUS_API_BASE_URL
            base_url = CENSUS_API_BASE_URL

        from .dataset_selector import DatasetSelector
        dataset_path = DatasetSelector.get_dataset_path(year, dataset)
        url = f"{base_url}/{dataset_path}/variables.json"

        try:
            import requests
            response = requests.get(url, timeout=timeout)
            response.raise_for_status()
            data = response.json()

            variables = data.get('variables', {})
            rows = []
            for code, info in variables.items():
                if code in ['for', 'in', 'ucgid']:
                    continue
                rows.append({
                    'code': code,
                    'label': info.get('label', ''),
                    'concept': info.get('concept', ''),
                    'predicateType': info.get('predicateType', ''),
                })

            df = pd.DataFrame(rows)

            if search and not df.empty:
                search_lower = search.lower()
                mask = (
                    df['code'].str.lower().str.contains(search_lower, na=False)
                    | df['label'].str.lower().str.contains(search_lower, na=False)
                    | df['concept'].str.lower().str.contains(search_lower, na=False)
                )
                df = df[mask]

            return df.sort_values('code').reset_index(drop=True)

        except Exception as e:
            log.error(f"Failed to list variables: {e}")
            return pd.DataFrame(columns=['code', 'label', 'concept', 'predicateType'])

    def list_groups(self) -> Dict[str, int]:
        """Return available variable groups and their variable counts."""
        return {name: len(vars_) for name, vars_ in self.groups.items()}

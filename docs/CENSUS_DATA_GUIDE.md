# Census Data Products Reference Guide

This guide explains the relationships between Census Bureau data products, when to use each, and how they integrate with `siege_utilities`.

---

## Quick Reference: Which Dataset Should I Use?

| Analysis Need | Best Dataset | Alternative | Notes |
|--------------|--------------|-------------|-------|
| **Official population counts** | Decennial (PL 94-171) | - | Legal/constitutional basis |
| **Redistricting** | PL 94-171 | - | Required by law |
| **Race/ethnicity at block level** | PL 94-171 | - | Only source for blocks |
| **Detailed demographics (tract+)** | ACS 5-Year | ACS 1-Year | Income, education, etc. |
| **Recent trends (large areas)** | ACS 1-Year | ACS 5-Year | 65,000+ population only |
| **Small area estimates** | ACS 5-Year | - | Most reliable for tracts |
| **Annual population estimates** | PEP | ACS 1-Year | Between decennials |
| **Housing characteristics** | ACS 5-Year | Decennial | Detailed housing data |

---

## Census Data Products Overview

### 1. Decennial Census

The constitutional mandate to count every person in the United States every 10 years.

#### PL 94-171 Redistricting Data
- **Purpose:** Provide data for legislative redistricting
- **Frequency:** Every 10 years (2010, 2020, 2030)
- **Geography:** Down to **block level**
- **Content:** Total population, race, ethnicity, voting age population, housing units
- **Release:** ~12 months after Census Day

**Variable Prefixes:**
| Prefix | Content |
|--------|---------|
| P1 | Total Population |
| P2 | Hispanic/Latino by Race |
| P3 | Race for Population 18+ |
| P4 | Hispanic/Latino by Race 18+ |
| P5 | Group Quarters Population |
| H1 | Housing Occupancy |

**Key PL 94-171 Variables:**
```
P1_001N  - Total Population
P1_003N  - Population of One Race
P1_004N  - White alone
P1_005N  - Black or African American alone
P1_006N  - American Indian and Alaska Native alone
P1_007N  - Asian alone
P1_008N  - Native Hawaiian and Pacific Islander alone
P1_009N  - Some Other Race alone
P1_010N  - Two or More Races
P2_002N  - Hispanic or Latino
P2_003N  - Not Hispanic or Latino
H1_001N  - Total Housing Units
H1_002N  - Occupied Housing Units
H1_003N  - Vacant Housing Units
```

#### Demographic and Housing Characteristics (DHC)
- **Purpose:** Detailed demographic profiles
- **Geography:** Down to block (some items), block group, tract
- **Content:** Age, sex, race, ethnicity, household relationships, housing
- **Release:** ~18-24 months after Census Day

---

### 2. American Community Survey (ACS)

Ongoing survey providing detailed socioeconomic data between decennials.

#### ACS 1-Year Estimates
- **Population threshold:** 65,000+ only
- **Geography:** Nation, state, county, place, CBSA (large ones)
- **Timeframe:** Single calendar year
- **Use when:**
  - Analyzing recent changes
  - Large geographic areas
  - Annual comparisons needed

#### ACS 3-Year Estimates (Discontinued after 2013)
- **Population threshold:** 20,000+
- **Note:** No longer produced; use 5-year instead

#### ACS 5-Year Estimates
- **Population threshold:** All geographies
- **Geography:** Down to block group
- **Timeframe:** Rolling 5-year period (e.g., 2018-2022)
- **Use when:**
  - Small area analysis (tracts, block groups)
  - Detailed demographics needed
  - Stable estimates preferred over currency

**ACS Variable Prefixes:**
| Table Series | Content |
|--------------|---------|
| B01xxx | Age and Sex |
| B02xxx | Race |
| B03xxx | Hispanic/Latino Origin |
| B05xxx | Citizenship |
| B06xxx | Place of Birth |
| B07xxx | Migration |
| B08xxx | Commuting |
| B09xxx | Children |
| B11xxx | Households |
| B15xxx | Education |
| B17xxx | Poverty |
| B19xxx | Income |
| B23xxx | Employment |
| B25xxx | Housing |

**Common ACS Variables:**
```
B01001_001E  - Total Population
B01002_001E  - Median Age
B02001_002E  - White alone
B03001_003E  - Hispanic or Latino
B19013_001E  - Median Household Income
B19301_001E  - Per Capita Income
B15003_022E  - Bachelor's Degree
B17001_002E  - Below Poverty Level
B25001_001E  - Total Housing Units
B25077_001E  - Median Home Value
```

---

### 3. Population Estimates Program (PEP)

Annual population estimates between decennials.

- **Frequency:** Annual (July 1 reference date)
- **Geography:** Nation, state, county, place
- **Content:** Population, components of change (births, deaths, migration)
- **Use when:** Need population estimates for years between decennials

---

## Comparing Data Products

### Geographic Coverage

| Geography | PL 94-171 | DHC | ACS 5-Year | ACS 1-Year | PEP |
|-----------|:---------:|:---:|:----------:|:----------:|:---:|
| Nation | ✓ | ✓ | ✓ | ✓ | ✓ |
| Region | ✓ | ✓ | ✓ | ✓ | ✓ |
| State | ✓ | ✓ | ✓ | ✓ | ✓ |
| County | ✓ | ✓ | ✓ | ✓* | ✓ |
| Place | ✓ | ✓ | ✓ | ✓* | ✓* |
| Tract | ✓ | ✓ | ✓ | ✗ | ✗ |
| Block Group | ✓ | ✓ | ✓ | ✗ | ✗ |
| Block | ✓ | ✗ | ✗ | ✗ | ✗ |

*Only for areas with 65,000+ population

### Variable Coverage

| Topic | PL 94-171 | DHC | ACS |
|-------|:---------:|:---:|:---:|
| Total Population | ✓ | ✓ | ✓ |
| Race | ✓ | ✓ | ✓ |
| Hispanic/Latino | ✓ | ✓ | ✓ |
| Age | Basic | ✓ | ✓ |
| Sex | ✗ | ✓ | ✓ |
| Voting Age Pop | ✓ | ✓ | ✓ |
| Income | ✗ | ✗ | ✓ |
| Education | ✗ | ✗ | ✓ |
| Employment | ✗ | ✗ | ✓ |
| Poverty | ✗ | ✗ | ✓ |
| Housing Value | ✗ | ✗ | ✓ |
| Commuting | ✗ | ✗ | ✓ |

### Data Quality Comparison

| Metric | Decennial | ACS 5-Year | ACS 1-Year |
|--------|-----------|------------|------------|
| **Method** | Complete count | Sample (~3.5M/year) | Sample (~3.5M/year) |
| **Margin of Error** | None | Lower | Higher |
| **Currency** | Point-in-time | 5-year average | Current year |
| **Small Area Reliability** | Excellent | Good | Poor (N/A for small areas) |

---

## Time-Series Analysis Considerations

### Boundary Changes

Census boundaries change between decennials. Use crosswalks when comparing:

| Comparison | Crosswalk Needed? | Notes |
|------------|:-----------------:|-------|
| 2020 ACS vs 2020 PL | No | Same boundaries |
| 2020 ACS vs 2019 ACS | No | Same boundaries (both use 2020) |
| 2020 ACS vs 2015 ACS | **Yes** | 2015 uses 2010 boundaries |
| 2020 PL vs 2010 PL | **Yes** | Different decennial boundaries |

### ACS Period Overlap

ACS 5-year estimates represent **averages** over the period:

| Release Year | Period Covered | Midpoint |
|--------------|----------------|----------|
| 2022 | 2018-2022 | Mid-2020 |
| 2021 | 2017-2021 | Mid-2019 |
| 2020 | 2016-2020 | Mid-2018 |
| 2019 | 2015-2019 | Mid-2017 |

**Implication:** Adjacent ACS 5-year releases share 4 years of data. For independent samples, compare releases 5 years apart.

---

## siege_utilities Support

### Currently Supported

| Dataset | Function | Geography | Variables |
|---------|----------|-----------|-----------|
| ACS 5-Year | `get_demographics()` | State → Block Group | All B-tables |
| ACS 1-Year | `CensusAPIClient.fetch_data(dataset='acs1')` | State → Place | All B-tables |
| PL 94-171 | `CensusAPIClient.fetch_data(dataset='dec')` | State → Block* | P1, H1 |
| PEP | `CensusAPIClient.fetch_data(dataset='pep')` | Limited | Population |

*Block-level PL 94-171 requires direct download, not API

### Usage Examples

```python
from siege_utilities.geo import (
    CensusAPIClient,
    get_demographics,
    get_census_data_with_geometry,
    VARIABLE_GROUPS
)

# ACS 5-Year: Detailed demographics
df = get_demographics(
    state='California',
    geography='tract',
    year=2022,
    variables='income'
)

# PL 94-171: Redistricting data
client = CensusAPIClient()
df = client.fetch_data(
    variables='decennial_population',  # Uses P1 variables
    year=2020,
    dataset='dec',
    geography='tract',
    state_fips='06'
)

# ACS 1-Year: Recent data for large areas
df = client.fetch_data(
    variables='B19013_001E',
    year=2022,
    dataset='acs1',
    geography='county',
    state_fips='06'
)

# With geometry for mapping
gdf = get_census_data_with_geometry(
    year=2020,
    geography='tract',
    variables='income',
    state='California'
)
```

### Predefined Variable Groups

```python
from siege_utilities.geo import VARIABLE_GROUPS

# Available groups:
# - 'total_population': B01001_001E
# - 'demographics_basic': Population, sex, median age
# - 'race_ethnicity': Race categories + Hispanic
# - 'income': Median HH income, per capita, aggregate
# - 'education': Educational attainment
# - 'poverty': Poverty status
# - 'housing': Housing units, tenure, value, rent
# - 'decennial_population': P1 variables for PL 94-171
```

---

## Gaps and Planned Enhancements

### Current Limitations

1. **Block-level PL 94-171:** API doesn't support blocks; requires file download
2. **DHC Tables:** Not yet integrated
3. **Full PL variable set:** Only P1 implemented, missing P2-P5, H1

### Planned for Future Releases

| Feature | Priority | Issue |
|---------|----------|-------|
| Full PL 94-171 variable set | High | TBD |
| DHC file integration | Medium | TBD |
| Block-level data download | Medium | TBD |
| CVAP (Citizen Voting Age) | Medium | TBD |

---

## References

- [Census API Documentation](https://www.census.gov/data/developers/guidance.html)
- [ACS Data Users Handbook](https://www.census.gov/programs-surveys/acs/library/handbooks.html)
- [Understanding ACS Estimates](https://www.census.gov/programs-surveys/acs/guidance/estimates.html)
- [PL 94-171 Technical Documentation](https://www.census.gov/programs-surveys/decennial-census/about/rdo/summary-files.html)
- [Geographic Boundary Files](https://www.census.gov/geographies/mapping-files.html)

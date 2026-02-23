# Census Data Products Reference Guide

This guide provides a complete conceptual understanding of Census Bureau data products, how they relate to each other, when to use each, and how they integrate with `siege_utilities`.

---

## Table of Contents

1. [The Mental Model: How Census Data Works](#the-mental-model-how-census-data-works)
2. [The Three Pillars of Census Data](#the-three-pillars-of-census-data)
3. [Geographic Hierarchy: The Nesting Structure](#geographic-hierarchy-the-nesting-structure)
4. [Understanding Census Variables](#understanding-census-variables)
5. [Counts vs. Estimates: The Fundamental Distinction](#counts-vs-estimates-the-fundamental-distinction)
6. [When to Use What: Decision Framework](#when-to-use-what-decision-framework)
7. [Combining Datasets: What Works and What Doesn't](#combining-datasets-what-works-and-what-doesnt)
8. [Census Data Products Overview](#census-data-products-overview)
9. [siege_utilities Support](#siege_utilities-support)

---

## The Mental Model: How Census Data Works

The Census Bureau produces data through **two fundamentally different methods**:

### Complete Enumeration (Counting Everyone)
- **What:** The Decennial Census attempts to count every person in the United States
- **When:** Every 10 years (years ending in 0)
- **Result:** Exact counts with no margin of error
- **Products:** PL 94-171, DHC, Summary Files

### Sample Surveys (Asking a Representative Sample)
- **What:** The American Community Survey samples ~3.5 million households annually
- **When:** Continuously, with annual releases
- **Result:** Estimates with margins of error
- **Products:** ACS 1-Year, ACS 5-Year estimates

**Key Insight:** These two methods produce data that *look* similar but are fundamentally different. A "Total Population" from PL 94-171 is a count; a "Total Population" from ACS is an estimate. You cannot directly compare them.

---

## The Three Pillars of Census Data

All Census data products fall into three categories:

```
┌─────────────────────────────────────────────────────────────────────┐
│                        CENSUS DATA UNIVERSE                         │
├─────────────────────┬─────────────────────┬─────────────────────────┤
│   DECENNIAL CENSUS  │         ACS         │          PEP            │
│   (Every 10 years)  │   (Continuous)      │    (Annual estimates)   │
├─────────────────────┼─────────────────────┼─────────────────────────┤
│ • Complete count    │ • Sample survey     │ • Model-based           │
│ • Constitutional    │ • Detailed topics   │ • Between decennials    │
│ • Block-level       │ • Block group min   │ • County minimum        │
│ • Limited topics    │ • All topics        │ • Population only       │
├─────────────────────┼─────────────────────┼─────────────────────────┤
│ Products:           │ Products:           │ Products:               │
│ • PL 94-171         │ • 1-Year (65K+ pop) │ • Annual Estimates      │
│ • DHC               │ • 5-Year (all areas)│ • Components of Change  │
│ • Summary File 1    │ • PUMS              │ • Vintage series        │
└─────────────────────┴─────────────────────┴─────────────────────────┘
```

### How They Relate to Each Other

1. **PEP controls to Decennial:** Annual population estimates are "benchmarked" to the most recent Decennial count and adjusted forward using births, deaths, and migration data.

2. **ACS uses Decennial boundaries:** ACS data is tabulated using the geographic boundaries from the most recent Decennial Census. When boundaries change (e.g., 2010 → 2020), you need crosswalks.

3. **ACS and PL measure the same concepts differently:** Both have "Total Population" but:
   - PL: Count as of Census Day (April 1)
   - ACS: Estimate averaged over a period (calendar year or 5 years)

---

## Geographic Hierarchy: The Nesting Structure

Census geography is **hierarchical and nested**. Smaller units always fit perfectly inside larger ones:

```
                    NATION
                       │
                    REGIONS (4)
                       │
                   DIVISIONS (9)
                       │
                    STATES (50 + DC + territories)
                       │
         ┌─────────────┴─────────────┐
         │                           │
      COUNTIES                    PLACES
         │                    (cities, towns)
         │
    CENSUS TRACTS
    (1,200-8,000 pop)
         │
    BLOCK GROUPS
    (600-3,000 pop)
         │
       BLOCKS
    (0-many pop)
```

### Understanding GEOIDs

Every geographic unit has a unique identifier called a GEOID. The structure reveals the hierarchy:

```
GEOID: 060371234561234

  06     037    123456    1     234
  ──     ───    ──────    ─     ───
State  County   Tract    BG    Block

060371234561 = Block Group (12 digits)
06037123456  = Tract (11 digits)
06037        = County (5 digits)
06           = State (2 digits)
```

**Key Insight:** You can always derive parent geography from a child GEOID by truncating.

### Non-Nesting Geographies

Some geographies don't nest perfectly:

| Geography | Nests Within | Notes |
|-----------|--------------|-------|
| Congressional Districts | State | Change with redistricting |
| School Districts | State | May cross county lines |
| ZCTAs | None | Approximate ZIP codes |
| Urban Areas | None | Cross state/county lines |
| Metropolitan Areas | None | Cross state lines |

---

## Understanding Census Variables

### Variable Naming Conventions

Census variables follow predictable patterns:

**ACS Variables (B-tables):**
```
B19013_001E
│ │    │  └── E = Estimate (M = Margin of Error)
│ │    └───── 001 = Variable sequence number
│ └────────── 19013 = Table number
└──────────── B = Base table (C = Collapsed, S = Subject)
```

**Table Number Meaning:**
| Series | Topic |
|--------|-------|
| B01xxx | Age and Sex |
| B02xxx | Race |
| B03xxx | Hispanic Origin |
| B05xxx | Citizenship |
| B08xxx | Commuting |
| B15xxx | Education |
| B17xxx | Poverty |
| B19xxx | Income |
| B25xxx | Housing |

**PL 94-171 Variables:**
```
P1_001N
│  │  └── N = Count (there is no "E" for estimates)
│  └───── 001 = Variable sequence
└──────── P1 = Table (P = Population, H = Housing)
```

### The Same Concept Across Products

Here's how "Total Population" appears in different products:

| Product | Variable | What It Represents |
|---------|----------|-------------------|
| PL 94-171 | P1_001N | Count on April 1 of Census year |
| DHC | P1_001N | Same as PL (identical) |
| ACS 1-Year | B01001_001E | Estimate for single calendar year |
| ACS 5-Year | B01001_001E | Estimate averaged over 5 years |
| PEP | POPESTIMATE | Modeled estimate for July 1 |

**These are NOT directly comparable.** The values will differ because:
1. Different reference dates (April 1 vs July 1 vs year average)
2. Different methods (count vs sample vs model)
3. Different definitions (group quarters handling varies)

---

## Counts vs. Estimates: The Fundamental Distinction

### Decennial Census = Counts
- No margin of error
- Exact value (within Census's ability to count)
- Point-in-time (April 1)
- Available for all geographies including blocks

### ACS = Estimates
- Always has a margin of error (MOE)
- The "true" value falls within the confidence interval
- Represents a period average, not a point in time
- Available only down to block group level

### Working with Margins of Error

ACS estimates should ALWAYS be evaluated with their MOE:

```
Median Household Income: $65,000 ± $5,000
                              ↑        ↑
                          Estimate    MOE

90% Confidence Interval: $60,000 to $70,000
```

**Rules of Thumb:**
- MOE > 30% of estimate = Unreliable, use with caution
- Compare overlapping confidence intervals = Not statistically different
- Smaller geographies = Larger MOEs

---

## When to Use What: Decision Framework

### Decision Tree

```
START: What do you need?
         │
         ├── Official population count for legal purposes?
         │         → PL 94-171 (Decennial)
         │
         ├── Block-level data?
         │         → PL 94-171 only
         │
         ├── Race/ethnicity data?
         │         ├── At block level? → PL 94-171
         │         └── At tract or higher? → ACS or PL
         │
         ├── Income, education, poverty, commuting?
         │         → ACS (not in Decennial)
         │
         ├── Small area (tract/block group)?
         │         → ACS 5-Year
         │
         ├── Current year trends (large area 65K+ pop)?
         │         → ACS 1-Year
         │
         └── Population for year between decennials?
                   → PEP (or ACS 1-Year)
```

### Quick Reference: Which Dataset Should I Use?

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

## Combining Datasets: What Works and What Doesn't

### Safe Combinations

| Combination | Safe? | Notes |
|-------------|:-----:|-------|
| ACS 5-Year + TIGER shapefiles (same year) | ✓ | Standard mapping workflow |
| PL 94-171 + TIGER shapefiles (same year) | ✓ | Redistricting mapping |
| Multiple ACS 5-Year releases (5+ years apart) | ✓ | Non-overlapping periods |
| ACS variables from same release | ✓ | Same sample, same period |

### Problematic Combinations

| Combination | Problem | Solution |
|-------------|---------|----------|
| PL + ACS directly | Different methods, dates | Use as separate analyses |
| ACS 1-Year + 5-Year | Different periods | Pick one based on need |
| Adjacent ACS 5-Year releases | 4-year overlap | Use 5+ years apart |
| 2010 data + 2020 boundaries | Boundary changes | Apply crosswalk |

### The Crosswalk Problem

Census tract boundaries change every 10 years. Comparing 2010 and 2020 data requires:

```
2010 Data                      2020 Data
(2010 boundaries)              (2020 boundaries)
      │                              │
      └───────────┬──────────────────┘
                  │
           CROSSWALK FILE
     (maps old tracts → new tracts)
                  │
                  ▼
        NORMALIZED DATA
     (all in 2020 boundaries)
```

**What can change:**
- Tract split into multiple tracts (disaggregation needed)
- Multiple tracts merged (aggregation needed)
- Tract renumbered (simple rename)

---

## Understanding ACS Time Periods

This is one of the most confusing aspects of Census data. Here's how it works:

### ACS 1-Year vs 5-Year: What's the Difference?

```
         2018      2019      2020      2021      2022
          │         │         │         │         │
ACS 1-Year│         │         │         │         │
  2022    │         │         │         │    ████████
          │         │         │         │    (1 year)
          │         │         │         │
ACS 5-Year│         │         │         │
  2022    │████████████████████████████████████████│
          │        (5 years: 2018-2022)            │
```

| Characteristic | ACS 1-Year | ACS 5-Year |
|---------------|------------|------------|
| **Time period** | Single calendar year | Rolling 5-year period |
| **Sample size** | ~3.5 million households | ~17.5 million (5 × 3.5M) |
| **Precision** | Lower (higher MOE) | Higher (lower MOE) |
| **Currency** | More recent | Less recent (midpoint) |
| **Geography** | 65,000+ pop only | All areas |
| **Best for** | Trends in large areas | Small area analysis |

### The 5-Year Period Overlap Problem

Adjacent ACS 5-Year releases share 4 years of data:

```
2021 ACS 5-Year: [2017─2018─2019─2020─2021]
2022 ACS 5-Year:      [2018─2019─2020─2021─2022]
                       └──── 4 years shared ────┘
```

**Implication:** Changes between 2021 and 2022 ACS 5-Year are NOT statistically independent. For true comparisons:
- Use releases 5+ years apart (no overlap)
- Or use 1-Year estimates for annual trends

### Which Boundaries Apply When?

ACS data uses the **boundaries from the most recent Decennial Census**:

| ACS Release | Data Period | Boundaries Used |
|-------------|-------------|-----------------|
| 2019 | 2015-2019 | **2010** Census |
| 2020 | 2016-2020 | **2020** Census |
| 2021 | 2017-2021 | **2020** Census |
| 2022 | 2018-2022 | **2020** Census |

**Key Insight:** The 2020 ACS 5-Year was a transition year. Data from 2016-2019 was collected on 2010 boundaries but tabulated to 2020 boundaries. This can introduce small inconsistencies.

### Reference Date Comparison

| Product | Reference Date | What It Means |
|---------|---------------|---------------|
| Decennial (PL) | April 1, 2020 | Where people lived on Census Day |
| ACS 1-Year 2022 | Calendar 2022 | Average over the year |
| ACS 5-Year 2022 | 2018-2022 | Average over 5 years (midpoint ~mid-2020) |
| PEP 2022 | July 1, 2022 | Estimated population on that date |

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
| PL 94-171 (API) | `CensusAPIClient.fetch_data(dataset='dec')` | State → Tract | P1-P5, H1 |
| PL 94-171 (Files) | `get_pl_blocks()`, `get_pl_data()` | State → Block | P1-P5, H1 |
| PEP | `CensusAPIClient.fetch_data(dataset='pep')` | Limited | Population |
| TIGER/Line | `SpatialDataSource.get_*()` | All levels | Boundaries |
| Crosswalks | `get_crosswalk()`, `apply_crosswalk()` | Tract | 2010↔2020 |
| Time-Series | `get_longitudinal_data()` | All API levels | Any variable |

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

## PL 94-171 File Downloads

The Census API does not support block-level PL 94-171 data. Use the `PLFileDownloader` for direct file downloads:

### Block-Level Data

```python
from siege_utilities.geo import get_pl_blocks, get_pl_data, PLFileDownloader

# Get block-level redistricting data for a state
blocks = get_pl_blocks('California', year=2020)

# Get block-level data for specific county
la_blocks = get_pl_blocks('California', county='037', year=2020)

# Get tract-level PL data
tracts = get_pl_data('California', geography='tract', year=2020)

# Specify which tables to include
blocks = get_pl_blocks(
    'California',
    tables=['P1', 'P2', 'H1']  # Race, Hispanic, Housing
)
```

### Available PL Tables

| Table | Content | Variables |
|-------|---------|-----------|
| P1 | Race | Total population, race categories |
| P2 | Hispanic/Latino by Race | Hispanic origin crossed with race |
| P3 | Race (18+) | Voting age population by race |
| P4 | Hispanic/Latino by Race (18+) | VAP by Hispanic origin and race |
| P5 | Group Quarters | Institutional and non-institutional |
| H1 | Housing Occupancy | Total, occupied, vacant units |

### PLFileDownloader Class

```python
from siege_utilities.geo import PLFileDownloader

# Initialize downloader with caching
downloader = PLFileDownloader(cache_dir='~/.census_cache')

# Download and parse PL files
df = downloader.get_data(
    state='CA',
    year=2020,
    geography='block',
    tables=['P1', 'P2', 'P3', 'P4', 'P5', 'H1']
)

# List available files
files = downloader.list_available_files(state='CA', year=2020)
```

---

## Complete PL 94-171 Variable Groups

The `census_api_client` provides predefined variable groups for all PL tables:

```python
from siege_utilities.geo import VARIABLE_GROUPS, CensusAPIClient

# Available PL variable groups:
# - 'pl_p1_race': Total population and race (13 variables)
# - 'pl_p2_hispanic': Hispanic/Latino by race (26 variables)
# - 'pl_p3_race_18plus': Race for 18+ population (13 variables)
# - 'pl_p4_hispanic_18plus': Hispanic by race 18+ (26 variables)
# - 'pl_p5_group_quarters': Group quarters population (10 variables)
# - 'pl_h1_housing': Housing occupancy (3 variables)
# - 'pl_redistricting_core': Essential redistricting vars (8 variables)
# - 'pl_voting_age': Voting age population subset (7 variables)

# Get tract-level data with full PL support
client = CensusAPIClient()
df = client.fetch_data(
    variables='pl_redistricting_core',
    year=2020,
    dataset='dec',
    geography='tract',
    state_fips='06'
)
```

---

## Shape/Boundary Downloads

siege_utilities provides comprehensive support for downloading TIGER/Line shapefiles:

```python
from siege_utilities.geo import SpatialDataSource

# Initialize data source
source = SpatialDataSource()

# Available geographies:
# - states, counties, tracts, block_groups, blocks
# - congressional_districts (cd), places, zctas, vtds

# Download state boundaries
states = source.get_states(year=2020)

# Download county boundaries for a state
ca_counties = source.get_counties(state_fips='06', year=2020)

# Download tracts with Census data
ca_tracts = source.get_tracts(
    state_fips='06',
    year=2020,
    include_demographics=True
)

# Download blocks for a county
la_blocks = source.get_blocks(
    state_fips='06',
    county_fips='037',
    year=2020
)

# Congressional districts
cds = source.get_congressional_districts(year=2020)

# Voting tabulation districts
vtds = source.get_vtds(state_fips='06', year=2020)
```

---

## Boundary Crosswalks (2010-2020)

Census tract boundaries change between decennials. Use crosswalks to normalize data:

```python
from siege_utilities.geo import (
    get_crosswalk,
    apply_crosswalk,
    normalize_to_year,
    identify_boundary_changes
)

# Get crosswalk table
crosswalk = get_crosswalk(
    source_year=2010,
    target_year=2020,
    geography_level='tract',
    state_fips='06'
)

# Apply crosswalk to transform 2010 data to 2020 boundaries
df_2020 = apply_crosswalk(
    df=df_2010,
    source_year=2010,
    target_year=2020,
    weight_method='area'  # or 'population', 'housing'
)

# Normalize multiple years to common boundaries
df_normalized = normalize_to_year(
    df=df,
    year_column='year',
    target_year=2020
)

# Identify boundary changes
changes = identify_boundary_changes(
    crosswalk,
    include_unchanged=False
)
```

---

## Time-Series Analysis

Longitudinal analysis with automatic boundary normalization:

```python
from siege_utilities.geo import (
    get_longitudinal_data,
    calculate_change_metrics,
    classify_trends,
    TrendThresholds
)

# Fetch multi-year data with boundary normalization
df = get_longitudinal_data(
    variables='B19013_001E',  # Median household income
    years=[2010, 2015, 2020],
    geography='tract',
    state='California',
    target_year=2020  # Normalize all years to 2020 boundaries
)

# Calculate change metrics
df = calculate_change_metrics(
    df,
    value_column='B19013_001E',
    metrics=['absolute', 'percent', 'cagr']
)

# Classify trends
df = classify_trends(
    df,
    change_column='B19013_001E_pct_change',
    thresholds=TrendThresholds(
        rapid_growth=0.20,
        moderate_growth=0.05,
        moderate_decline=-0.05,
        rapid_decline=-0.20
    )
)
```

---

## Current Limitations

1. **DHC Tables:** Demographic and Housing Characteristics files not yet integrated
2. **CVAP Data:** Citizen Voting Age Population special tabulation not yet supported
3. **Historical Data:** PL file downloads currently support 2020 only (2010 planned)

---

## References

- [Census API Documentation](https://www.census.gov/data/developers/guidance.html)
- [ACS Data Users Handbook](https://www.census.gov/programs-surveys/acs/library/handbooks.html)
- [Understanding ACS Estimates](https://www.census.gov/programs-surveys/acs/guidance/estimates.html)
- [PL 94-171 Technical Documentation](https://www.census.gov/programs-surveys/decennial-census/about/rdo/summary-files.html)
- [Geographic Boundary Files](https://www.census.gov/geographies/mapping-files.html)

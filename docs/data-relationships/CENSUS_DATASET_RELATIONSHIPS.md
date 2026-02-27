# Census Dataset Relationships and Selection Guide

This document describes the Census dataset structures, relationships, and
selection logic used by `siege_utilities` to help users choose the right
data products for their analysis. It covers:

- Survey types and their characteristics
- Dataset compatibility and relationships
- Geography level support by dataset
- GEOID hierarchy and structure
- Predefined variable groups for the Census API
- Analysis pattern matching and dataset scoring
- Time series and roll-up support

---

## Survey Types

The Census Bureau publishes data through several distinct survey programs.
`siege_utilities` models these as the `SurveyType` enum
(`siege_utilities.geo.census_dataset_mapper`):

| Survey Type | Enum Value | Cadence | Description |
|---|---|---|---|
| Decennial Census | `decennial` | Every 10 years | 100% population count. Most reliable but limited variables. |
| ACS 1-Year | `acs_1yr` | Annual | Detailed socioeconomic data for geographies with 65,000+ people. |
| ACS 3-Year | `acs_3yr` | Annual (discontinued 2013) | Intermediate ACS product. No longer published. |
| ACS 5-Year | `acs_5yr` | Annual (rolling 5-year window) | Most geographically detailed ACS product. Available down to block group. |
| Economic Census | `census_business` | Every 5 years | Complete count of business establishments. |
| Population Estimates | `population_estimates` | Annual | Modeled intercensal population estimates. |
| Housing Estimates | `housing_estimates` | Annual | Modeled intercensal housing estimates. |

### Year Availability

These ranges are derived dynamically from `census_constants.py`
(using `_CURRENT_YEAR = datetime.now().year`):

| Program | Available Years | Notes |
|---|---|---|
| Decennial | 2000, 2010, 2020 | PL 94-171 redistricting data also available for 2010, 2020. `DECENNIAL_YEARS` filters to `<= _CURRENT_YEAR`. |
| ACS 5-Year | 2009-present | `ACS_AVAILABLE_YEARS = range(2009, _CURRENT_YEAR+1)`. Each release covers prior 5 calendar years (e.g., 2020 release = 2016-2020). |
| ACS 1-Year | 2005-present | Standard 2020 ACS 1-year was **not released** on api.census.gov due to COVID-19 data collection disruption. Experimental 2020 ACS 1-year products were released separately by Census (Nov 2021) with comparison caveats. |
| TIGER/Line | 2010-present | Boundary shapefiles, updated annually. `AVAILABLE_CENSUS_YEARS = range(2010, _CURRENT_YEAR+1)`. |

---

## Dataset Catalog

The `CensusDatasetMapper` maintains a catalog of concrete datasets. Each
has a defined set of geography levels, variables, reliability, and use-case
recommendations.

### 2020 Decennial Census (`decennial_2020`)

- **Time period:** 2020-04-01
- **Reliability:** HIGH
- **Geography support:** nation, state, county, place, tract, block group, block
- **Key variables:** total_population, race, ethnicity, age, sex, household_type, housing_tenure, vacancy_status
- **Best for:** Official population counts, redistricting, constitutional requirements, high-precision geography
- **Limitations:** Only basic demographic questions; limited socioeconomic data; 10-year intervals

### ACS 5-Year Estimates 2020 (`acs_5yr_2020`)

- **Time period:** 2016-2020 (rolling window)
- **Reliability:** MEDIUM
- **Geography support:** nation, state, county, place, tract, block group
- **Key variables:** income, education, employment, housing_value, rent, commute_time, health_insurance, poverty_status
- **Best for:** Detailed socioeconomic analysis, small geography analysis, trend analysis, policy planning
- **Limitations:** 5-year period may mask recent changes; smaller geographies have higher margins of error

### ACS 1-Year Estimates 2020 (`acs_1yr_2020`)

- **Time period:** 2020
- **Reliability:** LOW
- **Geography support:** nation, state, county, place, CBSA
- **Key variables:** Same as ACS 5-Year
- **Best for:** Recent trend analysis, large geography analysis, annual comparisons
- **Limitations:** Only geographies with 65,000+ population; higher margins of error

### Population Estimates 2023 (`population_estimates_2023`)

- **Time period:** 2023-07-01
- **Reliability:** ESTIMATED
- **Geography support:** nation, state, county, place, CBSA
- **Key variables:** total_population, age_sex_race, components_of_change, housing_units
- **Best for:** Current population estimates, annual trends, intercensal estimates
- **Limitations:** Modeled estimates (not direct counts); limited detail; modeling assumptions

### Economic Census 2017 (`economic_census_2017`)

- **Time period:** 2017
- **Reliability:** HIGH
- **Geography support:** nation, state, county, place, ZCTA
- **Key variables:** business_count, employment, payroll, sales_receipts, industry_classification, business_size
- **Best for:** Business analysis, economic development, industry analysis, employment studies
- **Limitations:** 5-year intervals; limited to business establishments

---

## Dataset Relationships

The `DatasetRelationship` structure captures how datasets complement, supplement,
or replace each other. Each relationship includes a compatibility score (0.0-1.0).

| Primary | Related | Type | Compatibility | When to Use Primary | When to Use Related |
|---|---|---|---|---|---|
| Decennial 2020 | ACS 5-Year 2020 | complements | 0.9 | Official population counts or basic demographics | Detailed socioeconomic data or recent trends |
| ACS 5-Year 2020 | ACS 1-Year 2020 | supplements | 0.8 | Stable estimates for small geographies | Recent data for large geographies |
| Decennial 2020 | Pop. Estimates 2023 | replaces | 0.7 | Official 2020 counts | Current population estimates |
| Economic Census 2017 | ACS 5-Year 2020 | complements | 0.6 | Business establishment data | Demographic context for business analysis |

### Relationship Types

- **complements**: Datasets cover different aspects of the same topic. Use together for comprehensive analysis.
- **supplements**: One dataset fills gaps in the other. Use the supplement when the primary doesn't cover your requirements.
- **replaces**: The related dataset provides updated versions of the primary. Use the more recent one when recency matters.

---

## Geography Levels

The Census Bureau publishes data at different geographic resolutions. Not all
datasets are available at all levels. The canonical level definitions live in
`census_constants.CANONICAL_GEOGRAPHIC_LEVELS`.

### Canonical Levels and GEOID Structure

| Level | GEOID Length | GEOID Example | Components | Aliases |
|---|---|---|---|---|
| nation | 1 | `1` | — | us, national |
| region | 1 | `1` | — | — |
| division | 1 | `1` | — | — |
| state | 2 | `06` | SS | — |
| county | 5 | `06037` | SS+CCC | — |
| cousub | 10 | `0603790100` | SS+CCC+SSSSS | county_subdivision |
| place | 7 | `0644000` | SS+PPPPP | — |
| cd | 4 | `0614` | SS+DD | congressional_district |
| sldu | 5 | `06001` | SS+DDD | state_legislative_upper, state_legislative_district |
| sldl | 5 | `06001` | SS+DDD | state_legislative_lower |
| tract | 11 | `06037101100` | SS+CCC+TTTTTT | — |
| block_group | 12 | `060371011001` | SS+CCC+TTTTTT+G | bg, blockgroup |
| block | 15 | `060371011001001` | SS+CCC+TTTTTT+BBBB | tabblock |
| zcta | 5 | `90210` | ZZZZZ | zip_code, zcta5, zipcode |
| cbsa | 5 | `31080` | MMMMM | — |
| puma | 7 | `0600100` | SS+PPPPP | — |
| vtd | 6 | `060370` | SS+CCCC (varies) | voting_district |

### GEOID Hierarchy (Nesting)

GEOIDs are hierarchical. A child GEOID always starts with its parent's GEOID:

```
nation
 └─ state (2 digits)
     └─ county (5 digits = state + 3)
         └─ tract (11 digits = county + 6)
             └─ block_group (12 digits = tract + 1)
                 └─ block (15 digits = block_group + 3)
```

The `GEOID_PREFIX_LENGTHS` dictionary (used by `DemographicRollupService`)
encodes this nesting for roll-up aggregation:

```python
GEOID_PREFIX_LENGTHS = {
    "state": 2,
    "county": 5,
    "tract": 11,
    "block_group": 12,
    "block": 15,
}
```

Rolling up from block group to county means grouping by the first 5 digits
of each block group's 12-digit GEOID.

### Dataset-to-Geography Availability Matrix

| Geography | Decennial | ACS 5-Year | ACS 1-Year | Pop. Estimates | Economic Census |
|---|---|---|---|---|---|
| Nation | yes | yes | yes | yes | yes |
| State | yes | yes | yes | yes | yes |
| County | yes | yes | yes | yes | yes |
| Place | yes | yes | yes | yes | yes |
| CBSA | — | — | yes | yes | — |
| ZCTA | — | — | — | — | yes |
| Tract | yes | yes | — | — | — |
| Block Group | yes | yes | — | — | — |
| Block | yes | — | — | — | — |

---

## Predefined Variable Groups

The `CensusAPIClient` defines `VARIABLE_GROUPS` — curated sets of Census
API variable codes organized by topic. Use these as shorthand when fetching
data:

```python
client = CensusAPIClient()
df = client.fetch_data(variables='income', year=2020, geography='tract', state_fips='06')
```

### ACS Variable Groups

| Group Name | Table(s) | Variables | Description |
|---|---|---|---|
| `total_population` | B01001 | 1 variable | Total population count |
| `demographics_basic` | B01001, B01002 | 4 variables | Total pop, male, female, median age |
| `race_ethnicity` | B02001, B03001 | 9 variables | Race categories + Hispanic/Latino |
| `income` | B19013, B19301, B19025 | 3 variables | Median HH income, per capita, aggregate |
| `education` | B15003 | 8 variables | Educational attainment for pop 25+ |
| `poverty` | B17001 | 2 variables | Population below poverty level |
| `housing` | B25001-B25077 | 7 variables | Housing units, tenure, value, rent |

### PL 94-171 Redistricting Variable Groups

| Group Name | Table(s) | Variables | Description |
|---|---|---|---|
| `decennial_population` | P1 | 7 variables | Basic race counts from decennial |
| `pl_p1_race` | P1 | 11 variables | Complete race table |
| `pl_p2_hispanic` | P2 | 11 variables | Hispanic/Latino by race |
| `pl_p3_race_18plus` | P3 | 9 variables | Race for voting-age population |
| `pl_p4_hispanic_18plus` | P4 | 11 variables | Hispanic/Latino by race, 18+ |
| `pl_p5_group_quarters` | P5 | 10 variables | Group quarters by type |
| `pl_h1_housing` | H1 | 3 variables | Housing occupancy |
| `pl_redistricting_core` | P1-P4, H1 | 17 variables | Combined core redistricting set |

### Default Tables for Variable Metadata Loading

The `CensusAPIClient.VARIABLE_GROUPS` dictionary (in
`siege_utilities.geo.census_api_client`) defines curated sets of commonly-used
ACS table variables. The following tables are referenced across variable groups:

| Table ID | Subject |
|---|---|
| B01001 | Sex by Age |
| B01003 | Total Population |
| B02001 | Race |
| B03003 | Hispanic Origin |
| B19013 | Median Household Income |
| B19001 | Household Income (distribution) |
| B25001 | Housing Units |
| B25003 | Tenure |
| B15003 | Educational Attainment |

---

## Analysis Pattern Matching

The `CensusDataSelector` uses predefined analysis patterns to recommend
datasets based on what you're studying. Each pattern specifies preferred
datasets, relevant variables, geography preferences, time sensitivity,
and reliability requirements.

### Analysis Patterns

| Analysis Type | Primary Datasets | Geography Preferences | Time Sensitivity | Reliability Req. |
|---|---|---|---|---|
| demographics | ACS 5-Year, Decennial | tract, block_group, county | medium | medium |
| housing | ACS 5-Year, Decennial | tract, block_group, county | medium | medium |
| business | Economic Census, ACS 5-Year | county, place, ZCTA | low | high |
| transportation | ACS 5-Year | tract, county | medium | medium |
| education | ACS 5-Year | tract, county | medium | medium |
| health | ACS 5-Year | tract, county | medium | medium |
| poverty | ACS 5-Year | tract, county | medium | medium |

### Suitability Scoring

When you request a dataset recommendation, the selector scores each candidate
on a 0-5 scale:

| Score Component | Points | Condition |
|---|---|---|
| Geography match | +2.0 | Dataset supports the requested geography level |
| Primary dataset bonus | +1.5 | Dataset is in the pattern's primary list |
| Reliability match | +1.0 | Dataset meets or exceeds reliability requirement |
| Time period recency | +0.2 to +1.0 | Within 5 years (+0.2), 3 years (+0.5), or 1 year (+1.0) |
| Variable coverage | up to +1.0 | Proportion of requested variables available |
| Geography preference | +1.0 | Geography level is in pattern's preferred list |

**Score interpretation:** 0-2.0 (poor), 2.1-3.0 (moderate), 3.1-4.0 (good), 4.1-5.0 (excellent).

---

## Data Reliability Levels

Each dataset carries a reliability classification:

| Level | Value | Description | Examples |
|---|---|---|---|
| HIGH | `high` | Most reliable; complete counts or large samples | Decennial Census, Economic Census |
| MEDIUM | `medium` | Moderately reliable; sample-based with MOE | ACS 5-Year estimates |
| LOW | `low` | Less reliable; higher margins of error | ACS 1-Year estimates |
| ESTIMATED | `estimated` | Modeled estimates, not direct observation | Population Estimates Program |

---

## Time Series and Roll-Up Support

### Time Series (`TimeseriesService`)

The `TimeseriesService` fetches `DemographicSnapshot` records across
multiple years and computes:

- **CAGR** (Compound Annual Growth Rate): `(end/start)^(1/n) - 1`
- **Standard deviation** across the time series
- **Trend direction**: increasing, decreasing, or stable (based on linear fit)

Valid dataset/year combinations for time series:

| Dataset | Typical Year Range | Geography Levels |
|---|---|---|
| acs5 | 2009-present (annual, per `ACS_AVAILABLE_YEARS`) | state, county, tract, block_group |
| acs1 | 2005-present (standard 2020 not released; experimental only) | state, county, place, CBSA |
| decennial | 2000, 2010, 2020 (per `DECENNIAL_YEARS`) | state through block |

### Demographic Roll-Up (`DemographicRollupService`)

The `DemographicRollupService` aggregates data from finer to coarser
geographies using GEOID prefix matching. Supported operations:

| Operation | Description | Use Case |
|---|---|---|
| `sum` | Sum values across child geographies | Extensive variables (population, counts) |
| `avg` | Simple average | General-purpose averaging |
| `weighted_avg` | Population-weighted average | Intensive variables (median income, rates) |

**Valid roll-up paths** (source → target):

```
block → block_group → tract → county → state
```

Any source level can roll up to any coarser target level via GEOID prefix truncation.

---

## Source Modules

| Module | What It Provides |
|---|---|
| `siege_utilities.config.census_constants` | Canonical geography levels, FIPS codes, TIGER patterns, year ranges |
| `siege_utilities.geo.geoid_utils` | GEOID construction, validation, normalization, slug conversion |
| `siege_utilities.geo.census_dataset_mapper` | Dataset catalog, relationships, comparison, selection guide |
| `siege_utilities.geo.census_data_selector` | Analysis patterns, suitability scoring, compatibility matrix |
| `siege_utilities.geo.census_api_client` | Variable groups, API fetch, caching (parquet/Django) |
| `siege_utilities.geo.django.services.timeseries_service` | Time series population and statistics |
| `siege_utilities.geo.django.services.rollup_service` | Demographic aggregation via GEOID hierarchy |

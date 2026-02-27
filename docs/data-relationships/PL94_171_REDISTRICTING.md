# PL 94-171 Redistricting Data

Public Law 94-171 requires the Census Bureau to provide state legislatures
with population data for redistricting. This is the earliest detailed
demographic release after each decennial census, available at block level.

---

## What PL 94-171 Contains

PL 94-171 provides **55 variables** across 6 tables:

### P1: Race (Total Population)

| Variable | Description |
|---|---|
| P1_001N | Total population |
| P1_002N | Population of one race |
| P1_003N | White alone |
| P1_004N | Black or African American alone |
| P1_005N | American Indian and Alaska Native alone |
| P1_006N | Asian alone |
| P1_007N | Native Hawaiian and Other Pacific Islander alone |
| P1_008N | Some Other Race alone |
| P1_009N | Two or more races |
| P1_010N | Two races including Some Other Race |
| P1_011N | Two races excluding Some Other Race, and three or more races |

### P2: Hispanic or Latino by Race

| Variable | Description |
|---|---|
| P2_001N | Total population |
| P2_002N | Hispanic or Latino |
| P2_003N | Not Hispanic or Latino |
| P2_004N | Not Hispanic: Population of one race |
| P2_005N | Not Hispanic: White alone |
| P2_006N | Not Hispanic: Black or African American alone |
| P2_007N | Not Hispanic: American Indian and Alaska Native alone |
| P2_008N | Not Hispanic: Asian alone |
| P2_009N | Not Hispanic: Native Hawaiian and Other Pacific Islander alone |
| P2_010N | Not Hispanic: Some Other Race alone |
| P2_011N | Not Hispanic: Two or more races |

### P3: Race for Population 18 Years and Over

| Variable | Description |
|---|---|
| P3_001N | Total population 18+ |
| P3_002N | Population of one race |
| P3_003N | White alone |
| P3_004N | Black or African American alone |
| P3_005N | American Indian and Alaska Native alone |
| P3_006N | Asian alone |
| P3_007N | Native Hawaiian and Other Pacific Islander alone |
| P3_008N | Some Other Race alone |
| P3_009N | Two or more races |

### P4: Hispanic or Latino by Race (18+)

| Variable | Description |
|---|---|
| P4_001N | Total population 18+ |
| P4_002N | Hispanic or Latino |
| P4_003N | Not Hispanic or Latino |
| P4_004N | Not Hispanic: Population of one race |
| P4_005N | Not Hispanic: White alone |
| P4_006N | Not Hispanic: Black or African American alone |
| P4_007N | Not Hispanic: American Indian and Alaska Native alone |
| P4_008N | Not Hispanic: Asian alone |
| P4_009N | Not Hispanic: Native Hawaiian and Other Pacific Islander alone |
| P4_010N | Not Hispanic: Some Other Race alone |
| P4_011N | Not Hispanic: Two or more races |

### P5: Group Quarters Population by Type

| Variable | Description |
|---|---|
| P5_001N | Total group quarters population |
| P5_002N | Institutionalized population |
| P5_003N | Correctional facilities for adults |
| P5_004N | Juvenile facilities |
| P5_005N | Nursing facilities / Skilled-nursing facilities |
| P5_006N | Other institutional facilities |
| P5_007N | Noninstitutionalized population |
| P5_008N | College/University student housing |
| P5_009N | Military quarters |
| P5_010N | Other noninstitutional facilities |

### H1: Housing Occupancy

| Variable | Description |
|---|---|
| H1_001N | Total housing units |
| H1_002N | Occupied housing units |
| H1_003N | Vacant housing units |

---

## Geography Availability

PL 94-171 is available at every Census summary level:

| Level | GEOID Length | Example |
|---|---|---|
| State | 2 | `06` |
| County | 5 | `06037` |
| Tract | 11 | `06037101100` |
| Block Group | 12 | `060371011001` |
| **Block** | **15** | **`060371011001001`** |
| Place | 7 | `0644000` |
| VTD | 8 | `06037001` |
| CD | 4 | `0614` |
| SLDU / SLDL | 5 | `06001` |

Block-level data is what makes PL 94-171 unique — it is the **only**
Census product with demographic data at the block level.

---

## Data Distribution Formats

### Census API

```
GET https://api.census.gov/data/2020/dec/pl?get=P1_001N,P2_002N&for=block:*&in=state:06&in=county:037
```

- Available for 2010 and 2020
- Subject to the Census API rate limit
- Best for targeted queries (specific state/county)

### Bulk Files

The Census Bureau distributes PL data as pipe-delimited text files:

```
https://www2.census.gov/programs-surveys/decennial/2020/data/01-Redistricting_File--PL_94-171/
```

- One ZIP per state
- Contains geographic header file + data segments
- Two formats: legacy fixed-width and pipe-delimited
- Best for full-state or nationwide loads

The existing `pl_downloader.py` module handles downloading and parsing
these bulk files with parquet caching (30-day TTL).

---

## How PL Data Fits the siege_utilities Model

PL data is stored in `DemographicSnapshot` with `dataset="dec_pl"`:

```python
from django.contrib.contenttypes.models import ContentType
from siege_utilities.geo.django.models import Block
from siege_utilities.geo.django.models.demographics import DemographicSnapshot

DemographicSnapshot.objects.create(
    content_type=ContentType.objects.get_for_model(Block),
    object_id="060371011001001",
    year=2020,
    dataset="dec_pl",
    values={
        "P1_001N": 4521,
        "P2_002N": 1830,
        "P2_005N": 1250,
        "P3_001N": 3200,
        "H1_001N": 1800,
        "H1_002N": 1650,
        "H1_003N": 150,
    },
    total_population=4521,
)
```

### Roll-Up Aggregation

Block-level PL data can be aggregated to coarser geographies using
`DemographicRollupService`, which uses GEOID prefix matching:

```
Block (15 digits) → BlockGroup (12) → Tract (11) → County (5) → State (2)
```

All PL variables are **extensive** (counts, not rates), so simple
summation is the correct aggregation operation.

### Time Series

PL data from 2010 and 2020 can feed into `DemographicTimeSeries` for
decadal change analysis:

```python
DemographicTimeSeries(
    content_type=ContentType.objects.get_for_model(Tract),
    object_id="06037101100",
    variable_code="P1_001N",
    dataset="dec_pl",
    start_year=2010,
    end_year=2020,
    years=[2010, 2020],
    values=[4200, 4521],
    cagr=0.0074,
    trend_direction="increasing",
)
```

### Crosswalk Integration

Since block boundaries change between decennial censuses, PL data from
different years may not align geographically. Use `TemporalCrosswalk` to
map 2010 blocks to 2020 blocks with population-weighted allocation:

```python
TemporalCrosswalk.objects.filter(
    source_type="block",
    source_vintage_year=2010,
    target_vintage_year=2020,
)
```

---

## Predefined Variable Groups

The `CensusAPIClient` provides curated variable groups for PL data:

| Group | Table(s) | Count | Use Case |
|---|---|---|---|
| `pl_p1_race` | P1 | 11 | Race breakdown |
| `pl_p2_hispanic` | P2 | 11 | Hispanic/Latino by race |
| `pl_p3_race_18plus` | P3 | 9 | Voting-age race breakdown |
| `pl_p4_hispanic_18plus` | P4 | 11 | Voting-age Hispanic by race |
| `pl_p5_group_quarters` | P5 | 10 | Institutional population |
| `pl_h1_housing` | H1 | 3 | Housing occupancy |
| `pl_redistricting_core` | P1-P4, H1 | 17 | Combined core redistricting set |

---

## Common Use Cases

**Redistricting:** Block-level population by race and voting age is the
foundation of legislative redistricting. PL data is used with
`TractCDIntersection` and `VTDCDIntersection` to analyze how proposed
district boundaries divide communities.

**Voting Rights Act compliance:** Section 2 analysis requires
voting-age population by race at fine geography. PL tables P3 and P4
provide this at block level.

**Demographic change analysis:** Comparing 2010 and 2020 PL data (via
`TemporalCrosswalk` for boundary alignment) shows population shifts
at the most granular level available.

**Election analysis:** Combining PL demographic data with VTD election
results (via `VTDCDIntersection`) enables ecological inference and
racially polarized voting analysis.

---

## Related Tickets

- [su#162](https://github.com/siege-analytics/siege_utilities/issues/162) — Integrate PL 94-171 redistricting data files into Census pipeline
- [su#161](https://github.com/siege-analytics/siege_utilities/issues/161) — Consolidate scattered Census dataset structures into unified registry

# Multi-Source Spatial Data Tabulation Guide

This document covers the theory and practice of joining data from multiple
geographic data sources — Census ACS, NCES EDGE, NLRB, and RDH — at shared
geographic levels. It is the companion reference for
`notebooks/20_Multi_Source_Spatial_Tabulation.ipynb`.

The two themes that dominate cross-source tabulation are **margin of error (MoE)
propagation** and **scale mismatch**. Getting either wrong can produce results
that look precise but are statistically meaningless.

---

## Table of Contents

1. [Data Source Inventory](#1-data-source-inventory)
2. [Join Strategy Reference](#2-join-strategy-reference)
3. [Margin of Error Propagation](#3-margin-of-error-propagation)
4. [Scale and the Modifiable Areal Unit Problem](#4-scale-and-the-modifiable-areal-unit-problem)
5. [Areal Interpolation](#5-areal-interpolation)
6. [Temporal Alignment](#6-temporal-alignment)
7. [Practical Recipes](#7-practical-recipes)
8. [When Not to Tabulate](#8-when-not-to-tabulate)

---

## 1. Data Source Inventory

| Source | Module | Native Geography | Update Cadence | Error Model |
|--------|--------|-------------------|---------------|-------------|
| Census ACS 5-year | `geo.census_api_client` | Block group → State | Annual (rolling 5-year window) | Sampling MoE on every estimate |
| Census ACS 1-year | `geo.census_api_client` | County → State (pop ≥ 65k) | Annual | Wider MoE than 5-year |
| Census Decennial | `geo.census_api_client` | Block → State | Every 10 years | Complete enumeration (no MoE) |
| Census TIGER | `geo.spatial_data` | Block → State | Annual | Boundary precision ± meters |
| NCES EDGE | `geo.nces_download` | School point / Locale polygon | Annual (school year) | Geocoding accuracy varies |
| NLRB | `geo.django.services.nlrb_service` | State → Region | Static (changes rarely) | No error — administrative definition |
| RDH | `data.redistricting_data_hub` | Precinct / District | Per redistricting cycle | Boundary digitization error |

### Key distinction: estimates vs. counts vs. boundaries

- **Estimates** (ACS): Carry margins of error. Every derived quantity must propagate MoE.
- **Counts** (Decennial, NCES school counts): Exact within their universe. No MoE, but
  universe definitions differ (e.g., NCES counts public schools only).
- **Boundaries** (TIGER, NCES locale, RDH districts): Geometric. Error comes from
  digitization precision and vintage mismatch, not sampling.

---

## 2. Join Strategy Reference

### 2.1 GEOID Join (exact key match)

**When to use**: Both datasets share the same Census geography (e.g., county GEOID).

```
Census ACS county data  ──GEOID──▶  Census TIGER county boundaries
```

This is the simplest and most reliable join. No spatial operations needed. The only
risk is **vintage mismatch** — a 2020-vintage GEOID may not exist in 2010 boundaries
(tracts split, merged, or renumbered).

**MoE**: Preserved exactly. No additional error from the join itself.

### 2.2 FIPS Lookup (attribute join)

**When to use**: One dataset uses state-level identifiers (NLRB regions).

```
Census state population  ──State FIPS──▶  NLRB_REGIONS dict  ──▶  Region aggregation
```

This is a many-to-one join. Multiple states roll up into one NLRB region.

**MoE**: For population sums across states:
`MoE_region = sqrt(sum(MoE_state_i^2))`

**Caveat**: Some states appear in multiple NLRB regions (e.g., NY in regions 2, 3, 29).
The NLRB divides at the county level, but public data only provides state-level
assignments. You must either pick a primary region (lowest number) or accept
double-counting.

### 2.3 Spatial Join — Point in Polygon

**When to use**: Point data (schools) needs to be assigned to area data (districts, counties).

```
NCES school points  ──gpd.sjoin(predicate='within')──▶  RDH district polygons
```

**MoE**: The join itself introduces no statistical error, but:
- School geocoding accuracy varies (NCES reports accuracy codes)
- Points near polygon boundaries may be misassigned
- Slivers and topology errors in the polygon layer cause dropped or duplicated points

**Best practice**: Use `predicate='within'` for strict containment. Use `predicate='intersects'`
only when you want boundary-touching points included.

### 2.4 Spatial Join — Centroid in Polygon

**When to use**: Assigning areas (counties) to other areas (districts) when one
area is much smaller than the other.

```
County centroids  ──gpd.sjoin(predicate='within')──▶  Congressional district polygons
```

This is an approximation. A county whose centroid falls in District A is assigned
entirely to District A, even if part of the county is in District B.

**When this fails**: When the source unit (county) is large relative to the target
unit (district). Fairfax County, VA spans parts of multiple congressional districts.
Its centroid lands in one, so the others get zero Fairfax population — badly wrong.

**MoE**: The geometric approximation error dominates. MoE from ACS is secondary.

### 2.5 Spatial Overlay — Area-Weighted Interpolation

**When to use**: Assigning area data (tract demographics) to non-nesting areas
(districts) with population weighting.

```
Census tract demographics  ──demographic_profile()──▶  District-level aggregations
```

This is the `demographic_profile()` function in `redistricting_data_hub.py`.
It computes the geometric intersection of each tract with each district, then
allocates tract population proportionally by intersection area.

**MoE**: Two independent error sources compound:
1. ACS sampling error (MoE on the tract estimates)
2. Areal interpolation error (the assumption that population is uniformly
   distributed within each tract)

See §5 for detailed treatment.

---

## 3. Margin of Error Propagation

### 3.1 Background: What ACS MoE Means

The Census Bureau reports ACS estimates with a 90% confidence margin of error.
For an estimate `E` with margin `M`, the true value falls in `[E - M, E + M]`
with 90% confidence.

The standard error is: `SE = M / 1.645`

The coefficient of variation (CV) is: `CV = (SE / E) * 100`

**Reliability thresholds** (Census Bureau guidance):

| CV | Reliability | Action |
|----|-------------|--------|
| < 12% | High | Use freely |
| 12–40% | Medium | Use with caution, report CV |
| > 40% | Low | Suppress or flag — too noisy to be useful |

### 3.2 Propagation Rules

#### Rule 1: Sum of estimates

When summing ACS estimates (e.g., total population across tracts in a locale category):

```
E_sum = E_1 + E_2 + ... + E_n
MoE_sum = sqrt(MoE_1^2 + MoE_2^2 + ... + MoE_n^2)
```

This assumes independence between the estimates. For ACS data at different
geographic levels, this is approximately true. For variables from the same
table at the same geography, the estimates may be correlated and this formula
is an approximation.

**Example** (NB20 Part 3 — tract populations by locale):

```python
locale_pop = tracts.groupby("locale_category").agg(
    total_pop=("total_pop", "sum"),
    total_pop_moe=("total_pop_moe", lambda x: np.sqrt((x**2).sum())),
)
```

#### Rule 2: Difference of estimates

```
E_diff = E_1 - E_2
MoE_diff = sqrt(MoE_1^2 + MoE_2^2)
```

Same formula as sums. This is critical for change-over-time analysis.

**Caveat**: If the difference is small relative to its MoE, it is not
statistically significant. Test: `|E_diff| > MoE_diff`.

#### Rule 3: Proportion (ratio where numerator is subset of denominator)

```
p = X / Y
SE_p = (1/Y) * sqrt(SE_X^2 - p^2 * SE_Y^2)
```

If the term under the square root is negative (can happen when X ≈ Y),
use the approximation:

```
SE_p = (1/Y) * sqrt(SE_X^2 + p^2 * SE_Y^2)
```

**Example**: Poverty rate = population in poverty / total population.

#### Rule 4: Product of an estimate and a constant

```
E_product = k * E
MoE_product = |k| * MoE
```

No additional error from the constant.

#### Rule 5: Median (special case)

Medians (e.g., median household income) **cannot be aggregated by summing or averaging**.
The median of medians is not the overall median. The Census Bureau provides
MoE for each individual median estimate, but there is no closed-form formula
for the MoE of an aggregate median.

**Practical approach for NB20**: When grouping tracts by locale category, we
report `mean(median_income)` as a summary statistic and label it clearly as
"average of tract-level medians" — not the true median for the locale category.

### 3.3 MoE in Cross-Source Joins

When joining Census ACS data to non-Census data (NCES, NLRB, RDH), the
non-Census data typically has no sampling error. The MoE comes entirely
from the Census side, propagated through whatever aggregation the join requires.

| Join Type | MoE Source | Propagation |
|-----------|-----------|-------------|
| GEOID join | Census only | No change — 1:1 join |
| FIPS lookup + sum | Census only | Root-sum-of-squares |
| Spatial join (point in polygon) | Census only | Root-sum-of-squares for sums |
| Spatial overlay | Census + interpolation error | See §5 |

### 3.4 When MoE Makes Results Unusable

Small-area ACS estimates (block groups, small tracts) often have CVs above 40%.
When you aggregate these to a custom geography (locale category, congressional
district), the aggregation reduces CV (more data points → tighter estimates),
but not always enough.

**Rule of thumb**: If your aggregation zone contains fewer than ~20 tracts or
~50,000 population, check the CV before reporting the result.

```python
# Check CV for aggregated estimates
se = moe / 1.645
cv = (se / estimate) * 100
if cv > 40:
    warnings.warn(f"CV={cv:.0f}% — estimate is unreliable")
```

---

## 4. Scale and the Modifiable Areal Unit Problem

### 4.1 What is MAUP?

The Modifiable Areal Unit Problem (MAUP) states that the results of spatial
analysis depend on how you draw the boundaries of your analysis zones.
Aggregate the same data into different zones and you get different results.

This is not a bug — it is an inherent property of spatial data. But it means
that cross-source tabulations produce results that are **contingent on the
chosen geography**, not universal truths.

### 4.2 Scale Effects in NB20

Each data source in NB20 has a native scale:

| Source | Native Scale | Resolution |
|--------|-------------|------------|
| Census ACS | Tract (~4,000 people) | High |
| NCES locale | Locale territory (12 types nationally) | Very low |
| NLRB | Region (~6–12 states) | Very low |
| RDH district | Congressional district (~760k people) | Medium |
| County | County (~100k–10M people) | Medium |

When you cross-tabulate, the result inherits the **coarsest resolution**
of any participating source. Census tracts crossed with NLRB regions
produces NLRB-region-level results, not tract-level results.

### 4.3 The Ecological Fallacy

Cross-source tabulation invites ecological fallacy: inferring individual-level
relationships from aggregate data.

**Example**: If a congressional district has high median income *and* many
rural schools, you cannot conclude that rural areas in that district are wealthy.
The income may come from suburban tracts while the schools are in poor rural tracts.

**Mitigation**: Always tabulate at the finest shared geography. If you need
tract-level insights, don't aggregate to district level and then drill back down.

### 4.4 Scale Mismatch Warnings

The unified county-level tabulation in NB20 Part 7 involves multiple
scale mismatches:

| Column | Source Scale | County Scale | Mismatch Severity |
|--------|-------------|-------------|-------------------|
| `total_pop` | Exact (Census) | Native | None |
| `median_income` | Tract estimate | County aggregate | Medium — average of medians |
| `school_count` | School point | Count in county | None — exact count |
| `nlrb_region` | State | All counties same | None — uniform within state |
| `congressional_district` | District | Centroid approximation | **High** — counties split across districts |

The `congressional_district` column is the weakest link. For states with
many small counties (VA has 133), most counties fit within a single district
and the centroid approximation works. For states with large counties (CA,
TX), it breaks badly.

---

## 5. Areal Interpolation

### 5.1 The Problem

Census tracts and congressional districts have independent boundaries.
A tract may overlap two districts. To assign tract demographics to districts,
you must *interpolate* — split the tract's population between the districts
proportionally.

### 5.2 Area-Weighted Interpolation (AWI)

The simplest approach assumes population is uniformly distributed within
each tract:

```
pop_district_from_tract = pop_tract * (area_intersection / area_tract)
```

`demographic_profile()` in `redistricting_data_hub.py` uses this approach.

**When it works well**: Dense urban tracts where population is roughly uniform.

**When it fails**: Large rural tracts where the population clusters in a town
covering 1% of the tract's area. AWI would assign 99% of the population to
whichever district contains the empty land.

### 5.3 Dasymetric Refinement

A better approach uses ancillary data (land use, building footprints, nighttime
lights) to weight the interpolation. This is not currently implemented in
`siege_utilities` but is a known enhancement path.

### 5.4 Quantifying Interpolation Error

There is no closed-form formula for areal interpolation error. Empirical
studies suggest:

| Condition | Typical Error |
|-----------|---------------|
| Small source zones (tracts) → large targets (districts) | 2–5% |
| Large source zones (counties) → small targets (tracts) | 10–30% |
| Rural areas with clustered population | 15–50% |
| Dense urban areas | 1–3% |

**Practical guidance**: If more than 20% of your source zone area lies
outside the target zone, flag the result. If more than 50%, don't use AWI.

### 5.5 Combined Error: ACS MoE + Interpolation

When overlaying ACS tract data onto districts:

1. Each tract estimate has MoE from ACS sampling
2. Each tract-to-district allocation has interpolation error from AWI

These are independent error sources. The combined standard error is:

```
SE_combined = sqrt(SE_acs^2 + SE_interp^2)
```

In practice, `SE_interp` is hard to estimate without ground truth. For
reporting purposes:

- **Report the ACS-propagated MoE** (which you can compute)
- **Add a caveat** about interpolation uncertainty (which you can't precisely quantify)
- **Validate** against known district-level statistics when available (e.g., PL 94-171
  redistricting data provides block-level counts that can be aggregated exactly to districts)

---

## 6. Temporal Alignment

### 6.1 The Problem

Data sources have different reference periods:

| Source | Reference Period | Example |
|--------|-----------------|---------|
| ACS 5-year 2022 | Jan 2018 – Dec 2022 | Income, poverty, education |
| ACS 1-year 2022 | Jan 2022 – Dec 2022 | Same variables, less precision |
| Decennial 2020 | April 1, 2020 | Total population, race, Hispanic origin |
| NCES 2023 | 2022–2023 school year | School locations, locale codes |
| RDH enacted plans | Varies (2021–2023 for current cycle) | District boundaries |
| NLRB regions | Current (rarely changes) | Region boundaries |

### 6.2 Matching Rules

1. **ACS year should match or be close to TIGER boundary year.** ACS 2022
   estimates are tabulated against 2020-vintage geographies, but TIGER
   boundaries are updated annually. Use the same year for both.

2. **NCES school year should bracket the ACS reference period.** NCES
   2022–2023 data pairs well with ACS 2022 (5-year: 2018–2022).

3. **RDH enacted plans are valid for the redistricting cycle.** Plans
   enacted in 2021–2022 are valid through the 2030 Census. Use them
   with any ACS data from that decade.

4. **Decennial data is a snapshot.** Do not combine 2020 Decennial block
   counts with 2022 ACS tract estimates and sum them — they measure
   different things at different times.

### 6.3 Population Change Between Vintages

When combining 2020 Decennial data with 2022 ACS data, population may have
shifted. This matters most for:

- Fast-growing suburbs (tracts that gained thousands of residents)
- Areas affected by disasters (tracts that lost population)
- College towns (seasonal population swings)

**Practical approach**: For cross-source tabulation, pick one Census vintage
and stick with it. ACS 5-year is the safest default — broad coverage, annual
updates, decent MoE at tract level.

---

## 7. Practical Recipes

### 7.1 Census × NCES: Demographics by Urbanicity

**Goal**: How does median income vary by NCES locale category (city/suburban/town/rural)?

**Method**:
1. Download tract-level ACS income data with geometry
2. Download NCES locale boundaries
3. Spatial join: tract centroids → locale polygons (1:1 assignment)
4. Group by `locale_category`, sum populations, propagate MoE

**MoE handling**: Sum MoE via root-sum-of-squares for population totals.
For median income, report the average of tract medians with a caveat.

**Scale**: Each locale category contains hundreds to thousands of tracts nationally.
Aggregated CVs will be low (< 5%).

### 7.2 Census × NLRB: Population by Labor Region

**Goal**: How much population does each NLRB region cover?

**Method**:
1. Fetch state-level population (ACS or Decennial)
2. Map state abbreviation → primary NLRB region
3. Sum population by region, propagate MoE

**MoE handling**: State-level ACS population estimates have very low CVs (< 1%).
Root-sum-of-squares across 2–6 states per region yields negligible MoE.

**Scale**: NLRB regions are very coarse. This tabulation is only useful for
national-level comparisons, not sub-state analysis.

### 7.3 Census × RDH: District Demographic Profiles

**Goal**: What are the demographics of each congressional district?

**Method**:
1. Fetch tract-level ACS demographics with geometry
2. Fetch enacted plan boundaries (RDH or Census CD)
3. Spatial overlay via `demographic_profile()` — area-weighted interpolation

**MoE handling**: Propagate ACS MoE through the area-weighted sum. Add a
caveat about areal interpolation error. Validate against PL 94-171 block-level
data when available.

**Scale**: Each district contains ~200 tracts. Aggregated CVs are typically low.

### 7.4 NCES × RDH: Schools per District by Urbanicity

**Goal**: How many city/suburban/town/rural schools are in each district?

**Method**:
1. Spatial join: school points → district polygons
2. Cross-tabulate by `locale_category`

**MoE handling**: No MoE — school counts are exact within the NCES universe
(public schools only). The only error is geocoding accuracy for schools near
district boundaries.

**Scale**: Good — school points are precise and districts are well-defined.

### 7.5 Unified County-Level Tabulation

**Goal**: One row per county with columns from all four sources.

**Method**: See `build_multi_source_tabulation()` in NB20 Part 7.

**MoE handling**: Census columns carry MoE. School counts are exact. NLRB
region is a label (no MoE). Congressional district assignment is approximate
(centroid method — no formal MoE, but may be wrong for split counties).

**Scale**: County is a reasonable common denominator for most states.
For states with very large counties (San Bernardino, AZ counties), the
district assignment via centroid is unreliable.

---

## 8. When Not to Tabulate

Cross-source tabulation is powerful but not always appropriate. Avoid it when:

1. **The MoE exceeds the signal.** If the CV of your aggregated estimate
   exceeds 40%, the result is noise, not data. This happens with small-area
   ACS data (block groups, small tracts) in sparsely populated areas.

2. **The scale mismatch is too large.** Assigning NLRB region-level labor
   data to individual tracts is meaningless — the data doesn't vary at
   that resolution.

3. **The temporal gap is too wide.** Combining 2010 Decennial data with
   2023 NCES school locations papers over 13 years of population change.

4. **The universes don't overlap.** NCES covers public schools only. If
   you join school counts to Census tract demographics and conclude
   "tracts with no schools are education deserts," you're ignoring
   private schools, charter schools, and homeschooling.

5. **You're making causal claims from ecological data.** Cross-source
   tabulation produces correlations between aggregate measures. It does
   not support causal inference. "Districts with more rural schools
   have lower median income" is a description. "Rural schools cause
   lower income" is a fallacy.

---

## References

- U.S. Census Bureau. *Understanding and Using ACS Data: What All Data Users Need to Know*.
  Chapter 7: "Measures of Uncertainty." 2020.
- Schroeder, J.P. "Target-density weighting interpolation and uncertainty evaluation for
  temporal analysis of census data." *Geographical Analysis* 39(3), 2007.
- Openshaw, S. "The modifiable areal unit problem." *Concepts and Techniques in Modern
  Geography* 38, 1984.
- Goodchild, M.F. and Lam, N.S. "Areal interpolation: A variant of the traditional
  spatial problem." *Geo-Processing* 1, 1980.
- Census Bureau. *ACS General Handbook*, Appendix A: "Margin of Error and Confidence Intervals."

---

## Related

- **[NB04](../notebooks/04_Spatial_Data_Census_Boundaries.ipynb)** — Census TIGER boundaries, GEOIDs, crosswalks
- **[NB15](../notebooks/15_Census_Demographics_Integration.ipynb)** — Census convenience functions
- **[NB19](../notebooks/19_NLRB_Data_Integration.ipynb)** — NLRB region data integration
- **[NB20](../notebooks/20_Multi_Source_Spatial_Tabulation.ipynb)** — Cross-source tabulation notebook
- **[CENSUS_DATA_GUIDE.md](CENSUS_DATA_GUIDE.md)** — Census variable codes and dataset selection

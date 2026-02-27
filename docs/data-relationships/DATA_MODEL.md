# Unified Geographic Data Model

This document describes the siege_utilities geographic data model — a
temporal, multi-source hierarchy for storing and querying boundaries,
demographics, crosswalks, and intersections across Census, GADM, federal,
and other spatial data sources.

---

## Design Principles

1. **Temporal by default.** Every geographic feature has a `vintage_year`
   (edition of the source dataset) and optional `valid_from`/`valid_to`
   dates. Multiple versions of the same boundary coexist side by side.

2. **Source-agnostic base.** The root abstract model carries temporal
   identity but no geometry. Each geometry type (polygon, line, point) has
   its own abstract, so the same temporal identity pattern applies to
   boundaries, roads, and addresses alike.

3. **Demographics attach to anything.** DemographicSnapshot and
   DemographicTimeSeries use Django's ContentType framework to attach to
   any boundary model — Census tract, GADM admin2, school district, etc.

4. **Intersections are pre-computed.** Boundary overlaps (e.g.,
   county-to-congressional-district) are stored as area-weighted records,
   avoiding repeated PostGIS `ST_Intersection` calls at query time.

5. **Crosswalks track change over time.** When boundaries split, merge,
   or shift between vintage years, `TemporalCrosswalk` records the
   relationship with allocation weights.

---

## Abstract Hierarchy

```
TemporalGeographicFeature (abstract — no geometry)
│   Fields: feature_id, name, vintage_year, valid_from, valid_to, source
│
├── TemporalBoundary (abstract — MultiPolygon, SRID 4326)
│   │   Adds: geometry, internal_point, area_land, area_water
│   │
│   ├── CensusTIGERBoundary (abstract — GEOID-based US Census)
│   │   │   Adds: geoid, state_fips, lsad, mtfcc, funcstat
│   │   │
│   │   ├── State, County, Tract, BlockGroup, Block
│   │   ├── Place, ZCTA, CongressionalDistrict
│   │   ├── StateLegislativeUpper, StateLegislativeLower
│   │   ├── VTD, Precinct
│   │   ├── SchoolDistrictElementary, Secondary, Unified
│   │   ├── CBSA, UrbanArea
│   │   └── (future: TimezoneGeometry — su#166)
│   │
│   ├── GADMBoundary (abstract — GID-based international)
│   │   │   Adds: gid
│   │   │
│   │   └── GADMCountry, GADMAdmin1-5
│   │
│   └── Federal boundaries (no shared abstract below TemporalBoundary)
│       ├── NLRBRegion
│       └── FederalJudicialDistrict
│
├── TemporalLinearFeature (abstract — MultiLineString)
│   │   Adds: geometry, length_meters
│   │   (future: roads, rivers, rail lines)
│
└── TemporalPointFeature (abstract — Point)
        Adds: geometry
        (future: addresses, facilities, polling places)
```

Every concrete model inherits `vintage_year`, `valid_from`, `valid_to`,
and `source` from `TemporalGeographicFeature`. This means GADM 3.6 and
GADM 4.1 boundaries coexist, 2010 and 2020 Census tracts coexist, and
timezone boundaries can be versioned when definitions change.

---

## Census TIGER Boundaries

All inherit from `CensusTIGERBoundary`. Each has a hierarchical GEOID that
embeds its parent's identifier:

| Model | GEOID | Length | Components | Parent FK |
|---|---|---|---|---|
| State | `06` | 2 | SS | — |
| County | `06037` | 5 | SS+CCC | State |
| Tract | `06037101100` | 11 | SS+CCC+TTTTTT | State, County |
| BlockGroup | `060371011001` | 12 | SS+CCC+TTTTTT+G | State, County, Tract |
| Block | `060371011001001` | 15 | SS+CCC+TTTTTT+BBBB | State, County, Tract, BlockGroup |
| Place | `0644000` | 7 | SS+PPPPP | State |
| ZCTA | `90210` | 5 | ZZZZZ | — |
| CongressionalDistrict | `0614` | 4 | SS+DD | State |
| StateLegislativeUpper | `06001` | 5 | SS+DDD | State |
| StateLegislativeLower | `06001` | 5 | SS+DDD | State |
| VTD | `06037001` | 8 | SS+CCC+VVV | State, County, CD (soft) |
| Precinct | variable | — | SS+CCC+code | State, County |

**Nesting hierarchy** (child GEOID always starts with parent GEOID):

```
State (2)
 └── County (5)
      └── Tract (11)
           └── BlockGroup (12)
                └── Block (15)
```

**Non-nesting geographies** (can span county/state lines):
- CBSA (Metropolitan/Micropolitan Statistical Areas)
- UrbanArea (Urbanized Areas and Urban Clusters)
- ZCTA (ZIP Code Tabulation Areas)
- CongressionalDistrict, StateLegislativeUpper/Lower

All models enforce `unique_together = (geoid, vintage_year)` and carry
`CheckConstraint` validators on GEOID digit length.

---

## GADM (International Boundaries)

The Global Administrative Areas dataset provides worldwide boundaries at
up to 6 administrative levels. GADM uses its own identifier system (GID)
rather than Census GEOIDs.

| Model | GID Example | Parent FK |
|---|---|---|
| GADMCountry | `USA` | — |
| GADMAdmin1 | `USA.5_1` | GADMCountry |
| GADMAdmin2 | `USA.5.37_1` | GADMAdmin1 |
| GADMAdmin3 | `USA.5.37.1_1` | GADMAdmin2 |
| GADMAdmin4 | — | GADMAdmin3 |
| GADMAdmin5 | — | GADMAdmin4 |

Each level has `type_N` and `engtype_N` fields that describe the
administrative type in the local language and English (e.g., "Estado",
"State").

**Parallel loading pattern:** Each child model has a `gid_N_string` field
that stores the parent's GID as a plain string during bulk loading.
After loading, `populate_parent_relationships()` resolves these strings
into actual ForeignKey references.

**Multi-version:** `unique_together = (gid, vintage_year)` allows GADM
3.6 (2018) and GADM 4.1 (2024) to coexist.

---

## Federal and Education Boundaries

These boundaries don't follow Census or GADM identifier schemes.

**NLRBRegion** — National Labor Relations Board regions (34 regions).
Uses `region_number` as identifier, stores a `states_covered` JSON list.

**FederalJudicialDistrict** — US federal court districts (e.g., "CACD"
for Central District of California). Linked to circuit numbers (1-13).

**School Districts** — NCES school district boundaries with locale
classification. Three types: Elementary, Secondary, Unified. Each carries
an `lea_id` (NCES Local Education Agency ID) and NCES `locale_code`
(11-43) with category/subcategory.

---

## How Non-Spatial Data Connects

### Demographics (DemographicSnapshot)

Demographics attach to **any** boundary model via Django's ContentType
framework:

```
DemographicSnapshot
├── content_type  →  ContentType (e.g., "Tract", "GADMAdmin2", "County")
├── object_id     →  GEOID or GID of the boundary
├── year          →  Data year (e.g., 2020)
├── dataset       →  "acs5", "acs1", "dec", "dec_pl"
├── values        →  {variable_code: value}  (JSON)
├── moe_values    →  {variable_code: margin_of_error}  (JSON)
└── Pre-computed: total_population, median_household_income, median_age
```

This means the **same DemographicSnapshot model** stores:
- ACS 5-year estimates for a Census tract
- Decennial population for a block
- PL 94-171 redistricting data for a VTD
- ACS data for a GADM admin2 region (if fetched)

The `dataset` field distinguishes the source. The `values` JSON stores
arbitrary Census variable codes, so no schema change is needed when new
variables are added.

### Time Series (DemographicTimeSeries)

Longitudinal demographic data for a single variable across multiple years:

```
DemographicTimeSeries
├── content_type, object_id  →  any boundary
├── variable_code            →  e.g., "B01001_001E"
├── dataset                  →  "acs5", etc.
├── years                    →  [2015, 2016, 2017, 2018, 2019, 2020]
├── values                   →  [45000, 45200, 45100, 46000, 46500, 47000]
├── moe_values               →  [500, 480, 510, ...]
└── Computed: mean_value, std_dev, cagr, trend_direction
```

The `TimeseriesService` populates these from DemographicSnapshot records
and computes CAGR (compound annual growth rate), standard deviation, and
trend direction.

### Variable Metadata (DemographicVariable)

Reference table for Census variable definitions:

```
DemographicVariable
├── code     →  "B01001_001E"
├── label    →  "Estimate!!Total:"
├── concept  →  "SEX BY AGE"
├── dataset  →  "acs5"
├── group    →  "B01001"
└── universe →  "Total population"
```

---

## Crosswalks: Tracking Boundary Changes Over Time

When boundaries change between vintage years (e.g., 2010 tracts to 2020
tracts), `TemporalCrosswalk` records the relationship:

```
TemporalCrosswalk
├── source_boundary_id    →  "06037101100" (2010 tract)
├── source_vintage_year   →  2010
├── source_type           →  "tract"
├── target_boundary_id    →  "06037101101" (2020 tract)
├── target_vintage_year   →  2020
├── target_type           →  "tract"
├── relationship          →  SPLIT | MERGED | IDENTICAL | PARTIAL | RENAMED
├── weight                →  0.65 (allocation fraction)
├── weight_type           →  population | housing | area | land_area
└── allocated_population  →  pre-computed weighted population
```

**Relationship types:**
- `IDENTICAL` — boundary unchanged (weight = 1.0)
- `SPLIT` — one source becomes multiple targets (weights sum to 1.0)
- `MERGED` — multiple sources become one target
- `PARTIAL` — partial overlap (both boundary sets changed)
- `RENAMED` — same geography, different identifier

This enables questions like "what 2020 tracts correspond to this 2010
tract?" and population allocation across boundary changes.

---

## Intersections: Pre-Computed Spatial Overlaps

When two boundary sets overlap (e.g., counties and congressional
districts), the intersection area is stored to avoid repeated PostGIS
computations.

**Generic intersection** (any boundary pair):

```
BoundaryIntersection
├── source_type, source_boundary_id  →  ("county", "06037")
├── target_type, target_boundary_id  →  ("cd", "0614")
├── vintage_year                     →  2020
├── intersection_area                →  sq meters
├── pct_of_source, pct_of_target     →  0.0-1.0
└── is_dominant                      →  largest overlap for this source
```

**Typed intersections** (for frequently-queried pairs, with ForeignKeys):
- `CountyCDIntersection` — County ↔ CongressionalDistrict
- `VTDCDIntersection` — VTD ↔ CongressionalDistrict
- `TractCDIntersection` — Tract ↔ CongressionalDistrict

These are pre-computed by the `CrosswalkPopulationService` and used for
redistricting analysis, election result aggregation, and demographic
roll-ups across non-nesting geographies.

---

## How External Data Sources Connect

The model is designed for extension. External data connects through
several patterns:

### Pattern 1: DemographicSnapshot (for tabular data by geography)

Any dataset that provides values keyed by GEOID or GID can be stored in
DemographicSnapshot. The `dataset` field identifies the source, and
`values` JSON stores the data:

```python
DemographicSnapshot.objects.create(
    content_type=ContentType.objects.get_for_model(Tract),
    object_id="06037101100",
    year=2020,
    dataset="custom_survey",
    values={"food_desert_score": 0.85, "transit_access_index": 3.2},
)
```

**Suitable for:** election results, environmental scores, business counts,
health metrics, custom survey data — anything numeric keyed by geography.

### Pattern 2: BoundaryIntersection (for spatial overlaps)

When a new boundary type overlaps existing geographies, pre-compute the
intersections:

```python
BoundaryIntersection.objects.create(
    source_type="school_district",
    source_boundary_id="0600001",
    target_type="county",
    target_boundary_id="06037",
    vintage_year=2020,
    pct_of_source=0.85,
    pct_of_target=0.02,
)
```

**Suitable for:** school districts vs counties, utility service areas vs
tracts, fire districts vs cities, any non-nesting spatial overlay.

### Pattern 3: TemporalCrosswalk (for boundary version changes)

When a dataset's boundaries change between releases:

```python
TemporalCrosswalk.objects.create(
    source_boundary_id="USA.5_1",
    source_vintage_year=2018,  # GADM 3.6
    source_type="gadm_admin1",
    target_boundary_id="USA.5_1",
    target_vintage_year=2024,  # GADM 4.1
    target_type="gadm_admin1",
    relationship="IDENTICAL",
    weight=1.0,
    weight_type="area",
)
```

**Suitable for:** GADM version transitions, redistricting (old districts
to new), ZCTA redefinitions, any boundary-set-to-boundary-set mapping.

### Pattern 4: New model inheriting from TemporalBoundary

For first-class spatial entities that need their own fields, create a new
model in the hierarchy:

```python
class TimezoneGeometry(TemporalBoundary):
    tzid = models.CharField(max_length=80, db_index=True)
    utc_offset = models.DecimalField(...)

class WaterDistrict(CensusTIGERBoundary):
    district_name = models.CharField(...)
    water_source = models.CharField(...)
```

By inheriting from `TemporalBoundary`, the new model automatically gets:
- `vintage_year`, `valid_from`/`valid_to` for temporal versioning
- `geometry` (MultiPolygon) with spatial indexing
- `internal_point` for labeling and distance calculations
- Compatibility with `BoundaryManager` spatial queries (`.containing_point()`, `.nearest()`, `.within_distance()`)
- Compatibility with DemographicSnapshot (via ContentType)
- Compatibility with BoundaryIntersection
- Pydantic schema generation via the converters module

### Pattern 5: TemporalLinearFeature / TemporalPointFeature

For non-polygon spatial data:

- **Linear features** (roads, rivers, rail lines, pipelines) inherit from
  `TemporalLinearFeature` — gets MultiLineString geometry + length_meters.
- **Point features** (addresses, polling places, schools, facilities)
  inherit from `TemporalPointFeature` — gets Point geometry.

Both inherit the full temporal identity (vintage_year, valid_from/to,
source) so they can be versioned and queried the same way as boundaries.

---

## PL 94-171 Redistricting Data

PL 94-171 is the Census Bureau's redistricting data release, published
before the full decennial data. It provides population by race, Hispanic
origin, voting-age population, group quarters, and housing occupancy at
**block level** — the finest geography available.

### How PL Data Fits the Model

PL 94-171 data is stored in `DemographicSnapshot` with `dataset="dec_pl"`:

```python
DemographicSnapshot(
    content_type=ContentType.objects.get_for_model(Block),
    object_id="060371011001001",       # 15-digit block GEOID
    year=2020,
    dataset="dec_pl",
    values={
        "P1_001N": 4521,              # Total population
        "P2_002N": 1830,              # Hispanic or Latino
        "P2_005N": 1250,              # Not Hispanic: White alone
        "P3_001N": 3200,              # Total 18+
        "H1_001N": 1800,              # Total housing units
    },
    total_population=4521,
)
```

### PL Variable Tables

| Table | Subject | Variables |
|---|---|---|
| P1 | Race | 11 variables — total population by single/multiple race |
| P2 | Hispanic/Latino by Race | 11 variables — Hispanic origin cross-tabulated with race |
| P3 | Race (18+) | 9 variables — voting-age population by race |
| P4 | Hispanic/Latino by Race (18+) | 11 variables — VAP by Hispanic origin and race |
| P5 | Group Quarters | 10 variables — institutional and non-institutional |
| H1 | Housing Occupancy | 3 variables — total, occupied, vacant |

### PL vs Full Decennial vs ACS

| Attribute | PL 94-171 | Full Decennial | ACS 5-Year |
|---|---|---|---|
| Dataset code | `dec_pl` | `dec` | `acs5` |
| Finest geography | Block | Block | Block Group |
| Variables | 55 (race, VAP, housing) | Hundreds | Thousands |
| Release timing | ~12 months after Census Day | ~18-24 months | Annual rolling |
| Use case | Redistricting, VRA compliance | Official counts | Socioeconomic analysis |
| Variable naming | `P1_001N`, `H1_001N` | `P1_001N` (overlap) | `B01001_001E` |

### Predefined Variable Groups

The `CensusAPIClient.VARIABLE_GROUPS` dict provides curated PL variable
sets (see [CENSUS_DATASET_RELATIONSHIPS.md](CENSUS_DATASET_RELATIONSHIPS.md)
for the full list):

- `pl_p1_race` — complete P1 table (11 vars)
- `pl_p2_hispanic` — complete P2 table (11 vars)
- `pl_p3_race_18plus` — complete P3 table (9 vars)
- `pl_p4_hispanic_18plus` — complete P4 table (11 vars)
- `pl_p5_group_quarters` — complete P5 table (10 vars)
- `pl_h1_housing` — complete H1 table (3 vars)
- `pl_redistricting_core` — combined core set (17 vars)

### Ingestion Pipeline (planned — su#162)

The PL data ingestion pipeline will:
1. Download PL files (API or bulk pipe-delimited files)
2. Parse into DemographicSnapshot records with `dataset="dec_pl"`
3. Attach to Block, BlockGroup, Tract, County, and State boundaries
4. Support both 2010 and 2020 PL releases
5. Integrate with `DemographicRollupService` for aggregation to coarser
   geographies

---

## Pydantic Schema Layer

Every Django model has a corresponding Pydantic schema for
validation and serialization. Schemas live in `siege_utilities/geo/schemas/`.

**Conversion utilities** (`converters.py`):

| Function | Direction | Description |
|---|---|---|
| `gdf_to_schemas()` | GeoDataFrame → Pydantic | Validate shapefile/GeoJSON data |
| `schemas_to_orm()` | Pydantic → Django ORM | Create model instances from validated data |
| `orm_to_gdf()` | Django ORM → GeoDataFrame | Export query results for spatial analysis |

Geometry is excluded from schemas (stored as WKT strings) to keep
validation fast and serialization clean.

---

## Model Count Summary

| Category | Models | Examples |
|---|---|---|
| Abstract bases | 5 | TemporalGeographicFeature, TemporalBoundary, CensusTIGERBoundary |
| Census TIGER | 8 | State, County, Tract, BlockGroup, Block, Place, ZCTA, CD |
| Political | 4 | StateLegislativeUpper/Lower, VTD, Precinct |
| GADM | 7 | GADMCountry, GADMAdmin1-5 |
| Education | 4 | SchoolDistrictElementary/Secondary/Unified + abstract base |
| Federal | 2 | NLRBRegion, FederalJudicialDistrict |
| Extended Census | 2 | CBSA, UrbanArea |
| Intersections | 4 | BoundaryIntersection, CountyCDIntersection, VTDCDIntersection, TractCDIntersection |
| Demographics | 3 | DemographicVariable, DemographicSnapshot, DemographicTimeSeries |
| Crosswalks | 2 | TemporalCrosswalk, CrosswalkDataset |
| **Total** | **41** | |
| Pydantic schemas | 33 | Mirror of all concrete models |

# Geospatial Data Warehouse: Star Schema Design

**Companion to**: [unified-geo-model-schema.md](./unified-geo-model-schema.md)
**Date**: 2026-02-24
**Status**: Draft — Design Document
**Epics**: 13 (Socialwarehouse/DSTK Foundation), su#140 (PySAL), en#191 (Temporal Statistics API)

---

## 1. Overview

The unified geo model schema defines the **boundary catalog** — what geographic units exist and when they were valid. This document defines the **data warehouse** — what we know about those boundaries over time.

### Why a Separate Warehouse?

The web application database (Django default) handles transactional workloads: user sessions, API requests, admin CRUD. The warehouse handles analytical workloads: multi-year demographic comparisons, spatial interpolation, cross-vintage statistical queries. Mixing these in one database means either the web app suffers from heavy analytical queries or the warehouse is constrained by Django migration patterns.

**Two PostGIS instances:**

| Database | Purpose | Access Pattern | Django Config |
|----------|---------|---------------|---------------|
| **webapp** | Boundary dimensions, user data, API | Read/write, transactional | `DATABASES['default']` |
| **warehouse** | Fact tables, materialized views, analytics | Read-heavy, batch ETL writes | `DATABASES['warehouse']` |

The boundary dimension tables (State, County, Tract, etc.) live in **both** databases — the webapp has the authoritative copy managed by Django migrations, the warehouse has a read-optimized copy loaded by ETL. Fact tables live only in the warehouse.

### Three Layers of Data per Boundary

Every boundary in the system carries three categories of information:

1. **Metadata** — what IS this boundary (name, GEOID, vintage year, valid dates)
2. **Geometry** — WHERE is this boundary (the polygon, interior point, area)
3. **Facts** — what is TRUE about this boundary at a point in time (population, income, poverty rate, vote totals, urbanicity classification)

The unified geo schema handles layers 1 and 2. This document handles layer 3.

---

## 2. Dimensional Model

### 2.1 Geography Dimension (SCD Type 2)

Census geographies change over time. Tract `06037101100` in vintage 2020 may have different boundaries than the same GEOID in vintage 2010. This is a Slowly Changing Dimension (SCD) problem. We use **Type 2**: a new row for each version, with a surrogate integer key.

```sql
CREATE TABLE dim_geography (
    geo_id          SERIAL PRIMARY KEY,       -- Surrogate key (fact tables reference this)

    -- Natural key
    geoid           VARCHAR(20) NOT NULL,     -- Census GEOID or boundary_id
    vintage_year    SMALLINT NOT NULL,

    -- Geographic hierarchy
    summary_level   VARCHAR(10) NOT NULL,     -- 'state', 'county', 'tract', 'block_group', etc.
    state_fips      VARCHAR(2),
    county_fips     VARCHAR(3),
    tract_ce        VARCHAR(6),
    blockgroup_ce   VARCHAR(1),

    -- Human-readable
    name            VARCHAR(255),

    -- Parent reference (for drill-up)
    parent_geo_id   INTEGER REFERENCES dim_geography(geo_id),

    -- PostGIS geometry
    geometry        GEOMETRY(MultiPolygon, 4326) NOT NULL,
    internal_point  GEOMETRY(Point, 4326),
    aland           BIGINT,
    awater          BIGINT,

    -- SCD Type 2 bookkeeping
    effective_from  DATE NOT NULL,
    effective_to    DATE,                     -- NULL = current
    is_current      BOOLEAN DEFAULT TRUE,
    source          VARCHAR(50) DEFAULT 'TIGER',

    UNIQUE (geoid, vintage_year)
);

CREATE INDEX idx_dimgeo_geometry ON dim_geography USING GIST (geometry);
CREATE INDEX idx_dimgeo_point ON dim_geography USING GIST (internal_point);
CREATE INDEX idx_dimgeo_current ON dim_geography (summary_level, is_current) WHERE is_current = TRUE;
CREATE INDEX idx_dimgeo_geoid ON dim_geography (geoid, vintage_year);
CREATE INDEX idx_dimgeo_state ON dim_geography (state_fips, summary_level, vintage_year);
```

**Why surrogate keys?** Fact table FKs are a single integer (4 bytes) instead of `(varchar(20), smallint)` composite. Joins are faster. When vintages change, only the dimension gets new rows.

### 2.2 Survey/Data Product Dimension

ACS 5-year estimates and Decennial counts have fundamentally different semantics. ACS is a rolling sample with overlapping periods and margins of error. Decennial is a full enumeration with no MOE. The survey dimension tracks these distinctions.

```sql
CREATE TABLE dim_survey (
    survey_id       SERIAL PRIMARY KEY,
    survey_type     VARCHAR(20) NOT NULL,    -- 'acs5', 'acs1', 'decennial', 'decennial_dhc'
    vintage_year    SMALLINT NOT NULL,       -- End year: 2022 for ACS 2018-2022
    period_start    SMALLINT,                -- 2018 for ACS 2018-2022, NULL for decennial
    period_end      SMALLINT,                -- 2022 for ACS 2018-2022, NULL for decennial
    release_date    DATE,

    UNIQUE (survey_type, vintage_year)
);
```

**Key rule**: Temporal comparisons between non-overlapping ACS periods (e.g., 2014-2018 vs 2019-2023) are safe. Overlapping periods require special treatment per Census Bureau guidance.

### 2.3 Census Variable Dimension

The Census Bureau publishes thousands of variables organized into tables. Each variable has a type that matters for downstream interpolation: **extensive** (counts — summed during spatial interpolation) vs **intensive** (rates/medians — area-weighted averaged).

```sql
CREATE TABLE dim_census_variable (
    variable_id     SERIAL PRIMARY KEY,
    table_id        VARCHAR(20) NOT NULL,    -- 'B01001', 'B19013', 'P1', etc.
    variable_code   VARCHAR(30) NOT NULL,    -- 'B01001_001E'
    label           TEXT NOT NULL,            -- 'Total Population'
    concept         TEXT,                     -- 'SEX BY AGE'
    variable_type   VARCHAR(20) NOT NULL,    -- 'extensive' or 'intensive'
    universe        TEXT,                     -- 'Total population', 'Households', etc.

    UNIQUE (table_id, variable_code)
);

CREATE INDEX idx_dimvar_code ON dim_census_variable (variable_code);
CREATE INDEX idx_dimvar_table ON dim_census_variable (table_id);
```

### 2.4 Time Dimension

Separate from `dim_survey` (which tracks data products), the time dimension provides standard calendar attributes for any date-based analysis.

```sql
CREATE TABLE dim_time (
    time_id         SERIAL PRIMARY KEY,
    calendar_date   DATE NOT NULL UNIQUE,
    year            SMALLINT NOT NULL,
    quarter         SMALLINT NOT NULL,       -- 1-4
    month           SMALLINT NOT NULL,       -- 1-12
    day_of_year     SMALLINT NOT NULL,
    is_census_day   BOOLEAN DEFAULT FALSE,   -- April 1 of decennial years
    is_election_day BOOLEAN DEFAULT FALSE,   -- First Tuesday after first Monday in November
    fiscal_year     SMALLINT NOT NULL        -- Federal FY (Oct-Sep)
);

CREATE INDEX idx_dimtime_year ON dim_time (year);
CREATE INDEX idx_dimtime_quarter ON dim_time (year, quarter);
```

---

## 3. Fact Tables

### Design Principles

1. **Estimate + MOE always paired** in the same row — never split across rows or tables. An orphaned estimate without its MOE is a data quality hazard.
2. **One fact table per data product type** — ACS estimates and Decennial counts have different column structures. Interpolated results have different provenance tracking. Don't merge them.
3. **Reliability computed at load time** — the Census Bureau's coefficient of variation (CV) thresholds are applied during ETL, not at query time.

### 3.1 ACS Estimates

The core fact table for American Community Survey data. One row per geography + variable + survey.

```sql
CREATE TABLE fact_acs_estimate (
    fact_id                 BIGSERIAL PRIMARY KEY,
    geo_id                  INTEGER NOT NULL REFERENCES dim_geography(geo_id),
    variable_id             INTEGER NOT NULL REFERENCES dim_census_variable(variable_id),
    survey_id               INTEGER NOT NULL REFERENCES dim_survey(survey_id),

    -- The estimate-MOE pair
    estimate                NUMERIC,                 -- NULL = suppressed
    margin_of_error         NUMERIC,                 -- MOE at 90% confidence

    -- Derived quality fields (computed at load time)
    coefficient_of_variation NUMERIC,                -- (SE / estimate) * 100
    reliability             VARCHAR(5),              -- 'high' (<12% CV), 'med' (12-40%), 'low' (>40%)

    -- Census Bureau annotation flags
    estimate_annotation     VARCHAR(10),             -- '-', 'N', '(X)', '**', etc.
    moe_annotation          VARCHAR(10),             -- '***', '-', etc.

    UNIQUE (geo_id, variable_id, survey_id)
);

CREATE INDEX idx_acs_geo_survey ON fact_acs_estimate (geo_id, survey_id);
CREATE INDEX idx_acs_variable ON fact_acs_estimate (variable_id, survey_id);
```

**Reliability classification** (Census Bureau thresholds):

```python
def compute_reliability(estimate: float, moe: float) -> str:
    if estimate == 0 or estimate is None or moe is None:
        return 'low'
    se = moe / 1.645  # MOE is at 90% confidence
    cv = (se / abs(estimate)) * 100
    if cv < 12:
        return 'high'
    elif cv < 40:
        return 'med'
    else:
        return 'low'
```

### 3.2 Decennial Counts

Separate table — no MOE columns (full enumeration, not a sample).

```sql
CREATE TABLE fact_decennial_count (
    fact_id         BIGSERIAL PRIMARY KEY,
    geo_id          INTEGER NOT NULL REFERENCES dim_geography(geo_id),
    variable_id     INTEGER NOT NULL REFERENCES dim_census_variable(variable_id),
    survey_id       INTEGER NOT NULL REFERENCES dim_survey(survey_id),

    count_value     BIGINT,                  -- Exact enumeration

    UNIQUE (geo_id, variable_id, survey_id)
);

CREATE INDEX idx_dec_geo_survey ON fact_decennial_count (geo_id, survey_id);
```

### 3.3 Election Results

Election data at the precinct/VTD level, aggregatable to higher geographies via boundary intersections.

```sql
CREATE TABLE fact_election_result (
    fact_id             BIGSERIAL PRIMARY KEY,
    geo_id              INTEGER NOT NULL REFERENCES dim_geography(geo_id),
    election_date_id    INTEGER NOT NULL REFERENCES dim_time(time_id),

    -- Office identification
    office              VARCHAR(100) NOT NULL,   -- 'US President', 'US Senate', 'US House', 'Governor'
    district            VARCHAR(20),             -- CD number, state for statewide races
    state_fips          VARCHAR(2) NOT NULL,

    -- Candidate results
    candidate_name      VARCHAR(200) NOT NULL,
    party               VARCHAR(50),
    votes               INTEGER NOT NULL,
    vote_pct            NUMERIC(7, 4),           -- Percentage of total votes in this geography

    -- Totals for the race in this geography
    total_votes         INTEGER,
    registered_voters   INTEGER,
    turnout_pct         NUMERIC(7, 4),

    -- Source tracking
    source              VARCHAR(50) NOT NULL,    -- 'SOS', 'MEDSL', 'OpenElections'
    source_file         VARCHAR(200),

    UNIQUE (geo_id, election_date_id, office, district, candidate_name)
);

CREATE INDEX idx_election_geo ON fact_election_result (geo_id, election_date_id);
CREATE INDEX idx_election_office ON fact_election_result (office, state_fips, election_date_id);
```

### 3.4 Urbanicity Classification

NCES locale codes applied to boundaries. This bridges the NCES school district locale data to any geography via spatial overlay.

```sql
CREATE TABLE fact_urbanicity (
    fact_id             BIGSERIAL PRIMARY KEY,
    geo_id              INTEGER NOT NULL REFERENCES dim_geography(geo_id),

    -- NCES classification
    nces_year           SMALLINT NOT NULL,        -- Year of NCES locale data used
    locale_code         SMALLINT,                 -- 11-43 numeric code
    locale_category     VARCHAR(20),              -- city/suburban/town/rural
    locale_subcategory  VARCHAR(30),              -- city_large, rural_remote, etc.

    -- How classification was derived
    method              VARCHAR(30) NOT NULL,     -- 'direct' (is a school district) or 'overlay' (spatial join)
    source_district_geoid VARCHAR(20),            -- School district used for classification (if overlay)
    area_overlap_pct    NUMERIC(7, 4),            -- % of target covered by source district

    UNIQUE (geo_id, nces_year)
);

CREATE INDEX idx_urban_geo ON fact_urbanicity (geo_id);
CREATE INDEX idx_urban_category ON fact_urbanicity (locale_category, nces_year);
```

### 3.5 Interpolated Estimates

Results from PySAL tobler spatial interpolation. These have different provenance and quality characteristics than direct Census data.

```sql
CREATE TABLE fact_interpolated_estimate (
    fact_id                 BIGSERIAL PRIMARY KEY,
    target_geo_id           INTEGER NOT NULL REFERENCES dim_geography(geo_id),
    variable_id             INTEGER NOT NULL REFERENCES dim_census_variable(variable_id),

    interpolated_value      NUMERIC,

    -- Provenance
    source_survey_id        INTEGER REFERENCES dim_survey(survey_id),
    source_vintage_year     SMALLINT NOT NULL,
    source_summary_level    VARCHAR(10) NOT NULL,    -- 'tract', 'block_group', etc.
    target_summary_level    VARCHAR(10) NOT NULL,    -- What we interpolated TO
    interpolation_method    VARCHAR(50) NOT NULL,    -- 'area_weighted', 'dasymetric', 'model_based'
    interpolated_at         TIMESTAMP DEFAULT NOW(),

    -- Quality tracking (MOE does not survive interpolation)
    source_reliability_min  VARCHAR(5),              -- Worst reliability of contributing source geographies
    area_coverage_pct       NUMERIC(7, 4),           -- % of target area covered by source data
    n_source_units          INTEGER,                 -- Number of source geographies that contributed

    UNIQUE (target_geo_id, variable_id, source_vintage_year, interpolation_method)
);

CREATE INDEX idx_interp_target ON fact_interpolated_estimate (target_geo_id, source_vintage_year);
```

**Why no MOE on interpolated data?** Tobler's area-weighted interpolation does not propagate margins of error. The Census Bureau's MOE formulas assume independent samples, which breaks when you spatially redistribute data. Instead we track provenance and quality indicators. For rigorous uncertainty quantification, run the interpolation on Census Bureau Variance Replicate Estimates independently and build confidence intervals from the distribution.

### 3.6 Campaign Finance (FEC-Specific)

Enterprise-specific fact table for FEC donation data geocoded to boundaries.

```sql
CREATE TABLE fact_donation_summary (
    fact_id             BIGSERIAL PRIMARY KEY,
    geo_id              INTEGER NOT NULL REFERENCES dim_geography(geo_id),
    election_cycle      SMALLINT NOT NULL,       -- 2020, 2022, 2024

    -- Aggregated donation metrics
    total_amount        NUMERIC(15, 2),
    total_count         INTEGER,
    mean_amount         NUMERIC(10, 2),
    median_amount       NUMERIC(10, 2),
    unique_donors       INTEGER,

    -- Party breakdown
    dem_amount          NUMERIC(15, 2),
    rep_amount          NUMERIC(15, 2),
    other_amount        NUMERIC(15, 2),
    dem_count           INTEGER,
    rep_count           INTEGER,
    other_count         INTEGER,

    -- Source
    source              VARCHAR(50) DEFAULT 'FEC',

    UNIQUE (geo_id, election_cycle)
);

CREATE INDEX idx_donation_geo ON fact_donation_summary (geo_id, election_cycle);
```

---

## 4. Materialized Views

Materialized views pre-join dimension and fact tables for common analytical queries. They provide the "property field" experience — query `mv_tract_demographics.total_population` as if it were a column on the tract model.

### 4.1 Tract Demographics (Latest ACS)

The most common query: "give me tracts with their key demographics."

```sql
CREATE MATERIALIZED VIEW mv_tract_demographics AS
SELECT
    g.geo_id,
    g.geoid,
    g.name AS tract_name,
    g.state_fips,
    g.county_fips,
    g.vintage_year,
    g.geometry,
    g.internal_point,
    g.aland,
    g.awater,
    s.vintage_year AS acs_vintage,

    -- Population (B01001_001)
    pop.estimate AS total_population,
    pop.margin_of_error AS total_population_moe,
    pop.reliability AS total_population_reliability,

    -- Median Household Income (B19013_001)
    inc.estimate AS median_household_income,
    inc.margin_of_error AS median_household_income_moe,
    inc.reliability AS median_household_income_reliability,

    -- Median Age (B01002_001)
    age.estimate AS median_age,
    age.margin_of_error AS median_age_moe,

    -- Poverty Rate (derived: B17001_002 / B17001_001 * 100)
    CASE WHEN pov_total.estimate > 0
        THEN ROUND((pov_below.estimate::numeric / pov_total.estimate * 100), 2)
        ELSE NULL
    END AS pct_poverty,

    -- Race/ethnicity percentages
    CASE WHEN pop.estimate > 0
        THEN ROUND((white.estimate::numeric / pop.estimate * 100), 2)
        ELSE NULL
    END AS pct_white,
    CASE WHEN pop.estimate > 0
        THEN ROUND((black.estimate::numeric / pop.estimate * 100), 2)
        ELSE NULL
    END AS pct_black,
    CASE WHEN pop.estimate > 0
        THEN ROUND((hispanic.estimate::numeric / pop.estimate * 100), 2)
        ELSE NULL
    END AS pct_hispanic,
    CASE WHEN pop.estimate > 0
        THEN ROUND((asian.estimate::numeric / pop.estimate * 100), 2)
        ELSE NULL
    END AS pct_asian,

    -- Urbanicity (from fact_urbanicity)
    u.locale_category AS urbanicity,
    u.locale_subcategory AS urbanicity_detail,
    u.locale_code AS nces_locale_code

FROM dim_geography g
JOIN dim_survey s ON s.survey_type = 'acs5'
    AND s.vintage_year = (SELECT MAX(vintage_year) FROM dim_survey WHERE survey_type = 'acs5')
LEFT JOIN fact_acs_estimate pop ON pop.geo_id = g.geo_id AND pop.survey_id = s.survey_id
    AND pop.variable_id = (SELECT variable_id FROM dim_census_variable WHERE variable_code = 'B01001_001E')
LEFT JOIN fact_acs_estimate inc ON inc.geo_id = g.geo_id AND inc.survey_id = s.survey_id
    AND inc.variable_id = (SELECT variable_id FROM dim_census_variable WHERE variable_code = 'B19013_001E')
LEFT JOIN fact_acs_estimate age ON age.geo_id = g.geo_id AND age.survey_id = s.survey_id
    AND age.variable_id = (SELECT variable_id FROM dim_census_variable WHERE variable_code = 'B01002_001E')
LEFT JOIN fact_acs_estimate pov_below ON pov_below.geo_id = g.geo_id AND pov_below.survey_id = s.survey_id
    AND pov_below.variable_id = (SELECT variable_id FROM dim_census_variable WHERE variable_code = 'B17001_002E')
LEFT JOIN fact_acs_estimate pov_total ON pov_total.geo_id = g.geo_id AND pov_total.survey_id = s.survey_id
    AND pov_total.variable_id = (SELECT variable_id FROM dim_census_variable WHERE variable_code = 'B17001_001E')
LEFT JOIN fact_acs_estimate white ON white.geo_id = g.geo_id AND white.survey_id = s.survey_id
    AND white.variable_id = (SELECT variable_id FROM dim_census_variable WHERE variable_code = 'B02001_002E')
LEFT JOIN fact_acs_estimate black ON black.geo_id = g.geo_id AND black.survey_id = s.survey_id
    AND black.variable_id = (SELECT variable_id FROM dim_census_variable WHERE variable_code = 'B02001_003E')
LEFT JOIN fact_acs_estimate hispanic ON hispanic.geo_id = g.geo_id AND hispanic.survey_id = s.survey_id
    AND hispanic.variable_id = (SELECT variable_id FROM dim_census_variable WHERE variable_code = 'B03003_003E')
LEFT JOIN fact_acs_estimate asian ON asian.geo_id = g.geo_id AND asian.survey_id = s.survey_id
    AND asian.variable_id = (SELECT variable_id FROM dim_census_variable WHERE variable_code = 'B02001_005E')
LEFT JOIN fact_urbanicity u ON u.geo_id = g.geo_id
    AND u.nces_year = (SELECT MAX(nces_year) FROM fact_urbanicity)

WHERE g.summary_level = 'tract'
  AND g.is_current = TRUE
WITH DATA;

-- Required for REFRESH CONCURRENTLY
CREATE UNIQUE INDEX idx_mv_tract_demo_geoid ON mv_tract_demographics (geoid);
CREATE INDEX idx_mv_tract_demo_geom ON mv_tract_demographics USING GIST (geometry);
CREATE INDEX idx_mv_tract_demo_state ON mv_tract_demographics (state_fips);
CREATE INDEX idx_mv_tract_demo_urban ON mv_tract_demographics (urbanicity);
```

### 4.2 County Election Summary

Pre-aggregated election results at the county level with demographic context.

```sql
CREATE MATERIALIZED VIEW mv_county_election_demographics AS
SELECT
    g.geo_id,
    g.geoid,
    g.name AS county_name,
    g.state_fips,
    g.geometry,

    -- Latest presidential election
    pres.total_votes AS pres_total_votes,
    pres.dem_votes,
    pres.rep_votes,
    CASE WHEN pres.total_votes > 0
        THEN ROUND((pres.dem_votes::numeric / pres.total_votes * 100), 2)
        ELSE NULL
    END AS pres_dem_pct,

    -- Demographics
    td.total_population,
    td.median_household_income,
    td.pct_poverty,
    td.pct_white,
    td.pct_black,
    td.pct_hispanic,
    td.urbanicity

FROM dim_geography g
LEFT JOIN LATERAL (
    SELECT
        SUM(votes) FILTER (WHERE party = 'DEM') AS dem_votes,
        SUM(votes) FILTER (WHERE party = 'REP') AS rep_votes,
        SUM(total_votes) AS total_votes
    FROM fact_election_result er
    WHERE er.geo_id = g.geo_id
      AND er.office = 'US President'
      AND er.election_date_id = (
          SELECT time_id FROM dim_time
          WHERE is_election_day AND year = (SELECT MAX(year) FROM dim_time WHERE is_election_day)
      )
) pres ON TRUE
LEFT JOIN mv_tract_demographics td ON td.state_fips = g.state_fips  -- Simplified; real join uses aggregation

WHERE g.summary_level = 'county'
  AND g.is_current = TRUE
WITH DATA;
```

### 4.3 Refresh Strategy

Materialized views are refreshed on a schedule or on-demand:

```python
# Management command: refresh_warehouse_views
REFRESH_ORDER = [
    'mv_tract_demographics',
    'mv_county_election_demographics',
]

# Nightly cron or Rundeck job:
# python manage.py refresh_warehouse_views --concurrent
```

Concurrent refresh requires a unique index on the view (already defined above). It allows reads during refresh — no downtime for API consumers.

---

## 5. Django Integration

### 5.1 Database Configuration

```python
# settings.py
DATABASES = {
    'default': {
        'ENGINE': 'django.contrib.gis.db.backends.postgis',
        'NAME': 'webapp_db',
        'HOST': 'postgis.elect.info',
        ...
    },
    'warehouse': {
        'ENGINE': 'django.contrib.gis.db.backends.postgis',
        'NAME': 'census_warehouse',
        'HOST': 'warehouse.elect.info',
        'OPTIONS': {
            'options': '-c default_transaction_read_only=on',
        },
        ...
    },
}

DATABASE_ROUTERS = ['warehouse.routers.WarehouseRouter']
```

### 5.2 Router

```python
# warehouse/routers.py

WAREHOUSE_APPS = {'warehouse'}


class WarehouseRouter:
    """Route warehouse models to the warehouse database. Read-only from Django."""

    def db_for_read(self, model, **hints):
        if model._meta.app_label in WAREHOUSE_APPS:
            return 'warehouse'
        return None

    def db_for_write(self, model, **hints):
        if model._meta.app_label in WAREHOUSE_APPS:
            raise RuntimeError(
                f"Write attempted on warehouse model {model.__name__}. "
                f"Use ETL pipeline for warehouse writes."
            )
        return None

    def allow_relation(self, obj1, obj2, **hints):
        app1 = obj1._meta.app_label
        app2 = obj2._meta.app_label
        if app1 in WAREHOUSE_APPS and app2 in WAREHOUSE_APPS:
            return True
        if app1 in WAREHOUSE_APPS or app2 in WAREHOUSE_APPS:
            return False
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if db == 'warehouse':
            return False
        if app_label in WAREHOUSE_APPS:
            return False
        return None
```

### 5.3 Base Model and Manager

```python
# warehouse/models/base.py
from django.contrib.gis.db import models as gis_models


class WarehouseManager(gis_models.Manager):
    """Manager that always routes to the warehouse database."""
    def get_queryset(self):
        return super().get_queryset().using('warehouse')


class WarehouseModel(gis_models.Model):
    """Abstract base for all warehouse models. Read-only from Django."""
    objects = WarehouseManager()

    class Meta:
        abstract = True
        managed = False

    def save(self, **kwargs):
        raise RuntimeError("Warehouse models are read-only from Django. Use ETL pipeline.")

    def delete(self, **kwargs):
        raise RuntimeError("Warehouse models are read-only from Django. Use ETL pipeline.")
```

### 5.4 Django Models for Dimensions and Facts

```python
# warehouse/models/dimensions.py
from django.contrib.gis.db import models as gis_models
from .base import WarehouseModel


class DimGeography(WarehouseModel):
    geo_id = gis_models.AutoField(primary_key=True)
    geoid = gis_models.CharField(max_length=20, db_index=True)
    vintage_year = gis_models.SmallIntegerField()
    summary_level = gis_models.CharField(max_length=10)
    state_fips = gis_models.CharField(max_length=2, blank=True, null=True)
    county_fips = gis_models.CharField(max_length=3, blank=True, null=True)
    tract_ce = gis_models.CharField(max_length=6, blank=True, null=True)
    blockgroup_ce = gis_models.CharField(max_length=1, blank=True, null=True)
    name = gis_models.CharField(max_length=255)
    parent = gis_models.ForeignKey(
        'self', null=True, blank=True,
        on_delete=gis_models.DO_NOTHING,
        related_name='children',
        db_column='parent_geo_id',
    )
    geometry = gis_models.MultiPolygonField(srid=4326)
    internal_point = gis_models.PointField(srid=4326, null=True)
    aland = gis_models.BigIntegerField(null=True)
    awater = gis_models.BigIntegerField(null=True)
    effective_from = gis_models.DateField()
    effective_to = gis_models.DateField(null=True, blank=True)
    is_current = gis_models.BooleanField(default=True)
    source = gis_models.CharField(max_length=50, default='TIGER')

    class Meta(WarehouseModel.Meta):
        db_table = 'dim_geography'
        unique_together = [('geoid', 'vintage_year')]

    def __str__(self):
        return f"{self.name} ({self.geoid}, vintage {self.vintage_year})"


class DimSurvey(WarehouseModel):
    survey_id = gis_models.AutoField(primary_key=True)
    survey_type = gis_models.CharField(max_length=20)
    vintage_year = gis_models.SmallIntegerField()
    period_start = gis_models.SmallIntegerField(null=True)
    period_end = gis_models.SmallIntegerField(null=True)
    release_date = gis_models.DateField(null=True)

    class Meta(WarehouseModel.Meta):
        db_table = 'dim_survey'
        unique_together = [('survey_type', 'vintage_year')]

    def __str__(self):
        if self.period_start:
            return f"{self.survey_type} {self.period_start}-{self.period_end}"
        return f"{self.survey_type} {self.vintage_year}"


class DimCensusVariable(WarehouseModel):
    variable_id = gis_models.AutoField(primary_key=True)
    table_id = gis_models.CharField(max_length=20)
    variable_code = gis_models.CharField(max_length=30, db_index=True)
    label = gis_models.TextField()
    concept = gis_models.TextField(blank=True, null=True)
    variable_type = gis_models.CharField(max_length=20)  # 'extensive' or 'intensive'
    universe = gis_models.TextField(blank=True, null=True)

    class Meta(WarehouseModel.Meta):
        db_table = 'dim_census_variable'
        unique_together = [('table_id', 'variable_code')]

    def __str__(self):
        return f"{self.variable_code}: {self.label}"
```

```python
# warehouse/models/facts.py
from django.contrib.gis.db import models as gis_models
from .base import WarehouseModel
from .dimensions import DimGeography, DimSurvey, DimCensusVariable


class FactAcsEstimate(WarehouseModel):
    fact_id = gis_models.BigAutoField(primary_key=True)
    geo = gis_models.ForeignKey(DimGeography, on_delete=gis_models.DO_NOTHING, db_column='geo_id')
    variable = gis_models.ForeignKey(DimCensusVariable, on_delete=gis_models.DO_NOTHING, db_column='variable_id')
    survey = gis_models.ForeignKey(DimSurvey, on_delete=gis_models.DO_NOTHING, db_column='survey_id')
    estimate = gis_models.DecimalField(max_digits=15, decimal_places=2, null=True)
    margin_of_error = gis_models.DecimalField(max_digits=15, decimal_places=2, null=True)
    coefficient_of_variation = gis_models.DecimalField(max_digits=7, decimal_places=2, null=True)
    reliability = gis_models.CharField(max_length=5, null=True)
    estimate_annotation = gis_models.CharField(max_length=10, blank=True, null=True)
    moe_annotation = gis_models.CharField(max_length=10, blank=True, null=True)

    class Meta(WarehouseModel.Meta):
        db_table = 'fact_acs_estimate'
        unique_together = [('geo', 'variable', 'survey')]


class FactDecennialCount(WarehouseModel):
    fact_id = gis_models.BigAutoField(primary_key=True)
    geo = gis_models.ForeignKey(DimGeography, on_delete=gis_models.DO_NOTHING, db_column='geo_id')
    variable = gis_models.ForeignKey(DimCensusVariable, on_delete=gis_models.DO_NOTHING, db_column='variable_id')
    survey = gis_models.ForeignKey(DimSurvey, on_delete=gis_models.DO_NOTHING, db_column='survey_id')
    count_value = gis_models.BigIntegerField(null=True)

    class Meta(WarehouseModel.Meta):
        db_table = 'fact_decennial_count'
        unique_together = [('geo', 'variable', 'survey')]


class FactUrbanicity(WarehouseModel):
    fact_id = gis_models.BigAutoField(primary_key=True)
    geo = gis_models.ForeignKey(DimGeography, on_delete=gis_models.DO_NOTHING, db_column='geo_id')
    nces_year = gis_models.SmallIntegerField()
    locale_code = gis_models.SmallIntegerField(null=True)
    locale_category = gis_models.CharField(max_length=20, blank=True)
    locale_subcategory = gis_models.CharField(max_length=30, blank=True)
    method = gis_models.CharField(max_length=30)
    source_district_geoid = gis_models.CharField(max_length=20, blank=True, null=True)
    area_overlap_pct = gis_models.DecimalField(max_digits=7, decimal_places=4, null=True)

    class Meta(WarehouseModel.Meta):
        db_table = 'fact_urbanicity'
        unique_together = [('geo', 'nces_year')]


class FactInterpolatedEstimate(WarehouseModel):
    fact_id = gis_models.BigAutoField(primary_key=True)
    target_geo = gis_models.ForeignKey(DimGeography, on_delete=gis_models.DO_NOTHING, db_column='target_geo_id')
    variable = gis_models.ForeignKey(DimCensusVariable, on_delete=gis_models.DO_NOTHING, db_column='variable_id')
    interpolated_value = gis_models.DecimalField(max_digits=15, decimal_places=2, null=True)
    source_survey = gis_models.ForeignKey(DimSurvey, on_delete=gis_models.DO_NOTHING, db_column='source_survey_id', null=True)
    source_vintage_year = gis_models.SmallIntegerField()
    source_summary_level = gis_models.CharField(max_length=10)
    target_summary_level = gis_models.CharField(max_length=10)
    interpolation_method = gis_models.CharField(max_length=50)
    interpolated_at = gis_models.DateTimeField(auto_now_add=True)
    source_reliability_min = gis_models.CharField(max_length=5, null=True)
    area_coverage_pct = gis_models.DecimalField(max_digits=7, decimal_places=4, null=True)
    n_source_units = gis_models.IntegerField(null=True)

    class Meta(WarehouseModel.Meta):
        db_table = 'fact_interpolated_estimate'
        unique_together = [('target_geo', 'variable', 'source_vintage_year', 'interpolation_method')]
```

```python
# warehouse/models/views.py
from django.contrib.gis.db import models as gis_models
from django.db import connections
from .base import WarehouseModel


class MvTractDemographics(WarehouseModel):
    """Materialized view: tracts with pre-joined key demographics and urbanicity."""
    geo_id = gis_models.IntegerField(primary_key=True)
    geoid = gis_models.CharField(max_length=20)
    tract_name = gis_models.CharField(max_length=255)
    state_fips = gis_models.CharField(max_length=2)
    county_fips = gis_models.CharField(max_length=3)
    vintage_year = gis_models.SmallIntegerField()
    geometry = gis_models.MultiPolygonField(srid=4326)
    internal_point = gis_models.PointField(srid=4326, null=True)
    aland = gis_models.BigIntegerField(null=True)
    awater = gis_models.BigIntegerField(null=True)
    acs_vintage = gis_models.SmallIntegerField()

    # Pre-joined demographics
    total_population = gis_models.IntegerField(null=True)
    total_population_moe = gis_models.IntegerField(null=True)
    total_population_reliability = gis_models.CharField(max_length=5, null=True)
    median_household_income = gis_models.DecimalField(max_digits=10, decimal_places=2, null=True)
    median_household_income_moe = gis_models.DecimalField(max_digits=10, decimal_places=2, null=True)
    median_household_income_reliability = gis_models.CharField(max_length=5, null=True)
    median_age = gis_models.DecimalField(max_digits=5, decimal_places=1, null=True)
    median_age_moe = gis_models.DecimalField(max_digits=5, decimal_places=1, null=True)
    pct_poverty = gis_models.DecimalField(max_digits=5, decimal_places=2, null=True)
    pct_white = gis_models.DecimalField(max_digits=5, decimal_places=2, null=True)
    pct_black = gis_models.DecimalField(max_digits=5, decimal_places=2, null=True)
    pct_hispanic = gis_models.DecimalField(max_digits=5, decimal_places=2, null=True)
    pct_asian = gis_models.DecimalField(max_digits=5, decimal_places=2, null=True)

    # Urbanicity
    urbanicity = gis_models.CharField(max_length=20, null=True)
    urbanicity_detail = gis_models.CharField(max_length=30, null=True)
    nces_locale_code = gis_models.SmallIntegerField(null=True)

    class Meta(WarehouseModel.Meta):
        db_table = 'mv_tract_demographics'

    @classmethod
    def refresh(cls, concurrently=True):
        with connections['warehouse'].cursor() as cursor:
            keyword = 'CONCURRENTLY' if concurrently else ''
            cursor.execute(f"REFRESH MATERIALIZED VIEW {keyword} mv_tract_demographics")
```

### 5.5 Property-Style Access Pattern

The materialized views make "property fields" feel natural in Django:

```python
# Query: get tracts near a point with all their demographics
from django.contrib.gis.geos import Point
from django.contrib.gis.measure import D
from warehouse.models import MvTractDemographics

point = Point(-118.2437, 34.0522, srid=4326)  # Downtown LA

tracts = MvTractDemographics.objects.filter(
    geometry__dwithin=(point, D(km=5)),
).order_by('-total_population')

for tract in tracts[:10]:
    print(f"{tract.geoid} {tract.tract_name}")
    print(f"  Pop: {tract.total_population:,} (±{tract.total_population_moe:,})")
    print(f"  Income: ${tract.median_household_income:,.0f}")
    print(f"  {tract.pct_black}% Black, {tract.pct_hispanic}% Hispanic")
    print(f"  Urbanicity: {tract.urbanicity} ({tract.urbanicity_detail})")
```

For the star schema fact tables directly (more flexible, more verbose):

```python
from warehouse.models import DimGeography, FactAcsEstimate, DimSurvey

# All ACS variables for a specific tract in the latest survey
tract_geo = DimGeography.objects.get(geoid='06037101100', is_current=True)
latest_acs = DimSurvey.objects.filter(survey_type='acs5').order_by('-vintage_year').first()

facts = FactAcsEstimate.objects.filter(
    geo=tract_geo,
    survey=latest_acs,
).select_related('variable')

for fact in facts:
    print(f"  {fact.variable.label}: {fact.estimate} (±{fact.margin_of_error}) [{fact.reliability}]")
```

---

## 6. ETL Pipeline

### 6.1 Data Flow

```
Census Bureau API / TIGER Files / NCES / SOS Files
                    │
                    ▼
        ┌───────────────────────┐
        │  Python ETL Pipeline  │
        │  (siege_utilities +   │
        │   management commands)│
        └───────────┬───────────┘
                    │
          ┌─────────┼─────────┐
          ▼         ▼         ▼
    dim_geography  dim_survey  dim_census_variable
                    │
                    ▼
          ┌─────────┼─────────┐
          ▼         ▼         ▼
    fact_acs_*  fact_dec_*  fact_election_*
                    │
                    ▼
        ┌───────────────────────┐
        │  Materialized Views   │
        │  (REFRESH CONCURRENTLY│
        │   via management cmd) │
        └───────────────────────┘
                    │
                    ▼
        ┌───────────────────────┐
        │  PySAL Interpolation  │
        │  (tobler pipeline)    │
        └───────────┬───────────┘
                    │
                    ▼
        fact_interpolated_estimate
```

### 6.2 Load Order

Dimensions must be loaded before facts. Within facts, order doesn't matter.

```bash
# 1. Dimensions (idempotent -- upsert on natural keys)
python manage.py load_dim_geography --vintage 2020 --source TIGER
python manage.py load_dim_geography --vintage 2010 --source TIGER
python manage.py load_dim_survey --type acs5 --vintage 2022
python manage.py load_dim_variables --dataset acs5

# 2. Facts
python manage.py load_acs_facts --vintage 2022 --geography tract --state all
python manage.py load_decennial_facts --vintage 2020 --geography tract --state all
python manage.py load_urbanicity --nces-year 2023

# 3. Materialized views
python manage.py refresh_warehouse_views --concurrent

# 4. Interpolation (when needed)
python manage.py interpolate --source-vintage 2010 --target-vintage 2020 --level tract --state 06
```

### 6.3 Writing to the Warehouse

Django models are read-only. ETL writes use SQLAlchemy or raw psycopg2 through a separate connection:

```python
# warehouse/etl.py
from sqlalchemy import create_engine
import geopandas as gpd


def get_warehouse_engine():
    """SQLAlchemy engine for warehouse ETL (write access)."""
    return create_engine(
        'postgresql+psycopg2://etl_writer:password@warehouse.elect.info:5432/census_warehouse'
    )


def load_geography_dimension(gdf: gpd.GeoDataFrame, vintage_year: int):
    """Load boundary geometries into dim_geography."""
    engine = get_warehouse_engine()
    # ... transform and upsert logic
    gdf.to_postgis('dim_geography', engine, if_exists='append', index=False)
```

---

## 7. Relationship to Existing Models

### What Changes in siege_utilities

The existing `DemographicSnapshot` (GenericFK + JSONField) model in `siege_utilities.geo.django.models.demographics` is a **flexible exploratory tool** — great for notebooks and ad-hoc analysis. The warehouse star schema is the **production analytical store**. They coexist:

| Pattern | Use Case | Where |
|---------|----------|-------|
| `DemographicSnapshot` (JSONField) | Notebook exploration, ad-hoc queries, prototyping | Web app DB |
| Star schema fact tables | Production analytics, API, materialized views | Warehouse DB |
| `DemographicTimeSeries` | Pre-computed longitudinal summaries | Web app DB |

The `DemographicSnapshot` can be **populated from** the warehouse via a sync command:

```python
# Sync latest warehouse data into DemographicSnapshot for notebook users
python manage.py sync_snapshots_from_warehouse --vintage 2022 --level tract
```

### What siege_utilities Provides

siege_utilities continues to own:
- **Boundary models** (the Django ORM layer, managed migrations)
- **Census constants** (canonical level names, FIPS codes, TIGER URLs)
- **NCES constants** (locale codes, urbanicity classification)
- **Timeseries module** (longitudinal data fetching, change metrics, trend classification)
- **Pydantic schemas** (boundary validation, GeoDataFrame conversion)
- **PySAL interpolation wrapper** (su#140)

The warehouse is a **consumer** of siege_utilities — ETL uses siege_utilities functions to fetch, validate, and classify data before loading it into fact tables.

---

## 8. Volume Estimates

### Dimension Tables

| Table | Rows (2 vintages) | Estimated Size |
|-------|-------------------|----------------|
| `dim_geography` (all levels) | ~23M (mostly blocks) | ~15 GB |
| `dim_geography` (excl. blocks) | ~800K | ~3 GB |
| `dim_survey` | ~50 | <1 MB |
| `dim_census_variable` | ~40K | ~10 MB |
| `dim_time` | ~20K (55 years of dates) | ~2 MB |

### Fact Tables

| Table | Rows per vintage (tract-level, ~85K tracts x ~500 variables) | Estimated Size |
|-------|-------------------------------------------------------------|----------------|
| `fact_acs_estimate` (one vintage) | ~42M | ~8 GB |
| `fact_acs_estimate` (5 vintages) | ~210M | ~40 GB |
| `fact_decennial_count` (one vintage) | ~42M | ~5 GB |
| `fact_election_result` (one cycle) | ~2M (precinct-level) | ~500 MB |
| `fact_urbanicity` | ~800K | ~100 MB |
| `fact_interpolated_estimate` | Varies by use case | ~1 GB typical |
| `fact_donation_summary` | ~100K (per cycle) | ~50 MB |

### Materialized Views

| View | Rows | Estimated Size |
|------|------|----------------|
| `mv_tract_demographics` | ~85K | ~600 MB (includes geometry) |
| `mv_county_election_demographics` | ~3.2K | ~50 MB |

### Total Warehouse Size

- **Without blocks**: ~50-60 GB for 5 ACS vintages + 2 decennials + elections
- **With blocks**: Add ~15 GB per vintage for block-level geography
- **Recommended**: Start without blocks; add block-level data as partitioned tables if needed

---

## 9. Partitioning Strategy

For large fact tables, partition by state FIPS to keep individual partitions manageable:

```sql
CREATE TABLE fact_acs_estimate (
    fact_id         BIGSERIAL,
    geo_id          INTEGER NOT NULL,
    variable_id     INTEGER NOT NULL,
    survey_id       INTEGER NOT NULL,
    state_fips      VARCHAR(2) NOT NULL,     -- Denormalized for partitioning
    estimate        NUMERIC,
    margin_of_error NUMERIC,
    coefficient_of_variation NUMERIC,
    reliability     VARCHAR(5),
    estimate_annotation VARCHAR(10),
    moe_annotation  VARCHAR(10),
    PRIMARY KEY (fact_id, state_fips),
    UNIQUE (geo_id, variable_id, survey_id, state_fips)
) PARTITION BY LIST (state_fips);

-- Create partitions for each state
CREATE TABLE fact_acs_estimate_01 PARTITION OF fact_acs_estimate FOR VALUES IN ('01');
CREATE TABLE fact_acs_estimate_02 PARTITION OF fact_acs_estimate FOR VALUES IN ('02');
-- ... etc for all 56 state/territory FIPS codes
```

This keeps each partition under ~1M rows (manageable for index maintenance and vacuum) and enables partition pruning on state-scoped queries.

---

## Appendix A: Relationship to DSTK

The full DSTK replacement capability matrix:

| DSTK Feature | Warehouse Implementation | Status |
|-------------|-------------------------|--------|
| Geocode address → boundaries | `dim_geography` spatial query with `vintage_year` filter | Planned (unified geo schema) |
| Geocode address as of date X | Same + `effective_from`/`effective_to` SCD2 filter | Planned (unified geo schema) |
| Demographics for a point | `mv_tract_demographics` spatial query | Planned (this doc) |
| Demographics for a point as of year X | `fact_acs_estimate` + `dim_geography` with vintage filter | Planned (this doc) |
| Cross-vintage comparison | `fact_acs_estimate` joined twice + `BoundaryCrosswalk` | Planned (this doc + unified geo) |
| Spatial interpolation (change of support) | `fact_interpolated_estimate` via PySAL tobler | Planned (su#140) |
| Urbanicity classification | `fact_urbanicity` from NCES locale overlay | Planned (su#126, su#136) |
| Temporal statistics API | `en#191` Django views on warehouse | Planned |
| Bulk enrichment (geocode + demographics for N addresses) | Warehouse spatial join + fact lookup | Planned |

## Appendix B: Migration from DemographicSnapshot

The existing `DemographicSnapshot` (JSONField) pattern is not being replaced — it continues to serve notebook/exploratory use cases. The warehouse star schema is a new, parallel capability. Data flows from Census Bureau → warehouse (via ETL) → optionally synced to `DemographicSnapshot` (via management command).

No breaking changes to existing siege_utilities or enterprise code.

# NCES Urban-Centric Locale Classification + Project Settings Layer

**Date**: 2026-02-25
**Status**: Section 0 IMPLEMENTED; remainder Design Draft
**Affects**: siege_utilities.conf (settings layer — implemented), siege_utilities.geo.locale (new),
siege_utilities.geo.spatial_data (modifications)
**Epic**: 13 (SW/DSTK Foundation) — su#136-139
**Tickets**: su#144 (settings + CRS fix), remainder TBD

---

## 0. The Missing Settings Layer — IMPLEMENTED

> **Status**: Implemented in `siege_utilities.conf` package. All 8 hardcoded
> `srid=4326` references replaced with `settings.STORAGE_CRS`. Default is now
> NAD83 (EPSG:4269). See `siege_utilities/conf/__init__.py` and
> `siege_utilities/conf/defaults.py`.
>
> ```python
> from siege_utilities.conf import settings
> settings.STORAGE_CRS      # 4269 (NAD83)
> settings.PROJECTION_CRS   # 2163 (US National Atlas Equal Area)
> settings.WEB_CRS          # 4326 (WGS84)
> ```

### Problem

siege_utilities has models for *who* (UserProfile, ClientProfile — name, email,
API keys, branding) and constants for *what's available* (Census URLs, FIPS codes,
TIGER patterns, chart sizes). But there is no layer that controls *how the library
behaves* — the operational defaults that a project needs to override.

When we tried to fix the hardcoded `EPSG:4326`, the question immediately became:
"where does the correct default live?" The answer today is: nowhere configurable.
Every module either hardcodes a literal or reads from `constants.py`, which is
immutable. A project can't say "use NAD83 for storage, Albers for projection,
PostGIS as my spatial backend, and Spark as my tabular engine."

This is the Django `settings.py` problem. Django solved it with a module-level
settings object that every component reads from, overridable per-project.

### What Exists Today

| Module | What It Configures | Scope |
|--------|-------------------|-------|
| `config/constants.py` | Timeouts, chart sizes, file thresholds | Library-wide, immutable |
| `config/census_constants.py` | Census URLs, FIPS, TIGER patterns | Library-wide, immutable |
| `config/nces_constants.py` | NCES URLs, locale codes, thresholds | Library-wide, immutable |
| `config/user_config.py` | User prefs in `~/.siege_utilities/config/` | Per-user |
| `config/enhanced_config.py` | Pydantic-validated user/client profiles | Per-user/client |
| `config/projects.py` | Project dirs and metadata | Per-project (but only paths) |
| `config/clients.py` | Client branding, report prefs | Per-client |
| `config/databases.py` | Database connection definitions | Per-environment |

### What's Missing

A **project-level settings** layer that controls operational behavior:

- **Geo settings**: Storage CRS, projection CRS, input CRS, distance units
- **Engine settings**: Default tabular engine (Spark/Pandas/Polars), spatial
  backend (PostGIS/Sedona/GeoPandas), fallback chain
- **Data settings**: Default Census year, default ACS vintage, TIGER cache dir
- **Pipeline settings**: Provenance tracking, quality checks, logging verbosity
- **Feature flags**: Enable/disable optional modules (DuckDB, Databricks, etc.)

### Proposed: `siege_utilities.conf` Settings Object

Like Django's `settings`, siege_utilities needs a singleton settings object that
modules read from. Resolution order (highest priority first):

1. **Function/method parameter** — explicit override in code
2. **Environment variable** — `SU_STORAGE_CRS=4269`, `SU_TABULAR_ENGINE=spark`
3. **Project settings file** — `siege_utilities.yaml` in project root (or path
   set by `SU_SETTINGS_FILE` env var)
4. **Library defaults** — `config/defaults.py` (replaces scattering across
   `constants.py`, `census_constants.py`, etc.)

```python
# siege_utilities/conf/__init__.py

class Settings:
    """Lazy-loaded settings object, Django-style.

    Reads from (in priority order):
    1. Environment variables (SU_* prefix)
    2. Project settings file (siege_utilities.yaml)
    3. Library defaults
    """

    # --- Geo ---
    STORAGE_CRS: int = 4269       # NAD83 — native Census/TIGER datum
    PROJECTION_CRS: int = 2163    # US National Atlas Equal Area
    INPUT_CRS: int = 4269         # Assumed when data has no .prj
    DISTANCE_UNITS: str = "miles" # "miles", "km", "meters"

    # --- Engine ---
    TABULAR_ENGINE: str = "pandas"   # "pandas", "spark", "polars", "databricks"
    SPATIAL_BACKEND: str = "geopandas"  # "geopandas", "postgis", "sedona"
    SPATIAL_FALLBACK_CHAIN: list = ["sedona", "geopandas", "pandas"]

    # --- Data ---
    DEFAULT_CENSUS_YEAR: int = 2020
    TIGER_CACHE_DIR: str = "~/.siege_utilities/cache/tiger"

    # --- Pipeline ---
    ENABLE_PROVENANCE: bool = True
    ENABLE_QUALITY_CHECKS: bool = True

    def __init__(self):
        self._loaded = False

    def _load(self):
        """Load settings from env vars and project file."""
        if self._loaded:
            return
        # 1. Set library defaults (already done via class attributes)
        # 2. Override from project settings file
        self._load_from_file()
        # 3. Override from environment variables
        self._load_from_env()
        self._loaded = True

    def _load_from_file(self):
        """Load from siege_utilities.yaml if present."""
        import os, yaml
        settings_file = os.environ.get(
            "SU_SETTINGS_FILE",
            "siege_utilities.yaml"
        )
        # Walk up from CWD looking for the file (like pyproject.toml)
        ...

    def _load_from_env(self):
        """Override from SU_* environment variables."""
        import os
        prefix = "SU_"
        for attr in dir(self):
            if attr.startswith("_") or not attr.isupper():
                continue
            env_key = f"{prefix}{attr}"
            env_val = os.environ.get(env_key)
            if env_val is not None:
                # Coerce to the attribute's current type
                current = getattr(self, attr)
                if isinstance(current, bool):
                    setattr(self, attr, env_val.lower() in ("1", "true", "yes"))
                elif isinstance(current, int):
                    setattr(self, attr, int(env_val))
                elif isinstance(current, list):
                    setattr(self, attr, [s.strip() for s in env_val.split(",")])
                else:
                    setattr(self, attr, env_val)

    def __getattr__(self, name):
        if not name.startswith("_"):
            self._load()
            return object.__getattribute__(self, name)
        raise AttributeError(name)


# Module-level singleton — every module imports this
settings = Settings()
```

### Usage

```python
# In any siege_utilities module:
from siege_utilities.conf import settings

srid = gdf.crs.to_epsg() if gdf.crs else settings.STORAGE_CRS

# In PostGISConnector:
create_sql = f"... GEOMETRY({pg_geom_type}, {settings.STORAGE_CRS})"

# In Django model:
geometry = models.MultiPolygonField(srid=settings.STORAGE_CRS)

# In NCESLocaleClassifier:
proj_crs = projection_crs or settings.PROJECTION_CRS
```

### Project Settings File

```yaml
# siege_utilities.yaml (in project root)

geo:
  storage_crs: 4269
  projection_crs: 2163
  input_crs: 4269
  distance_units: miles

engine:
  tabular: spark
  spatial: geopandas
  spatial_fallback:
    - sedona
    - geopandas
    - pandas

data:
  default_census_year: 2020
  tiger_cache_dir: /data/cache/tiger

pipeline:
  enable_provenance: true
  enable_quality_checks: true
```

### Why Not Just Environment Variables

Environment variables work for single values (`SU_STORAGE_CRS=4269`) but:
- They don't express structure (the fallback chain is a list)
- They can't be checked into a repo (unlike `siege_utilities.yaml`)
- They're invisible — you can't `cat` the complete configuration
- They conflict across projects in the same shell session

The settings file is the canonical configuration; env vars are the override
mechanism for CI, containers, and one-off adjustments.

### Relationship to Existing Config

The existing config modules don't go away:
- `constants.py` stays — it holds truly immutable library metadata and
  computation constants (chart sizes, timeout multipliers)
- `census_constants.py` stays — FIPS codes, geographic hierarchies, API URLs
- `nces_constants.py` stays — locale code mappings, NCES data URLs
- `user_config.py` stays — personal preferences (download dir, color scheme)
- `clients.py` stays — client branding and report preferences

The new `conf/settings.py` is the **operational defaults layer** between them:

```
constants.py         ← immutable library facts (FIPS, URLs, chart sizes)
conf/settings.py     ← operational defaults (CRS, engine, pipeline behavior)  ← NEW
user_config.py       ← personal preferences (download dir, color scheme)
clients.py           ← client-specific (branding, report format)
projects.py          ← project-specific (directories, metadata)
```

Every module that currently reads from `constants.py` for an operational default
should instead read from `settings`. Constants are for things that never change
(a FIPS code is a FIPS code). Settings are for things that *could* change per
project but have sensible defaults.

---

## 1. What NCES Locale Codes Are

The National Center for Education Statistics (NCES) classifies all U.S. territory into
12 locale codes organized in a 4x3 grid. The four major types — City, Suburban, Town,
Rural — each have three subtypes differentiated by population size (City/Suburb) or
proximity to urban centers (Town/Rural).

NCES publishes pre-computed locale assignments for schools and school districts, but
the classification algorithm itself is reproducible from Census spatial data. Reproducing
it ourselves is important because:

1. We want to classify **arbitrary points and polygons**, not just schools
2. We want locale codes for **any year**, not just the years NCES publishes
3. We want to use locale classification as a **dimension** in the warehouse star schema

### The 12 Locale Codes

| Code | Type | Subtype | Classification Rule |
|------|------|---------|---------------------|
| 11 | City | Large | Inside Urbanized Area (UA), inside principal city, city pop >= 250,000 |
| 12 | City | Midsize | Inside UA, inside principal city, city pop 100,000-249,999 |
| 13 | City | Small | Inside UA, inside principal city, city pop < 100,000 |
| 21 | Suburb | Large | Inside UA, **outside** principal city, UA pop >= 250,000 |
| 22 | Suburb | Midsize | Inside UA, outside principal city, UA pop 100,000-249,999 |
| 23 | Suburb | Small | Inside UA, outside principal city, UA pop < 100,000 |
| 31 | Town | Fringe | Inside Urban Cluster (UC), <= 10 mi from nearest UA |
| 32 | Town | Distant | Inside UC, 10-35 mi from nearest UA |
| 33 | Town | Remote | Inside UC, > 35 mi from nearest UA |
| 41 | Rural | Fringe | Not in UA or UC, <= 5 mi from UA **or** <= 2.5 mi from UC |
| 42 | Rural | Distant | Not in UA/UC, 5-25 mi from UA **or** 2.5-10 mi from UC |
| 43 | Rural | Remote | Not in UA/UC, > 25 mi from UA **and** > 10 mi from UC |

### Key Definitions (Census Bureau)

- **Urbanized Area (UA)**: Densely settled territory with population >= 50,000.
  Defined from census block-level population density. Boundaries published decennially
  (2010, 2020) with the TIGER/Line UAC shapefile.

- **Urban Cluster (UC)**: Densely settled territory with population 2,500-49,999.
  Same methodology as UA, just smaller. Also in the UAC shapefile. (Note: the 2020
  Census eliminated the UC designation, merging all urban areas into a single
  classification with a 5,000-person minimum. For locale classification using 2020+
  data, UCs from the 2010 Census may still be needed, or the threshold logic adjusts.)

- **Principal City**: The largest city within a Core-Based Statistical Area (CBSA),
  plus any city meeting certain employment or population thresholds. Listed in the
  OMB CBSA delineation files. In TIGER terms, these are Places that have been
  designated as principal cities.

- **Distance**: NCES uses **Euclidean (straight-line) distance**, not road distance.
  This is deliberate — Euclidean distance is stable across years, unaffected by
  road network changes, analytically reproducible, and simple to implement.

### Sources

- [NCES Locale Definitions](https://nces.ed.gov/surveys/annualreports/topical-studies/locale/definitions)
- [NCES Locale Boundaries (shapefile downloads)](https://nces.ed.gov/programs/edge/Geographic/LocaleBoundaries)
- [NCES Locale Framework (PDF)](https://nces.ed.gov/programs/edge/docs/NCES_Locale_Framework.pdf)
- [NCES Locale Technical Memo (PDF)](https://nces.ed.gov/programs/edge/docs/NCES_LOCALE_TECHMEMO_051222.pdf)
- [NCES Urban-Centric Categories (2006 original)](https://nces.ed.gov/pubs2007/ruraled/exhibit_a.asp)

---

## 2. The Classification Algorithm

### Required Spatial Inputs

| Layer | Source | Geometry Type | Scope | TIGER Name |
|-------|--------|---------------|-------|------------|
| Urbanized Areas | Census TIGER UAC | MultiPolygon | National | `uac` / `uac20` |
| Urban Clusters | Census TIGER UAC | MultiPolygon | National | Same file as UA (filtered by `UATYP10`) |
| Places | Census TIGER PLACE | MultiPolygon | Per-state | `place` |
| Principal City list | OMB CBSA delineation | Tabular | National | Not in TIGER — CSV from OMB/Census |
| Place populations | Census PL/ACS | Tabular | National | Census API or PL files |
| UA populations | Census TIGER UAC attributes | Tabular | National | Attribute of UAC shapefile (`ALAND10`, `POP10`) |

### Required Tabular Inputs

| Data | Source | Purpose |
|------|--------|---------|
| CBSA delineation file | OMB (via Census) | Maps principal cities to CBSAs |
| Place population estimates | Census Population Estimates Program | Current-year city populations for size classification |
| UA/UC population | UAC shapefile attributes | UA/UC population for suburb size classification |

### Decision Tree (per point)

```
classify_point(lon, lat):

    # Step 1: Is the point inside an Urbanized Area?
    ua = spatial_join(point, urbanized_areas)

    if ua is not None:
        # Step 2: Is it inside a principal city Place?
        place = spatial_join(point, principal_city_places)

        if place is not None:
            # CITY — subtype by principal city population
            pop = place.population
            if pop >= 250_000:   return 11  # City-Large
            if pop >= 100_000:   return 12  # City-Midsize
            return 13                        # City-Small
        else:
            # SUBURB — subtype by UA population
            ua_pop = ua.population
            if ua_pop >= 250_000: return 21  # Suburb-Large
            if ua_pop >= 100_000: return 22  # Suburb-Midsize
            return 23                         # Suburb-Small

    # Step 3: Is the point inside an Urban Cluster?
    uc = spatial_join(point, urban_clusters)

    if uc is not None:
        # TOWN — subtype by distance to nearest UA boundary
        d_ua = nearest_distance(point, urbanized_areas)  # Euclidean, miles
        if d_ua <= 10:  return 31  # Town-Fringe
        if d_ua <= 35:  return 32  # Town-Distant
        return 33                   # Town-Remote

    # Step 4: Rural — subtype by distance to nearest UA AND nearest UC
    d_ua = nearest_distance(point, urbanized_areas)   # Euclidean, miles
    d_uc = nearest_distance(point, urban_clusters)    # Euclidean, miles

    # RURAL — two-threshold system
    if d_ua <= 5 or d_uc <= 2.5:
        return 41  # Rural-Fringe
    if d_ua <= 25 or d_uc <= 10:
        return 42  # Rural-Distant
    return 43      # Rural-Remote
```

### Distance Computation

Distances are Euclidean (straight-line) measured in **miles**. For geographic
coordinates (NAD83/4269 or WGS84/4326), this requires projecting to an
equal-area/equal-distance CRS. You **cannot** compute meaningful distances
in a geodetic CRS — the units are degrees, not meters.

The practical approach:

1. Project both point and boundary polygons to the configured projection CRS
   (default: US National Atlas Equal Area, EPSG:2163; override for AK/HI)
2. Compute `point.distance(polygon_boundary)` in meters
3. Convert meters to miles (/ 1609.344)

The projection CRS is not hardcoded — it's read from `DEFAULT_PROJECTION_CRS`
in `siege_utilities.config.geo_constants` and can be overridden per-classifier
instance or via the `SU_PROJECTION_CRS` environment variable.

For bulk operations, `geopandas.sjoin_nearest()` with `distance_col` handles
this efficiently. For simple containment checks (Steps 1-3), `geopandas.sjoin()`
with `predicate='within'` is sufficient.

### Gap Year Handling

Census UA/UC boundaries are defined at the decennial census (2010, 2020).
Between decennials, NCES uses the most recent boundaries but updates
population estimates annually.

Our approach:
- **Boundaries**: Use the most recent decennial (2020 boundaries for 2020-2029,
  2010 boundaries for 2010-2019)
- **Populations**: Use the most recent annual estimates from Census PEP
- **Principal city lists**: Use the most recent OMB CBSA delineation

This means a point's locale code can change between years even without
boundary changes, because city populations cross thresholds.

---

## 3. Point-Level Classification and Polygon Aggregation

### Why Point-Level Matters

The user's key insight: if every point can be classified, then any arbitrary
polygon can be classified by the distribution of points it contains.

**Use cases:**
- Classify a **geocoded address** → single locale code
- Classify a **census tract** → majority locale code, or distribution
- Classify a **congressional district** → distribution of locale codes
  (e.g., "CD-07 is 40% Suburb-Large, 30% City-Large, 20% Town-Fringe, 10% Rural-Fringe")
- Classify a **custom region** (sales territory, campaign region) → distribution

### Polygon Classification Methods

Given a polygon P and a set of classified points within it:

1. **Majority rule**: The locale code held by the plurality of points
2. **Area-weighted**: Intersect P with the pre-computed locale territory polygons,
   report the fraction of P's area in each locale
3. **Population-weighted**: Weight each point's locale code by the population
   at that point (requires population data at the point level)
4. **Distribution**: Return the full distribution as a dict
   `{11: 0.40, 21: 0.30, 31: 0.20, 41: 0.10}`

Method 2 (area-weighted) is the most faithful to the NCES methodology, since
NCES classifies territory, not points. But method 1 is cheapest and often
sufficient for large polygons.

### Pre-Computed Locale Territory

Rather than classifying points on the fly, we can pre-compute the locale
territory for the entire US as a set of polygons (one per locale code).
NCES actually publishes this as the **Locale Boundaries** shapefile.

For maximum flexibility, we support both:
- **Pre-computed**: Download NCES locale boundary shapefiles, spatial join
- **On-the-fly**: Compute from Census UA/UC/Place inputs (for custom years
  or when NCES boundaries aren't available)

---

## 4. Required Changes to Spatial Data Stack

### Problem A: Hardcoded CRS (EPSG:4326 Everywhere)

Six locations across four files hardcode `srid=4326` (WGS84). This is wrong
for two reasons:

1. **Census TIGER data is NAD83 (EPSG:4269)**, not WGS84. The two are
   practically identical for positioning (~1-2m difference in CONUS) but
   they're different datums. Storing NAD83 data tagged as WGS84 is
   technically incorrect and creates confusion when data from other sources
   (with real WGS84 coordinates) is mixed in.

2. **Distance and area computations in 4326/4269 are meaningless** — the
   units are degrees, not meters. Any operation that needs distance or area
   must project to an appropriate CRS first. The current code doesn't
   enforce or facilitate this.

Hardcoded locations:

| File | Line(s) | Usage |
|------|---------|-------|
| `spatial_transformations.py` | 388 | `GEOMETRY(POLYGON, 4326)` in PostGIS DDL |
| `django/models/base.py` | 40-41 | `srid=4326` on MultiPolygonField |
| `django/managers/boundary_manager.py` | 34, 228, 234 | `Point(..., srid=4326)`, `GEOSGeometry(..., srid=4326)` |
| `django/services/population_service.py` | 212-213, 292, 294 | Force-reproject to 4326, `GEOSGeometry(..., srid=4326)` |

`distributed/spark_utils.py` already does this correctly — `reproject_geom_columns()`
takes `source_srid` and `target_srid` as parameters.

### Proposed CRS Architecture

CRS defaults live in the settings layer described in Section 0:

```python
from siege_utilities.conf import settings

settings.STORAGE_CRS       # 4269 (NAD83) — what gets written to PostGIS/Django
settings.PROJECTION_CRS    # 2163 (US Natl Atlas Equal Area) — distance/area ops
settings.INPUT_CRS         # 4269 (NAD83) — assumed when data has no .prj
```

These are overridable per-project (`siege_utilities.yaml`), per-environment
(`SU_STORAGE_CRS=4326`), or per-call (function parameters).

Every current `4326` literal becomes `settings.STORAGE_CRS`. The Django model
field becomes `srid=settings.STORAGE_CRS`. The PostGIS connector detects CRS
from the GeoDataFrame and falls back to `settings.STORAGE_CRS`.

### Problem B: Geometry Type Blindness

The current `BOUNDARY_TYPE_CATALOG` and `TIGER_FILE_PATTERNS` don't track
geometry type. The `PostGISConnector._create_spatial_table` hardcodes
`GEOMETRY(POLYGON, 4326)`. This breaks for:

| Layer | Geometry Type | Example |
|-------|---------------|---------|
| Roads | MultiLineString | `tl_2024_06_roads.zip` |
| Rails | MultiLineString | `tl_2024_us_rails.zip` |
| Linear Water | MultiLineString | `tl_2024_06_linearwater.zip` |
| Edges | MultiLineString | `tl_2024_06_edges.zip` |
| Address Features | MultiLineString | `tl_2024_06_addrfeat.zip` |
| Point Landmarks | Point | Not yet in catalog |
| Geocoded Addresses | Point | User-supplied |

For NCES locale classification specifically, we only need polygons (UA, UC,
Place). But the spatial data stack should handle all geometry types because:
1. Address geocoding produces points
2. Road network analysis needs lines
3. The SW warehouse will ingest all of these

### Proposed Changes

#### 4a. Add `geometry_type` to `BOUNDARY_TYPE_CATALOG`

```python
BOUNDARY_TYPE_CATALOG = {
    'state':        {'category': 'redistricting', 'abbrev': 'STATE',
                     'name': 'State Boundaries', 'geometry_type': 'MultiPolygon'},
    'county':       {'category': 'redistricting', 'abbrev': 'COUNTY',
                     'name': 'County Boundaries', 'geometry_type': 'MultiPolygon'},
    # ...
    'roads':        {'category': 'general', 'abbrev': 'ROADS',
                     'name': 'Roads', 'geometry_type': 'MultiLineString'},
    'rails':        {'category': 'general', 'abbrev': 'RAILS',
                     'name': 'Railroads', 'geometry_type': 'MultiLineString'},
    'linear_water': {'category': 'general', 'abbrev': 'LINEARWATER',
                     'name': 'Linear Water Features', 'geometry_type': 'MultiLineString'},
    'edges':        {'category': 'general', 'abbrev': 'EDGES',
                     'name': 'All Edges', 'geometry_type': 'MultiLineString'},
    'address_features': {'category': 'general', 'abbrev': 'ADDRFEAT',
                     'name': 'Address Features', 'geometry_type': 'MultiLineString'},
    'uac':          {'category': 'general', 'abbrev': 'UAC',
                     'name': 'Urban Areas', 'geometry_type': 'MultiPolygon'},
    'uac20':        {'category': 'general', 'abbrev': 'UAC20',
                     'name': 'Urban Areas (2020)', 'geometry_type': 'MultiPolygon'},
    # new entries:
    'pointlm':      {'category': 'general', 'abbrev': 'POINTLM',
                     'name': 'Point Landmarks', 'geometry_type': 'Point'},
    'arealm':       {'category': 'general', 'abbrev': 'AREALM',
                     'name': 'Area Landmarks', 'geometry_type': 'MultiPolygon'},
}
```

#### 4b. Add missing entries to `TIGER_FILE_PATTERNS`

The following are in `BOUNDARY_TYPE_CATALOG` (for discovery) but missing from
`TIGER_FILE_PATTERNS` (for download URL construction):

```python
# National-scope files (no state FIPS)
"uac":     "tl_{year}_us_uac20.zip",     # or uac10 for pre-2020
"uac20":   "tl_{year}_us_uac20.zip",
"cbsa":    "tl_{year}_us_cbsa.zip",
"rails":   "tl_{year}_us_rails.zip",
"aiannh":  "tl_{year}_us_aiannh.zip",

# State-scope files (require state FIPS)
"roads":            "tl_{year}_{state_fips}_roads.zip",
"linear_water":     "tl_{year}_{state_fips}_linearwater.zip",
"area_water":       "tl_{year}_{state_fips}_areawater.zip",
"edges":            "tl_{year}_{state_fips}_edges.zip",
"address_features": "tl_{year}_{state_fips}_addrfeat.zip",
"pointlm":          "tl_{year}_{state_fips}_pointlm.zip",
"arealm":           "tl_{year}_{state_fips}_arealm.zip",
"elsd":             "tl_{year}_{state_fips}_elsd.zip",
"scsd":             "tl_{year}_{state_fips}_scsd.zip",
"unsd":             "tl_{year}_{state_fips}_unsd.zip",
```

#### 4c. Fix `PostGISConnector._create_spatial_table` to detect geometry type and CRS

Instead of hardcoding `GEOMETRY(POLYGON, 4326)`:

```python
from siege_utilities.conf import settings

def _create_spatial_table(self, table_name: str, gdf: GeoDataFrame):
    """Create a spatial table in PostGIS with correct geometry type and CRS."""
    # Detect geometry type from the data
    geom_type = gdf.geometry.geom_type.unique()
    if len(geom_type) == 1:
        pg_geom_type = geom_type[0].upper()
    else:
        pg_geom_type = "GEOMETRY"  # mixed types — use generic

    # Detect CRS from data, fall back to configured default (NAD83)
    srid = gdf.crs.to_epsg() if gdf.crs else settings.STORAGE_CRS

    cursor = self.connection.cursor()
    create_sql = f"""
    CREATE TABLE IF NOT EXISTS {table_name} (
        id SERIAL PRIMARY KEY,
        geom GEOMETRY({pg_geom_type}, {srid})
    );
    """
    cursor.execute(create_sql)
    self.connection.commit()
```

---

## 5. Proposed Module: `siege_utilities.geo.locale`

### API Surface

```python
# siege_utilities/geo/locale.py

from dataclasses import dataclass
from typing import Optional
from enum import IntEnum

class LocaleType(IntEnum):
    """NCES major locale types."""
    CITY = 1
    SUBURB = 2
    TOWN = 3
    RURAL = 4

@dataclass(frozen=True)
class LocaleCode:
    """An NCES 12-code locale classification."""
    code: int           # 11-43
    type: LocaleType    # City, Suburb, Town, Rural
    subtype: str        # Large/Midsize/Small or Fringe/Distant/Remote

    @property
    def label(self) -> str:
        """Human-readable label: 'City-Large', 'Rural-Remote', etc."""
        return f"{self.type.name.title()}-{self.subtype}"

    @classmethod
    def from_code(cls, code: int) -> "LocaleCode":
        """Construct from integer code (11-43)."""
        ...

# Pre-defined constants
CITY_LARGE = LocaleCode(11, LocaleType.CITY, "Large")
CITY_MIDSIZE = LocaleCode(12, LocaleType.CITY, "Midsize")
# ... all 12


class NCESLocaleClassifier:
    """Classify geographic points and polygons into NCES locale codes.

    Uses Census TIGER spatial data (Urbanized Areas, Urban Clusters,
    Places) and OMB CBSA principal city designations to implement the
    NCES urban-centric locale classification algorithm.

    The classifier operates in two modes:
    1. Pre-computed: Uses NCES-published locale boundary shapefiles
    2. On-the-fly: Computes from Census inputs (for custom years/data)
    """

    def __init__(
        self,
        census_year: int = 2020,
        mode: str = "precomputed",  # "precomputed" or "computed"
        cache_dir: Optional[Path] = None,
        projection_crs: Optional[int] = None,
    ):
        """Initialize classifier and load spatial data.

        Args:
            census_year: Census vintage for boundaries (2010 or 2020)
            mode: "precomputed" uses NCES shapefiles, "computed" uses
                  Census UA/UC/Place inputs
            cache_dir: Directory for caching downloaded shapefiles
            projection_crs: EPSG code for distance/area computations.
                If None, uses DEFAULT_PROJECTION_CRS from config
                (EPSG:2163 US National Atlas Equal Area).
                Override for Alaska (EPSG:3338) or Hawaii (EPSG:26963).
        """
        ...

    def classify_point(self, lon: float, lat: float) -> LocaleCode:
        """Classify a single point.

        Args:
            lon: Longitude (WGS84)
            lat: Latitude (WGS84)

        Returns:
            LocaleCode for the point's location
        """
        ...

    def classify_points(
        self,
        gdf: "GeoDataFrame",
        geometry_col: str = "geometry",
    ) -> "GeoDataFrame":
        """Bulk classify a GeoDataFrame of points.

        Adds columns: locale_code (int), locale_type (str),
        locale_subtype (str), locale_label (str).

        Uses geopandas.sjoin for containment tests and
        sjoin_nearest for distance computation. Projects to
        EPSG:2163 (US National Atlas Equal Area) for distance.

        Args:
            gdf: GeoDataFrame with point geometries
            geometry_col: Name of geometry column

        Returns:
            Input GeoDataFrame with locale columns added
        """
        ...

    def classify_polygon(
        self,
        geometry: "BaseGeometry",
        method: str = "area_weighted",
    ) -> dict:
        """Classify a polygon by locale distribution.

        Args:
            geometry: Shapely polygon or multipolygon
            method: "area_weighted", "majority", or "distribution"

        Returns:
            If method=="majority": {"locale_code": 21, "locale_label": "Suburb-Large"}
            If method=="distribution": {11: 0.40, 21: 0.30, 31: 0.20, 41: 0.10}
            If method=="area_weighted": same as distribution
        """
        ...

    def classify_polygons(
        self,
        gdf: "GeoDataFrame",
        method: str = "majority",
    ) -> "GeoDataFrame":
        """Bulk classify a GeoDataFrame of polygons.

        Adds locale columns based on the chosen method.
        For "majority", adds locale_code, locale_type, locale_subtype.
        For "distribution", adds locale_dist (dict column).

        Args:
            gdf: GeoDataFrame with polygon geometries
            method: Classification method for polygons

        Returns:
            Input GeoDataFrame with locale columns added
        """
        ...

    @staticmethod
    def locale_label(code: int) -> str:
        """Convert integer code to human label.

        >>> NCESLocaleClassifier.locale_label(11)
        'City-Large'
        >>> NCESLocaleClassifier.locale_label(43)
        'Rural-Remote'
        """
        return LocaleCode.from_code(code).label
```

### Internal Implementation Sketch

```python
class NCESLocaleClassifier:

    def _load_precomputed(self):
        """Download and cache NCES locale boundary shapefiles."""
        # NCES publishes state-level and national locale boundary files
        # at https://nces.ed.gov/programs/edge/Geographic/LocaleBoundaries
        # These are pre-classified territory polygons with locale codes
        ...

    def _load_computed(self):
        """Load Census UA/UC/Place layers for on-the-fly classification."""
        from siege_utilities.geo.spatial_data import CensusDataSource

        census = CensusDataSource()

        # National layers
        self._ua_gdf = census.get_geographic_boundaries(
            year=self.census_year, geographic_level='uac'
        )
        # Split UA vs UC
        # 2010: UATYP10 == 'U' (urbanized area) vs 'C' (urban cluster)
        # 2020: All are UA (Census eliminated UC designation)
        self._urbanized_areas = self._ua_gdf[self._ua_gdf['uatyp10'] == 'U']
        self._urban_clusters = self._ua_gdf[self._ua_gdf['uatyp10'] == 'C']

        # Per-state place boundaries (national file not always available)
        # For bulk: iterate states, download and concatenate
        self._places_gdf = self._load_all_places()

        # Filter to principal cities only
        self._principal_cities = self._identify_principal_cities()

        # Project to equal-area CRS for distance computations
        # Uses configured default from settings (EPSG:2163 US National Atlas
        # Equal Area), but caller can override via projection_crs parameter
        # for Alaska (3338), Hawaii (26963), or non-US data
        from siege_utilities.conf import settings
        proj = projection_crs or settings.PROJECTION_CRS
        self._crs_proj = f"EPSG:{proj}"
        self._ua_proj = self._urbanized_areas.to_crs(self._crs_proj)
        self._uc_proj = self._urban_clusters.to_crs(self._crs_proj)

    def _identify_principal_cities(self) -> "GeoDataFrame":
        """Cross-reference Places with OMB CBSA principal city list.

        The OMB CBSA delineation file lists principal cities by name
        and state. We match these to Place geometries by name + state FIPS.

        Source: https://www.census.gov/geographies/reference-files/time-series/demo/metro-micro/delineation-files.html
        """
        ...

    def _compute_distances_to_ua(self, points_proj: "GeoDataFrame") -> "Series":
        """Compute Euclidean distance from each point to nearest UA boundary.

        Uses geopandas.sjoin_nearest with EPSG:2163 projection.
        Returns distances in miles.
        """
        ...

    def _compute_distances_to_uc(self, points_proj: "GeoDataFrame") -> "Series":
        """Same as above but for Urban Clusters."""
        ...
```

### Integration with Existing Stack

The classifier integrates with existing siege_utilities modules:

```
siege_utilities.geo.spatial_data.CensusDataSource
    → Downloads UA/UC/Place shapefiles via TIGER
    → Requires geometry_type awareness (section 4)

siege_utilities.geo.locale.NCESLocaleClassifier
    → Uses CensusDataSource for input layers
    → Pure GeoPandas internally (Tier 1 spatial)
    → Output is flat columns (int code + string labels)

siege_utilities.distributed.spark_utils (or Pandas/Polars/Databricks)
    → Receives classified points as tabular data (Tier 2 tabular)
    → Locale code is just an integer column — any engine handles it
```

This is the **two-tier pattern** in action:
- **Tier 1 (Spatial)**: Classification runs in GeoPandas. Always. Even on
  Databricks without Sedona, because it's a local operation on reference data.
- **Tier 2 (Tabular)**: Once classified, the locale code column is pushed to
  whatever tabular engine the project uses. No spatial libraries needed.

---

## 6. The 2020 Census Urban Area Complication

The 2020 Census changed the urban area methodology:

- **2010**: Urbanized Areas (pop >= 50,000) and Urban Clusters (pop 2,500-49,999)
  are separate designations. The locale algorithm depends on this distinction.
- **2020**: Urban Clusters were **eliminated**. All urban areas now have a minimum
  population threshold of 5,000. There is no UA/UC split.

This affects Town and Rural classifications, which depend on the UA/UC distinction.

**Options:**
1. For 2020+ data, use 2010 UC boundaries for the UC distance thresholds
   (NCES appears to do something similar)
2. Treat all 2020 urban areas < 50,000 as de facto UCs
3. Use the 2020 urban area boundaries directly and adjust thresholds

We should check what NCES actually does for their 2024/2025 locale files and
follow their precedent. The NCES locale boundary files from 2024 are downloadable
and would reveal their approach.

---

## 7. Test Plan

### Unit Tests (`tests/unit/test_locale.py`)

1. `test_locale_code_from_int` — all 12 codes round-trip correctly
2. `test_locale_code_labels` — labels match expected strings
3. `test_locale_type_enum` — City=1, Suburb=2, Town=3, Rural=4
4. `test_classify_known_city` — point in Manhattan → City-Large (11)
5. `test_classify_known_suburb` — point in Bethesda MD → Suburb-Large (21)
6. `test_classify_known_town` — point in small UC → Town-Fringe/Distant/Remote
7. `test_classify_known_rural` — point in Wyoming → Rural-Remote (43)
8. `test_distance_computation` — known distance pairs validate Euclidean math
9. `test_polygon_majority` — tract with mixed locale → correct majority
10. `test_polygon_distribution` — tract returns correct fractional distribution
11. `test_gap_year_boundary_selection` — 2023 uses 2020 boundaries
12. `test_precomputed_vs_computed` — both modes agree on sample points

### Integration Tests (require network / Census data)

13. `test_download_uac_shapefile` — CensusDataSource can fetch UAC
14. `test_download_place_shapefile` — CensusDataSource can fetch Places
15. `test_classify_sample_addresses` — end-to-end on geocoded addresses
16. `test_classify_congressional_districts` — CDs get reasonable distributions

---

## 8. Implementation Sequence

| Order | Task | Size | Depends On |
|-------|------|------|------------|
| 1 | Create `siege_utilities/conf/` settings layer with defaults + env + YAML | M | None |
| 2 | Replace all hardcoded `4326` with `settings.STORAGE_CRS` (6 locations, 4 files) | M | #1 |
| 3 | Add `geometry_type` to `BOUNDARY_TYPE_CATALOG` | XS | None |
| 4 | Add missing entries to `TIGER_FILE_PATTERNS` | S | None |
| 5 | Fix `PostGISConnector._create_spatial_table` geometry + CRS detection | S | #1, #3 |
| 6 | Add `pointlm`, `arealm` to catalog + patterns | XS | #3, #4 |
| 7 | Create `siege_utilities/geo/locale.py` with `LocaleCode` dataclass | S | None |
| 8 | Implement `NCESLocaleClassifier` precomputed mode | M | #1, #7 |
| 9 | Implement `NCESLocaleClassifier` computed mode | L | #1, #4, #7 |
| 10 | Implement `classify_polygon` / `classify_polygons` | M | #8 or #9 |
| 11 | Unit tests (1-12) | M | #7-#10 |
| 12 | Integration tests (13-16) | M | #8-#10 |

**Task #1 is the keystone.** The settings layer is not just a CRS fix — it's the
foundation for engine selection, pipeline behavior, and every other operational
default. Once `siege_utilities.conf.settings` exists, every module has a single,
consistent way to read configurable defaults.

Tasks 3-6 (spatial data fixes) can proceed in parallel with tasks 7-12 (locale
module), but both depend on #1 for CRS awareness.

---

## 9. Open Questions

1. **2020 Census UC elimination**: What does NCES do for 2024 locale files?
   Download their 2024 boundaries and compare to the algorithm output.

2. **Principal city identification**: The OMB CBSA delineation file changes annually.
   Should we bundle a copy or download fresh? Bundling is simpler; downloading is
   more current. Recommend: bundle the delineation file with a `census_year` version
   tag, same as we do for TIGER boundaries.

3. **Performance for bulk classification**: For millions of addresses, `sjoin` on the
   full US UA/UC layer may be slow. Consider spatial indexing (R-tree, which GeoPandas
   uses via `pygeos`/`shapely 2.0`) and state-level partitioning.

4. **Warehouse dimension table**: The locale code should become a dimension in the
   star schema (see `warehouse-star-schema.md`). A `dim_locale` table with the 12
   codes and their attributes. This is trivial but needs to be wired in.

5. **NCES-published locale assignments**: NCES publishes locale codes for every school
   and school district. Should we download and cross-reference these as a validation
   set? Yes — this is how we verify our algorithm matches theirs.

---

## 10. Related Documents

- [NCES Locale Boundaries Download](https://nces.ed.gov/programs/edge/Geographic/LocaleBoundaries) — pre-computed shapefiles
- [NCES Locale Lookup Tool](https://nces.ed.gov/programs/maped/LocaleLookup/) — interactive map
- [OMB CBSA Delineation Files](https://www.census.gov/geographies/reference-files/time-series/demo/metro-micro/delineation-files.html) — principal city lists
- [unified-geo-model-schema.md](./unified-geo-model-schema.md) — geographic model architecture
- [warehouse-star-schema.md](./warehouse-star-schema.md) — star schema for analytical warehouse

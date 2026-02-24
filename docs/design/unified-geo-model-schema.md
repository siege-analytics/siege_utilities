# Unified Geographic Model Schema

**Date**: 2026-02-24
**Status**: Draft
**Epics**: 13 (SW/DSTK Foundation), 11 (siege_utilities Integration)
**Affects**: siege_utilities.geo.django, pure-translation django_app, geodjango_simple_template, socialwarehouse

---

## 1. Overview

### The Problem

Geographic boundary models currently exist in three independent codebases with incompatible schemas:

| Codebase | What It Has | What's Missing |
|----------|-------------|----------------|
| **siege_utilities.geo.django** | Census TIGER: State, County, Tract, BlockGroup, Block, Place, ZCTA, CD. Abstract `CensusBoundary` base. `BoundaryCrosswalk` model. | No GADM. No temporal validity ranges. No state legislative districts. No VTD. No NLRB/NCES. No intersection models. |
| **pure-translation django_app** | GADM: Admin_Level_0-5. Census TIGER: State, County, Tract, BlockGroup, Block, CD, SLDU, SLDL, VTD, Place, ZCTA, TribalTract. Intersection models (County-CD, VTD-CD). | No abstract base class. Models are flat (no shared fields). No crosswalk model. No temporal validity ranges beyond `year`/`census_year`. GADM has no temporal fields at all. |
| **geodjango_simple_template** | Whatever subset pure-translation ships | Same gaps as pure-translation |

The result: every downstream consumer (GST, socialwarehouse) re-invents boundary storage, and none of them can answer temporal queries like "what Congressional district contained this address in 2014?"

### The Solution: Concentric Circles

The unified schema uses a **concentric circles** model:

```
                    +--------------------------+
                    |   TemporalBoundary       |   Abstract base: geometry +
                    |   (abstract)             |   temporal fields
                    +----------+---------------+
                               |
              +----------------+------------------+
              |                |                  |
    +---------+-------+  +----+----------+  +----+---------+
    | GADMBoundary    |  | USCensusTIGER |  | SpecialDist  |
    | (international) |  | (US Census)   |  | (NLRB, NCES) |
    +-----------------+  +---------------+  +--------------+
```

**Ring 1 (innermost)**: `TemporalBoundary` -- shared by everything.
**Ring 2**: GADM (international) and Census TIGER (US) boundary hierarchies.
**Ring 3**: Overlay/special-purpose districts (NLRB regions, NCES school districts, federal judicial districts).
**Ring 4**: Intersection models linking any two boundary types with area-weighted overlap.

### Where It Lives

- **Canonical definitions**: `siege_utilities.geo.django.models` (Django ORM) + `siege_utilities.geo.schemas` (Pydantic)
- **Consumers**: GST and socialwarehouse install siege_utilities and use these models directly
- **pure-translation**: Migrates its `locations` app to use siege_utilities.geo.django models (or thin subclasses with app-specific LayerMapping dicts)

---

## 2. Model Hierarchy

### 2.1 Abstract Base: `TemporalBoundary`

Every boundary model inherits from this. It replaces both the current `CensusBoundary` (siege_utilities) and the implicit field sets in pure-translation.

| Field | Type | Description |
|-------|------|-------------|
| `boundary_id` | `CharField(max_length=60)` | Universal identifier. GEOID for Census boundaries, gid_N for GADM. Indexed. |
| `name` | `CharField(max_length=255)` | Human-readable name |
| `geometry` | `MultiPolygonField(srid=4326)` | Boundary geometry in WGS84 |
| `vintage_year` | `PositiveSmallIntegerField` | Release year of the source data (TIGER year, GADM version year) |
| `valid_from` | `DateField(null=True)` | Date this boundary became effective (null = unknown) |
| `valid_to` | `DateField(null=True)` | Date this boundary was superseded (null = still current) |
| `area_land` | `BigIntegerField(null=True)` | Land area in square meters |
| `area_water` | `BigIntegerField(null=True)` | Water area in square meters |
| `internal_point` | `PointField(srid=4326, null=True)` | Representative interior point |
| `source` | `CharField(max_length=50)` | Data provenance: `TIGER`, `GADM`, `NCES`, `NLRB`, `CUSTOM` |
| `created_at` | `DateTimeField(auto_now_add=True)` | Row creation timestamp |
| `updated_at` | `DateTimeField(auto_now=True)` | Row update timestamp |

```python
class TemporalBoundary(models.Model):
    """Abstract base for all geographic boundaries with temporal versioning."""

    boundary_id = models.CharField(max_length=60, db_index=True)
    name = models.CharField(max_length=255)
    geometry = models.MultiPolygonField(srid=4326)
    vintage_year = models.PositiveSmallIntegerField(db_index=True)
    valid_from = models.DateField(null=True, blank=True)
    valid_to = models.DateField(null=True, blank=True)
    area_land = models.BigIntegerField(null=True, blank=True)
    area_water = models.BigIntegerField(null=True, blank=True)
    internal_point = models.PointField(srid=4326, null=True, blank=True)
    source = models.CharField(max_length=50, default="TIGER")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        ordering = ["boundary_id"]

    @property
    def is_current(self) -> bool:
        return self.valid_to is None

    @property
    def total_area(self) -> int:
        return (self.area_land or 0) + (self.area_water or 0)
```

**Key design decisions**:

1. **`boundary_id` not `geoid`**: GADM uses `gid_N` identifiers, Census uses GEOIDs, NLRB uses region numbers. A generic name avoids confusion.
2. **`srid=4326` everywhere**: The current pure-translation models use 4269 (NAD83). 4326 (WGS84) is the web standard and what siege_utilities already uses. Pure-translation's TIGER data will be reprojected on load. The difference between 4269 and 4326 is sub-meter for CONUS.
3. **`valid_from`/`valid_to` are DateField, not just year**: Redistricting can take effect mid-year. Annexations have specific effective dates.

### 2.2 GADM (International) Models

GADM provides 6 administrative levels (0-5). Each level has a foreign key to its parent.

| Model | `boundary_id` Format | Example | Parent FK |
|-------|---------------------|---------|-----------|
| `GADMCountry` (Level 0) | ISO 3-letter code | `USA` | -- |
| `GADMAdmin1` (Level 1) | `{GID_0}.{num}_1` | `USA.5_1` (California) | `GADMCountry` |
| `GADMAdmin2` (Level 2) | `{GID_0}.{num}.{num}_2` | `USA.5.18_2` (LA County) | `GADMAdmin1` |
| `GADMAdmin3` (Level 3) | pattern continues | -- | `GADMAdmin2` |
| `GADMAdmin4` (Level 4) | pattern continues | -- | `GADMAdmin3` |
| `GADMAdmin5` (Level 5) | pattern continues | -- | `GADMAdmin4` |

Additional fields per GADM model (beyond `TemporalBoundary`):

| Field | Type | Description |
|-------|------|-------------|
| `country` | `CharField(max_length=250)` | Country name |
| `gid_N` | `CharField(max_length=250)` | GADM identifier for this level |
| `name_N` | `CharField(max_length=250)` | Name at this level |
| `varname_N` | `CharField(max_length=250, blank=True)` | Variant/local name |
| `nl_name_N` | `CharField(max_length=250, blank=True)` | Native language name |
| `type_N` | `CharField(max_length=250, blank=True)` | Administrative type in local language |
| `engtype_N` | `CharField(max_length=250, blank=True)` | English administrative type |
| `cc_N` | `CharField(max_length=250, blank=True)` | Country-specific code |
| `hasc_N` | `CharField(max_length=250, blank=True)` | HASC code (levels 1-3) |
| `iso_N` | `CharField(max_length=250, blank=True)` | ISO code (level 1 only) |

**Mapping from current pure-translation GADM models**: The existing `Admin_Level_0` through `Admin_Level_5` classes map directly. The main changes are:
- Inherit from `TemporalBoundary` (gaining `vintage_year`, `valid_from`, `valid_to`)
- `boundary_id` is set to `gid_N` value
- `geometry` field (from base) replaces `geom`
- FK fields change from `gid_0 = ForeignKey(Admin_Level_0)` to `parent = ForeignKey(GADMCountry)`
- Drop the `gid_N_string` temp fields (use proper bulk loading instead)

**Unique constraint**: `(gid_N, vintage_year)` -- same GADM unit can exist across GADM releases.

### 2.3 US Census TIGER Models

All Census models share a `CensusTIGERBoundary` intermediate abstract class that adds Census-specific fields.

```python
class CensusTIGERBoundary(TemporalBoundary):
    """Intermediate abstract for Census TIGER boundaries."""

    geoid = models.CharField(max_length=20, db_index=True,
                             help_text="Census GEOID (also stored as boundary_id)")
    state_fips = models.CharField(max_length=2, db_index=True, blank=True)
    lsad = models.CharField(max_length=2, blank=True)
    mtfcc = models.CharField(max_length=5, blank=True)
    funcstat = models.CharField(max_length=1, blank=True)

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        # Keep boundary_id in sync with geoid
        if self.geoid and not self.boundary_id:
            self.boundary_id = self.geoid
        super().save(*args, **kwargs)
```

#### Statistical Hierarchy (nests cleanly)

| Model | GEOID Length | GEOID Example | Parent FK(s) | Unique Constraint |
|-------|-------------|---------------|-------------|-------------------|
| `State` | 2 | `06` | -- | `(geoid, vintage_year)` |
| `County` | 5 | `06037` | `State` | `(geoid, vintage_year)` |
| `Tract` | 11 | `06037101100` | `State`, `County` | `(geoid, vintage_year)` |
| `BlockGroup` | 12 | `060371011001` | `State`, `County`, `Tract` | `(geoid, vintage_year)` |
| `Block` | 15 | `060371011001001` | `State`, `County`, `Tract`, `BlockGroup` | `(geoid, vintage_year)` |

Additional `State` fields:

| Field | Type | Description |
|-------|------|-------------|
| `state_fips` | `CharField(max_length=2, unique per vintage)` | 2-digit FIPS |
| `abbreviation` | `CharField(max_length=2)` | e.g. `CA` |
| `region` | `CharField(max_length=2)` | Census region code |
| `division` | `CharField(max_length=2)` | Census division code |

Additional `County` fields:

| Field | Type | Description |
|-------|------|-------------|
| `county_fips` | `CharField(max_length=3)` | 3-digit county FIPS |
| `county_name` | `CharField(max_length=100)` | Name without "County" suffix |
| `legal_statistical_area` | `CharField(max_length=2, blank=True)` | LSAD code |

Additional `Tract` fields:

| Field | Type | Description |
|-------|------|-------------|
| `tract_code` | `CharField(max_length=6)` | 6-digit tract code |

Additional `BlockGroup` fields:

| Field | Type | Description |
|-------|------|-------------|
| `tract_code` | `CharField(max_length=6)` | Parent tract code |
| `block_group` | `CharField(max_length=1)` | 1-digit block group |

Additional `Block` fields:

| Field | Type | Description |
|-------|------|-------------|
| `tract_code` | `CharField(max_length=6)` | Parent tract code |
| `block_code` | `CharField(max_length=4)` | 4-digit block code |

#### Non-Nesting Census Geographies

These do not nest cleanly into the State > County > Tract hierarchy (they cross county or tract boundaries):

| Model | GEOID Length | GEOID Example | Parent FK(s) | Notes |
|-------|-------------|---------------|-------------|-------|
| `Place` | 7 | `0644000` | `State` | Cities/towns/CDPs. Can span counties. |
| `ZCTA` | 5 | `90210` | -- | No parent FK; ZCTAs cross state lines |
| `CBSA` | 5 | `31080` | -- | Metro/micro statistical areas. Cross state lines. |
| `UrbanArea` | 5 | `51445` | -- | Census Urban Areas (UAC) |

#### Political/Electoral Geographies

| Model | GEOID Length | GEOID Example | Parent FK(s) | Notes |
|-------|-------------|---------------|-------------|-------|
| `CongressionalDistrict` | 4 | `0614` | `State` | Changes with redistricting. `congress_number` field. |
| `StateLegislativeUpper` | 5 | `06028` | `State` | State senate districts |
| `StateLegislativeLower` | 5 | `06051` | `State` | State house/assembly districts |
| `VTD` | 11 (st+co+vtd) | `06037000100` | `State`, `County` | Voter Tabulation District. Enhanced fields from RDH. |
| `Precinct` | varies | varies | `State`, `County` | State-specific, may differ from VTD |

Additional `VTD` fields (preserved from current pure-translation model):

| Field | Type | Description |
|-------|------|-------------|
| `vtdst` | `CharField(max_length=6)` | VTD code |
| `vtdi` | `CharField(max_length=1, blank=True)` | VTD indicator |
| `precinct_name` | `CharField(max_length=200, blank=True)` | From RDH or state data |
| `precinct_code` | `CharField(max_length=50, blank=True)` | Local precinct ID |
| `registered_voters` | `IntegerField(null=True)` | If available |
| `data_source` | `CharField(max_length=50)` | `CENSUS_TIGER`, `RDH`, `STATE` |

Additional `CongressionalDistrict` fields:

| Field | Type | Description |
|-------|------|-------------|
| `district_number` | `CharField(max_length=2)` | `00` = at-large, `98` = non-voting |
| `congress_number` | `PositiveSmallIntegerField(null=True)` | e.g. 118 for 118th Congress |

### 2.4 Federal Administrative Boundaries

These are non-Census boundary systems that overlay the TIGER geography.

#### NLRB Regions

The National Labor Relations Board divides the US into numbered regions. These change rarely but are not static.

| Field | Type | Description |
|-------|------|-------------|
| (inherits `TemporalBoundary`) | | |
| `region_number` | `PositiveSmallIntegerField` | NLRB region number (1-31, with gaps) |
| `regional_office_city` | `CharField(max_length=100)` | City where regional office is located |
| `regional_office_state` | `CharField(max_length=2)` | State abbreviation |
| `subregion_number` | `PositiveSmallIntegerField(null=True)` | If region has subregions |

`boundary_id` format: `NLRB-{region_number}` (e.g., `NLRB-21`)
Unique constraint: `(region_number, vintage_year)`
Source: `NLRB`

#### Federal Judicial Districts

| Field | Type | Description |
|-------|------|-------------|
| (inherits `TemporalBoundary`) | | |
| `district_name` | `CharField(max_length=100)` | e.g. "Central District of California" |
| `circuit` | `CharField(max_length=10)` | Circuit number (e.g., "9th") |
| `state_fips` | `CharField(max_length=2)` | State FIPS |

`boundary_id` format: `FJD-{state_fips}-{district_code}` (e.g., `FJD-06-C`)
Unique constraint: `(district_name, vintage_year)`
Source: `CUSTOM`

### 2.5 Education and Urbanicity Boundaries (NCES)

NCES data serves two purposes in the unified schema: **school district boundaries** and **urbanicity classification**. The NCES locale codes (city/suburban/town/rural with subcategories like large/midsize/small/fringe/distant/remote) provide the standard urbanicity measure used across federal datasets — this is how Census tracts, block groups, and addresses get classified as "urban" or "rural" for demographic and econometric analysis. Three school district types share a common base.

```python
class SchoolDistrictBase(CensusTIGERBoundary):
    """Abstract base for NCES school districts (loaded from Census TIGER files)."""

    lea_id = models.CharField(max_length=7, db_index=True,
                              help_text="LEA ID (Local Education Agency)")
    district_type = models.CharField(max_length=20,
                                     choices=[("elementary", "Elementary"),
                                              ("secondary", "Secondary"),
                                              ("unified", "Unified")])
    locale_code = models.PositiveSmallIntegerField(
        null=True, blank=True,
        help_text="NCES locale code (11-43)")
    locale_category = models.CharField(
        max_length=20, blank=True,
        help_text="city/suburban/town/rural")
    locale_subcategory = models.CharField(
        max_length=30, blank=True,
        help_text="e.g. city_large, rural_remote")

    class Meta:
        abstract = True
```

| Model | TIGER Layer | Notes |
|-------|-------------|-------|
| `SchoolDistrictElementary` | `ELSD` | Elementary-only districts |
| `SchoolDistrictSecondary` | `SCSD` | Secondary-only districts |
| `SchoolDistrictUnified` | `UNSD` | Unified K-12 districts |

`boundary_id` format: GEOID from TIGER (state_fips + district_fips, 7 digits)
Unique constraint: `(geoid, vintage_year)`

NCES locale codes (from `siege_utilities.config.nces_constants`) are stored directly on the model rather than requiring a join. This denormalization is intentional: locale classification is the primary enrichment value of NCES data.

**Urbanicity beyond school districts**: The NCES locale codes apply broadly — any point or boundary in the system can be classified by spatial join against school district boundaries. This enables queries like "what share of voters in CD-34 live in rural areas?" or "how does donation volume differ between suburban and urban tracts?" The `locale_code`, `locale_category`, and `locale_subcategory` fields on `SchoolDistrictBase` are the authoritative source, but downstream analysis may propagate these classifications to tracts and block groups via spatial overlay.

### 2.6 Intersection Models

Intersection models store pre-computed spatial relationships between any two boundary types, with area overlap percentages. This replaces pure-translation's current `CountyCongressionalDistrictIntersection` and `VTDCongressionalDistrictIntersection` with a generalized pattern.

#### Generic Intersection Model

```python
class BoundaryIntersection(models.Model):
    """Pre-computed spatial intersection between two boundary types."""

    # Source boundary (identified by type + boundary_id + vintage_year)
    source_type = models.CharField(max_length=50, db_index=True,
                                   help_text="Model name: 'State', 'County', 'CD', etc.")
    source_boundary_id = models.CharField(max_length=60, db_index=True)
    source_vintage_year = models.PositiveSmallIntegerField()

    # Target boundary
    target_type = models.CharField(max_length=50, db_index=True)
    target_boundary_id = models.CharField(max_length=60, db_index=True)
    target_vintage_year = models.PositiveSmallIntegerField()

    # Intersection result
    intersection_geometry = models.MultiPolygonField(srid=4326)
    intersection_area_sqm = models.BigIntegerField()
    pct_of_source = models.DecimalField(max_digits=7, decimal_places=4,
                                        help_text="Fraction of source area in this intersection")
    pct_of_target = models.DecimalField(max_digits=7, decimal_places=4,
                                        help_text="Fraction of target area in this intersection")

    # Classification
    is_dominant = models.BooleanField(default=False, db_index=True,
                                     help_text="True if >50% of source is in this target")

    computed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("source_type", "source_boundary_id", "source_vintage_year",
                           "target_type", "target_boundary_id", "target_vintage_year")]
        indexes = [
            models.Index(fields=["source_type", "source_boundary_id", "source_vintage_year"]),
            models.Index(fields=["target_type", "target_boundary_id", "target_vintage_year"]),
            models.Index(fields=["source_type", "target_type", "source_vintage_year"]),
        ]
```

#### Typed Convenience Intersection Models

For high-frequency intersection queries, typed models with proper ForeignKeys remain useful. These are thin wrappers:

| Model | Source FK | Target FK | Key Use Case |
|-------|----------|-----------|--------------|
| `CountyCDIntersection` | `County` | `CongressionalDistrict` | Donor attribution by CD for county-level data |
| `VTDCDIntersection` | `VTD` | `CongressionalDistrict` | Split-precinct donor attribution |
| `TractCDIntersection` | `Tract` | `CongressionalDistrict` | Census-to-political crosswalk |
| `CountySchoolDistrictIntersection` | `County` | `SchoolDistrictUnified` | Education analysis |

These typed models inherit the same fields (intersection geometry, area, percentages) but add typed ForeignKeys for ORM convenience. They are generated by a compute job, not maintained manually.

---

## 3. Temporal Model

### 3.1 How Temporal Versioning Works

Every boundary row has three temporal fields:

| Field | Meaning | Example |
|-------|---------|---------|
| `vintage_year` | The release year of the shapefile/dataset | `2020` for TIGER2020 files |
| `valid_from` | When this boundary became legally effective | `2023-01-03` (start of 118th Congress) |
| `valid_to` | When this boundary was superseded | `2025-01-03` (end of 118th Congress), or `NULL` if still active |

**Rules**:
- `vintage_year` is required on every row. It identifies which dataset release the geometry came from.
- `valid_from` / `valid_to` are optional. If null, the boundary is assumed valid for the full range of its vintage year dataset.
- The unique constraint is `(boundary_id, vintage_year)`, not `(boundary_id, valid_from)`. This means the same GEOID can appear multiple times if loaded from different TIGER vintages (e.g., tract 06037101100 from TIGER2010 and TIGER2020).

### 3.2 Temporal Query Patterns

**Pattern 1: "What boundaries were active on date X?"**

```python
from datetime import date

def boundaries_as_of(model_class, as_of_date):
    """Return boundaries valid on the given date."""
    return model_class.objects.filter(
        models.Q(valid_from__lte=as_of_date) | models.Q(valid_from__isnull=True),
        models.Q(valid_to__gte=as_of_date) | models.Q(valid_to__isnull=True),
    )

# Example: Congressional districts active on 2018-06-15
active_cds = boundaries_as_of(CongressionalDistrict, date(2018, 6, 15))
```

**Pattern 2: "Resolve this GEOID as of vintage year Y"**

```python
def resolve_boundary(model_class, geoid, vintage_year):
    """Get the boundary for a GEOID in a specific vintage."""
    return model_class.objects.get(geoid=geoid, vintage_year=vintage_year)

# Example: Get tract geometry from 2010 boundaries
tract_2010 = resolve_boundary(Tract, "06037101100", 2010)
```

**Pattern 3: "Show all versions of this boundary"**

```python
def boundary_history(model_class, geoid):
    """Get all vintage versions of a boundary."""
    return model_class.objects.filter(
        geoid=geoid
    ).order_by("vintage_year")

# Shows tract 06037101100 in 2010 and 2020 (geometry may differ)
versions = boundary_history(Tract, "06037101100")
```

### 3.3 Temporal Crosswalk Model

The existing `BoundaryCrosswalk` in siege_utilities.geo.django.models.crosswalks is already well-designed for this purpose. The unified schema retains it with one addition: it gains `valid_from`/`valid_to` awareness.

```python
class TemporalCrosswalk(models.Model):
    """Links boundary versions across time with allocation weights."""

    RELATIONSHIP_CHOICES = [
        ("IDENTICAL", "Unchanged"),
        ("SPLIT", "One-to-many split"),
        ("MERGED", "Many-to-one merge"),
        ("PARTIAL", "Partial overlap"),
        ("RENAMED", "GEOID changed, boundary same"),
    ]

    WEIGHT_TYPE_CHOICES = [
        ("population", "Population-weighted"),
        ("housing", "Housing unit-weighted"),
        ("area", "Area-weighted"),
        ("land_area", "Land area-weighted"),
    ]

    # Source
    source_type = models.CharField(max_length=50, db_index=True)
    source_boundary_id = models.CharField(max_length=60, db_index=True)
    source_vintage_year = models.PositiveSmallIntegerField(db_index=True)

    # Target
    target_type = models.CharField(max_length=50, db_index=True)
    target_boundary_id = models.CharField(max_length=60, db_index=True)
    target_vintage_year = models.PositiveSmallIntegerField(db_index=True)

    # Relationship
    relationship = models.CharField(max_length=20, choices=RELATIONSHIP_CHOICES, db_index=True)
    weight = models.DecimalField(max_digits=10, decimal_places=8)
    weight_type = models.CharField(max_length=20, choices=WEIGHT_TYPE_CHOICES, default="population")

    # Context
    state_fips = models.CharField(max_length=2, blank=True, db_index=True)
    source_population = models.PositiveIntegerField(null=True, blank=True)
    target_population = models.PositiveIntegerField(null=True, blank=True)
    allocated_population = models.PositiveIntegerField(null=True, blank=True)
    intersection_area_sqm = models.BigIntegerField(null=True, blank=True)
    data_source = models.CharField(max_length=100, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("source_boundary_id", "target_boundary_id",
                           "source_vintage_year", "target_vintage_year", "weight_type")]
        indexes = [
            models.Index(fields=["source_boundary_id", "source_vintage_year"]),
            models.Index(fields=["target_boundary_id", "target_vintage_year"]),
            models.Index(fields=["source_type", "target_type",
                                "source_vintage_year", "target_vintage_year"]),
        ]
```

**Crosswalk query: "What 2020 tracts correspond to 2010 tract 06037101100?"**

```python
mappings = TemporalCrosswalk.objects.filter(
    source_type="Tract",
    source_boundary_id="06037101100",
    source_vintage_year=2010,
    target_vintage_year=2020,
).order_by("-weight")

# Returns: [
#   {target_boundary_id: "06037101101", weight: 0.62, relationship: "SPLIT"},
#   {target_boundary_id: "06037101102", weight: 0.38, relationship: "SPLIT"},
# ]
```

### 3.4 Relationship to Existing Crosswalk Code

The Pydantic dataclasses in `siege_utilities.geo.crosswalk.relationship_types` (`CrosswalkRelationship`, `CrosswalkMetadata`, `GeographyChange`) remain as the in-memory processing layer. The `TemporalCrosswalk` Django model is the persistence layer. Data flows:

```
Census crosswalk CSV
    --> crosswalk_processor.py (Pydantic dataclasses)
    --> TemporalCrosswalk.objects.bulk_create()
```

The existing `SUPPORTED_CROSSWALK_YEARS` dict in `relationship_types.py` (currently `{(2010, 2020), (2000, 2010)}`) continues to define which crosswalks are available.

---

## 4. Pydantic / Django ORM Mapping Pattern

### The Dual-Schema Pattern

siege_utilities serves two audiences:
1. **Notebook users** (Pydantic): work with pandas/geopandas, no database needed.
2. **Web/database users** (Django ORM): need PostGIS-backed models for spatial queries.

The pattern: define the **schema** in Pydantic first (in `siege_utilities.geo.schemas`), then mirror it in Django ORM (in `siege_utilities.geo.django.models`). The Pydantic model is the source of truth for field names and validation rules. The Django model adds database concerns (indexes, ForeignKeys, migrations).

### Concrete Example: State

**Pydantic schema** (`siege_utilities/geo/schemas/boundaries.py`):

```python
from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, Field, field_validator

class TemporalBoundarySchema(BaseModel):
    """Base schema for all geographic boundaries."""
    boundary_id: str = Field(..., max_length=60)
    name: str = Field(..., max_length=255)
    vintage_year: int = Field(..., ge=1990, le=2050)
    valid_from: Optional[date] = None
    valid_to: Optional[date] = None
    area_land: Optional[int] = None
    area_water: Optional[int] = None
    source: str = Field(default="TIGER", max_length=50)
    # geometry is NOT in the Pydantic model -- it's a shapely/WKT concern,
    # handled separately via GeoDataFrame or WKT string field

    @property
    def is_current(self) -> bool:
        return self.valid_to is None

    @property
    def total_area(self) -> int:
        return (self.area_land or 0) + (self.area_water or 0)

class CensusTIGERSchema(TemporalBoundarySchema):
    """Base for Census TIGER boundaries."""
    geoid: str = Field(..., max_length=20)
    state_fips: str = Field(default="", max_length=2)
    lsad: str = Field(default="", max_length=2)
    funcstat: str = Field(default="", max_length=1)

    @field_validator("boundary_id", mode="before")
    @classmethod
    def set_boundary_id_from_geoid(cls, v, info):
        if not v and "geoid" in info.data:
            return info.data["geoid"]
        return v

class StateSchema(CensusTIGERSchema):
    """US State boundary."""
    state_fips: str = Field(..., min_length=2, max_length=2)
    abbreviation: str = Field(..., min_length=2, max_length=2)
    region: str = Field(default="", max_length=2)
    division: str = Field(default="", max_length=2)

    @classmethod
    def geoid_length(cls) -> int:
        return 2
```

**Django ORM model** (`siege_utilities/geo/django/models/boundaries.py`):

```python
class State(CensusTIGERBoundary):
    """US State or Territory. Mirrors StateSchema."""

    abbreviation = models.CharField(max_length=2, db_index=True)
    region = models.CharField(max_length=2, blank=True)
    division = models.CharField(max_length=2, blank=True)

    class Meta:
        verbose_name = "State"
        verbose_name_plural = "States"
        unique_together = [("geoid", "vintage_year")]
        indexes = [
            models.Index(fields=["state_fips", "vintage_year"]),
            models.Index(fields=["abbreviation"]),
        ]

    @classmethod
    def from_schema(cls, schema: "StateSchema", geometry_wkt: str = None) -> "State":
        """Create a State instance from a Pydantic schema."""
        instance = cls(
            boundary_id=schema.boundary_id,
            geoid=schema.geoid,
            name=schema.name,
            vintage_year=schema.vintage_year,
            valid_from=schema.valid_from,
            valid_to=schema.valid_to,
            area_land=schema.area_land,
            area_water=schema.area_water,
            source=schema.source,
            state_fips=schema.state_fips,
            abbreviation=schema.abbreviation,
            region=schema.region,
            division=schema.division,
            lsad=schema.lsad,
            funcstat=schema.funcstat,
        )
        if geometry_wkt:
            from django.contrib.gis.geos import GEOSGeometry
            instance.geometry = GEOSGeometry(geometry_wkt, srid=4326)
        return instance

    def to_schema(self) -> "StateSchema":
        """Convert to Pydantic schema (for serialization, notebook use)."""
        from ..schemas.boundaries import StateSchema
        return StateSchema(
            boundary_id=self.boundary_id,
            geoid=self.geoid,
            name=self.name,
            vintage_year=self.vintage_year,
            valid_from=self.valid_from,
            valid_to=self.valid_to,
            area_land=self.area_land,
            area_water=self.area_water,
            source=self.source,
            state_fips=self.state_fips,
            abbreviation=self.abbreviation,
            region=self.region,
            division=self.division,
            lsad=self.lsad,
            funcstat=self.funcstat,
        )
```

### Conversion Utilities

A shared utility module provides bulk conversions:

```python
# siege_utilities/geo/conversion.py

def gdf_to_schemas(gdf: "GeoDataFrame", schema_class) -> list:
    """Convert GeoDataFrame rows to Pydantic schemas."""
    ...

def schemas_to_orm(schemas: list, model_class, geometry_column="geometry") -> list:
    """Convert Pydantic schemas to Django ORM instances (for bulk_create)."""
    ...

def orm_to_gdf(queryset, schema_class) -> "GeoDataFrame":
    """Convert Django queryset to GeoDataFrame via Pydantic schemas."""
    ...
```

---

## 5. Data Sources

| Model | Source | URL Pattern | Frequency |
|-------|--------|-------------|-----------|
| **State** | Census TIGER | `census.gov/geo/tiger/TIGER{YYYY}/STATE/tl_{yyyy}_us_state.zip` | Annual |
| **County** | Census TIGER | `census.gov/geo/tiger/TIGER{YYYY}/COUNTY/tl_{yyyy}_us_county.zip` | Annual |
| **Tract** | Census TIGER | `census.gov/geo/tiger/TIGER{YYYY}/TRACT/tl_{yyyy}_{ss}_tract.zip` | Annual (per state) |
| **BlockGroup** | Census TIGER | `census.gov/geo/tiger/TIGER{YYYY}/BG/tl_{yyyy}_{ss}_bg.zip` | Annual (per state) |
| **Block** | Census TIGER | `census.gov/geo/tiger/TIGER{YYYY}/TABBLOCK20/tl_{yyyy}_{ss}_tabblock20.zip` | Decennial (per state) |
| **Place** | Census TIGER | `census.gov/geo/tiger/TIGER{YYYY}/PLACE/tl_{yyyy}_{ss}_place.zip` | Annual (per state) |
| **ZCTA** | Census TIGER | `census.gov/geo/tiger/TIGER{YYYY}/ZCTA520/tl_{yyyy}_us_zcta520.zip` | Annual |
| **CD** | Census TIGER | `census.gov/geo/tiger/TIGER{YYYY}/CD/tl_{yyyy}_us_cd{NNN}.zip` | Per Congress |
| **SLDU/SLDL** | Census TIGER | `census.gov/geo/tiger/TIGER{YYYY}/SLD[UL]/tl_{yyyy}_{ss}_sld[ul].zip` | Per redistricting |
| **VTD** | Census TIGER | `census.gov/geo/tiger/TIGER{YYYY}/VTD/tl_{yyyy}_{ss}_vtd20.zip` | Decennial |
| **VTD (enhanced)** | Redistricting Data Hub | `redistrictingdatahub.org/` (state-specific downloads) | Per redistricting |
| **GADM Levels 0-5** | GADM | `gadm.org/download_country.html` | Irregular (~every 2-3 years) |
| **SchoolDistrict** | Census TIGER (NCES) | `census.gov/geo/tiger/TIGER{YYYY}/{ELSD,SCSD,UNSD}/tl_{yyyy}_{ss}_{type}.zip` | Annual |
| **NLRB Regions** | NLRB | Manual digitization or NLRB website boundary descriptions | Rarely changes |
| **Federal Judicial Districts** | USGS / DOJ | `hifld-geoplatform.opendata.arcgis.com` | Rarely changes |
| **Temporal Crosswalks** | Census Bureau | `census.gov/geo/docs/maps-data/data/rel2020/` | Per decennial |

### Data Loading Strategy

Each model type gets a management command following the existing pure-translation pattern:

```bash
# Census TIGER boundaries
python manage.py load_boundaries --type state --year 2020
python manage.py load_boundaries --type tract --year 2020 --state 06

# GADM international
python manage.py load_gadm --country USA --level 2 --version 4.1

# NCES school districts
python manage.py load_school_districts --type unified --year 2023 --state 06

# Temporal crosswalks
python manage.py load_crosswalk --source-year 2010 --target-year 2020 --type tract

# Intersection computation (not a file load -- computed from existing geometries)
python manage.py compute_intersections --source County --target CD --year 2020
```

---

## 6. Migration Path

### Phase 1: Build the Base in siege_utilities (Epics 11, 13 -- Phase 2-3)

1. **Create `siege_utilities/geo/schemas/` package** with Pydantic boundary schemas.
2. **Refactor `siege_utilities/geo/django/models/base.py`**: Rename `CensusBoundary` to `TemporalBoundary`. Add `valid_from`, `valid_to`, `internal_point`, `source`. Rename `census_year` to `vintage_year`. Rename `aland`/`awater` to `area_land`/`area_water`.
3. **Add `CensusTIGERBoundary`** intermediate abstract with `geoid`, `state_fips`, `lsad`, `mtfcc`, `funcstat`.
4. **Update concrete models** in `boundaries.py`: State, County, Tract, BlockGroup, Block, Place, ZCTA, CongressionalDistrict. Add `vintage_year`-based unique constraints. Add missing models: StateLegislativeUpper, StateLegislativeLower, VTD.
5. **Add GADM models**: `GADMCountry` through `GADMAdmin5` inheriting from `TemporalBoundary`.
6. **Add NCES models**: `SchoolDistrictBase`, `SchoolDistrictElementary`, `SchoolDistrictSecondary`, `SchoolDistrictUnified`.
7. **Add NLRB model**: `NLRBRegion`.
8. **Add intersection models**: `BoundaryIntersection` (generic) + typed convenience models.
9. **Refactor `BoundaryCrosswalk`** into `TemporalCrosswalk` with `source_type`/`target_type` fields.

### Phase 2: GST Adoption (Epic 13 -- Phase 4)

geodjango_simple_template currently has its own copies of location models. Migration:

1. Add `siege_utilities` as a dependency.
2. Replace bespoke location models with `from siege_utilities.geo.django.models import *`.
3. Keep GST-specific LayerMapping dicts as thin wrappers if needed.
4. Run `makemigrations` to generate the transition migration.
5. Update GST management commands to use the unified load commands.

### Phase 3: pure-translation / enterprise Adoption (Epic 12 -- Phase 3)

pure-translation's `locations` app has the most models to migrate. Strategy:

1. **Add siege_utilities dependency** to pure-translation's requirements.
2. **Create migration**: For each existing model (`United_States_Census_State`, `Admin_Level_0`, etc.), create a Django migration that:
   - Renames existing tables to `legacy_*`
   - Creates new tables from siege_utilities models
   - Copies data from legacy tables with field mapping
   - Drops legacy tables
3. **Field mapping** (example for State):

   | pure-translation field | unified schema field | Notes |
   |----------------------|---------------------|-------|
   | `statefp` | `state_fips` | Direct copy |
   | `geoid` | `geoid` + `boundary_id` | Copy to both |
   | `name` | `name` | Direct copy |
   | `stusps` | `abbreviation` | Rename |
   | `year` | `vintage_year` | Rename |
   | `geom (srid=4269)` | `geometry (srid=4326)` | Reproject NAD83 to WGS84 |
   | `aland` | `area_land` | Rename |
   | `awater` | `area_water` | Rename |
   | `intptlat`/`intptlon` | `internal_point` | Combine into PointField |
   | `region`, `division` | `region`, `division` | Direct copy |
   | -- | `valid_from` | Set NULL initially |
   | -- | `valid_to` | Set NULL initially |
   | -- | `source` | Set `"TIGER"` |

4. **Update all imports** across pure-translation to use siege_utilities models.
5. **Update serializers** (`locations/serializers/`) to match new field names.
6. **Update views** (`locations/views/`) to use new querysets.
7. **Update LayerMapping dicts** -- these stay in pure-translation since they're TIGER-shapefile-specific.

### Phase 4: Socialwarehouse Layer (Epic 13 -- Phase 5)

Socialwarehouse adds warehouse-service endpoints on top of the unified models:

1. Import siege_utilities.geo.django models.
2. Add warehouse-specific views (temporal queries, intersection lookups, crosswalk resolution).
3. No new boundary models needed -- just service logic on top of the unified ones.

---

## 7. What This Enables (DSTK Replacement)

The unified schema with temporal versioning replaces the need for a separate Data Science Toolkit (DSTK) instance. DSTK was more than a geocoder — it provided **statistics in time and space**: the ability to ask "what were the demographics of this place at that time?" The replacement covers three capabilities:

1. **Temporal geocoding**: Resolve an address or coordinate to its containing boundaries as of any date (not just the current vintage).
2. **Temporal statistics**: Join demographic/economic data to boundaries that were valid when the data was collected, and compare across vintages using crosswalks.
3. **Spatial interpolation**: Estimate values for target geographies using areal weighting from source geographies (e.g., estimate 2020-vintage tract demographics from 2010-vintage tract data when boundaries changed). PySAL's `tobler` package provides the interpolation engine; the unified schema provides the boundary geometries and crosswalk weights it operates on.

### Query: "Geocode this address as of 2018"

```python
from datetime import date
from django.contrib.gis.geos import Point

point = Point(-118.2437, 34.0522, srid=4326)  # Downtown LA
query_date = date(2018, 6, 15)

# Find tract containing this point, valid in 2018
# 2018 data uses 2010 TIGER boundaries
tract = Tract.objects.filter(
    geometry__contains=point,
    vintage_year=2010,  # 2018 falls in 2010 boundary era
).first()

# Find Congressional District active on that date
cd = CongressionalDistrict.objects.filter(
    geometry__contains=point,
    models.Q(valid_from__lte=query_date) | models.Q(valid_from__isnull=True),
    models.Q(valid_to__gte=query_date) | models.Q(valid_to__isnull=True),
).first()
```

### Query: "What CD was this tract in before redistricting?"

```python
tract_geoid = "06037101100"

# Pre-redistricting (2010 boundaries, 115th-116th Congress maps)
cd_pre = TractCDIntersection.objects.filter(
    source_boundary_id=tract_geoid,
    source_vintage_year=2010,
    target_vintage_year=2010,
    is_dominant=True,
).first()

# Post-redistricting (2020 boundaries, 118th Congress maps)
cd_post = TractCDIntersection.objects.filter(
    source_boundary_id=tract_geoid,
    source_vintage_year=2020,
    target_vintage_year=2020,
    is_dominant=True,
).first()

print(f"Before: {cd_pre.target_boundary_id}")  # e.g., 0634
print(f"After: {cd_post.target_boundary_id}")   # e.g., 0630
```

### Query: "Show me all boundary changes in this county between 2010 and 2020"

```python
county_fips = "06037"  # LA County

# Find all tract changes
changes = TemporalCrosswalk.objects.filter(
    source_type="Tract",
    source_vintage_year=2010,
    target_vintage_year=2020,
    state_fips="06",
    source_boundary_id__startswith=county_fips,
).exclude(
    relationship="IDENTICAL"
).order_by("source_boundary_id")

# Summary
splits = changes.filter(relationship="SPLIT").count()
merges = changes.filter(relationship="MERGED").count()
renamed = changes.filter(relationship="RENAMED").count()
print(f"LA County tract changes 2010->2020: {splits} splits, {merges} merges, {renamed} renames")
```

### Query: "What NLRB region covers this address?"

```python
point = Point(-87.6298, 41.8781, srid=4326)  # Chicago

nlrb_region = NLRBRegion.objects.filter(
    geometry__contains=point,
    valid_to__isnull=True,  # Current region boundaries
).first()

print(f"NLRB Region: {nlrb_region.region_number}")  # Region 13
```

### Query: "What school district is this tract in?"

```python
tract = Tract.objects.get(geoid="06037101100", vintage_year=2020)

district = SchoolDistrictUnified.objects.filter(
    geometry__intersects=tract.geometry,
    vintage_year=2023,
).first()

print(f"District: {district.name}")
print(f"Locale: {district.locale_category} ({district.locale_subcategory})")
```

### Integration with Existing siege_utilities Timeseries

The `siege_utilities.geo.timeseries` module already handles longitudinal data fetching with boundary normalization. The unified schema improves this by:

1. `_get_boundary_year()` can now query `TemporalCrosswalk` instead of hardcoding year ranges.
2. `apply_crosswalk()` can read weights from the database instead of CSV files.
3. Longitudinal data results can be persisted via `DemographicSnapshot` and `DemographicTimeSeries` (already defined in `siege_utilities.geo.django.models.demographics`).

### Spatial Interpolation via PySAL

When boundaries change between vintages (e.g., 2010 → 2020 tracts), raw crosswalk weights alone aren't sufficient for accurate statistical comparison — you need areal interpolation that accounts for how population and other variables are distributed within the source geometries. PySAL's `tobler` package provides this.

The unified schema supports PySAL integration at two levels:

1. **Boundary geometries as input**: `tobler.area_weighted.area_interpolate()` takes source and target GeoDataFrames. The unified models provide both via `orm_to_gdf()` for any pair of vintage years.

2. **Pre-computed crosswalk weights as validation**: The `TemporalCrosswalk` area overlap percentages serve as a baseline; PySAL's dasymetric methods (using ancillary data like land use or population density) can refine these weights for more accurate interpolation.

```python
import tobler
from siege_utilities.geo.conversion import orm_to_gdf

# Get 2010 and 2020 tract geometries for a county
tracts_2010 = orm_to_gdf(
    Tract.objects.filter(state_fips="06", vintage_year=2010,
                         geoid__startswith="06037"),
    TractSchema
)
tracts_2020 = orm_to_gdf(
    Tract.objects.filter(state_fips="06", vintage_year=2020,
                         geoid__startswith="06037"),
    TractSchema
)

# Attach 2010 ACS data to 2010 tracts (e.g., population, median income)
tracts_2010["population"] = ...  # from Census API or DemographicSnapshot
tracts_2010["median_income"] = ...

# Interpolate 2010 data onto 2020 boundaries
interpolated = tobler.area_weighted.area_interpolate(
    source_df=tracts_2010,
    target_df=tracts_2020,
    extensive_variables=["population"],      # Sums (split proportionally)
    intensive_variables=["median_income"],    # Averages (area-weighted)
)
# Result: 2020-vintage tracts with estimated 2010-era demographics
```

This enables longitudinal analysis even when the underlying geography has changed — the core capability that made DSTK valuable for researchers.

---

## Appendix A: Field Name Reconciliation

Current field names vary across codebases. The unified schema standardizes them.

| Concept | siege_utilities (current) | pure-translation (current) | Unified Name |
|---------|--------------------------|---------------------------|--------------|
| Geographic ID | `geoid` | `geoid` | `geoid` + `boundary_id` |
| Geometry | `geometry` (srid=4326) | `geom` (srid=4269) | `geometry` (srid=4326) |
| Release year | `census_year` | `year` | `vintage_year` |
| Land area | `aland` | `aland` | `area_land` |
| Water area | `awater` | `awater` | `area_water` |
| State FIPS | `state_fips` | `statefp` | `state_fips` |
| County FIPS | `county_fips` | `countyfp` | `county_fips` |
| Name | `name` | `name` / `namelsad` | `name` (use `namelsad` as alias) |
| Interior point | -- | `intptlat` / `intptlon` | `internal_point` (PointField) |
| GADM ID | -- | `gid_N` | `gid_N` (level-specific) + `boundary_id` |

## Appendix B: Volume Estimates

Storage per vintage year:

| Model | Record Count | Estimated Size |
|-------|-------------|----------------|
| GADM Level 0 | ~250 | <10 MB |
| GADM Level 1 | ~3,600 | ~100 MB |
| GADM Level 2 | ~40,000 | ~500 MB |
| State | 56 | <10 MB |
| County | 3,200 | ~50 MB |
| Tract | 85,000 | ~500 MB |
| BlockGroup | 240,000 | ~800 MB |
| Block | 11,000,000 | ~5 GB |
| Place | 30,000 | ~200 MB |
| ZCTA | 33,000 | ~350 MB |
| CD | 435 | ~30 MB |
| SLDU | 2,000 | ~100 MB |
| SLDL | 5,000 | ~150 MB |
| VTD | 180,000 | ~600 MB |
| SchoolDistrict (all types) | ~18,000 | ~300 MB |
| NLRB Region | 31 | <5 MB |

**Total for one vintage year** (excluding Blocks): ~3.2 GB
**Total for two vintage years (2010 + 2020)**: ~6.4 GB
**Blocks add ~5 GB per vintage year** -- consider partitioning by state.

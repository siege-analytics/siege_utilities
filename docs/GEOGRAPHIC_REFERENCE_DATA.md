# Geographic Reference Data Structures

This document explains the canonical geographic level system, GEOID utilities, boundary type catalog, and how they interrelate. These structures are the foundation of all Census-related operations in `siege_utilities`.

---

## Table of Contents

1. [Design Principle](#design-principle)
2. [CANONICAL_GEOGRAPHIC_LEVELS](#canonical_geographic_levels)
3. [resolve_geographic_level()](#resolve_geographic_level)
4. [GEOID_LENGTHS](#geoid_lengths)
5. [GeographyLevel Enum](#geographylevel-enum)
6. [BOUNDARY_TYPE_CATALOG](#boundary_type_catalog)
7. [TIGER_FILE_PATTERNS](#tiger_file_patterns)
8. [GEOGRAPHIC_HIERARCHY](#geographic_hierarchy)
9. [Backward-Compatible GEOGRAPHIC_LEVELS](#backward-compatible-geographic_levels)
10. [How They Relate](#how-they-relate)
11. [Common Usage Patterns](#common-usage-patterns)

---

## Design Principle

**One canonical name per geographic level. Accept any variant. Resolve early, use canonical everywhere.**

The Census Bureau uses many names for the same geographic levels. Congressional districts might be called `cd`, `congressional_district`, `CD`, `CD118`, or `CONGRESSIONAL_DISTRICT` depending on context. This system normalizes all variants to a single canonical form at the earliest possible point, so downstream code never needs to worry about naming variants.

---

## CANONICAL_GEOGRAPHIC_LEVELS

**Location:** `siege_utilities/config/census_constants.py`

The single source of truth for all geographic level metadata. Every other structure derives from this dict.

```python
from siege_utilities.config.census_constants import CANONICAL_GEOGRAPHIC_LEVELS
```

### Structure

Each entry maps a **canonical name** (the authoritative short form) to its metadata:

```python
CANONICAL_GEOGRAPHIC_LEVELS = {
    'nation':       {'aliases': ['us', 'national'],                    'geoid_length': 1},
    'state':        {'aliases': [],                                    'geoid_length': 2},
    'county':       {'aliases': [],                                    'geoid_length': 5},
    'cousub':       {'aliases': ['county_subdivision'],                'geoid_length': 10},
    'cd':           {'aliases': ['congressional_district'],            'geoid_length': 4},
    'sldu':         {'aliases': ['state_legislative_upper', ...],      'geoid_length': 5},
    'sldl':         {'aliases': ['state_legislative_lower', ...],      'geoid_length': 5},
    'tract':        {'aliases': [],                                    'geoid_length': 11},
    'block_group':  {'aliases': ['bg', 'blockgroup'],                  'geoid_length': 12},
    'block':        {'aliases': ['tabblock'],                          'geoid_length': 15},
    'zcta':         {'aliases': ['zip_code', 'zcta5', 'zipcode'],      'geoid_length': 5},
    # ... plus region, division, place, cbsa, puma, vtd, tabblock10, tabblock20
}
```

### Key Properties

- **Keys are canonical names** — short, lowercase, matching Census conventions
- **`aliases`** — list of alternative names that resolve to this canonical name
- **`geoid_length`** — number of digits in a properly formatted GEOID for this level
- **No alias collisions** — each alias maps to exactly one canonical name
- **Canonical names are not aliases of other levels** — no ambiguity

### Why These Canonical Names?

| Canonical | Why Not the Long Form? |
|-----------|----------------------|
| `cd` | Matches TIGER/Line filenames, BOUNDARY_TYPE_CATALOG keys, Census API |
| `cousub` | Census abbreviation used in all file formats |
| `sldu` / `sldl` | Distinguishes upper/lower (long form `state_legislative_district` was ambiguous) |
| `zcta` | Census standard name for ZIP Code Tabulation Areas |
| `block_group` | Exception — kept long form because it's used everywhere including GEOID_LENGTHS, Census API, DataFrames |

---

## resolve_geographic_level()

**Location:** `siege_utilities/config/census_constants.py`

The workhorse function. Accepts any geographic level name variant and returns the canonical form.

```python
from siege_utilities.config.census_constants import resolve_geographic_level

resolve_geographic_level('congressional_district')  # → 'cd'
resolve_geographic_level('bg')                       # → 'block_group'
resolve_geographic_level('zip_code')                 # → 'zcta'
resolve_geographic_level('CD')                       # → 'cd' (case-insensitive)
resolve_geographic_level('  tract  ')                # → 'tract' (strips whitespace)
resolve_geographic_level('nonsense')                 # → ValueError
```

### Behavior

1. Strips whitespace and lowercases the input
2. Looks up in `_ALIAS_TO_CANONICAL` (precomputed reverse lookup)
3. Returns canonical name if found
4. Raises `ValueError` with a helpful message if not found

### When to Use

Call this function **at the boundary** — wherever user input or external data enters the system:
- Function parameters that accept a geography level string
- Config file parsing
- CLI argument handling
- DataFrame column values that represent geography types

### Companion: validate_geographic_level()

Returns `True`/`False` instead of raising an exception:

```python
from siege_utilities.config.census_constants import validate_geographic_level

validate_geographic_level('cd')                       # → True
validate_geographic_level('congressional_district')    # → True
validate_geographic_level('nonsense')                  # → False
```

---

## GEOID_LENGTHS

**Location:** `siege_utilities/geo/geoid_utils.py`

Derived from `CANONICAL_GEOGRAPHIC_LEVELS` — maps canonical names to their GEOID digit count.

```python
from siege_utilities.geo.geoid_utils import GEOID_LENGTHS

GEOID_LENGTHS['state']       # → 2
GEOID_LENGTHS['county']      # → 5
GEOID_LENGTHS['tract']       # → 11
GEOID_LENGTHS['block_group'] # → 12
GEOID_LENGTHS['cd']          # → 4
```

### How It's Built

```python
GEOID_LENGTHS = {
    name: info['geoid_length']
    for name, info in CANONICAL_GEOGRAPHIC_LEVELS.items()
    if info.get('geoid_length') is not None
}
```

### GEOID Format Examples

| Level | Length | Example | Components |
|-------|--------|---------|------------|
| state | 2 | `06` | state(2) |
| county | 5 | `06037` | state(2) + county(3) |
| tract | 11 | `06037101100` | state(2) + county(3) + tract(6) |
| block_group | 12 | `060371011001` | state(2) + county(3) + tract(6) + bg(1) |
| block | 15 | `060371011001001` | state(2) + county(3) + tract(6) + block(4) |
| cd | 4 | `0604` | state(2) + cd(2) |
| place | 7 | `0644000` | state(2) + place(5) |
| zcta | 5 | `90210` | zcta(5) |

### GEOID Functions

All GEOID functions accept **any geographic level variant** (they call `resolve_geographic_level()` internally):

```python
from siege_utilities.geo.geoid_utils import (
    normalize_geoid,       # Zero-pad to correct length
    construct_geoid,       # Build from components
    parse_geoid,           # Split into components
    validate_geoid,        # Check format
    extract_parent_geoid,  # Get parent geography
)

# These all work — aliases resolved automatically
normalize_geoid('6037', 'county')                    # → '06037'
normalize_geoid('604', 'congressional_district')      # → '0604'
construct_geoid('bg', state='06', county='037',
                tract='101100', block_group='1')       # → '060371011001'
validate_geoid('90210', 'zip_code')                    # → True
```

---

## GeographyLevel Enum

**Location:** `siege_utilities/geo/census_dataset_mapper.py`

Python enum with canonical values and backward-compatible aliases.

```python
from siege_utilities.geo.census_dataset_mapper import GeographyLevel

# Canonical members
GeographyLevel.CD.value        # → 'cd'
GeographyLevel.COUSUB.value    # → 'cousub'
GeographyLevel.SLDU.value      # → 'sldu'
GeographyLevel.BLOCK_GROUP.value  # → 'block_group'

# Backward-compatible aliases (Python enum aliases — same object)
GeographyLevel.CONGRESSIONAL_DISTRICT is GeographyLevel.CD        # → True
GeographyLevel.COUNTY_SUBDIVISION is GeographyLevel.COUSUB        # → True
GeographyLevel.ZIP_CODE is GeographyLevel.ZCTA                    # → True

# _missing_ resolves string variants
GeographyLevel('congressional_district')  # → GeographyLevel.CD
GeographyLevel('bg')                       # → GeographyLevel.BLOCK_GROUP
GeographyLevel('zip_code')                 # → GeographyLevel.ZCTA
```

### How _missing_ Works

When you call `GeographyLevel(value)` and `value` isn't an exact match for any member's `.value`, Python calls the `_missing_()` classmethod. Our implementation calls `resolve_geographic_level()` to find the canonical name, then finds the matching enum member.

This means any string that `resolve_geographic_level()` accepts will also work with `GeographyLevel()`.

---

## BOUNDARY_TYPE_CATALOG

**Location:** `siege_utilities/geo/spatial_data.py`

A comprehensive catalog of all Census TIGER/Line boundary types with metadata.

```python
from siege_utilities.geo.spatial_data import BOUNDARY_TYPE_CATALOG

BOUNDARY_TYPE_CATALOG['cd']
# → {'category': 'redistricting', 'abbrev': 'CD', 'name': 'Congressional Districts'}

BOUNDARY_TYPE_CATALOG['county']
# → {'category': 'general', 'abbrev': 'COUNTY', 'name': 'Counties'}
```

### Structure

Each entry has:
- **`category`**: Either `'redistricting'` (political boundaries that change) or `'general'` (administrative/statistical boundaries)
- **`abbrev`**: TIGER/Line file abbreviation (used in download URLs)
- **`name`**: Human-readable name

### Categories

**Redistricting** (boundaries used in redistricting and electoral analysis):
- `state`, `county`, `cousub`, `tract`, `block_group`, `block`, `tabblock20`, `tabblock10`, `place`
- `cd`, `cd116`, `cd117`, `cd118`, `cd119` — Congressional Districts
- `sldu`, `sldl` — State Legislative Districts
- `vtd`, `vtd20` — Voting Districts
- `zcta` — ZIP Code Tabulation Areas

**General** (statistical, administrative, and infrastructure):
- `cbsa`, `csa`, `metdiv`, `micro` — Metropolitan/Micropolitan areas
- `necta`, `nectadiv`, `cnecta` — New England areas
- `aiannh`, `aitsce`, `ttract`, `tbg`, `anrc` — Tribal areas
- `elsd`, `scsd`, `unsd` — School districts
- `roads`, `rails`, `edges` — Transportation
- `linear_water`, `area_water` — Hydrography
- `address_features`, `concity`, `submcd`, `uac`, `uac20` — Other

### Session-Specific Variants

Keys like `cd116`, `cd117`, `cd118`, `cd119` represent specific Congress sessions. Their base type (`cd`) is a canonical geographic level; the session-specific variants are boundary types for TIGER/Line downloads.

### Discovery Function

```python
from siege_utilities.geo.spatial_data import discover_boundary_types

redistricting = discover_boundary_types(category='redistricting')
general = discover_boundary_types(category='general')
all_types = discover_boundary_types()
```

---

## TIGER_FILE_PATTERNS

**Location:** `siege_utilities/config/census_constants.py`

Maps canonical geographic levels to their TIGER/Line download URL patterns.

```python
from siege_utilities.config.census_constants import TIGER_FILE_PATTERNS, get_tiger_url

TIGER_FILE_PATTERNS['county']
# → 'tl_{year}_us_county.zip'

TIGER_FILE_PATTERNS['tract']
# → 'tl_{year}_{state_fips}_tract.zip'

# Convenience function (accepts aliases)
get_tiger_url('congressional_district', year=2020)
# → resolves to 'cd', returns full URL
```

### State-Required vs National

Some levels download as a single national file; others require a state FIPS code:

| Pattern | National | State-Required |
|---------|----------|----------------|
| `tl_{year}_us_*.zip` | nation, state, county, zcta, cd, cbsa | — |
| `tl_{year}_{state_fips}_*.zip` | — | cousub, tract, block_group, block, place, sldu, sldl, vtd, puma |

---

## GEOGRAPHIC_HIERARCHY

**Location:** `siege_utilities/config/census_constants.py`

The nesting order of statistical geographies, from largest to smallest:

```python
from siege_utilities.config.census_constants import GEOGRAPHIC_HIERARCHY

GEOGRAPHIC_HIERARCHY
# → ['nation', 'region', 'division', 'state', 'county', 'cousub', 'tract', 'block_group', 'block']
```

All entries use **canonical names** (e.g., `'cousub'` not `'county_subdivision'`).

---

## Backward-Compatible GEOGRAPHIC_LEVELS

**Location:** `siege_utilities/config/census_constants.py`

A dict that preserves the original UPPER_CASE key format for backward compatibility, but values now come from the canonical system:

```python
from siege_utilities.config.census_constants import GEOGRAPHIC_LEVELS

GEOGRAPHIC_LEVELS['STATE']                    # → 'state'
GEOGRAPHIC_LEVELS['COUNTY']                   # → 'county'
GEOGRAPHIC_LEVELS['CONGRESSIONAL_DISTRICT']   # → 'cd'       (was 'congressional_district')
GEOGRAPHIC_LEVELS['COUNTY_SUBDIVISION']       # → 'cousub'   (was 'county_subdivision')
GEOGRAPHIC_LEVELS['ZIP_CODE']                 # → 'zcta'     (was 'zip_code')
```

**Note:** This dict exists only for backward compatibility. New code should use `CANONICAL_GEOGRAPHIC_LEVELS` or `resolve_geographic_level()` directly.

---

## How They Relate

```
CANONICAL_GEOGRAPHIC_LEVELS (single source of truth)
├── derives → GEOID_LENGTHS (geoid_utils.py)
├── derives → GEOGRAPHIC_LEVELS (backward compat, census_constants.py)
├── drives  → resolve_geographic_level() (alias resolution)
├── drives  → validate_geographic_level() (boolean check)
├── drives  → GeographyLevel enum (_missing_ classmethod)
└── keys match → TIGER_FILE_PATTERNS (download URLs)

BOUNDARY_TYPE_CATALOG (spatial_data.py)
├── keys are canonical names for base types
├── also includes session-specific variants (cd116, cd117, ...)
└── used by → discover_boundary_types(), get_census_boundaries()

GEOGRAPHIC_HIERARCHY (census_constants.py)
└── uses canonical names for nesting order

All GEOID functions (geoid_utils.py)
└── call resolve_geographic_level() on geography parameter
```

---

## Common Usage Patterns

### Downloading Boundaries

```python
from siege_utilities.geo.spatial_data import get_census_boundaries

# All of these work — aliases resolved internally
counties = get_census_boundaries(2020, 'county', state_fips='06')
tracts = get_census_boundaries(2020, 'tract', state_fips='06')
cds = get_census_boundaries(2020, 'cd')  # national file
```

### Working with GEOIDs

```python
from siege_utilities.geo.geoid_utils import (
    construct_geoid, parse_geoid, normalize_geoid, validate_geoid
)

# Build a GEOID from components
geoid = construct_geoid('tract', state='06', county='037', tract='101100')
# → '06037101100'

# Parse a GEOID into components
parts = parse_geoid('06037101100', 'tract')
# → {'state': '06', 'county': '037', 'tract': '101100'}

# Zero-pad a short GEOID
normalized = normalize_geoid('6037', 'county')
# → '06037'

# Validate format
is_valid = validate_geoid('06037', 'county')
# → True
```

### Census API Queries

```python
from siege_utilities.geo.census_api_client import CensusAPIClient

client = CensusAPIClient(api_key='your-key')

# geography parameter accepts any variant
data = client.get_demographics(2022, 'tract', '06', 'income')
data = client.get_demographics(2022, 'block_group', '06', 'population')
```

### Resolving User Input

```python
from siege_utilities.config.census_constants import resolve_geographic_level

user_input = 'Congressional District'  # from form, CLI, config file
canonical = resolve_geographic_level(user_input)  # → 'cd'
# Now use 'cd' everywhere downstream
```

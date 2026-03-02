# Compatibility Policy

## Python Versions

| Version | Status |
|---------|--------|
| 3.11 | Supported (CI matrix, Databricks LTS) |
| 3.12 | Supported (CI matrix) |
| 3.10 | Not tested; may work but not guaranteed |
| < 3.10 | Not supported |

## Pydantic

**Requirement:** `pydantic>=2.0.0`

siege_utilities is built for Pydantic v2. A lazy-load compatibility shim in
`config/__init__.py` (lines 238-330) allows importing the library when Pydantic v1
is installed, but all schema functionality requires v2. The CI job `test-pydantic-v1`
validates that the library imports cleanly under v1 without crashing.

**In practice:** Always install Pydantic v2. The v1 shim exists only so downstream
packages with mixed dependency trees don't fail at import time.

## System Dependencies (GDAL / GEOS / PROJ)

Geospatial features (`siege_utilities.geo`) require GDAL, GEOS, and PROJ system
libraries. These are **not** Python packages and must be installed separately.

### Ubuntu / Debian

```bash
sudo apt-get install -y gdal-bin libgdal-dev libgeos-dev libproj-dev
```

### macOS (Homebrew)

```bash
brew install gdal geos proj
```

### Databricks

GDAL is **not available** on standard Databricks runtimes. The `geo` extra will
install geopandas and shapely (which bundle their own GEOS/PROJ via wheels), but
GDAL-dependent features (Fiona file I/O, Django GIS) will not work. Use the
`databricks_fallback` module for cluster-safe spatial loading.

### When GDAL Is Not Required

The following modules work **without** GDAL:

- `siege_utilities.core` (logging, strings, sql_safety)
- `siege_utilities.config` (Pydantic models, census constants)
- `siege_utilities.geo.geoid_utils` (GEOID manipulation)
- `siege_utilities.geo.boundary_result` (result types and exceptions)
- `siege_utilities.databricks` (all modules)
- `siege_utilities.data` (sample data, Faker)

The CI job `test-core` validates that core modules import without any heavy deps.
The CI job `test-geo-no-gdal` validates geo without system GDAL.

## Optional Dependency Groups

Install only what you need:

```bash
# Core only (pydantic, pyyaml, requests, tqdm)
pip install siege-utilities

# Geospatial
pip install siege-utilities[geo]

# Data manipulation (pandas, numpy, openpyxl)
pip install siege-utilities[data]

# Databricks SDK
pip install siege-utilities[databricks]

# GeoDjango (Django + PostGIS)
pip install siege-utilities[geodjango]

# Everything
pip install siege-utilities[all]

# Development
pip install siege-utilities[dev]
```

| Extra | Key Packages | System Deps |
|-------|-------------|-------------|
| `geo` | geopandas, shapely, pyproj, fiona | GDAL, GEOS, PROJ |
| `data` | pandas, numpy, openpyxl, faker | None |
| `databricks` | databricks-sdk | None |
| `distributed` | pyspark, apache-sedona | Java 17+ |
| `geodjango` | django, djangorestframework-gis | GDAL, PostGIS |
| `reporting` | matplotlib, seaborn, folium, reportlab | None |
| `analytics` | google-analytics-data, scipy, scikit-learn | None |
| `config-extras` | hydra-core, hydra-zen, omegaconf | None |
| `database` | psycopg2-binary, sqlalchemy | PostgreSQL client libs |
| `dev` | pytest, pytest-cov, black, flake8, django | GDAL (for full test suite) |

## Dependency Ceilings

To prevent breaking changes from upstream, the `geo` extra pins upper bounds:

- `geopandas>=0.13.2,<1.0` - geopandas 1.0 may change APIs
- `shapely>=1.8.0,<3.0` - shapely 3.0 may change geometry model

These ceilings will be raised as upstream releases are validated.

## Lazy-Load Pattern

siege_utilities uses PEP 562 (`__getattr__` / `__dir__`) for lazy imports at both
the package level (`siege_utilities/__init__.py`) and the geo subpackage
(`siege_utilities/geo/__init__.py`). This means:

- `import siege_utilities` is fast (< 100ms) even with all extras installed
- Heavy modules (geopandas, pyspark, django) are only loaded on first access
- Core functionality (config, logging, strings) is always available
- Import errors for missing optional deps surface at use time, not import time

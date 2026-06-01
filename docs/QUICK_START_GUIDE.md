# Quick Start Guide - Siege Utilities

Get up and running with Siege Utilities. This guide is ordered by
architectural priority: geo is the gravitational center, engines scale it,
credentials unlock it, and domain packages feed it.

## Installation

```bash
# Core with geospatial support (recommended — geo is the center of the library)
pip install siege-utilities[geo]

# Full installation (geo + distributed + dev tools)
pip install siege-utilities[distributed,geo,dev]
```

## The Composition Chain

The canonical workflow in siege_utilities is:

```
address -> geocoder -> GEOID -> boundary provider -> demographic overlay -> choropleth or report
```

Everything starts with geo. Domain packages (political, economic, education,
survey, analytics) produce events; geo locates them in space-time; engines
scale the computation; reporting presents the results.

## 1. Geospatial (the gravitational center)

```python
import siege_utilities as su

# Get Census boundaries — the starting point for most analyses
counties = su.get_census_boundaries(
    year=2020,
    geographic_level='county',
    state_fips='06'  # California
)
print(f"Found {len(counties)} counties")

# Geocode addresses into the coordinate system
addresses = ["San Francisco, CA", "Los Angeles, CA"]
for address in addresses:
    result = su.use_nominatim_geocoder(address)
    if result:
        coords = json.loads(result)
        print(f"{address}: {coords['nominatim_lat']}, {coords['nominatim_lng']}")
```

Geo uses the OSGeo stack (GDAL/OGR, PROJ, Shapely, Fiona, rasterio) by
default. When the deployment target cannot run C libraries (Databricks,
Lambda), use Sedona or DuckDB-spatial — the constraint must be explicit.

## 2. Engine-Agnostic DataFrame

The same analysis at different scales without rewriting:

```python
from siege_utilities.engines import get_engine

# pandas for exploration
engine = get_engine("pandas")
df = engine.read_parquet("boundaries.parquet")

# DuckDB for medium scale
engine = get_engine("duckdb")
df = engine.read_parquet("boundaries.parquet")

# Spark for distribution
engine = get_engine("spark")
df = engine.read_parquet("boundaries.parquet")
```

When you must drop to native (Spark SQL, raw pandas), use that engine's
idioms directly. The abstraction serves the general case.

## 3. Credential Management

Credentials come from external tools — never hardcoded:

```python
# 1Password CLI (preferred when siege_zsh is available)
# Environment variables (standard fallback)
# Databricks secret scopes (in-cluster)

from siege_utilities.config import HydraConfigManager

with HydraConfigManager() as manager:
    user_profile = manager.load_user_profile()
    print(f"Welcome, {user_profile.full_name}!")
```

The `siege_zsh` shell environment sets up credentials that siege_utilities
expects. Code detects and leverages these conventions but does not hard-fail
without them.

## 4. Distributed Computing

```python
# Spark Connect — setup requires PySpark
spark, data_path = su.setup_distributed_environment()
```

### Databricks (first-class target)

Azure Databricks cannot install GDAL. The `databricks/` bridge pattern
(Spark -> driver-side GeoPandas -> back to Spark) is the architectural
solution:

```python
from siege_utilities.databricks import get_databricks_client

client = get_databricks_client()
```

### Snowflake (first-class target)

Snowflake's geography type and Trino federation are parallel vendor paths
for spatial computation at scale.

## 5. Domain Packages

Domain packages are primitives, not applications. They encode domain
expertise — what data exists, where it lives, how to access it — not domain
analysis.

```python
# Political: DDL and entities for political geography
from siege_utilities.political import get_redistricting_plan

# Education: NCES data downloads
from siege_utilities.education import download_nces_data

# Survey: pipeline composition (Chain, weights, significance)
from siege_utilities.survey import Chain

# Analytics: third-party connectors (GA, data sources)
from siege_utilities.analytics import create_ga_connector
```

## 6. Configuration and Profiles

```python
from siege_utilities.config import UserProfile, ClientProfile, BrandingConfig

# User profile
user = UserProfile(
    username="analyst",
    email="analyst@example.com",
    full_name="Data Analyst",
    default_output_format="pptx",
    preferred_download_directory="/Users/analyst/output"
)

# Client branding for reports
from siege_utilities.config import HydraConfigManager

with HydraConfigManager() as manager:
    branding = manager.load_branding_config("client_a")
    print(f"Primary color: {branding.primary_color}")
```

## 7. Core Utilities

```python
import siege_utilities as su

# Logging — every side-effecting process must produce observable output
su.log_info("Starting pipeline")

# File operations
hash_value = su.get_file_hash("myfile.txt")
su.ensure_path_exists("data/processed")

# String utilities
clean_text = su.remove_wrapping_quotes_and_trim('  "hello world"  ')
```

## Troubleshooting

### Missing Dependencies

```python
# ImportError propagates with an actionable message — do not swallow it.
# The library uses lazy loading (PEP 562 __getattr__), so import errors
# surface when you first access a name, not at module import time.

# WRONG — violates SU-1 (errors are not data):
# try:
#     from siege_utilities.geo import something
# except ImportError:
#     print("not available")  # caller cannot distinguish this from success

# RIGHT — let the error propagate with context:
from siege_utilities.geo import get_census_boundaries  # raises ImportError if GDAL missing
```

### Configuration Issues

```python
from siege_utilities.config import get_default_profile_location

profile_dir = get_default_profile_location()
print(f"Profile directory: {profile_dir}")

# Create default profiles if needed
from siege_utilities.config import create_default_profiles
create_default_profiles()
```

## Next Steps

1. **Notebooks**: 32 notebooks in `notebooks/` organized by domain (spatial, engines, reports, foundations)
2. **Architecture**: `docs/ARCHITECTURE.md` for the full structural picture
3. **Intent**: `docs/INTENT.md` for one-line module purposes
4. **Tests**: `python -m pytest tests/` to verify the installation

## Key Principles

- **Geo is the gravitational center** — all domain modules produce events that need space-time location
- **Errors are not data (SU-1)** — never return empty results on failure; raise or log with a warning
- **Lazy loading by design** — import one piece without pulling the whole library
- **Temporal awareness is first-class** — not just "where" but "where-when"

---

**Ready to dive deeper?** See [ARCHITECTURE.md](ARCHITECTURE.md) and [CLAUDE.md](../CLAUDE.md) for the full set of architectural principles.

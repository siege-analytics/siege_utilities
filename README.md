# Siege Utilities

A comprehensive Python utilities package providing **300+ functions** across **12 categories** for data engineering, analytics, geospatial analysis, and distributed computing workflows.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: AGPLv3%20or%20Commercial](https://img.shields.io/badge/License-AGPLv3%20or%20Commercial-orange.svg)](LICENSE)
[![Functions](https://img.shields.io/badge/functions-300+-orange.svg)](https://github.com/siege-analytics/siege_utilities)
[![Tests](https://img.shields.io/badge/tests-1800+-green.svg)](https://github.com/siege-analytics/siege_utilities)
[![Documentation](https://img.shields.io/badge/docs-GitHub%20Pages-blue)](https://siege-analytics.github.io/siege_utilities/)

## What This Does

**siege_utilities** is the foundational verb layer for Siege Analytics. It provides:

- **Geospatial Intelligence**: 37 Django models for Census, GADM, political, education, federal, and timezone boundaries with PostGIS spatial queries
- **Census Data Pipeline**: API client, PL 94-171 redistricting data, demographic snapshots, time series, and crosswalk-aware rollups
- **Configuration Management**: Hydra + Pydantic configs with client-specific overrides
- **Distributed Computing**: Spark utilities, HDFS operations, Databricks integration
- **Professional Reporting**: PDF generation, PowerPoint, choropleths, and Google Analytics reports

## Quick Start

```bash
# Core only (pyyaml, requests, tqdm, pydantic) — fast, minimal
pip install siege-utilities

# With geospatial support
pip install siege-utilities[geo]

# With GeoDjango (Django + PostGIS)
pip install siege-utilities[geodjango]

# Everything
pip install siege-utilities[all]
```

```python
import siege_utilities  # ~0.02s (lazy loaded via PEP 562)

# Core functions always available
siege_utilities.log_info("Ready.")

# Geo functions load on first access (requires [geo] extra)
from siege_utilities.geo import select_census_datasets
recommendations = select_census_datasets("demographics", "tract")

# Missing extras give helpful errors, not crashes
try:
    from siege_utilities import ReportGenerator  # requires [reporting]
except ImportError as e:
    print(e)  # Shows exactly what to install
```

## GeoDjango Integration

Full spatial data platform with **37 concrete models**, **9 population services**, and **7 management commands**.

### Model Hierarchy

```
TemporalGeographicFeature (abstract — no geometry)
├── TemporalBoundary (abstract — MultiPolygon)
│   ├── CensusTIGERBoundary (abstract — GEOID + TIGER metadata)
│   │   ├── State, County, Tract, BlockGroup, Block, Place, ZCTA
│   │   ├── CongressionalDistrict, CBSA, UrbanArea
│   │   ├── StateLegislativeUpper, StateLegislativeLower, VTD, Precinct
│   │   └── SchoolDistrictElementary, Secondary, Unified
│   ├── GADMBoundary → GADMCountry, GADMAdmin1-5
│   ├── NLRBRegion, FederalJudicialDistrict
│   ├── NCESLocaleBoundary, TimezoneGeometry
│   └── Intersections (County×CD, VTD×CD, Tract×CD)
├── TemporalLinearFeature (abstract — MultiLineString)
└── TemporalPointFeature (abstract — Point)
    └── SchoolLocation
```

### Spatial Queries

```python
from django.contrib.gis.geos import Point
from siege_utilities.geo.django.models import Tract, County, State

# Find tract containing a point
point = Point(-122.4194, 37.7749, srid=4326)
tract = Tract.objects.containing_point(point).for_year(2020).first()

# Nearest boundaries within distance
nearby = County.objects.nearest(point, distance_km=50)

# Temporal + spatial filtering
counties_2020 = County.objects.for_state("06").for_year(2020)
```

### Management Commands

```bash
# Census TIGER/Line boundaries
python manage.py populate_boundaries --year 2020 --type county --state CA

# Demographics from ACS
python manage.py populate_demographics --year 2020 --dataset acs5 --variables B19013_001

# PL 94-171 redistricting data
python manage.py populate_pl_demographics --year 2020 --state CA

# Boundary crosswalks (2010 → 2020)
python manage.py populate_crosswalks --source-year 2010 --target-year 2020

# NCES school district + locale data
python manage.py populate_nces --year 2020

# NLRB region boundaries
python manage.py populate_nlrb_regions --year 2024

# Timezone boundaries (from timezone-boundary-builder)
python manage.py populate_timezones --file timezones.geojson --year 2024
```

### Services

| Service | Purpose |
|---------|---------|
| `BoundaryPopulationService` | Load TIGER/Line shapefiles into boundary models |
| `DemographicPopulationService` | Fetch ACS/Decennial data into DemographicSnapshot |
| `CrosswalkPopulationService` | Build boundary change crosswalks between vintages |
| `TimeseriesService` | Auto-populate DemographicTimeSeries from snapshots |
| `DemographicRollupService` | Aggregate child geographies to parents (GEOID or crosswalk) |
| `UrbanicityClassificationService` | Classify tracts by NCES urbanicity codes |
| `NCESPopulationService` | Load school districts, locales, and school locations |
| `NLRBPopulationService` | Populate NLRB region boundaries |
| `TimezonePopulationService` | Load IANA timezone geometries from GeoJSON |

### Demographics & Rollups

```python
from siege_utilities.geo.django.models import DemographicSnapshot, DemographicTimeSeries
from siege_utilities.geo.django.services import DemographicRollupService

# Query demographics
snapshots = DemographicSnapshot.objects.filter(
    content_type__model='tract',
    dataset='acs5',
    year=2020,
)

# Roll up tract data to county level
svc = DemographicRollupService()
results = svc.rollup(
    source_level='tract',
    target_level='county',
    year=2020,
    variables=['B19013_001', 'B01003_001'],
    state_fips='06',
    min_coverage=0.8,  # warn if <80% of child geographies have data
)

# Crosswalk-aware rollup (handles boundary changes)
results = svc.rollup(
    source_level='tract',
    target_level='county',
    year=2020,
    variables=['B01003_001'],
    crosswalk_year=2010,  # map 2010 tracts to 2020 counties via crosswalk
)
```

## Census Data Intelligence

Consolidated Census metadata registry with intelligent dataset selection.

```python
from siege_utilities.config.census_registry import (
    SurveyType, GeographyLevel, resolve_geographic_level,
    VARIABLE_GROUPS, CANONICAL_GEOGRAPHIC_LEVELS,
)
from siege_utilities.geo import quick_census_selection

# Resolve geography aliases
level = GeographyLevel("congressional_district")  # resolves alias → "cd"

# Quick selection for analysis
result = quick_census_selection("business", "county")
print(f"Use {result['recommendations']['primary_recommendation']['dataset']}")

# Census API with caching
from siege_utilities.geo import CensusAPIClient

client = CensusAPIClient(cache_backend='django')  # or 'sqlite', 'memory'
data = client.get_acs5(
    year=2020,
    variables=['B19013_001'],
    geography='tract',
    state='06',
)
```

## Census API Client

Direct access to Census Bureau data with built-in caching and rate limiting.

```python
from siege_utilities.geo import CensusAPIClient

client = CensusAPIClient(api_key="your-key")

# ACS 5-Year estimates
median_income = client.get_acs5(
    year=2020,
    variables=['B19013_001', 'B01003_001'],
    geography='county',
    state='06',
)

# PL 94-171 redistricting data
from siege_utilities.geo.census_files.pl_downloader import PLFileDownloader

downloader = PLFileDownloader()
pl_data = downloader.download_state("CA", year=2020)
```

## Hydra + Pydantic Configuration

```python
from siege_utilities.config import HydraConfigManager

with HydraConfigManager() as manager:
    user_profile = manager.load_user_profile()
    branding = manager.load_branding_config("client_a")
    db_connections = manager.load_database_connections("client_a")
```

## Reporting & Visualization

```python
from siege_utilities.reporting.examples.google_analytics_report_example import (
    generate_ga_report_pdf
)

# Professional PDF with KPI cards, sparklines, geographic maps
generate_ga_report_pdf(
    ga_data=ga_data,
    output_path="report.pdf",
    client_name="Demo Company",
)
```

**Capabilities**: 7+ map types (choropleth, marker, 3D, heatmap, cluster, flow), PDF reports with TOC, PowerPoint generation, GA geographic analysis with Census demographic joins.

## Function Categories

| Category | Count | Description | Dependencies |
|----------|-------|-------------|--------------|
| **Core** | 16 | Logging, strings, basic utils | None |
| **Config** | 54 | Database, project, client setup | None |
| **Files** | 21 | File ops, paths, remote downloads | None |
| **Distributed** | 37 | Spark utilities, HDFS operations | PySpark |
| **Geo** | 65+ | Census data, boundaries, spatial, GeoDjango | pandas, geopandas |
| **Analytics** | 28 | Google Analytics, Snowflake APIs | pandas, connectors |
| **Reporting** | 30+ | Charts, maps, GA reports, PDF generation | matplotlib, reportlab |
| **Testing** | 15 | Environment setup, test runners | None |
| **Git** | 9 | Branch ops, commit management | None |
| **Development** | 9 | Architecture analysis, code hygiene | None |
| **Hygiene** | 5 | Docstring generation, analysis | None |
| **Data** | 3 | Sample data utilities | pandas |

## Installation Options

```bash
# Core only (pyyaml, requests, tqdm, pydantic)
pip install siege-utilities

# Add extras for what you need
pip install siege-utilities[geo]              # geopandas, shapely, pyproj, tobler
pip install siege-utilities[geodjango]        # Django, DRF, PostGIS
pip install siege-utilities[data]             # pandas, numpy, openpyxl, faker
pip install siege-utilities[reporting]        # matplotlib, seaborn, folium, plotly, reportlab
pip install siege-utilities[analytics]        # GA4, Facebook, Snowflake, scipy, scikit-learn
pip install siege-utilities[distributed]      # PySpark, Apache Sedona
pip install siege-utilities[config-extras]    # Hydra, hydra-zen, omegaconf
pip install siege-utilities[web]              # BeautifulSoup, lxml
pip install siege-utilities[database]         # SQLAlchemy, psycopg2
pip install siege-utilities[all]              # Everything

# Combine extras
pip install siege-utilities[data,geo,reporting]

# Development
git clone https://github.com/siege-analytics/siege_utilities.git
cd siege_utilities
pip install -e ".[all,dev]"
```

## Testing

**1800+ tests** across all modules.

```bash
# Full suite
python -m pytest tests/ -v

# By marker
python -m pytest tests/ -m core
python -m pytest tests/ -m geo
python -m pytest tests/ -m "not requires_gdal"

# Quick smoke test
python -m pytest tests/ --tb=short -q
```

## Architecture

```
siege_utilities/
├── config/              # Census registry, Hydra/Pydantic configs, client management
│   ├── census_registry.py   # Single source of truth for Census metadata
│   └── ...
├── geo/                 # Geospatial: Census API, GEOID utils, geocoding, spatial ops
│   ├── census_api_client.py
│   ├── census_files/    # PL 94-171, TIGER/Line downloaders
│   └── django/          # GeoDjango integration
│       ├── models/      # 37 concrete models (boundaries, demographics, crosswalks)
│       ├── services/    # 9 population services
│       ├── management/  # 7 management commands
│       ├── managers/    # Custom querysets (containing_point, nearest, for_year)
│       └── serializers/ # DRF GeoJSON serializers
├── distributed/         # Spark, HDFS, Databricks utilities
├── reporting/           # PDF, PowerPoint, choropleth, GA reports
├── analytics/           # GA4, Snowflake connectors
├── files/               # File operations, hashing, remote downloads
├── core/                # Logging, string utilities
└── development/         # Architecture analysis, package management
```

## Documentation

- **Sphinx Docs**: [siege-analytics.github.io/siege_utilities](https://siege-analytics.github.io/siege_utilities/)
- **Notebooks**: 15 Jupyter notebooks covering all major features (in `notebooks/`)

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Run tests: `python -m pytest tests/ --tb=short -q`
4. Commit and push
5. Submit a Pull Request

## License

Dual license model (effective March 6, 2026):

- AGPL-3.0-only for open-source usage
- Commercial license for proprietary/commercial usage by separate agreement

Attribution is required in both paths. See `LICENSE`, `LICENSES/AGPL-3.0.txt`, and `COMMERCIAL_LICENSE.md`.

---

**Siege Utilities**: Spatial Intelligence, In Python.

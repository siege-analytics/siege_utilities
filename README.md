# Siege Utilities

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: AGPLv3%20or%20Commercial](https://img.shields.io/badge/License-AGPLv3%20or%20Commercial-orange.svg)](LICENSE)
[![Documentation](https://img.shields.io/badge/docs-GitHub%20Pages-blue)](https://siege-analytics.github.io/siege_utilities/)

`siege_utilities` is the shared utilities library behind Siege Analytics workflows:

- Geospatial + GeoDjango boundary/data services
- Census API/data selection/crosswalk tooling
- Configuration and profile management
- Distributed processing helpers (Spark/HDFS/Databricks)
- Reporting and chart generation

## Install

See [Installation Options](#installation-options) for all supported install commands (`base`, `geo`, `geodjango`, `all`).

## Quick Usage

```python
import siege_utilities as su

su.log_info("Ready.")
recommendations = su.select_census_datasets("demographics", "tract")
```

## Import Philosophy

This project intentionally favors convenience access patterns, including broad function availability from the package surface. That is a design choice, not an accident.

Contributor rule: convenience imports are acceptable in explicit API-aggregation surfaces, but implementation modules should prefer explicit imports to avoid hidden collisions and reduce regression risk.

## Contributor Requirements

Every PR must include:

- Tests for changed behavior (and regression test for bug fixes)
- Documentation updates
- Notebook updates when user-facing workflows or APIs change
- CodeRabbit feedback addressed for correctness/regression/API-risk findings
- Required CI/PR checks green (including CodeRabbit status once enabled)

### Pre-PR Validation Commands

```bash
# Test naming/location hygiene
python scripts/check_test_file_hygiene.py

# API contract tooling regression check
python scripts/contracts/generate_public_api_contract.py --output /tmp/contract_candidate.json
python scripts/contracts/compare_public_api_contracts.py \
  --baseline /tmp/contract_baseline.json \
  --candidate /tmp/contract_candidate.json \
  --release-impact patch \
  --allowlist scripts/contracts/contract_allowlist.json

# Contract-tool unit tests
python -m pytest -q --no-cov tests/test_api_contract_tools.py
```

See:

- `docs/policies/CODING_STYLE.md`
- `docs/policies/PR_REVIEW_RUBRIC.md`
- `docs/policies/CHANGE_CLASSIFICATION_AND_RELEASE_POLICY.md`
- `docs/policies/CONTRIBUTOR_GOVERNANCE.md`
- `docs/EXAMPLES.md`

## External Contributor Workflow

Use this path when contributing from a fork:

1. Fork this repository on GitHub, then clone your fork:

```bash
git clone https://github.com/<your-user>/siege_utilities.git
cd siege_utilities
git remote add upstream https://github.com/siege-analytics/siege_utilities.git
```

2. Create and activate a local virtual environment, then install from the cloned repo:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

3. Validate notebooks and notebook outputs:

```bash
python -m pytest -q --no-cov tests/test_notebooks_output_policy.py
```

If your change updates user-facing workflows or APIs, update the impacted notebooks and ensure `notebooks/output/` artifacts remain reviewable.

4. Open an issue in `siege-analytics/siege_utilities` describing the change for merge review, link your fork branch/PR, and include:
- Reproduction or motivation
- Proposed change scope
- Test evidence
- Documentation and notebook updates

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

# Nearest boundaries within distance (meters)
nearby = County.objects.nearest(point, max_distance_m=50_000)

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
from siege_utilities.reporting import ReportGenerator

report_gen = ReportGenerator(client_name="Demo Company")

report_content = {
    "metadata": {"title": "Analytics Summary"},
    "sections": [{"type": "text", "title": "Overview", "content": "Report summary."}],
}
report_gen.generate_pdf_report(report_content, output_path="report.pdf")
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

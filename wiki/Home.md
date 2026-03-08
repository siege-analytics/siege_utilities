# Siege Utilities Wiki

Welcome to the comprehensive documentation and examples for Siege Utilities - a powerful Python utilities package with enhanced auto-discovery and comprehensive geographic data processing capabilities.

**Current Version:** [v2.0.0](https://pypi.org/project/siege-utilities/2.0.0/) | [GitHub Release](https://github.com/siege-analytics/siege_utilities/releases/tag/v2.0.0) | **Python >= 3.11**

```bash
pip install siege-utilities==2.0.0
```

## What's New in v2.0.0

- **Person/Actor architecture** — unified domain model with Hydra config, JSON/CSV/Parquet export
- **Geographic reconciliation** — 20 canonical levels, alias resolution, GeographyLevel enum
- **Census API client** — retry/fallback, boundary type catalog, state FIPS lookup
- **GeoDjango integration** — spatial data utilities for choropleth generation
- **OAuth2 1Password credential wiring** — GA4 reporting with service-account fallback
- **GA4 multi-client reporter** — real Analytics 4 data fetching with cached OAuth2 tokens
- **Choropleth library** — heatmap dispatcher, bivariate choropleth, Folium attribution fixes
- **Release manager** — `scripts/release_manager.py` with PyPI upload, twine validation, git tagging
- **17 Jupyter notebooks** — data science workflows, spatial analysis, GA4 reporting
- **724 tests** — unit, E2E, and pipeline/environment coverage

## Core Documentation

### Getting Started
- [**Basic Setup**](Getting-Started.md) - Quick start guide for new users
- [**Architecture Overview**](Architecture-Analysis.md) - Understanding the system design
- [**Testing Guide**](Testing-Guide.md) - Comprehensive testing strategies

### Core Utilities
- [**String Utilities**](String-Utilities.md) - Text processing and manipulation
- [**File Operations**](File-Operations.md) - File and directory management
- [**Logging Utilities**](Logging.md) - Advanced logging and debugging

### Geographic & Spatial Data
- [**Enhanced Census Utilities**](Enhanced-Census-Utilities.md) - Dynamic Census data access
- [**Geocoding Services**](Geocoding.md) - Address geocoding and reverse geocoding
- [**Configurable Map Generation**](Configurable-Map-Generation.md) - Choropleth and thematic maps
- [**Bivariate Choropleth Maps**](Bivariate-Choropleth-Maps.md) - Advanced mapping techniques
- [**3D Mapping**](3D-Mapping.md) - Three-dimensional spatial visualization

### Distributed Computing
- [**HDFS Operations**](HDFS-Operations.md) - Hadoop Distributed File System integration
- [**Spark Utilities**](Spark-Processing.md) - Apache Spark processing and optimization
- [**Batch Processing**](Batch-Processing.md) - Large-scale data processing workflows

### Analytics & Reporting
- [**Analytics Integration**](Analytics-Integration.md) - Facebook Business, Google Analytics, and more
- [**Comprehensive Reporting**](Comprehensive-Reporting.md) - Advanced reporting and visualization

### Configuration & Credentials
- [**Enhanced Configuration System**](Enhanced-Configuration-System.md) - Hydra/Pydantic config
- [**Database Connections**](Database-Connections.md) - Database integration
- [**UV Package Management**](UV-Package-Management.md) - Modern package management

### Advanced Features
- [**Remote Operations**](Remote-Operations.md) - SSH and remote system management
- [**Shell Operations**](Shell-Operations.md) - Command-line automation and scripting
- [**Code Modernization**](Code-Modernization.md) - Legacy code upgrade strategies
- [**Multi-Engine Processing**](Multi-Engine-Data-Processing.md) - Distributed computing

## Recipe Collection

### Advanced Workflows
- [**Advanced Census Workflows**](Recipes/Advanced-Census-Workflows.md) - Complex Census data pipelines
- [**Demographic Analysis Pipeline**](Recipes/Demographic-Analysis-Pipeline.md) - Demographic analysis
- [**Census Data Intelligence Guide**](Recipes/Census-Data-Intelligence-Guide.md) - Smart data retrieval
- [**Business Intelligence Site Selection**](Recipes/Business-Intelligence-Site-Selection.md) - BI/site selection
- [**Real Estate Market Intelligence**](Recipes/Real-Estate-Market-Intelligence.md) - Real estate analytics

### Examples
- [**Client Management**](Examples/Client-Management.md) - Managing client profiles and configurations

## Architecture
- [**System Architecture Overview**](Architecture/System-Architecture-Overview.md) - High-level design
- [**Code Decisions and Design Patterns**](Architecture/Code-Decisions-and-Design-Patterns.md) - Design rationale
- [**System Interrelationships**](Architecture/System-Interrelationships.md) - Module dependencies

## Quick Start

```python
import siege_utilities as su

# Check version
print(su.__version__)  # 2.0.0

# Census data
from siege_utilities.geo.spatial_data import census_source
years = census_source.discovery.get_available_years()
ca_counties = census_source.get_geographic_boundaries(
    year=2020, geographic_level='county', state_fips='06'
)

# Person/Actor model
from siege_utilities.models.person import Person
person = Person(first_name="Jane", last_name="Doe")
```

## Development

- **Branch model:** `main` (releases) / `develop` (integration) / `dheerajchand/<feature>` (feature work)
- **Release process:** See `scripts/release_manager.py` and [Contributor Governance](../CONTRIBUTOR_GOVERNANCE.md)
- **Tests:** `pytest tests/ -x -q` (724 tests, 30% coverage)
- **CI/CD:** GitHub Actions with test, battle-test, build, release, security jobs

## Integration & Compatibility

- **Data Science Stack**: Pandas, NumPy, GeoPandas, Shapely
- **Big Data**: Apache Spark, Hadoop, HDFS
- **Databases**: PostgreSQL/PostGIS, DuckDB (optional)
- **Cloud Platforms**: AWS, Azure, Google Cloud
- **Analytics**: Facebook Business API, Google Analytics API
- **Visualization**: Matplotlib, Seaborn, Folium, Plotly
- **Configuration**: Hydra, Pydantic, OmegaConf

---

**Ready to get started?** Install with `pip install siege-utilities` and check out [Basic Setup](Getting-Started.md).

# Changelog

All notable changes to siege_utilities will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [3.1.0] - 2026-03-01

### Added
- **NCES urbanicity download** — `NcesDownloadService`, Django models (`NcesSchool`, `NcesDistrict`, `NcesLocale`), and `populate_nces` management command (PR#173, su#136-138)
- **Areal interpolation** — `ArealInterpolationService` wrapping PySAL Tobler for area-weighted and dasymetric interpolation between geographic boundaries (PR#174, su#140)
- **Crosswalk time series analytics** — `CrosswalkTimeSeriesService` for temporal analysis across geographic boundary changes, with rollup and trend detection (PR#175, su#139)

### Fixed
- `county_fips` threading issue in geography services (su#176)
- Geography alias normalization for Census boundary lookups (su#177)
- GEOID preservation during geographic enrichment joins (su#178)
- `strict_years` validation rejecting valid year ranges in time series queries (su#180)
- Stale/missing source references in Census dataset documentation (su#163)

### Changed
- `run_tests.py` rewritten to match actual 41 test files in test suite

### Removed
- `hdfs_legacy.py` — broken duplicate stubs of HDFS utilities
- Stale `__init__.py.backup` artifact

## [3.0.1] - 2026-02-27

### Added
- **Census Django gaps** (su#116) — `nearest()` query, Tract urbanicity lookup, GEOID validators, GEOID slugs, Django cache layer, timeseries + rollup services
- **Urbanicity classification** (su#131) — `UrbanicityClassificationService` and `populate_urbanicity` management command
- Migration 0002: `urbanicity_code` field + GEOID check constraints
- Census dataset relationships documentation (`docs/data-relationships/`)
- Spatio-temporal events design doc for election cycles and races

### Fixed
- `CensusDataSelector` primary dataset bonus never applied (su#164, PR#169)
- `CheckConstraint` API: `check=` → `condition=` for Django 5.2 compatibility
- Pydantic v2 config system lazy-loaded for Databricks v1 compatibility (su#160, PR#170)

## [3.0.0] - 2026-02-25

### Added
- **Unified Geographic Model** (Epic 14) — complete rearchitecture of spatial data layer:
  - `TemporalGeographicFeature` → `TemporalBoundary` → `CensusTIGERBoundary` hierarchy replacing `CensusBoundary`
  - `TemporalLinearFeature` + `TemporalPointFeature` abstract bases for roads/addresses
  - 25+ new models: political districts, GADM administrative boundaries, education boundaries, federal boundaries, intersections, crosswalks
  - 50+ geometry columns across 34 tables in initial migration (`0001_initial.py`)
  - Full Pydantic schema layer (`geo/schemas/`) with GDF↔Schema↔ORM converters
- Updated managers, serializers, and services for v3 field renames
- CBSA, UrbanArea, and intersection models
- Template architecture problem design doc
- Sphinx `conf.py` files added to release manager version tracking

### Changed
- Version bump 2.2.0 → 3.0.0 (breaking: model renames and field changes)
- CI updated to install GDAL/GEOS/PROJ for GeoDjango test jobs

## [2.0.0] - 2026-02-23

### Added
- **Person/Actor architecture** — unified domain model for people across political, business, and nonprofit contexts, with Hydra config integration, JSON/CSV/Parquet export, and deprecation shims for legacy code
- **Geographic reconciliation** — canonical `CANONICAL_GEOGRAPHIC_LEVELS` (20 entries), `resolve_geographic_level()` alias resolver, `GeographyLevel` enum with `_missing_()`, 75 tests
- **Census API client** — `CensusDataIntelligence` with retry/fallback, boundary type catalog, and state FIPS lookup
- **GeoDjango integration** — spatial data utilities for choropleth and bivariate choropleth map generation
- **OAuth2 1Password credential wiring** — `get_google_oauth_from_1password()` for GA4 reporting, with service-account-first fallback to OAuth2
- **GA4 multi-client reporter** — real Google Analytics 4 data fetching via `fetch_real_ga4_data()` with cached OAuth2 tokens
- **Choropleth library** — heatmap dispatcher, bivariate choropleth serialization, Folium attribution fixes
- **Credential manager** — 1Password integration for secure credential retrieval across notebooks
- **Release manager** — consolidated `scripts/release_manager.py` with PyPI upload, twine validation, dry-run, git tagging, and changelog extraction
- **Boundary type catalog** — comprehensive reference for Census geographic boundary types
- **Census data intelligence** — smart data retrieval with automatic variable resolution
- **17 Jupyter notebooks** — NB01 through NB17 covering data science workflows, spatial analysis, GA4 reporting, and more
- **724 tests** — comprehensive test suite covering unit, E2E, and pipeline/environment tests

### Changed
- Python version floor raised to **3.11** (from 3.9)
- Structured logging across 32 modules via `siege_utilities.core.logging`
- Dynamic package discovery in `setup.py` and `pyproject.toml`
- CI/CD pipeline: UV-based installs, Java 17 for Spark, branch pattern expansion, twine validation in build job
- Branch naming convention updated: developer-prefixed (`dheerajchand/<feature>`), release branches accept `v` prefix and `-rc.N` suffixes

### Fixed
- Census API retry fallback for intermittent 500 errors
- Bivariate choropleth serialization for GeoJSON export
- Folium map attribution rendering in notebook environments
- Heatmap dispatcher type resolution for custom color schemes
- NB10 SecurityError with pickle deserialization
- NB16 JAVA_HOME detection for PySpark sessions

### Deprecated
- `siege_utilities.hygiene.pypi_release` — all public functions emit `DeprecationWarning`, use `scripts/release_manager.py` instead

### Removed
- 20 unvalidated test files from early restoration (preserved in git history)
- Stale merge artifacts from initial branch setup

## [1.1.0] - 2024-12-15

### Added
- Hygiene module with docstring generation and PyPI release utilities
- Git workflow utilities for branch validation and commit conventions
- Core logging module with structured output

### Changed
- Package structure reorganized into core/, git/, hygiene/ submodules

## [1.0.0] - 2024-08-01

### Added
- Initial release of siege_utilities
- Spatial data processing functions
- Multi-client reporting framework
- Basic choropleth generation
- Package configuration with setup.py and pyproject.toml

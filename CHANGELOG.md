# Changelog

All notable changes to siege_utilities will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

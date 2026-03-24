# Changelog

All notable changes to siege_utilities will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [3.12.1] - 2026-03-22

### Fixed
- **Missing data exports** (su#328) — `data/__init__.py` missing 7 exports from `redistricting_data_hub`.
- **Name collisions** (su#329) — top-level `__init__.py` had two name collisions (`get_dataset_info`, `diagnose_environment`).
- **extras_require sync** (su#330) — `setup.py` extras out of sync with `pyproject.toml`.
- **Bare except clauses** (su#331) — replaced 19 bare `except:` with `except Exception:` across 7 files.
- **CONTRIBUTING.md test count** (su#332) — updated from 1884 to 3058.
- **CI contract allowlist** — updated for changed top-level API signatures.
- **geo-no-gdal CI lane** — updated ignore list for Django/Google-dependent test files.
- **F401/F841 lint violations** — cleaned up unused imports and variables across source and test files.

## [3.11.0] - 2026-03-22

### Added
- **Enterprise onboarding notebooks** — NB21 for branded PPT/PDF generation using `ChartGenerator` and `ClientBrandingManager`.
- **Commit-to-issue linkage script** — `scripts/link_commits_to_issues.py` for retroactive GitHub issue traceability.

## [3.10.0] - 2026-03-11

### Added
- **Vector chart export** — `ChartGenerator.save_figure_as_vector()` for SVG/EPS/PDF output.
  All 7 GA report chart functions gained `vector_export_path` parameter; `generate_ga_report_pdf()`
  gained `vector_export_dir` for batch SVG export (designer handoff for InDesign/Illustrator).
- **Period-over-period comparison** (su#304) — `create_period_comparison_chart()` overlays
  current vs prior period daily sessions with fill_between shading and change annotation.
  Prior daily data added to both `generate_sample_ga_data()` and `fetch_real_ga4_data()`.
- **Report cosmetic enhancements** (su#305) — GA term definitions footnote system after KPI
  and traffic tables, cover page logo support (`client_logo_path`/`company_logo_path`),
  dynamic section numbering across all report sections.
- **Raster chart export** — `generate_ga_report_pdf()` gained `raster_export_dir` parameter
  to save high-resolution PNG copies (300 DPI) of all 8 charts for presentations and web use.
- **Design kit export** — `export_design_kit()` produces a complete InDesign handoff package:
  SVG vector charts, PNG raster charts, CSV data tables, report narrative markdown, and
  metadata YAML with KPIs and file inventory.
- **SVG logo support** — Cover page logo auto-converts SVG to PNG via `cairosvg` for
  ReportLab compatibility (graceful fallback if cairosvg not installed).

### Fixed
- **GA4 API response parsing** (su#302, PR #299) — `dimension_headers`/`metric_headers`
  now read from the Response object (not Row objects). Metric columns coerced to numeric
  via `pd.to_numeric()` to fix `nlargest`/aggregation on string-typed values.

### Tests
- **GA4 connector tests** (PR #301) — 7 unit tests covering response parsing, numeric
  coercion, empty responses, dimensions-only, metrics-only, and unauthenticated state.

## [3.9.1] - 2026-03-10

### Fixed
- **Credential hygiene** — `.gitignore` blocks `*credentials*.json`, `*service_account*.json`,
  `*token*.json`, `*client_secret*.json`, `*.pem` from accidental commits.
- **Hardcoded credentials removed** — `database_connections.yaml` now uses `CHANGE_ME` placeholders.
- **Name collision fix** — `load_client_profile`/`save_client_profile`/`list_client_profiles`
  rename shims in `__init__.py` to avoid shadowing.
- **`get_download_directory()` signature** — fixed call in `files/__init__.py` and
  `reporting/__init__.py` to pass `username` arg, added `client_code` path handling.
- **`release_manager.py`** — now tracks `docs/source/conf_fast.py` version.
- **Geocoding log noise** — demoted `log_warning` to `log_debug` in `use_nominatim_geocoder`.
- **`get_available_survey_years`** — added alias in `geo/timeseries` for clarity
  (`get_available_years` still works).

## [3.9.0] - 2026-03-10

### Added
- **1Password integration for Google Workspace** — `GoogleWorkspaceClient.from_1password()`
  auto-detects OAuth client secret vs service account key from 1Password Document items.
  `get_google_oauth_document_from_1password()` in credential_manager.
- **URL helpers** — `GoogleWorkspaceClient.spreadsheet_url()`, `document_url()`,
  `presentation_url()`, `file_url()` static methods. Create functions now log live URLs.
- **folder_id support** — `create_spreadsheet()`, `create_document()`, `create_presentation()`
  accept `folder_id` to place files in a specific Drive folder at creation time.
- **Auth script** — `scripts/google_workspace_auth.py` with `--mode`, `--item`, `--vault`,
  `--account` CLI options. Supports both OAuth (browser) and service account (headless) modes.

### Fixed
- **Registry register() self-default bug** — re-registering an account with `is_default=True`
  no longer clears its own default flag.
- **from_service_account() null crash** — raises `ValueError` instead of `AttributeError`
  when 1Password returns no data.
- **credential_manager error logging** — `op` stderr now surfaced in error messages.

## [3.8.4] - 2026-03-09

### Added
- **Google Workspace write APIs** (su#289) — `GoogleWorkspaceClient` base client with
  OAuth2 and service account auth. Module-level functions for Sheets (`create_spreadsheet`,
  `write_dataframe`, `read_dataframe`), Slides (`create_presentation`, `add_blank_slide`,
  `create_textbox`), and Docs (`create_document`, `insert_paragraph`, `insert_table`,
  `replace_text`). Drive utilities (`copy_file`, `share_file`, `move_to_folder`).
- **Multi-Google-account management** (su#290) — `GoogleAccount` model, `GoogleAccountRegistry`
  with JSON persistence and default selection, `Person.google_accounts` integration,
  `GoogleWorkspaceClient.from_account()` / `from_registry()` factory methods,
  `migrate_single_account()` utility.
- **Tiered geo extras** (su#275) — `[geo-lite]` tier (shapely, pyproj, geopy — no GDAL),
  import guards on 5 modules, `geo_capabilities()` runtime detection function.
  `[geo]` and `[geodjango]` tiers preserved. Managed environments docs (Databricks, Colab, SageMaker).
- **IsochroneResult Django model** + `IsochroneComputeService` + migration 0004 (su#287).
- **Isochrone quality rewrite** (su#268) — Domain exceptions (`IsochroneError`,
  `IsochroneNetworkError`, `IsochroneProviderError`), TypedDict result types, retry logic,
  method dispatch, configurable CRS via `get_default_crs()`/`set_default_crs()`.
- **CRS parameter** on 19 spatial-returning functions across `spatial_data`, `spatial_transformations`,
  `temporal/query`, `interpolation/areal`, `schemas/converters`, `nces_download`, `boundary_manager`.
- **Python version support policy** doc and CI for Python 3.13 (su#274).
- **Convergence diagram** chart type in reporting module.
- **Notebook NB18** — Google Workspace demo using elect.info onboarding content.
- **Sphinx docs** — `google_workspace.rst`, updated `geo.rst` with tiered extras and isochrones.

### Changed
- **License model update (effective March 6, 2026)** — moved from MIT to a dual-license model:
  - AGPL-3.0-only for open-source use
  - Commercial license path for proprietary/commercial use by separate agreement
  - Attribution required in both license paths
- **Raised dependency floors** — pandas>=2.0, numpy>=1.24, scipy>=1.11, shapely>=2.0.0,
  geopandas uncapped (removed <1.0 cap). Python floor: 3.11.
- **Version sync** via `importlib.metadata` — single source of truth in pyproject.toml.

## [3.2.0] - 2026-03-01

### Changed
- **Lazy imports** — `import siege_utilities` is now lazy-loaded via PEP 562 `__getattr__`. Import time reduced from ~29s to ~0.02s. All public API names remain accessible via `from siege_utilities import X` (su#183)
- **Optional dependencies** — Core install (`pip install siege-utilities`) now pulls only 4 packages: pyyaml, requests, tqdm, pydantic. All heavy packages (geopandas, matplotlib, pyspark, etc.) moved to optional extras. Use `pip install siege-utilities[all]` for previous behavior (su#181, su#182)
- All subsystem `__init__.py` files converted from eager imports to lazy `__getattr__` registries: distributed, core, geo, reporting, analytics, testing
- `release_manager.py` tracks 5 version locations (removed hardcoded `get_package_info` version, now uses `__version__` dynamically)

### Added
- **New dependency extras**: `data`, `config-extras`, `web`, `database` (joins existing `geo`, `reporting`, `analytics`, `distributed`, `geodjango`, etc.)
- **CI lanes**: `test-core` (core-only install), `test-geo-no-gdal` (geo without GDAL system libs) (su#184)
- **Pytest markers**: `core`, `geo`, `requires_gdal`, `requires_spark`, `integration`
- **`check_ci_status()`** in `release_manager.py` — queries GitHub Actions before release
- **`tests/test_backward_compat.py`** — 202-test regression gate verifying all critical names remain importable

### Migration guide
- `pip install siege-utilities` — only 4 core packages installed
- `pip install siege-utilities[all]` — full install, identical to v3.1.0
- `pip install siege-utilities[geo]` — geo functions only
- `from siege_utilities import X` — works exactly as before (lazy loaded)

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

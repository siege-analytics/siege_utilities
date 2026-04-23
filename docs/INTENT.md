# siege_utilities — Intent

Per-module purpose statements. Source: each module's `__init__.py` docstring, cross-referenced with the first substantive commit that introduced the module. Written as part of **ELE-2416** (audit sub-issue 1/6).

This file is the definitive answer to "what is this module for?" Any future behavior divergence from what's written here should be reconciled either by updating the behavior or by updating this file — not by letting them drift.

## Top-level modules

### `siege_utilities/admin/`

**Purpose:** library administration. Manage the on-disk location of user / client profile directories (where credentials and per-profile settings live) and perform migrations between versions of that layout. Re-exports `profile_manager` functions at package level.

**Status (2026-04-22):** aligned with stated intent. Small surface area.

### `siege_utilities/analytics/`

**Purpose:** external analytics integrations. Connectors for Google Analytics (read), Facebook Business, Snowflake, Data.world, plus Google Workspace write APIs (Sheets, Docs, Slides). Lazy-loaded via PEP 562 `__getattr__` so importing the package doesn't pull every third-party SDK.

**Status:** aligned. Google Slides writer now includes the `create_argument_slide` / `create_report_from_arguments` public API added in PR #392.

### `siege_utilities/conf/`

**Purpose:** foundational settings singleton and hard-coded defaults. Sits under `config/` and is imported by it; callers should prefer `siege_utilities.config.settings` rather than reaching into `conf`.

**Status:** aligned. Intentionally small (`defaults.py` + `__init__.py`).

### `siege_utilities/config/`

**Purpose:** centralized configuration and constants. Re-exports `conf.settings` for discoverability, plus library metadata (`LIBRARY_NAME`, `LIBRARY_VERSION`, …), canonical geographic level names (`CANONICAL_GEOGRAPHIC_LEVELS`), and per-subject constant modules (census, FIPS, database connections, credentials, pydantic models).

**Status:** aligned. **Divergence candidate:** `credential_manager.py` contains 1Password integration that overlaps with `analytics/google_analytics.py::create_ga_connector_from_1password` — intended coupling? Follow-up to confirm.

### `siege_utilities/configs/` (data directory — not a Python package)

**Purpose:** on-disk config files shipped with the library — e.g. default color palettes, client-branding templates. Populated at install time; callers should not import from it, only read files.

**Status:** aligned (no Python, no API surface).

### `siege_utilities/core/`

**Purpose:** foundational utilities that every other module may import. Logging setup (`log_info` / `log_warning` / `log_error` / `log_debug` family), string manipulation, SQL safety helpers. Lazy-loaded.

**Status:** aligned. Dependency root — nothing in core should import from `geo`, `reporting`, `survey`, etc.

### `siege_utilities/data/`

**Purpose:** two concerns bundled: (1) built-in sample datasets for testing and demo; (2) engine-agnostic DataFrame operations that abstract over pandas, DuckDB, Spark, and PostGIS. The Redistricting Data Hub client (`RDHClient`) also lives here.

**Status:** **Divergence candidate 1:** sample data vs. multi-engine DataFrame ops are two distinct concerns that happen to share a directory. Consider splitting as part of ELE-2417 (architecture). **Divergence candidate 2:** RDH is a specific data provider — could arguably live under `geo/` or in its own `providers/` subtree alongside boundary providers.

### `siege_utilities/databricks/`

**Purpose:** Databricks + LakeBase client utilities. Authenticated workspace clients, Spark↔pandas / Spark↔GeoPandas bridges, LakeBase JDBC URL builders, job-run URL construction for Databricks Asset Bundles.

**Status:** aligned. Surface area is the Databricks runtime API — see ELE-2417 for ADR candidate on whether to move this under `distributed/` or keep it separate.

### `siege_utilities/development/`

**Purpose:** developer tooling for understanding the library's own structure — architecture diagram generation, package-structure analysis. Meta, not user-facing.

**Status:** aligned.

### `siege_utilities/distributed/`

**Purpose:** PySpark utilities and HDFS operations. Lazy-loaded; re-exports `pyspark.sql.functions` names (`col`, `lit`, `when`, …) through `spark_utils` so downstream code can `from siege_utilities.distributed import col`.

**Status:** aligned. **Divergence candidate:** `hdfs_legacy/` subdirectory exists in docs but grep the source for whether it's current — follow-up under ELE-2418.

### `siege_utilities/examples/` (demo scripts — not a Python package)

**Purpose:** standalone `.py` scripts illustrating library usage. Not importable.

**Status:** aligned, but ELE-2421 (notebook redistribution) will consolidate these with the `notebooks/` demos.

### `siege_utilities/exceptions.py` (top-level file, not a package)

**Purpose:** unified exception hierarchy. All domain exceptions inherit from `SiegeError` so a caller can catch the whole family with one `except SiegeError:`. Also defines the `OnErrorStrategy` literal and `handle_error(...)` dispatcher — standardizes the `on_error` parameter across functions that expose a "raise / warn / skip" knob.

**Status:** aligned. This is the place future modules should register new domain exceptions.

### `siege_utilities/files/`

**Purpose:** file operations at the path level — directory management, copy/move/delete, remote downloads with retry, file hashing and integrity verification. Everything is promoted to package-level exports for mutual availability across modules.

**Status:** aligned.

### `siege_utilities/geo/`

**Purpose:** geographic utilities. Census data access (TIGER + TIGER PL for VTDs + RDH + GADM), coordinate reference system operations, spatial data manipulation, mapping. Lazy-loaded so pure-Python modules (`census_constants`, `geoid_utils`) remain importable without `geopandas`.

**Status:** aligned — recently reshaped by PRs #386 (TIGER2020PL VTD routing + RDHProvider) and #388 (CensusTIGERProvider refactor). The `BoundaryProvider` ABC pattern is the canonical extension point.

### `siege_utilities/git/`

**Purpose:** programmatic Git operations for siege-internal tooling (release automation, branch analysis). Not meant for end-user Git workflows — that's what `gh` / `git` are for.

**Status:** aligned.

### `siege_utilities/hygiene/`

**Purpose:** package-maintenance tooling. Auto-generate docstrings, automate PyPI releases (version bump, build, twine upload), cleanup of build artifacts, validate package readiness. Supports both `setup.py` and `pyproject.toml` projects.

**Status:** aligned. **Divergence candidate:** `hygiene/README.md` contains `password="password"` example — harmless but will trip secret scanners; replace with `os.environ` pattern as part of ELE-2420.

### `siege_utilities/profiles/` (data directory)

**Purpose:** on-disk default profile fixtures for clients and users. Loaded by `admin/profile_manager.py` at runtime. Not a Python package.

**Status:** aligned.

### `siege_utilities/reporting/`

**Purpose:** the full reporting pipeline — charts (`chart_generator`, typed chart classes), pages (`page_models` with `TableType`, `Argument`, `TitlePage`, `TableOfContentsPage`, `ContentPage`), engines (`bar_engine`, `map_engine`, `stats_engine`, `composite_engine`, `base_engine`), templates (title / toc / content), and output generators (`report_generator` for PDF, `powerpoint_generator` for PPTX). Also hosts the polling-analytics subpackage `reporting/analytics/` that wraps GA / cross-tab tooling.

**Status:** **Divergence candidate 1:** `reporting/analytics/polling_analyzer.py` is analytics code living inside a reporting namespace — name suggests it should be under `siege_utilities.analytics/` or a new `analytics/polling/` module. Surface in ELE-2417. **Divergence candidate 2:** `reporting/engines/*` — 5+ engine files with suspected copy-paste duplication per PR-386 thread pattern. Flag for ELE-2420 shared-core rewrite. **Divergence candidate 3:** `reporting/pages/page_models.py` now holds `Argument` and `TableType` — both used across `survey/` and `analytics/google_slides.py`. Consider promoting to a neutral location (maybe `core/models.py` or a new `models/` subpackage).

### `siege_utilities/runtime.py` (top-level file)

**Purpose:** runtime compatibility guard for Databricks notebooks. Idempotent bootstrap — verifies (and, when possible, repairs) the Python environment before heavy siege_utilities submodules are imported. Deliberately stdlib-only so it can always be imported even when `pydantic` or other deps are in a broken state.

**Status:** aligned. Critical stability surface; do not add third-party imports here.

### `siege_utilities/survey/`

**Purpose:** survey/crosstab report engine. Quantipy-inspired `Stack → Cluster → Chain → View` hierarchy, built fresh on pandas + weightipy for Python 3.12. Provides `build_chain`, `chain_to_argument`, `stack_to_arguments`, significance tests (`column_proportion_test`, `chi_square_flag`), and RIM weighting (`apply_rim_weights`). Optional install: `pip install siege-utilities[survey]`.

**Status:** aligned — reshaped by PR #391. **Divergence candidate:** `Chain.to_argument()` method duplicates `survey.render.chain_to_argument(chain, ...)` — both are entry points to the same pipeline. Pick one canonical and delegate from the other. Covered by ELE-2417 ADR.

### `siege_utilities/testing/`

**Purpose:** helpers for the library's own tests — environment management (set/restore env vars, isolate working directories) and a pytest-compatible runner. Lazy-loaded.

**Status:** aligned.

## Divergences catalog (summary)

For each divergence called out above, a follow-up issue will be filed under ELE-2415:

| # | Module | Divergence | Proposed resolution |
|---|---|---|---|
| D1 | `config/` | `credential_manager.py` 1Password logic overlaps with `analytics/google_analytics` | Confirm ownership; consolidate to one | 
| D2 | `data/` | Sample data + multi-engine ops in one directory | Split under ELE-2417 |
| D3 | `data/` | `RDHClient` is a specific data provider | Consider moving to `geo/providers/` or new `providers/` subtree |
| D4 | `distributed/` | `hdfs_legacy/` — current or stale? | Audit in ELE-2418 |
| D5 | `hygiene/README.md` | Contains `password="password"` example | Replace with `os.environ` pattern |
| D6 | `reporting/` | `reporting/analytics/polling_analyzer.py` is analytics in a reporting namespace | ELE-2417 ADR |
| D7 | `reporting/engines/` | Suspected copy-paste across 5+ engine files | ELE-2420 shared-core rewrite |
| D8 | `reporting/pages/page_models.py` | Holds `Argument` / `TableType` used by `survey/` and `analytics/` | Promote to neutral location |
| D9 | `survey/` | `Chain.to_argument()` + `survey.render.chain_to_argument()` duplicate entry points | ELE-2417 ADR (pipeline ownership) |

## Next

- ELE-2417 consumes this file as input for architecture decisions
- ELE-2418 and ELE-2420 will pick up the divergences they're best suited to resolve
- Keep this file current — any future PR that adds a module must update this file, and any PR that changes a module's purpose must reconcile

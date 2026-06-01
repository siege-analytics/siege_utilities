# siege_utilities — Intent

**Goal:** one-line purpose for every top-level module. The definitive answer to "what is this for?" Divergences between this file and actual behavior should be reconciled by changing one or the other — not left to drift.

**Guiding principles:** This file is downstream of `CLAUDE.md`, which codifies the architectural decisions and tactical principles for the library. The key axioms: geo is the gravitational center; the engine abstraction serves many scales; domain packages are primitives not applications; temporal awareness is first-class; errors are not data (SU-1 through SU-4). See `CLAUDE.md` for the full set.

**Scope:** Snapshot date: 2026-04-22, updated 2026-05-31.

**Source:** each module's `__init__.py` docstring, cross-referenced with the first substantive commit that introduced the module.

---

## Module table

Status column: **Aligned** (behavior matches intent), **Divergent** (discrepancy with a planned resolution), **Meta** (non-user-facing: docs, examples, dev tools).

| Module | Purpose | Status | Planned change |
|---|---|---|---|
| `admin/` | Manage profile-directory layout + migrations | Aligned | — |
| `analytics/` | Third-party connectors (GA, Facebook, Snowflake, Data.world, Google Workspace) | Aligned | D1 wrapper rename |
| `conf/` | Foundational settings singleton + hard-coded defaults | Aligned | — |
| `config/` | Re-exports `conf.settings` + canonical constants (census, FIPS, credentials, pydantic models) | Aligned | — |
| `configs/` | On-disk config data (palettes, branding templates); not a Python package | Aligned | — |
| `core/` | Foundational utilities (logging, string, SQL safety); dependency root | Aligned | — |
| `data/` | Sample datasets + engine-agnostic DataFrame ops + RDH client | **Divergent** | Aggressive split by nature; RDH moves to `geo/providers/` |
| `databricks/` | Databricks + LakeBase clients, Spark-to-pandas bridges (Azure lacks GDAL — separation is load-bearing) | Aligned | — |
| `development/` | Meta tooling (architecture diagrams, structure analysis) | Meta | — |
| `distributed/` | PySpark + HDFS utilities; re-exports `pyspark.sql.functions` names | Aligned | — |
| `economic/` | Economic data utilities (BLS, FRED, industry classifications) | Aligned | — |
| `education/` | Education data access (NCES downloads, school district boundaries) | Aligned | — |
| `engines/` | Engine-agnostic DataFrame abstraction (pandas, DuckDB, Spark, PostGIS) | Aligned | — |
| `examples/` | Standalone demo `.py` scripts (held to library standard — SU-3) | Meta | Consolidating with `notebooks/` |
| `exceptions.py` | Unified exception hierarchy (`SiegeError`); `OnErrorStrategy`; `handle_error()` | Aligned | — |
| `files/` | Path manipulation, file operations, remote download, hashing | Aligned | — |
| `geo/` | Geospatial data access, boundary providers, geocoding, CRS, Django models | Aligned | External spatial sources consolidate under `geo/providers/` |
| `git/` | Branch/commit helpers | Aligned | — |
| `hygiene/` | Maintenance tooling (docstring generation, PyPI release flow) | Meta | — |
| `identifiers/` | Entity identification, matching, and fuzzy resolution at seams | Aligned | — |
| `political/` | Political data utilities (DDL, entities, redistricting plans, effective dates) | Aligned | — |
| `reference/` | Reference data lookups (geographic levels, FIPS, canonical name tables) | Aligned | — |
| `reporting/` | PDF/PowerPoint generation, chart types, client branding, page templates | **Divergent** | `reporting/analytics/` deleted; `analytics_reports.py` promoted; new `wave_charts.py` |
| `runtime.py` | Runtime environment detection + guards | Aligned | — |
| `schema/` | Schema definitions and validation (DDL generation, type contracts) | Aligned | — |
| `survey/` | Survey pipeline (Chain, weights, render, significance) | **Divergent** | `Chain.to_argument()` removed; new `Wave`/`WaveSet` subsystem |
| `testing/` | Test-only fixtures and helpers | Meta | — |
| `trino/` | Trino connector for federated queries across data sources | Aligned | — |

---

## Divergence catalog

All divergences carry a planned resolution.

| ID | Where | Decision | Target |
|---|---|---|---|
| D1 | `create_ga_connector_from_1password` wrapper name | Rename — auth-mechanism shouldn't leak into analytics API surface | — |
| D2 | `data/` bundles multiple natures | Aggressive split: `data/statistics/`, `reference/`, top-level `engines/` | — |
| D3 | External spatial sources scattered across `geo/` | Consolidate under `geo/providers/` (structural moves only; interface unification is a later epic) | — |
| D4 | `databricks/` vs `distributed/` | Keep separate. Azure Databricks lacks Sedona + C-libs — separation is load-bearing | — |
| D7 | `reporting/analytics/polling_analyzer` | Deprecate `PollingAnalyzer`; extract longitudinal/change-detection to `data/statistics/`; delete `reporting/analytics/` subdirectory; add survey `Wave`/`WaveSet` | — |
| D8 | `Chain.to_argument()` method vs `chain_to_argument()` function | Delete the method; function is sole entry point. Chain stays pure data | — |
| D9 | `chart_generator` / `map_generator` kwargs ignored on `chain_to_argument` | Honor them (minimal ceremony — duck type, no Protocol yet). Drop from `ChartTypeRegistry.create_chart` (internal dispatch layer) | — |

*Closed, no action:*
- **D5** (`hdfs_legacy/`) — file was already removed; only stale `.pyc` remained.
- **D6** (`geo/` silent-swallow sites) — not architectural; operational debt.

---

## How to use this file

- **Adding a new module?** Add a row. State purpose in one sentence. If you can't, the module's scope isn't clear enough yet.
- **Behavior changed in ways that contradict a row?** Update the row, or open a ticket to restore intent.
- **Found a new divergence?** Add a `Dn` entry to the catalog and link it to a follow-up issue.

See also: [ARCHITECTURE.md](ARCHITECTURE.md) · [CLAUDE.md](../CLAUDE.md) · [FAILURE_MODES.md](FAILURE_MODES.md) · [ADRs](adr/)

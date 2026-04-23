# siege_utilities — Intent

**Goal:** one-line purpose for every top-level module. The definitive answer to "what is this for?" Divergences between this file and actual behavior should be reconciled by changing one or the other — not left to drift.

**Scope:** ELE-2416 (audit sub-issue 1/6). Snapshot date: 2026-04-22.

**Source:** each module's `__init__.py` docstring, cross-referenced with the first substantive commit that introduced the module.

---

## Module table

Status column: **Aligned** (behavior matches intent), **Divergent** (discrepancy with a planned resolution), **Meta** (non-user-facing: docs, examples, dev tools).

| Module | Purpose | Status | Planned change |
|---|---|---|---|
| `admin/` | Manage profile-directory layout + migrations | Aligned | — |
| `analytics/` | Third-party connectors (GA, Facebook, Snowflake, Data.world, Google Workspace) | Aligned | D1 wrapper rename (ELE-2442) |
| `conf/` | Foundational settings singleton + hard-coded defaults | Aligned | — |
| `config/` | Re-exports `conf.settings` + canonical constants (census, FIPS, credentials, pydantic models) | Aligned | — |
| `configs/` | On-disk config data (palettes, branding templates); not a Python package | Aligned | — |
| `core/` | Foundational utilities (logging, string, SQL safety); dependency root | Aligned | — |
| `data/` | Sample datasets + engine-agnostic DataFrame ops + RDH client | **Divergent** | Aggressive split by nature (ELE-2437); RDH moves to `geo/providers/` (ELE-2438) |
| `databricks/` | Databricks + LakeBase clients, Spark↔pandas bridges | Aligned | Motivation docstring added (ELE-2442) — kept separate from `distributed/` because Azure Databricks lacks Sedona + C-libs |
| `development/` | Meta tooling (architecture diagrams, structure analysis) | Meta | — |
| `distributed/` | PySpark + HDFS utilities; re-exports `pyspark.sql.functions` names | Aligned | — |
| `examples/` | Standalone demo `.py` scripts | Meta | Consolidating with `notebooks/` in ELE-2421 |
| `exceptions.py` | Unified exception hierarchy (`SiegeError`); `OnErrorStrategy`; `handle_error()` | Aligned | — |
| `files/` | Path manipulation, file operations, remote download, hashing | Aligned | — |
| `geo/` | Geospatial data access, boundary providers, geocoding, CRS, Django models | Aligned | External spatial sources consolidate under `geo/providers/` (ELE-2438); silent-swallow sweep under ELE-2420 |
| `git/` | Branch/commit helpers | Aligned | — |
| `hygiene/` | Maintenance tooling (docstring generation, PyPI release flow) | Meta | — |
| `reporting/` | PDF/PowerPoint generation, chart types, client branding, page templates | **Divergent** | `reporting/analytics/` subdirectory deleted (ELE-2439); `analytics_reports.py` promoted one level; new `wave_charts.py` lands with ELE-2440 |
| `runtime.py` | Runtime environment detection + guards | Aligned | — |
| `survey/` | Survey pipeline (Chain, weights, render, significance) | **Divergent** | `Chain.to_argument()` method removed (ELE-2441); new `Wave`/`WaveSet` subsystem (ELE-2440) |
| `testing/` | Test-only fixtures and helpers | Meta | — |

---

## Divergence catalog

All divergences carry a planned resolution and a target sub-issue.

| ID | Where | Decision | Target |
|---|---|---|---|
| D1 | `create_ga_connector_from_1password` wrapper name | Rename — auth-mechanism shouldn't leak into analytics API surface | ELE-2442 |
| D2 | `data/` bundles multiple natures | Aggressive split: `data/statistics/`, `reference/`, top-level `engines/` | ELE-2437 |
| D3 | External spatial sources scattered across `geo/` | Consolidate under `geo/providers/` (structural moves only; interface unification is a later epic) | ELE-2438 |
| D4 | `databricks/` vs `distributed/` | Keep separate. Document in `__init__.py` that Azure Databricks lacks Sedona + C-libs — separation is load-bearing | ELE-2442 |
| D7 | `reporting/analytics/polling_analyzer` | Deprecate `PollingAnalyzer`; extract longitudinal/change-detection to `data/statistics/`; delete `reporting/analytics/` subdirectory; add survey `Wave`/`WaveSet` | ELE-2439 + ELE-2440 |
| D8 | `Chain.to_argument()` method vs `chain_to_argument()` function | Delete the method; function is sole entry point. Chain stays pure data | ELE-2441 |
| D9 | `chart_generator` / `map_generator` kwargs ignored on `chain_to_argument` | Honor them (minimal ceremony — duck type, no Protocol yet). Drop from `ChartTypeRegistry.create_chart` (internal dispatch layer) | ELE-2441 |

*Closed, no action:*
- **D5** (`hdfs_legacy/`) — file was already removed; only stale `.pyc` remained.
- **D6** (`geo/` silent-swallow sites) — not architectural; operational debt tracked under ELE-2420.

---

## How to use this file

- **Adding a new module?** Add a row. State purpose in one sentence. If you can't, the module's scope isn't clear enough yet.
- **Behavior changed in ways that contradict a row?** Update the row, or open a ticket to restore intent.
- **Found a new divergence?** Add a `Dn` entry to the catalog and link it to a follow-up issue.

See also: [ARCHITECTURE.md](ARCHITECTURE.md) · [FAILURE_MODES.md](FAILURE_MODES.md) · [ADRs](adr/)

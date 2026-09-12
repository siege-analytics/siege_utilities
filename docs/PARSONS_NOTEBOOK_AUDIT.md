# Notebook track audit (Phase 6 of Parsons integration epic)

**Purpose:** produce the empirical grounding + sub-ticket queue for the notebook-rework track (Phase 6) of the Parsons integration epic. This audit corrects three claims from the scoping ticket that turned out to be over/under-stated once counted against actual state.

**Closes N-0 of parent epic:** [#1154 (scoping ticket)](https://github.com/siege-analytics/siege_utilities/issues/1154), Phase 6 of [#1148 (parent epic)](https://github.com/siege-analytics/siege_utilities/issues/1148).

## Inventory

39 notebook files across `notebooks/`. Full per-file inventory:

| Path | Code cells | Executed | In `RE_WRITTEN` | In README canonical | Archive |
|---|---:|---:|:---:|:---:|:---:|
| `analytics/01_connectors.ipynb` | 5 | 5 | ✅ | ✅ | |
| `analytics/02_ga_end_to_end.ipynb` | 4 | 4 | ✅ | ✅ | |
| `analytics/03_social_media_analytics.ipynb` | 14 | 0 | ❌ | ❌ | |
| `analytics/04_crm_pipeline.ipynb` | 10 | 0 | ❌ | ❌ | |
| `analytics/05_crm_sales_reports.ipynb` | 8 | 0 | ❌ | ❌ | |
| `config/credential_management.ipynb` | 3 | 1 | ❌ | ❌ | |
| `economic/economic_data_irs_bls.ipynb` | 3 | 3 | ❌ | ❌ | |
| `engines/01_multi_engine_dataframes.ipynb` | 5 | 5 | ✅ | ✅ | |
| `engines/02_distributed_spark.ipynb` | 1 | 1 | ✅ | ✅ | |
| `engines/03_databricks_geo.ipynb` | 3 | 3 | ✅ | ✅ | |
| `engines/04_statistics_primitives.ipynb` | 11 | 11 | ✅ | ✅ | |
| `foundations/01_configuration.ipynb` | 5 | 0 | ✅ | ✅ | |
| `foundations/02_profiles_branding.ipynb` | 5 | 5 | ✅ | ✅ | |
| `foundations/entity_identification.ipynb` | 3 | 3 | ❌ | ❌ | |
| `foundations/file_operations_and_security.ipynb` | 4 | 4 | ❌ | ❌ | |
| `git/repo_analysis.ipynb` | 4 | 0 | ❌ | ❌ | |
| `reports/01_charts_and_pdf.ipynb` | 4 | 4 | ✅ | ✅ | |
| `reports/02_slides_pptx_and_google.ipynb` | 3 | 3 | ✅ | ✅ | |
| `reports/03_polling_survey_analysis.ipynb` | 8 | 8 | ✅ | ✅ | |
| `reports/04_survey_full_showcase.ipynb` | 12 | 12 | ✅ | ❌ | |
| `spatial/01_boundaries.ipynb` | 6 | 0 | ✅ | ✅ | |
| `spatial/02_geocoding.ipynb` | 5 | 0 | ✅ | ✅ | |
| `spatial/03_choropleth_maps.ipynb` | 6 | 3 | ✅ | ✅ | |
| `spatial/04_redistricting.ipynb` | 4 | 4 | ✅ | ✅ | |
| `spatial/05_multi_source_joins.ipynb` | 5 | 5 | ✅ | ✅ | |
| `spatial/06_geodjango.ipynb` | 0 | 0 | ✅ | ✅ | |
| `spatial/07_natural_language_to_geometry.ipynb` | 5 | 0 | ❌ | ❌ | |
| `archive/*` (12 files) | 178 | 0 | ❌ | ❌ | ✅ |

**Totals:** 39 notebooks, 324 code cells, 84 executed (26% overall).
**Live only** (excluding 12 `archive/`): 27 notebooks, 146 code cells, 84 executed (**57%**).
**Live and in `RE_WRITTEN`** (18 notebooks): 92 cells, 73 executed (**79%**).
**Live but NOT in `RE_WRITTEN`** (9 notebooks): 54 cells, 11 executed (**20%**).

## Falsification of N-0 scoping claims

The scoping ticket [#1154](https://github.com/siege-analytics/siege_utilities/issues/1154) asserted four claims. Empirical audit result per claim:

### Claim A — `tests/test_notebooks.py` executes zero notebooks in CI

**PARTIALLY FALSIFIED but the underlying diagnosis holds.** Re-reading `tests/test_notebooks.py`:

- `_notebook_path(nb_num)` uses `NOTEBOOKS_DIR.glob(f"{nb_num:02d}_*.ipynb")` — this globs the root `notebooks/` directory, not subdirectories.
- Actual layout is subdirectory-based (`foundations/`, `spatial/`, etc.). Zero files match `notebooks/{NN}_*.ipynb` at the root.
- Therefore `pytest.skip("Notebook NN not found")` fires for every parametrized `nb_num`.

**But** the file was authored for the *pre-migration* flat layout (before `ELE-2456` reorganized into subdirs). It is not broken by ignorance; it is stale by omission-of-migration. The papermill execution surface is inert.

**Verdict:** the underlying claim ("zero notebooks executed in CI") stands. The finer point is that the test file's design assumed a layout that no longer exists — this is a migration debt from `ELE-2456`, not a bug in test authoring. N-1 fixes it.

### Claim B — ≥14 of 24 canonical notebooks are outside `RE_WRITTEN`

**FALSIFIED.** README canonical count is 17 (not 24), and **all 17 are in `RE_WRITTEN`**. The audit-scoping ticket overestimated both the canonical population and the coverage gap.

**Corrected finding:** the real gap is not in the canonicals — it's in the 9 non-canonical live notebooks that are neither documented in the README nor covered by hygiene. Those are:

- `analytics/03_social_media_analytics.ipynb`, `04_crm_pipeline.ipynb`, `05_crm_sales_reports.ipynb`
- `config/credential_management.ipynb`
- `economic/economic_data_irs_bls.ipynb`
- `foundations/entity_identification.ipynb`, `file_operations_and_security.ipynb`
- `git/repo_analysis.ipynb`
- `spatial/07_natural_language_to_geometry.ipynb`

These 9 notebooks were added after the `ELE-2456` migration and are outside the hygiene contract. Six of them are unexecuted; three are executed but with no CI enforcement.

### Claim C — Executed-to-total cell ratio ≤ 30%

**TRUE (26%) for the full tree, but the framing is misleading.** Once we exclude the 12 `archive/` notebooks (which are explicitly out-of-CI by design), the live-notebook execution ratio is 57%. The `RE_WRITTEN` cohort's ratio is 79%.

**Corrected finding:** the "26% executed" number is dominated by the archive. Actionable execution debt lives in three places:

1. Two `RE_WRITTEN` notebooks with 0 executed cells: `foundations/01_configuration.ipynb` (5 cells) and `spatial/01_boundaries.ipynb` (6 cells), plus `spatial/02_geocoding.ipynb` (5 cells).
2. Six of the 9 non-canonical live notebooks (see Claim B).
3. `spatial/06_geodjango.ipynb` has **zero code cells** — it's a shell.

### Claim D — Parsons's 6 priority connectors map primarily to ElectInfo, not Masai Interactive

**CONFIRMED.** All 6 (VAN, ActionKit, Mobilize America, ActBlue, EveryAction, Redshift) are campaign / advocacy / civic-tech tools serving the electoral / progressive-org constituency documented as **ElectInfo's** persona in `notebooks/README.md`. None is a web / social analytics tool (Masai Interactive's territory).

**Placement decision:** Parsons notebooks land in a **new `notebooks/advocacy/` subdirectory** rather than extending `analytics/`. Rationale:

- `analytics/` in the current layout is web / social analytics (Google Analytics, Facebook, Snowflake, data.world) per README's group table. Mixing VAN / ActionKit / Mobilize there dilutes the group's purpose.
- Parsons's own docs group these connectors as "advocacy tools," which matches the persona split.
- New subdirectory lets us add a fresh README section rather than editing the existing analytics table.
- Two-firm narrative: `advocacy/` notebooks star ElectInfo end-to-end (VAN pull → adapter → siege reporting under `elect_info` branding).

## `tests/test_notebooks.py` stale-glob diagnosis

Current test file structure:

```python
NOTEBOOKS_DIR = Path(__file__).parent.parent / "notebooks"

# Numbered dependency groups referencing the old flat layout
PURE_PYTHON = [1, 2, 3, 6, 8, 11, 12, 17, 21, 22, 23, 24, 27]
GEO_NOTEBOOKS = [4, 5, 7, 25, 26]
DJANGO_NOTEBOOKS = [13, 15]
ANALYTICS_NOTEBOOKS = [9, 14, 18]
SPARK_NOTEBOOKS = [16]
CREDENTIAL_NOTEBOOKS = [10]
EXTERNAL_DOWNLOAD_NOTEBOOKS = [19, 20]

def _notebook_path(nb_num: int) -> Path:
    for p in sorted(NOTEBOOKS_DIR.glob(f"{nb_num:02d}_*.ipynb")):
        return p
    pytest.skip(f"Notebook {nb_num:02d} not found")
```

The dependency groups reference a numbered flat layout that predates the subdirectory reorganization. Notebooks 1-27 don't exist as `notebooks/{NN}_*.ipynb` anymore — they exist as `notebooks/{group}/{NN}_*.ipynb`.

**Proposed fix in N-1:**

Replace numbered-integer groups with subdirectory-path groups. Rewrite `_notebook_path` as `_notebook_paths_in(group_dir: str) -> list[Path]`. Reparametrize each test group on the actual `.ipynb` paths under its directory. Skip cleanly on notebooks that are known to require env-specific fixtures.

Rough shape:

```python
NOTEBOOK_GROUPS = {
    "foundations": ["foundations/01_configuration.ipynb", ...],
    "spatial-pure": ["spatial/01_boundaries.ipynb", "spatial/02_geocoding.ipynb", ...],
    "spatial-gdal": ["spatial/03_choropleth_maps.ipynb", "spatial/04_redistricting.ipynb", ...],
    "spatial-django": ["spatial/06_geodjango.ipynb"],
    "analytics-pure": ["analytics/01_connectors.ipynb"],
    "analytics-integration": ["analytics/02_ga_end_to_end.ipynb", ...],
    "engines-pure": ["engines/01_multi_engine_dataframes.ipynb", "engines/04_statistics_primitives.ipynb"],
    "engines-spark": ["engines/02_distributed_spark.ipynb"],
    "engines-databricks": ["engines/03_databricks_geo.ipynb"],
    "reports": ["reports/01_charts_and_pdf.ipynb", ...],
    "advocacy": ["advocacy/01_parsons_van_quickstart.ipynb", ...],  # populated by N-4..N-9
}
```

## Sub-ticket queue (N-1..N-10)

Provisional filing order after N-0 closes:

- **N-1** Rewrite `tests/test_notebooks.py` to walk subdirectories and drop the numbered-integer group scheme. Prerequisite for every other N-*. **Size: M.**
- **N-2** Backfill or archive the 3 `RE_WRITTEN` notebooks that have 0 executed cells (`foundations/01_configuration.ipynb`, `spatial/01_boundaries.ipynb`, `spatial/02_geocoding.ipynb`, plus `spatial/06_geodjango.ipynb` which is empty). Execute + commit outputs OR mark them as "requires-env" and skip cleanly. **Size: M.**
- **N-3** Decide the fate of the 9 non-canonical live notebooks: for each, either (a) promote to canonical (add to README table + `RE_WRITTEN`), (b) delete, or (c) move to `archive/`. Filed as one ticket producing a decisions doc + a follow-up per notebook. **Size: S.**
- **N-4** Author `advocacy/README.md` + `advocacy/01_parsons_van_quickstart.ipynb` (ElectInfo → VAN → adapter → siege reporting under `elect_info` branding). Canonical demo of the epic. **Size: L.** Depends on P0-3 (adapter spike) + P1-2 (`_adapter.py` shipped).
- **N-5** `advocacy/02_parsons_action_kit.ipynb` (ActionKit end-to-end).
- **N-6** `advocacy/03_parsons_mobilize.ipynb` (Mobilize America event pull → siege reporting).
- **N-7** `advocacy/04_parsons_actblue.ipynb` (ActBlue contribution feed → siege pandas).
- **N-8** `advocacy/05_parsons_everyaction.ipynb` (EveryAction via VAN + `db="EveryAction"`).
- **N-9** `advocacy/06_parsons_redshift.ipynb` (Redshift → siege DataFrameEngine bridge).
- **N-10** Archive-notebook pruning decision: 12 `archive/` notebooks are stale. For each: keep-for-history, or delete. **Non-blocking; can defer.**

## Placement decision

- **New subdirectory:** `notebooks/advocacy/`.
- **README addition:** new group table titled "Campaign / advocacy" pointing at the 6 Parsons quickstart notebooks. Positioned between `analytics/` and `engines/` in the layout, since it's about pulling data (`analytics/`-adjacent) but scales like `engines/` for larger jobs.
- **Two-firm narrative wiring:** all 6 `advocacy/*` notebooks feature **ElectInfo** as the running example (uses `elect_info` branding preset, pulls campaign-adjacent data). Masai Interactive's persona is unchanged.

## Falsification for this audit doc

- Full-tree execution ratio: 84/324 = 26%. Re-audit reproduces this within ±5% or the audit script has drifted.
- README canonical count: 17. Re-scan of `notebooks/README.md` link markdown yields <15 or >20 → tables changed since audit.
- `RE_WRITTEN` allowlist size: 18. Re-count of `tests/test_notebook_hygiene.py` `RE_WRITTEN` list yields ≠18 → migration has advanced or regressed.
- Placement decision (new `advocacy/` group): falsifies if a subsequent reviewer prefers extending `analytics/` over adding a group. Not epic-blocking.

## Blocks

- All Phase 6 sub-tickets (N-1..N-10).
- **Does NOT block** Phase 0-5 progression.
- **Is not itself blocked** by the epic CI-credibility prerequisite (this doc is read-only investigation).

## References

- N-0 scoping ticket: [#1154](https://github.com/siege-analytics/siege_utilities/issues/1154)
- Parent epic: [#1148](https://github.com/siege-analytics/siege_utilities/issues/1148)
- `notebooks/README.md`: two-firm narrative + canonical tables
- `tests/test_notebooks.py`: papermill execution harness (stale)
- `tests/test_notebook_hygiene.py`: hygiene contract + `RE_WRITTEN` allowlist

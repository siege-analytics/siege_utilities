---
ticket: "#1176"
scope: "siege_utilities/__init__.py, tests/test_public_api_surface.py"
---

# Self-Review — #1176 batch 2: promote reporting canonicals

## Assumptions

Working as: Software Engineer
Goal source: #1176 body — "Public API categorization: 283 lazy symbols not in __all__". Batch 2 continues the per-subpackage promotion template established by batch 1 (PR #1207).
Investigate-artifact: TRIVIAL
Pre-mortem-artifact: TRIVIAL
Hostile-review-artifact: plans/hostile-review-1176-batch2.md
Pre-author-inventory: `scripts/audit_public_api_surface.py --markdown --report` output filtered to `.reporting*` (26 canonicals total across `.reporting`, `.reporting.chart_generator`, `.reporting.chart_types`, `.reporting.analytics.polling_analyzer`).

Assumed:
- Batch 1 (PR #1207) established the explicit `__all__` block and the `_register_lazy` duplicate-registration guard. Batch 2 is additive only: 26 new names appended to the "Promoted canonicals" region.
- All 26 batch-2 names resolve to modules under `siege_utilities.reporting.*` — verified at runtime.
- Unlike batch 1 (single source module), batch 2 spans 4 submodules by design. Test uses `module.startswith("siege_utilities.reporting")` rather than an exact match.

## Peer review

- **writing-code:16 (migration completeness):** N/A — metadata addition, no symbol relocation.
- **writing-releases:1 (BREAKING when public surface changes):** ADDITIVE only. 26 names added, none removed. Not BREAKING.
- **writing-claims:8 (specific counts must cite command):**
  - "26 canonical symbols" — `python scripts/audit_public_api_surface.py --markdown --report 2>&1 | grep -E '\`\.reporting' | awk -F'\`' '{print $2}' | sort -u | wc -l` → 26.
  - "canonical tier drops 121 → 103" — verified pre/post-diff.
  - "`__all__` length: 79 → 105" — runtime-verified via `python -c 'import siege_utilities as su; print(len(su.__all__))'`.
- **writing-tests:1 (tests must fail on revert):** `TestBatch2Promotions` (52 tests, 26 in-all + 26 resolve-check) would go red if any batch-2 name were removed from `__all__` or rebound to a non-reporting module.
- **SU-5 (parse verification):** `python -c "import ast; ast.parse(open('siege_utilities/__init__.py').read())"` → OK.
- **SU-4b (error-path coverage):** The 26 promoted symbols include multiple `create_*` chart-generation functions with documented error paths. Test coverage is inherited from the pre-existing `tests/test_reporting_*` and `tests/test_chart_*` files; batch 2 does not change those behaviours, only their public visibility.

## Lead review

Working as: Tech Lead

Affirmative:
- The template pattern from batch 1 (PR #1207) held up: batch 2 is a pure additive edit with no structural changes to the `__all__` block layout. Future batches can follow the same pattern.
- Cross-module scope handled correctly: batch 2's 4-submodule fan-out required loosening the resolve-check assertion from `== "siege_utilities.geo.spatial_data"` (batch 1) to `startswith("siege_utilities.reporting")`. Explicitly documented in the test's class docstring so future readers know it's intentional, not sloppy.
- 112 tests passing (60 from batch 1 + 52 from batch 2). Baseline GDAL/Django failures unchanged.

Deferred:
- Reporting has additional non-`_reporting.*`-prefixed symbols in `_LAZY_IMPORTS` (e.g., `hex_tile_layout`, `IDMLExporter`, `ThreeDMapRenderer`) that are extension-tier or optional-dep-gated and were not classified as canonical by the audit. Not promoted in batch 2 by design.
- The `create_powerpoint_generator` / `create_report_generator` / `get_report_output_directory` symbols are defined DIRECTLY in `reporting/__init__.py` (not in a submodule); they resolve to `siege_utilities.reporting`. The `startswith` assertion covers them.

## Trivial-investigation declaration

Category: descriptive-docstring-fix
Cannot produce error: Additive metadata edit. Each name verified at runtime to resolve via existing `__getattr__` path. No new code paths, no exception handlers.
Evidence: `git diff --stat` (relative to batch-1 head) shows 2 files changed: `__init__.py` +27 lines, `tests/test_public_api_surface.py` +43 lines. `pytest tests/test_public_api_surface.py -v` → 112 passed.
Falsification: If any batch-2 name fails to resolve OR resolves to a non-reporting module OR is silently missing from `__all__` after commit.

## Hostile review responses

Hostile review artifact: `plans/hostile-review-1176-batch2.md` (SHIP WITH REVISIONS verdict).

**F1 (Major, cross-module collision on `create_bivariate_choropleth`):** RESOLVED by (a) filing follow-up ticket #1208 to reconcile the two definitions (`reporting/chart_generator.py` chart-oriented vs `geo/choropleth.py` GeoDataFrame-oriented), and (b) adding an inline NOTE comment in `__all__` explicitly documenting the current binding and cross-referencing #1208. Batch 2's promotion does NOT change runtime resolution — the reporting variant was already the top-level winner via `_LAZY_IMPORTS`. Promotion makes the choice explicit contract rather than accidental. Long-term reconciliation deferred to #1208 per `writing-code:17` (deprecation shims require follow-up tickets).

**F2 (Minor, test assertion too loose):** RESOLVED by tightening `test_batch_2_symbol_resolves_under_reporting` from `startswith("siege_utilities.reporting")` to explicit `== "siege_utilities.reporting" OR startswith("siege_utilities.reporting.")`. Rejects hypothetical `reporting_v2` sibling packages. All 26 tests still pass.

## Trivial pre-mortem declaration

Additive metadata edit + additive test cases. No behaviour modified. Follows the template pattern proven by batch 1 (PR #1207 hostile-reviewed and shipped with revisions applied).

# Hostile review — #1176 batch 2 (reporting canonicals)

Branch: `feat/1176-promote-canonicals-reporting-batch2` vs `feat/1176-promote-canonicals-geo-spatial-data`.

## Findings

### F1 (Major) — Cross-module name collision: `create_bivariate_choropleth`

Two independent definitions exist with the same public name:

- `siege_utilities/reporting/chart_generator.py:219` — `def create_bivariate_choropleth(...)` (batch-2 target, in `reporting.__all__` L545, in `reporting/__init__.py` re-export L357)
- `siege_utilities/geo/choropleth.py:440` — `def create_bivariate_choropleth(...)` (in `geo/choropleth.py:__all__` L63)

Same shape as batch-1 F1. Batch 2 registers this name against `.reporting` — verified via runtime `getattr(su, 'create_bivariate_choropleth').__module__ == 'siege_utilities.reporting.chart_generator'`. The `geo.choropleth` version is now the shadowed variant at the top level. The `_register_lazy` guard does NOT fire because `geo.choropleth.create_bivariate_choropleth` was never registered as a lazy import — it was reachable only via `from siege_utilities.geo.choropleth import ...`.

Risk: if a future batch registers `geo.choropleth.create_bivariate_choropleth` lazily, the guard raises. More immediately, docs/notebooks importing `create_bivariate_choropleth` from top-level now silently get the reporting variant. These are different functions (reporting one takes `data: DataFrame|Dict`; geo one has different signature per file). Needs an explicit resolution: rename one, add an `_LAZY_IMPORT_OVERRIDES` entry, or document canonical.

### F2 (Minor) — `test_batch_2_symbol_resolves_under_reporting` uses `startswith("siege_utilities.reporting")` which matches a hypothetical `siege_utilities.reporting_v2` sibling package. Given the 4-submodule spread this is a defensible relaxation from batch-1's exact match, but tightening to `startswith("siege_utilities.reporting.") or module == "siege_utilities.reporting"` would eliminate the false-negative surface without cost.

## Verifications performed

- `git diff feat/1176-...geo-spatial-data..HEAD` on `__init__.py` + tests — 26 names added, TestBatch2Promotions added, no other edits.
- `grep -rn "^def NAME\|^class NAME"` for all 26 batch-2 names — one collision (F1); others unique.
- Runtime `getattr(su, name).__module__` for all 26 — all resolve under `siege_utilities.reporting.*` (chart_generator ×12, reporting ×6, analytics.polling_analyzer, analytics_reports, templates.base_template, chart_types, client_branding, powerpoint_generator, report_generator).
- `pytest tests/test_public_api_surface.py` — 112 passed (52 batch-2 + 60 pre-existing). Batch-1 exact-match test still green — no shadow of geo names.
- Extension-tier omission check: 12 reporting-package extension candidates (Argument, TableType, BUILTIN_LAYOUTS, hex_tile_*, IDMLExporter, ThreeDMapRenderer, SIMPLEIDML_AVAILABLE, PYDECK_AVAILABLE, etc.) are all present in `reporting.__all__` but NOT in `_LAZY_IMPORTS`. Audit script only classifies lazy-registered symbols; these are out of scope for #1176. Exclusion is justified.
- Batch-2 vs batch-1 name-duplicate check — no overlap.

## Verdict

**SHIP WITH REVISIONS**

F1 is a real hazard and matches the batch-1 F1 shape that was explicitly handled there. Requires a decision (rename, override, or documentation) before merge. F2 is polish; can defer.


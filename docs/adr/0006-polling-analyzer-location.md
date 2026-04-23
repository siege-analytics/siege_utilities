# ADR 0006 — polling_analyzer location

**Status:** Proposed
**Date:** 2026-04-22
**Epic:** ELE-2415 (sub-issue ELE-2417)

## Context

`siege_utilities/reporting/analytics/polling_analyzer.py` lives under `reporting/`, but its code is analytics, not reporting. Functions like `create_cross_tabulation_matrix`, `create_longitudinal_analysis`, `create_performance_rankings`, and `create_change_detection_data` are pure data operations. Only `create_heatmap_visualization` and `create_trend_analysis_chart` are reporting-shaped (they produce matplotlib Figures).

`docs/INTENT.md` flagged this as divergence D6. PR #389 reshaped the file but didn't move it.

## Decision

**Split on the function boundary, not the module-of-concern.**

1. Create `siege_utilities/analytics/polling/` as a new subpackage.
2. Move generic analytics primitives there: `create_cross_tabulation_matrix`, `create_longitudinal_analysis`, `create_performance_rankings`, `create_change_detection_data`, `create_polling_summary`. Also move `PollingAnalysisError` and `_choose_heatmap_fmt` helper.
3. Keep reporting-shaped wrappers in `reporting/analytics/polling/` or inline them in `reporting/charts/`: `create_heatmap_visualization`, `create_trend_analysis_chart`.
4. `PollingAnalyzer` class stays in the analytics tree; the two chart methods become standalone module functions in the reporting tree OR a `ChartablePollingAnalyzer` mixin that depends on `reporting`.

The end goal: importing `siege_utilities.analytics.polling` does NOT pull reportlab/matplotlib at module load — only when a charting function is called.

## Consequences

**Positive:**
- Analytics primitives don't require reportlab (fixes the `reportlab` module-load cascade per ADR 0005)
- Location matches purpose (directly addresses divergence D6)
- Easier to test the analytics functions in a slim environment

**Negative:**
- Existing callers that do `from siege_utilities.reporting.analytics.polling_analyzer import PollingAnalyzer` need to change. Fix: re-export from old path with a `DeprecationWarning` for one minor version.
- The `PollingAnalyzer` class API is now split across two trees. Fix: keep the class in analytics/; chart methods become free functions `from siege_utilities.reporting.analytics.polling import render_heatmap`.

## Alternatives considered

1. **Keep as-is** — rejected. Violates the intent statement; compounds the import-cascade problem.
2. **Move the whole file to `analytics/`** — rejected. Then chart functions in `analytics/` import matplotlib at module load — same problem, different directory.
3. **Split further: data/polling/ for pandas ops, analytics/ for analytics wrappers, reporting/ for charts** — rejected as over-engineering. Two locations is enough.

## Migration

- Phase M2 (per ARCHITECTURE.md): create `siege_utilities/analytics/polling/` alongside existing file.
- Export `PollingAnalyzer` from new location; old path re-exports with `DeprecationWarning`.
- Notebooks using the old path work unchanged; new notebooks (ELE-2421) use the new path.
- Remove old path in next major version.

## References

- `docs/INTENT.md` D6
- `reporting/analytics/polling_analyzer.py` (current location)
- PR #389 (recent reshape)
- ADR 0005 (lazy-import convention)

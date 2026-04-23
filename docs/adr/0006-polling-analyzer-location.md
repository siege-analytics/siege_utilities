# ADR 0006 — PollingAnalyzer deprecation and replacement

**Status:** Accepted (supersedes prior "Proposed" draft that recommended moving the class)
**Date:** 2026-04-22 (revised 2026-04-23)
**Epic:** ELE-2415 (implemented under ELE-2439 + ELE-2440)

## Context

`reporting/analytics/polling_analyzer.py` was written before the `survey/` module existed. It bundles three concerns:

1. Cross-tabulation (now duplicated by `survey.crosstab.build_chain` + `data.cross_tabulation`).
2. Longitudinal analysis + change detection (genuinely useful, nowhere else in the library).
3. Heatmap / trend chart generation (reporting's job, not analytics').

On top of this, its location (`reporting/analytics/`) inverts the natural dependency: analytics is an upstream concern; reporting is one consumer of it. And surveys *have waves* — meaning the "longitudinal" concept belongs in the survey model, not a standalone analyzer.

The original draft of this ADR proposed moving the file into a new `analytics/polling/` location. That was a half-measure. With the survey module already offering a cleaner pipeline, the right answer is to deprecate `PollingAnalyzer` and distribute its value to places that already handle the underlying natures.

## Decision

**Deprecate `PollingAnalyzer`. Redistribute its content by nature. Remove after one minor version.**

### Immediate (this audit)

| Thing | New home | Rationale |
|---|---|---|
| Cross-tabulation | `data/statistics/cross_tabulation` (ELE-2437) | Already lives there; polling_analyzer's was a near-duplicate. |
| Longitudinal analysis, change detection | `data/statistics/longitudinal.py` | Pure stats primitives; survey waves delegate to these. |
| Heatmap / trend chart helpers | `reporting/polling_charts.py` (or absorbed by `reporting/wave_charts.py`) | Reporting's responsibility. |
| `PollingAnalyzer` class | Stays for one minor version, emits `DeprecationWarning` on construction. | Soft break for any unknown consumers. |
| `reporting/analytics/` subdirectory | Deleted. `analytics_reports.py` promoted to `reporting/analytics_reports.py`. | The subdirectory existed only for polling_analyzer. |

### Near-term (ELE-2440)

Add first-class **`Wave`** and **`WaveSet`** dataclasses to `survey/models.py`. A `WaveSet.compare_chain(row_var, break_vars)` produces longitudinal crosstab results directly — the thing `PollingAnalyzer.longitudinal_analysis` was trying to do, but natively modeled instead of tacked on.

`survey/waves.py` holds the longitudinal logic (delegating to `data/statistics/longitudinal`). `reporting/wave_charts.py` provides the chart wrappers.

### Next minor release

Remove `PollingAnalyzer`, remove the top-level export, remove the deprecation shim.

## Consequences

**Positive:**
- Nature wins: cross-tab is stats, longitudinal is stats, charts are reporting, waves are survey. Each lives where it belongs.
- Waves model fills a genuine gap in the survey module.
- Deletes ~467 LOC of duplicated / orphaned logic.
- Eliminates the inverted `reporting/analytics/` path.

**Negative:**
- Any external caller using `from siege_utilities import PollingAnalyzer` gets a `DeprecationWarning` now and a hard break one release later. Mitigation: migration guide in the deprecation message and CHANGELOG.
- Heatmap / trend chart helpers need a new home. Not a lot of code.

## Alternatives considered

1. **Move `PollingAnalyzer` intact to `analytics/polling/`** (the previous draft). Rejected. Leaves the duplicated cross-tab logic, doesn't address the missing wave abstraction, and keeps an orphaned class.
2. **Straight-delete with no deprecation window.** Rejected even though the class has no known users. It's publicly exported; unknown downstream users deserve a warning.
3. **Keep and fix in place.** Rejected — there's no way to fix the "bundled by workflow, not nature" design without splitting.

## Migration

- Phase 1 (this audit, paired with ELE-2437):
  - Extract longitudinal/change-detection to `data/statistics/longitudinal.py`.
  - Add `DeprecationWarning` on `PollingAnalyzer.__init__` with migration text pointing to `survey.WaveSet` (incoming) + `data.statistics`.
  - Delete `reporting/analytics/` subdirectory; promote `analytics_reports.py`.
- Phase 2 (ELE-2440):
  - Ship `Wave` / `WaveSet` + `reporting/wave_charts.py`.
- Phase 3 (next minor release):
  - Remove `PollingAnalyzer` class and top-level export.

## References

- `docs/INTENT.md` D7
- `reporting/analytics/polling_analyzer.py` (current location; to be removed)
- `survey/__init__.py` (target home for wave abstraction)
- `data/cross_tabulation.py` (already present; will grow a `longitudinal.py` sibling)
- ELE-2437, ELE-2439, ELE-2440

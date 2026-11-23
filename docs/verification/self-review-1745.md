# Self-review: PR #1745 chart annotations, grouped bars and dashboard data loss (#1556)

Review-Tier: C (public reporting engines; pre-flight round with a develop merge and a BREAKING classification).

## Assumptions
Working as: software engineer (Junior) and reporting tech lead (Lead).
Domain(s): software engineering (matplotlib chart engines, dashboard composition, exception contracts).
Geospatial cross-cut: no.
Goal source: #1556 (horizontal bar labels misplaced and truncated, `group_by` ignored, dashboards silently dropping datasets and subplots). This round is a pre-flight of the existing implementation at `150cdd9c`: resolve the develop conflict, classify the CHANGELOG entry against the v4.0.0 tag, correct the stale PR-body note about the allow-list, and re-run red/green evidence. No library code changed in this round.
Plan reference: docs/verification/self-review-1745.md#pre-mortem
Investigate-artifact: https://github.com/siege-analytics/siege_utilities/issues/1556#issuecomment-6758612886
Pre-mortem-artifact: https://github.com/siege-analytics/siege_utilities/issues/1556#issuecomment-6758612886
Project-contribution: charts label the values they draw, and a dashboard either shows every dataset or fails loudly.

## Investigation
- GitHub reported PR #1745 CONFLICTING with develop `71f02b0b` (2 ahead, 104 behind). Merge base `9620d258`. The only file changed on both sides is `CHANGELOG.md` (`[4.1.0] ### Fixed`); the three engines, `scripts/exception_contracts_allowlist.json` and the new test file are unchanged on develop.
- v4.0.0 `composite_engine.py` subplot helpers caught `(ValueError, TypeError, KeyError, IndexError, AttributeError)`, logged, and carried on, so `create_dashboard` returned a partial image. The PR removes the four handlers and their allow-list entries; `create_dashboard` raises `RuntimeError(f"Dashboard Error: {e}") from e`.
- The PR body still says the four-entry allow-list cleanup "awaits approval", but it is already in the diff (commit `150cdd9c`). The body correction is prepared alongside this round.
- REST: 0 inline review comments and 0 reviews on PR #1745.

## Pre-mortem
1. Tiger. Severity: P1. The CHANGELOG union drops a develop line. Mitigation: develop's side of the only hunk kept verbatim; post-merge `git diff origin/develop -- CHANGELOG.md` empty; after the BREAKING entry, 0 removed lines.
2. Tiger. Severity: P2. Develop added handlers that make the allow-list stale or incomplete. Mitigation: `scripts/check_exception_contracts.py` on the merged tree -> 203 handlers flagged, 0 unlisted, 0 stale.
3. Paper Tiger. Severity: P2. Red evidence is vacuous. Mitigation: failures read; most are behaviour assertions. Three of the 24 fail because v4.0.0 lacks the new `value_format` keyword or the helper's `text` argument; these are API-shape reds, recorded as such.
4. Elephant. Severity: P3. The PR body contradicts the diff. Mitigation: body correction prepared.

## Peer review (Junior: shelves, gates)
- Shelves: SU-1 (subplot errors propagate instead of producing a partial image); SU-4b (every removed handler's error path is now a raise covered by the regression file).
- Gate 1 (syntax): no Python file changed in this round.
- Gate 2 (tests): on the merged tree, the regression file plus the bar/base/composite/stats/map engine error suites, dashboard and chart wrapper contracts, chart generator and chart types -> 100 passed.

## Lead review (adversarial)
Phase A coherence: CHANGELOG, tests and diff agree on the raised `RuntimeError`, the labels/datasets schema, grouped bars and the heatmap/pie fixes.
Phase B verification (red/green): `tests/test_chart_engines_labels_and_dashboard.py` copied into a detached v4.0.0 worktree (`9c3463b1`) -> 24 failed (e.g. `DID NOT RAISE` for overflow/unknown type/invalid data, `assert [] == ['First', 'Second']` for missing legends, `ValueError: cannot convert float NaN to integer` for pie totals). On the merged branch -> 24 passed. Import paths were checked to resolve to each worktree's package.

## Findings
| ID | Priority | Description | Resolution |
|----|----------|-------------|------------|
| F1 | P2 | Branch CONFLICTING with develop (CHANGELOG only) | additive merge `efbb4480`; develop side kept verbatim |
| F2 | P2 | Caller-visible changes listed under Fixed, not BREAKING | entry under `[4.1.0] ### BREAKING` with Migration |
| F3 | P3 | PR body describes the allow-list cleanup as pending | body correction prepared |
| F4 | P3 | Tip lacked review trailers | this commit carries them |

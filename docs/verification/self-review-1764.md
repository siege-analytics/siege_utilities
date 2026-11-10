# Self-review: PR #1764 legend and classification accuracy (#1535), pre-flight

Review-Tier: C (the checkout's path floor; this commit changes `siege_utilities/reporting/engines/map_engine.py`, `stats_engine.py`, tests and `CHANGELOG.md`).

## Assumptions
Working as: software engineer (Junior) and cartography/visualization tech lead (Lead).
Domain(s): choropleth classification, legends, heatmaps.
Geospatial cross-cut: yes (choropleth classes over polygons; no CRS change).
Goal source: the #1535 Problem / Done when / Falsifier sections; ruling to complete each ticket's acceptance criteria on its PR (natural_breaks computes real Jenks or raises; no forced centring on sequential colormaps).
Plan reference: https://github.com/siege-analytics/siege_utilities/issues/1535#issuecomment-6761746998
Investigate-artifact: https://github.com/siege-analytics/siege_utilities/issues/1535#issuecomment-6761746998
Pre-mortem-artifact: https://github.com/siege-analytics/siege_utilities/issues/1535#issuecomment-6761746998
Hostile-review-artifact: none yet. An independent exact-head review of the pushed commit is pending; this is NOT a pass.
Project-contribution: maps and heatmaps read the way their legends say.

## Investigation
- At PR head `d7337a4b`, the heatmap legend bins, the bivariate legend orientation and the advanced choropleth's range legend are fixed and tested. `classification="natural_breaks"` still ran `pd.qcut` ("quantiles as approximation"), and `create_heatmap` still passed `center=0` with `YlOrRd`. The PR body called both "follow-ups" and left #1535 open.
- `siege_utilities.geo.classification.classify_series(values, "natural_breaks", k)` already computes Fisher-Jenks (numpy, or mapclassify `FisherJenks` when installed; mapclassify is in the `geo` and `reporting` extras). It returns per-value class indices (`-1` for NaN) and k+1 edges.
- Develop `2deb6a1f` changed none of the touched files since merge-base `7f534f6c`.

## Pre-mortem
1. Tiger (launch-blocking). Severity: P1. Map and legend disagree after switching classifiers. Mitigation: both come from one `ClassificationResult`; `test_natural_breaks_uses_fisher_jenks_not_quantiles` checks legend edges against the classifier and each polygon's swatch against its class.
2. Tiger (fast-follow). Severity: P2. NaN handling. Mitigation: `-1` becomes NaN before plotting; `test_natural_breaks_leaves_missing_values_unclassified`.
3. Tiger (launch-blocking for release notes). Severity: P1. Non-breaking mislabel. Mitigation: `### BREAKING` + Migration in `CHANGELOG.md` and the PR body.
4. Paper Tiger. Severity: P3. mapclassify missing. Mitigation: the numpy Fisher-Jenks fallback in `geo/classification.py`.
5. Elephant. Severity: P3. Correlation heatmaps still use a sequential colormap; choosing a diverging map is outside #1535.

## Peer review (Junior: shelves, gates)
- Shelves: SU-2 (natural_breaks now does what it says); reuse an existing library API instead of a new dependency.
- Gate 1 (syntax/lint): flake8 with the ratchet rule set is clean on the touched files; the remaining E128/E303/E402 style hits are pre-existing and outside the changed lines. `scripts/check_test_file_hygiene.py`: PASS.
- Gate 2 (tests): reporting-related files (`test_reporting_markup_escaping`, `test_reporting_mapping_wrapper_contracts`, `test_public_api_surface`, `test_stats_engine_errors`, `test_exception_contract_sites`, `test_chart_generator`, `test_map_engine_errors`, `test_polling_analyzer`, `test_backward_compat`, `test_reporting_module`, `test_legend_data_accuracy`) plus smoke/runtime-guard/SQL-safety, `--no-cov -p no:randomly`: 808 passed, 1 skipped.
- Gate 3 (docs): the #1535 entry in `CHANGELOG.md` `[4.1.0]` `### BREAKING` (with Migration), mirrored in the PR body.
- Notebook impact (SU-4a): no notebook calls `create_advanced_choropleth` or `create_heatmap`.

## Lead review (adversarial)
Phase A coherence: natural breaks → `classify_series`; heatmap centring → keyword removed.
Phase B verification (`tests/test_legend_data_accuracy.py`, 19 tests):
- Against PR head `d7337a4b`'s two engines: 3 failed / 16 passed (natural breaks, heatmap pivot and correlation); the missing-value test passes there as a control.
- Against `v4.0.0`'s `map_engine.py`, `stats_engine.py` and `legend_manager.py`: 19 failed / 0 passed.
- After: 19 passed.
- Fixture check: the natural-breaks test asserts that its fixture's Jenks and quantile edges differ; the first candidate fixture did not separate them and was replaced.

## Findings
| ID | Priority | Description | Resolution |
|----|----------|-------------|------------|
| F1 | P1 | natural_breaks computed as quantiles | Fisher-Jenks via `classify_series` |
| F2 | P2 | Heatmap centred a sequential colormap at 0 | `center` removed |
| F3 | P2 | No `CHANGELOG.md` entry; body "Refs", Fixed, follow-up wording, local interpreter path | BREAKING entry in `CHANGELOG.md` and body; "Fixes #1535"; hygiene |

Out of scope, reported only: an unrecognised `classification` value silently falls back to quantiles.

## Ticket-fitness exemption

writing-rules:4 exemption for the governing ticket.

### #1535
- **Reason:** #1535 predates the canonical ticket template. It uses Problem / Evidence / Failure scenario / Done when / Assumptions / Falsifier sections.
- **Evidence:** the defects, the v4.0.0 probes and the acceptance criteria are in the #1535 body. The investigation, pre-mortem and Junior/Senior review are at https://github.com/siege-analytics/siege_utilities/issues/1535#issuecomment-6761746998.
- **Falsification:** restore `siege_utilities/reporting/engines/map_engine.py` and `stats_engine.py` from `d7337a4b`; `test_natural_breaks_uses_fisher_jenks_not_quantiles` and both `test_heatmap_does_not_center_sequential_colormap` cases then fail. Verified on 2026-11-10.

## Test plan / Quantified claims
Interpreter: local Python 3.11.11, run from the repository root.
- Reporting run as in Gate 2: 808 passed, 1 skipped.
- `tests/test_legend_data_accuracy.py`: 3 failed / 16 passed on `d7337a4b`; 19 failed on `v4.0.0`; 19 passed after.

## Review follow-up (three review threads)
- 4523483238 (`map_engine.py:434`, boundary inclusivity): a probe of both backends on the same data showed mapclassify reports each class's upper bound while the numpy backend reports the next class's lower bound (e.g. `[0, 2, 32, 62]` vs `[0, 30, 60, 62]` for the same partition), each assigning classes consistently with its own breaks. A first attempt to re-assign classes with `searchsorted(side="left")` would have misclassified numpy edge values and was replaced: the legend keeps the backend's classes and builds upper-inclusive ranges ending at each class's largest value. The numpy backend's own class assignment and breaks in `geo/classification.py` are unchanged (outside this PR).
- 4523483252 (`map_engine.py:450`, zero-width intervals): precision uses only positive finite widths, falling back to one decimal; zero-width ranges print the value.
- 4523483272 (`legend_manager.py:181`, fractional edges with step ≥ 1): precision is the fewest decimals (≤ 6) that represent every edge exactly; the step < 1 behaviour is unchanged.
- Red at `821fd9a4`: `test_natural_breaks_value_on_interior_break_uses_lower_range[numpy]`, `test_natural_breaks_constant_fractional_column`, and both `step-over-one-fractional` cases (4 failed; the mapclassify boundary case passes as a control). After: 24 passed in the legend tests; 838 passed, 1 skipped in the reporting run.

## Rework ledger
- Pre-flight round, 2026-11-10: Fisher-Jenks natural breaks; heatmap centring removed; CHANGELOG entry; body classification and acceptance map.

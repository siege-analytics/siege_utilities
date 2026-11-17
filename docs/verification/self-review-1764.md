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

## Fix round, 2026-11-17: label precision from edges as well as widths

The whole-PR review of head `e6e43b1d` failed with one S2 (https://github.com/siege-analytics/siege_utilities/pull/1764#issuecomment-6935347297).

### Cause
Both formatter families picked decimals from the interval width only, so a fractional offset was lost.
- Heatmap (`LegendManager._heatmap_legend_bins`, which feeds the Matplotlib elements and the ReportLab table): 0.004 to 0.054 in five levels printed `0.00 - 0.01` up to `0.04 - 0.05`, leaving out the maximum. One level over 0.004 to 0.014 printed `0.00 - 0.01`, and a minimum of 0.006 printed as 0.01.
- Advanced choropleth (`MapChartMixin.create_advanced_choropleth`): quantiles over 0.0625 to 15.0625 started at 0.1, equal interval over 10.125 to 20.125 ended at 20.1, and natural breaks lost the minimum on both classifier backends.

The earlier note on review thread 4523483272 said the step < 1 behaviour was unchanged; that branch is now covered by this fix round.

### Fix
- New private module `siege_utilities/reporting/_range_labels.py`, used by both formatters. `format_range_edges(edges, minimum_decimals)` starts from the caller's width-based decimals and adds decimals until every edge is shown exactly. The cap is six decimals, or the width-based count if that is larger.
- If an edge is still not exact at the cap (1/3, 0.0000013), every edge is shown at the cap. Interior edges are rounded to nearest. The first and last bounds are rounded outward (floor and ceiling), so the displayed extent always contains the data; a displayed outer bound can then be slightly wider than the data. The docstring and the CHANGELOG say so.
- "Exact" allows floating-point noise (0.1 + 0.2 counts as 0.3). The first version used one tolerance for all edges; the second fix round below replaced it with a per-edge tolerance.
- Adjacent ranges share one formatted string for their common edge, so the labels stay contiguous.
- Unchanged: class assignments, dropped duplicate edges, the shared swatch normalization, and the zero-width advanced branch (a range whose ends are equal still prints the value itself). The width-based minimum is still computed the same way in both places.

### Label changes outside the reported cases
- Equal-interval legends now show the lowered first edge that `pd.cut` uses to include the minimum when it has a fractional part. Integer data 1 to 10 in three bins reads `0.991 - 4.000` instead of `1.0 - 4.0`. This is the true classification edge; it is listed for the reviewer to judge.
- Heatmap edges that never terminate (0 to 1 in three levels) now show six decimals, as steps of 1 or more already did at `e6e43b1d` (0 to 100 in seven levels).
- A constant heatmap at 0.125 now reads `0.125 - 0.125` instead of `0.12 - 0.12`.

### Tests (`tests/test_legend_data_accuracy.py`, 36 new, all on final labels)
- Heatmap offsets, both renderers: the review's four heatmap cases plus a negative offset (10).
- Heatmap cap path, both renderers: 0.0000013 to 0.0000113 reads `0.000001` to `0.000012` (2).
- Heatmap labels unchanged from `e6e43b1d`, both renderers: integer, unit, 0 to 7.5, thousands and zero-width (10).
- Helper: outward rounding only on the outer bounds, and floating-point noise not widened (1).
- Advanced offsets, quantiles, equal interval and natural breaks on mapclassify and NumPy (6).
- Advanced cap path: quantiles over 1/3 to 50/7 reads `0.333333` to `7.142858` (1).
- Advanced labels unchanged from `e6e43b1d`: quantiles, equal interval, dropped duplicate edges, small fractions, natural breaks and zero width (6).

### Results
- Red on `e6e43b1d` (the two source files restored from that head): the 19 offset and cap regressions failed. The 16 unchanged-label controls and the helper test passed, which shows those labels are the same as before. The reviewer's reproducer, run in the worktree with byte copies of its frozen v4.0.0 modules, failed its 12 extent cases and passed the other 26.
- After: the reviewer's reproducer passed 38 of 38. The legend module with both bivariate tie modules passed 104 (the 68 existing plus 36 new). The map and stats error, mapping-wrapper, release-process and changelog-export modules passed 33. `tests/test_reporting_module.py` passed 77 with 1 existing skip.
- `ruff check --select F,E9` on the changed Python files: no findings. Exception-contract scanner: 0 unlisted, 0 stale.
- The reproducer and the frozen modules were removed from the worktree before staging and are not part of the PR.

### Not changed
S3 (adjacent labels such as `0.0 - 2.0` and `2.0 - 32.0` do not show which range holds 2.0) is left for a follow-up. A legend note would change the legend title that the existing tests and users' image baselines depend on, or add a new text element to every advanced map.

## Second fix round, 2026-11-17: per-edge exactness

The delta review of staged tree `4bcaeae8` failed with one S2: the exactness tolerance was global.

### Cause
`format_range_edges` judged every edge against one tolerance, `max(1e-9 x smallest width, 8 eps x largest |edge|)`. One distant edge inflated it: with an edge at 1e12 it was about 0.0018, so 1.0044 counted as exact at 1.004 and outward rounding was suppressed. Quantiles over two classes of `[-1e12, 1.0044, 1.0064]` printed `-1,000,000,000,000.000 - 1.004` and `1.004 - 1.006`, so the median and the maximum both lay above their own class labels. The mirror case `[-1.0064, -1.0044, 1e12]` lost the minimum, and `[1.0044, 1.0064, 1e12]` showed 1.006 as the first class's upper bound, below the plotted 1.0064. A review addendum found the same cause in a heatmap with steps of 1 or more: 0.875 to 1e18 in five levels printed its first lower bound as `1` on both renderers, where `e6e43b1d` printed `0.875`.

### Fix
- Each edge is judged against its own magnitude only: an edge is exact at a decimal count when rounding moves it by at most 8 units in the last place of that edge. No other edge enters its tolerance, so a distant edge cannot hide a small edge's digits. This also holds when every neighbour of the small edge is distant (`[1.0044, 5e11, 1e12]`, `[-1e12, 1.0044, 1e12]`, or a one-level heatmap from 1.0044 to 1e12). A first attempt that used the nearest neighbour's scale failed those cases and was replaced before staging.
- Outward rounding of the first and last bounds follows from the same per-edge test.
- Heatmap edges are now computed in exact decimal arithmetic from the decimal forms of min and max, so evenly spaced edges carry no float noise for the per-edge test to misread (in floats the middle edge of -0.2 to 0.1 in three levels is 2.8e-17; in decimal it is 0). Their labels are unchanged.
- An edge that rounds to zero is shown as `0.000`, never `-0.000`.
- Tradeoff: if an advanced-map edge reaches the formatter as float noise near zero (for example 5.6e-17 between -0.1 and 0.1), it is no longer counted as zero, so that legend uses the six-decimal cap and shows the edge as `0.000000`. That label approximates the edge to about the size of the float noise; it is not the exact edge. Quantiles over `[-0.1, -n, -n/2, 0.1]`, with `n = 0.1 + 0.2 - 0.3`, put the interior edge at -4.16e-17, and the second range is printed from `0.000000` although its member `-n/2` lies 2.78e-17 below zero. The third fix round's round-trip rule leaves this case as it is: the labels are still `-0.100000 - 0.000000` and `0.000000 - 0.100000`. The fourth fix round prints the same values with fewer zeros, `-0.10 - 0.00` and `0.00 - 0.10`; the approximation is unchanged.

### Tests (`tests/test_legend_data_accuracy.py`, 18 new)
- Helper, the review's three cross-scale cases (3), and three cases where every neighbour is distant (3).
- One-level heatmap from 1.0044 to 1e12, both renderers (2).
- Heatmap from 0.875 to 1e18 in five levels, both renderers, with the labels `e6e43b1d` printed (2).
- Signed zero (1).
- Rendered quantiles for the review's three cases: exact labels, and every value inside its own class label (3).
- Unchanged-label heatmap controls for float noise crossing zero and above zero, both renderers (4).

### Results
- Red on staged `4bcaeae8` (the two changed source files restored from the index): 14 of the 18 new tests failed, and the four float-noise controls passed. The same four controls also pass with `e6e43b1d`'s `legend_manager.py`. The review's falsifier (13 items), run in the worktree as a byte copy, failed 8 (three helper, three rendered quantile, two wide heatmap) and passed its 5 label-change checks. The review's base control, which loads `e6e43b1d`'s `legend_manager.py` and checks that it printed `Low: 0.875 - ...`, passed.
- After: the review's falsifier passed 13 of 13, its base control passed, and the earlier boundary reproducer (with byte copies of its frozen v4.0.0 modules) passed 38 of 38. The legend module with both bivariate tie modules passed 122. The map and stats error, mapping-wrapper, release-process and changelog-export modules passed 33, and `tests/test_reporting_module.py` passed 77 with 1 existing skip: 284 passed in one run.
- The label changes the review accepted are kept: the equal-interval first edge `0.991` from `pd.cut` is not clamped, non-terminating heatmap edges show six decimals, and a constant 0.125 heatmap reads `0.125` on both renderers.
- `ruff check --select F,E9`: no findings. Exception-contract scanner: 0 unlisted, 0 stale. Test-file hygiene: pass.
- The falsifier, its base control, the reproducer, the frozen modules and a temporary probe test were removed from the worktree before staging.

## Third fix round, 2026-11-17: exactness by round-trip

The delta review of staged tree `b4606bd5` failed with one S2: a per-edge tolerance of 8 units in the last place (ulps) still hid real digits. The second fix round's per-edge tolerance described above is replaced by the rule below.

### Cause
At 1e12 one ulp is about 1.2e-4. Quantile edges `[0, 1e12 + 36 ulp, 1e12 + 52 ulp]` make a final class 16 ulps wide, and three decimals move each edge by 3 ulps, within the 8-ulp tolerance but 18.75% of that class. The labels ended `...000.004` and `...000.006`, excluding the real `...000.0044` and `...000.0063`; the negative and inner-class variants failed the same way in the rendered legend. In both heatmap renderers, 1e15 + 0.875 to 10 above it in five levels printed its first lower bound as `1,000,000,000,000,001`, excluding the exact minimum by 0.125; `e6e43b1d` printed `...000.9`, which reads back as the same float.

### Fix
- An outer edge (the first or last) is shown only when its label reads back as the identical float: `float(f"{edge:.{d}f}") == edge`. The decimal count is the smallest from the width-based minimum up to the cap at which every edge is shown. If an outer edge still does not read back at the cap, it is rounded outward as before, now from the float's exact binary value (`Decimal(edge)`) rather than its shortest text, so the bound is never on the wrong side of the edge.
- An interior edge also counts as shown when its label is within the smaller of 8 ulps of the edge itself and 1e-9 of the narrower class it bounds. Both terms are local to the edge. This keeps pandas' quantile edges such as `1000.0000000000002`, `260.0000000000001` and `5.062499999999999` showing as `1,000.0`, `260.0` and `5.0625`, as at `e6e43b1d`; under round-trip alone every ordinary quantile legend went to the six-decimal cap. The class term blocks the 1e12 case above (1e-9 of a 16-ulp class is far below 3 ulps), and the ulp term keeps 1.0044 between -1e12 and 1e12 at four decimals.
- Unchanged: the exact decimal heatmap edges (each is the float nearest its decimal, so it reads back), the unsigned zero, the six-decimal cap and its outward rounding, and the accepted label changes (the equal-interval `0.991` first edge, six-decimal non-terminating edges, a constant `0.125`).

### Tests (`tests/test_legend_data_accuracy.py`, 9 new)
- Helper, the review's three large-magnitude cases, with exact labels that read back as the edges (3).
- Rendered quantiles for the same three cases, each value inside its own class label (3).
- Heatmap 1e15 + 0.875 to 10 above it, both renderers, exact labels and both outer bounds equal to the data (2).
- A noisy pandas edge (`1000.0000000000002`) shown as `1,000.0` inside the legend but widened outward from its exact value as an outer bound (1).

### Results
- Red on staged `b4606bd5` (the three source files restored from the index): the 9 new tests failed. The review's 17-item falsifier, run in the worktree as a byte copy, failed its 8 large-magnitude and heatmap cases and passed its 9 controls; the earlier 13-item falsifier and the base control passed.
- After: the 17-item falsifier passed 17, the 13-item falsifier passed 13, the base control passed, and the earlier boundary reproducer (with byte copies of its frozen v4.0.0 modules) passed 38. The legend module (87) with both bivariate tie modules passed 131. The map and stats error, mapping-wrapper, release-process and changelog-export modules passed 33, and `tests/test_reporting_module.py` passed 77 with 1 existing skip: 310 passed in one run. All earlier legend regressions pass unchanged.
- `ruff check --select F,E9`: no findings. Exception-contract scanner: 0 unlisted, 0 stale. Test-file hygiene: pass.
- The falsifiers, the base control, the reproducer, the frozen modules and a temporary probe test were removed from the worktree before staging.

## Fourth fix round, 2026-11-17: every edge that can be written exactly is

The delta review of staged tree `07a48747` failed with one S2 and ruled the third fix round's interior allowance out: an interior edge that can be written exactly within the six-place cap must be written exactly. The allowance described in the third fix round above is removed.

### Cause
An interior edge counted as shown when its label was within the smaller of 8 ulps of the edge and 1e-9 of the narrower adjacent class. Those bound how far the printed edge moves, not how many data values it moves past. Quantiles over `[0] + [1e9 + 0.100001] * 20 + [2e9]` have the interior edge 1000000000.100001, which reads back exactly at six places, but the legend printed `0.0 - 1,000,000,000.1`, leaving 20 of the 21 first-class members above their own range. `1e12 + 0.1001`, exact at four places, failed the same way, and a negative mirror left upper-class members four ulps below their printed lower bound.

### Fix
- Each edge has a required decimal count, from the width-based minimum up to the cap. If the edge reads back as the identical float at some count up to the cap, it requires that count, so it is written exactly. If it never does (1/3, or pandas edges such as `1000.0000000000002` and `5.062499999999999`), it is shown as its value at the cap and requires only as many decimals as give that same value: `1000.0000000000002` shows as `1,000.0` because `1000.0` and `1000.000000` are the same number.
- For an outer edge that cannot be written exactly, the value compared is the outward-rounded one, from the float's exact binary value. A first edge of `1000.0000000000002` floors to `1,000.0` at one place, the same as at the cap; a last edge of the same value needs the cap (`1,000.000001`) rather than being widened to `1,000.1`.
- The legend uses the largest required count. The ulp and class-width allowance is gone.
- An outer edge rounded outward to zero now prints unsigned. A heatmap from -0.1 to -1e-17 in one level printed `Low: -0.10 - -0.00`, because the outward rounding returned `Decimal("-0.00")` before the zero check; it now prints `Low: -0.10 - 0.00`.
- What remains approximate, within the six-decimal cap: an edge that cannot be written exactly within the cap is shown as its value there, so a value closer to an interior edge than the last printed decimal can still sit on the printed edge rather than inside its own range (the near-zero case below).
- The CHANGELOG entry now states this rule: edges that read back exactly within the cap are written with at least that many decimals; others show their value at the cap with as few decimals as give it; outer edges of that kind are rounded outward, which can take one more digit (`1,000.000001`); and the cap approximation above.
- Unchanged: the exact decimal heatmap edges, the six-place cap and the accepted label changes (the equal-interval `0.991` first edge, six-decimal non-terminating edges, a constant `0.125`). The near-zero case now prints `-0.10 - 0.00` and `0.00 - 0.10`, the same values as before with fewer zeros.

### Tests (`tests/test_legend_data_accuracy.py`, 8 new, 2 updated)
- Helper: 1e9 + 0.100001 at six places, 1e12 + 0.1001 at four, and the negative mirror, with exact labels that read back as the edges (3).
- Rendered quantiles for the 1e9 and 1e12 cases and a negative case whose upper class holds 9 values 4 ulps above the edge, with no member outside its own class label (3).
- The near-zero case's labels pinned as `-0.10 - 0.00` and `0.00 - 0.10` (1).
- Heatmap from -0.1 to -1e-17 in one level, both renderers: `Low: -0.10 - 0.00`, with the upper bound at or above the data (1 test, 2 cases).
- Updated: a near-zero interior edge in the helper now shows `0.0` (its value at the cap) instead of `0.000000`; a noisy pandas edge as a first edge now shows `1,000.0` instead of `1,000.000000`, and a new assertion covers the same value as a last edge, which still needs `1,000.000001`.

### Results
- Red on staged `07a48747` (the helper restored from the index): the 6 representable-edge tests failed, and the 2 updated tests failed on their new expectations. On `07a48747` the negative rendered case left 9 upper-class members outside their range. The near-zero pin was added after that run; the same helper printed that case as `-0.100000 - 0.000000` when it was executed in the previous review round, so the pin does not hold there either. The unsigned-zero heatmap test failed with the helper staged earlier in this round (`48918c5`) on both renderers (`Low: -0.10 - -0.00`).
- After: the 17-item and 13-item falsifiers, the base control and the earlier boundary reproducer (38) passed. The legend module (96) with both bivariate tie modules passed 140. The map and stats error, mapping-wrapper, release-process and changelog-export modules passed 33 with the revised CHANGELOG entry, and `tests/test_reporting_module.py` passed 77 with 1 existing skip: 319 passed in one run.
- `ruff check --select F,E9`: no findings. Exception-contract scanner: 0 unlisted, 0 stale. Test-file hygiene: pass.
- The review's 15-item falsifier for this round (`test_review_1764_round3_edges.py`, sha256 `82622e025127cc4802f17709f7bb65bee8b7b1c93707d12b99a1591051a474ac`) was copied unmodified and run against this tree. It fails at collection, before any test runs: line 7 imports `_interior_allowance` from `siege_utilities.reporting._range_labels`, and this round removes that function by design, so the run was 0 of 15 executed. Its near-zero case also expects the third fix round's output (`-0.100000`, `0.000000`, `0.100000` and an 8-ulp allowance), which conflicts with the cap-equivalent shortening this round adopts (`-0.1`, `0.0`, `0.1`). The other 14 items were not executed. That they would pass, because they cover the same cases as this round's passing regressions, is an inference only and is not claimed as a result.
- The falsifiers, the base control, the reproducer, the frozen modules and a temporary probe test were removed from the worktree before staging.

## Rework ledger
- Pre-flight round, 2026-11-10: Fisher-Jenks natural breaks; heatmap centring removed; CHANGELOG entry; body classification and acceptance map.
- Fix round, 2026-11-17: range-label decimals from edges as well as widths in both formatters, outward rounding of the outer bounds at the cap, 36 final-label regressions, CHANGELOG precision claims corrected.
- Second fix round, 2026-11-17: per-edge exactness tolerance, exact decimal heatmap edges, unsigned zero, 18 regressions.
- Third fix round, 2026-11-17: outer edges must read back as the same float, interior edges within a local ulp and class-width allowance, outward rounding from the exact binary value, 9 regressions.
- Fourth fix round, 2026-11-17: every edge that can be written exactly within the cap is, others show their value at the cap with as few decimals as give it; the interior allowance removed; unsigned outward zero; CHANGELOG wording revised; 8 regressions.

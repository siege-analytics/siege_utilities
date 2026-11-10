# Self-review: PR #1826 statistical correctness across analytics modules (#1422)

Review-Tier: C (public analytics API; pre-flight round with a develop merge, a BREAKING classification and a modified develop test).

## Assumptions
Working as: software engineer (Junior) and analytics tech lead (Lead).
Domain(s): software engineering (pipeline metrics, forecasting, scoring, risk, comparison, pricing).
Geospatial cross-cut: no.
Goal source: #1422 (seven statistical-correctness defects). This round is a pre-flight of the existing implementation at `d1800887`: restore the CHANGELOG entries as BREAKING against the v4.0.0 tag, resolve a semantic conflict with develop, and re-run red/green evidence. No library code changed in this round.
Plan reference: docs/verification/self-review-1826.md#pre-mortem
Investigate-artifact: https://github.com/siege-analytics/siege_utilities/issues/1422#issuecomment-6759217759
Pre-mortem-artifact: https://github.com/siege-analytics/siege_utilities/issues/1422#issuecomment-6759217759
Project-contribution: analytics outputs report what their names claim, and invalid inputs fail loudly instead of producing plausible numbers.

## Investigation
- GitHub reported PR #1826 MERGEABLE/CLEAN (no textual conflict). A temporary no-commit merge of develop `2deb6a1f` showed a semantic conflict: develop's #1444 test `tests/test_analytics_datetime.py::test_pipeline_aware_timestamps_are_normalized_to_utc[default|utc|offset]` failed 3/3 with `assert [] == ['aging']`, while the same cases pass on develop without this PR. Develop was therefore merged (`0937d390`), as approved for a demonstrated semantic conflict.
- The six analytics modules are unchanged between v4.0.0 and this branch's merge base; `analytics/pipeline.py` changed on develop afterwards (#1444) and auto-merged.
- Commit `ef5ae6c0` had moved the seven CHANGELOG bullets into the PR body; they are restored to `CHANGELOG.md`.
- Notebook impact: on develop `2deb6a1f`, `git grep -E 'ConversionRate|\.conversions|aging_threshold'` over notebooks/, siege_utilities/ (excluding pipeline.py) and docs/ finds only the `analytics/__init__.py` export that this PR renames; after this round only the PR's migration doc (`docs/source/analytics.rst:16`) mentions the old names.
- REST: 0 inline review comments and 0 reviews on PR #1826.

## Develop test modified
- File and test: `tests/test_analytics_datetime.py::test_pipeline_aware_timestamps_are_normalized_to_utc` (landed on develop for #1444 via #1778).
- Change: only the analyzer construction, `PipelineAnalyzer(["lead"])` → `PipelineAnalyzer(["lead"], aging_threshold=14.0)`. Every assertion, fixture and parametrization is unchanged; no other line in this or any other develop test changes (`git diff --stat` for the file: 1 insertion, 1 deletion).
- Reason: the test's `aging_items == ["aging"]` assertion depended on the v4.0.0 default (multiplier 2.0 × the stage's average age, about 14 days for its 3/5/20-day items). #1422 replaces that default with an absolute 30-day limit, under which the 20-day item is not overdue. The test exists to check aware-UTC age arithmetic, not the default threshold, so 14.0 days reproduces the same expected aging set under the new semantics.
- Evidence on the merged tree (`0937d390` plus the pin):
  - (a) without the pin: 3 failed, `test_analytics_datetime.py:179: assert [] == ['aging']`;
  - (b) with the pin: all 3 pass (the whole file: 29 passed);
  - (c) mutation controls on the #1444 logic in `analytics/pipeline.py`, each applied temporarily and restored (file byte-identical to HEAD afterwards):
    - M1, default `as_of` made naive (`as_of = datetime.now()` at line 220): the pinned test fails 1/3 (`[default]`: `ValueError: as_of is naive but entered_stage is aware ...`); the other two cases pass an explicit `as_of`;
    - M2, offset dropped instead of converted (`entered_stage.replace(tzinfo=timezone.utc)` at line 334 instead of `astimezone`): the pinned test fails 3/3 (`test_analytics_datetime.py:177: assert 6.9 == 7.0`).
  The pinned test still detects loss of the aware-UTC normalization it was written for.

## Direct coverage of the new aging default
Review found no test pinned the new default: `test_aging_alerts_work_for_small_samples` passes `aging_threshold` explicitly, the #1444 pin passes 14.0 explicitly, and `test_velocity_with_timestamps` (default analyzer, items at 5, 3 and 31 days) passes under both rules because v4.0.0's 2.0 x stage-average threshold there is 26 days.
- Added `tests/test_1422_analytics_correctness.py::test_default_aging_threshold_is_an_exclusive_30_day_limit`: a default-constructed `PipelineAnalyzer` with items at 29.9, 30.0 and 30.1 days flags only the 30.1-day item. The boundary is exclusive because `pipeline.py` flags `d > self._aging_threshold`, so exactly 30.0 is not flagged. On v4.0.0 the same items give a 60-day threshold (2.0 x 30.0 average) and nothing is flagged: fails with `assert [] == ['over']`. At the tip: passes.
- Tightened `tests/test_analytics_pipeline.py::test_velocity_with_timestamps` to also assert the 5-day and 3-day items are not flagged. This holds under both rules (passes on v4.0.0 and at the tip), so it is a control, not a defect test.
- Analytics, datetime and temporal suites on the merged tree: 253 passed, 1 skipped.

## Pre-mortem
1. Tiger. Severity: P1. Modifying a develop test weakens it. Mitigation: one-line pin with (a)/(b)/(c) evidence above; disclosed here, in the PR body and in the BREAKING entry's Migration line.
2. Tiger. Severity: P2. A Migration line missing for one of the seven changes. Mitigation: each bullet has its own Migration.
3. Paper Tiger. Severity: P2. Develop's #1444 pipeline changes interact with the day threshold beyond the one test. Mitigation: analytics suites plus `test_analytics_datetime.py` and `test_1780_temporal_boundaries.py` on the merged tree: 252 passed, 1 skipped.
4. Tiger. Severity: P1. Wrong ref or non-fast-forward push. Mitigation: explicit refspec, no force, remote head checked to advance from `d1800887`.

## Peer review (Junior: shelves, gates)
- Shelves: SU-1 (insufficient data is an explicit grade, not a Poor/neutral number; invalid weights and pricing answers raise); SU-2 (`StageRatio` names what is computed).
- Gate 1 (syntax): one test line changed; the file imports and runs (29 passed).
- Gate 2 (tests): on the merged tree with the pin, `tests/test_1422_analytics_correctness.py`, the eleven `tests/test_analytics_*`/connector files, `tests/test_analytics_datetime.py` and `tests/test_1780_temporal_boundaries.py`: 252 passed, 1 skipped (the live GA smoke test).

## Lead review (adversarial)
Phase A coherence: CHANGELOG bullets, PR body table and regression rows describe the same seven changes; the develop-test pin is consistent with the new aging semantics.
Phase B verification (red/green): `tests/test_1422_analytics_correctness.py` copied into a detached v4.0.0 worktree (`9c3463b1`) -> 25 failed (e.g. `'Poor' == 'Insufficient data'`, `[] == ['overdue']`, `DID NOT RAISE ValueError` for invalid weights and inconsistent pricing, tier boundary mismatches, `PipelineReport` has no `stage_ratios`). On the merged branch -> 25 passed. Import paths were checked to resolve to the worktree package.

## Findings
| ID | Priority | Description | Resolution |
|----|----------|-------------|------------|
| F1 | P1 | Semantic conflict with develop's #1444 test (3 failures on the merged tree) | develop merged `0937d390`; test call pinned to `aging_threshold=14.0` with (a)/(b)/(c) evidence |
| F2 | P2 | CHANGELOG bullets only in the PR body | restored under `[4.1.0] ### BREAKING`, each with Migration |
| F3 | P3 | Tip lacked review trailers | this commit carries them |

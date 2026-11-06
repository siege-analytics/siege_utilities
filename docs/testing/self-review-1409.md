# Self-review: crosswalk weighting, missing values and rates (#1409, PR #1779)

Scope of this artifact: the PR as a whole at its current head. The code commits up to b71f1069 were reviewed independently at that exact head by the external reviewer (ticket #1409, review comment 6257195272). Since then the branch gained a develop sync, the `[4.1.0]` release notes and this file, and a final commit (on top of the sync merge 5495d540) that changes library code: AREA weighting now rejects missing row weights and `weighted_mean` excludes missing values from its denominator. That final commit has not been through the external review; it needs a fresh exact-head review.

Review-Tier: B for the final commit (library behavior change with tests and release notes); A for the earlier process commits.

The PR carries a BREAKING classification (AREA, POPULATION and HOUSING reject missing row weights, POPULATION and HOUSING require their weight columns, and `weighted_mean` changes its denominator). The operator decided to ship it in 4.1.0 as BREAKING (option A) and directed that the two follow-ups the earlier body left open be fixed in this PR instead of ticketed.

## Assumptions

- Goal source: ticket #1409. Crosswalk processing must keep NaN for all-missing extensive targets, use the real population and housing weights, divide EQUAL splits correctly, and let `normalize_to_year` and `get_longitudinal_data` identify rates.
- Roles: author is the PR owner; the independent reviewer is the cross-family hostile reviewer who recorded the head b71f1069 verdict on the ticket.
- The code diff against `origin/develop` touches `crosswalk_processor.py`, `longitudinal_data.py`, `docs/CENSUS_DATA_GUIDE.md`, `tests/test_crosswalk_weights_1409.py` and `CHANGELOG.md`. The final commit edits `crosswalk_processor.py` only for library code: a shared `_reject_missing_weights` helper used by the AREA and POPULATION/HOUSING paths, and the `weighted_mean` denominator.
- The body claims were checked against the code at this head: `sum(min_count=1)` for extensive sums (`crosswalk_processor.py` lines 441 and 446); `<col>_coverage` output columns (lines 480 and 490); `WeightMethod(value)` conversion (line 219); `population_weight` and `housing_weight` selection (line 283); AREA and POPULATION/HOUSING missing-weight rejection (lines 329 and 339, helper at 502); the `weighted_mean` denominator from the column's covered weight (lines 473-474); `intensive_columns` forwarded as `intensive_variables` in `longitudinal_data.py` (lines 307 and 904).
- Release convention: user-visible notes belong in `[4.1.0]`. This commit moves the BREAKING Changed entry and the Fixed entry verbatim, keeping their migration detail. No other `[Unreleased]` entry was touched.
- Pre-author-inventory: NONE. Trivial-against-state: the commit moves existing text between two sections of one file, checked with `git diff origin/develop -- CHANGELOG.md`, which shows only #1409 additions and no removed lines after the sync.

## Peer review

Gate evidence, all observed in this work cycle:

- Local pytest on the tree with the final commit, run from the `tests` directory with Python 3.11 and the repository pyproject: `python -m pytest test_crosswalk_weights_1409.py test_geo_crosswalk_crosswalk_processor_errors.py test_longitudinal_aligner.py` -> 65 passed in 0.73s (the 61 earlier cases plus 4 new ones). Other files that call the crosswalk processor, `test_batch1_1373.py test_crosswalk.py test_final_hardening_consensus.py test_round5_class_hardening.py test_round6_class_hardening.py test_longitudinal_normalization_consensus.py` -> 164 passed, 8 warnings in 3.32s. The warnings are existing geometry and scipy notices.
- New and changed tests: `test_area_missing_row_weight_is_an_error_naming_source_and_target`, `test_area_unmatched_sources_keep_their_values_and_zero_weights_are_valid`, `test_weighted_mean_excludes_missing_values_from_the_denominator`, `test_weighted_mean_all_missing_target_is_nan_with_zero_coverage`, and the `weighted_mean` parameter of `test_extensive_sum_preserves_missing_and_sums_available_values`, whose expected partial-target value changes from 2.5 (the old diluted denominator) to 5.0. The unmatched/zero-weight test and the all-missing test pin behavior that already held; they pass before and after the fix and are guards, not fix evidence.
- Hosted CI at the pushed head is recorded in the PR body once it finishes.
- Known baseline: develop CI has failures from the DuckDB 2.0 break (about 30) until the #1863 pin successor lands. They are not attributable to this PR and were not chased.

## Test plan

- Confirm exact-head CI at the pushed head reports success other than the known DuckDB 2.0 failures on develop.
- Confirm `CHANGELOG.md` has both #1409 entries under `[4.1.0]` and none under `[Unreleased]`.
- Request a fresh exact-head review: the earlier result is void once the head moves, and the code diff is unchanged.
- Obtain the operator's release sign-off for the BREAKING classification before tagging.

## Ticket-fitness exemption

Governing ticket: #1409 (the #1398 epic is context only and is not a governing ticket).

- **Reason:** #1409 predates the canonical ticket template (Context / Goal / Acceptance, a design link and Assumptions). It uses the earlier hostile-review Problem / Done-when / Falsifier narrative, so the ticket-fitness check reports a structure gap. The exemption is for ticket structure only.
- **Evidence:** the Problem (all-missing extensive targets converted to zero, silent area weights for POPULATION and HOUSING, inflated EQUAL splits, no rate handling in `normalize_to_year`), the evidence and the Done-when live in the ticket, https://github.com/siege-analytics/siege_utilities/issues/1409, and in the PR description. The reviewer verdict is https://github.com/siege-analytics/siege_utilities/issues/1409#issuecomment-6257195272.
- **Falsification:** revert the implementation (`crosswalk_processor.py` and `longitudinal_data.py` changes of this PR); `tests/test_crosswalk_weights_1409.py::test_extensive_sum_preserves_missing_and_sums_available_values` goes red because an all-missing extensive sum becomes 0 instead of NaN. Observed revert run: with `crosswalk_processor.py` and `longitudinal_data.py` restored to origin/develop (`git checkout origin/develop -- siege_utilities/geo/crosswalk/crosswalk_processor.py siege_utilities/geo/timeseries/longitudinal_data.py`), `python -m pytest test_crosswalk_weights_1409.py::test_extensive_sum_preserves_missing_and_sums_available_values -q`, run from the tests directory, gave 2 failed in 0.41s (the sum-5.0 and weighted_mean-2.5 parameters, AssertionError). After `git checkout HEAD --` of the files the command gave 2 passed in 0.37s and the three-file set gave 61 passed (that run was at the earlier, process-only head).
- **Falsification for the final commit (AREA weights and `weighted_mean`):** with only `siege_utilities/geo/crosswalk/crosswalk_processor.py` restored to the sync merge 5495d540 (`git checkout HEAD -- siege_utilities/geo/crosswalk/crosswalk_processor.py`, before the final commit existed) and the new tests in place, `python -m pytest test_crosswalk_weights_1409.py -q`, run from the tests directory, gave 3 failed, 33 passed in 0.67s. The failures were `test_extensive_sum_preserves_missing_and_sums_available_values[weighted_mean-5.0]`, `test_area_missing_row_weight_is_an_error_naming_source_and_target` and `test_weighted_mean_excludes_missing_values_from_the_denominator`; the last one failed with the obtained 2.0 against the expected 8.0 (the missing value's weight was still in the denominator). After restoring the fixed file the three-file set gave 65 passed in 0.68s.

## Lead review

The final commit changes behavior on purpose, under the operator's decision for option A (BREAKING) with the two follow-ups fixed in this PR. Callers whose crosswalk has a matched row with a missing `area_weight` now get a `ValueError` naming the source and target instead of full-value allocation, and `weighted_mean` results rise where values were missing. Intensive-only calls under the default AREA method are held to the same missing-weight rule, because the weight check runs before the value columns are split; this is stated in the `[4.1.0]` entry. The change reverts with one commit. A fresh exact-head review is needed before merge; any earlier verdict is void once the head moves.

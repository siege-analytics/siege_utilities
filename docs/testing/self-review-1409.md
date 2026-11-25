# Self-review: crosswalk weighting, missing values and rates (#1409, PR #1779)

Scope of this artifact: the PR as a whole at its current head. The code commits up to b71f1069 were reviewed at that head (ticket #1409, review comment 6257195272, headed CHANGES REQUESTED for release and process items only). The branch then gained a develop sync, the release notes, this file and a commit that made AREA reject missing row weights and `weighted_mean` exclude missing values from its denominator (head 34d7b1a1). An independent review of 34d7b1a1 failed on the `<col>_coverage` outputs and asked for two rulings. The latest round (see "Develop sync cef92084, the #1945 rule and coverage") merges develop, implements the operator's #1945 decision and fixes the coverage outputs.

Review-Tier: C. This PR changes library code in `siege_utilities/geo/crosswalk/` and `siege_utilities/geo/timeseries/`.

The PR carries a BREAKING classification: AREA, POPULATION and HOUSING reject missing row weights, POPULATION and HOUSING require their weight columns, `weighted_mean` changes its denominator, an extensive total with a missing contributor is NaN, and transformed frames gain `<col>_coverage` columns whose names are reserved. The entry sits under `### BREAKING` in `[Unreleased]`; 5.0.0 and 6.0.0 are released and do not contain it.

## Assumptions

- Goal source: ticket #1409. Crosswalk processing must keep NaN for all-missing extensive targets, use the real population and housing weights, divide EQUAL splits correctly, and let `normalize_to_year` and `get_longitudinal_data` identify rates.
- Missing-contributor rule: the operator's decision on #1945 (https://github.com/siege-analytics/siege_utilities/issues/1945#issuecomment-7151906694). For extensive totals, a target with any missing contributor is missing (NaN), on the crosswalk path and on the areal-interpolation path, so they agree.
- Roles: author is the PR owner; the independent reviewer is a separate same-family reviewer whose review of 34d7b1a1 is summarized under "Independent review".
- The code diff against `origin/develop` touches `crosswalk_processor.py`, `longitudinal_data.py`, `docs/CENSUS_DATA_GUIDE.md`, `tests/test_crosswalk_weights_1409.py`, `tests/test_crosswalk_areal_missing_and_coverage.py`, this file and `CHANGELOG.md`.
- Release convention: user-visible notes belong under `[Unreleased]`. The #1409 entry is one `### BREAKING` entry with a Migration line.
- Pre-author-inventory: NONE.

## Peer review

Gate evidence for the earlier commits (kept for the record):

- At 34d7b1a1: `test_crosswalk_weights_1409.py`, `test_geo_crosswalk_crosswalk_processor_errors.py` and `test_longitudinal_aligner.py` gave 65 passed; the other files that call the crosswalk processor gave 164 passed.
- The AREA missing-weight and `weighted_mean` red/green runs are under "Falsification for the AREA and weighted_mean commit" below.

Gate evidence for the latest round is in "Develop sync cef92084, the #1945 rule and coverage".

## Test plan

- Confirm exact-head CI at the pushed head reports success.
- Confirm `CHANGELOG.md` has the #1409 entry under `[Unreleased]` / `### BREAKING` and none under a released section.
- Request a delta review of the latest round against 34d7b1a1; any earlier verdict is void once the head moves.

## Pre-flight (develop 71f02b0b)

Develop was merged additively. The only conflict was `CHANGELOG.md`; every develop line was kept. At that time no develop change touched `siege_utilities/geo/crosswalk/` or `siege_utilities/geo/timeseries/`. The former `### Changed` and `### Fixed` notes were merged into one `### BREAKING` entry with a Migration line.

## Develop sync cef92084, the #1945 rule and coverage

- **Develop merge.** Develop `cef92084` merged with no conflicts. Develop's #1437 guard now touches `siege_utilities/geo/timeseries/longitudinal_data.py` (`_raise_for_ct_2022_crossing` at the top of the multi-year normalization) and does not interact with this PR. Because the merge was clean, the #1409 entry would have landed in the released 5.0.0 section; the sync commit moves it, unchanged, to the end of `[Unreleased]` / `### BREAKING`. Every other file equals the plain automatic merge.
- **#1945 rule, crosswalk path.** With `aggregation_func='sum'`, a target is NaN when any contributing row (a matched row with a nonzero weight) has a missing value. Before, `sum(min_count=1)` returned the sum of the remaining values (100 in #1945's example). A zero-weight row with a missing value is not a contributor. `weighted_mean`, `mean` and intensive columns still average the values that are present. The target's `<col>_coverage` still reports the share of contribution weight that had data.
- **#1945 rule, areal path.** `interpolate_areal` already returned NaN for an extensive target that overlaps a source with a missing value; it is unchanged and now pinned next to the crosswalk path on the same geography and data.
- **Coverage names reserved.** `transform` raises `ValueError` when an input column already has the name `<col>_coverage` of a value column `<col>`, instead of overwriting it. `LongitudinalAligner.align` checks the same before its first step, so the per-step areal fallback cannot hide the error.
- **Coverage carried through a chain.** `transform` and `apply_crosswalk` accept `carried_coverage`, the coverage columns of an earlier step. They are not transformed as values, and each source row's contribution to the new coverage is scaled by its carried coverage. `LongitudinalAligner.align` passes them on every step after a crosswalk step. A 2000 to 2020 chain no longer returns `pop_coverage_coverage`, and a target fed by a half-missing step-1 target reports coverage 0.5 instead of 1.0.
- **Coverage in the areal fallback.** `_apply_areal_interpolation` averages carried coverage columns by area like intensive columns instead of splitting them as counts. With complete data the fallback reports coverage 1.0 instead of 0.5.
- **Tests.** `tests/test_crosswalk_weights_1409.py` gains nine tests, and its sum/weighted_mean test is renamed `test_extensive_missing_contributors_by_aggregation`: its `sum` case now expects NaN for the partially missing target, which is the #1945 decision. `tests/test_crosswalk_areal_missing_and_coverage.py` adds six tests through `LongitudinalAligner` and `interpolate_areal` on a three-vintage geography. Against the 34d7b1a1 library code these 16 new or changed tests give 12 failed and 4 passed; the four passes (a split of a missing source, a zero-weight missing row, intensive averaging, a coverage-named column without its base column) are guards. All pass at this head.

## Carried coverage with weighted_mean and chained normalize_to_year (after 577cb10d)

- **weighted_mean.** With `carried_coverage`, `weighted_mean` divided by the covered weight, which is the weight scaled by the carried coverage, so a value of 10 at coverage 0.5 came out as 20. Carried coverage says how complete a value is, not how much weight it has. The denominator is now the weight of the rows whose value is present, kept separate from the covered weight used for coverage.
- **Chained normalize_to_year.** `normalize_to_year` supports 2000 to 2010 and 2010 to 2020, so 2000 to 2020 takes two calls. The second call received the first call's `<col>_coverage` columns, refused them as reserved names and had no way to accept them, where develop returned values. `normalize_to_year` now accepts `carried_coverage` and forwards it.
- **Docs.** The CHANGELOG and the census data guide tell callers chaining their own calls to pass the coverage columns in `carried_coverage` rather than rename them, since a renamed coverage column is summed as a count; renaming is only for a caller's own data column with a reserved name.
- **Tests.** `tests/test_crosswalk_carried_coverage_chains.py`, seven tests: 6 failed and 1 passed at 577cb10d, 7 passed with the fix, which is the reviewer's suggested patch applied unchanged.

## Ticket-fitness exemption

Governing ticket: #1409 (the #1398 epic is context only and is not a governing ticket).

- **Reason:** #1409 predates the canonical ticket template (Context / Goal / Acceptance, a design link and Assumptions). It uses the earlier hostile-review Problem / Done-when / Falsifier narrative, so the ticket-fitness check reports a structure gap. The exemption is for ticket structure only.
- **Evidence:** the Problem (all-missing extensive targets converted to zero, silent area weights for POPULATION and HOUSING, inflated EQUAL splits, no rate handling in `normalize_to_year`), the evidence and the Done-when live in the ticket, https://github.com/siege-analytics/siege_utilities/issues/1409, and in the PR description.
- **Falsification:** revert the implementation (`crosswalk_processor.py` and `longitudinal_data.py` changes of this PR); `tests/test_crosswalk_weights_1409.py::test_extensive_missing_contributors_by_aggregation` (named `test_extensive_sum_preserves_missing_and_sums_available_values` before the latest round) goes red because an all-missing extensive sum becomes 0 instead of NaN. Observed revert run at an earlier head: with both files restored to origin/develop, the test gave 2 failed (AssertionError); with the files restored to the PR versions it gave 2 passed.
- **Falsification for the AREA and weighted_mean commit:** with only `crosswalk_processor.py` restored to the sync merge 5495d540 and the new tests in place, `test_crosswalk_weights_1409.py` gave 3 failed, 33 passed; `test_weighted_mean_excludes_missing_values_from_the_denominator` failed with 2.0 against the expected 8.0. With the fixed file the three-file set gave 65 passed.

## Lead review

The latest round changes behavior on purpose, under the operator's #1945 decision: an extensive total with a missing contributor is now NaN on the crosswalk path, as it already was on the areal path. The coverage changes fix outputs this PR introduced and do not change any data value, except that a caller column with a reserved coverage name is now refused instead of silently overwritten; that refusal is stated in the CHANGELOG with its migration. The change reverts with the commits of this round.

## Findings

| ID | Priority | Description | Resolution |
|----|----------|-------------|------------|
| F1 | P1 | `<col>_coverage` shared the value-column namespace: a chained alignment re-transformed it as a count and reported coverage 1.0 for a half-missing target, the areal fallback split it by area, and a caller's own `<col>_coverage` column was overwritten | fixed |
| F2 | P1 | The crosswalk path summed the remaining values of a target with a missing contributor, while the areal path returned NaN; the #1945 decision makes both NaN | fixed |
| F3 | P2 | The #1409 CHANGELOG entry would have merged into the released 5.0.0 section; moved to `[Unreleased]` / `### BREAKING` and states the #1945 rule | fixed |
| F4 | P3 | This artifact named 4.1.0, a cross-family reviewer, a DuckDB 2.0 CI baseline and no develop change to `geo/timeseries/`, which no longer hold | fixed |
| F5 | P1 | `weighted_mean` with `carried_coverage` divided by weight times coverage, doubling a value carried at coverage 0.5 | fixed |
| F6 | P1 | A chained `normalize_to_year` call refused the first call's coverage columns and could not accept them as `carried_coverage`, where develop returned values | fixed |

## Independent review

Independent review of 34d7b1a1: FAIL on the `<col>_coverage` outputs (F1), with rulings asked on #1945 and on the release section. #1945 was decided by the operator (option A) and the entry is under `[Unreleased]`. 577cb10d addressed F1 to F4.

Independent review of 577cb10d: changes requested on two items, F5 and F6; everything from the previous round was verified fixed. This head applies the reviewer's suggested patch and tests unchanged; a delta review of this head is pending, not a pass.

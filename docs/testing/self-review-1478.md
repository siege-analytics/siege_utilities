# Self-review: survey inference with weighted data (#1478, PR #1732)

Scope of this artifact: the PR as a whole at its code head b7e92bb9, plus the later commits that sync with develop, add this file and fix the weight-dtype validation. The 71f02b0b sync changed `CHANGELOG.md` conflict handling and this document and no library code; the fbb280c7 sync changes `siege_utilities/survey/crosstab.py` (see "Sync with develop fbb280c7").

Review-Tier: C. This PR changes library code in `siege_utilities/survey/`, and its sync and fix commits carry the `Review-Tier: C` trailer. The code was reviewed independently at earlier heads (see "Independent review").

## Assumptions

- Goal source: ticket #1478. Survey inference must use effective sample sizes and unweighted respondent counts, keep the full top-N denominator, and use weighted means and standard errors for MEAN_SCALE.
- Roles: author is the PR owner; the independent reviewer is the reviewer whose reviews of `a2315d1a`, `f088bc3d` and `7ff5e25f` are summarized under "Independent review".
- The code diff against `origin/develop` after the sync touches `siege_utilities/survey/crosstab.py`, `models.py`, `significance.py`, `docs/source/packages/survey.rst`, two survey notebooks, five survey test files (including `tests/test_survey_weight_dtypes.py` from the fbb280c7 sync) and `CHANGELOG.md`.
- The #1478 note sits in `CHANGELOG.md` under `### BREAKING` in `[Unreleased]` (see "Sync with develop fbb280c7"). It began under `[4.1.0]` Fixed; at the 71f02b0b sync the only conflict with develop was in that section, settled by keeping the #1478 entry and every develop entry.
- Pre-author-inventory: NONE. Trivial-against-state: `git diff origin/develop -- CHANGELOG.md` shows only the #1478 entry as an addition after the sync.

## Peer review

Gate evidence, all observed in this work cycle:

- Local pytest on the tree after the sync, run from the `tests` directory with the pyenv Python 3.11 and the repository pyproject: `python -m pytest test_survey_significance_weighting.py test_survey_significance.py test_survey_crosstab.py` -> 48 passed in 1.42s.
- Hosted CI at the pushed head is recorded in the PR body once it finishes. The CI run cited in the earlier body belongs to an old head and is superseded.
- Known baseline: this branch and develop pin `duckdb>=0.7.0,<2.0`, so the DuckDB 2.0 failures no longer appear in CI. Exact-head CI at `f088bc3d` finished with 17 successful, 2 skipped and 1 neutral check runs and no failures.

## Test plan

- Confirm exact-head CI at the pushed head reports success.
- Confirm `CHANGELOG.md` has the #1478 entry under `[Unreleased]` / `### BREAKING` and none under a released section.
- Request a fresh exact-head review: any earlier result is void once the head moves, and the code diff against develop is unchanged.

## Pre-flight (develop 71f02b0b)

Develop was merged additively. The only conflict was `CHANGELOG.md`; every develop line was kept. Develop wins on any disagreement, and none exists: no develop change touches `siege_utilities/survey/`.

Classification: caller code that worked on v4.0.0 behaves differently (significance flags, shares and confidence intervals change for the same data; `build_chain` and `column_proportion_test` raise where they returned; `ci` is `None` where it was `0.0`). The #1478 entry therefore moved from `### Fixed` to `### BREAKING` in `[4.1.0]` with a Migration line, with no change in meaning. The entry sits at its own position in the BREAKING list, not at the top of Fixed, so that the other open PRs do not conflict with it in the merge queue. `git diff origin/develop -- CHANGELOG.md` shows 18 added lines and 0 removed lines. The PR body classification is updated to match.

Tests, run from the `tests` directory (Python 3.11, repository pyproject): `python -m pytest test_survey_significance_weighting.py test_survey_significance.py test_survey_crosstab.py -q` -> 48 passed in 1.38s. The library code is unchanged since the red/green run recorded in the Falsification entry below, which still applies to this head.

## Ticket-fitness exemption

Governing ticket: #1478 (the #1398 epic is context only and is not a governing ticket).

- **Reason:** #1478 predates the canonical ticket template (Context / Goal / Acceptance, a design link and Assumptions). It uses the earlier hostile-review Problem / Done-when / Falsifier narrative, so the ticket-fitness check reports a structure gap. The exemption is for ticket structure only.
- **Evidence:** the Problem (weighting making unchanged respondent data look significant, inflated top-N shares, unweighted scale means), the evidence and the Done-when live in the ticket, https://github.com/siege-analytics/siege_utilities/issues/1478, and in the PR description, https://github.com/siege-analytics/siege_utilities/pull/1732. The reviewer verdicts are recorded on the ticket thread and the PR conversation.
- **Falsification:** revert the implementation (`crosstab.py`, `models.py` and `significance.py` changes of this PR); `tests/test_survey_significance_weighting.py::test_issue_1_population_weight_scaling_preserves_empty_flags` goes red because scaling weights by 10000 again produces spurious significance letters. Observed revert run: with `siege_utilities/survey/crosstab.py`, `models.py` and `significance.py` restored to origin/develop (`git checkout origin/develop -- siege_utilities/survey/crosstab.py siege_utilities/survey/models.py siege_utilities/survey/significance.py`), `python -m pytest test_survey_significance_weighting.py::test_issue_1_population_weight_scaling_preserves_empty_flags -q`, run from the tests directory, gave 1 failed in 1.11s (AssertionError). After `git checkout HEAD --` of the files the command gave 1 passed in 1.16s, `test_survey_significance_weighting.py`, `test_survey_significance.py` and `test_survey_crosstab.py` gave 48 passed on the pushed head, and the worktree was clean. The latest commit of this PR is process-only.

## Lead review

The process-only commits (the 71f02b0b sync and this document) change no library behavior. The library change of this PR, including the fbb280c7 weight-validation fix, is the breaking change classified above. No claim in this artifact exceeds what was observed.

## Sync with develop fbb280c7

- **Develop merge.** No conflicts; `CHANGELOG.md` is the only file changed on both sides, and no develop commit since the merge base touches `siege_utilities/survey/`. Develop released the old `[4.1.0]` bucket as `[5.0.0] - 2026-11-20`, so the #1478 entry would have merged into a released section. It now sits under `### BREAKING` in `[Unreleased]`, reworded against 6.0.0, and states plainly that `chi_square_flag` tests unweighted respondent counts.
- **Weight dtypes.** `build_chain` ran `np.isfinite` on the caller's raw weight column. Decimal (from a database NUMERIC column), object-dtype floats and bool weights, all of which 6.0.0 accepted, raised a raw `TypeError` or `NotImplementedError`, and a `pd.NA` in a nullable column passed the finite check and its row was dropped silently. The column is now converted with `pd.to_numeric(...).astype("float64")` before the check: a non-numeric column raises `CrosstabInputError`, a missing weight is non-finite and raises `CrosstabInputError`, and Decimal, object, nullable and bool columns give the same table as float64.
- **Small effective n.** MEAN_SCALE now reports `ci=None` when the effective n is below 2. Between 1 and 2 the t critical value has fewer than one degree of freedom and the interval exploded (for example `2.28e64` for scores `[1, 5]` with weights `[100, 1]`). `test_weighted_small_effective_sample_without_scipy_refuses` now uses weights with an effective n of about 5, so it still exercises the SciPy refusal for an effective n below 30 that has an estimable interval. Its old weights gave an effective n of about 1.002, which the below-two rule makes not estimable before any critical value is needed; the weight change is a direct consequence of that rule and keeps the test's purpose.
- **Docs and notebooks.** `docs/source/packages/survey.rst` now states the below-two CI rule and the weight-column handling. Two notebook sentences this PR re-emits lost their typographic dashes (`03_polling_survey_analysis.ipynb`: a colon; `04_survey_full_showcase.ipynb`: "1-to-N").
- **Tests.** `tests/test_survey_weight_dtypes.py` (14 tests: Decimal, object, float32, nullable Float64 and int64 weights match float64; bool weights act as 0/1; NaN, `pd.NA` in Float64 and Int64, None, inf and text raise `CrosstabInputError`; two MEAN_SCALE cells with an effective n between 1 and 2 report `ci=None`). At the previous head `a2315d1a`: 8 failed, 6 passed. At `f088bc3d`: 14 passed, and the survey suites (`test_survey_weight_dtypes.py`, `test_survey_significance_weighting.py`, `test_survey_significance.py`, `test_survey_crosstab.py`, `test_survey_waves.py`) give 77 passed.

## Weight-column conversion fix (after `f088bc3d`)

- **Non-string column labels.** The conversion stored the float64 weights with `df.assign(**{weight_var: weights})`, which needs a string key. A frame with integer column labels (as read with `header=None`) and a weight column raised `TypeError: keywords must be strings`, where 6.0.0 and `a2315d1a` returned the table. The weights are now written with `df.copy()` and `df[weight_var] = weights`, so the caller's frame is still left unchanged.
- **Datetime, timedelta and complex weights.** `pd.to_numeric` turns datetime64 and timedelta64 columns into nanosecond counts, and `astype("float64")` drops the imaginary part of complex values, so such a weight column returned a table weighted by those numbers, where 6.0.0 raised. Only object columns and real numeric or bool columns are now converted; any other dtype raises `CrosstabInputError` ("must be numeric"), which matches the CHANGELOG and the survey docs. Numeric strings stay accepted, and a categorical column of numbers is rejected, as on develop.
- **Tests.** Six tests in `tests/test_survey_weight_dtypes.py`: integer column labels give the same cells as string labels for a weighted cross-tab and the same mean and interval for a weighted MEAN_SCALE; datetime64, timedelta64 and complex weights raise `CrosstabInputError`; the caller's Decimal weight column is unchanged after `build_chain`. Before the fix: 5 failed, 1 passed (the unchanged-column case). With the fix: 6 passed.

## Weight and metric column fix (after `7ff5e25f`)

- **Arrow-backed bool weights.** The conversion accepted object columns and columns where `is_numeric_dtype` is true, which is false for `bool[pyarrow]`, so those weights raised "must be numeric" where 6.0.0 and `f088bc3d` returned the table. Bool columns of any backing are now accepted; categorical columns are still rejected.
- **Complex values in an object column.** An object column of complex values was still converted, dropping the imaginary part, where 6.0.0 raised. Such values now raise `CrosstabInputError`.
- **Decimal metric columns.** A Decimal metric with Decimal, int, Int64 or bool weights raised `TypeError: unsupported operand type(s) for *: 'decimal.Decimal' and 'float'` in the six count-based table types (CROSS_TAB, SINGLE_RESPONSE, MULTIPLE_RESPONSE, LONGITUDINAL, RANKING, BANNER), where 6.0.0 returned the table. That is the database NUMERIC case the conversion was meant for; it now works, and the caller's Decimal column is unchanged.
- **Rulings on three further cases.** Fraction weights are accepted, as in 6.0.0. When the weight column is also a break or row variable, its cell keys keep their 6.0.0 form (`w=1`, `w=True`) instead of the converted floats. A weight column labelled `0`, `''` or `False` is applied to counts and bases, consistently with the effective n. A weight too large for float64 raises `CrosstabInputError` instead of a raw `OverflowError`.
- **Tests.** `tests/test_survey_weight_and_metric_columns.py`, 37 tests: 33 failed and 4 passed at `7ff5e25f` (the four are guards), 37 passed with the fix. The fix is the reviewer's suggested patch, applied unchanged.

## Findings

| ID | Priority | Description | Resolution |
|----|----------|-------------|------------|
| F1 | P1 | Weight validation crashed on Decimal, object-dtype and bool weight columns that 6.0.0 accepted, and let a nullable `pd.NA` weight pass; fixed by converting the column to float64 before the finite and nonnegative check | fixed |
| F2 | P2 | MEAN_SCALE reported exploding confidence intervals for an effective n between 1 and 2; now `ci=None` below 2 | fixed |
| F3 | P2 | The #1478 CHANGELOG entry would have merged into the released 5.0.0 section; moved to `[Unreleased]` / `### BREAKING` | fixed |
| F4 | P3 | This artifact contradicted itself on the CHANGELOG section and on "No behavior change" | fixed |
| F5 | P1 | The float64 weight conversion raised a raw `TypeError` for frames with integer column labels, which 6.0.0 accepted, and turned datetime, timedelta and complex weight columns into numbers instead of raising `CrosstabInputError`; the weights are now assigned by item and only object, real numeric and bool columns are converted | fixed |
| F6 | P3 | This artifact named Review-Tier A, a cross-family reviewer and a DuckDB 2.0 CI baseline that no longer apply | fixed |
| F7 | P1 | Arrow-backed bool weight columns raised "must be numeric" after the F5 fix, where 6.0.0 accepted them | fixed |
| F8 | P1 | Complex values in an object weight column were converted with the imaginary part dropped, where 6.0.0 raised | fixed |
| F9 | P1 | A Decimal metric column with Decimal, int, Int64 or bool weights raised a raw TypeError in six table types, where 6.0.0 returned the table | fixed |
| F10 | P2 | Fraction weights, cell keys of a weight column used as a break or row variable, falsy weight-column labels and float64 overflow differed from 6.0.0 or raised raw errors | fixed |

## Independent review

Independent review of `a2315d1a`: FAIL, recorded at https://github.com/siege-analytics/siege_utilities/pull/1732#issuecomment-7119480819 (weight-column dtypes; CHANGELOG placement). `f088bc3d` addressed both.

Independent review of `f088bc3d`: FAIL on one finding, the weight-column conversion (F5 above), recorded at https://github.com/siege-analytics/siege_utilities/pull/1732#issuecomment-7150907037. The reviewer found everything else in that delta correct and exact-head CI green. `7ff5e25f` applied the suggested fix.

Independent review of `7ff5e25f`: changes requested on F7 to F9, with F10 ruled in scope, recorded at https://github.com/siege-analytics/siege_utilities/pull/1732#issuecomment-7152068648. This head applies the reviewer's suggested patch unchanged and its 37 tests; a delta re-review of this head is pending, not a pass.

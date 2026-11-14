# Self-review: survey inference with weighted data (#1478, PR #1732)

Scope of this artifact: the PR as a whole at its code head b7e92bb9, plus the process-only commit that syncs with develop and adds this file. The process commit changes `CHANGELOG.md` conflict handling and this document and no library code.

Review-Tier: A for the process commit (documentation only). The code commits under review were reviewed independently at an earlier head by the external reviewer.

## Assumptions

- Goal source: ticket #1478. Survey inference must use effective sample sizes and unweighted respondent counts, keep the full top-N denominator, and use weighted means and standard errors for MEAN_SCALE.
- Roles: author is the PR owner; the independent reviewer is the cross-family hostile reviewer who recorded the earlier approval on the ticket.
- The code diff against `origin/develop` after the sync touches `siege_utilities/survey/crosstab.py`, `models.py`, `significance.py`, `docs/source/packages/survey.rst`, two survey notebooks, four survey test files and `CHANGELOG.md`. This commit adds no library code.
- The #1478 note already sits in `CHANGELOG.md` under `[4.1.0]` Fixed. The only conflict with develop was in that section; it was settled by keeping the #1478 entry and every develop entry, with no wording changed.
- Pre-author-inventory: NONE. Trivial-against-state: `git diff origin/develop -- CHANGELOG.md` shows only the #1478 entry as an addition after the sync.

## Peer review

Gate evidence, all observed in this work cycle:

- Local pytest on the tree after the sync, run from the `tests` directory with the pyenv Python 3.11 and the repository pyproject: `python -m pytest test_survey_significance_weighting.py test_survey_significance.py test_survey_crosstab.py` -> 48 passed in 1.42s.
- Hosted CI at the pushed head is recorded in the PR body once it finishes. The CI run cited in the earlier body belongs to an old head and is superseded.
- Known baseline: develop CI has failures from the DuckDB 2.0 break (about 30) until the #1863 pin successor lands. They are not attributable to this PR and were not chased.

## Test plan

- Confirm exact-head CI at the pushed head reports success other than the known DuckDB 2.0 failures on develop.
- Confirm `CHANGELOG.md` has the #1478 entry under `[4.1.0]` and none under `[Unreleased]`.
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

The change is additive and reverts with one commit. No behavior change. No claim in this artifact exceeds what was observed.

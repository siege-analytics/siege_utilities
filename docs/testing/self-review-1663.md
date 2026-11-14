# Self-review: engines notebook parity claim (#1663, PR #1781)

Scope of this artifact: the PR as a whole at its code head a8788825, plus the process-only commit that syncs with develop, moves the release note into `[4.1.0]` and adds this file. The process commit changes `CHANGELOG.md` and this document and no library code or notebook content. The PR body was also refreshed.

Review-Tier: A for the process commit (documentation and release notes only). The code commits under review were reviewed independently at exact head a8788825 by the external reviewer (ticket #1663, review comment 6257235814).

## Assumptions

- Goal source: ticket #1663. The engines/01 notebook must teach result parity using different query implementations for pandas and DuckDB, not a constructor-only swap, and its synthetic data description must match the generator (five TX counties).
- Roles: author is the PR owner; the independent reviewer is the cross-family hostile reviewer who recorded the head a8788825 verdict on the ticket.
- The code diff against `origin/develop` after the sync is `notebooks/engines/01_multi_engine_dataframes.ipynb`, `tests/test_1663_engines_notebook_truth.py` and `CHANGELOG.md`. This commit adds no notebook or library change.
- Release convention: user-visible notes belong in `[4.1.0]`. This commit moves the #1663 entry verbatim. No other `[Unreleased]` entry was touched. The neighboring engines notebook ticket (#1664) owns the separate engines/02 parity claim; nothing here closes it.
- Pre-author-inventory: NONE. Trivial-against-state: `git diff origin/develop -- CHANGELOG.md` shows only the #1663 entry as an addition after the sync.

## Peer review

Gate evidence, all observed in this work cycle:

- Local pytest on the tree after the sync, run from the `tests` directory with the pyenv Python 3.11 and the repository pyproject: `python -m pytest test_1663_engines_notebook_truth.py` -> 3 passed in 1.88s (the three content assertions).
- Hosted CI at the pushed head is recorded in the PR body once it finishes. The run cited in the earlier body belongs to an old head and is superseded.
- Known baseline: develop CI has failures from the DuckDB 2.0 break (about 30) until the #1863 pin successor lands. They are not attributable to this PR and were not chased.

## Test plan

- Confirm exact-head CI at the pushed head reports success other than the known DuckDB 2.0 failures on develop, including the headless notebook execution.
- Confirm `CHANGELOG.md` has the #1663 entry under `[4.1.0]` and none under `[Unreleased]`.
- Request a fresh exact-head review: any earlier result is void once the head moves, and the code diff against develop is unchanged.

## Pre-flight (develop 71f02b0b)

Develop was merged additively. The only conflict was `CHANGELOG.md`; every develop line was kept. Develop wins on any disagreement, and none exists: no develop change touches `notebooks/engines/`.

Classification: this PR changes a notebook's prose and its test only, so no caller code that worked on v4.0.0 behaves differently; it is not BREAKING and the entry stays under `### Fixed` in `[4.1.0]`. The entry now sits at its own position in that list, not at the top, so that the other open PRs do not conflict with it in the merge queue.

Tests, run from the `tests` directory (Python 3.11, repository pyproject): `python -m pytest test_1663_engines_notebook_truth.py -q` -> 3 passed in 2.00s. The notebook is unchanged since the red/green run recorded in the Falsification entry below, which still applies to this head.

## Ticket-fitness exemption

Governing ticket: #1663 (the #1398 epic is context only and is not a governing ticket).

- **Reason:** #1663 predates the canonical ticket template (Context / Goal / Acceptance, a design link and Assumptions). It uses the earlier hostile-review Problem / Done-when / Falsifier narrative, so the ticket-fitness check reports a structure gap. The exemption is for ticket structure only.
- **Evidence:** the Problem (the engines/01 notebook promising that swapping the constructor preserves query code while the pandas and DuckDB cells use different queries), the evidence and the Done-when live in the ticket, https://github.com/siege-analytics/siege_utilities/issues/1663, and in the PR description. The reviewer verdict is https://github.com/siege-analytics/siege_utilities/issues/1663#issuecomment-6257235814.
- **Falsification:** revert the implementation (the notebook edit of this PR); `tests/test_1663_engines_notebook_truth.py::test_teaching_claims_result_parity_with_different_queries` goes red because the notebook again promises a constructor-only swap. Observed revert run: with `notebooks/engines/01_multi_engine_dataframes.ipynb` restored to origin/develop (`git checkout origin/develop -- notebooks/engines/01_multi_engine_dataframes.ipynb`), `python -m pytest test_1663_engines_notebook_truth.py::test_teaching_claims_result_parity_with_different_queries -q`, run from the tests directory, gave 1 failed in 0.80s (AssertionError on the narrowed parity claim). After `git checkout HEAD --` of the notebook the command gave 1 passed in 0.76s, `test_1663_engines_notebook_truth.py` gave 3 passed on the pushed head, and the worktree was clean. The latest commit of this PR is process-only.

## Lead review

The change is additive and reverts with one commit. No behavior change. No claim in this artifact exceeds what was observed.

# Self-review: RDH compactness scoring and projection (#1467, PR #1792)

Scope of this artifact: the PR as a whole at its code head 567e743a, plus the process-only commit that syncs with develop, adds the release note to `CHANGELOG.md` under `[4.1.0]` and adds this file. The process commit changes `CHANGELOG.md` and this document and no library code. The PR body was also refreshed.

Review-Tier: A for the process commit (documentation and release notes only). The code commits under review were reviewed independently at an earlier head by the external reviewer.

## Assumptions

- Goal source: ticket #1467. RDH compactness calculations understated circle scores and disagreed between APIs; Reock must use the minimum bounding circle, projection must be a per-district local AEQD, and `compute_compactness` and `compare_plans` must share the scoring.
- Roles: author is the PR owner; the independent reviewer is the cross-family hostile reviewer who recorded the earlier approval on the ticket and PR.
- The code diff against `origin/develop` after the sync is `siege_utilities/geo/providers/redistricting_data_hub.py`, `tests/test_1467_rdh_compactness_projection.py` and `tests/test_redistricting_data_hub.py`, plus `CHANGELOG.md` from this commit. The connector files that appeared in the earlier branch diff belong to an unrelated change that is already on develop and no longer appear. This commit adds no library code.
- Release convention: user-visible notes belong in `CHANGELOG.md` under `[4.1.0]`. Before this commit the #1467 note existed only in the PR body block; this commit adds it to `CHANGELOG.md` verbatim from that block.
- Out of scope, inherited: the antimeridian handling in the compactness helpers is existing behavior and is not changed here.
- Pre-author-inventory: NONE. Trivial-against-state: after the sync, `git diff origin/develop -- CHANGELOG.md` shows only the #1467 entry as an addition.

## Peer review

Gate evidence, all observed in this work cycle:

- Local pytest on the tree after the sync, run from the `tests` directory with the pyenv Python 3.11 and the repository pyproject: `python -m pytest test_1467_rdh_compactness_projection.py test_redistricting_data_hub.py` -> 137 passed, 6 warnings in 1.90s. The warnings are a shapely deprecation notice for an existing `resolution` argument and an `RDHClient.__del__` message in the existing missing-requests test.
- Hosted CI at the pushed head is recorded in the PR body once it finishes.
- Known baseline: develop CI has failures from the DuckDB 2.0 break (about 30) until the #1863 pin successor lands. They are not attributable to this PR and were not chased.

## Test plan

- Confirm exact-head CI at the pushed head reports success other than the known DuckDB 2.0 failures on develop.
- Confirm `CHANGELOG.md` has the #1467 entry under `[4.1.0]` Fixed exactly once.
- Request a fresh exact-head review: any earlier result is void once the head moves, and the code diff against develop is unchanged.

## Ticket-fitness exemption

Governing ticket: #1467 (the #1398 epic is context only and is not a governing ticket).

- **Reason:** #1467 predates the canonical ticket template (Context / Goal / Acceptance, a design link and Assumptions). It uses the earlier hostile-review Problem / Done-when / Falsifier narrative, so the ticket-fitness check reports a structure gap. The exemption is for ticket structure only.
- **Evidence:** the Problem (RDH compactness scores understating circles and disagreeing between APIs), the evidence and the Done-when live in the ticket, https://github.com/siege-analytics/siege_utilities/issues/1467, and in the PR description, https://github.com/siege-analytics/siege_utilities/pull/1792. The reviewer verdicts are recorded on the ticket thread and the PR conversation.
- **Falsification:** revert the implementation (the `redistricting_data_hub.py` changes of this PR); `tests/test_1467_rdh_compactness_projection.py::test_reock_equilateral_triangle` goes red because the Reock score returns 0.315045 instead of 0.413497. Observed revert run: with `siege_utilities/geo/providers/redistricting_data_hub.py` restored to origin/develop (`git checkout origin/develop -- siege_utilities/geo/providers/redistricting_data_hub.py`), `python -m pytest test_1467_rdh_compactness_projection.py::test_reock_equilateral_triangle -q`, run from the tests directory, gave 1 failed, 1 warning in 0.50s (AssertionError on the Reock score). After `git checkout HEAD --` of the file the command gave 1 passed in 0.43s, `test_1467_rdh_compactness_projection.py` with `test_redistricting_data_hub.py` gave 137 passed (6 warnings) on the pushed head, and the worktree was clean. The latest commit of this PR is process-only.

## Lead review

The change is additive and reverts with one commit. No behavior change. No claim in this artifact exceeds what was observed.

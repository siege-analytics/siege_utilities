# Self-review: geocode validation across CRSs and the Null Island sentinel (#1459, PR #1773)

Scope of this artifact: the PR as a whole at its code head 402a74bc, plus the process-only commit that syncs with develop, restores the two release notes in `CHANGELOG.md` under `[4.1.0]` and adds this file. The process commit changes `CHANGELOG.md` and this document and no library code. The PR body was also rewritten to describe the final diff.

Review-Tier: A for the process commit (documentation and release notes only). The code commits under review were reviewed independently at exact head 402a74bc by the external reviewer (ticket #1459, review comment 6262494933).

## Assumptions

- Goal source: ticket #1459. Pandas geocode validation must accept NAD83 coordinates on both sides of the antimeridian, compare projected coordinates in CRS units, and reject the exact geographic `(0, 0)` failed-geocode sentinel; Spark validation must reject the same sentinel.
- Roles: author is the PR owner; the independent reviewer is the cross-family hostile reviewer who recorded the head 402a74bc verdict on the ticket.
- The code diff against `origin/develop` after the sync is `siege_utilities/geo/geocoding.py`, `siege_utilities/distributed/spark_utils.py`, `scripts/exception_contracts_allowlist.json` (one entry removed, the old `_get_crs_bounds` handler fingerprint), `tests/test_geocode_validation_crs.py` and `CHANGELOG.md`. This commit adds no library code.
- The body claims were checked against the code at this head: geographic CRSs use world ranges `(-90, 90, -180, 180)` (`_get_crs_bounds`, lines 486-489); projected CRSs use the area of use transformed with `always_xy=True` and `densify_pts=21` (lines 496-501); when bounds cannot be derived the function logs a warning and leaves projected bounds unbounded (lines 505-511); geographic `(0, 0)` is rejected in `_pandas_coordinate_mask` (lines 133-137); Spark `validate_geocode_data` and `mark_valid_geocode_data` exclude the exact `(0, 0)` pair (`spark_utils.py`).
- Release convention: user-visible notes belong in `CHANGELOG.md` under `[4.1.0]`, not only in a PR body. This commit restores both #1459 entries there, verbatim from the PR body's earlier release-note text. No other `[Unreleased]` entry was touched.
- Pre-author-inventory: NONE. Trivial-against-state: after the sync, `git diff origin/develop -- CHANGELOG.md` shows only the two #1459 additions.

## Peer review

Gate evidence, all observed in this work cycle:

- Local pytest on the merged tree, run from the `tests` directory with the pyenv Python 3.11 and the repository pyproject: `python -m pytest test_geocode_validation_crs.py test_geocode_validation_pandas.py` -> 45 passed in 12.00s, no skips.
- The Spark case ran for real: `test_geocode_validation_crs.py::test_spark_validators_reject_null_island PASSED` (1 passed, 44 deselected in 9.57s with `-k spark -v`). The run used a local Java runtime (JAVA_HOME from the sdkman install) and a real Spark session; no stub replaced Spark.
- Hosted CI at the pushed head, including the Spark path in a Java-capable lane, is recorded in the PR body once it finishes. The earlier exact-head run was cancelled, so a fresh run is required.
- Known baseline: develop CI has failures from the DuckDB 2.0 break (about 30) until the #1863 pin successor lands. They are not attributable to this PR and were not chased.

## Test plan

- Confirm exact-head CI at the pushed head runs to completion and reports success other than the known DuckDB 2.0 failures on develop.
- Confirm `CHANGELOG.md` has both #1459 entries under `[4.1.0]` Fixed and none under `[Unreleased]`.
- Request a fresh exact-head review: the earlier result is void once the head moves, and the code diff against develop is unchanged.

## Pre-flight (develop 71f02b0b)

Develop was merged additively. The only conflict was `CHANGELOG.md`; every develop line was kept. Develop wins on any disagreement, and none exists: no develop change touches `siege_utilities/geo/geocoding.py` or `siege_utilities/distributed/spark_utils.py`.

Classification: caller code that worked on v4.0.0 now sees different results, because which geocodes pass validation changes (the exact `(0, 0)` sentinel is rejected in pandas and Spark; coordinates v4.0.0 wrongly dropped are kept). The two #1459 entries are now one entry under `### BREAKING` in `[4.1.0]` with a Migration line, at its own position in the BREAKING list so it does not conflict with the other open PRs. `git diff origin/develop -- CHANGELOG.md` shows 16 added lines and 0 removed lines. The PR body classification is updated to match.

Tests, run from the `tests` directory (Python 3.11, repository pyproject): `python -m pytest test_geocode_validation_crs.py test_geocode_validation_pandas.py -q` -> 45 passed in 8.83s. The library code is unchanged since the red/green run recorded in the Falsification entry below, which still applies to this head.

## Ticket-fitness exemption

Governing ticket: #1459 (the #1398 epic is context only and is not a governing ticket).

- **Reason:** #1459 predates the canonical ticket template (Context / Goal / Acceptance, a design link and Assumptions). It uses the earlier hostile-review Problem / Done-when / Falsifier narrative, so the ticket-fitness check reports a structure gap. The exemption is for ticket structure only.
- **Evidence:** the Problem (NAD83 rows rejected across the antimeridian, projected coordinates compared with degree bounds, the (0, 0) sentinel accepted), the evidence and the Done-when live in the ticket, https://github.com/siege-analytics/siege_utilities/issues/1459, and in the PR description. The reviewer verdict is https://github.com/siege-analytics/siege_utilities/issues/1459#issuecomment-6262494933.
- **Falsification:** revert the implementation (`geocoding.py` and `spark_utils.py` changes of this PR); `tests/test_geocode_validation_crs.py::test_nad83_keeps_pacific_territories` goes red because NAD83 coordinates across the antimeridian are rejected again, and `tests/test_geocode_validation_crs.py::test_spark_validators_reject_null_island` goes red because the Spark validators accept (0, 0). Observed revert run: with `siege_utilities/geo/geocoding.py` and `siege_utilities/distributed/spark_utils.py` restored to origin/develop (`git checkout origin/develop -- siege_utilities/geo/geocoding.py siege_utilities/distributed/spark_utils.py`), `python -m pytest test_geocode_validation_crs.py::test_nad83_keeps_pacific_territories test_geocode_validation_crs.py::test_spark_validators_reject_null_island -q`, run from the tests directory with a local Java runtime and a real Spark session, gave 2 failed in 7.41s. After `git checkout HEAD --` of the files the command gave 2 passed in 6.74s, `test_geocode_validation_crs.py` with `test_geocode_validation_pandas.py` gave 45 passed on the pushed head, and the worktree was clean. The latest commit of this PR is process-only.

## Lead review

The change is additive and reverts with one commit. No behavior change. No claim in this artifact exceeds what was observed.

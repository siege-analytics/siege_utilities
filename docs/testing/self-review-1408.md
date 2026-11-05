# Self-review: longitudinal aligner raises instead of masking errors (#1408, PR #1775)

Scope of this artifact: the PR as a whole at its code head, plus the process-only commit that syncs with develop, moves the release note into `[4.1.0]` and adds this file. The process commit changes `CHANGELOG.md` and this document and no library code. The PR body was also corrected to describe the code at this head.

Review-Tier: A for the process commit (documentation and release notes only). The code commits under review were reviewed independently at exact head 0df1ff40 by the external reviewer (ticket #1408, review comment 6257020991).

## Assumptions

- Goal source: ticket #1408. `LongitudinalAligner.align` must not catch every crosswalk exception and silently fall back to areal interpolation, and must raise instead of returning partial data when the fallback also fails.
- Roles: author is the PR owner; the independent reviewer is the cross-family hostile reviewer who recorded the head 0df1ff40 verdict on the ticket.
- The code diff against `origin/develop` touches the aligner, the crosswalk client and processor, the crosswalk package export, `scripts/exception_contracts_allowlist.json` (two entries removed), five test files and `CHANGELOG.md`. This commit adds no library code.
- The body claims were checked against the diff: `CrosswalkUnavailable(ValueError)` is defined in `crosswalk_client.py` and re-exported from `siege_utilities/geo/crosswalk/__init__.py`; the allowlist diff shows the two `LongitudinalAligner.align` entries removed, so the earlier description of them as an open CI blocker is out of date; `tests/test_batch1_1373.py` uses the specific availability exception.
- Release convention: user-visible notes belong in `[4.1.0]`. This commit moves the #1408 entry verbatim. No other `[Unreleased]` entry was touched.
- Pre-author-inventory: NONE. Trivial-against-state: the commit moves existing text between two sections of one file, checked with `git diff origin/develop -- CHANGELOG.md`, which shows only #1408 additions after the sync.

## Peer review

Gate evidence, all observed in this work cycle:

- Local pytest on the merged tree: `python -m pytest test_longitudinal_aligner.py test_geo_crosswalk_crosswalk_client_errors.py test_batch1_1373.py` from the `tests` directory -> 88 passed, 4 warnings in 3.19s (Python 3.11, repository pyproject as config). The warnings come from the tobler dependency replacing NaN with 0 in an existing test.
- Hosted CI at the pushed head is recorded in the PR body once it finishes.
- Known baseline: develop CI has failures from the DuckDB 2.0 break (about 30) until the #1863 pin successor lands. They are not attributable to this PR and were not chased.

## Test plan

- Confirm exact-head CI at the pushed head reports success other than the known DuckDB 2.0 failures on develop.
- Confirm `CHANGELOG.md` has the #1408 entry under `[4.1.0]` and none under `[Unreleased]`.
- Request a fresh exact-head review: the earlier result is void once the head moves, and the code diff is unchanged.

## Ticket-fitness exemption

Governing ticket: #1408 (the #1398 epic is context only and is not a governing ticket).

- **Reason:** #1408 predates the canonical ticket template (Context / Goal / Acceptance, a design link and Assumptions). It uses the earlier hostile-review Problem / Done-when / Falsifier narrative, so the ticket-fitness check reports a structure gap. The exemption is for ticket structure only.
- **Evidence:** the Problem (the longitudinal aligner catching every crosswalk exception and silently falling back to areal interpolation), the evidence and the Done-when live in the ticket, https://github.com/siege-analytics/siege_utilities/issues/1408, and in the PR description. The reviewer verdict is https://github.com/siege-analytics/siege_utilities/issues/1408#issuecomment-6257020991.
- **Falsification:** revert the implementation (`siege_utilities/geo/timeseries/longitudinal_data.py` and the crosswalk client changes of this PR); `tests/test_longitudinal_aligner.py::TestAlign::test_crosswalk_error_propagates_without_areal` goes red because a crosswalk processing error is swallowed into an areal fallback instead of propagating. Observed revert run: with `siege_utilities/geo/timeseries/longitudinal_data.py` restored to origin/develop (`git checkout origin/develop -- siege_utilities/geo/timeseries/longitudinal_data.py`), `python -m pytest test_longitudinal_aligner.py::TestAlign::test_crosswalk_error_propagates_without_areal -q`, run from the tests directory, gave 3 failed in 0.40s (`Failed: DID NOT RAISE` for the KeyError and ValueError parameters). Restoring all four implementation files of the PR instead makes the whole test module fail at import with `ImportError: cannot import name 'CrosswalkUnavailable'`. After `git checkout HEAD --` the named command gave 3 passed in 0.37s, `test_longitudinal_aligner.py`, `test_geo_crosswalk_crosswalk_client_errors.py` and `test_batch1_1373.py` gave 88 passed (4 warnings) on the pushed head, and the worktree was clean. The latest commit of this PR is process-only.

## Lead review

The change is additive and reverts with one commit. No behavior change. No claim in this artifact exceeds what was observed.

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

## Lead review

The change is additive and reverts with one commit. No behavior change. No claim in this artifact exceeds what was observed.

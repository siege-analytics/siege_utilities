# Self-review: place history reverse lineage (#1434, PR #1772)

Scope of this artifact: the PR as a whole at its code head, plus the process-only commit that syncs with develop, moves the release note into `[4.1.0]` and adds this file. The process commit changes `CHANGELOG.md` and this document and no library code. The PR body was also rewritten to describe the code at this head.

Review-Tier: A for the process commit (documentation and release notes only). The code commits under review were reviewed independently at exact head bd3c1127 by the external reviewer (ticket #1434, resolution review comment 6256938655).

## Assumptions

- Goal source: ticket #1434. Reverse place-history queries must keep real ancestors, pair GEOIDs with the correct vintage years, and report cumulative terminal weights.
- Roles: author is the PR owner; the independent reviewer is the cross-family hostile reviewer who recorded the head bd3c1127 verdict on the ticket.
- The code diff against `origin/develop` is limited to `siege_utilities/geo/place_history.py`, `tests/test_place_history_lineage.py` and `CHANGELOG.md`. This commit adds no library code.
- The body claims were checked against `place_history.py` at this head: `CrosswalkRecord.reverse_weight` (line 149), `DictCrosswalkProvider.add(..., reverse_weight=...)` (line 205), reverse `min_weight` pruning and the empty `terminal_weights` when any retained terminal path has an unknown weight (`_build_lineage`, lines 291-385), and the public `Lineage.terminal_weights` field (line 90).
- Release convention: user-visible notes belong in `[4.1.0]`. This commit moves the #1434 entry verbatim. No other `[Unreleased]` entry was touched.
- Pre-author-inventory: NONE. Trivial-against-state: the commit moves existing text between two sections of one file, checked with `git diff origin/develop -- CHANGELOG.md`, which shows only #1434 additions after the sync.

## Peer review

Gate evidence, all observed in this work cycle:

- Local pytest on the merged tree: `python -m pytest test_place_history_lineage.py test_place_history.py` from the `tests` directory -> 72 passed, 1 failed in 0.44s. The one failure is `test_place_history.py::TestPlaceHistory::test_no_provider_returns_error`, which imports Django GIS through `_get_default_provider` and stops with `ImproperlyConfigured: Could not find the GDAL library`. The GDAL library is not installed on this machine; the hosted CI image provides it. The failing path is not part of this PR's diff.
- Hosted CI at the pushed head is recorded in the PR body once it finishes.
- Known baseline: develop CI has failures from the DuckDB 2.0 break (about 30) until the #1863 pin successor lands. They are not attributable to this PR and were not chased.

## Test plan

- Confirm exact-head CI at the pushed head reports success other than the known DuckDB 2.0 failures on develop, and that `test_no_provider_returns_error` passes in the CI image.
- Confirm `CHANGELOG.md` has the #1434 entry under `[4.1.0]` and none under `[Unreleased]`.
- Request a fresh exact-head review: the earlier result is void once the head moves, and the code diff is unchanged.

## Lead review

The change is additive and reverts with one commit. No behavior change. No claim in this artifact exceeds what was observed.

# Self-review: crosswalk weighting, missing values and rates (#1409, PR #1779)

Scope of this artifact: the PR as a whole at its last code head b71f1069, plus the process-only commit that syncs with develop, moves the two release notes into `[4.1.0]` and adds this file. The process commit changes `CHANGELOG.md` and this document and no library code. The PR body was also rewritten to describe the code at this head.

Review-Tier: A for the process commit (documentation and release notes only). The code commits under review were reviewed independently at exact head b71f1069 by the external reviewer (ticket #1409, review comment 6257195272).

The PR carries a BREAKING classification (POPULATION and HOUSING now require their weight columns and reject missing weights). This artifact does not decide that classification. The release sign-off for it belongs to the operator.

## Assumptions

- Goal source: ticket #1409. Crosswalk processing must keep NaN for all-missing extensive targets, use the real population and housing weights, divide EQUAL splits correctly, and let `normalize_to_year` and `get_longitudinal_data` identify rates.
- Roles: author is the PR owner; the independent reviewer is the cross-family hostile reviewer who recorded the head b71f1069 verdict on the ticket.
- The code diff against `origin/develop` touches `crosswalk_processor.py`, `longitudinal_data.py`, `docs/CENSUS_DATA_GUIDE.md`, `tests/test_crosswalk_weights_1409.py` and `CHANGELOG.md`. This commit adds no library code.
- The body claims were checked against the code at this head: `sum(min_count=1)` for extensive sums (`crosswalk_processor.py` lines 434 and 439); `<col>_coverage` output columns (lines 469 and 479); `WeightMethod(value)` conversion (line 213); `population_weight` and `housing_weight` selection (lines 277-278); `intensive_columns` forwarded as `intensive_variables` in `longitudinal_data.py` (lines 307 and 904).
- Release convention: user-visible notes belong in `[4.1.0]`. This commit moves the BREAKING Changed entry and the Fixed entry verbatim, keeping their migration detail. No other `[Unreleased]` entry was touched.
- Pre-author-inventory: NONE. Trivial-against-state: the commit moves existing text between two sections of one file, checked with `git diff origin/develop -- CHANGELOG.md`, which shows only #1409 additions and no removed lines after the sync.

## Peer review

Gate evidence, all observed in this work cycle:

- Local pytest on the merged tree: `python -m pytest test_crosswalk_weights_1409.py test_geo_crosswalk_crosswalk_processor_errors.py test_longitudinal_aligner.py test_longitudinal_normalization_consensus.py test_crosswalk.py::TestCrosswalkProcessor test_crosswalk.py::TestConvenienceFunctions` from the `tests` directory -> 78 passed, 1 warning in 3.12s (Python 3.11, repository pyproject as config). The warning is a scipy FutureWarning inside an existing test. The client cache test that fails on a PyArrow duplicate filesystem registration is outside this selection and outside the PR's diff.
- Hosted CI at the pushed head is recorded in the PR body once it finishes.
- Known baseline: develop CI has failures from the DuckDB 2.0 break (about 30) until the #1863 pin successor lands. They are not attributable to this PR and were not chased.

## Test plan

- Confirm exact-head CI at the pushed head reports success other than the known DuckDB 2.0 failures on develop.
- Confirm `CHANGELOG.md` has both #1409 entries under `[4.1.0]` and none under `[Unreleased]`.
- Request a fresh exact-head review: the earlier result is void once the head moves, and the code diff is unchanged.
- Obtain the operator's release sign-off for the BREAKING classification before tagging.

## Lead review

The change is additive and reverts with one commit. No behavior change. No claim in this artifact exceeds what was observed.

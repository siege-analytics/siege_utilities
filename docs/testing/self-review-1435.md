# Self-review: Facebook insights parsing and API isolation (#1435, PR #1774)

Scope of this artifact: the PR as a whole at its code head, plus the process-only commit that syncs with develop, moves the three release notes into `[4.1.0]` and adds this file. The process commit changes `CHANGELOG.md` and this document and no library code. The PR body was also rewritten to describe the code at this head.

Review-Tier: A for the process commit (documentation and release notes only). The code commits under review were reviewed independently at exact head 0b2b6234 by the external reviewer (ticket #1435, review comment 6256996896).

## Assumptions

- Goal source: ticket #1435. Page insights must join every metric's daily values by measured day instead of copying the first value into every column, and each connector must use its own API session.
- Roles: author is the PR owner; the independent reviewer is the cross-family hostile reviewer who recorded the head 0b2b6234 verdict on the ticket.
- The code diff against `origin/develop` is limited to `siege_utilities/analytics/facebook_business.py`, `tests/test_facebook_business_connector.py`, `tests/test_facebook_business_insights.py` and `CHANGELOG.md`. This commit adds no library code.
- The body claims were checked against `facebook_business.py` at this head: the page `date` is `YYYY-MM-DD` for the date of `end_time` minus one day with absent values as NaN (`get_page_insights`, lines 184-238); ad insights request `time_increment=1` and the fields `ad_id`, `ad_name`, `date_start`, `date_stop`, with NaN for absent metrics (`get_ad_insights`, lines 121-168); business missing metrics are NaN (`get_business_insights`); `batch_retrieve_facebook_data` takes the optional `config_directory: str | None = None` and forwards it to all three retrieval paths (lines 475-501); every SDK object receives `api=self.api`.
- Release convention: user-visible notes belong in `[4.1.0]`. This commit moves the three #1435 entries verbatim. No other `[Unreleased]` entry was touched.
- Pre-author-inventory: NONE. Trivial-against-state: the commit moves existing text between two sections of one file, checked with `git diff origin/develop -- CHANGELOG.md`, which shows only #1435 additions after the sync.

## Peer review

Gate evidence, all observed in this work cycle:

- Local pytest on the merged tree: `python -m pytest test_facebook_business_insights.py test_facebook_business_connector.py -m "not integration and not requires_api_key"` from the `tests` directory -> 29 passed, 1 deselected in 0.92s (Python 3.11, repository pyproject as config). The deselected test is the live Facebook API smoke test. All tests use mocked SDK objects.
- Hosted CI at the pushed head is recorded in the PR body once it finishes.
- Known baseline: develop CI has failures from the DuckDB 2.0 break (about 30) until the #1863 pin successor lands. They are not attributable to this PR and were not chased.

## Test plan

- Confirm exact-head CI at the pushed head reports success other than the known DuckDB 2.0 failures on develop.
- Confirm `CHANGELOG.md` has the three #1435 entries under `[4.1.0]` and none under `[Unreleased]`.
- Request a fresh exact-head review: the earlier result is void once the head moves, and the code diff is unchanged.

## Pre-flight (develop 71f02b0b)

Develop was merged additively. The only conflict was `CHANGELOG.md`; every develop line was kept, including develop's #1444 entry, which already states that "the Facebook daily-label fix is tracked separately in #1435". Develop wins on any disagreement, and none exists: the analytics files changed by the merge are Google Analytics, Instagram, Vista Social, X and the pipeline analyzer, and none is the Facebook connector.

Classification: caller code that worked on v4.0.0 now sees different results (page-insight `date` is a `YYYY-MM-DD` string for the day before `end_time`, absent values are NaN instead of zero, ad insights are daily rows with added columns). The three #1435 entries are now one entry under `### BREAKING` in `[4.1.0]` with a Migration line, at its own position in the BREAKING list so it does not conflict with the other open PRs. `git diff origin/develop -- CHANGELOG.md` shows 16 added lines and 0 removed lines. The PR body classification is updated to match.

Tests, run from the `tests` directory (Python 3.11, repository pyproject): `python -m pytest test_facebook_business_insights.py test_facebook_business_connector.py -m "not integration and not requires_api_key" -q` -> 29 passed, 1 deselected in 0.79s. The library code is unchanged since the red/green run recorded in the Falsification entry below, which still applies to this head.

## Integration with #1812 (develop 79f37f4d)

#1812 landed first, as the reviewer decided, and both PRs fix the same v4.0.0 page-insights bug with contradictory output contracts. This merge has parents 32f961e9 (this branch) then 79f37f4d (develop). The only conflict was the `get_page_insights` row-building hunk in `siege_utilities/analytics/facebook_business.py`; `CHANGELOG.md` and `tests/test_facebook_business_connector.py` merged without conflict. The hunk is resolved to the reviewer's contract:

- `period=day`: `end_time` is normalized to UTC before one calendar day is subtracted (`_page_insight_measured_day`); a naive `end_time` is read as UTC, never host local time; an empty `end_time` stays empty.
- Columns are fixed to `['date', *metrics]` in requested order. An absent value or metric is NaN, a known 0 stays 0, and an empty or unrequested-only response is a zero-row frame with that schema.
- Every insight name is validated before any value is projected, so an unnamed insight raises `ValueError` even with empty values (#1812's behavior; this branch's skip-unnamed behavior is gone). Named but unrequested insights are dropped before their values are read.
- Kept unchanged: #1812's Graph defaults and comma-joined `metric` parameter, and this branch's per-instance API sessions, ad insights, business NaN and `config_directory`.

Disclosed test changes. Every other assertion and control is kept.
- (a) `test_facebook_business_connector.py::test_get_page_insights_keys_by_metric_name_across_every_date`: the date expectation moves from the raw `end_time` to the measured day (`["2025-12-31", "2026-01-01"]`). The value and cardinality assertions are unchanged.
- (b) `test_facebook_business_insights.py::test_page_insights_without_named_values_has_schema`: its `no-name` case moves to the new `test_page_insights_rejects_unnamed_insight_before_projection`, which expects `ValueError`. The `no-insights` and `no-values` schema cases stay.
- (c) `test_page_insights_normalises_every_end_time_to_measured_day`, `+1400` case: the expectation moves from `["2024-02-29", "2024-03-01"]` to `["2024-02-28", "2024-02-29"]`. 00:00 at +14:00 is 10:00 UTC the previous day, and the old expectation encoded the literal local date, which the UTC contract replaces.

New controls: offset equivalence (three spellings of one instant), the year boundary (naive, UTC, east and west of UTC), host-TZ independence for a naive `end_time` (`TZ` forced to Pacific/Kiritimati, America/Los_Angeles and UTC), a requested metric absent from the response, an unrequested-only response (including one with an unparseable `end_time`, which is never read), an unrequested metric creating no rows, an explicit null value next to a known zero, and unnamed insights with values, empty values, an empty name and a null name.

Red and green, from the `tests` directory (Python 3.11, repository pyproject, mock transport only; no live Facebook, network or TLS claim):
- This branch's parent source (`facebook_business.py` at 32f961e9): `test_facebook_business_connector.py` and `test_facebook_business_insights.py` gave 9 failed, 39 passed, 1 skipped. All 9 are behavioral: unnamed insights did not raise (5), and offset/UTC labels were wrong (4). The naive host-TZ control passes on this parent, because literal-date parsing is also host-independent.
- Develop's parent source (79f37f4d): 36 failed, 12 passed, 1 skipped. 22 page-insights failures are behavioral (raw `end_time` dates, dynamic columns, unrequested rows, and a `TypeError` on `values: None`). The other 14 are this branch's features absent from develop: per-instance sessions (7, including the two connector init tests), ad fields (2) and business NaN (1) fail behaviorally; of the 4 `config_directory` cases, three batch calls fail with an interface `TypeError` and the signature check fails its assertion.
- The merged tree: the two Facebook files gave 48 passed, 1 skipped (the skip is the `requires_api_key` live test). With `test_social_connectors_cluster.py`, `test_social_media_reports_nulls.py`, `test_social_review_blockers.py`, the four `test_1812_*` files, `test_instagram_token_exchange_logging.py` and `test_x_budget_enforced_per_attempt.py`: 411 passed, 1 skipped. `test_social_media_reports_errors.py` and the three exception-contract files: 68 passed. `test_notebook_hygiene.py` and `test_notebooks.py`: 265 passed, 1 skipped.

CHANGELOG: develop's #1474 BREAKING entry keeps Instagram's `None` policy; only its Facebook clause now says a missing daily value is unavailable (NaN). This branch's #1435 entry, now under `[5.0.0]`, states the one Facebook contract above and its Migration, including that `date` was the raw `end_time` in v4.0.0. No other entry is changed or moved.

This comparison is the implementer's own and is not an independent hostile review.

## Ticket-fitness exemption

Governing ticket: #1435 (the #1398 epic is context only and is not a governing ticket).

- **Reason:** #1435 predates the canonical ticket template (Context / Goal / Acceptance, a design link and Assumptions). It uses the earlier hostile-review Problem / Done-when / Falsifier narrative, so the ticket-fitness check reports a structure gap. The exemption is for ticket structure only.
- **Evidence:** the Problem (page insights copying the first value into every metric column and sharing one SDK token across connectors), the evidence and the Done-when live in the ticket, https://github.com/siege-analytics/siege_utilities/issues/1435, and in the PR description. The reviewer verdict is https://github.com/siege-analytics/siege_utilities/issues/1435#issuecomment-6256996896.
- **Falsification:** revert the implementation (`siege_utilities/analytics/facebook_business.py` changes of this PR); `tests/test_facebook_business_insights.py::test_page_insights_pivots_each_metric_for_each_day` goes red because each metric column again receives the first returned value and later days are dropped. Observed revert run: with `siege_utilities/analytics/facebook_business.py` restored to origin/develop (`git checkout origin/develop -- siege_utilities/analytics/facebook_business.py`), `python -m pytest test_facebook_business_insights.py::test_page_insights_pivots_each_metric_for_each_day -q`, run from the tests directory, gave 1 failed in 0.71s (AssertionError). After `git checkout HEAD --` of the file the command gave 1 passed in 0.53s, `test_facebook_business_insights.py` with `test_facebook_business_connector.py` (marker "not integration and not requires_api_key") gave 29 passed, 1 deselected on the pushed head, and the worktree was clean. The latest commit of this PR is process-only.

## Lead review

The change is additive and reverts with one commit. No behavior change. No claim in this artifact exceeds what was observed.

# Self-review: R-1812-4 (strict fidelity, history-free baseline, cumulative wait budget, #1812)

Scope: one commit on PR #1812 after `b7199b4e`. Production change:
`siege_utilities/analytics/instagram.py` and `x_twitter.py` (cumulative retry
wait). Audit change: `scripts/check_social_review_fidelity.py`. Tests:
`tests/test_1812_cumulative_wait_budget.py` (new),
`tests/test_1812_fidelity_oracle.py`, `tests/test_social_review_blockers.py`.
Fixtures: `tests/fixtures/social_baseline_d329eef7/` (three frozen sources).
CHANGELOG.md gains the `[4.1.0]` notes for #1458, #1465, #1474 and #1812.

## Assumptions

Domain(s): software engineering (social connectors, retry policy, audit
tooling).
Goal source: review finding R-1812-4 on #1812 (exact-head review of
`b7199b4e`, findings F1 and F2) and the cumulative-wait finding on #1458
(issuecomment-6635453036); the null policy that an unavailable social metric
is `None`, never `0`.
Working as: software engineer (Junior) and tech lead (Lead); both reviews are
below.

## Peer review

- Cumulative wait. Each request tracks the time it has slept. Before any
  sleep, `_within_wait_budget` checks `waited + delay <= max_retry_wait`
  (a NaN delay fails closed). A rate-limit wait over the budget raises the
  `SocialMediaRateLimitError` with the hint kept in `retry_after`; a transport
  or 5xx backoff over the budget ends the retries, and the final error reports
  the attempts made. Before this change one request could sleep 600 + 600 s,
  or 900 + 900 s with a large backoff.
- Changed assertion (disclosed): `test_b4_configured_backoff_is_capped`
  previously asserted two 900 s sleeps and a success on the third call. It now
  asserts one 900 s sleep, two calls and the failure, because the first capped
  wait spends the whole budget.
- Strict fidelity. Two null leaves are equal only when they have the same type
  (`None`, `pd.NA`, `NaT`, `NaN` stay distinct). Frames must match on index and
  columns type, dtype and names. The eight authorized zero-to-null cells are
  unchanged.
- History-free baseline. The three `d329eef7` modules are committed
  byte-identical as `.txt` files (not collected by pytest or ruff). The audit
  loads them instead of running `git show`, and it checks each file's git blob
  id (`7cafa6ca`, `da2b74e6`, `cd034658`) before use. Frozen sources were chosen
  over frozen outputs because output dtypes differ by pandas version
  (`datetime64[ns, UTC]` on 2.3.3, `datetime64[s, UTC]` on 3.1.0).
- A pre-existing mid-file `import numbers` (ruff E402) moved to the top.

## Known integer counts render as integers

The None-not-0 fix makes a count column float once any post omits the
count, so a known 7 likes rendered `7.0` (and 1234 followers `1,234.0`).
`_format_metric` now renders an integral float as an integer when the
format spec has no precision; fractional values (`7.5`), explicit-precision
specs (the `,.0f` average) and missing values (`unavailable`) are unchanged.
`tests/test_1812_integral_count_rendering.py`: 3 failed / 6 passed at
`54cb4348` (`'7.0' != '7'`, `['7.0', '1.0'] != ['7', '1']`,
`'1,234.0' != '1,234'`), 9 passed with the change.

## Focused verification of the cumulative wait budget

`tests/test_1812_wait_budget_grid.py` enumerates every sequence of three
`Retry-After` hints drawn from {0, 1, 15, 450, 600, 899, 900} (343 sequences)
for Instagram and X, with `max_retry_wait` 900 and 20, and compares the real
sleep schedule with a reference model: a wait is taken only while the
running total stays within the cap, and the first wait that would exceed it
ends the request with `SocialMediaRateLimitError`. It also asserts the total
slept never exceeds the cap. On the pre-fix connectors (tree of `b7199b4e`
with this test added) all 4 cases fail with
`DID NOT RAISE SocialMediaRateLimitError` (the old code keeps sleeping past
the cap); at this head all 4 pass (1,372 schedules checked).

## Deviation from R-1812-4 (b)

R-1812-4 (b) asked for the baseline *outputs* to be committed as a frozen
fixture. This PR deliberately freezes the baseline *sources* instead (the
three `d329eef7` modules, byte-identical, pinned by git blob id in
`BASELINE_BLOBS` and by `test_frozen_baseline_matches_the_reviewed_commit`).
Reason: the audit compares dtypes exactly, and output dtypes depend on the
pandas version a lane resolves. The reviewer's own evidence for F1 shows the
omitted Instagram `published_at` column as `datetime64[ns, UTC]` on pandas
2.3.3 and `datetime64[s, UTC]` on pandas 3.1.0, so outputs frozen on one
version would fail the strict audit on a lane with the other (a false red).
Frozen sources rebuild the baseline outputs on the lane's own pandas, so old
and new are compared on one version. Evidence: the oracle and budget tests
pass on pandas 2.3.3 (18 + 14) and 3.1.0 (32), and 32 pass in a `--depth 1`
clone where `d329eef7` is absent.

## Combined tree with #1807 (None-not-0)

Built against the latest #1807 head at the time of the run: `56e8a5fa`
(merged without committing into a local scratch clone of `f3829edb`; never
pushed). `siege_utilities/reporting/social_media_reports.py` conflicts in 7
regions, and #1807's side was used. On that tree the None-not-0 checks hold:
`tests/test_1812_null_policy_end_to_end.py` (4) and #1807's
`tests/test_1469_social_media_report_totals.py` pass; 187 passed, 7 failed
overall. The 7 failures are wording couplings, not null-policy violations: 5
`StopIteration` title lookups in `tests/test_social_media_reports_nulls.py`
(titles #1807 renames) and 2 fidelity-oracle failures on #1807's intended
`executive_summary` rewording. Those are resolved in this PR's develop sync
after #1807 lands. #1812 does not use #1807's `f"{exc}"` / `from exc`
exception pattern; the one `from exc` in `x_twitter.py` (JSON decode error)
predates this PR (#1069, on develop).

## Lead review

The retry change narrows behavior on purpose: a caller that set
`max_retry_wait` now gets that bound for the whole request, which is what the
setting's name and the reviewer's finding require. In-budget retries are
unchanged. The audit changes add checks without relaxing any; the review's
four seeds now fail the real audit. The combined-tree check with #1807 is
separate work on this PR.

## Ticket-fitness exemption

The governing tickets #1458, #1465 and #1474 were written before the current
evaluate-ticket structure (Problem / Evidence / Done-when headings), which is
the Reason for each exemption; it covers ticket structure only. #1398 is the
parent epic and context only.

Revert run (observed 2026-11-05, Python 3.11.11). The three tickets were
implemented together in `4eebecbd` and `6991a852`, with one regression file,
`tests/test_social_connectors_cluster.py`, so the revert removes the shared
implementation of all three at once: the tree of `4eebecbd^`
(`git archive 4eebecbd^`) with that test file from `6991a852` overlaid, run
from its `tests/` directory with
`python -m pytest -o addopts="" --rootdir=.. -c ../pyproject.toml -p no:cacheprovider -q -p no:randomly test_social_connectors_cluster.py`.
Result: 94 failed / 16 passed. Each entry names a node whose failure is that
ticket's own behavior. Head: the file is 113 passed.

- **#1458** (Instagram connector: missing metrics, throttling, token expiry).
  Node: `tests/test_social_connectors_cluster.py::test_instagram_missing_account_metric_is_not_zero`.
  In the revert run it fails with `assert False` (a missing account metric is
  reported as a number). Head: passes.
- **#1465** (X connector: user-id validation, page sizes, insight merge).
  Node: `tests/test_social_connectors_cluster.py::test_x_nonexistent_user_id_fails_authentication`.
  In the revert run two cases fail with
  `DID NOT RAISE SocialMediaAuthError` and one with
  `AttributeError: 'NoneType' object has no attribute 'get'` (a nonexistent
  user id authenticates). Head: passes.
- **#1474** (Graph insight defaults). Node:
  `tests/test_social_connectors_cluster.py::test_instagram_defaults_use_current_metrics`
  (and `test_facebook_page_defaults_and_metric_parameter`). In the revert run
  the Instagram account, post and story cases fail with
  `AssertionError: assert not ({... 'impressions' ...} & {...retired metrics...})`
  (retired metrics are still the defaults), and the Facebook cases fail with
  the same retired-metric overlap and `KeyError: 'metric'`. Head: passes.

## Test plan

- Red first, unmodified connectors: `tests/test_1812_cumulative_wait_budget.py`
  14 cases, 12 failed and 2 passed (the passes are the in-budget control).
- Red first, unmodified audit: the four review seeds in
  `tests/test_1812_fidelity_oracle.py` failed (the audit certified each
  mutation); the two controls passed.
- After the change, Python 3.11.11, pandas 2.3.3: the eleven social modules
  (`test_1812_cumulative_wait_budget`, `test_1812_fidelity_oracle`,
  `test_analytics_instagram_errors`, `test_analytics_x_twitter_errors`,
  `test_facebook_business_connector`, `test_social_connectors_cluster`,
  `test_social_media_reports_errors`, `test_social_media_reports_nulls`,
  `test_social_review_blockers`, `test_vista_social`,
  `test_vista_social_connector`) are 325 passed, 2 skipped (both need live
  API credentials).
- Same commit with pandas 3.1.0: `test_1812_fidelity_oracle` and
  `test_1812_cumulative_wait_budget` are 32 passed.
- `ruff check` on every changed Python file passes.

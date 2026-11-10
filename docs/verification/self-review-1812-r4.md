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

Residual (review of `6da7775f`): an integral `numpy.float32`, which pandas
returns for a nullable `Float32` column and is not a `float` subclass, still
rendered followers as `1,234.0`. The check is now
`isinstance(value, (float, np.floating)) and float(value).is_integer()`.
New cases in the same test file cover `np.float32(1234.0)`, a pandas
`Float32` element, `np.float32(7.5)` (stays `7.5`) and `np.float32(12.4)`
with `,.0f` (stays `12`), plus an end-to-end case where a connector's
`get_account_info()` returns `Float32` counts through `_collect_platform_data`
into `_build_report_data`, asserting both the platform and total follower
metrics. At `fcc16c3a`: 3 failed / 11 passed (`'1,234.0' != '1,234'` for both
metrics); with the change: 14 passed.

The reviewer's pinned case is
`test_float32_count_next_to_missing_platform_count`: instagram
`followers_count=np.float32(1234)` next to x_twitter `followers_count=None`,
asserting `'1,234'`, `'unavailable'` and total `'1,234'`, with the Float32
posts row (7 likes / 1 comment) as a control. At-head control at `b832dee7`:
reversing only the widening (back to `isinstance(value, float) and
value.is_integer()`, the `6da7775f` logic) fails it with
`'1,234.0' == '1,234'`; restored, it passes (file: 15 passed).

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

At-head controls (the falsifiers; observed 2026-11-05 at `6da7775f`, Python
3.11.11, current tests). For each ticket only its surviving implementation
lines were reversed by hand, the named node was run from `tests/` with
`python -m pytest -o addopts="" --rootdir=.. -c ../pyproject.toml -p no:cacheprovider -q -p no:randomly test_social_connectors_cluster.py -k <node>`,
the file was restored with `git checkout HEAD -- <file>`, the node was run
again, and `git status --short` was empty.

- **#1458.** In `get_account_insights`
  (`siege_utilities/analytics/instagram.py:255` and `:259`), changed
  `value_entry.get("value")` to the pre-fix `value_entry.get("value", 0)`.
  Node `test_instagram_missing_account_metric_is_not_zero`: 1 failed,
  `assert False` at the test's `pd.isna(...)` check (a missing daily metric
  becomes 0). Restored: 1 passed.
- **#1465.** In `authenticate`'s user-id branch
  (`siege_utilities/analytics/x_twitter.py:175-178`), removed the
  `if not user: raise SocialMediaAuthError(...)` check, matching the pre-fix
  branch. Node `test_x_nonexistent_user_id_fails_authentication`: 3 failed,
  two with `DID NOT RAISE SocialMediaAuthError` (an unknown user id
  authenticates) and the `{"data": None}` case with
  `AttributeError: 'NoneType' object has no attribute 'get'`, which is what
  the pre-fix branch does with that body. Restored: 3 passed.
- **#1474.** Reverted the default-metric constants
  (`siege_utilities/analytics/instagram.py:65-66`) to the pre-fix
  `"impressions,reach,profile_views,follower_count"` and
  `"impressions,reach,engagement,saved,shares"`. Node
  `test_instagram_defaults_use_current_metrics`: 2 failed (`[account]`,
  `[post]`), each `AssertionError: assert not ({... 'impressions' ...} & DEPRECATED)`
  (retired metrics are requested by default). Restored: 3 passed.

Historical revert run (context, not the falsifier; observed 2026-11-05, Python 3.11.11). The three tickets were
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

## Develop sync with #1794 (merge of `560a858e`)

develop's #1794 (#1439, #1833) rewrote the same Instagram request, paging and
post code. The merge conflicted in 9 regions of
`siege_utilities/analytics/instagram.py` and 1 in
`scripts/check_credential_urls.py`. The rule applied: #1794's Graph-origin
check, redirect refusal and pagination contract stay intact, and #1812's retry
budget, null policy and post-frame schema are layered on top. Where the two
disagree, #1794's security boundary wins.

Resolution, by region:

- `_request_url`. #1794's HTTPS `GRAPH_HOSTS` origin check runs first, before
  #1812's expired-token check, so no request (and no expiry state change)
  happens for an untrusted URL. The session call passes both
  `allow_redirects=False` (#1794) and the token-exchange
  `Authorization: None` header (#1812). The 3xx refusal runs before #1812
  reads the body for Graph codes 190/463, rate limits and token-exchange
  rejection, so a redirect body is never interpreted. #1812's retry budget
  (`_within_wait_budget`) and `_is_rate_limited` are unchanged.
- `get_account_insights`. #1794's 30-day UTC chunking and `_iter_pages` are
  kept. The auto-merged line `value_entry.get("value", 0)` from develop is
  changed to `value_entry.get("value")`: #1812's null policy (a missing
  metric is `None`, not `0`). Git reported no conflict on that line, so
  without this edit the null policy would have been silently lost.
- `get_posts`. #1794's `_iter_pages` loop, per-page date window, total limit
  and stop-when-a-page-predates-the-window are kept. #1812's
  partial-results rule wraps the loop: a `SocialMediaRateLimitError` on a
  later page returns the posts collected so far with a warning; with nothing
  collected it propagates. Docstrings combine both contracts.
- Imports: the union of both sides.
- `scripts/check_credential_urls.py`: the reviewed-site key is the merged call's
  `ast.unparse` text, and the reason now states both the origin and redirect
  restriction (#1794) and the token-exchange header removal (#1812). The guard
  reports 0 unreviewed sites.

Disagreement, resolved for #1794: develop's `get_posts` keeps only posts with
a valid in-range timestamp. Three #1812 test fixtures assumed the pre-#1794
shape. `test_instagram_absolute_paging_url_preserves_partial_results` used a
post with no timestamp, and two account-insight tests and
`test_instagram_missing_account_metric_is_not_zero` mocked one response for a
31-day range that #1794 now splits into two 30-day windows. The fixtures were
adapted (an in-range timestamp; a second window response); no assertion
changed and no library code was relaxed.

Controls on the merged tree. Changing the account-insight line back to
`.get("value", 0)` makes `test_instagram_missing_account_metric_is_not_zero`
fail; disabling the partial-results branch makes
`test_rate_limit_after_first_page_returns_partial_results[instagram]` and
`test_instagram_absolute_paging_url_preserves_partial_results` fail. Both
were restored.

Merged-tree verification (Python 3.11.11): the changelog tests, the named
social suites, the frozen-source fidelity oracle, `test_1439_*`, `test_1794_*`
and `tests/guard/test_exception_contract_guard.py` are 904 passed, 1 skipped.
`check_exception_contracts.py --list`: 205 flagged, 0 unlisted, 0 stale (no
handler fingerprint moved, so none was refreshed).
`check_credential_urls.py`: 0 unreviewed sites. The static-guard scripts and
`ruff check` on the three changed files pass.

## Develop sync with #1809, #1778 and #1780 (merges of `e6350590` and `71f02b0b`)

`e6350590` (#1809) merged without conflicts. `71f02b0b` brought #1778 (#1444) and
#1780. #1778 labels Instagram daily insight rows with the covered day (one day before
Graph's `end_time` marker), takes X account snapshots on the UTC date, and adds
pipeline timezone handling. The merge conflicted in 2 regions of
`analytics/instagram.py` (imports, the `get_account_insights` docstring), 2 of
`analytics/x_twitter.py` (imports, the `get_account_insights` docstring) and the
CHANGELOG [4.1.0] Fixed tail. All were resolved as unions: both import sets, and
docstrings that state both #1778's labelling and #1812's null policy. The CHANGELOG
keeps every develop line, including #1444's entry, beside this PR's entries. The
code bodies merged without conflicts. #1812's null policy survived
(`value_entry.get("value")` beside #1778's covered-day code), and no `0` default
appears in either connector.

Disagreement, resolved for develop: #1778's covered-day labels change two
#1812-owned checks.
- `test_instagram_missing_account_metric_is_not_zero` used `end_time`s that now
  label the previous day. Its fixture `end_time`s move forward one day, so the
  assertions are unchanged.
- The fidelity oracle compares against the frozen d329eef7 baseline, which labels
  Instagram rows by `end_time` and X snapshots by local `date.today()`. It now
  authorizes exactly #1444's relabel, and only in the `date` cells of
  `get_account_insights`: an Instagram label must equal the baseline label minus
  one day, and an X label must equal today's UTC date. The audit requires the
  Instagram relabel to fire. Every other value, null and string still compares
  strictly.
- Control: changing the allowed shift to two days makes `test_unmutated_audit_is_green`
  and `test_seed_controls_leave_the_audit_green` fail on
  `instagram.get_account_insights[0,'date']`. It was restored.

Verification on the merged tree (Python 3.11.11): the changelog tests, the social
suites, the fidelity oracle, `test_1439_*` (which holds #1444's Instagram checks),
`test_analytics_datetime`, `test_1794_*`, `test_1475_*`, `test_1809_*`,
`test_1780_*`, `test_1661_*` and the exception-contract guard test are 1028 passed,
1 skipped. `check_exception_contracts.py --list`: 205 flagged, 0 unlisted, 0 stale.
`check_credential_urls.py`: 0 unreviewed sites. ruff passes on the changed files.

## Open review threads at `e5ee2d5c` (13 threads)

Each thread was checked against the code at `e5ee2d5c`. Outcome by thread:

- Fixed in this commit:
  - The notebook `instagram_insights` fixture now uses `reach` and `follower_count`.
  - Both connectors' `_parse_retry_after` read a zone-less HTTP date as UTC, and treat a date already past as no hint, so the configured backoff applies.
  - Facebook Page Insights send comma-separated `metric` names, keep a missing daily value as `None`, and raise `ValueError` for an insight with no metric name.
  - The fidelity oracle has type hints and compares column dtypes; a dtype may change only in a column that received an authorized null.
  - `refresh_access_token` documents intermediary-log redaction for the GET token exchange.
- Already addressed:
  - The rate-limit cap: `max_retry_wait` (default 900 s) raises without sleeping above the cap, and the cumulative budget bounds total sleep.
  - The review-response record: the file was deleted at `b0eacc57`, and this record holds no local paths.
  - Paging-URL origin: #1794's `GRAPH_HOSTS` check in `_request_url`, now merged here.
- Proposed as tracked deferrals:
  - The known-likes count in the average-likes insight. #1807 rewrites that sentence, and the follow-up is prepared with the #1807 patches.
  - Renaming and consolidating the review-round test files. This is broad churn mid-review and would invalidate cited evidence.

Red checks: the eight new or changed tests fail on the `e5ee2d5c` library code (past and naive HTTP dates for both platforms, the comma-separated metric for both parameter cases, the Facebook missing value, and the nameless insight). Both dtype tests fail on the `e5ee2d5c` oracle. All pass after the fix.

Verification (Python 3.11.11):
- The full #1812 set plus `test_notebook_hygiene` and `test_notebooks` is 1301 passed, 2 skipped.
- `check_exception_contracts.py --list`: 205 flagged, 0 unlisted, 0 stale.
- `check_credential_urls.py`: 0 unreviewed sites.
- The static guards and ruff pass.

## X snapshot date in the fidelity oracle (#1879)

At `09ed493c` the oracle compared the X snapshot under the real clock. The
baseline labels it with host-local `date.today()`, the fix with the UTC date,
and the two are usually equal. As a result:

- (a) A current producer that regressed to the host-local date matched the
  baseline exactly, skipped the UTC rule, and the audit stayed green. Only the
  Instagram relabel was required to fire.
- (b) The oracle read the clock a second time, so a correct Jan 31 23:59:59Z
  snapshot compared at Feb 1 00:00:01Z was rejected.

The fix is a bounded clock contract inside the oracle, not a clock subsystem.
The X `get_account_insights` comparison runs only under `X_CLOCKS`: one UTC
instant on a host whose local date is ahead of UTC (+06:00 at Jan 31
23:59:59Z), then behind it (-06:00 at Feb 1 00:00:01Z). Each clock patches
`date`/`datetime` in the baseline module and the current connector, for that
call only. The expected date is that same instant's UTC date, with no second
clock read. Outside a fixed clock no X date difference is authorized. Each
clock must produce the UTC relabel, so a snapshot equal to the host-local
baseline fails. A clock without a date divergence is refused. Instagram's exact
one-day rule and the strict field, dtype and null checks are unchanged.

Tests in `tests/test_1812_fidelity_oracle.py` set the clocks from outside the
helper. With the `09ed493c` helper, 11 of the 32 fail:

- The five behavioural reds:
  - the wrong host-local snapshot, issue steps 1-2: did not raise, the false
    green;
  - the correct snapshot across UTC midnight, issue step 3: "unexpected value
    diff '2026-02-01' -> '2026-01-31'", the false red;
  - the host-local producer through `date.today()` and through naive
    `datetime.now()`: did not raise;
  - an X date difference outside a fixed clock: did not raise.
- Six tests configure `X_CLOCKS` (five divergent-host greens, and the refusal
  of a non-divergent clock). They fail on the old helper only because it has
  no such hook.

The 21 that pass on both helpers include the Instagram two-day-shift
rejection and every earlier strict-comparison control. All 32 pass at this
commit.

Verification (Python 3.11.11): the social/oracle sweep gave 1054 passed and 31
skipped. `check_exception_contracts.py`: 205 flagged, 0 unlisted, 0 stale.
`check_credential_urls.py`: 0. Test-file hygiene PASS; ruff clean on both
changed files. Running the script directly was blocked by a local shell guard
(environment-variable prefix). The same `audit()` runs in full through the
oracle tests.

## Review threads at `006fc895` (6 threads)

- **urllib3 DEBUG logging (Security, Major): fixed, not just documented.**
  - urllib3 2.6.3 logs each request's path and query string at DEBUG: the
    request line, `Retry: <url>` and `Redirecting <url>`. The token exchange
    is a GET with `client_secret` and `fb_exchange_token` in that query, so
    turning on DEBUG for `urllib3.connectionpool` wrote both credentials to
    the log.
  - For the duration of the exchange only, `refresh_access_token` adds a
    filter to that logger that applies the library's `redact_url_secrets` to
    every record. A record that cannot be rendered is replaced with a fixed
    marker rather than emitted raw. The filter is removed afterwards, also on
    failure.
  - The docstring and the #1812 Security entry state this, keep the
    proxy/load-balancer warning, and add that `http.client` `debuglevel`
    output must stay off.
  - Native evidence, as the reviewer required, in
    `tests/test_instagram_token_exchange_logging.py`:
    - The test runs the real path `refresh_access_token` -> `requests` ->
      urllib3's HTTPS connection pool for the real
      `https://graph.facebook.com/v22.0/oauth/access_token` URL, with DEBUG
      enabled on `urllib3.connectionpool`. It captures urllib3's own records.
    - The real `HTTPSConnectionPool` and its native DEBUG logging run, but the
      pool's `ConnectionCls` is replaced with a plain-HTTP `HTTPConnection` to
      a local Graph stand-in. There is no TLS handshake: the test proves the
      native DEBUG sink and its redaction, not TLS or provider acceptance.
      The stand-in confirms it received both sentinel credentials in the
      query string.
    - With the `006fc895` `instagram.py` (red), urllib3's own record from
      `connectionpool.py:544` contained
      `client_secret=SYNTHETIC_APP_SECRET_6d1e&fb_exchange_token=SYNTHETIC_LOGIN_TOKEN_93ab`.
    - With the fix (green), both native request lines show
      `client_secret=[REDACTED]&fb_exchange_token=[REDACTED]`, and neither
      sentinel appears in any record.
    - The earlier security report excluded third-party HTTP DEBUG logging;
      this test is the first coverage of it.
- **"Largest audience" with one known count (Minor): fixed.**
  - The insight needs at least two known follower counts. With K of M known
    (K < M), it says "largest audience among the K of M platforms with known
    follower counts".
  - Tests: three one-known cases, an all-known case and a two-of-three case
    in `tests/test_social_media_reports_nulls.py`. The four K-limited cases
    were red at `006fc895`.
  - #1877 (posts with known like counts) is a separate site and stays open.
- **Narrow `TypeError` handling in the audit (Minor): fixed.** Only the
  baseline report, on an input with an unknown follower count, may record the
  `TypeError` placeholder. Any other `TypeError` re-raises with its traceback.
  `test_new_type_error_in_current_report_surfaces_unmasked` (2 cases) got an
  `AssertionError` from the old audit instead of the original `TypeError`.
- **X `get_account_info` null-check guard (Trivial): fixed.** The check is
  selected by fixture identity (`body is account_empty`), not value equality,
  and the audit asserts that it ran exactly once. No behaviour changes for the
  current fixtures, so there is no red/green pair; every green audit run
  exercises the new assertion.
- **Merge `test_1812_integral_count_rendering.py` (Trivial): done.** Its five
  test functions (15 cases) moved unchanged into
  `tests/test_social_media_reports_nulls.py`, the report's null-policy
  module, and the issue-numbered file was removed. Same test names and
  assertions, so the case count is unchanged.
- **Mixed 429/5xx/transport sequences (Trivial): added.**
  `test_mixed_429_5xx_and_transport_sequences_share_the_budget` runs all 125
  three-event sequences of {429 with hint 0/15/450, 503, ConnectionError},
  for both connectors and both caps. Each is checked against a reference
  model for the sleeps taken and the error type: `SocialMediaRateLimitError`
  when a 429 exhausts the budget, plain `SocialMediaError` when a 5xx or
  transport backoff does. At the 20-second cap both exhaustion types are
  reached. This adds coverage of existing behaviour, so it passes on both
  sides.

Verification (Python 3.11.11): the social/oracle/notebook-hygiene sweep gave
1292 passed and 31 skipped. Exception contracts: 205 flagged, 0 unlisted, 0
stale. Credential-URL guard: 0. Test-file hygiene PASS; ruff clean on all
changed files.

## Temporal missing values in count slots (#1880)

At `006fc895`/`a6343d63` the audit authorized any baseline-zero -> missing
change at the eight omitted-count cells, including a temporal `pd.NaT`. It
then exempted the column's dtype change because an authorized null landed
there. So a converter emitting `like_count` as `datetime64[ns]` NaT passed,
even though numeric `+ 1` on that column raises `TypeError`.

Bounded repair in `compare()`, with no new validation framework:

- The authorized zero -> missing branch rejects temporal values and markers
  (`pd.NaT`, `datetime64`/`timedelta64`, date/time objects).
- The dtype exemption for an authorized-null column now requires a count
  domain: numeric (not bool) or object. A datetime or timedelta column is
  never exempt.
- None, float NaN and nullable `Int64` `pd.NA` stay authorized. Non-null text
  still fails as a value difference.

Tests in `tests/test_1812_fidelity_oracle.py`:

- `test_temporal_missing_like_count_is_rejected_by_the_real_audit` runs the
  real full audit with only the omitted-post converter mutated, `like_count`
  set to a `pd.Series([pd.NaT])`. On the `a6343d63` helper it did not raise,
  the false green; now it raises.
- `test_temporal_dtype_is_not_exempt_in_an_authorized_null_column` is the same
  at the `compare()` level: red before, green now.
- Controls green on both helpers: `test_numeric_unknown_like_count_stays_authorized`
  (float NaN, nullable Int64 NA, object None) and
  `test_text_like_count_is_still_rejected`.
- The fixed-clock X, wrong-host-local, UTC-midnight, Instagram two-day and
  dtype checks are unchanged and pass: 40 oracle tests in all.
- No product connector, frozen baseline or report code changed.

Verification (Python 3.11.11): social/oracle/notebook-hygiene sweep 1298
passed, 31 skipped. Exception contracts 205 flagged, 0 unlisted, 0 stale; ruff
clean.

## Native urllib3 capture in a full run (CI 42760542058)

`geo without GDAL` failed both capture tests in
`tests/test_instagram_token_exchange_logging.py` with zero captured
`urllib3.connectionpool` records.

- Cause: `tests/django_project/settings.py` `LOGGING` uses
  `disable_existing_loggers=True`. Once that configuration is applied in the
  same process, it disables the origin logger, `urllib3.connectionpool`, so
  that logger emits no records and `caplog` sees nothing.
  - An independent reproduction showed that setting only
    `urllib3.connectionpool.disabled = False` after the same configuration
    makes the old tests pass.
  - The configuration's CRITICAL root level is not the cause; it does not by
    itself block propagated child records.
  - This is a test isolation gap. Redaction did not fail: nothing was
    captured at all.
- Fix (tests only):
  - The capture attaches its own handler to `urllib3.connectionpool`,
    re-enables that logger and clears `logging.disable` for the duration,
    then restores every setting.
  - `test_capture_works_after_logging_was_disabled_by_earlier_setup` starts
    from the disabled, non-propagating state.
- Evidence (pytest-django cannot load the project here without the GIS
  stack, so the same `LOGGING` dict was applied with `dictConfig` in a
  throwaway first test):
  - the committed tests failed exactly as in CI (2 failed, empty capture);
  - the reworked tests pass: 5 passed, which is the 4 committed tests plus
    the 1 throwaway preparation test;
  - against the pre-fix `instagram.py` from `006fc895`, the native test
    still fails on the leaked `client_secret` in urllib3's own request line.

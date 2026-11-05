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

#1458, #1465 and #1474 were written before the current evaluate-ticket
structure (Problem / Evidence / Done-when headings). #1398 is the parent epic
and context only. The exemption covers ticket structure only.

- **#1458** (Instagram connector). Reason: legacy shape. Evidence:
  `tests/test_analytics_instagram_errors.py`, `tests/test_social_review_blockers.py`,
  `tests/test_1812_cumulative_wait_budget.py` and
  `tests/test_social_connectors_cluster.py` pass in the run below.
  Falsification: a #1458 Done-when item has no mapped test in the PR body, or
  a mapped test fails at the head.
- **#1465** (X connector). Reason: legacy shape. Evidence:
  `tests/test_analytics_x_twitter_errors.py` and the X cases of the suites
  above pass in the run below. Falsification: as above.
- **#1474** (Graph insight defaults). Reason: legacy shape. Evidence:
  `tests/test_facebook_business_connector.py` and
  `tests/test_social_connectors_cluster.py` pass in the run below (one
  credential-gated case skips). Falsification: as above.

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

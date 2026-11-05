---
ticket_refs:
  - siege-analytics/siege_utilities#1469: comment posted
---

# Self-review: #1469 / PR #1807 (social report failures, sample labels, unavailable metrics)

## Assumptions
Domain(s): software engineering, analytics reporting
Goal source: #1469 (capped post counts reported as window totals; swallowed connector errors)
Policy source: owner ruling that an unavailable social metric is None/"unavailable", never 0 (a fabricated zero is SU-1)
Plan reference: https://github.com/siege-analytics/siege_utilities/issues/1469#issuecomment-6651274112
Review being answered: https://github.com/siege-analytics/siege_utilities/issues/1469#issuecomment-6260721218 (joint finding with #1812: 13 conflict regions, opposite null policies)
Pre-author-inventory: the Investigation section of the plan reference above

## Scope of this round
`social_media_reports.py` replaces `_zero_if_missing` (and `.get(..., 0)`
defaults, `fillna(0)`) with the companion PR's exact `_known_sum` /
`_format_metric` helpers at every metric site: followers and following, the
summary and metric totals, the followers chart, the likes chart, the
comparison table, the post table, the daily series, the largest-audience
insight and average likes. Known zeros stay 0. Like counts are coerced only
to rank (sort key) and to average, so displayed values keep their source form.
#1807's own scope is unchanged: connector errors raise `SocialMediaError`, the
`posts_limit` option applies, and sample labels remain.

## Peer review (the Junior's checklist)

### writing-code
- Severe flake8 on the changed files -> no output.
- `scripts/check_exception_contracts.py` -> 202 flagged, 0 unlisted, 0 stale.
- `scripts/check_no_stub_docstrings.py` -> OK; `scripts/check_test_file_hygiene.py` -> PASS.
- grep for `_zero_if_missing`, `fillna(0)` and `, 0)` in the module -> none.

### writing-tests
- Red at 5a0d8626 (updated/new tests, old code): pytest -> 13 failed, 15 passed.
  The failures are 9 missing-count cases now asserting "unavailable", the
  absent-key/all-unknown case, the chart-gap case, and 2 nullable daily-series cases.
- After the change: pytest -> 144 passed (test_1469, test_social_media_reports_errors,
  smoke, runtime_guard, sql_safety). After the develop merge: 144 passed again.

### Integration with #1812 (local proof, not committed)
A no-commit merge of #1812's head b7199b4e onto aa501053 produced 7 conflict
regions, down from 13, all in this module and all same-policy wording or
implementation differences. Keeping the #1807 side resolves all 7, and the
resulting file is byte-identical to aa501053. On that integrated tree, both
PRs' social suites gave 281 passed / 6 failed / 1 skipped. Five failures are
#1812 null tests that look up the two titles #1469 relabels ("Top Posts — X
Twitter", "Total Likes by Platform"). With only those literals updated, the
result is 286 passed / 1 failed / 1 skipped, and every #1812 null-value
assertion passes. The remaining failure is #1812's fidelity oracle, which pins
the old executive-summary wording. The merge was aborted, and the tree is
clean at the #1807 head.

### writing-claims
- The counts are pytest summary lines from this work cycle.

## Lead review
The two PRs now share one null policy. Whichever PR merges second takes this
module from #1807, updates the two title literals in
`tests/test_social_media_reports_nulls.py`, and authorizes the #1469 wording
diffs in `scripts/check_social_review_fidelity.py`. This PR does not touch
#1812's files. `notebooks/analytics/03_social_media_analytics.ipynb` builds the
payload from complete fixture metrics; its contract is unchanged, so no
notebook edit is needed.

## Rework ledger
- a15ae436/5a0d8626: unknown counts rendered as 0. Fixed in aa501053 per the ruling.
- The 4.1.0 Changed and Fixed notes are restored to CHANGELOG.md, and the Fixed note states the policy.

## Findings
The ruling is applied. Integration follow-ups for the second merger are listed in the Lead review.

## Ticket-fitness exemption

Governing tickets: #1469 and #1461. The #1398 epic is context only.

### #1469
Reason: #1469 predates the canonical ticket template. Its body uses Problem / Evidence / Failure scenario / Done when / Assumptions / Falsifier / Related instead of Context / Goal / Acceptance, and it links no /think design note.
Evidence: https://github.com/siege-analytics/siege_utilities/issues/1469 states the capped-total, silent-zero and None-crash defects under "## Problem", the citations under "## Evidence" (`reporting/social_media_reports.py`), and the done-when criteria under "## Done when". The reviewer verdict is https://github.com/siege-analytics/siege_utilities/issues/1469#issuecomment-6260721218.
Falsification: revert the implementation; `tests/test_1469_social_media_report_totals.py::test_connector_failure_raises_with_platform_and_cause` goes red because a connector failure becomes an empty frame instead of `SocialMediaError`, `::test_post_counts_and_engagement_are_labeled_as_samples` goes red because 120 posts are reported as window totals, and `::test_missing_counts_render_unavailable_never_zero` goes red because an unavailable follower count renders as "0".

### #1461
Reason: #1461 predates the canonical ticket template (Problem / Evidence / Failure scenario / Done when / Assumptions / Falsifier / Related; no Context / Goal / Acceptance, no /think link). This PR does not implement it: `create_social_media_report` still calls `create_analytics_report(report_data, title)` unchanged, and the #1469 tests mock that writer.
Evidence: https://github.com/siege-analytics/siege_utilities/issues/1461 (OPEN) states the swapped `ReportGenerator` signature under "## Problem" and cites `reporting/social_media_reports.py:92-96` and `reporting/report_generator.py:94-183` under "## Evidence". `git diff origin/develop...HEAD -- siege_utilities/reporting/social_media_reports.py` shows no change to the `create_analytics_report` call.
Falsification: there is no test in this PR that goes red for #1461, because the PR leaves its defect in place. This exemption is wrong if reverting this PR changes the report writer call, or if a #1807 test asserts that a PDF is written.

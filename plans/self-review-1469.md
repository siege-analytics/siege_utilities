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

### Round 2026-11-13: develop 6c049c2c integration
All results below are from the integrated, uncommitted tree. The interpreter was Python 3.11.11 (pandas 2.3.3, numpy 2.4.2), and it imported `social_media_reports` from this worktree.
- writing-code: `ruff check` on the five placed files → All checks passed (which also proves they parse). `check_exception_contracts.py --list` → 200 flagged, 0 unlisted, 0 stale. `check_credential_urls.py` → 0 unreviewed sites. `check_test_file_hygiene.py` → PASS (run from the repository root). `check_secret_literals.py` → PASS, 0 violations in 395 files. `check_no_stub_docstrings.py` → OK.
- writing-tests: the directly relevant selection was test_1469, report nulls, the fidelity oracle, report errors, the null-policy end-to-end test, social review blockers, the #1404 Census fallback, dual-source 1375, summary file 1385 and `tests/guard`. pytest → 461 passed. The wider social connector selection (Instagram paging and redirects, wait budgets, Instagram and X errors, Facebook, token-exchange logging, the connectors cluster, Vista, the X budget) gave pytest → 335 passed, 2 skipped. Both skips are `requires_api_key` with no credentials file (`test_facebook_business_connector.py:84`, `test_vista_social_connector.py:127`). They are skips, not passes.
- writing-tests (red on revert, on the integrated tree): with the module swapped to the pre-guard composition (sha256 70329e61), `test_1469_social_media_report_totals.py` → 8 failed, 38 passed. Every failure is an `inf` or `-inf` rendered in the report payload. After restoring the guarded module (sha256 edb368e1, re-hashed), the same file → 46 passed.
- writing-claims: every count above is a pytest or guard summary line from this cycle. The fidelity oracle's seeded manifest controls are part of `tests/test_1812_fidelity_oracle.py`, inside the 461.

## Lead review
The two PRs now share one null policy. Whichever PR merges second takes this
module from #1807, updates the two title literals in
`tests/test_social_media_reports_nulls.py`, and authorizes the #1469 wording
diffs in `scripts/check_social_review_fidelity.py`. This PR does not touch
#1812's files. `notebooks/analytics/03_social_media_analytics.ipynb` builds the
payload from complete fixture metrics; its contract is unchanged, so no
notebook edit is needed.

## Security: connector error text and causes (reviewer finding at 3cd937ba)
Finding: `_collect_platform_data` wrapped connector failures as
`SocialMediaError(f"...: {exc}") from exc`. A connector error carrying
`?access_token=...` in a request URL exposed the token in `str(error)` and in
the formatted traceback. The previous code swallowed the error, so this PR
introduced the disclosure.

Fix (0f301a56): `_retrieval_error(operation, platform, exc)` builds
`Failed to get <operation> from <platform> (<ExceptionType>)` with no
exception text, and each site raises it `from None`, so `__cause__` is None and
`__suppress_context__` is True. URL redaction alone was not used, because it
does not cover header or body tokens such as `Authorization: Bearer ...`.
The error path has no logging call; the only log line names the platform.

Tests: `test_1469_social_media_report_totals.py::test_connector_failure_raises_with_platform_and_category`
(replaces the old `__cause__ is cause` contract) and
`::test_connector_failure_never_exposes_secrets` (dummy secret in a URL and in
a bearer header, for account info, insights and posts; asserts absence from
str, repr, `traceback.format_exception` and caplog after `log.exception`).
`test_social_media_reports_errors.py::test_collect_platform_data_raises_on_connector_failures`
gets the same contract.

Observed red/green (2026-11-05). Command:
`git checkout db3eaa4d -- siege_utilities/reporting/social_media_reports.py && (cd tests && python -m pytest -o addopts="" -p no:cacheprovider --rootdir=.. -q test_1469_social_media_report_totals.py::test_connector_failure_raises_with_platform_and_category test_1469_social_media_report_totals.py::test_connector_failure_never_exposes_secrets test_social_media_reports_errors.py); git checkout HEAD -- siege_utilities/reporting/social_media_reports.py`
- At `db3eaa4d`: 13 failed, 0 passed.
- At the fix head: 13 passed. The wider selection (test_1469, report errors, smoke, runtime guard, sql safety) gave 150 passed. Exception contracts: 202 flagged / 0 unlisted / 0 stale. `check_secret_literals.py`: 0 violations.

## Review round: CodeRabbit 4499070041 and 4499070047 (2026-11-10)

Develop sync first: `13405c8a` merges develop `71f02b0b` for a positional CHANGELOG conflict (the #1444 and #1469 Fixed entries). Both are kept, and a diff against develop deletes 0 develop lines. No already-merged develop behaviour disagrees with this PR.

- 4499070041 (`social_media_reports.py:205`): the protocol allows text counts, so a `followers_count` of `"1200"` reached `sum` and raised `TypeError`. Fixed in `4fbc80fe`: `_numeric_count` converts numeric text, renders unparseable text as unavailable (`None`), and returns an `int` for integral values. Every section reads counts through `_followers`/`_following`: summary, metrics, followers chart, comparison table and largest-audience insight. A grep finds no other raw `followers_count`/`following_count` read in the module.
- 4499070047 (`social_media_reports.py:419`): with a repeated index label, `posts.loc[label]` returned several rows, and `int()` of them raised `TypeError`. Fixed in `4fbc80fe`: the row and like count are selected by position (`reset_index(drop=True).idxmax()`, `iloc`).
- Tests: `test_1469_social_media_report_totals.py::test_string_account_counts_are_normalized_in_every_section` (parametrized over `"1200"` and `"1200.0"`) and `::test_top_post_is_selected_by_position_with_duplicate_index_labels`.
- Red/green, command: `git checkout 13405c8a -- siege_utilities/reporting/social_media_reports.py`; `(cd tests && python -m pytest -o addopts="" -p no:cacheprovider --rootdir=.. -c ../pyproject.toml -q test_1469_social_media_report_totals.py -k "string_account_counts or duplicate_index")`; `git checkout HEAD -- siege_utilities/reporting/social_media_reports.py`. At `13405c8a`: 3 failed. At `4fbc80fe`: 3 passed, and the worktree was clean afterwards.
- Wider check at `4fbc80fe`: test_1469, report errors, smoke, runtime guard, sql safety, release process, changelog export, analytics datetime and 1661 notebook connector truth gave 234 passed. Severe flake8 is clean. Exception contracts: 202 flagged / 0 unlisted / 0 stale. Stub docstrings: OK. `check_test_file_hygiene.py` was not validly run: from `tests/` it flags every file in the repository, because it resolves paths relative to the working directory.
- Classification: on v4.0.0 both inputs crashed, so no caller could rely on the old behaviour. The fix extends the existing 4.1.0 Fixed entry, and the BREAKING entries are unchanged.

## Review round: develop 6c049c2c integration (2026-11-13)

Working as: software engineer, tech lead
Goal source: #1469, and the integration plan posted at https://github.com/siege-analytics/siege_utilities/issues/1469#issuecomment-6840828280
Investigate-artifact: https://github.com/siege-analytics/siege_utilities/issues/1469#issuecomment-6840828280 (Investigation section)
Pre-mortem-artifact: https://github.com/siege-analytics/siege_utilities/issues/1469#issuecomment-6840828280 (Pre-mortem section)
Hostile-review-artifact: https://github.com/siege-analytics/siege_utilities/issues/1469#issuecomment-6260721218 (the PR's independent review). In a later round, the same independent reviewer accepted the finite-count guard and the oracle manifest by exact sha256 (below). An independent review of the new head is still pending and will follow publication.
Project-contribution: the social report module reaches develop with one null policy shared with the companion null-policy work, and the fidelity oracle now pins every rewritten baseline occurrence by fixture, rule, slot kind and path, so downstream report consumers get unavailable counts instead of fabricated zeros or infinities.

Scope. This merges develop 6c049c2c (merge base 71f02b0b). The merge brings in develop's social oracle and null-policy work and the #1791 Census retry and fallback fix. No behavior is added beyond what was already reviewed.

Conflicts, from `git merge --no-ff --no-commit`: exactly `CHANGELOG.md` and `siege_utilities/reporting/social_media_reports.py`. `scripts/exception_contracts_allowlist.json` auto-merged. No other path conflicted.

Resolution. Each placed file was checked by sha256 against the independently reviewed value, before and after placing it:
- `siege_utilities/reporting/social_media_reports.py`: edb368e13e66ccf35916c46f1f20f9513fb8073ca340747cd3d1467bafeda612. This is the integrated module plus the finite-count guard: after `pd.isna`, a floating value that is not finite is unavailable. It is not hand-merged and does not take either whole side.
- `scripts/check_social_review_fidelity.py`: 0cc954568ab432221e8492ba81bb05abf64aaa09f2de1e74c8d0674c94e85cc3. The oracle has a literal 24-occurrence manifest keyed by fixture, rule, slot kind and original baseline path, compared with exact Counter equality.
- `tests/test_1812_fidelity_oracle.py`: d9ab912511caa94ab00d5a5df4eba833fbfd3ff626b4e7a9a64eb645ffeb1cb7 (seeded manifest controls).
- `tests/test_1469_social_media_report_totals.py`: 86ec9f7f56bb9212f4757a697768cbab272a84bd84a417b4a4ee3cf69712ff4b (nine finite-count cases added).
- `tests/test_social_media_reports_nulls.py`: 05fad46cecb6515960e0f96ddab225573471fdd69ebf5075473206e73e8f55aa. This file is called out explicitly: it is outside the reviewed hash list above. It is the mechanical consequence of this PR's relabels. Two title literals change ("Top Posts — X Twitter" becomes "Top analyzed posts — X Twitter"; "Total Likes by Platform" becomes "Likes from analyzed posts by Platform"). Without the change, develop's null-policy test fails on the merged tree. No assertion value changes.
- `scripts/exception_contracts_allowlist.json`: the auto-merge result, blob 0afcd5938a61cf18e1b0ef08d79242a42e65b152 (sha256 83aee513b8aef86c20e188dd437923680a2c812efacd8472b8475962adcc8e4e). It equals develop minus this PR's five `_collect_platform_data` entries, and the exception-contracts guard reports 0 unlisted and 0 stale.
- `CHANGELOG.md`: a develop-first verbatim union. A diff against develop's file shows additions only: this PR's #1469 Fixed entry after the #1474 entry, and its two #1469 BREAKING entries after the #1404 Census entry. All develop lines are kept, including the Census retry and fallback text.

Evidence: see "Round 2026-11-13" under Peer review.

Not done in this step: no local full-suite run (the full suite is CI's exact-head run after publication). No notebook execution: `notebooks/analytics/03_social_media_analytics.ipynb` uses `SocialMediaReportGenerator`, but a grep finds none of the relabeled titles under `notebooks/`.

Open reviewer question (no change made): the #1469 CHANGELOG Fixed entry says counts that are "NaN, text or unparseable" render as unavailable. The finite-count guard also makes `inf`, `-inf`, `"inf"` and `"Infinity"` unavailable, and the entry does not mention it. The accepted wording is kept as is. Whether to add the non-finite case is left to the reviewer.

Inherited limits (unchanged, disclosed): `pd.to_numeric` turns the integer 10**30 into an inexact float, and an integer above float range such as 10**400 raises `OverflowError`. Ties for the largest audience go to the first platform in input order. The guard adds no float conversion, and a 2**63+1 case pins exact large-integer formatting.

## Rework ledger
- a15ae436/5a0d8626: unknown counts rendered as 0. Fixed in aa501053 per the ruling.
- The 4.1.0 Changed and Fixed notes are restored to CHANGELOG.md, and the Fixed note states the policy.
- 3cd937ba/db3eaa4d: connector text and causes leaked into the error. Fixed in 0f301a56; the CHANGELOG Changed note is reworded.
- Classification (operator rule 2026-11-06: if a change alters v4.0.0 caller behaviour, it is BREAKING). Two #1469 changes do: `create_social_media_report` raises `SocialMediaError` where 4.0.0 logged and built a PDF from empty data, and missing counts render `unavailable`/`None` where 4.0.0 rendered `0`. Both move to 4.1.0 BREAKING with Migration lines, together with the "analyzed" label renames. The NaN-crash and `nan`-display fix stays under Fixed, because no caller could rely on it. `posts_limit=50` matches the 4.0.0 fixed limit and is additive. No code changed.
- 21957ef7: the BREAKING entries named a nonexistent `generate_report` method (finding by a second implementer, hub-verified). The public method is `create_social_media_report`. Corrected in the CHANGELOG, this ledger and the PR body. No code changed.

## Findings
The ruling is applied. Integration follow-ups for the second merger are listed in the Lead review.

## Ticket-fitness exemption

Governing ticket: #1469. The #1398 epic is context only.

Refs #1461 (context; not implemented by this PR; create_social_media_report → create_analytics_report path unchanged). Per the coordinator ruling, #1461 is context for this PR and not a governing ticket, so it has no exemption block or falsifier. The PR does not close it.

### #1469
Reason: #1469 predates the canonical ticket template. Its body uses Problem / Evidence / Failure scenario / Done when / Assumptions / Falsifier / Related instead of Context / Goal / Acceptance, and it links no /think design note.
Evidence: https://github.com/siege-analytics/siege_utilities/issues/1469 states the capped-total, silent-zero and None-crash defects under "## Problem", the citations under "## Evidence" (`reporting/social_media_reports.py`), and the done-when criteria under "## Done when". The reviewer verdict is https://github.com/siege-analytics/siege_utilities/issues/1469#issuecomment-6260721218.
Falsification: revert the implementation; `tests/test_1469_social_media_report_totals.py::test_connector_failure_raises_with_platform_and_category` (named `..._and_cause` before `0f301a56`) goes red because a connector failure becomes an empty frame instead of `SocialMediaError`, `::test_post_counts_and_engagement_are_labeled_as_samples` goes red because 120 posts are reported as window totals, and `::test_missing_counts_render_unavailable_never_zero` goes red because an unavailable follower count renders as "0".
Observed revert results (2026-11-05). Command, with `REV` set to the revert target and `TESTS` set to the named tests:
`git checkout REV -- siege_utilities/reporting/social_media_reports.py && (cd tests && python -m pytest -o addopts="" -p no:cacheprovider --rootdir=.. -q TESTS); git checkout HEAD -- siege_utilities/reporting/social_media_reports.py`
- `REV=dc7d3f76` (develop), with `TESTS` = `test_1469_social_media_report_totals.py::test_connector_failure_raises_with_platform_and_cause`, `::test_post_counts_and_engagement_are_labeled_as_samples` and `::test_missing_counts_render_unavailable_never_zero`: 17 failed, 0 passed.
- `REV=5a0d8626` (pre-ruling head), with `TESTS` = `::test_missing_counts_render_unavailable_never_zero` and `::test_absent_and_all_unknown_counts_render_unavailable`: 10 failed, 0 passed.
- Current-head green: after the file was restored, `(cd tests && python -m pytest -o addopts="" -p no:cacheprovider --rootdir=.. -q test_1469_social_media_report_totals.py)` gave 28 passed. The worktree was clean.
- Name change: these 2026-11-05 runs used `test_connector_failure_raises_with_platform_and_cause`. The credential fix `0f301a56` later renamed it `test_connector_failure_raises_with_platform_and_category`, because the error no longer chains a cause. The 2026-11-10 review round above gives the current-head green for the whole file.

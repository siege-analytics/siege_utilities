---
ticket_refs:
  - siege-analytics/siege_utilities#1444: comment posted https://github.com/siege-analytics/siege_utilities/issues/1444#issuecomment-6651398971
---

# Self-review: #1444 / PR #1778, release note placement and non-closing reference

Working as: software engineer

Goal source: https://github.com/siege-analytics/siege_utilities/issues/1444#issuecomment-6257165128 (required changes 1 and 2)
Review-Tier: C (task classifier floor: the branch diff against main includes `.github/workflows/`)
Pre-author-inventory: https://github.com/siege-analytics/siege_utilities/issues/1444#issuecomment-6651365577 (fact sheet: body keyword, commit messages, CHANGELOG placement)
Investigate-artifact: https://github.com/siege-analytics/siege_utilities/issues/1444#issuecomment-6651365577
Pre-mortem-artifact: https://github.com/siege-analytics/siege_utilities/issues/1444#issuecomment-6651365577
Hostile-review-artifact: WAIVED

## Hostile-review-waiver

Reason: this commit changes only `CHANGELOG.md` placement and adds this artifact; no executable code changes, and the code at this head was already verified by the independent reviewer at `adac594e`.
Scope: `CHANGELOG.md` (move of the #1444 entry from `[Unreleased]` to `[4.1.0]` Fixed, text unchanged) and `plans/self-review-1444-metadata.md`.
Compensating-control: the 297-test analytics set rerun after the develop merge; the independent exact-head re-review requested after push; a check that the PR has no closing-issue reference.

## Ticket-fitness exemption

### #1444

Reason: #1444 predates the canonical ticket template; it was filed before `evaluate-ticket.sh` gating, and this PR covers only part of it (the Facebook part is #1435 / PR #1774).
Evidence: Problem, Evidence, Failure scenario, Done when, Assumptions and Falsifier sections live in https://github.com/siege-analytics/siege_utilities/issues/1444; the reviewer verdict is https://github.com/siege-analytics/siege_utilities/issues/1444#issuecomment-6257165128.
Falsification: revert the implementation; `tests/test_analytics_datetime.py::test_instagram_insights_use_covered_day` goes red because daily values carry the next day's end-of-period date instead of the covered day.
Verified 2026-11-05: with `siege_utilities/analytics/instagram.py` checked out from `origin/develop`, `pytest tests/test_analytics_datetime.py -k test_instagram_insights_use_covered_day` -> 6 failed (`test_analytics_datetime.py:92` date-label mismatch, including leap-day and year boundaries); after `git checkout HEAD --` -> 6 passed, worktree clean.

## Assumptions

1. 4.1.0 is held and untagged, so the #1444 note belongs in `[4.1.0]`.
2. #1444 must stay open until both this PR and #1774 (#1435, Facebook measured day) are integrated and verified.

## Test plan

- After merging develop `dc7d3f76`: `pytest tests/test_analytics_datetime.py tests/test_analytics_pipeline.py tests/test_analytics_instagram_errors.py tests/test_credential_url_leak.py tests/test_social_media_reports_errors.py` with host timezone America/Chicago -> 297 passed (the reviewer's count at `adac594e`).
- No code changed in this commit; the merge brought only develop's changes.

## Peer review

- Shelves: writing-claims:1 (the body states only verified behavior), writing-releases (note in the held release section, boundary checked).
- Syntax check: N/A (no `.py` changes in this commit).
- Test suite: 297 passed (exit 0).
- Findings: the #1444 entry sits at `CHANGELOG.md:121-132`, inside `[4.1.0]` (`:34`) and before `[4.0.0]` (`:749`); its text is unchanged. None of the branch commit messages carries a closing keyword.
- Notebook API: N/A.

## Lead review

- The auto-close risk lives in the PR body, which is metadata and is edited separately to `Part of #1444`, naming PR #1774 / #1435.
- Post-mortem: not applicable; nothing reached a published version.

## Quantified claims

- 297 passed post-merge.

## Rework ledger

None.

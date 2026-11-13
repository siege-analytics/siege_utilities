---
ticket_refs:
  - siege-analytics/siege_utilities#1623: comment posted https://github.com/siege-analytics/siege_utilities/issues/1623#issuecomment-6799974359
---

# Self-review: #1623 seat uniqueness (PR #1755)

Ticket: siege-analytics/siege_utilities#1623

Review-Tier: C (a schema migration that can fail on existing deployed data).

## Assumptions
Working as: software engineer (Junior) and data engineer (Lead).
Domain(s): software engineering, data engineering.
Geospatial cross-cut: yes (GeoDjango models; the affected tests need GDAL and PostGIS).
Goal source: #1623 "Done when": uniqueness includes `senate_class`, a single PRESIDENT seat is enforced, and a migration ships with the change.
Goal source verification: not run (no ticket-evaluation script was executed in this review pass).
Plan reference: https://github.com/siege-analytics/siege_utilities/issues/1623#issuecomment-6799974359 (Junior task description).
Pre-author-inventory: https://github.com/siege-analytics/siege_utilities/issues/1623#issuecomment-6799974359 (Investigation).
Investigate-artifact: https://github.com/siege-analytics/siege_utilities/issues/1623#issuecomment-6799974359
Pre-mortem-artifact: https://github.com/siege-analytics/siege_utilities/issues/1623#issuecomment-6799974359
Hostile-review-artifact: https://github.com/siege-analytics/siege_utilities/issues/1623#issuecomment-6800282408 (independent fresh-context senior review, with responses). This file is the author's record, not a pass. Independent whole-PR review and the merge decision happen outside it, on the exact final head.
Project-contribution: the political seat model can hold both U.S. Senate seats of a state and exactly one presidency. Applying the migration to data that violates the presidency rule stops with a precise, non-destructive report.

The original implementation (`15579261`, commit dated 2026-10-18) had no investigation, pre-mortem or hostile review. Those remain absent for that round. This file records the current review pass only.

## Current integration round (develop 79f37f4d)

Merge of develop `79f37f4df28059a875c8dbf84cf77ce86812bdbb` into the PR branch at `15579261182e0d68914426058d72c37222bd6e82`. The merge base is `e16c03f977b27ec80eaf36e40ea47bb6750382bd`.

- **Conflicts:** `CHANGELOG.md` only, in the `[Unreleased]` / Fixed hunk. No source, test, migration or workflow file conflicted.
- **Resolution:** develop's entries first (#1667, #1507), then the branch's only entry (#1623) verbatim.
- **Judgment call:** the branch side of the hunk also held the #1468 entry. That entry is merge-base content, not a branch change, and develop had moved it into `[5.0.0]`. A literal union of both sides would list it twice, so it is kept once, where develop placed it.
- **Develop content arriving through the merge:** includes develop's own `.github/actions/apt-install/action.yml` and `.github/workflows/ci.yml` changes. No workflow file is edited by this branch.
- **Migration graph:** develop adds no `siege_geo` migration after `0019_demographic_geoid_keys`, so `0020_seat_uniqueness` remains the single leaf.
- **Verification:**
  - `git diff --stat 79f37f4d <merged tree>`, excluding this file, lists exactly the branch's five original files: `CHANGELOG.md`, the 0020 migration, `temporal_political.py`, `tests/test_district_geoid_constraints.py` and `tests/test_django_temporal_models_orm.py` (+130/-7, the same as the PR's own diff).
  - The branch's code and test files are byte-identical to `15579261`.
- **Tests for this commit:** none were executed locally. The affected modules need GDAL and PostGIS, which are not available to the local test settings in this pass. The evidence is the exact-final-head CI run. The geospatial-library install step has recently failed on another PR's run (cause unconfirmed); if that recurs, the database tests stay not run.

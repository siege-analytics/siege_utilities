# Self-review: PR #1817 place-history overlays (#1466), integration round

Review-Tier: C (shared geo overlay contracts consumed by place_history).

## Assumptions
Working as: software engineer (Junior) and geo-platform tech lead (Lead).
Domain(s): software engineering (geo overlays, redistricting spans).
Geospatial cross-cut: yes (state FIPS scoping, redistricting effective dates).
Goal source: the #1466 Problem/Done-when and the PR #1817 body. Code at 2b63a9f7 closed the independent review's cross-state span finding, and the hub records an earlier local PASS on code. This round is integration only: develop sync, canonical CHANGELOG.md note, this artifact, exact-head CI. No library behavior changes.
Plan reference: docs/verification/self-review-1817.md#pre-mortem
Pre-author-inventory: docs/verification/self-review-1817.md#investigation
Investigate-artifact: docs/verification/self-review-1817.md
Pre-mortem-artifact: docs/verification/self-review-1817.md
Hostile-review-artifact: PR #1817 body, section "Cross-state span fix (head 2b63a9f7)", which covers the independent review's finding and fixture. Re-review of the integration head is pending; this is NOT a pass of it.
Project-contribution: place-history overlays return correctly scoped, correctly dated election, redistricting and seat context for a place.

## Investigation
- PR files (5): `siege_utilities/geo/overlays/election_results.py`, `redistricting.py`, `seats.py`, `tests/test_1466_place_history_overlays.py`, `tests/test_1817_cross_state_span.py`.
- `election_results.py` and `redistricting.py`: `state_fips` is mapped through `FIPS_TO_STATE` before matching, so numeric FIPS codes filter correctly. `redistricting.py` adds `_has_nonempty_span`, raises `ValueError` on inverted spans, and filters by state before validating spans. `seats.py` adds `_current_districts_at` for the group selection rule.
- At 2b63a9f7 there was no CHANGELOG.md entry; the body had only a bullet list. The owner's criteria on #1484 (issuecomment-6649267710) state that a PR-body note alone is not the adopted location.
- The branch was BEHIND develop dc7d3f76, with a positional CHANGELOG.md conflict against #1463.

## Pre-mortem
1. Tiger (launch-blocking). Severity: P1. The develop merge alters overlay code. Mitigation: `git diff 2b63a9f7` on the five PR paths is empty after the merge, and the tree differs from develop only in those files.
2. Paper Tiger. Severity: P2. The CHANGELOG entry overstates scope, for example the PlanDistrict-equivalence seam, which is pending an operator decision. Mitigation: the entry lists only the fixes in the body and uses `Refs`.
3. Paper Tiger. Severity: P2. A positional CHANGELOG conflict. Mitigation: the entry is at the end of `[4.1.0]` / `### Fixed`; merge-tree is checked.
4. Elephant. Severity: P3. Known DuckDB 2.0 CI failures until the pin lands (#1861/#1863). Labelled, not chased.

## Peer review (Junior: shelves, gates)
- Shelves: release-note discipline (canonical entry); SU-2 (the entry states the inclusive-years versus half-open-dates difference instead of implying one convention).
- Gate 1 (syntax): no Python changed in this round; pytest imported the PR modules -> 360 passed.
- Gate 2 (tests): pytest on the merged tree -> 360 passed, 5 failed. All 5 failures are `django.core.exceptions.ImproperlyConfigured: Could not find the GDAL library` on the no-provider paths, because the local Django GIS cannot locate GDAL. `tests/test_redistricting_models.py` and `tests/test_redistricting_plan_status.py` fail the same way and were not run to completion locally. Hosted CI provides GDAL.
- Gate 3 (guards): lint ratchet phases 1 to 4 against develop dc7d3f76 (recorded in the PR body).
- Gate 4 (docs/notebooks): CHANGELOG.md only.

## Lead review (adversarial)
Phase A coherence: each CHANGELOG clause maps to a body bullet or to the "Behavior change vs develop" section (Case 5).
Phase B verification: the PR files are identical to 2b63a9f7, so the independent review's findings and fixtures still apply.

## Findings
| ID | Priority | Description | Resolution |
|----|----------|-------------|------------|
| F1 | P2 | Release note only in the PR body | canonical CHANGELOG.md entry added |
| F2 | P3 | Branch behind develop with a positional CHANGELOG conflict | additive merge, develop entry kept |
| F3 | P3 | GDAL-dependent tests cannot run in this local environment | disclosed; hosted CI covers them |

## Test plan / Quantified claims
Interpreter: ~/.pyenv/versions/default_31111/bin/python (Python 3.11.11), merged tree.
- `python -m pytest tests/test_1466_place_history_overlays.py tests/test_1817_cross_state_span.py tests/test_demographics_overlay.py tests/test_events_overlay.py tests/test_overlay_registry.py tests/test_place_history.py tests/test_rdh_overlays.py tests/test_redistricting_data_hub.py tests/test_seats_overlay.py tests/test_urbanicity_overlay.py tests/test_release_process.py tests/test_user_config_export_changelog.py --no-cov` -> 360 passed, 5 failed (all GDAL `ImproperlyConfigured`, listed above).
- `git diff --stat origin/develop` -> the 5 PR files; `git diff 2b63a9f7` on those paths -> empty.

## Ticket-fitness exemption

writing-rules:4 exemption for the governing ticket. The #1398 epic is context only.

### #1466
- **Reason:** #1466 predates the canonical ticket template. It uses Problem / Evidence / Failure scenario / Done when / Assumptions / Falsifier sections, so `evaluate-ticket.sh` does not accept it as written.
- **Evidence:** the problem, the evidence and the done-when criteria live in the #1466 body under `## Problem`, `## Evidence` (with the `ElectionReturn`/`DistrictAssignment` fixture) and `## Done when`. The PR #1817 body records the earlier independent review: its cross-state finding and fixture, the behavioral red-first, and the selection rule. No public reviewer verdict for this PR exists yet; the review request is at https://github.com/siege-analytics/siege_utilities/pull/1817#issuecomment-6259734028. Investigation, pre-mortem and Junior/Senior records are on the ticket at issuecomment-6651154786 and issuecomment-6651204533.
- **Falsification:** revert the implementation's filtering (restore `siege_utilities/geo/overlays/election_results.py` and `redistricting.py` from develop) and `tests/test_1466_place_history_overlays.py::test_state_fips_matches_state_abbreviations[election]` goes red, because a numeric `state_fips` returns `[]` instead of the matching Texas election return. `test_inverted_redistricting_span_raises[provider]` goes red because no `ValueError` is raised. This was verified on 2026-11-05: 11 failed and 38 passed; with the files restored, 49 passed. Reverting `seats.py` as well makes the module fail to import, because `_current_districts_at` is new in this PR.

## Rework ledger
Empty.

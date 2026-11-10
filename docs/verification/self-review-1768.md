# Self-review: PR #1768 plan lifecycle resolution (#1442), pre-flight

Review-Tier: C (the checkout's path floor; this commit adds documentation only, and the code under review is `siege_utilities/geo/plan_lifecycle.py` at `fd21ca8f`).

## Assumptions
Working as: software engineer (Junior) and release tech lead (Lead).
Domain(s): redistricting plan lifecycle (temporal resolution), Python library API.
Geospatial cross-cut: no (no geometry; dates and statuses only).
Goal source: the #1442 Problem / Done when / Falsifier sections.
Plan reference: https://github.com/siege-analytics/siege_utilities/issues/1442#issuecomment-6761041236
Investigate-artifact: https://github.com/siege-analytics/siege_utilities/issues/1442#issuecomment-6761041236
Pre-mortem-artifact: https://github.com/siege-analytics/siege_utilities/issues/1442#issuecomment-6761041236
Hostile-review-artifact: none yet. An independent exact-head review of the pushed commit is pending; this is NOT a pass.
Project-contribution: `resolve_plan_at` returns the plan actually in force, so attribution by election date uses the right map.

## Investigation
- `siege_utilities/geo/plan_lifecycle.py` at `v4.0.0` is identical to the merge-base `7f534f6c` (empty `git diff --stat v4.0.0 7f534f6c -- siege_utilities/geo/plan_lifecycle.py`). On it, `ACTIVE_STATUSES` includes `STAYED` (`:72-76`) and `latest_event` / `status_at` use `max(..., key=effective_date)` (`:139`, `:158`).
- At `fd21ca8f`, `STAYED` is removed from `ACTIVE_STATUSES` and both selectors use `(effective_date, _LIFECYCLE_STAGE_ORDINAL[status])`.
- `ACTIVE_STATUSES` is in `__all__`, so the change is caller-visible. `siege_utilities/geo/django/models/redistricting.py:103` already uses `("enacted", "challenged")`.
- Sibling search over `siege_utilities/`: no other effective-date max selection or stayed-as-active logic.
- Develop `2deb6a1f` changed neither touched file since the merge-base; `git merge-tree --write-tree origin/develop HEAD` produced a tree with no conflicts.
- Review threads on PR #1768: 0.

## Pre-mortem
1. Tiger (launch-blocking for release notes). Severity: P1. The change ships labelled as a non-breaking fix. Mitigation: the PR body CHANGELOG block moves to `### BREAKING` with a Migration line.
2. Tiger (fast-follow). Severity: P2. CI predates 81 develop commits. Mitigation: this additive commit triggers a full run.
3. Paper Tiger. Severity: P3. A develop conflict. Mitigation: the trial merge is clean.
4. Elephant. Severity: P3. External callers relying on stayed-as-active. Mitigation: disclosed via the Migration line.

## Peer review (Junior: shelves, gates)
- Shelves: SU-2 (does it do what it says: the module docstring and `resolve_plan_at` docstring now state stayed/challenged semantics and same-date ordering); SU-1 (no empty-on-error paths touched).
- Gate 1 (syntax): no Python changed in this commit.
- Gate 2 (tests): `tests/test_plan_lifecycle.py tests/test_smoke.py tests/test_runtime_guard.py tests/test_sql_safety.py` with `--no-cov -p no:randomly`: 189 passed.
- Gate 3 (docs): this record; the #1442 entry in `CHANGELOG.md` `[4.1.0]` under `### BREAKING` (with the Migration line), mirrored exactly in the PR body. The entry was added at the end of the last `[4.1.0]` `### BREAKING` list, a region develop has not changed; `git merge-tree` with develop is recorded in the PR body.
- Notebook impact (SU-4a): `grep -rln "plan_lifecycle|resolve_plan_at|ACTIVE_STATUSES|was_active_at" notebooks/` finds no notebook. No notebook update is needed; the absence of a lifecycle demonstration is a pre-existing documentation gap.

## Lead review (adversarial)
Phase A coherence: the two #1442 defects map to the two code changes (the `ACTIVE_STATUSES` membership and the tie-break key).
Phase B verification:
- Red: with `siege_utilities/geo/plan_lifecycle.py` checked out from `v4.0.0` and the new tests in place, `TestPlanLifecycleResolutionRegressions` gives 19 failed / 16 passed.
- After: the head file restored; the same class gives 35 passed.
- Composition: `PlanLineage.plan_at` and `resolve_plan_at` both read `ACTIVE_STATUSES` through `was_active_at`, so the stayed exclusion applies on both paths. `TERMINAL_STATUSES` is unchanged.

## Findings
| ID | Priority | Description | Resolution |
|----|----------|-------------|------------|
| F1 | P2 | PR body says "no public symbols change" and "[Unreleased]" | body corrected: BREAKING + Migration, CHANGELOG [4.1.0] block |
| F2 | P2 | PR body interpreter location is a local path | replaced with "local Python 3.11.11" / `python` |
| F3 | P3 | PR body lacks the ticket-fitness exemption block | added to the body |

## Ticket-fitness exemption

writing-rules:4 exemption for the governing ticket.

### #1442
- **Reason:** #1442 predates the canonical ticket template. It uses Problem / Evidence / Failure scenario / Done when / Assumptions / Falsifier sections.
- **Evidence:** the defects, the v4.0.0 probe and the acceptance criteria live in the #1442 body. This round's investigation, pre-mortem and Junior/Senior review are at https://github.com/siege-analytics/siege_utilities/issues/1442#issuecomment-6761041236.
- **Falsification:** restore `siege_utilities/geo/plan_lifecycle.py` from `v4.0.0`. Then `tests/test_plan_lifecycle.py::TestPlanLifecycleResolutionRegressions` fails 19 of 35, including the stayed-successor fallback and same-date ordering in both selectors. Verified on 2026-11-10.

## Test plan / Quantified claims
Interpreter: local Python 3.11.11, run from the repository root.
- `python -m pytest tests/test_plan_lifecycle.py tests/test_smoke.py tests/test_runtime_guard.py tests/test_sql_safety.py --no-cov -q -p no:randomly`: 189 passed.
- Revert check as above: 19 failed / 16 passed on `v4.0.0`; 35 passed on the head.

## Rework ledger
- Pre-flight round, 2026-11-10: no code change; classification corrected to BREAKING; body hygiene and exemption block; this record.
- Same round, second commit: the release notes carried no #1442 entry, because an earlier convention commit had moved it out of `CHANGELOG.md` into the PR body only. The BREAKING entry is now in `CHANGELOG.md`; `tests/test_release_process.py`, `tests/test_user_config_export_changelog.py` and `tests/test_plan_lifecycle.py`: 99 passed.

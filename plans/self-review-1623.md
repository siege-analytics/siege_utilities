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

## Precheck change (current review round)

Hostile-review-artifact for this section: https://github.com/siege-analytics/siege_utilities/issues/1623#issuecomment-6800282408 (independent fresh-context review, with responses). Ticket-side self-review: https://github.com/siege-analytics/siege_utilities/issues/1623#issuecomment-6800678454.

- **Change:**
  - `0020_seat_uniqueness` gains a read-only `RunPython(reject_duplicate_presidents, RunPython.noop, hints={"model_name": "seat"})` as its first operation. It uses the historical `Seat` model on `schema_editor.connection.alias` and filters `office="PRESIDENT"`, the singleton's own condition. With two or more rows it raises `RuntimeError` naming `seat_president_singleton`, the total, the alias and up to 20 primary keys in pk order, and states that this migration changed no rows or constraints. The three constraint operations are unchanged.
  - New `tests/test_0020_seat_uniqueness_precheck.py` (database-free; skips without GeoDjango) and `tests/test_0020_seat_uniqueness.py` (`postgis` marker; real `MigrationExecutor` from historical 0019 state, including a no-DDL-before-error assertion).
  - `tests/test_0019_demographic_geoid_keys.py`: teardown restores the computed `siege_geo` leaf.
  - `CHANGELOG.md`: the #1623 entry moves to 5.0.0 BREAKING with a Migration line, including the reverse limitation.
- **Deviation from the reviewed draft:** the database-free module gained a GeoDjango skip guard (the pattern in `tests/test_district_geoid_constraints.py`). Without it, the module errored at collection when GDAL was absent.
- **Syntax check:** `python -m py_compile` on the migration and the three test modules, exit 0.
- **Tests:** zero test cases were executed locally.
  - The database-free module skips because GDAL is not configured for the local test settings. Its 6 cases run in CI `test (3.11/3.12/3.13)`.
  - The PostGIS module (5 cases), the 0019 module and the singleton/Senate ORM tests run only in `test-postgis`. The named tests must be shown executed there, not skipped, before any pass is claimed.
  - Red-on-revert is inferred, not executed.
- **Findings:** F1 to F12, recorded on the ticket. F5 (a pre-existing exception-handling mismatch in `siege_utilities/geo/django/__init__.py`) is out of scope, and F6 (no completed exact-head CI run yet) is open.

## Peer review

- SU-1: the precheck raises; there is no empty-on-error return.
- SU-2: "read-only" matches the code, which only calls `count()` and a bounded `values_list`.
- SU-4b: the raise path is tested in both new modules.
- SU-4a: no live notebook covers `Seat` (only an archived one). This is a documentation gap and is not changed here.
- writing-tests:3 (skip messages name the remediation): local `pytest` on the two new modules → `SKIPPED [1] tests/test_0020_seat_uniqueness_precheck.py:22: Install GDAL/GEOS and configure GDAL_LIBRARY_PATH/GEOS_LIBRARY_PATH to run migration tests.` and `SKIPPED [1] tests/test_0020_seat_uniqueness.py:9: Set SIEGE_TEST_POSTGIS=1 and SIEGE_TEST_DB_* for live PostGIS tests.`
- writing-code:4 (verify a symbol exists before naming it): `grep -n "def test_…"` → the five test names cited in the precheck commit's Negative-Tests trailer exist at `tests/test_0020_seat_uniqueness.py:69`, `:100`, `:116` and `tests/test_0020_seat_uniqueness_precheck.py:107`, `:120`.
- writing-claims:8 (counts cite their command): the "6 cases" and "5 cases" counts → `grep -c "^def test_"` gives 5 (database-free module) and 4 (PostGIS module), plus one two-case `parametrize` in each.

## Lead review

- Approach fit (data engineer, Lead): this follows the 0019 data-check precedent. Reporting rather than repairing is the right boundary, because seat foreign keys cascade on delete.
- Completeness (data engineer, Lead): only the singleton can newly reject rows that were valid under 0019, so a single-condition check is complete for this migration.
- Blast radius (data engineer, Lead): any database applying `siege_geo` migrations. With 0 or 1 PRESIDENT seats the behavior is unchanged; with more, the migration stops cleanly instead of raising a raw error.

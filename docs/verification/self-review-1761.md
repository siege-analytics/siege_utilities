# Self-review: PR #1761 demographic_profile straddling units (#1562), pre-flight

Review-Tier: C (the checkout's path floor; this commit changes `siege_utilities/geo/providers/redistricting_data_hub.py` and its tests).

## Assumptions
Working as: software engineer (Junior) and geospatial tech lead (Lead).
Domain(s): census-to-district demographic overlay; spatial joins.
Geospatial cross-cut: yes (point-in-polygon assignment on shared edges, CRS alignment).
Goal source: the #1562 Problem / Done when / Falsifier sections; ruling to complete each ticket's acceptance criteria on its PR.
Plan reference: https://github.com/siege-analytics/siege_utilities/issues/1562#issuecomment-6761355127
Investigate-artifact: https://github.com/siege-analytics/siege_utilities/issues/1562#issuecomment-6761355127
Pre-mortem-artifact: https://github.com/siege-analytics/siege_utilities/issues/1562#issuecomment-6761355127
Hostile-review-artifact: independent review of the develop-integration tree `44601fa8` (pass, no S1/S2; five S3 findings addressed in the fix round below): https://github.com/siege-analytics/siege_utilities/pull/1761#issuecomment-6934039643. A review of the fix-round tree is pending.
Project-contribution: district demographic totals conserve the input population, and losses are reported instead of silent.

## Investigation
- `v4.0.0` joins census polygons to districts with `predicate="within"`; straddling units are dropped.
- PR head `3b0488e7` joins `representative_point()`s with `predicate="within"`. Executed on 2026-11-10: the #1562 probe unit `box(9, 1, 11, 2)` has representative point `POINT (10 1.5)`, which lies on the shared D1/D2 edge and is `within` neither district. The probe returned a total of 300 of 600 at `3b0488e7`.
- At `3b0488e7`, units outside the plan were excluded silently, and districts with no units were missing from the result. The existing straddle test asserted that absence (`GEOID == ["A"]`).
- The census frame was copied whole into the join, so a census `GEOID` column collides with the plan's `GEOID` (`GEOID_left` / `GEOID_right`), and `groupby("GEOID")` raises `KeyError`. Census tract layers usually carry `GEOID`.
- Caller: `siege_utilities/geo/django/services/rdh_loader.py:574` writes one `DistrictDemographics` row per returned district. No notebook calls `demographic_profile`.
- Develop `2deb6a1f` changed none of the PR's files since merge-base `7f534f6c`.

## Pre-mortem
1. Tiger (launch-blocking). Severity: P1. The issue probe loses population. Mitigation: `intersects` on representative points, then one row per unit (first matching plan row); `test_issue_probe_conserves_input_population` asserts D1=400, D2=200.
2. Tiger (launch-blocking). Severity: P1. Double counting with `intersects`. Mitigation: `drop_duplicates("_unit_row")` after a stable sort on `(_unit_row, _plan_row)`; the probe test asserts the exact per-district totals.
3. Tiger (fast-follow). Severity: P2. Silent loss outside the plan. Mitigation: `UserWarning` and `log.warning` stating the count and per-column totals; `pytest.warns` with the message.
4. Tiger (launch-blocking for release notes). Severity: P1. Non-breaking mislabel. Mitigation: `### BREAKING` + Migration in the PR body.
5. Paper Tiger. Severity: P3. Integer columns become floats after reindexing. Mitigation: `reindex(..., fill_value=0)` keeps `int64`; `assert_frame_equal` against integer frames.
6. Elephant. Severity: P3. Area or block-weight apportionment. The ticket accepts documented representative-point assignment.

## Peer review (Junior: shelves, gates)
- Shelves: SU-1 (silent exclusion replaced by a warning that states what was dropped); SU-2 (the docstring states edge tie-breaking, the warning, and zero rows); geospatial: assignment is decided by point-in-polygon on interior points, and CRS alignment precedes the join.
- Gate 1 (syntax/lint): flake8 on the module is clean; the test file's E402 hits are pre-existing (imports after `pytest.importorskip`), outside the ratchet's rule set. `scripts/check_test_file_hygiene.py`: PASS.
- Gate 2 (tests): `tests/test_demographic_profile.py tests/test_redistricting_data_hub.py tests/test_rdh_silent_wrong_data_1571.py tests/test_rdh_selection_1571.py tests/test_smoke.py tests/test_runtime_guard.py tests/test_sql_safety.py` with `--no-cov -p no:randomly`: 249 passed, 5 skipped. `tests/test_rdh_precinct_loader.py` cannot be collected locally (Django GIS needs the GDAL library, which is not installed here); CI provides GDAL.
- Gate 3 (docs): `demographic_profile` docstring; the #1562 entry in `CHANGELOG.md` `### BREAKING` (with Migration), mirrored exactly in the PR body block. Historical: at pre-flight the entry sat under `[4.1.0]`; since the develop integration (`1cdd6fb3`) it sits under `[5.0.0]` `### BREAKING`.
- Notebook impact (SU-4a): no notebook calls `demographic_profile`.

## Lead review (adversarial)
Phase A coherence: acceptance items map to code. Representative-point assignment documented → docstring and edge tie-break; dropped population reported → warning; every district with zeros → reindex; the probe conserving 600 → exact test.
Phase B verification (8 tests in `tests/test_demographic_profile.py`):
- Against `v4.0.0` `redistricting_data_hub.py`: 8 failed / 0 passed.
- Against PR head `3b0488e7`: 8 failed / 0 passed. The four straddle cases fail only on the new zero row for district B; the probe fails 300 != 600.
- After the fix: 8 passed.
- Changed assertion: the existing straddle test's expected frame gains a row `B: TOTPOP 0, VAP 0`. This adds a row required by #1562 ("every district appears ... with zeros"); no value is removed.
- Composition (as first written; superseded by the fix round below): `rdh_loader` would have written zero-valued `DistrictDemographics` rows for districts with no units. The fix round changed this: the loader skips those districts, writes nothing for them, counts them in `records_skipped` and reports them.

## Findings
| ID | Priority | Description | Resolution |
|----|----------|-------------|------------|
| F1 | P1 | #1562 probe still lost 300 of 600 at the PR head (edge point) | `intersects` + one row per unit |
| F2 | P1 | Unmatched population not reported | `UserWarning` + log with count and totals |
| F3 | P2 | Districts without units missing | reindex over plan districts with 0 |
| F4 | P2 | Census `GEOID` column collided with the plan's `GEOID` | join only population columns and the interior point |
| F5 | P2 | PR body "Refs", Fixed, `[Unreleased]`, local interpreter path | body: "Fixes #1562", BREAKING + Migration, item-to-test map, hygiene |

## Ticket-fitness exemption

writing-rules:4 exemption for the governing ticket.

### #1562
- **Reason:** #1562 predates the canonical ticket template. It uses Problem / Evidence / Failure scenario / Done when / Assumptions / Falsifier sections.
- **Evidence:** the defect, the v4.0.0 probe and the acceptance criteria are in the #1562 body. The investigation, pre-mortem and Junior/Senior review are at https://github.com/siege-analytics/siege_utilities/issues/1562#issuecomment-6761355127.
- **Falsification:** restore `siege_utilities/geo/providers/redistricting_data_hub.py` from `v4.0.0` or from `3b0488e7`; `tests/test_demographic_profile.py::test_issue_probe_conserves_input_population` then fails (`300 == 600` at `3b0488e7`). Verified on 2026-11-10.

## Test plan / Quantified claims
Interpreter: local Python 3.11.11, run from the repository root.
- Focused run as in Gate 2: 249 passed, 5 skipped.
- `tests/test_demographic_profile.py`: 8 failed on `v4.0.0`, 8 failed on `3b0488e7`, 8 passed after.

## Review follow-up (tie-break rule)
- `test_edge_unit_follows_plan_row_order`: the #1562 probe with plan rows reversed (`D2`, `D1`) gives D2 = 500, D1 = 100 with no warning, so the whole edge unit follows the first matching plan row.
- `test_result_is_stable_under_census_unit_order` (all 6 permutations of the three probe units): always D1 = 400, D2 = 200.
- Against `3b0488e7`'s module: all 7 cases fail (the edge unit is dropped, so totals are 100/200 in every order); at the tip: 7 passed. `tests/test_demographic_profile.py`: 15 passed.

## Review follow-up (null district IDs)
- Review thread on `redistricting_data_hub.py:1359` (comment 4522899917): a plan row with a null district ID could win the first-match tie-break, and `groupby` then dropped the null key, so the unit vanished from both the result and the warning. Fixed: plan rows with a null ID are excluded before the join; docstring and CHANGELOG say "first matching district with a non-null ID".
- `test_null_id_plan_row_does_not_capture_a_shared_edge_unit` and `test_unit_matching_only_a_null_id_row_is_reported_as_excluded`: both fail at `dfd30beb`, pass after. Related run: 283 passed, 5 skipped.

## Rework ledger
- Pre-flight round, 2026-11-10: edge-point assignment, unmatched-population warning, zero rows, census `GEOID` collision; body classification and acceptance map corrected.
- Develop integration, 2026-11-16 (`1cdd6fb3`, develop `60c5bb84`): import-only conflict kept all imports; reviewed at the link above.
- Fix round, 2026-11-17 (base `1cdd6fb3`): the review's S3-1 to S3-5; see below.

## Fix round, 2026-11-17: districts without units, row order, dtype-safe totals (base `1cdd6fb3`)

### Assumptions
- Goal: a district that receives no census unit must not be stored as a measured zero. Row order and non-NumPy dtypes must be documented and safe.
- Scope: `redistricting_data_hub.py`, `geo/django/services/rdh_loader.py` (added to this PR's files for S3-1), `tests/test_demographic_profile.py`, the new `tests/test_rdh_loader_demographics_1562.py`, the #1562 CHANGELOG entry and this document. No develop merge.

### Findings addressed
- **S3-1, no-unit districts.**
  - Before: `demographic_profile` returned zeros for a district with no unit, and `load_demographics_for_plan` stored them with `update_or_create`. A reload therefore overwrote earlier values with zeros and reported success, while the loader's GEOID path skips unmatched districts.
  - `demographic_profile` now keeps its shape and zero rows, and adds no column. The loader stores every non-ID column in `values`, so a count column would leak into stored data. Instead it names those districts in a `UserWarning` (a private subclass, `_DistrictsWithoutUnitsWarning`) plus a log line, and sets `result.attrs["districts_without_units"]` in plan order.
  - The loader's spatial path records the overlay's warnings in `RDHLoadResult.warnings`. It skips those districts (`records_skipped`, no `update_or_create`) and reuses `_report_unmatched`: a warning when some district received units, an error when none did, as on the GEOID path. The no-unit warning category is excluded from the recorded warnings, because the skip accounting already reports those districts once.
  - `DataFrame.attrs` can be dropped by later pandas operations. The loader reads it directly off the returned frame, so it is reliable here, and the docstring says so.
- **S3-2, row order.** Rows follow plan first-occurrence order of district IDs; v4.0.0 sorted by district ID. This is stated in the docstring and in the CHANGELOG Migration (`sort_values(district_id_col)`).
- **S3-3, `.item()`.** Excluded-unit totals used `.sum().item()`. An object or Arrow column sums to a Python scalar with no `.item()`, so the call raised `AttributeError`, which the loader would turn into "Spatial join failed". `_python_scalar` now uses `.item()` only when present.
- **S3-4, loader-level test.** `tests/test_rdh_loader_demographics_1562.py` is the first test that calls `load_demographics_for_plan`. Its three cases:
  - a partial no-unit plan is skipped plus a warning, with stored `values` checked;
  - no district receiving units is an error, with the excluded-unit warning recorded;
  - every district receiving units stores all of them, with no warnings.
  It also checks that no warning leaks out of the loader.
- **S3-5.** This document no longer claims a `[4.1.0]` placement (labelled historical) or that no review exists.
- The CHANGELOG Migration previously said the loader writes zero-valued rows for districts with no units. That is no longer true, and it is replaced by the skip-and-report behaviour.

### Test plan and results (local, Python 3.11.11, `pytest -o addopts="" -p no:cacheprovider`)
- **New in `tests/test_demographic_profile.py`:**
  - no-unit districts named in a warning and in `attrs` (1);
  - `attrs` empty with no warning when all districts receive units (1);
  - plan order, not sorted IDs (1);
  - object and `int64[pyarrow]` population columns (2).
- **RED, against the unchanged `1cdd6fb3`:**
  - the two `attrs`/warning tests fail;
  - both dtype tests fail with `AttributeError: 'int' object has no attribute 'item'` at the old line 1567;
  - the plan-order test passes, documenting existing behaviour.
- **After the fix:** `tests/test_demographic_profile.py` gives 22 passed. Of those, 17 existed. Three of them turn warnings into errors (`tests/test_demographic_profile.py:103`, `:132`, `:167`); they still pass because every district in them receives a unit, so the new no-unit warning is not raised there.
- **Loader tests:** SKIPPED locally ("GeoDjango/GDAL not available"). The GeoDjango models import needs the GDAL library, which this machine's Django settings cannot load, and a local `GDAL_LIBRARY_PATH` override was refused by the local command guard. CI evidence that they execute: run 42809563816, job `test (3.11)` on `8eae1dfd`, installs system GDAL and `--extra all --extra gdal --extra dev`, and runs `pytest tests/ -v -m "not integration and not postgis"`. In that log, the GDAL-guarded `tests/test_rdh_selection_1571.py::TestLoaderCVAPMatch` cases and the GeoDjango model tests (`test_redistricting_models`, `test_django_temporal_models_orm`, 27 cases) are PASSED, not skipped. The new file uses the same markers (`requires_gdal`, no `integration`/`postgis` marker) and a stricter guard than `tests/test_rdh_selection_1571.py` (it also imports the GeoDjango models, `tests/test_rdh_loader_demographics_1562.py:17-26`), so the same job selects it, and it executes there provided those model imports succeed, as they do for the 27 model tests in that job. Its first-ever execution, RED or after, is therefore CI on the new head.
- **Regression set:** `test_1480_rdh_chamber_sldu_sldl`, `test_redistricting_data_hub`, `test_boundary_providers`, `test_1415_rdh_atomic_download`, `test_rdh_selection_1571`, `test_release_process` and `test_user_config_export_changelog` give 313 passed, 0 failed. `tests/test_rdh_precinct_loader.py` (unchanged here) cannot be collected locally (GDAL), as at pre-flight; CI provides GDAL.
- ruff `--select F,E9` on the four Python files: no findings. `py_compile`: OK. `scripts/check_test_file_hygiene.py`: PASS.
- Not run locally: the full suite, PostGIS tests, lint ratchet, bandit and package checks. No live RDH, network or database call was made. Hosted CI on the new head is the authority.

### Independent review
- The independent review of the fix-round staged tree (`3fa4e293`) failed it with one S2 and three S3: https://github.com/siege-analytics/siege_utilities/pull/1761#issuecomment-6936343865. Fix round 2 below answers them.

## Fix round 2, 2026-11-17: JSON-safe `attrs`, categorical IDs, test gaps (base staged tree `3fa4e293`)

### Findings addressed
- **S2-1, integer district IDs.** `attrs["districts_without_units"]` held the values from `pd.unique`, which are NumPy scalars for `int64`, `int32` and nullable `Int64` IDs. `to_parquet` writes `attrs` with `json.dumps` and raised `TypeError: Object of type int64 is not JSON serializable`. Each listed ID now goes through `_python_scalar`, so the list holds plain Python values.
- **S3-6, categorical district IDs.** `groupby` kept unobserved categories with a zero total, so a district with no unit was neither warned about nor listed. The overlay now groups with `observed=True`; districts without units are found and filled with zeros by the existing `reindex`. This also avoids pandas' `FutureWarning` about the `observed` default.
- **S3-7, CHANGELOG.** Two sentences described fixes relative to states that never shipped. The `AttributeError` for object or Arrow totals existed only inside this PR, so the entry now just says the excluded-unit totals support any population dtype. v4.0.0 never stored zeros for districts without units; the loader change is now stated relative to v4.0.0 (counted in `records_skipped` and reported; a load in which no district receives a unit now fails). The Migration also points to the `attrs` list as the exact filter, since a `> 0` filter drops real zero totals too.
- **S3-8, test gaps.** A test with seven of eight districts lacking units pins the "(and 2 more)" truncation, the log line and the plan order of `attrs`.
- This document: the earlier composition line now says it was superseded, the count of tests that turn warnings into errors is corrected (three), and the loader test guard is described as stricter than `tests/test_rdh_selection_1571.py`'s.

### Tests and results (local, Python 3.11.11)
- **New in `tests/test_demographic_profile.py`:**
  - `int64`, `int32` and `Int64` IDs with a district lacking units: the warning, `attrs == [2]` as a plain `int`, a successful `to_parquet` of the result and of a filtered, sorted copy, and a `read_parquet` round trip of values and `attrs` (3);
  - categorical IDs: the warning, `attrs == ["D2"]`, no `FutureWarning`, rows and totals (1);
  - seven of eight districts lacking units: exact warning text and log record, `attrs` in plan order, rows and totals (1).
- **RED, against staged tree `3fa4e293`:** 4 failed, 23 passed. The three integer cases fail in `to_parquet` with `Object of type int64 / int32 is not JSON serializable`, and the categorical case fails with no warning. The truncation test passes there, because it pins existing behaviour.
- **Log line:** with the no-unit `log.warning` temporarily removed, the truncation test fails (1 failed, 26 passed); the line was restored before staging.
- **After the fix:** `tests/test_demographic_profile.py` and `tests/test_rdh_loader_demographics_1562.py` give 27 passed and 3 skipped. The three loader tests skip locally for the GDAL reason above.

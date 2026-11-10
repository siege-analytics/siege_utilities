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
Hostile-review-artifact: none yet. An independent exact-head review of the pushed commit is pending; this is NOT a pass.
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
- Gate 3 (docs): `demographic_profile` docstring; the #1562 entry in `CHANGELOG.md` `[4.1.0]` `### BREAKING` (with Migration), mirrored exactly in the PR body block.
- Notebook impact (SU-4a): no notebook calls `demographic_profile`.

## Lead review (adversarial)
Phase A coherence: acceptance items map to code. Representative-point assignment documented → docstring and edge tie-break; dropped population reported → warning; every district with zeros → reindex; the probe conserving 600 → exact test.
Phase B verification (8 tests in `tests/test_demographic_profile.py`):
- Against `v4.0.0` `redistricting_data_hub.py`: 8 failed / 0 passed.
- Against PR head `3b0488e7`: 8 failed / 0 passed. The four straddle cases fail only on the new zero row for district B; the probe fails 300 != 600.
- After the fix: 8 passed.
- Changed assertion: the existing straddle test's expected frame gains a row `B: TOTPOP 0, VAP 0`. This adds a row required by #1562 ("every district appears ... with zeros"); no value is removed.
- Composition: `rdh_loader` now writes zero-valued `DistrictDemographics` rows for districts with no units, instead of writing nothing. That is accurate for the input; disclosed as BREAKING.

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

## Rework ledger
- Pre-flight round, 2026-11-10: edge-point assignment, unmatched-population warning, zero rows, census `GEOID` collision; body classification and acceptance map corrected.

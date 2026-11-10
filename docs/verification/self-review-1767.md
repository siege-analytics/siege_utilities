# Self-review: PR #1767 interpolate_areal equal-area measurement (#1407), pre-flight

Review-Tier: C (the checkout's path floor; this commit changes `siege_utilities/geo/interpolation/areal.py`, its tests and `CHANGELOG.md`).

## Assumptions
Working as: software engineer (Junior) and geospatial tech lead (Lead).
Domain(s): areal interpolation, equal-area projections.
Geospatial cross-cut: yes (area measurement CRS, reprojection, backend parity).
Goal source: the #1407 Problem / Done when / Falsifier sections; ruling to complete each ticket's acceptance criteria on its PR (configurable equal-area CRS, recorded in output metadata, tobler included).
Plan reference: https://github.com/siege-analytics/siege_utilities/issues/1407#issuecomment-6761991608
Investigate-artifact: https://github.com/siege-analytics/siege_utilities/issues/1407#issuecomment-6761991608
Pre-mortem-artifact: https://github.com/siege-analytics/siege_utilities/issues/1407#issuecomment-6761991608
Hostile-review-artifact: none yet. An independent exact-head review of the pushed commit is pending; this is NOT a pass.
Project-contribution: interpolated values no longer depend on the input CRS or on which backend is installed.

## Investigation
- At PR head `fae0534d`: Shapely and DuckDB measure areas in a hard-coded `"ESRI:54009"`; tobler, the first backend in dispatch order, measured geographic input in degrees and warned, and `test_tobler_keeps_geographic_crs_warning` asserted that warning. `ArealInterpolationResult` recorded no area CRS, and the PR body said "Fixes #1407". `CHANGELOG.md` was not in the diff.
- Values from every backend are assigned back to `target.copy()` by position, so reprojecting the backend inputs does not change output geometry, columns, order or CRS.
- Callers: `geo/crosswalk/crosswalk_processor.py` and `geo/timeseries/longitudinal_data.py` call `interpolate_areal`; no notebook does.
- Locally installed: tobler 0.13.0 and DuckDB 1.4.4 with the spatial extension (the DuckDB cases ran, none skipped).
- Develop `2deb6a1f` changed none of the PR's files since merge-base `7f534f6c`.

## Pre-mortem
1. Tiger (launch-blocking). Severity: P1. tobler output order or schema after reprojection. Mitigation: positional assignment unchanged; tobler cases assert per-target values, unchanged target schema and output CRS.
2. Tiger (launch-blocking). Severity: P1. A geographic `area_crs` reintroduces the defect. Mitigation: `_validate_area_crs` raises `ValueError`; tested with `EPSG:4326` and an invalid string.
3. Tiger (fast-follow). Severity: P2. NaN-intensive subsets bypass `area_crs`. Mitigation: `area_crs` passes through `_run_backend`, which every subset call uses.
4. Tiger (launch-blocking for release notes). Severity: P1. Missing changelog entry; "Fixes" claim with unmet items. Mitigation: `### BREAKING` entry in `CHANGELOG.md` and the body.
5. Elephant. Severity: P3. `area_crs` is validated as projected, not as equal-area; the docstring says to choose an equal-area projection.

## Peer review (Junior: shelves, gates)
- Shelves: SU-2 (results no longer depend on the backend; the parameter is validated); geospatial: areas measured in a projected equal-area CRS.
- Gate 1 (syntax/lint): flake8 on the test file is clean; on `areal.py` the only hit is a pre-existing E127 also present at `fae0534d`. `scripts/check_test_file_hygiene.py`: PASS.
- Gate 2 (tests): `test_areal_interpolation`, `test_batch1_1373`, `test_areal_equal_area`, `test_final_hardening_consensus`, `test_round5_class_hardening`, `test_round6_class_hardening`, `test_longitudinal_normalization_consensus`, `test_crosswalk`, `test_crosswalk_analytics`, `test_geo_crosswalk_crosswalk_processor_errors`, `test_longitudinal_aligner`, `test_timeseries`, `test_timeseries_errors`, smoke, runtime-guard and SQL-safety, `--no-cov -p no:randomly`: 457 passed.
- Gate 3 (docs): `interpolate_areal` docstring; the #1407 entry in `CHANGELOG.md` `[4.1.0]` `### BREAKING` (with Migration), mirrored in the PR body.
- Notebook impact (SU-4a): no notebook calls the areal interpolation functions.

## Lead review (adversarial)
Phase A coherence: configurable → `area_crs` keyword (also on both wrappers); recorded → `ArealInterpolationResult.area_crs`; every backend → `area_crs` passed to tobler (reprojected inputs), DuckDB and Shapely.
Phase B verification (`tests/test_areal_equal_area.py`, 33 tests, tobler added to the backend fixture):
- Against PR head `fae0534d`'s `areal.py`: 19 failed / 14 passed (all tobler equal-area cases and all `area_crs` cases fail; the Shapely/DuckDB equal-area and output-CRS cases pass).
- Against `v4.0.0`'s `areal.py`: 33 failed / 0 passed.
- After: 33 passed.
- Test changes: `test_tobler_keeps_geographic_crs_warning` asserted the remaining defect and is replaced by `test_tobler_measures_in_area_crs_not_degrees`. Shapely/DuckDB keep the `rtol=1e-8` comparison; tobler cases use `1e-6` (its own intersection pipeline differs by ~1e-7 relative; #1407 requires 0.1%). The configurability test uses Mercator (`EPSG:3857`) as a deliberately non-equal-area CRS and asserts that its shares differ from Mollweide's by more than 5, so the test proves the parameter drives the areas.

## Findings
| ID | Priority | Description | Resolution |
|----|----------|-------------|------------|
| F1 | P1 | tobler measured geographic input in degrees | inputs reprojected to `area_crs` |
| F2 | P1 | Equal-area CRS not configurable, not recorded | `area_crs` keyword and result field |
| F3 | P2 | A test asserted the tobler defect | replaced by equal-area assertions on tobler |
| F4 | P2 | No `CHANGELOG.md` entry; body "Fixes" claim premature; local interpreter path | BREAKING entry in `CHANGELOG.md` and body; hygiene |

## Ticket-fitness exemption

writing-rules:4 exemption for the governing ticket.

### #1407
- **Reason:** #1407 predates the canonical ticket template. It uses Problem / Done when / Related / Falsifier sections.
- **Evidence:** the defect, the 30–45°N falsifier fixture and the acceptance criteria are in the #1407 body. The investigation, pre-mortem and Junior/Senior review are at https://github.com/siege-analytics/siege_utilities/issues/1407#issuecomment-6761991608.
- **Falsification:** restore `siege_utilities/geo/interpolation/areal.py` from `fae0534d`; `test_tobler_measures_in_area_crs_not_degrees` then fails (500/500 with a geographic-CRS warning) and every `area_crs` test fails. Verified on 2026-11-10.

## Test plan / Quantified claims
Interpreter: local Python 3.11.11, run from the repository root.
- Related run as in Gate 2: 457 passed.
- `tests/test_areal_equal_area.py`: 19 failed / 14 passed on `fae0534d`; 33 failed on `v4.0.0`; 33 passed after.

## Rework ledger
- Pre-flight round, 2026-11-10: `area_crs` parameter and metadata; tobler measures in the equal-area CRS; CHANGELOG entry; body correction.

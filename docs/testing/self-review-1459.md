# Self-review: geocode validation across CRSs and the Null Island sentinel (#1459, PR #1773)

Scope of this artifact: the PR as a whole at its code head 402a74bc, plus the process-only commit that syncs with develop, restores the two release notes in `CHANGELOG.md` under `[4.1.0]` and adds this file. The process commit changes `CHANGELOG.md` and this document and no library code. The PR body was also rewritten to describe the final diff.

Review-Tier: A for the process commit (documentation and release notes only). The code commits under review were reviewed independently at exact head 402a74bc by the external reviewer (ticket #1459, review comment 6262494933).

## Assumptions

- Goal source: ticket #1459. Pandas geocode validation must accept NAD83 coordinates on both sides of the antimeridian, compare projected coordinates in CRS units, and reject the exact geographic `(0, 0)` failed-geocode sentinel; Spark validation must reject the same sentinel.
- Roles: author is the PR owner; the independent reviewer is the cross-family hostile reviewer who recorded the head 402a74bc verdict on the ticket.
- The code diff against `origin/develop` after the sync is `siege_utilities/geo/geocoding.py`, `siege_utilities/distributed/spark_utils.py`, `scripts/exception_contracts_allowlist.json` (one entry removed, the old `_get_crs_bounds` handler fingerprint), `tests/test_geocode_validation_crs.py` and `CHANGELOG.md`. This commit adds no library code.
- The body claims were checked against the code at this head: geographic CRSs use world ranges `(-90, 90, -180, 180)` (`_get_crs_bounds`, lines 486-489); projected CRSs use the area of use transformed with `always_xy=True` and `densify_pts=21` (lines 496-501); when bounds cannot be derived the function logs a warning and leaves projected bounds unbounded (lines 505-511); geographic `(0, 0)` is rejected in `_pandas_coordinate_mask` (lines 133-137); Spark `validate_geocode_data` and `mark_valid_geocode_data` exclude the exact `(0, 0)` pair (`spark_utils.py`).
- Release convention: user-visible notes belong in `CHANGELOG.md` under `[4.1.0]`, not only in a PR body. This commit restores both #1459 entries there, verbatim from the PR body's earlier release-note text. No other `[Unreleased]` entry was touched.
- Pre-author-inventory: NONE. Trivial-against-state: after the sync, `git diff origin/develop -- CHANGELOG.md` shows only the two #1459 additions.

## Peer review

Gate evidence, all observed in this work cycle:

- Local pytest on the merged tree, run from the `tests` directory with the pyenv Python 3.11 and the repository pyproject: `python -m pytest test_geocode_validation_crs.py test_geocode_validation_pandas.py` -> 45 passed in 12.00s, no skips.
- The Spark case ran for real: `test_geocode_validation_crs.py::test_spark_validators_reject_null_island PASSED` (1 passed, 44 deselected in 9.57s with `-k spark -v`). The run used a local Java runtime (JAVA_HOME from the sdkman install) and a real Spark session; no stub replaced Spark.
- Hosted CI at the pushed head, including the Spark path in a Java-capable lane, is recorded in the PR body once it finishes. The earlier exact-head run was cancelled, so a fresh run is required.
- Known baseline: develop CI has failures from the DuckDB 2.0 break (about 30) until the #1863 pin successor lands. They are not attributable to this PR and were not chased.

## Test plan

- Confirm exact-head CI at the pushed head runs to completion and reports success other than the known DuckDB 2.0 failures on develop.
- Confirm `CHANGELOG.md` has both #1459 entries under `[4.1.0]` Fixed and none under `[Unreleased]`.
- Request a fresh exact-head review: the earlier result is void once the head moves, and the code diff against develop is unchanged.

## Pre-flight (develop 71f02b0b)

Develop was merged additively. The only conflict was `CHANGELOG.md`; every develop line was kept. Develop wins on any disagreement, and none exists: no develop change touches `siege_utilities/geo/geocoding.py` or `siege_utilities/distributed/spark_utils.py`.

Classification: caller code that worked on v4.0.0 now sees different results, because which geocodes pass validation changes (the exact `(0, 0)` sentinel is rejected in pandas and Spark; coordinates v4.0.0 wrongly dropped are kept). The two #1459 entries are now one entry under `### BREAKING` in `[4.1.0]` with a Migration line, at its own position in the BREAKING list so it does not conflict with the other open PRs. `git diff origin/develop -- CHANGELOG.md` shows 16 added lines and 0 removed lines. The PR body classification is updated to match.

Tests, run from the `tests` directory (Python 3.11, repository pyproject): `python -m pytest test_geocode_validation_crs.py test_geocode_validation_pandas.py -q` -> 45 passed in 8.83s. The library code is unchanged since the red/green run recorded in the Falsification entry below, which still applies to this head.

## Ticket-fitness exemption

Governing ticket: #1459 (the #1398 epic is context only and is not a governing ticket).

- **Reason:** #1459 predates the canonical ticket template (Context / Goal / Acceptance, a design link and Assumptions). It uses the earlier hostile-review Problem / Done-when / Falsifier narrative, so the ticket-fitness check reports a structure gap. The exemption is for ticket structure only.
- **Evidence:** the Problem (NAD83 rows rejected across the antimeridian, projected coordinates compared with degree bounds, the (0, 0) sentinel accepted), the evidence and the Done-when live in the ticket, https://github.com/siege-analytics/siege_utilities/issues/1459, and in the PR description. The reviewer verdict is https://github.com/siege-analytics/siege_utilities/issues/1459#issuecomment-6262494933.
- **Falsification:** revert the implementation (`geocoding.py` and `spark_utils.py` changes of this PR); `tests/test_geocode_validation_crs.py::test_nad83_keeps_pacific_territories` goes red because NAD83 coordinates across the antimeridian are rejected again, and `tests/test_geocode_validation_crs.py::test_spark_validators_reject_null_island` goes red because the Spark validators accept (0, 0). Observed revert run: with `siege_utilities/geo/geocoding.py` and `siege_utilities/distributed/spark_utils.py` restored to origin/develop (`git checkout origin/develop -- siege_utilities/geo/geocoding.py siege_utilities/distributed/spark_utils.py`), `python -m pytest test_geocode_validation_crs.py::test_nad83_keeps_pacific_territories test_geocode_validation_crs.py::test_spark_validators_reject_null_island -q`, run from the tests directory with a local Java runtime and a real Spark session, gave 2 failed in 7.41s. After `git checkout HEAD --` of the files the command gave 2 passed in 6.74s, `test_geocode_validation_crs.py` with `test_geocode_validation_pandas.py` gave 45 passed on the pushed head, and the worktree was clean. The latest commit of this PR is process-only.

## Lead review

The change alters which geocodes pass validation (see the BREAKING classification above), and it reverts with one commit. No claim in this artifact exceeds what was observed.

## Fix round after review of cb7423e0 (2026-11-17)

Earlier sections describe head 402a74bc and its `[4.1.0]` placement. They are kept as written.

- **Review finding (S2):** at `cb7423e0`, projected bounds were an x/y envelope sampled from the area-of-use edges (`transform_bounds(..., densify_pts=21)`) and used as an exact rejection boundary. Sampling misses projection extrema, so valid interior points were rejected: EPSG:5070 and EPSG:5069 at lon -96, lat 24.41001, and EPSG:3413 at lon 45, lat 60.001, through both public pandas validators.
- **Fix:** `_projected_area_of_use_mask` inverse-projects each candidate point to WGS84 lon/lat and tests membership in the CRS area of use.
  - The area is widened by 0.01 degrees, the precision of published EPSG area-of-use bounds, which also covers the difference between a CRS's datum and WGS84.
  - The point must project back to its input within 1 km on the ground, converted to CRS units through the axis unit factor. This rejects points beyond the projection's domain whose inverse longitude wraps around.
  - Every point inside the area of use passes, so the check is conservative for legitimate points.
  - A missing area of use or a failed transformation still logs "skipping bounds validation" and accepts finite coordinates.
  - `_get_crs_bounds` now returns unbounded x/y for projected CRSs.
- **Why these tolerances, with the observed evidence.** A first implementation used a 1e-7 degree membership margin and a 1 mm round-trip tolerance.
  - On EPSG:5069 (NAD27 / CONUS Albers), it rejected two legitimate points through both public APIs:
    - Miami (lat 25.7617, lon -80.1918), well inside the area of use, in the existing `test_albers_validators_keep_southern_conus_points`;
    - the extremum point at lon -96, lat 24.41001.
  - The same code accepted every EPSG:5070 (NAD83) and EPSG:3413 (WGS84) case.
  - Miami is far from every area-of-use edge, so membership cannot have rejected it. The failure was in the round trip.
  - Inference, not measured per point: the 5069 transforms to and from WGS84 cross a NAD27 datum shift, and PROJ can choose different operations in the two directions, so the round trip drifts by metres rather than sub-millimetres.
  - The final tolerances follow from that, not from tuning to the test:
    - 0.01 degrees covers the published rounding of EPSG area-of-use bounds and the NAD27 to WGS84 difference (tens to a few hundred metres);
    - 1 km on the ground covers datum-operation drift, while a longitude wrap-around misses by thousands of kilometres. It is scaled to CRS units by the first axis's unit factor, so feet-based CRSs get the same ground distance.
- **Tests (pytest on the PR worktree):**
  - `test_projected_extrema_inside_area_of_use_are_valid` covers the three extrema through both APIs. RED at `cb7423e0`: 6 failed, while the 6 new negative tests passed.
  - `test_projected_points_outside_area_of_use_are_invalid`, `test_projected_x_beyond_domain_does_not_wrap_into_area` and `test_projected_points_with_non_finite_inverse_are_invalid` are negative tests.
  - The mocked transform-failure test now mocks `transform` instead of `transform_bounds`. Its former non-finite-bounds case is replaced by the non-finite-inverse test, because a point that cannot be inverse-projected is outside the CRS domain.
  - GREEN: `tests/test_geocode_validation_crs.py` and `tests/test_geocode_validation_pandas.py`: 57 passed.
- **Guards:**
  - `scripts/check_exception_contracts.py --list`: 0 unlisted, 0 stale (`_get_crs_bounds` keeps an explicit return in its handler).
  - `ruff check --select F,E9` on `geocoding.py` and the test file: no findings.
- **CHANGELOG:** after the develop merge the #1459 entry sits under `[5.0.0]` -> `### BREAKING`, because develop renamed the former `[4.1.0]` section. Its projected-bounds sentences and Migration line now describe the area-of-use rule.
- **Notebook:** `notebooks/playground/01_geocoding_data_quality.ipynb` calls both pandas validators and its fixture outputs remain valid. Its narrative does not yet explain the Null Island policy or the CRS-bounds rule, and it has no sentinel example. That update is tracked in #1943.
- **Commit layout:** one commit carries the develop `2c51af86` merge and this fix round. Against git's own merge result for `cb7423e0` and `2c51af86`, the fix is exactly four files: `siege_utilities/geo/geocoding.py`, `tests/test_geocode_validation_crs.py`, `CHANGELOG.md` and this document.

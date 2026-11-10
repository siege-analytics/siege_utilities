# Self-review: PR #1831 null-CRS mixes and conflicting crs= in spark_to_geopandas (#1413)

Review-Tier: C (CRS handling in the Databricks bridge; pre-flight round with a BREAKING classification).

## Assumptions
Working as: software engineer (Junior) and geospatial/Databricks tech lead (Lead).
Domain(s): software engineering (Spark → GeoPandas conversion, CRS metadata).
Geospatial cross-cut: yes (CRS agreement and reprojection).
Goal source: #1413 (unknown-CRS rows inherited another row's CRS; a conflicting `crs=` relabelled coordinates without transforming). This round is a pre-flight of the existing implementation at `ad7c655c`: restore the CHANGELOG entry as BREAKING against the v4.0.0 tag and re-run red/green evidence. No library code changed in this round.
Plan reference: docs/verification/self-review-1831.md#pre-mortem
Investigate-artifact: https://github.com/siege-analytics/siege_utilities/issues/1413#issuecomment-6759225798
Pre-mortem-artifact: https://github.com/siege-analytics/siege_utilities/issues/1413#issuecomment-6759225798
Project-contribution: Spark geometries arrive in GeoPandas in the coordinates their CRS label claims.

## Investigation
- GitHub reported PR #1831 MERGEABLE/CLEAN. `databricks/dataframe_bridge.py` did not change between v4.0.0 and the merge base.
- pyspark is installed in the evidence interpreter; the regression file uses a pandas-backed `SparkFrame` stand-in, and all 21 cases execute (no skips) on both runs.
- The test `test_target_crs_cannot_hide_invalid_stored_crs` shows a third caller-visible change: an invalid stored CRS raises `pyproj.exceptions.CRSError` even when `crs=` is passed; it is named in the entry.
- REST: 0 inline review comments and 0 reviews on PR #1831.

## Pre-mortem
1. Tiger. Severity: P2. Red evidence vacuous due to skips. Mitigation: confirmed 0 skips; 11 failures are behaviour assertions.
2. Paper Tiger. Severity: P2. The entry misstates declaration vs reprojection. Mitigation: the entry quotes the branch docstring semantics and the test's numeric result.
3. Paper Tiger. Severity: P3. The CHANGELOG insertion conflicts with develop. Mitigation: read-only trial merge and merged-tree tests before push.
4. Tiger. Severity: P1. Wrong ref or non-fast-forward push. Mitigation: explicit refspec, no force, remote head checked to advance from `ad7c655c`.

## Peer review (Junior: shelves, gates)
- Shelves: geospatial shelf (never combine or relabel geometries across CRSs without transforming); SU-1 (mixed metadata raises instead of silently choosing a CRS).
- Gate 1 (syntax): no Python file changed in this round.
- Gate 2 (tests): on the branch, `tests/test_1413_spark_to_geopandas_crs.py` 21 passed.

## Lead review (adversarial)
Phase A coherence: CHANGELOG entry, PR body and tests describe the mixed-null rejection, reprojection to a conflicting `crs=`, invalid stored CRS rejection and declaration semantics for absent/all-null metadata.
Phase B verification (red/green): `tests/test_1413_spark_to_geopandas_crs.py` copied into a detached v4.0.0 worktree (`9c3463b1`) -> 11 failed, 10 passed. The 10 passing cases are controls (matching CRS preserved, unknown source CRS declared by the caller, multiple stored CRS already rejected, empty frames). Failures: 6 `DID NOT RAISE ValueError` for mixed null/non-null metadata, 4 `assert 1.0 == 111319.49...` for relabel-instead-of-reproject, 1 `DID NOT RAISE CRSError` for an invalid stored CRS. On the branch -> 21 passed. Import paths were checked to resolve to the worktree package.

## Findings
| ID | Priority | Description | Resolution |
|----|----------|-------------|------------|
| F1 | P2 | CHANGELOG entry only in the PR body | restored under `[4.1.0] ### BREAKING` with Migration |
| F2 | P3 | Invalid stored CRS rejection missing from the PR body entry | added to the entry |
| F3 | P3 | Tip lacked review trailers | this commit carries them |

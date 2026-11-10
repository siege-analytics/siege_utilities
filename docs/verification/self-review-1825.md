# Self-review: PR #1825 projected inputs in locale and H3/S2 APIs (#1451)

Review-Tier: C (geospatial CRS handling in public APIs; pre-flight round with a BREAKING classification).

## Assumptions
Working as: software engineer (Junior) and geospatial tech lead (Lead).
Domain(s): software engineering (NCES locale classification, H3/S2 indexing and joins).
Geospatial cross-cut: yes (CRS agreement before reading coordinates).
Goal source: #1451 (projected GeoDataFrames read as degrees in locale and H3/S2 APIs). This round is a pre-flight of the existing implementation at `ed49393b`: add the CHANGELOG entry as BREAKING against the v4.0.0 tag and re-run red/green evidence. No library code changed in this round.
Plan reference: docs/verification/self-review-1825.md#pre-mortem
Investigate-artifact: https://github.com/siege-analytics/siege_utilities/issues/1451#issuecomment-6759215360
Pre-mortem-artifact: https://github.com/siege-analytics/siege_utilities/issues/1451#issuecomment-6759215360
Project-contribution: locale codes and grid cells come from the real location of the input, whatever projection the caller's frame uses.

## Investigation
- GitHub reported PR #1825 MERGEABLE/CLEAN. The branch diff contains no `CHANGELOG.md` change, although the PR body says the changelog documents the change; the entry is added here.
- `geo/locale.py` changed between v4.0.0 and the merge base (#1441 published NCES codes). The locale red case still isolates this PR's defect at the tag: in `test_classify_points_projected_matches_geographic`, line 37 (`expected == [11]` for the EPSG:4269 point) passes on v4.0.0, and line 38 fails with `[43] == [11]` for the same point after `to_crs(3857)`.
- v4.0.0 `h3_index_polygon`/`s2_index_polygon` accept only Shapely or GeoJSON-like geometries; passing a GeoDataFrame raised `TypeError: Unsupported geometry type 'FeatureCollection'`. The CHANGELOG entry states frame acceptance as new rather than as a silent-misread fix.
- h3 and s2sphere are installed in the evidence interpreter, so native cell-parity cases execute.
- REST: 0 inline review comments and 0 reviews on PR #1825.

## Pre-mortem
1. Tiger. Severity: P2. The PR body's "Bug fix / Patch / not breaking" classification contradicts the BREAKING entry. Mitigation: the body addendum states BREAKING with the same entry.
2. Paper Tiger. Severity: P2. The red evidence is inflated by input-type or harness failures. Mitigation: failures are classified below; the defect-proving cases are named separately.
3. Paper Tiger. Severity: P3. The CHANGELOG insertion conflicts with develop. Mitigation: read-only trial merge against develop before push.
4. Tiger. Severity: P1. Wrong ref or non-fast-forward push. Mitigation: explicit refspec, no force, remote head checked to advance from `ed49393b`.

## Peer review (Junior: shelves, gates)
- Shelves: geospatial shelf (CRS agreement before combining or reading coordinates); SU-2 (functions that claim to take GeoDataFrames honour their CRS).
- Gate 1 (syntax): no Python file changed in this round.
- Gate 2 (tests): on the branch, `tests/test_1451_locale_h3_s2_crs.py` 42 passed; `tests/test_locale.py tests/test_h3_utils.py tests/test_s2_utils.py` 131 passed.

## Lead review (adversarial)
Phase A coherence: CHANGELOG entry, PR body and tests describe reprojection for frames with a CRS, the new `ValueError` for out-of-range CRS-less inputs, and unchanged behaviour for valid geographic inputs.
Phase B verification (red/green): `tests/test_1451_locale_h3_s2_crs.py` copied into a detached v4.0.0 worktree (`9c3463b1`) -> 40 failed, 2 passed (the two passing cases are CRS-less geographic inputs to `classify_points`/`classify_polygons`, which should behave the same). Failure classes on v4.0.0:
- defect at the tag, silent wrong output: locale projected cases (`[43] == [11]`, empty distributions), projected H3/S2 joins (`DataFrame are different`);
- defect at the tag, no rejection: `DID NOT RAISE ValueError` for CRS-less out-of-range and bare projected polygons;
- new input support, not a silent-misread fix: `TypeError ... 'FeatureCollection'` for frame inputs to `*_index_polygon`;
- harness mismatch with v4.0.0 internals: `'types.SimpleNamespace' object has no attribute 'CellId'` in the mocked S2 cell-call cases.
On the branch -> 42 passed. Import paths were checked to resolve to the worktree package.

## Findings
| ID | Priority | Description | Resolution |
|----|----------|-------------|------------|
| F1 | P2 | No CHANGELOG entry despite the PR body's claim | entry added under `[4.1.0] ### BREAKING` with Migration |
| F2 | P2 | PR body classification says not breaking | body addendum states BREAKING |
| F3 | P3 | Tip lacked review trailers | this commit carries them |

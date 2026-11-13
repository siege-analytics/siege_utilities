# Self-review: semantic CRS comparison in the shared spatial_join check (#1619, PR #1751)

Scope: the commits on PR #1751 after `0e8dfeb3`. Each is listed with the round it belongs to; evidence below is labelled by round.

- Fix round, `56e6781c`: semantic CRS comparison. Production change in `siege_utilities/engines/dataframe_engine.py` (`_same_crs`, used by `_validate_spatial_join_crs`). Tests: `tests/test_1619_crs_semantic_compare.py` (new) and one added parameter in `tests/test_spatial_join_crs_check.py`. Docs: `docs/engines/INVARIANTS.md` and the #1619 CHANGELOG entry.
- Merge round, `81adb754`: merge of develop `6c049c2c`. The only conflict was the CHANGELOG `[Unreleased]` block; the #1619 entry moved to `[5.0.0]` `### BREAKING` with a Migration line.
- Correction round, `0aec21a6`. DuckDB and PostGIS `spatial_join` check the inputs as passed, before conversion supplies a default CRS. Two tests were added to `tests/test_spatial_join_crs_check.py`, and the CHANGELOG entry and INVARIANTS bullet were narrowed. This artifact was also updated in that commit.
- Test-timeout round, `a02c9dd8`: the `_run_python` test helper gained `timeout=60` after the exact-head CI static guards flagged it (`scripts/check_unbounded_io.py`).
- Merge rounds, `c8bddd1a` (develop `f22dce96`) and `b0ceb40b` (develop `cab06ce4`): additive develop merges. Against develop, each result changed only this PR's six files. Each round's self-review and independent hostile review are on #1619 (issuecomment-6845610783 and issuecomment-6847498515).
- Multi-layer round, `1222d802`. `multi_assign` keeps points that arrive without CRS metadata unknown for every boundary layer, so the default CRS that converting them for the first join assigns is not compared against later layers. One two-layer test on DuckDB and PostGIS was added.
- Merge rounds, `39714439` (develop `75371af8`) and `7ef48554` (develop `1dcb1e59`): additive develop merges. In `7ef48554` the only conflict was CHANGELOG.md, resolved with develop's bullets first and the #1619 bullet unchanged as the last item of the first `[5.0.0]` BREAKING list. Each round's self-review and independent hostile review are on #1619 (issuecomment-6850868302 and issuecomment-6852271626).

Written 2026-11-11 and updated 2026-11-13, after the original implementation at `0e8dfeb3` (authored and committed 2026-10-18). No investigation, pre-mortem or hostile review was recorded for the original round; those remain absent for it.

## Assumptions

Domain(s): software engineering, data engineering (geospatial).
Geospatial cross-cut: yes.
Goal source: #1619. Further goal material: the review decisions on PR #1751 to compare known CRS metadata semantically through pyproj (fix round), and to validate the original inputs in DuckDB and PostGIS `spatial_join` before conversion supplies a default CRS (correction round). Both keep static attribute inspection and the mismatch `ValueError` and its message. Neither allows reprojection, CRS inference from WKT, axis-order relaxation or new packaging scope.
Pre-author-inventory: https://github.com/siege-analytics/siege_utilities/issues/1619#issuecomment-6800336384
Investigate-artifact: https://github.com/siege-analytics/siege_utilities/issues/1619#issuecomment-6800336384
Pre-mortem-artifact: https://github.com/siege-analytics/siege_utilities/issues/1619#issuecomment-6800336384
Hostile-review-artifact: https://github.com/siege-analytics/siege_utilities/issues/1619#issuecomment-6843376148
Project-contribution: every engine's spatial join applies one CRS contract. Known, different CRS raise before the join. CRS values that name the same system match. A frame without CRS metadata is treated as unknown rather than as an assumed default. Callers get the same answer for the same inputs on pandas, DuckDB and PostGIS, and the documented Spark scope.
Review-Tier: the content tier of the fix and correction rounds is B. The local gate classified this worktree's actions as tier C from whole-tree paths outside the PR diff, and the merge commit's push was refused as tier C. The follow-up commit therefore declares tier C and carries the tier C artifacts.
Working as: software engineer (Junior) and tech lead (Lead). Independent fresh-context reviewers attacked the design before the fix round, and the merge and correction in the correction round. Their reports are on #1619 (Senior checklist issuecomment-6800336384; merge-round reviews issuecomment-6843376148).

1. The fix-round defect is reachable only through explicit CRS metadata that is not a pyproj `CRS`, in practice a Spark frame's `crs` attribute. A GeoDataFrame's `.crs` is a pyproj `CRS`, whose `__eq__` already parses the other operand.
2. pyproj belongs to the optional `geo` extra. It is imported only inside `_same_crs`, after both values are known and not literally equal.
3. In installed pyproj 3.7.2, `CRSError` subclasses `ProjError(RuntimeError)`, and `DataDirError` also subclasses `RuntimeError`. Catching `(CRSError, ValueError, TypeError)` treats unparseable metadata as a different CRS and lets a broken PROJ installation surface as itself.
4. Equality is pyproj's default `CRS.__eq__`, which is sensitive to axis order, the same policy as `geo.crs.reproject_if_needed`. `geo.crs._normalize_crs` is not reused, because it raises a different `ValueError` and collapses to an EPSG code.
5. Correction round: DuckDB and PostGIS `to_geodataframe` stamp the configured default CRS on frames without CRS metadata. Checking after that conversion compared an assigned label. A plain frame was therefore checked as EPSG:4326, and PostGIS `multi_assign` (whose `to_pandas` drops the frame CRS between layers) raised on a matching non-default CRS. Checking the inputs as passed removes both effects. PostGIS `multi_assign` then checks only its first layer; that limitation predates the PR and is tracked in #1898.

## Test plan

Local Python 3.11.11, pytest 8.4.2, pyproj 3.7.2, pyspark with a real local SparkSession. Runs clear the coverage addopts. Tracebacks show the checkout's module, not an installed copy.

Fix round (`56e6781c`):
- Parent control on unmodified `0e8dfeb3`, extended tests: 6 failed, 46 passed. Failing because of the defect: the two case-variant tests, the integer `4326` test and the real-Spark `case_variant` case. Failing for other reasons: the `DataDirError` and no-pyproj tests, because the parent never consults pyproj.
- With the change: 52 passed, 0 skipped. Regression sweep over six spatial-join test files: 153 passed.

Merge round (`81adb754`):
- Merged snapshot: 174 passed, 1 failed. The failure is the #1463 session-state test, whose first Spark catalog call could not reach the HDFS default filesystem configured on this machine, before any engine code ran.
- Repository guards: exception contracts 0 unlisted; no stub docstrings; 0 credential literals; error-path coverage 395 modules pass; lazy imports OK.

Correction round (follow-up commit):
- With the new tests and the merge commit's engine: 3 failed, 34 passed. The failures are the PostGIS two-layer `multi_assign` case and the plain-WKT case on DuckDB and PostGIS, each a false `left has EPSG:4326, right has EPSG:3857` mismatch.
- With the correction: 57 passed, 0 failed, 0 skipped across `tests/test_spatial_join_crs_check.py` and `tests/test_1619_crs_semantic_compare.py`. That includes the real-Spark cases and the driver-side PostGIS cases.

Multi-layer round (`1222d802`):
- With the new two-layer test and the `b0ceb40b` engine: the DuckDB case fails with `left has EPSG:4326, right has EPSG:3857` at the second layer, raised from `multi_assign` through `assign_boundaries` and `spatial_join`. The PostGIS case passes, because PostGIS `to_pandas` already drops the assigned CRS between layers.
- With the change: 87 passed across `tests/test_spatial_join_crs_check.py`, `tests/test_1619_crs_semantic_compare.py`, `tests/test_dataframe_engine_spatial.py` and `tests/property/test_spatial_join_invariants.py`. `scripts/check_unbounded_io.py` reports 0 violations on the library and on tests, and the exception contracts guard reports 0 unlisted handlers.
- The independent review of this change asked for a test that a known CRS mismatch still raises on a later layer. `test_multi_assign_rejects_a_known_mismatch_on_a_later_layer` covers Pandas and DuckDB (PostGIS checks only its first layer, #1898). It passes with the change. With the new condition temporarily weakened to ignore whether the points had CRS metadata, it fails on both engines (DuckDB: did not raise), and the code was then restored.

Not run here: the full repository suite, and PostGIS against a live database. The `postgis`-marked cases join on the driver and open no connection. Exact-head CI is the full-suite evidence and must show the named tests executing, not skipped.

## Peer review

- writing-code:7 (fix round): `_same_crs` catches `(CRSError, ValueError, TypeError)` and returns a documented "not the same CRS" result that the caller turns into the existing `ValueError`. The ImportError path logs a warning that names the `geo` extra. The catch class was checked against the installed pyproj source. Exception contracts guard (merge round) → 0 unlisted.
- writing-code:8 (fix round): pyproj is imported lazily inside the comparison. Without it, the warning names the install target and the comparison fails closed. A subprocess with pyproj blocked imports the engine and validates → pass.
- writing-tests:1 and writing-tests:5 (fix and correction rounds): each new test fails on the prior engine and passes after it. Fix round: 6 failed → 52 passed. Correction round: 3 failed → 57 passed. Every new `except` path is exercised by a test that forces it.
- writing-claims:1 (fix round): a grep for raw `.crs` comparisons found four other sites (`geo/crs.py:110`, `geo/temporal/query.py:100`, `geo/providers/redistricting_data_hub.py:1334`, `geo/interpolation/areal.py:108`). All four compare GeoDataFrame CRS objects, which is already semantic, and are out of scope by the review decision.
- writing-claims:8: every count above names the run and round that produced it.
- writing-claims:10 (fix round): the import-path tests assert that the engine module file is inside the checkout. A non-editable installed copy exists in the interpreter's site-packages and is not the one imported → pass.
- writing-releases:1 (merge and correction rounds): the #1619 entry is under `[5.0.0]` `### BREAKING` with a Migration line. Against develop the CHANGELOG diff is additions only.
- SU-4a: no notebook calls `spatial_join` with CRS metadata (`notebooks/spatial/07_natural_language_to_geometry.ipynb` mentions it only in prose and a diagram). Noted as a documentation gap.

## Lead review

- Tech lead, approach fit: the comparison lives in one private helper, `_same_crs`, with one consumer. The correction moves one existing call in each of the two converting engines, without a new abstraction, codec, relabel or reprojection.
- Tech lead, blast radius: every caller of `spatial_join` and the helpers on pandas, DuckDB, PostGIS and Spark.
  - On DuckDB and PostGIS, plain frames without CRS metadata now count as unknown instead of the default CRS. Known mismatches between GeoDataFrames still raise; the existing mismatch tests pass unchanged.
  - The documented limits are PostGIS `multi_assign` checking only its first layer (#1898), and Spark `assign_boundaries` and `multi_assign` not checking (#1896).
- Data engineer, class closure: GeoDataFrame pairs compare semantically on every engine, and string metadata compares semantically where pyproj is installed. The two inherited gaps are tracked, not closed, by decision.
- Software engineer, sequencing assumption: the reviewer's exact-head review and exact-head CI follow this commit. The PostGIS service lane is where the `postgis`-marked cases run in CI.

## Findings

| ID | Priority | Description | Resolution |
|----|----------|-------------|------------|
| F1 | P3 | Array-like CRS metadata would make the literal `==` shortcut raise an ambiguous-truth error, as on the parent. CRS metadata is expected to be scalar. | noted |
| F2 | P3 | Without pyproj, case-variant metadata still raises, with a warning that names the `geo` extra. | noted (fails closed by design) |
| F3 | P3 | A Spark mismatch test that needs no JVM was suggested by the independent review; the real-Spark tests ran locally instead. | noted |
| F4 | P2 | The CHANGELOG entry sat under `[Unreleased]` `### Fixed`; it belonged under BREAKING with a Migration line. | fixed by merge 81adb754 |
| F5 | P1 | PostGIS `multi_assign` with two layers in a matching non-default CRS raised a false mismatch. | fixed in the correction commit |
| F6 | P2 | DuckDB and PostGIS checked frames without CRS metadata as the default CRS instead of unknown. | fixed in the correction commit |
| F7 | P2 | Spark `assign_boundaries` and `multi_assign` do not run the CRS check. | ticket #1896 |
| F8 | P2 | PostGIS `multi_assign` checks only its first boundary layer, because `to_pandas` drops the frame CRS between layers (inherited). | ticket #1898 |
| F9 | P1 | DuckDB `multi_assign` with points that have no CRS metadata raised a false mismatch from the second layer on, against the default CRS that the first join's conversion assigned. | fixed in 1222d802 |

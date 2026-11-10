# Self-review -- R-1852-5 (importorskip + unused-import on #1852)

## Assumptions

Working as: software engineer (Junior) and tech lead (Lead).
Goal source: review finding R-1852-5 on #1852 (outside this diff).
Domain(s): software engineering (test hygiene).
Base: additive commit on fix/engine-cluster @ a6755071.

## Peer review

- Two edits to tests/test_1852_conversion_siblings.py: remove the unused `import copy` (no `copy.` reference in the file) and add a module-level `pytest.importorskip("duckdb")` after the imports. No assertion changed; `git diff` is +2/-1 in one file.
- Placement: `DuckDBEngine.__init__` guards `import duckdb` and re-raises an actionable ImportError (`siege_utilities/engines/dataframe_engine.py:932-937`; an earlier version of this file cited `:78`, which is the geopandas capability probe), so the module imports without duckdb; the importorskip at module scope makes the module skip cleanly when duckdb is absent, converting the 8 fixture setup errors to skips.

## Lead review

In software engineering: the change is test-only and additive; it removes a no-DuckDB false-error class without touching assertions or library code. Blast radius: this one test module. No findings.

## Ticket-fitness exemption

The governing tickets #1479, #1497 and #1412 were written before the current
evaluate-ticket structure (Problem / Evidence / Done-when headings), which is
the Reason for each exemption; it covers ticket structure only.

Revision relationship. The record was reviewed at `eff07712`. Both
`c157abff` (the at-head controls) and `7cac3e01` (the 105-test run) are
ancestors of `eff07712` (`git merge-base --is-ancestor`). Between `c157abff`
and `eff07712` the only change is this file. Between `7cac3e01` and
`eff07712` no library file and none of the four named test files changed
(`git diff --stat 7cac3e01 eff07712 -- siege_utilities <four test files>`
is empty). The results therefore hold at `eff07712`. Later revisions are
recorded in their own self-review.

The falsifier for each ticket is the at-head control below. The pre-fix-tree
runs that follow are historical context: they show each defect existed before
its fix, not that the current code still depends on it.

At-head controls (observed 2026-11-05 at `c157abff`, Python 3.11.11, duckdb
1.5.6, current tests). For each ticket, only its surviving implementation
lines were reversed by hand, the named node was run from `tests/` with
`python -m pytest -o addopts="" --rootdir=.. -c ../pyproject.toml -p no:cacheprovider -q -p no:randomly <file> -k <node>`,
the file was restored with `git checkout HEAD -- <file>`, the node was run
again, and `git status --short` was empty.

- **#1412.** Removed
  `result.attrs[_GEOMETRY_CRS_ATTR] = {...}` from `_materialize_geometry_wkb`
  (`siege_utilities/engines/dataframe_engine.py:1511`). Node
  `tests/test_1412_duckdb_query_wkb_crs.py::test_typed_wkb_preserves_crs`:
  6 failed, each `AttributeError: 'NoneType' object has no attribute 'to_epsg'`
  at the test's assertion `result.crs.to_epsg() == 3857` (the typed CRS is
  lost). Restored: 6 passed.
- **#1479.** In `_spatial_join_projection`
  (`siege_utilities/engines/dataframe_engine.py:1979-1987`), replaced the
  `_left`/`_right` suffix mapping with plain names and removed its
  duplicate-name guard (with the guard alone left in place the run would stop
  on the guard's `ValueError` instead of showing the collision). Node
  `tests/test_1479_spark_join_collisions.py::test_spark_join_has_one_geometry_and_suffixes[spatial_join]`:
  1 failed, `AssertionError: assert 6 == 4` at
  `len(result.columns) == len(set(result.columns))` (duplicate `GEOID` and
  `name` columns). Restored: 1 passed.
- **#1497.** In base `nearest`
  (`siege_utilities/engines/dataframe_engine.py:707-709`), replaced
  `to_geodataframe(..., crs=crs)` plus `_require_projected_crs(...)` with the
  pre-fix `to_geodataframe(..., crs=crs or "EPSG:4326")` and no projected check
  (the check alone would raise its `ValueError` before the distance assertion).
  Node
  `tests/test_1497_engine_crs_preservation.py::test_nearest_preserves_metres_and_crs`:
  3 failed (`[pandas]`, `[duckdb]`, `[postgis]`), each
  `assert [0.004785668397299115] == approx([500 ± 5.0e-04])` (distance in
  degrees, not metres). Restored: 3 passed.

Historical revert runs (observed 2026-11-05, Python 3.11.11, duckdb 1.5.6 for #1412).
Each ticket landed in one implementation commit. The revert is taken at the
point it landed: the tree of `<impl>^` (`git archive <impl>^`) with the
ticket's own test file from `<impl>` overlaid, run with
`python -m pytest -o addopts="" --rootdir=.. -c ../pyproject.toml -p no:cacheprovider -q -p no:randomly <test file>`
from its `tests/` directory. Head counts are at `e5200588` (develop sync of
`1c4b2793`; the sync changes no engine file). Every failure listed is an
assertion or missing-raise on the ticket's behavior.

- **#1479** (spatial-join column collisions, multi-assign on Spark).
  Node: `tests/test_1479_spark_join_collisions.py::test_spark_join_has_one_geometry_and_suffixes[spatial_join]`.
  Revert of `cabed715` (tree of `cabed715^`): 7 failed / 1 passed; the join
  cases fail with `AssertionError: assert 2 == 1` (two geometry columns),
  `test_spark_multi_assign_stays_native` fails with
  `Failed: multi_assign must not collect to the driver`, and two collision
  cases with `DID NOT RAISE ValueError`. Head: 14 passed.
- **#1497** (nearest, apportion and dissolve reproject projected input to
  EPSG:4326). Node:
  `tests/test_1497_engine_crs_preservation.py::test_nearest_preserves_metres_and_crs[pandas]`.
  Revert of `82369502` (tree of `82369502^`): 30 failed / 3 passed; the
  nearest cases fail with `TypeError: DataFrameEngine.nearest() got an
  unexpected keyword argument 'crs'`, six cases with
  `DID NOT RAISE ValueError`, and a CRS read fails with
  `AttributeError: 'NoneType' object has no attribute 'to_epsg'`. Head: 33
  passed.
- **#1412** (DuckDB `query` drops parameters, GEOMETRY to WKB relabels CRS).
  Node: `tests/test_1412_duckdb_query_wkb_crs.py::test_typed_wkb_preserves_crs[query-value]`.
  Revert of `2b0bd994` (tree of `2b0bd994^`): 27 failed / 0 passed; that node
  fails with `assert 4326 == 3857` (the EPSG:3857 geometry is relabelled
  EPSG:4326), and
  `test_unknown_query_keyword_is_rejected_before_execution` with
  `DID NOT RAISE TypeError`. Head: 50 passed under duckdb 1.5.6 (under duckdb
  1.4.4, 32 cases skip because they need CRS-qualified geometry types).

Context only, not governing (no revert run): #1398 (parent epic); #1463
(`SparkEngine.nearest`, landed on develop through #1793; the PR body calls its
behavior existing baseline); #1749 (an open proposal for per-PR CHANGELOG
fragments, not a ticket this PR implements; it was cited only for the
body-only CHANGELOG convention, and the `[4.1.0]` notes are now in
`CHANGELOG.md`); #1667 (named in the ticket-fitness review, but this PR's
body, diff against develop and branch commits do not reference it).

## Test plan

- Under duckdb 1.4.4 (default_31111, within #1862's pinned range): `pytest tests/test_1852_conversion_siblings.py` -> 8 passed. Without duckdb the module now skips via importorskip instead of producing 8 setup errors.
- At `7cac3e01` under duckdb 1.5.6 (Python 3.11.11): `tests/test_1412_duckdb_query_wkb_crs.py`, `tests/test_1479_spark_join_collisions.py`, `tests/test_1497_engine_crs_preservation.py` and `tests/test_1852_conversion_siblings.py` -> 105 passed, 0 skipped.

## duckdb 1.4.x support (after the develop sync at `695c4b92`)

`pyproject.toml` allows `duckdb>=0.7.0,<2.0`, so duckdb 1.4.x is a supported install. Under the SZSH duckdb 1.4.4, the named and touched #1852 files failed 30 cases, every one with `Binder Error: Type 'GEOMETRY' does not take any type modifiers`.

Which case applies: **tests only (2b)**. The production code never builds a CRS-qualified geometry type. In `siege_utilities/`, `GEOMETRY('` appears only in docstrings. `_geometry_column_positions` (`siege_utilities/engines/dataframe_engine.py:1430-1435`) accepts the bare `GEOMETRY` that 1.4.x reports as well as the qualified `GEOMETRY('EPSG:…')` that 1.5.x reports. `_materialize_geometry_wkb` (`:1496-1504`) runs `ST_CRS(NULL::<type>)` only when the reported type is qualified, which only 1.5.x produces, and maps a bare `GEOMETRY` to unknown CRS (`None`). The 30 failures come from the test helpers `frame` (`tests/test_1852_extra_crs.py`), `_frame` (`tests/test_1852_mixed_crs_inputs.py`) and `raw` (`tests/test_1852_geometry_aware_boundaries.py`), which cast `ST_Point(1,1)::GEOMETRY('EPSG:<n>')` in SQL. duckdb 1.4.x rejects that cast at bind time.

Change: each of the three helpers calls a version gate before a CRS-qualified cast. The gate is identical to `typed_engine` in `tests/test_1412_duckdb_query_wkb_crs.py:21-23`: same `tuple(map(int, duckdb.__version__.split(".")[:2])) < (1, 5)` check and same reason string. Bare-geometry (`crs=None`) cases still run on 1.4.x. No assertion and no library code changed. ruff on the three files: 30 findings before and after (26 E702, 4 E701, all in the existing compact style), none new.

Counts for the 7 files (test_1412, test_1479, test_1497, test_1852_conversion_siblings, test_1852_extra_crs, test_1852_geometry_aware_boundaries, test_1852_mixed_crs_inputs), Python 3.11.11:

| duckdb | before (`695c4b92`) | after |
|---|---|---|
| 1.4.4 (SZSH default) | 30 failed, 136 passed, 32 skipped | 0 failed, 136 passed, 62 skipped |
| 1.5.6 | 198 passed | 198 passed (0 skipped) |

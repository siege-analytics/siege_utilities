# Self-review: R-1818-5 (MERGE durability case below PostgreSQL 17, #1818)

Scope: commit `38999ebe` on PR #1818 (`tests/test_1818_spatial_review_postgis.py`
only) plus this file. No library code changes.

## Assumptions

Domain(s): software engineering (PostGIS connector tests, CI gating).
Goal source: review finding R-1818-5 on #1818. The hosted PostGIS lane runs
PostgreSQL 16.4 (job 126456154969 of run 41794769405) and its no-skip gate
failed on `test_r2_1_mutating_cte_rows_match_durable_state_after_close[MERGE]`,
which skipped below PostgreSQL 17.
Base: PR head `a2e8efd8`; this change is additive.
Working as: software engineer (Junior) and tech lead (Lead); both reviews are
below.

## Peer review

- The `MERGE` case no longer skips. On PostgreSQL 17 and later it keeps the
  existing assertion: `WITH written AS (MERGE ... RETURNING p.*) SELECT * FROM
  written` returns id 8 with EPSG:4326, and the write is durable after success
  and after close.
- Below 17, `MERGE ... RETURNING` and `MERGE` inside `WITH` are not available.
  The case runs the same `MERGE` without `RETURNING` inside `with connector:`
  and asserts the connector's no-row path: the return value is the rowcount
  (`spatial_transformations.py:701`, `cursor.rowcount`), equal to 1 for the one
  matched row, and the connector-owned commit (`:719-721`) makes the write
  durable after success and after close (`[(8,)]` both times).
- This mirrors `test_r7_merge_without_returning_writes_durable_state`, which
  passes on the hosted 16.4 lane.
- The seed `INSERT` moves above the version branch; both branches use it.
- No skip is added, the workflow is unchanged, and no other test changes.

## Lead review

The lane's no-skip gate is the contract; the fix keeps it strict by making
both server versions run a real assertion rather than relaxing the gate.

Hosted CI evidence for the below-17 branch: Actions run 41983741272 on
`b2951ec6` (the first head carrying this change), job `test-postgis`
127099541616, started `PostgreSQL 16.4 (Debian 16.4-1.pgdg110+2)`, so
`server_version < 170000` and the test takes the below-17 path. The job log
shows
`tests/test_1818_spatial_review_postgis.py::test_r2_1_mutating_cte_rows_match_durable_state_after_close[MERGE] PASSED`,
the lane summary `338 passed, 1 skipped`, and the job concluded `success`, so
the lane's "PostGIS database tests must not skip" assertion held. The same
run's main test lanes failed because they resolved `duckdb==2.0.0` (this
branch does not yet carry the `<2.0` pin, #1861 / PR #1867): `test (3.11)`
reports 36 failed, of which 30 are the known class-hardening failures, 3 the
`gis.W001` case (#1868), and 3 are in this PR's DuckDB paths under 2.0:
`test_1414_spatial_transformations_writes.py::test_duckdb_empty_and_projected_results_accept_source_crs`
and `::test_duckdb_legacy_append_preserves_unknown_crs` ("Resource In Use
Error: connection has an unfinished result from execute(); call complete()
..."), and `test_1818_spatial_review_regressions.py::test_b2_empty_table_crs_survives_reconnect[download]`
(regex mismatch). Under duckdb 1.5.6 these pass locally; they are DuckDB 2.0
adaptation work tracked in #1862, not covered by this PR, and the pin removes
2.0 from CI once it reaches this branch. Locally there is no PostgreSQL
15 or 16 cluster (the local server is 14.22); a disposable PostgreSQL 17.11
cluster ran the 17+ branch and a probe of the below-17 statements.

Coverage gap to watch: the below-17 branch runs in hosted CI only because the
lane pins PostgreSQL 16. If the lane moves to 17 or later, that branch stops
executing anywhere in CI. The proposal for that case is a CI-run unit test
that drives the same test body through a connector whose observer reports
`server_version = 160000` against a 17+ server (plain `MERGE` is valid on 17),
so the fallback assertions keep running regardless of the lane's version.

## Ticket-fitness exemption

- **#1414** (spatial_transformations uploads replace tables by default;
  `startswith('SELECT')` misroutes CTE and RETURNING). Reason: written before
  the current evaluate-ticket structure (Problems / Done when / Why p2
  headings); #1398 is the parent epic and context only. The exemption covers
  ticket structure only.
  Node: `tests/test_1414_spatial_transformations_writes.py::test_row_returning_queries_return_rows[cte-postgis]`
  (and `test_duckdb_existing_table_survives_upload[append]`).
  Observed revert run (2026-11-05, Python 3.11.11): #1414 was implemented in
  `b0cf3429` (its tests landed first in `db81d776`). The revert is taken at
  the point it landed: the tree of `b0cf3429^` (`git archive b0cf3429^`) with
  `tests/test_1414_spatial_transformations_writes.py` from `b0cf3429`
  overlaid, run from its `tests/` directory with
  `python -m pytest -o addopts="" --rootdir=.. -c ../pyproject.toml -p no:cacheprovider -q -p no:randomly test_1414_spatial_transformations_writes.py`.
  Result: 25 failed / 1 passed. The CTE and RETURNING cases fail with
  `TypeError: 'int' object is not subscriptable` (a rowcount is returned where
  rows are expected); `test_duckdb_existing_table_survives_upload[append]`
  fails with `RuntimeError: Failed to upload to DuckDB: Catalog Error: Table
  with name "places" already exists!` and the `[default]` case with
  `DID NOT RAISE RuntimeError` (the existing table is dropped);
  `test_postgis_existing_table_survives_failed_upload[default]` and
  `[replace]` fail. Every failure is on #1414's behavior, not an import or
  fixture error. Head (`ba1a28f4`): the same file is 26 passed, with no live
  database needed. Broader evidence at `38999ebe`: the non-live #1414/#1818
  suites ran as 169 passed and 31 skipped (all for the missing live-PostGIS
  DSN).

## Test plan

- `ruff check tests/test_1818_spatial_review_postgis.py`: all checks passed.
- Collection: the four `test_r2_1_mutating_cte_rows_match_durable_state_after_close`
  cases collect; without a DSN they skip in the existing fixture guard.
- Local non-live suites listed above: 169 passed, 31 skipped (DSN only).
- Live PostgreSQL 16.4 (hosted): run 41983741272, job 127099541616 on
  `b2951ec6`: the `[MERGE]` case PASSED on the below-17 path; lane 338 passed,
  1 skipped; job `success`.

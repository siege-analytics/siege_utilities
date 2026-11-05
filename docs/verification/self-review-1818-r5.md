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
both server versions run a real assertion rather than relaxing the gate. The
remaining risk is that the below-17 branch has not run on a live PostgreSQL 15
or 16 locally (the local server is 14.22 and no 15 or 16 cluster is
available), so the hosted 16.4 lane is its first execution. If it fails there,
the failure is visible in that lane, not hidden by a skip.

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
- Live PostgreSQL 16.4: the hosted PostGIS lane on the pushed head.

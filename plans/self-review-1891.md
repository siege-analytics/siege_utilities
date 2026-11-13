---
ticket_refs:
  - siege-analytics/siege_utilities#1891: pre-implementation record https://github.com/siege-analytics/siege_utilities/issues/1891#issuecomment-6842143287
---

# Self-review: #1891, TemporalTimeseriesBuilder groups the snapshot frame once

Working as: software engineer

Goal source: https://github.com/siege-analytics/siege_utilities/issues/1891
Review-Tier: C
Pre-author-inventory: https://github.com/siege-analytics/siege_utilities/issues/1891#issuecomment-6842143287
Investigate-artifact: https://github.com/siege-analytics/siege_utilities/issues/1891#issuecomment-6842143287 (Investigation fact sheet)
Pre-mortem-artifact: https://github.com/siege-analytics/siege_utilities/issues/1891#issuecomment-6842143287 (Pre-mortem)
Base: develop `6c049c2c`

## Change

`siege_utilities/geo/temporal/services.py`, `TemporalTimeseriesBuilder.build`:

- Before: for every requested variable, `boundary_ids = snapshots_df["boundary_id"].unique()`,
  then for every boundary `snapshots_df[snapshots_df["boundary_id"] == bid]` and `iterrows()`.
  Each boundary scanned the whole frame, once per variable: O(V x B x N).
- After: on the first variable only, `boundary_ids` is computed the same way and
  `_positions_by_boundary(snapshots_df, boundary_ids)` returns the row positions of each entry
  in frame order. Every variable then iterates `boundary_ids` in the same order and reads each
  boundary's rows with `snapshots_df.take(positions).iterrows()`. Grouping is O(N) once; row
  reads are O(V x N), as before per row.
- `_positions_by_boundary`: `pd.factorize(..., sort=False)` groups ids (missing ids coded -1,
  so they get no group); `pd.Index(uniques).get_indexer(boundary_ids)` matches each id to its
  group with pandas' own lookup; a missing id gets an empty list.
- The per-row body (year None/NaN skip, `int()`, requested-year filter, `row.get("values", {})`,
  None value skip, MOE lookup), the statistics and the schema construction are unchanged.

`CHANGELOG.md`: one `[Unreleased]` / `### Fixed` entry (#1891).

`tests/test_temporal_builder_grouping_1891.py`: new.

## Equivalence argument

- Order: `boundary_ids` is still `unique()` (first appearance); the zip keeps that order.
- Rows per boundary: positions are collected in frame order, so `take()` yields the same rows
  in the same order as the boolean filter; the last duplicate year still wins.
- Dtypes: `take()` and boolean indexing both return a sub-frame with the frame's columns and
  dtypes, so `iterrows()` yields the same per-row values.
- Missing ids: `== None`/`== NaN` matched no rows; factorize gives them no group and
  `get_indexer` returns -1, so they get no rows and each still counts as one skipped boundary.
- Error timing: grouping happens inside the variable loop, so an empty `variables` list still
  reads no column; a missing `boundary_id` column still raises `KeyError` at `unique()`; a
  missing `year` column still raises at `row["year"]`, only when a boundary has rows.
- Known limit: equivalence relies on pandas' hash-table id equivalence (shared by `unique()`,
  `factorize` and `get_indexer`) matching elementwise `==`. That holds for str, int, float,
  datetime, categorical, None and NaN ids, which the tests cover.

## Rework ledger

Design changes made during self-review, before staging:

1. A first draft cached every boundary's rows as pandas Series across variables. Rejected:
   memory proportional to N with a large per-row constant (hundreds of MB for a tract-level
   frame), which the old loop never held. Now only integer positions are cached.
2. A second draft keyed a dict by factorize's uniques and looked ids up with `dict.get`.
   Rejected: `unique()` yields numpy scalars (e.g. `np.datetime64`) while the factorized Index
   yields pandas scalars (`Timestamp`), whose Python hashes can differ, so a datetime id could
   miss its rows. Now `Index.get_indexer` does the lookup.

## Peer review

Syntax check: NOT RUN locally (local env blocked). `ast.parse` on the 2 changed `.py` files
has not been run; exact-head CI import and collection is the evidence.
Test suite: NOT RUN locally (local env blocked); CI is the evidence. Neither the new test file
nor the existing temporal tests have been run locally. Nothing here claims a pass. Command for
a working environment:

`cd tests && python -m pytest -o addopts="" --rootdir=.. -c ../pyproject.toml -p no:cacheprovider test_temporal_builder_grouping_1891.py test_temporal_services.py test_exception_contracts.py -q`

Cases (each compares the new builder field by field with a verbatim copy of the old loop):
empty frame with columns; single boundary; missing requested year; duplicate years (last row
wins, MOE follows); unrequested year; NaN year; NaN and None boundary ids; mixed int/str ids
interleaved; value None and variable absent; non-dict `values`/`moe_values` cells; int64 ids;
float ids with NaN; datetime ids; categorical ids with a missing value.
Direct assertions: first-appearance (unsorted) boundary order; missing ids each count as one
skipped boundary; duplicate year keeps the last row; the frame is grouped exactly once for
three variables; no grouping and no column read with an empty variable list; missing
`boundary_id` and missing `year` raise `KeyError` in both implementations; a missing `year`
column with only missing ids does not raise in either.

Negative tests: the two `KeyError` cases and the no-variables case pin the error paths. A
red-on-revert check is not meaningful for a pure refactor (the oracle is the old algorithm);
the grouped-once test is the one that fails on the old loop's structure.

## Rules

- SU-1: no new `except` or empty-on-error return; the SU-1 grep hits in this module are
  pre-existing lines outside the diff.
- SU-2: no public signature or docstring claim changed.
- SU-4a: no notebook calls `TemporalTimeseriesBuilder` (grep of `notebooks/`); the contract is
  unchanged, so no notebook update. The missing notebook coverage is pre-existing.
- SU-4b: error paths covered as above.
- SU-5: 3 files change (plus this record); the parse check is NOT RUN locally (local env
  blocked); CI is the evidence.

## Lead review

Implementer-authored adversarial pass only; not an independent hostile review. Checked:
order, NaN/None ids, duplicate years, dtype preservation, error timing, memory, numpy versus
pandas scalar lookup, mixed-type object ids, categorical ids, empty frames.

## Findings

- Fixed before staging: cached row objects (memory) and dict lookup by scalar hash (datetime
  ids). See the rework ledger.
- Open: the syntax check and tests are NOT RUN locally (local env blocked); exact-head CI is
  the evidence and must be green on these tests before merge.
- Open, nonblocking: no independent hostile review yet; no benchmark (no performance claim).
- Ticket copy: https://github.com/siege-analytics/siege_utilities/issues/1891#issuecomment-6842389878

## Rollback

Revert the single commit; no data, schema or API migration.

## Not verified

- No test, syntax check or benchmark has been run locally (local env blocked); CI is the
  evidence.
- No performance figure is claimed; only the removal of the per-boundary full-frame scan.

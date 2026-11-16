---
ticket_refs:
  - siege-analytics/siege_utilities#1891: pre-implementation record https://github.com/siege-analytics/siege_utilities/issues/1891#issuecomment-6842143287
---

# Self-review: #1891, TemporalTimeseriesBuilder groups the snapshot frame once

## Assumptions

Working as: software engineer

Goal source: https://github.com/siege-analytics/siege_utilities/issues/1891
Review-Tier: C
Pre-author-inventory: https://github.com/siege-analytics/siege_utilities/issues/1891#issuecomment-6842143287
Investigate-artifact: https://github.com/siege-analytics/siege_utilities/issues/1891#issuecomment-6842143287 (Investigation fact sheet)
Pre-mortem-artifact: https://github.com/siege-analytics/siege_utilities/issues/1891#issuecomment-6842143287 (Pre-mortem)
Hostile-review-artifact: https://github.com/siege-analytics/siege_utilities/issues/1891#issuecomment-6842576602
Project-contribution: the temporal time-series builder no longer rescans the whole snapshot frame per boundary per variable, so multi-variable builds over tract-level census vintages stay practical for downstream where-when analysis
Base: develop `6c049c2c`

Stated assumptions:
- `boundary_id` values are the hashable scalar types the builder sees in practice (GEOID strings, integers); exotic id types are out of scope for this change (see Findings).
- pandas 2.x semantics (the project pins `pandas>=2.0,<3.0`): `Series.unique()`, `pd.factorize` and `Index.get_indexer` share one hash-table equivalence.
- The previous loop at develop `6c049c2c` is the behavioral reference; the change must not alter any output for supported id types.

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

Shelves: writing-tests:1 (the new tests import `siege_utilities.geo.temporal.services` and
assert the builder's output; the oracle is the previous algorithm, not the new one, so a
behavior change in the builder turns the equivalence cases red); writing-claims:2 (the counts
below carry their command; the commit's Verified-by trailer repeats them).

History: this file at commit 9b76f485 (tree 7de65494) said the syntax check and tests were NOT
RUN locally (local environment host-blocked). That was written when the tree was staged. The
syntax parse below then ran before the commit on that same staged tree (the 9b76f485 commit
message records it); the tests ran only after the commit.

- Syntax check, before commit 9b76f485, on staged tree 7de65494, 2026-11-12 ~21:01 CST: `python3 -m py_compile siege_utilities/geo/temporal/services.py tests/test_temporal_builder_grouping_1891.py` under the system Python 3.9.6 → exit 0 (parse only, not a test run).
- Test suite, AFTER 9b76f485, on its tree 7de65494 (worktree clean, HEAD = 9b76f485), 2026-11-12 ~21:12 CST: `python -m pytest -o addopts="" -p no:cacheprovider tests/test_temporal_builder_grouping_1891.py tests/test_temporal_services.py -q` from the worktree root, Python 3.11.11 → 42 passed in 1.08s (exit 0). The grouped-once and no-variables tests monkeypatch `_positions_by_boundary`, which exists only in the new code, so the worktree code was the code under test.
- Notebook API check: N/A (no notebook calls `TemporalTimeseriesBuilder`).

Command used for the equivalence and temporal tests (also runnable from `tests/` with
`--rootdir=..`):

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
- SU-5: 3 files change (plus this record); both changed `.py` files parse (syntax check above,
  exit 0).

## Lead review

Implementer-authored adversarial pass. Checked: order, NaN/None ids, duplicate years, dtype
preservation, error timing, memory, numpy versus pandas scalar lookup, mixed-type object ids,
categorical ids, empty frames.

Independent hostile review: a fresh-context adversarial reviewer, given the old loop and the
staged diff only (read-only, no interpreter), found no S1 or S2:
https://github.com/siege-analytics/siege_utilities/issues/1891#issuecomment-6842576602

## Findings

- Fixed before staging: cached row objects (memory) and dict lookup by scalar hash (datetime
  ids). See the rework ledger.
- Resolved after commit 9b76f485: the syntax check (exit 0) and the 42 equivalence and temporal
  tests (42 passed) ran; see Peer review. Exact-head CI remains the full-suite evidence.
- Hostile-review S3/S4, nonblocking: exotic `boundary_id` types (overlapping Interval ids, and
  `Timestamp`/`np.datetime64` objects for the same instant in one object column) make
  `get_indexer` raise where the old `==` filter worked; tuple ids change behavior; nullable
  `Int64`/`string` with pd.NA, tz-aware, bool, unused categories and a non-default index are not
  yet in the equivalence tests. Tracked in #1897.
- Open, nonblocking: no benchmark (no performance claim).
- Ticket copy of the self-review: https://github.com/siege-analytics/siege_utilities/issues/1891#issuecomment-6842389878

## Rollback

Revert the single commit; no data, schema or API migration.

## Not verified

- Only the two test files above ran locally; the full suite has not run locally, and
  exact-head CI is the full-suite evidence.
- No benchmark: no performance figure is claimed; only the removal of the per-boundary
  full-frame scan.
- The exotic-id divergences in Findings are reasoned by the hostile review, not reproduced.

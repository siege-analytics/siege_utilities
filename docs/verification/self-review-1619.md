# Self-review: semantic CRS comparison in the shared spatial_join check (#1619, PR #1751)

Scope: one commit on PR #1751 after `0e8dfeb3`. Production change:
`siege_utilities/engines/dataframe_engine.py` (`_same_crs`, used by
`_validate_spatial_join_crs`). Tests: `tests/test_1619_crs_semantic_compare.py`
(new) and one added parameter in `tests/test_spatial_join_crs_check.py`. Docs:
`docs/engines/INVARIANTS.md` and the existing #1619 CHANGELOG entry.

Written 2026-11-11, after the original implementation at `0e8dfeb3`
(authored and committed 2026-10-18). The investigation, pre-mortem, Junior
task description and Senior adversarial checklist for this round are on
#1619 (issuecomment-6800336384 restates them under ticket headings). No
investigation, pre-mortem or hostile review was recorded for the original
round; those remain absent for it.

## Assumptions

Domain(s): software engineering, data engineering (geospatial).
Geospatial cross-cut: yes.
Goal source: #1619 and the review decision on PR #1751 to compare known CRS
metadata semantically through pyproj, keeping static attribute inspection,
the mismatch `ValueError` and its message, with no reprojection, no CRS
inference from WKT, no axis-order relaxation and no new packaging scope.
Review-Tier: B (content). The local pre-commit gate classified this
worktree's actions as tier C from whole-tree paths that are not in the PR
diff, so the tier C local artifacts (Junior and Senior comments, posted
investigation and pre-mortem) were produced as well. That does not change
the content tier.
Working as: software engineer (Junior) and tech lead (Lead). An independent
fresh-context reviewer attacked the design before implementation; its items
and the responses are in the Senior checklist on #1619.

1. The defect is reachable only through explicit CRS metadata that is not a
   pyproj `CRS`, in practice a Spark frame's `crs` attribute. A
   GeoDataFrame's `.crs` is a pyproj `CRS`, whose `__eq__` already parses the
   other operand, so the Pandas, DuckDB and PostGIS paths compared
   semantically before this change.
2. pyproj belongs to the optional `geo` extra. It is imported only inside
   `_same_crs`, after both values are known and not literally equal.
3. In installed pyproj 3.7.2, `CRSError` subclasses `ProjError(RuntimeError)`,
   and `DataDirError` also subclasses `RuntimeError`. Catching
   `(CRSError, ValueError, TypeError)` treats unparseable metadata as a
   different CRS (the existing mismatch error) and lets a broken PROJ
   installation surface as itself.
4. Equality is pyproj's default `CRS.__eq__`, which is sensitive to axis
   order, the same policy as `geo.crs.reproject_if_needed`. The
   `geo.crs._normalize_crs` helper is not reused: it raises a different
   `ValueError` and collapses to an EPSG code.

## Test plan

Local Python 3.11.11, pytest 8.4.2, pyproj 3.7.2, pyspark with a real local
SparkSession. Runs clear the coverage addopts. Every traceback and the
import-path tests show the checkout's module, not an installed copy.

- Parent control 1: the new test file as first written, on unmodified
  `0e8dfeb3`: 3 failed, 11 passed.
  - The two case-variant tests fail with the false mismatch
    (`left has EPSG:4326, right has epsg:4326`).
  - The no-pyproj warning test fails because no warning exists.
  - The CRS-object against string test passes on the parent; it is a guard,
    not a defect control.
- Parent control 2: the extended tests, still on unmodified `0e8dfeb3`:
  6 failed, 46 passed.
  - Failing because of the defect: the two case-variant tests, the integer
    `4326` against `"EPSG:4326"` test, and the Spark engine-level
    `case_variant` case, which ran against a real SparkSession.
  - Failing because the parent never consults pyproj: the `DataDirError`
    propagation test.
  - Failing because there is no warning: the no-pyproj test.
- With the change, the two files pass: 52 passed, 0 skipped. That includes
  all four Spark cases and the `postgis`-marked driver-side cases.
- Regression sweep: 153 passed, test order randomized. Files:
  - `tests/property/test_spatial_join_invariants.py`
  - `tests/test_dataframe_engine_spatial.py`
  - `tests/test_h3_utils.py`
  - `tests/test_s2_utils.py`
  - the two files above
- `py_compile` on the three changed Python files: exit 0.

Negative tests present:
- 4326 against 3857 raises the exact message, as strings and as object
  against string.
- `OGC:CRS84` against `EPSG:4326` still raises (no axis-order relaxation).
- Unparseable strings and non-string objects never match.
- `DataDirError` propagates rather than becoming a mismatch.
- Without pyproj, literally different values raise the mismatch and log one
  warning.
- A Spark data column named `crs` is ignored.
- Importing the engine module does not load pyproj, and validation works
  with pyproj blocked.

Not run here:
- The full repository suite.
- PostGIS against a live database. The `postgis`-marked cases in these files
  join on the driver and open no connection.

Exact-head CI must show the named tests executing, not skipped.

## Peer review

- `_same_crs` has one consumer and stays private. No new public helper.
- The static `crs` read, the exception type and the message f-string
  (original values) are unchanged.
- SU-1: the two `return False` statements inside `except` blocks are not
  valid-shaped empty results. They mean "not the same CRS", and the caller
  then raises the existing `ValueError`, so the failure stays visible. The
  ImportError path also logs a warning naming the `geo` extra.
- SU-4a: no notebook calls `spatial_join` with CRS metadata
  (`notebooks/spatial/07_natural_language_to_geometry.ipynb` mentions it only
  in prose and a diagram). Noted as a documentation gap.
- Class scan: the other raw `.crs` comparisons (`geo/crs.py:110`,
  `geo/temporal/query.py:100`, `geo/providers/redistricting_data_hub.py:1334`,
  `geo/interpolation/areal.py:108`) compare GeoDataFrame CRS objects, which is
  already semantic. Out of scope by the review decision.

## Findings

| ID | Priority | Description | Resolution |
|----|----------|-------------|------------|
| F1 | P3 | Array-like CRS metadata would make the literal `==` shortcut raise an ambiguous-truth error, as on the parent. CRS metadata is expected to be scalar. | noted |
| F2 | P3 | Without pyproj, case-variant metadata still raises, with a warning that names the `geo` extra. | noted (fails closed by design) |
| F3 | P3 | A Spark mismatch test that needs no JVM was suggested by the independent review; the real-Spark tests ran locally instead. | noted |
| F4 | P2 | The CHANGELOG entry still sits under `[Unreleased]` `### Fixed`. Develop integration must move it to the BREAKING section with a Migration line. | open: develop integration step, outside this commit |

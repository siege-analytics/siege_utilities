# Cross-backend engine invariants

The `DataFrameEngine` premise -- consumer code should not branch on backend -- is unverified. `PandasEngine`, `DuckDBEngine`, `SparkEngine`, and `PostGISEngine` diverge in edge cases: empty inputs, NaN propagation, sort stability, identifier validation. This doc pins down what *must* be the same and what is allowed to differ.

## How to read this doc

Each operation has:

- **Required input shape** -- what the caller is responsible for providing.
- **Required output shape** -- what the engine guarantees in return.
- **Tolerances** -- where each engine is allowed to differ, with the rationale.
- **Open question** -- anything still TBD.

The granularity is operation-level, not backend-level. If an engine can't meet an invariant, that's a bug fix, not a reason to weaken the invariant.

## Universal invariants (apply to every operation)

1. **Empty input → empty output, never raise.** A 0-row DataFrame in must yield a 0-row DataFrame out, with the correct schema. Engines that currently raise on empty input (Spark's groupby occasionally; PostGIS on aggregations) are bugs.
2. **Schema invariance.** Output column names + dtypes are reproducible from `(operation, input_schema)`. No engine may add a backend-specific metadata column.
3. **No silent NaN coercion across backends.** If pandas produces `NaN`, the other engines must produce their backend-native missing value (`None` for DuckDB/PostGIS, `null` for Spark), and `to_pandas()` must round-trip it back to `NaN`.
4. **Identifier validation at the engine boundary.** _Aspiration, not current behavior._ Today only the upload/DDL paths in `SnowflakeConnector` and `spatial_transformations` call `validate_sql_identifier`; the engine-level operations (`groupby_agg`, `filter`, `join`) do not. Listed here so property-test work can pin the invariant once the engines route through validation.

## Per-operation invariants

### `read_csv(path, *, schema=None)`

- **Input:** UTF-8 CSV file at *path*. Optional schema dict; when present, engines must coerce dtypes to match.
- **Output:** DataFrame with header row as columns, all subsequent rows as data.
- **Tolerance:**
  - Spark may infer numeric columns as `LongType` where pandas picks `Int64` -- equivalent under `to_pandas()`.
  - PostGIS reads via `COPY FROM`; identifier rules apply.
- **Open question:** behavior on malformed UTF-8 -- fail fast vs. replace.

### `read_parquet(path)`

- **Input:** Parquet file at *path* (single-file or directory of part-files).
- **Output:** DataFrame with the parquet schema.
- **Tolerance:** none -- parquet is self-describing. Divergences are bugs.

### `groupby_agg(by, agg_dict)`

- **Input:** `by` is a column or list of columns; `agg_dict` maps `column -> agg_name` where `agg_name` is one of `sum`, `mean`, `avg` (synonym for `mean`), `count`, `min`, `max`, `first`, `last`, `stddev`, `variance`, `approx_count_distinct`. Unknown names raise `ValueError` on every engine; the shared `_SUPPORTED_AGG_NAMES` constant in `dataframe_engine.py` is the source of truth.
- **Output:** One row per unique `by` tuple, including tuples with NULL keys (pandas `dropna=False`, matching SQL/Spark), with one column per `agg_dict` entry. The output column name **equals the input column name** (pandas `df.groupby(...).agg({col: fn}).reset_index()` convention -- the aggregated value replaces the original column with no suffix). Non-pandas engines must match this, not append `_{agg_name}`. Plus the `by` columns.
- **Tolerance:**
  - Sort order is not guaranteed. Callers that need ordering must call `.sort_values()` themselves. Tests compare row contents as a multiset, not a list.
  - `sum`, `mean`/`avg`, `min`, and `max` ignore missing values and return NULL (NaN/NA in pandas) when a group has no non-null values. `count` excludes missing values and returns 0 for an all-null group. A partially-null group sums its non-null values; a genuine zero sum remains 0. These rules also apply to NULL-key groups and match SQL/Spark NULL semantics. Spark inputs must represent missing values as SQL NULL; IEEE NaN in a Spark numeric column is a distinct value.
  - **Residual `first`/`last` difference (#1454):** PandasEngine, DuckDBEngine, and PostGISEngine aggregate in pandas and return the first/last non-null value in the supplied frame's row order, or a missing value for an all-null group. This is deterministic for a fixed input order. SparkEngine uses `F.first`/`F.last` with `ignorenulls=False`, so it includes NULLs and has no guaranteed encounter order after a shuffle. SQL `first`/`last` behavior depends on the backend and explicit ordering/null-handling options; DuckDB SQL includes NULLs by default. Cross-engine `first`/`last` parity is not guaranteed by this API, which has no ordering parameter; SparkEngine is unchanged by #1454.
- All four engines call the shared `_validate_agg_names` at the top of `groupby_agg`; unknown names raise `ValueError`, and an empty `agg_dict` raises `ValueError` with the same shape.

### `filter(condition)`

- **Input:** boolean Series or expression string.
- **Output:** DataFrame containing only rows where `condition` is True.
- **Tolerance:** NaN in the condition is treated as False on every backend. (PostGIS treats it as `UNKNOWN` natively; the engine must coerce to False before applying.)

### `join(other, on, how)`

- **Input:** another DataFrame; `on` is column or list; `how ∈ {inner, left, right, outer}`.
- **Output:** Join semantics per `how`. Column collision is resolved by appending `_left` / `_right` suffixes (pandas default behavior -- other engines must match).
- **Tolerance:**
  - Row order on `outer` is not guaranteed.
  - PostGIS may not support arbitrary join keys (must be indexable); the engine raises `NotImplementedError` on the unsupported key types rather than silently coercing.
- **Open question:** what is the canonical behavior when the same join key has duplicates on both sides? Pandas cross-product; Spark same; PostGIS same. Confirm and pin.

### `spatial_join(other, predicate)`

- **Input:** two GeoDataFrames; `predicate ∈ {intersects, contains, within}`.
- **Output:** rows from the left side, joined with the matching rows from the right side, indexed by `(left_idx, right_idx)`.
- **Tolerance:**
  - **Relation semantics modes** (BOUNDED / HALFPLANE / CONTAINS_CENTROID) are an explicit parameter; engines must respect it identically.
  - Sort order is not guaranteed.
- **Caller-aligned CRS contract.** Both inputs must already be in the same CRS at call time. A shared check raises `ValueError` before the join when both inputs have known, different CRS. Pandas, DuckDB, and PostGIS check the GeoDataFrames passed to `gpd.sjoin`; Spark checks explicit frame `crs` attributes when available. Missing or `None` CRS remains allowed. Spark's WKT conversion does not preserve CRS metadata, and a data column named `crs` is not metadata, so callers must still align those coordinates themselves. Engines do not reproject inputs. The convenience methods that delegate to `spatial_join` inherit the check (#1619).

### `to_geodataframe(geometry_column="geometry")`

- **Input:** DataFrame with a column of either WKT strings or GeoJSON dicts.
- **Output:** GeoDataFrame with that column converted to shapely geometries.
- **Tolerance:**
  - Missing column → `ValueError` with the column name in the message.
  - Mixed-type column (some WKT, some GeoJSON) → `ValueError`, not silent partial conversion.
- All four engines must raise `ValueError` when the column is missing. PandasEngine already does (`dataframe_engine.py:646`). Pin the others with property tests.

### `index_points(grid, resolution)` / `index_polygon(grid, resolution)`

- **Input:** GeoDataFrame; `grid ∈ {h3, s2}`; `resolution` int.
- **Output:** Original frame + an `{grid}_id` column (e.g. `h3_id` string or `s2_id` int64).
- **Tolerance:**
  - **`index_points`**: one cell ID per row. Deterministic across backends.
  - **`index_polygon`**: zero, one, or many cell IDs per row (the polygon may overlap multiple cells). Output is a new row per `(input_row, cell_id)` pair. Number of cells per input row must match across backends within a `±1` tolerance at cell boundaries (this is the H3/S2 library's edge-case difference; pin the tolerance, don't try to eliminate it).

## Out of scope

- **Performance invariants.** Hot-path perf lives in `tests/perf/`; this doc is about correctness only.
- **API surface.** We're testing the existing public surface, not redesigning it. Anything that would require a new method on `DataFrameEngine` is out of scope.
- **Cross-engine optimization.** No "we will detect that PandasEngine and DuckDBEngine produce equivalent output and skip one" tricks. The point of property testing is to *find* divergences, not paper over them.

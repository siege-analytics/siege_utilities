# Self-review -- #1852 pre-flight round (13 review threads)

## Assumptions

Working as: software engineer (Junior) and tech lead (Lead).
Goal source: the 13 open review threads on #1852 at `46f7b249`.
Domain(s): software engineering (engine CRS contracts, Spark SQL joins, test hygiene).
Base: additive commit on fix/engine-cluster @ `46f7b249`.

## Thread dispositions

| Thread | Finding | Disposition |
|---|---|---|
| 4478425316 | Spark projection keeps only the left geometry under right/outer joins | FIX: `_spatial_join_projection` takes `how` and rejects anything but `inner`/`left` before any temp view is registered; both callers pass `how`. `tests/test_1852_spark_join_types.py`. |
| 4478425304 | Base operations relabel plain WKT instead of reprojecting it | FIX: base `_operation_frame` reads at the source CRS (plain WKT at EPSG:4326), then reprojects a known CRS or assigns an unknown one; used by base `dissolve`, `apportion` and `nearest`. Spark overrides it to assign, because Spark stores no source CRS. `tests/test_1852_plain_wkt_operations.py`. |
| 4420609855 | Spark apportion `crs=` cannot reproject | KEEP assign semantics (operator ruling B), documented. v4.0.0 apportion had no `crs` and no projected-CRS requirement, and ran on Spark in the stored coordinates. 4.1.0 requires a projected measurement CRS, and a Spark frame without `crs` is labelled EPSG:4326, so passing `crs` is the only working path. Rejecting it would make every Spark apportion call raise. v4.0.0 `SparkEngine.to_geodataframe` already defines `crs` as assign ("pass the crs the coordinates are actually in"). The base `apportion` docstring and the CHANGELOG now state that on Spark `crs` declares the stored CRS and point to `read_spatial(crs=...)` or `to_pandas` plus `to_crs` for reprojection. `tests/test_1852_spark_apportion_crs.py`: with the declared projected CRS, Spark matches the pandas engine. No lon/lat-bounds heuristic (false positives on small projected extents). Left for the reviewer's explicit accept. |
| 4424699771 | `_column_crs` falls back to stale attrs for a live unknown GeoSeries | ADDRESSED in `f24ff5c8` (a real GeoSeries is authoritative even when its CRS is None). Added the requested outer-join regression `test_mixed_outer_live_unknown_geoseries_ignores_stale_known_attrs`. |
| 4463189134 | No test for a plain DataFrame with a `crs` column in Spark `from_geodataframe` | FIX: `tests/test_1852_spark_from_geodataframe.py` (warning fires; the column stays data). |
| 4420609863 | Type hints on four helpers | FIX: `_require_projected_crs`, `_boundary_column_names`, `_bind_spatial_if_needed`, `_spatial_join_projection`. |
| 4424699727 | Geometry join test does not assert the retained row | FIX: `test_key_geometry_source_selected_while_nonkey_geometry_keeps_own_crs` asserts one row and the key and suffixed values. |
| 4428118201 | Module errors without GeoPandas | FIX: `pytest.importorskip("geopandas")` before the GeoPandas-dependent imports. |
| 4424699760, 4428118214 | CRS-qualified DuckDB cases need duckdb 1.5 | ADDRESSED in `32acf93f`: `require_typed_geometry` gates every CRS-qualified cast in `tests/test_1852_extra_crs.py` and `tests/test_1852_geometry_aware_boundaries.py`. |
| 4420609842, 4420609847 | Unstable references and a stale claim in `self-review-1852-r1r2.md` | ADDRESSED in `22750edb`, which removed that file; the claim appears nowhere else. |
| 4478425298 | r5 results not tied to the reviewed revision | FIX: r5 now records that `c157abff` and `7cac3e01` are ancestors of `eff07712` and that the intervening diffs touch no tested code. |

## Red on revert

Each behavioural fix was reverted in memory (a patched method, nothing on disk) and its tests run:

- Join-type rejection reverted to always building the projection: 10 of 14 cases in `test_1852_spark_join_types.py` fail (`DID NOT RAISE ValueError`); the 4 inner/left controls pass.
- `_operation_frame` reverted to `to_geodataframe(..., crs=crs)`: 9 of 9 in `test_1852_plain_wkt_operations.py` fail (lon/lat values relabelled as metres).
- `_column_crs` reverted to the attrs fallback: the new outer-join case fails (`DID NOT RAISE ValueError`); the other 11 pass.
- `from_geodataframe` with attribute access in place of the `isinstance` check: the new test fails on the warning assertion.
- Spark's `_operation_frame` override removed, so Spark falls back to the base read-then-reproject: `test_1852_spark_apportion_crs.py` fails (the stored metres are reprojected as degrees, and GEOS raises on NaN/Inf).
- `geopandas` made unimportable: `test_1852_geometry_aware_boundaries.py` reports 1 skipped instead of a collection error.

## CHANGELOG

- The #1479 BREAKING entry now states that Spark `spatial_join` and `assign_boundaries` reject `right`/`outer`/`full`. v4.0.0 ran them (checked against the `v4.0.0` source), so this is BREAKING; the Migration line says to swap the inputs and use `how="left"`.
- The #1497 BREAKING entry now says explicitly that v4.0.0 imposed no projected-CRS requirement on apportion or nearest (it measured in the EPSG:4326 frame `to_geodataframe` returned), so a v4.0.0 call with geographic input now raises on every engine; its Migration line already covers this.
- The #1497 entry spells out that plain WKT is read at EPSG:4326 and reprojected to a requested `crs`, and that on Spark `crs` on `apportion` and `dissolve` declares the stored CRS (Spark `nearest` takes no `crs`). `crs` on dissolve, apportion and nearest is new in 4.1.0 (absent at `v4.0.0`), so this changes no v4.0.0 caller.

## Lead review

In software engineering: the library changes are confined to `siege_utilities/engines/dataframe_engine.py`. They are a join-type guard on the Spark projection, one shared read-then-reproject step for the three base operations, and type hints. The blast radius is Spark spatial joins (right/outer now raise) and base operations called with plain WKT and a `crs` (now reprojected). Both are covered by new tests that fail on revert.

## Test plan

32 test files that import the engine (including the new ones), Python 3.11.11:

| duckdb | result |
|---|---|
| 1.4.4 | 593 passed, 71 skipped |
| 1.5.6 | 656 passed, 8 skipped |

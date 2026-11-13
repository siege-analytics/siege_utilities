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
| 4420609855 | Spark apportion `crs=` cannot reproject | KEEP assign semantics (option B, a working choice made during this round and refined by the reviewer on 2026-11-09; the reviewer accepted it on technical grounds on 2026-11-10, which is a prospective technical acceptance, not a backdated owner permission; see the provenance note below), documented as a truthful shared contract. v4.0.0 apportion had no `crs` and no projected-CRS requirement, and ran on Spark in the stored coordinates. 5.0.0 (then named 4.1.0) requires a projected measurement CRS, and a Spark frame without `crs` is labelled EPSG:4326, so passing `crs` is the only working path; rejecting it would make every Spark apportion call raise. v4.0.0 `SparkEngine.to_geodataframe` already defines `crs` as assign ("pass the crs the coordinates are actually in"). The base `apportion` docstring no longer promises that `crs` reprojects both inputs. It states per input: a known CRS (GeoDataFrame, DuckDB WKB with an attrs CRS) is transformed; plain WKT on Pandas/DuckDB/PostGIS is read as EPSG:4326 and transformed; no-CRS geometry and every Spark frame are declared, not transformed, so the coordinates must already be in that projected CRS, and degrees must never be declared as projected. `dissolve` and `nearest` point to that contract. `tests/test_1852_spark_apportion_crs.py`: a declared projected CRS matches pandas (300/700) and keeps the stored coordinates (250/750); a declared EPSG:4326 and no declaration are refused; a no-CRS GeoDataFrame is refused without `crs` and declared with it. No lon/lat-bounds heuristic (false positives on small projected extents). Left for the reviewer's explicit accept. |
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
- Refinement round: Spark `_operation_frame` patched to the base read-then-reproject: the 300/700 and 250/750 tests fail and the 3 rejection controls pass. `_require_projected_crs` patched to a no-op: the 3 rejection controls fail and the 2 valid cases pass.
- `geopandas` made unimportable: `test_1852_geometry_aware_boundaries.py` reports 1 skipped instead of a collection error.

## CHANGELOG

- The #1479 BREAKING entry now states that Spark `spatial_join` and `assign_boundaries` reject `right`/`outer`/`full`. v4.0.0 ran them (checked against the `v4.0.0` source), so this is BREAKING. The Migration line says to swap the inputs, use `how="left"` and reverse a directional predicate (`within` and `contains` swap; swapping alone would make `assign_boundaries` test whether a point contains a polygon). For `assign_boundaries` with `how="right"` it gives `spatial_join(polygons, points, how="left", predicate="contains")` (corrected in the findings round below).
- The #1497 BREAKING entry now says explicitly that v4.0.0 imposed no projected-CRS requirement on apportion or nearest (it measured in the EPSG:4326 frame `to_geodataframe` returned), so a v4.0.0 call with geographic input now raises in apportion on every engine and in nearest on the Pandas, DuckDB and PostGIS engines. `SparkEngine.nearest` keeps v4.0.0's stored-unit behaviour (scoped in the findings round below). The Migration line already covers this.
- The #1497 entry spells out that plain WKT is read at EPSG:4326 and reprojected to a requested `crs`, and that on Spark `crs` on `apportion` and `dissolve` declares the stored CRS (Spark `nearest` takes no `crs`). `crs` on dissolve, apportion and nearest is new in 5.0.0, then named 4.1.0 (absent at `v4.0.0`), so this changes no v4.0.0 caller.
- Refinement round: no new BREAKING classification. The #1497 Migration line now says that `crs=` transforms only known-CRS inputs (plain WKT included) and only declares on Spark frames and no-CRS geometry, and that a call without `crs` on Spark frames or plain WKT, which v4.0.0 ran on the stored coordinates (checked at the `v4.0.0` tag), now raises under the default EPSG:4326.

## Lead review

In software engineering: the library changes are confined to `siege_utilities/engines/dataframe_engine.py`. They are a join-type guard on the Spark projection, one shared read-then-reproject step for the three base operations, and type hints. The blast radius is Spark spatial joins (right/outer now raise) and base operations called with plain WKT and a `crs` (now reprojected). Both are covered by new tests that fail on revert.

## Test plan

32 test files that import the engine (including the new ones), Python 3.11.11:

| duckdb | result |
|---|---|
| 1.4.4 | 597 passed, 71 skipped |
| 1.5.6 | 660 passed, 8 skipped |

Counts are after the refinement round, which adds 4 tests to `test_1852_spark_apportion_crs.py` (593 and 656 passed before it).

## Provenance note: option B

The trailers of `05dabf47` and `4f27b727` say "operator ruling B". Read that as the working choice made during this round to keep `crs` as a declaration on Spark apportion. On 2026-11-10 the reviewer accepted it on technical grounds after seeing the published tip. That is a prospective technical acceptance of the change, not an owner permission backdated to those commits.

## Findings round (9 review threads at `a72bfd09`)

| Thread | Finding | Disposition |
|---|---|---|
| 4521498199 | CHANGELOG: `to_pandas` then `to_crs` cannot work; "every engine" overstates the guard | FIX: the recipe is now `to_geodataframe(crs=<actual CRS>)` then `to_crs` and the Pandas engine (`to_pandas` returns plain WKT text). The guard is scoped to apportion on every engine and nearest on the Pandas, DuckDB and PostGIS engines; `SparkEngine.nearest` keeps v4.0.0's stored-unit behaviour. |
| 4521498205 | Right-join migration: swapping inputs inverts directional predicates | FIX: CHANGELOG, this record and the Spark rejection message say to reverse `within`/`contains` when swapping, and give `spatial_join(polygons, points, how="left", predicate="contains")` for `assign_boundaries`. Spark's ON clause is `ST_<Pred>(left, right)`, so that call is `ST_Contains(polygon, point)`. |
| 4521498210 | `SparkEngine.nearest` lacks `crs` and the projected guard | FIX, minimal capability handling: an explicit `crs` keyword that raises `NotImplementedError` with the working routes, so the call no longer fails as an unexpected keyword. The no-keyword path is unchanged (stored-unit distances, as in v4.0.0). Base and Spark `nearest` docstrings say so. Valid Spark apportion is untouched. |
| 4521498220 | `query` guards for `table`/`df` pairing and zero statements are untested | FIX: `test_table_and_df_must_be_supplied_together` (both halves, nothing created) and `test_parameters_without_a_statement_are_rejected` (empty and comment-only SQL). |
| 4521498227 | `test_1852_conversion_siblings.py` imports GeoPandas unguarded | FIX: `pytest.importorskip("geopandas")` and the DuckDB skip now come before every project import. |
| 4521498232 | `test_1852_extra_crs.py` conversions need GeoPandas | FIX: GeoDataFrame conversions go through `to_gdf`, which skips without GeoPandas; raw-WKB cases still run. |
| 4521498238 | The #1864 test pins a known bug as expected | FIX: `test_raw_composite_wkb_right_join_keeps_right_crs` asserts the correct right-join result (one row, EPSG:3857). It calls `pytest.xfail` only for the exact `unhashable type: 'bytearray'` cause; any other `TypeError` fails (checked with a patched join raising an unrelated `TypeError`). A blanket `xfail(raises=TypeError)` was not used, because it would accept an arbitrary `TypeError`. |
| 4521498245 | Dead `AUDIT` counters | FIX: removed; the snapshot assertions are unchanged. |
| 4521498256 | `test_1852_mixed_crs_inputs.py` needs GeoPandas | FIX: `pytest.importorskip("geopandas")`; every case converts a side with `to_geodataframe`. |

Also from the reviewer's confirmation: the `apportion` docstring and CHANGELOG now treat EPSG:4326 as the configurable default. With `set_default_crs("EPSG:5070")`, Spark apportion without `crs` runs in that CRS (`test_spark_apportion_without_crs_uses_the_configured_default`).

Red on revert (in memory, nothing on disk):
- Spark `nearest` with its `a72bfd09` signature: the `crs` test fails (it raises `TypeError`).
- The old rejection message: the predicate-guidance test fails.
- A hard-coded EPSG:4326 default: the configured-default test fails.
- An unrelated `TypeError` from the join: the #1864 test fails instead of xfailing.

No new BREAKING classification: `crs` on `nearest` is new in 5.0.0 (then named 4.1.0), and the no-keyword Spark path is v4.0.0's behaviour.

32 engine test files after this round, Python 3.11.11:

| duckdb | result |
|---|---|
| 1.4.4 | 604 passed, 71 skipped |
| 1.5.6 | 666 passed, 8 skipped, 1 xfailed (#1864, specific cause) |

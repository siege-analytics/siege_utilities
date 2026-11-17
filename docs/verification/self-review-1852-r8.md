# Self-review: #1852 round 8 and the #1751 re-integration

This record covers two pieces of work:
- the round-8 fix, commit `cfca6c7a`, with its develop merge `6b8dfe6e`;
- the re-integration of this branch onto develop `b18233da`, which carries the spatial_join CRS check from #1751. This is merge `94f8d592` plus the follow-up commit.

The posted reviews and self-reviews on #1852 are the detailed evidence.

## Round 8 (`cfca6c7a`, `6b8dfe6e`)

- **DuckDB plain-frame CRS.**
  - **Defect:** a plain DataFrame of Shapely objects, such as `load_points` output, or an all-null column, kept no CRS on DuckDB. Base nearest, apportion and dissolve then labelled lon/lat degrees with a projected `crs=` instead of reprojecting them.
  - **Fix:** such frames now get `crs`, or the default CRS, as on Pandas and PostGIS.
  - **Unchanged:** a geometry-dtype column keeps its own CRS, and WKB bytes and hex WKB without CRS metadata keep an unknown CRS that `crs=` declares.
  - **Red on the unfixed code:** DuckDB nearest gave 0.014 against 1468.2 on Pandas, and apportion gave 50.0/50.0 against 53.61/46.39.
- **multi_assign with a non-"geometry" active geometry:** the layer's active geometry column keeps its name and is joined on. Red at the time on Pandas and DuckDB.
- **Records:** issuecomment-6851112542 (review), issuecomment-6851114525 (self-review) and issuecomment-6851205618 (merge review).

## Re-integration onto develop `b18233da` (#1751)

- **Merge `94f8d592`.** Conflicts: `CHANGELOG.md` and `siege_utilities/engines/dataframe_engine.py`.
  - CHANGELOG is a union by construction: develop's CRM entries first, then this branch's block unchanged.
  - In `dataframe_engine.py`, the base `multi_assign` keeps this branch's loop: attributes prefixed before the join, the active geometry kept, the generated right index dropped. It adds #1751's handling for points without CRS metadata: when the original points carry no CRS, each later layer receives the previous result as a plain frame.
  - Every other change in the file is #1751's as it landed. The merged file's numstat against `6b8dfe6e` (76/7) equals develop's own change since the base.
- **Follow-up commit:**
  - **Plain layers and the CRS check.** A layer without CRS metadata gets the default CRS from `to_geodataframe`. Before this commit, known-CRS points in a non-default CRS against a plain WKT layer raised a false "left has EPSG:3857, right has EPSG:4326" mismatch on Pandas, DuckDB and PostGIS. `multi_assign` now removes that stamp (`set_crs(None, allow_override=True)`) only when the points have a known CRS that differs from it. Otherwise the layer keeps the stamp, as a direct `spatial_join` would.
  - **Warnings and output compared with v4.0.0** (source at `9c3463b1`):
    - In v4.0.0, DuckDB and PostGIS `spatial_join` labelled a plain layer EPSG:4326 and called `gpd.sjoin`. That was silent for EPSG:4326 points and emitted geopandas' "CRS mismatch between the CRS of left geometries and the CRS of right geometries" notice for points in another CRS.
    - After the fix:
      - default-CRS points with a plain layer join with no warning;
      - non-default points with a plain layer join with that same notice (left CRS known, right CRS unknown).
      - Both are asserted in tests, and the assigned rows and the points' geometry and CRS are unchanged.
    - Pandas `spatial_join` failed on a non-GeoDataFrame layer in v4.0.0, and the call now runs.
    - PostGIS `multi_assign` now returns a GeoDataFrame, where v4.0.0 returned a plain DataFrame. This is disclosed in the CHANGELOG.
    - Two cases follow from the shared rules and are disclosed in the CHANGELOG and docstring:
      - A DuckDB layer of WKB bytes or hex WKB without CRS metadata stays unknown, under the shared contract for WKB without metadata. Default-CRS points against it therefore get geopandas' notice, where v4.0.0 labelled that layer EPSG:4326 and was silent.
      - A layer whose CRS is recorded only in DuckDB attrs counts as unknown for the check, because attrs are not read (disclosed). Its recorded CRS is removed for the join when it differs from the points' known CRS, as for a default stamp.
    - An earlier draft of this commit removed the stamp from every plain layer, which would have added the notice in the default-CRS case. The fresh review caught it before commit, and the default-CRS test guards against it.
  - **#1898.** Without the `to_pandas` step between layers, PostGIS `multi_assign` checks every boundary layer, as Pandas and DuckDB do. `test_postgis_multi_assign_checks_a_later_layer` is red on develop `b18233da`'s engine ("DID NOT RAISE") and green here.
  - **Collision error.** `multi_assign` raises `ValueError("multi_assign: layer columns collide with point columns: [...]")` when it runs again with the same layer name. It is tested for Pandas, DuckDB, PostGIS and Spark. v4.0.0 produced duplicate column labels.
  - **Docs.**
    - The CHANGELOG and `docs/engines/INVARIANTS.md` replace the "PostGIS checks only the first layer" sentence. They now say that a CRS recorded per column in DuckDB pandas attrs is not read by the check.
    - The `multi_assign` CHANGELOG bullet gains the v4.0.0 output-name Migration, the collision clause, and the Pandas-only and PostGIS-return-type notes.
    - DuckDB `buffer` is named for plain Shapely geometry.
    - `self-review-1852-r6.md` now says 5.0.0 where it said 4.1.0.

## Tests (Python 3.11.11, DuckDB 1.4.4 locally)

- **New file `tests/test_1852_multi_assign_crs_layers.py`:** a plain layer counts as unknown against non-default points (Pandas, DuckDB, PostGIS); a plain layer with default-CRS points joins with no warning (Pandas, DuckDB, PostGIS); a known mismatching layer still raises; the #1898 PostGIS later-layer check; the repeated-layer-name collision (Pandas, DuckDB, PostGIS, Spark).
- **On merge `94f8d592`, before the follow-up fix:** 3 failed, 69 passed with #1751's tests. The 3 failures were the plain-layer test on all three engines, with the false mismatch.
- **#1898 test on develop `b18233da`'s engine:** 1 failed (DID NOT RAISE).
- **On the follow-up fix:** the regression set gave **762 passed, 71 skipped, 11 failed**. It covers:
  - the engine-importing test modules and the engine property modules;
  - #1751's `test_spatial_join_crs_check.py` and `test_1619_crs_semantic_compare.py`;
  - every #1852 test, including the new file;
  - the readers, release and changelog tests.

  All 11 failures are local environment failures that also fail before this round:
  - four PyArrow "scheme 'file' already registered" parquet failures, documented in the PR as develop-wide;
  - seven Spark catalog or warehouse failures against an unreachable local `hdfs://localhost:19000`.

Hosted CI on the pushed head is the authority.

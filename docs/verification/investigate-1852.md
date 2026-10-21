---
propagation-deferred: "Repo-resident investigation record for PR #1852 B1/B2; travels with the PR."
---

# Investigation — PR #1852 engine-cluster B1/B2 (#1398)

Source of record: the snug-coral hostile review (FAIL @66a6b280) plus direct code
read of siege_utilities/engines/dataframe_engine.py on fix/engine-cluster.

### Verified Shapes
- PROBED: SparkEngine.spatial_join and assign_boundaries called
  `createOrReplaceTempView` on both inputs BEFORE `_spatial_join_projection`
  computed the suffix map and raised on a collision. Confirmed by red-first run
  (tasks/b2dghkskk.output): `test_collision_rejection_does_not_retain_catalog_views`
  fails `assert 6 == 0` (spatial_join) and `assert 12 == 6` (assign_boundaries) —
  the ValueError IS raised (pytest.raises matched) but two views leak per call.
- PROBED: DuckDBEngine.join returned a merged frame whose geometry columns lost
  their per-column CRS (known EPSG → None). Covered by the #1412 typed-join
  additions (test_known_crs_survives_engine_attribute_join[4326/3857],
  test_unknown_crs_stays_none_through_engine_attribute_join), which exercise the
  new `_merge_geometry_crs` re-attachment.
- ATTESTED: snug-coral independently reproduced both the catalog-view leak and
  the CRS loss at 66a6b280.

### Findings
- F-B1 (high): add `_merge_geometry_crs` to DuckDBEngine.join to re-attach each
  geometry column's CRS after the pandas merge (honouring `on`/`suffixes`).
- F-B2 (high): reject suffix collisions before registering any temp view, and
  drop views on post-registration SQL failure, so rejected joins leave no catalog
  views behind (#1479).

### Verification
- B2 green after fix (tasks/b59x1r4cr.output): 10 passed in 9.14s, including both
  view-retention params.
- B1 local (DuckDB 1.4.4): tests/test_1412_duckdb_query_wkb_crs.py = 18 passed,
  12 skipped (typed CRS path requires DuckDB 1.5 — CI-only).

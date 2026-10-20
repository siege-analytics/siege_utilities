# Self-review — PR #1852 scoped re-review R1/R2 (#1398) (Tier B)

Review-Tier: B (shared engine abstraction: geometry join-key CRS provenance + Spark temp-view failure lifecycle; data-correctness + resource-leak, no credentials/branch/deploy).

## Assumptions
Working as: software engineer (Junior, implementing) and tech lead (Lead, adversarial review).
Domain(s): software engineering; geospatial (CRS provenance through the engine abstraction).
Geospatial cross-cut: yes.
Goal source: snug-coral scoped re-review of PR #1852 (FAIL @46f4b882, R1 + R2) + hub FINAL.
Plan reference: /Users/dheerajchand/.craft-agent/workspaces/my-workspace/plans/pre-mortem-1852.md
Pre-author-inventory: NONE
Investigate-artifact: docs/verification/investigate-1852-r1r2.md
Pre-mortem-artifact: docs/verification/pre-mortem-1852-r1r2.md
Hostile-review-artifact: sessions/261019-snug-coral/data/SU-1852-rereview-46f4b882.md (FAIL @46f4b882; this commit addresses R1+R2; exact-head re-review of the new SHA pending).
Project-contribution: keeps authoritative left-geometry CRS through an engine join key (no silent relabeling) and makes the Spark spatial-join temp-view lifecycle exception-safe at every registration, reinforcing the engine-agnostic DataFrame contract.

## Test plan
- R1 direct (version-independent): call `DuckDBEngine._merge_geometry_crs` with a left EPSG:4326 geometry key and a right EPSG:3857 (then unknown) geometry key, on='geometry'; the coalesced key CRS must be EPSG:4326 in both cases. Observed: EPSG:4326 for right=3857 and right=None.
- R1 committed tests: the reviewer's `test_left_geometry_join_key_is_not_relabelled_from_right[None/3857]` (plus the two supporting DuckDB delta tests) adopted into test_1412 via typed_engine. They require DuckDB 1.5 and skip on local 1.4.4 (observed: 7 skipped); CI (DuckDB 1.5.5) runs them. Reviewer red @46f4b882 documented.
- R2 native-Sedona (SZSH): full tests/test_1479_spark_join_collisions.py. Observed: 14 passed, including test_second_registration_failure_leaves_no_catalog_views and test_sql_failure_leaves_no_catalog_views for both methods. The pytest.raises gate proves the injection fired; after==before proves zero leaked views.
- Regression: test_1497_engine_crs_preservation 33 passed; test_1412 18 passed/19 skipped. No CRS regression.

## Peer review (Junior)
- writing-code: R1 adds a single `on_cols` branch to the existing loop (no new abstraction); R2 replaces two bare drops with a tracked `registered` list inside the try.
- Engine-agnostic DataFrame (CLAUDE.md decision 2): left key CRS is authoritative; non-key right geometry keeps its CRS under the suffix; unknown stays None.
- SU-1 / SU-2: no empty-result-on-failure; no silent CRS relabeling (the R1 defect) remains.
- Gate 1 Syntax: ast.parse on dataframe_engine.py and both test files -> OK.

## Lead review (adversarial)
Phase A coherence: the two re-review findings (join-key relabeling; second-registration leak) map directly to the `on_cols` left-wins branch and the inside-the-try tracked cleanup; no drift.
Phase B verification: did it fix or move the problem? Fixed. R1: the direct check shows the key keeps EPSG:4326 for both right=3857 and unknown; no blanket EPSG:4326 fallback was reintroduced (unknown-source non-key geometry still resolves to None via the unchanged path). R2: the native-Sedona fault-injection at the second registration now leaves zero new views, and the SQL-failure control still passes; the success path is unchanged (views dropped only on the exception path).
Dismissal: the 16 retained success-path views are real but explicitly out of this scope; filed as #1854 (Refs #1815).

Post-mortem applicability: N/A -- forward reviewer-directed fix closing a re-review FAIL, not a revert or regression-fix of shipped code.

## Findings
| ID | Priority | Description | Resolution |
|----|----------|-------------|------------|
| F1 | P3 | R1 committed typed tests require DuckDB 1.5 and skip on local 1.4.4 | verification-environment note: logic verified by the direct helper check; CI (DuckDB 1.5.5) runs the typed tests; exact-head re-review covers it. |

## Quantified claims
- "right=3857/None -> EPSG:4326" -- direct DuckDBEngine._merge_geometry_crs check.
- "14 passed" -- native-Sedona SZSH tests/test_1479_spark_join_collisions.py.
- "33 passed / 18 passed, 19 skipped" -- tests/test_1497_engine_crs_preservation.py and tests/test_1412_duckdb_query_wkb_crs.py locally.

## Evidence-predates-work
Artifact: docs/verification/self-review-1852-r1r2.md, committed in the same never-pushed work commit (self-ancestor). Written post-implementation, pre-push.

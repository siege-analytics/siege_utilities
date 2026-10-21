# Self-review — PR #1852 engine-cluster B1 (CRS-through-join) + B2 (temp-view leak) (Tier B)

Review-Tier: B (behavioral change to a shared engine abstraction: DuckDB join CRS + Spark spatial-join catalog-view lifecycle; resource-leak + data-correctness, no credentials/branch/deploy).

## Assumptions
Working as: software engineer (Junior, implementing) and tech lead (Lead, adversarial review).
Domain(s): software engineering; geospatial (CRS preservation, spatial joins).
Geospatial cross-cut: yes (CRS metadata through the engine abstraction).
Goal source: snug-coral hostile review of PR #1852 (B1 #1412 + B2 #1479 FAIL @66a6b280) + hub FINAL (commit+push #1852; B1 typed CI-only).
Plan reference: /Users/dheerajchand/.craft-agent/workspaces/my-workspace/plans/pre-mortem-1852.md
Pre-author-inventory: NONE
Investigate-artifact: docs/verification/investigate-1852.md
Pre-mortem-artifact: docs/verification/pre-mortem-1852.md
Hostile-review-artifact: snug-coral review (FAIL @66a6b280; this commit addresses B1+B2; independent exact-head re-review of the new SHA pending — NOT a pass of this commit).
Project-contribution: keeps geometry CRS alive through the DuckDB join path and stops SparkEngine spatial joins from leaking session catalog views on rejected joins — both reinforce the engine-agnostic DataFrame contract (same analysis at different scales without silent metadata/resource loss).

## Peer review (Junior — mechanics, shelves, gates)
- writing-code: B2 adds no new abstraction — it reorders existing calls (projection before view registration) and adds an exception-path cleanup. B1 adds one private helper `_merge_geometry_crs`; symbols verified (`_spatial_join_projection` at :1773, `_merge_geometry_crs` call at :1173 / def :1183).
- Engine-agnostic DataFrame (CLAUDE.md decision 2): B1 preserves per-column CRS across the pandas merge; B2 keeps the Spark path's lazy-frame contract (views dropped only on failure, never on the success path).
- Error-handling (SU-1): B2 re-raises after dropping views (no empty-result-on-failure); the collision still raises a typed ValueError with the same message.
- Logging (CLAUDE.md tactical 3): `_ensure_sedona` debug lines unchanged; no new silent side effects.
- Gate 1 Syntax: `ast.parse` on dataframe_engine.py → OK (exit 0).
- Gate 2 Test suite: B2 red-first (leak-order) 2 failed → green 10 passed; B1 test_1412 18 passed + 12 CI-only skips. (see Quantified claims)
- Gate 3 Doc build: N/A (no Sphinx source changed; this verification file is not a doc source).
- Gate 4 Notebook API: N/A (no .ipynb changes; join/spatial_join signatures unchanged).

## Lead review (adversarial)
Phase A coherence: snug-coral's two findings (CRS loss through join; catalog-view leak on rejected spatial join) map directly to B1 (`_merge_geometry_crs`) and B2 (projection-before-view + exception-path drop). The diff implements exactly those, no scope drift.
Phase B verification:
- Did it fix or move the problem? Fixed. B2: red-first proves views leaked (6, then 12) BEFORE the fix; green proves `temp_view_count() == before` after. The collision ValueError is raised at the same point with the same match.
- Lazy-frame safety: views are dropped ONLY in `except ... raise`, so the returned lazy DataFrame (success path) still references its views — confirmed by the 8 non-leak tests (real joins) passing green.
- B1 CRS: typed tests assert known 4326/3857 survive and unknown stays None; these require DuckDB 1.5 (CRS-qualified geometry types) and skip on local 1.4.4 — honestly CI-deferred, not claimed green locally.
- Dismissal: none. B1 typed coverage is CI-only by DuckDB-version necessity, not by choice; logged below as the one unverified-locally item.

Post-mortem applicability: N/A — forward reviewer-directed fix closing a snug-coral FAIL, not a revert or regression-fix of shipped code; no pre-mortem Tiger materialized and no shipped bug passed a prior self-review.

## Test plan
- B2 (#1479) red-first: run `tests/test_1479_spark_join_collisions.py -k test_collision_rejection_does_not_retain_catalog_views` against the leak-order source (real JVM + Sedona) and confirm it FAILS by accumulating catalog views. Observed: `assert 6 == 0` (spatial_join), `assert 12 == 6` (assign_boundaries) — tasks/b2dghkskk.output.
- B2 green: run the full `tests/test_1479_spark_join_collisions.py` after the fix and confirm 10/10 pass, including both view-retention params and the 8 real-join tests (proves the success path still returns a usable lazy frame with its views). Observed: 10 passed in 9.14s — tasks/b59x1r4cr.output.
- B1 (#1412): run `tests/test_1412_duckdb_query_wkb_crs.py`; non-typed query/CRS tests pass locally, typed CRS-join tests skip on DuckDB 1.4.4. Observed: 18 passed, 12 skipped. The typed CRS assertions (known 4326/3857 survive; unknown stays None) must be verified GREEN on CI with DuckDB 1.5 before this head is blessed.
- Static: `ast.parse` on dataframe_engine.py (OK); grep confirms no stale `RED-FIRST TEMP REVERT` markers remain.
- Negative/regression boundary: the collision ValueError type and `match="duplicate output column.*name_left"` are unchanged, so callers relying on the rejection contract are unaffected.

## Findings
| ID | Priority | Description | Resolution |
|----|----------|-------------|------------|
| F1 | P3 | B1 typed CRS-join tests (test_known_crs_survives / test_unknown_crs_stays_none) require DuckDB 1.5 and skip on local 1.4.4 | verification-environment note, not a code defect: locally they skip cleanly (not error); GREEN on CI (DuckDB 1.5) is required before this head is blessed, and the exact-head re-review covers it. |

## Quantified claims
- "B2 red-first 2 failed" — tests/test_1479_spark_join_collisions.py -k test_collision_rejection_does_not_retain_catalog_views against leak-order source (tasks/b2dghkskk.output): `assert 6 == 0` (spatial_join), `assert 12 == 6` (assign_boundaries) → 2 failed.
- "B2 green 10 passed" — full tests/test_1479_spark_join_collisions.py after the restore (tasks/b59x1r4cr.output): 10 passed, 2 warnings in 9.14s, both view-retention params PASSED.
- "B1 18 passed, 12 skipped" — tests/test_1412_duckdb_query_wkb_crs.py on local DuckDB 1.4.4: 18 passed, 12 skipped (typed CRS path, incl. the 2 B1 join additions at :177/:195).

## Evidence-predates-work
Artifact: docs/verification/self-review-1852.md
First-added commit: this artifact is committed in the same (never-pushed) B1/B2 work commit, so its first-added commit IS the work commit (self-ancestor). The review was written post-implementation, pre-push.
Work commit: the B1/B2 implementation commit on fix/engine-cluster.
Verification: `git merge-base --is-ancestor <work-commit> <work-commit>` → 0.

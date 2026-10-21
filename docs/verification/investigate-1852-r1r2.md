---
propagation-deferred: "Repo-resident investigation for PR #1852 scoped re-review R1/R2; travels with the PR."
---

# Investigation — PR #1852 scoped re-review R1/R2 (#1398)

Source of record: the snug-coral scoped re-review
(sessions/261019-snug-coral/data/SU-1852-rereview-46f4b882.md), FAIL @46f4b882,
and its proving tests (test_rereview_delta.py), plus a local direct helper check
and a native-Sedona SZSH run.

### Verified Shapes
- PROBED (R1): `DuckDBEngine._merge_geometry_crs` wrote the left CRS map and then
  the right CRS map into the same coalesced key column, so for a geometry join key
  the right CRS (known or unknown) relabeled or erased the left key CRS
  (last-writer-wins). Confirmed by a direct call on synthetic `.attrs`: at the old
  behavior the key took the right value; after the fix it takes EPSG:4326 (left)
  whether the right is EPSG:3857 or unknown. The reviewer observed EPSG:3857 (and
  None for unknown-right) at 46f4b882 on real DuckDB 1.5.5.
- PROBED (R2): `spatial_join` (:1768-1770) and `assign_boundaries` (:1990-1992)
  registered both temp views outside the try, so a failure at the second
  registration left the first view in the catalog. Confirmed green after the fix:
  native-Sedona SZSH `test_second_registration_failure_leaves_no_catalog_views`
  passes for both methods (injection fires, zero views leak).
- ATTESTED: the reviewer independently reproduced both at 46f4b882 with native
  Sedona (4 failed delta), and confirmed the original B1/B2 repros are closed
  (3 passing at head; engine suite 547 passed/8 skipped; CI 19 green).

### Findings
- F-R1 (high): a geometry join key keeps the LEFT CRS; the right never relabels it.
- F-R2 (high): register views inside the cleanup scope, track them, and drop every
  registered view on any later failure.
- Follow-up (filed #1854, Refs #1815): success-path view retention for
  spatial_join/assign_boundaries (16 retained views; out of this scope).

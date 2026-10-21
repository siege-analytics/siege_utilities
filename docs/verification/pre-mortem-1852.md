---
propagation-deferred: "Repo-resident pre-mortem for PR #1852 B1/B2; travels with the PR."
---

# Pre-mortem — PR #1852 engine-cluster B1 (CRS-through-join) + B2 (temp-view leak) (#1398)

Reviewer-directed (snug-coral) fixes on fix/engine-cluster. B1 = #1412, B2 = #1479.

## What / Context
snug-coral FAIL @66a6b280:
- B1 (#1412): DuckDBEngine.join dropped per-column geometry CRS across the pandas
  merge (known 4326/3857 became None on the result).
- B2 (#1479): SparkEngine spatial_join/assign_boundaries created temp views before
  the suffix-collision check, leaking two catalog views per rejected call.

## Approach
- B1: `_merge_geometry_crs(left, right, result, on, suffixes)` re-attaches each
  surviving geometry column's CRS from the contributing input after the merge.
- B2: compute `_spatial_join_projection(...)` (raises the collision ValueError)
  BEFORE `createOrReplaceTempView`; try/except drops the views on any
  post-registration SQL failure before re-raising.

## Risks
### R1: dropping views breaks the returned lazy frame
Severity: medium — mitigated: drop only in the except path, never finally; success
path returns the lazy frame with views intact (green 10/10).
### R2: CRS re-attachment mislabels a suffixed column
Severity: medium — mitigated: keys off merge `on` + `suffixes`; typed tests assert
4326/3857 survive, unknown stays None (DuckDB 1.5 CI-only).
### R3: earlier collision check changes error ordering
Severity: low — mitigated: ValueError type/message unchanged; the raises-match test
still matches.

## Severity
Overall: medium. Shared engine abstraction; resource-leak + data-correctness; no
credentials/branch/deploy.

## Launch readiness
B2 red-first 2 failed → green 10 passed; B1 18 passed + 12 CI-only skips. No tiger.

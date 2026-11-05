---
ticket_refs:
  - siege-analytics/siege_utilities#1455: comment posted
---

# Self-review: #1455 / PR #1801 (numpy Fisher-Jenks; choropleth fallback colours)

## Assumptions
Domain(s): software engineering, numerical methods, cartographic classification
Goal source: #1455 (numpy Jenks path non-optimal, wrong class count, edge assignment)
Plan reference: https://github.com/siege-analytics/siege_utilities/issues/1455#issuecomment-6650930050
Review being answered: https://github.com/siege-analytics/siege_utilities/issues/1455#issuecomment-6259546974 (exact-head review of 9b96ef2f: F1, F2, process)
Pre-author-inventory: the Investigation section of the plan reference above

## Scope of this round
F1: segment SSE came from `s2 - s1**2/n` over prefix sums translated by the
global minimum. For a tight cluster far from that minimum, the prefix sums
reach about 3e18 and the cluster's SSE cancels. The DP now accumulates
Welford's running mean and M2 over each candidate segment, growing the last
class backward from its end, inside the same O(n^2 k) loops. The one-class
column uses the same forward accumulation. Ties between equal values are
never split, and among equal finite costs the smallest start wins (`<=` in
the backward scan, same as the old ascending scan with `<`).

F2: `classify_series` bins are upper-inclusive (`searchsorted(..., side="left")`)
and `BoundaryNorm` is lower-inclusive. `_upper_inclusive_boundaries` moves each
internal edge to `np.nextafter(edge, +inf)`. Any float64 above the original
edge is at least the nudged edge, so a value's colour class equals its bin
exactly. The outer edges are unchanged.

## Peer review (the Junior's checklist)

### writing-code
- Severe flake8 on the three changed files -> no output.
- `scripts/check_exception_contracts.py` -> 207 flagged, 0 unlisted, 0 stale.
- `scripts/check_no_stub_docstrings.py` -> OK; `scripts/check_test_file_hygiene.py` -> PASS.

### writing-tests
- Red at f384d3d0 (new tests, old code): pytest -> 6 failed, 32 passed. The
  failures are 3 large-offset optimality cases, the reviewer's case (SSE 48.67
  vs 2.0), and 2 edge-colour cases (natural_breaks, equal_interval). The
  quantiles colour case has no value on an edge and serves as a control. Two
  large-offset cases happened to be optimal before the fix and act as oracles.
- After the fix: pytest -> 137 passed (test_1455 + test_classification +
  test_choropleth), including the 300-sample brute-force oracle.
- test_exception_contract_sites + smoke + runtime_guard + sql_safety -> 146 passed.

### writing-claims
- The counts are pytest summary lines from this work cycle.

## Lead review
Numerics: Welford's update gives M2 >= 0 at every step, and its error scales
with the segment's own spread, not with the distance to the global minimum.
Cartography: there is exactly one BoundaryNorm site in the library (grep).
`notebooks/spatial/03_choropleth_maps.ipynb` calls `create_choropleth`; its
contract is unchanged, so no notebook edit is needed. Maps whose values sit on
a break may change colour in the no-mapclassify path, which is the intended fix.

## Rework ledger
- 9b96ef2f/f384d3d0: prefix-sum cancellation and the BoundaryNorm edge mismatch. Both F1 and F2 are fixed in this round.
- The 4.1.0 note is restored to CHANGELOG.md and covers both.

## Findings
F1 and F2 fixed. No new findings.

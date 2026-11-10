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
- Pre-flight (2026-11-10). Develop sync: `7f6f0e6e` merges develop `71f02b0b` for a positional CHANGELOG conflict (the #1444 and #1455 Fixed entries). Both are kept, a diff against develop deletes 0 develop lines, and no merged develop behaviour disagrees with this PR. Classification follows the operator rule (2026-11-06): a change that alters v4.0.0 caller behaviour is BREAKING. On the v4.0.0 tag, the numpy path of `classify_series` uses `np.searchsorted(breaks[1:-1], clean, side="right")` and masks only `np.isnan`. The mapclassify path already used `side="left"`. So numpy-backend bins for values on an internal break move down one class, infinities move to bin `-1`, and natural breaks for clustered or outlier data change. The entry moves from 4.1.0 Fixed to BREAKING with a **Migration:** line scoped to the numpy backend. No code changed.

## Findings
F1 and F2 fixed. No new findings.

## Ticket-fitness exemption

Governing ticket: #1455. The #1398 epic is context only.

### #1455
Reason: #1455 predates the canonical ticket template. Its body uses Problem / Evidence / Failure scenario / Done when / Assumptions / Falsifier / Related instead of Context / Goal / Acceptance, and it links no /think design note.
Evidence: https://github.com/siege-analytics/siege_utilities/issues/1455 states the merged-outlier and on-break defects under "## Problem", the probe under "## Evidence (v4.0.0, CONFIRMED by probe)" (`geo/classification.py`), and the done-when criteria under "## Done when". The reviewer verdict is https://github.com/siege-analytics/siege_utilities/issues/1455#issuecomment-6259546974.
Falsification: revert the implementation; `tests/test_1455_classify_numpy_jenks.py::test_numpy_jenks_keeps_singleton_top_class` goes red because the singleton maximum merges into the previous class, and `::test_numpy_jenks_reviewer_case_finds_sse_two` goes red because the partition SSE is wrong. Revert only the F1/F2 round (back to `f384d3d0`); the reviewer case goes red at SSE 48.67 instead of 2.0, and `::test_choropleth_fallback_colours_edge_values_with_their_class` goes red because an edge value takes the next class's colour.
Observed revert results (2026-11-05). Command, with `REV` set to the revert target:
`git checkout REV -- siege_utilities/geo/classification.py siege_utilities/geo/choropleth.py && (cd tests && python -m pytest -o addopts="" -p no:cacheprovider --rootdir=.. -q test_1455_classify_numpy_jenks.py::test_numpy_jenks_keeps_singleton_top_class test_1455_classify_numpy_jenks.py::test_numpy_jenks_reviewer_case_finds_sse_two test_1455_classify_numpy_jenks.py::test_choropleth_fallback_colours_edge_values_with_their_class); git checkout HEAD -- <same files>`
- `REV=dc7d3f76` (develop): 2 failed, 3 passed. The singleton and reviewer-case tests fail. The 3 edge-colour cases pass, because develop's classifier is lower-inclusive like `BoundaryNorm`; the mismatch arrived with this PR's upper-inclusive bins.
- `REV=f384d3d0` (pre-F1/F2 head): 3 failed, 2 passed. The reviewer case and both edge-valued colour cases fail; the singleton test and the no-edge quantiles control pass.
- Current-head green: after the files were restored, `(cd tests && python -m pytest -o addopts="" -p no:cacheprovider --rootdir=.. -q test_1455_classify_numpy_jenks.py)` gave 38 passed. The worktree was clean.

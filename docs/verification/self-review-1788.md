# Self-review — #1788 test-scope CI fix (#1672) (Tier B)

Review-Tier: B (test-only change to CI lane selection; marks one collector integration, no library or notebook change).

## Assumptions
Working as: software engineer (Junior, implementing) and tech lead (Lead, adversarial review).
Domain(s): software engineering (test scoping / CI lanes); geospatial (the geo notebook group).
Geospatial cross-cut: yes (the geo notebook group runs real TIGER).
Goal source: fair-bobcat exact-head review of PR #1788 (TEST-SCOPE FAIL) + hub item-4 queue.
Plan reference: /Users/dheerajchand/.craft-agent/workspaces/my-workspace/plans/pre-mortem-1672.md
Pre-author-inventory: NONE
Investigate-artifact: docs/verification/investigate-1788.md
Pre-mortem-artifact: docs/verification/pre-mortem-1788.md
Hostile-review-artifact: sessions/261019-fair-bobcat/data/notebook-pr-reviews.md (#1788 TEST-SCOPE FAIL @a1752350; this commit addresses it; exact-head re-review pending).
Project-contribution: keeps the gazetteer regression's geo-group coverage out of the offline ordinary lane (where it ran real TIGER) while preserving it in the network lane, so the default CI lane stays offline-safe.

## Test plan
- Red-first: `pytest tests/test_1672_gazetteer_notebook_truth.py --collect-only` in the default lane selects all 6 test_geo_notebook_group params (incl. 01_boundaries real TIGER). Observed: 6 selected.
- Green default lane: after the integration mark, the default lane selects 0 geo-group params. Observed: 0.
- Green integration lane: `-m integration --collect-only` still selects the 6 params. Observed: 6.
- Content coverage intact: the gazetteer semantic tests still run and pass in the default lane. Observed: 5 passed, 6 deselected.

## Peer review (Junior)
- writing-tests: the geo-group genuinely needs network (unmocked notebooks); `integration` is the correct lane; the offline mocked geo-group run is provided by #1783 (noted in the comment, no duplication).
- Scope: only test_geo_notebook_group gains the mark; the gazetteer semantic tests are untouched.
- Gate 1 Syntax: the edited test file parses (pytest collected and ran it).

## Lead review (adversarial)
Phase A coherence: the fair-bobcat finding (unmocked geo-group in the ordinary lane runs real TIGER -> BoundaryFetchError) maps directly to the integration mark; no drift.
Phase B verification: did it fix or move the problem? Fixed: red-first proves the 6 params are selected in the default lane; green proves 0 in the default lane and 6 under integration. No assertion was loosened and no coverage was dropped (network coverage moves to the integration lane; offline coverage is #1783's mocked group).

Post-mortem applicability: N/A — forward test-scope fix closing a reviewer FAIL, not a revert or regression-fix of shipped code.

## Findings
| ID | Priority | Description | Resolution |
|----|----------|-------------|------------|
| (none) | - | - | - |

## Quantified claims
- "6 selected / 0 selected / 6 under integration" — `pytest --collect-only` in the default and `-m integration` lanes.
- "5 passed, 6 deselected" — tests/test_1672_gazetteer_notebook_truth.py in the default lane.

## Evidence-predates-work
Artifact: docs/verification/self-review-1788.md, committed in the same never-pushed work commit (self-ancestor). Written post-implementation, pre-push.

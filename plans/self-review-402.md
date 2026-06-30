---
propagation-deferred: will post to ticket with PR
---

# Self-review: Multi-signal risk stacking (#402)

Self-Review: risk stacking engine with signal types, tier classification, and intervention mapping
Self-Review-Source: plans/self-review-402.md
Design-Note-Source: https://github.com/siege-analytics/claude-configs-public/issues/402
Investigate-artifact: TRIVIAL (see ## Trivial-investigation declaration below)
Pre-mortem-artifact: TRIVIAL (see ## Trivial-investigation declaration below)
Hostile-review-artifact: WAIVED — new module, no existing callers affected

## Hostile-review-waiver
Reason: New module addition — no existing code modified
Scope: siege_utilities/analytics/risk.py (new), tests/test_analytics_risk.py (new), __init__.py (lazy import)
Compensating-control: 23 tests pass; module is isolated

## Trivial-investigation declaration
Category: new module addition
Cannot produce error: no existing behavior modified
Reason: Adding new risk module to analytics package
Evidence: git diff --stat shows 2 new files + 5 lines added to __init__.py
Falsification: If existing analytics imports broke, investigation would be required

## Assumptions
Goal source: https://github.com/siege-analytics/claude-configs-public/issues/402
Investigate-artifact: TRIVIAL (see ## Trivial-investigation declaration above)
Pre-mortem-artifact: TRIVIAL (see ## Trivial-investigation declaration above)
Pre-author-inventory: NONE
Trivial-against-state: new module addition, no existing state contact
Working as: software engineer
Roles: Junior (implemented risk engine and tests), Senior (verified SU-1 compliance, enum enforcement, tier boundaries)

## Peer review

Shelves checked: writing-code:1, writing-tests:1

### Gate evidence
- 23 tests pass: `python -m pytest tests/test_analytics_risk.py -v -o 'addopts=' — 23 passed`
- SU-1: ValueError for invalid weights, missing signals, out-of-range scores, bad enum types
- SignalType enforced as enum per acceptance criteria

## Lead review

**[Senior]** Clean implementation. Signal types as enum prevents free-text drift.
RiskTier ordering is validated in RiskTierConfig. Intervention mapping is optional.
Shares the weighted-composition pattern with scoring.py but is independent — no
coupling between modules.

## Quantified claims

- 1 new module: siege_utilities/analytics/risk.py
- 1 new test file: tests/test_analytics_risk.py
- 23 tests: 1 enum, 4 signal, 6 config, 12 analyzer
- Every raise path has a negative test

## Findings

No findings.

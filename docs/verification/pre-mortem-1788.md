---
propagation-deferred: "Repo-resident pre-mortem for PR #1788 (#1672); travels with the PR."
---

# Pre-mortem: #1788 natural-language geometry notebook honesty (#1672)

## What / Context
The natural-language geometry notebook needed distinct illustrative fixtures and fixture-specific directional labels, and the regression file wraps the geo notebook group in six integration-marked parameters that need network access.

## Approach
Give each place name its own illustrative fixture, reject unknown names, label directional results against the queried fixture, add offline regression tests, mark the network-dependent group `integration`, and place the release note in `[4.1.0]`. Record a real local run of the six parameters.

## Risks
### R1: collected is mistaken for executed
Severity: medium. No workflow job runs the six integration-marked parameters. The description and self-review state that plainly and cite the local run instead.
### R2: the local run depends on the network
Severity: low. The run fetches real TIGER boundaries; a failure would be reported as it occurred, not inferred away.
### R3: fixture geometry
Severity: low. The Lake Geneva fixture is illustrative and the south-shore assertions are checked against it.

## Severity
Overall: low. Notebook prose and fixtures, tests and documentation; no library code change.

## Launch readiness
The five offline cases pass (5 passed, 6 deselected) and all six integration parameters executed and passed locally on the synced tree. No tiger.

---
propagation-deferred: "Repo-resident pre-mortem for PR #1784 (#1664) content fix; travels with the PR."
---

# Pre-mortem — #1784 NOTEBOOKS.md content fix (#1664)

## What / Context
NOTEBOOKS.md claimed spatial/06 runs an import smoke cell; spatial/06 has 0 code
cells (nbformat), so the claim is false and conflicts with #1786's markdown-only docs.

## Approach
Correct the credential-table row to "markdown-only, no code cells execute" and
split the "Why" paragraph so engines/02 keeps its import smoke cell and spatial/06
is markdown-only; add a regression test.

## Risks
### R1: drift from #1786
Severity: medium — both now say spatial/06 is markdown-only; land #1784 first.
### R2: test over-reach onto engines/02
Severity: low — the test filters to spatial/06 lines only.

## Severity
Overall: low. Docs + one test; no code behavior change.

## Launch readiness
Red-first new test fails on the false doc; green full test_1664 9 passed. No tiger.

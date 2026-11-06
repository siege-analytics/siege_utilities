---
propagation-deferred: "Repo-resident pre-mortem for PR #1784 (#1664); travels with the PR."
---

# Pre-mortem: #1784 Spark notebook and notebook guide honesty (#1664)

## What / Context
The Spark notebook promised cluster-attached execution it could not deliver, and the notebook guide claimed `spatial/06` runs an import smoke cell although it has 0 code cells. A neighboring PR (#1786) edits the same guide lines for the GeoDjango notebook.

## Approach
Label the Sedona SQL schematic, document the views and runtime prerequisites, correct the guide so `spatial/06` is markdown-only and `engines/02` keeps its import smoke cell, add a regression test, and place the release note in `[4.1.0]`.

## Risks
### R1: drift from #1786
Severity: medium. Both PRs edit the notebook guide's `spatial/06` lines. Both now say markdown-only, so a later merge of either must keep both correct statements.
### R2: test over-reach onto engines/02
Severity: low. The test filters to `spatial/06` lines only.
### R3: release note in the wrong section
Severity: low. The note is under `[4.1.0]` and a search of `[Unreleased]` for `#1664` returns nothing.

## Severity
Overall: low. Documentation, one notebook prose edit and one test; no library behavior change.

## Launch readiness
Red-first test fails on the false guide; the full `tests/test_1664_spark_notebook_truth.py` file passes (9 passed on the synced tree). No tiger.

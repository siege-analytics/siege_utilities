---
propagation-deferred: "Repo-resident pre-mortem for PR #1782 (#1662); travels with the PR."
---

# Pre-mortem: #1782 GA end-to-end notebook honesty (#1662)

## What / Context
The GA end-to-end notebook presented a fixed April fixture as a live or weekly client digest, and inbound references in other notebooks and the notebook guide repeated that claim. The neighboring PR #1787 edits the same first cell of the reports/01 notebook.

## Approach
Label the notebook an offline fixed-date demo, document a separate credentialed recipe with tests, reword every inbound reference, drop `analytics/02` from the credential row, run the credential-free notebook in the pure notebook lane, and place the release note in `[4.1.0]`.

## Risks
### R1: overlap with #1787 in the reports/01 first cell
Severity: medium. Both PRs edit that cell. The Next bullet wording agrees with #1787. This PR still calls the PDF branded while #1787 states the frame is unbranded; that difference is an open wording decision and will conflict in the same cell until it is made.
### R2: test over-reach
Severity: low. The cross-notebook test checks only `analytics/02` lines and the specific credential row.
### R3: punctuation regressions
Severity: low. The edited cells and these documents use ASCII punctuation only.

## Severity
Overall: low to medium because of R1. Notebook prose, one rewritten demo notebook, tests and documentation; no library behavior change.

## Launch readiness
The 26 cases of `tests/test_1662_ga_notebook_truth.py` pass on the synced tree. R1 is open and is reported to the maintainers. No tiger.

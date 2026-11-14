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
Severity: low after reconciliation. Both PRs edit the first markdown cell and the step 3 cell. They now carry byte-identical text there (unbranded PDF frame, the #1789 link, and the offline fixed-date `analytics/02` bullet), so a later merge of either does not conflict in those cells.
### R2: test over-reach
Severity: low. The cross-notebook test checks only `analytics/02` lines and the specific credential row.
### R3: punctuation regressions
Severity: low. The edited cells and these documents use ASCII punctuation only.

## Severity
Overall: low. Notebook prose, one rewritten demo notebook, tests and documentation; no library behavior change.

## Launch readiness
The 26 cases of `tests/test_1662_ga_notebook_truth.py` pass on the synced tree, and 34 pass together with the reports/01 hygiene selection after the reconciliation. No tiger.

---
propagation-deferred: "Repo-resident pre-mortem for PR #1787 (#1673); travels with the PR."
---

# Pre-mortem: #1787 reports/01 units and wording honesty (#1673)

## What / Context
The reports/01 notebook labeled cumulative sign-up counts as percentage shares and overstated its PDF branding. The neighboring PR #1782 edits the same first markdown cell of that notebook for the `analytics/02` bullet.

## Approach
Use counts throughout, derive growth once, state the unbranded PDF frame, add regression tests including a rendered-table check guarded by `pytest.importorskip("reportlab")`, place the release note in `[4.1.0]`, and use the offline fixed-date wording for the `analytics/02` bullet.

## Risks
### R1: overlap with #1782 in the first cell
Severity: low after reconciliation. Both PRs edit that cell and the step 3 cell. They now carry byte-identical text in both (unbranded PDF frame, the #1789 link, the offline fixed-date `analytics/02` bullet, ASCII punctuation), so a later merge of either does not conflict there.
### R2: a false skip hides a renderer regression
Severity: low. The guard skips only when the reportlab package is absent and fails when the package is present but its Table is unavailable.
### R3: punctuation regressions
Severity: low. The edited cell and these documents use ASCII punctuation only.

## Severity
Overall: low. Notebook prose and numbers, tests and documentation; no library behavior change.

## Launch readiness
The three test functions pass with ReportLab present, and the notebook hygiene selection for reports/01 passes (11 passed together on the synced tree). No tiger.

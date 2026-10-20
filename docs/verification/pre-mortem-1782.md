---
propagation-deferred: "Repo-resident pre-mortem for PR #1782 (#1662) content fix; travels with the PR."
---

# Pre-mortem — #1782 inbound GA-digest honesty (#1662)

## What / Context
Inbound refs (analytics/01 Next+Related, reports/01 Next) called analytics/02 a
full/weekly/live GA digest after it became an offline fixed-date demo;
NOTEBOOKS.md listed it under GOOGLE_APPLICATION_CREDENTIALS.

## Approach
Reword the inbound bullets to offline framing (ASCII punctuation), drop
analytics/02 from the credential row, add a cross-notebook regression test.

## Risks
### R1: prose-scanner violations in edited cells
Severity: low — touched cells' em-dashes normalized to ASCII.
### R2: test over-reach
Severity: low — only analytics/02 lines and the specific credential row are checked.

## Severity
Overall: low. Docs + notebook prose + one test; analytics/02 itself untouched.

## Launch readiness
Red-first new test fails on current refs; green test_1662 26 passed, both notebooks
valid. No tiger.

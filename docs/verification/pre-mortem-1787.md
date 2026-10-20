---
propagation-deferred: "Repo-resident pre-mortem for PR #1787 (#1673) CI fix; travels with the PR."
---

# Pre-mortem — #1787 test-portability CI fix (#1673)

## What / Context
`test_pdf_table_renders_counts` subclasses report_generator.Table, which is None
without ReportLab, raising TypeError in the minimal (geo without GDAL) lane.

## Approach
`if rgmod.Table is None: pytest.skip(<actionable msg>)` before the subclass.

## Risks
### R1: skip hides a regression where the dep is absent
Severity: low — the test needs ReportLab to render a PDF table; it still runs and
asserts fully where ReportLab is present.

## Severity
Overall: low. Test-only; no library/notebook behavior change.

## Launch readiness
Red-first TypeError reproduced; green 3 passed with ReportLab and clean skip when
Table is None. No tiger.

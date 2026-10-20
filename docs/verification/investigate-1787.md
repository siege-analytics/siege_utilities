---
propagation-deferred: "Repo-resident investigation for PR #1787 (#1673) CI fix; travels with the PR."
---

# Investigation — #1787 test-portability CI fix (#1673)

Source of record: the fair-bobcat exact-head review (#1787 TEST/CI FAIL) and CI
job 117826636836 (geo without GDAL), plus local reproduction.

### Verified Shapes
- PROBED: in tests/test_1673_reports01_units_notebook_truth.py,
  test_pdf_table_renders_counts defines `class Spy(rgmod.Table)` where
  `rgmod` is siege_utilities.reporting.report_generator. report_generator.Table
  is None when ReportLab is absent, so the class statement raises
  `TypeError: NoneType takes no arguments`. Reproduced locally by forcing
  report_generator.Table = None at the class-def site.
- ATTESTED: the fair-bobcat review observed the same on the hosted
  `geo without GDAL` lane at head 5a3c4b01 (test file line 109).

### Findings
- F-1787 (high): skip the test when report_generator.Table is None so the
  minimal lane skips rather than errors; keep full coverage where ReportLab is
  installed.

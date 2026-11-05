---
propagation-deferred: "Repo-resident investigation for PR #1787 (#1673); travels with the PR."
---

# Investigation: #1787 reports/01 units and wording honesty (#1673)

Sources of record: the exact-head reviews recorded on PR #1787 and ticket #1673, the regression tests in `tests/test_1673_reports01_units_notebook_truth.py`, and a local read of the neighboring PR's notebook.

### Verified Shapes
- PROBED: on `develop` the `notebooks/reports/01_charts_and_pdf.ipynb` chart title and PDF caption described `[42, 45, 51]` as percentage shares, while the table used 51 sign-ups against a baseline count of 37 with no population denominator. The notebook now treats the series as month-end cumulative Q1 volunteer sign-up counts and derives +37.8% from `(51 - 37) / 37 * 100` once, for the chart title, table delta, summary and chart caption. The table keeps the +14 count change.
- PROBED: the notebook now says only the chart image uses ElectInfo's primary color and the PDF frame has no ElectInfo header, footer or page numbering. The library behavior behind that (`generate_pdf_report` ignoring `self.branding_config`) is tracked separately in #1789.
- PROBED: the test module has three test functions: counts in chart, table and report; growth matching the counts on every report surface; and the rendered PDF table cells. The rendered-table test uses `pytest.importorskip("reportlab")` plus an assertion that `report_generator.Table` is not None, so a present-but-unavailable Table fails instead of skipping.
- PROBED: the Next bullet in the notebook's first cell called `analytics/02_ga_end_to_end.ipynb` "Masai's weekly GA digest in the same PDF style". The neighboring PR #1782 shows `analytics/02` is an offline fixed-date demo. That bullet now reads "an offline fixed-date GA digest demo in the same PDF style", the wording used by #1782.
- ATTESTED: the independent reviews flagged the release-note placement, a contradictory description, a self-review that covered only the guard, and the weekly-GA wording.

### Findings
- F-1787a (medium): the `#1673` release note belongs in the `[4.1.0]` section of `CHANGELOG.md`.
- F-1787b (medium): the Next bullet must not call `analytics/02` weekly; corrected to the offline fixed-date wording.
- F-1787c (medium): the description and self-review must cover the whole PR, not only the ReportLab guard.
- F-1787d (open, neighboring PR): #1782 still calls the reports/01 PDF fully branded. That is a decision for #1782 and is not edited from this PR.

---
propagation-deferred: "Repo-resident investigation for PR #1782 (#1662); travels with the PR."
---

# Investigation: #1782 GA end-to-end notebook honesty (#1662)

Sources of record: the exact-head reviews recorded on PR #1782 and ticket #1662, the regression tests in `tests/test_1662_ga_notebook_truth.py`, and a local read of the neighboring PR's notebook.

### Verified Shapes
- PROBED: on `develop` the `notebooks/analytics/02_ga_end_to_end.ipynb` credential branch never queried GA, both branches selected the April fixture, and the PDF presented a fixed 3000-session comparison as a weekly client result. The notebook now identifies an OFFLINE fixed-date demo (2026-04-17 through 2026-04-23) in its narrative, chart, PDF, console output and Slack example, and documents a separate credentialed recipe that raises on API errors, empty or malformed data and a zero prior total.
- PROBED: inbound references called `analytics/02` a live, weekly or full-pipeline digest: `notebooks/analytics/01_connectors.ipynb` (Next and Related bullets), `notebooks/reports/01_charts_and_pdf.ipynb` (Next bullet), and `docs/NOTEBOOKS.md` listed `analytics/02` under the GOOGLE_APPLICATION_CREDENTIALS row. They now use offline fixed-date wording and the credential row omits `analytics/02`. `docs/source/notebooks.rst`, `notebooks/reports/02_slides_pptx_and_google.ipynb` and `tests/test_notebooks.py` also changed in the PR.
- PROBED: nine files differ from `develop`: `CHANGELOG.md`, `docs/NOTEBOOKS.md`, `docs/source/notebooks.rst`, `notebooks/analytics/01_connectors.ipynb`, `notebooks/analytics/02_ga_end_to_end.ipynb`, `notebooks/reports/01_charts_and_pdf.ipynb`, `notebooks/reports/02_slides_pptx_and_google.ipynb`, `tests/test_1662_ga_notebook_truth.py` and `tests/test_notebooks.py`.
- PROBED: earlier heads of this PR described the reports/01 PDF as a single branded PDF in the client's colors, with a client header, footer and page numbering. The neighboring PR #1787 shows the PDF frame has no such header, footer or page numbering (library behavior tracked in #1789). Both PRs edit the same cells, so they were reconciled: the first markdown cell and the step 3 cell of `notebooks/reports/01_charts_and_pdf.ipynb` now carry the unbranded-frame wording, the #1789 link and the offline fixed-date `analytics/02` bullet, byte-identical in both PRs.
- ATTESTED: the independent reviews flagged the release-note placement, a stale description, punctuation, a narrow self-review and the branded-PDF wording.

### Findings
- F-1782a (high): inbound references to `analytics/02` must say offline fixed-date; guarded by `test_inbound_references_describe_analytics_02_as_offline`.
- F-1782b (medium): the `#1662` release note belongs in the `[4.1.0]` section of `CHANGELOG.md`.
- F-1782c (medium): the description and self-review must cover all nine changed files.
- F-1782d (closed in this PR): the reports/01 sentences calling the PDF branded were replaced with the unbranded-frame wording from #1787, as a reconciliation with that PR, authorized by the maintainers. Only markdown cells changed.

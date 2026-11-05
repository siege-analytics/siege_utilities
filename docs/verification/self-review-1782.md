# Self-review: #1782 GA end-to-end notebook honesty (#1662)

Review-Tier: B (notebook narrative and fixtures, documentation and regression tests; no library code change).

Scope: the PR as a whole at its current head. The diff against `develop` is `CHANGELOG.md`, `docs/NOTEBOOKS.md`, `docs/source/notebooks.rst`, `notebooks/analytics/01_connectors.ipynb`, `notebooks/analytics/02_ga_end_to_end.ipynb`, `notebooks/reports/01_charts_and_pdf.ipynb`, `notebooks/reports/02_slides_pptx_and_google.ipynb`, `tests/test_1662_ga_notebook_truth.py` and `tests/test_notebooks.py`, plus these three verification documents.

## Assumptions
Working as: software engineer (implementing) and tech lead (adversarial review).
Domain(s): software engineering (notebook truthfulness, report provenance).
Geospatial cross-cut: no.
Goal source: ticket #1662 and the exact-head reviews recorded on PR #1782.
Pre-author-inventory: NONE
Investigate-artifact: docs/verification/investigate-1782.md
Pre-mortem-artifact: docs/verification/pre-mortem-1782.md
Hostile-review-artifact: the pinned review on PR #1782 and the ticket #1662 review comment for the prior head (CHANGES REQUESTED on release-note placement, a stale description, punctuation, a narrow self-review and the branded-PDF wording); the current head addresses the process points and awaits a fresh exact-head review.
Project-contribution: keeps the GA end-to-end notebook and every reference to it truthful about being an offline fixed-date demo.

## Test plan
- Red-first: the offline-framing test fails against the pre-fix inbound references, which matched weekly, live, ships or full-GA-pipeline wording.
- Green on the current tree: `python -m pytest test_1662_ga_notebook_truth.py` run from the `tests` directory -> 26 passed, 2 warnings in 32.98s; together with the reports/01 selection of `test_notebook_hygiene.py` after the reconciliation edit -> 34 passed (Python 3.11, repository pyproject as config). The warnings are google-api-core Python version notices. The tests execute the notebook's demo cells and the documented credentialed recipe against mocked GA responses; no real GA property is contacted.
- Hosted CI at the pushed head is recorded in the PR description once it finishes. Develop CI has known failures from the DuckDB 2.0 break (about 30) that are not attributable to this PR.

## Peer review
- writing-claims: the inbound references no longer call `analytics/02` live or weekly. The reports/01 sentences that called the PDF branded were replaced with the unbranded-frame wording from #1787 (first markdown cell and step 3 cell, markdown only, with the #1789 link), as a reconciliation with that PR authorized by the maintainers. The two PRs now carry byte-identical text in those cells.
- writing-prose: the verification documents use ASCII punctuation only.
- Scope: nine changed files listed above plus these documents; no library code changed.
- Gate evidence: pytest -> 26 passed as above.

## Ticket-fitness exemption

Governing ticket: #1662 (the #1398 epic is context only and is not a governing ticket).

- **Reason:** #1662 predates the canonical ticket template (Context / Goal / Acceptance, a design link and Assumptions). It uses the earlier hostile-review Problem / Done-when / Falsifier narrative, so the ticket-fitness check reports a structure gap. The exemption is for ticket structure only.
- **Evidence:** the Problem (the GA end-to-end notebook presenting a fixed April fixture as a live or weekly client digest, repeated by inbound references), the evidence and the Done-when live in the ticket, https://github.com/siege-analytics/siege_utilities/issues/1662, and in the PR description. The reviewer verdict is https://github.com/siege-analytics/siege_utilities/issues/1662#issuecomment-6298384540.
- **Falsification:** revert the implementation (the notebook, guide and inbound-reference edits of this PR); `tests/test_1662_ga_notebook_truth.py::test_inbound_references_describe_analytics_02_as_offline` goes red because an inbound line again calls `analytics/02` weekly, live or a full pipeline. The latest commit of this PR is process-only; that existing regression test guards the accepted fix.

## Lead review (adversarial)
Phase A coherence: the reviewer findings (release-note placement, stale description, punctuation, narrow self-review) map to the `[4.1.0]` entry, the refreshed description, ASCII documents and this whole-PR artifact; no drift.
Phase B verification: did it fix or move the problem? Fixed for the offline framing and the credential row. The branded-PDF sentences in reports/01 were reconciled with #1787 by replacing them with its already-reviewed wording; no code cell or library code changed.

Post-mortem applicability: N/A. This is a forward content fix, not a revert or regression-fix of shipped code.

## Findings
| ID | Priority | Description | Resolution |
|----|----------|-------------|------------|
| F-1 | medium | reports/01 first cell and step 3 cell called the PDF branded | Closed: replaced with the unbranded-frame wording from #1787 |

## Quantified claims
- "26 passed" is the full `test_1662_ga_notebook_truth.py` run on the synced tree.
- "nine files" is the count from `git diff origin/develop --stat`.

## Restoration note
The three `docs/verification` documents for this PR were removed by commit 01e6f3b8 and are restored from its parent, 814242243abe1e9dbb8853b8fcc6eecd55ff2820. They were not restored byte for byte: they were rewritten to cover the whole PR at the current head, and internal session names, absolute local paths, client names and non-ASCII punctuation were removed so that nothing internal is published.

## Evidence-predates-work
This artifact is committed in the PR branch at `docs/verification/self-review-1782.md`. The test results above were produced in the same work cycle that restored it, after the implementation commits.

# Self-review: #1784 Spark notebook and notebook guide honesty (#1664)

Review-Tier: B (documentation, notebook prose and one regression test; corrects false capability claims; no library code change).

Scope: the PR as a whole at its current head. The diff against `develop` is `CHANGELOG.md`, `docs/NOTEBOOKS.md`, `notebooks/engines/02_distributed_spark.ipynb` and `tests/test_1664_spark_notebook_truth.py`, plus these three verification documents.

## Assumptions
Working as: software engineer (implementing) and tech lead (adversarial review).
Domain(s): software engineering (documentation truthfulness, notebook governance).
Geospatial cross-cut: yes (the Sedona SQL and the GeoDjango `spatial/06` notebook are described, not executed).
Goal source: ticket #1664 and the exact-head reviews recorded on PR #1784.
Pre-author-inventory: NONE
Investigate-artifact: docs/verification/investigate-1784.md
Pre-mortem-artifact: docs/verification/pre-mortem-1784.md
Hostile-review-artifact: the pinned review on PR #1784 and the ticket #1664 review comment for the prior head (CHANGES REQUESTED on release-note placement, a stale description and punctuation); the current head addresses those points and awaits a fresh exact-head review.
Project-contribution: keeps `docs/NOTEBOOKS.md` and the Spark notebook truthful about what executes, so readers are not told a schematic notebook runs a cluster or that a markdown-only notebook runs an import cell.

## Test plan
- Red-first: `test_notebooks_doc_marks_spatial_06_markdown_only` fails against the false guide text; `test_sedona_sql_is_labeled_schematic` fails against the baseline notebook.
- Truth basis: `nbformat.read` on `notebooks/spatial/06_geodjango.ipynb` reports 0 code cells.
- Green on the current tree: `python -m pytest test_1664_spark_notebook_truth.py` run from the `tests` directory -> 9 passed in 3.39s (Python 3.11, repository pyproject as config).
- Hosted CI at the pushed head is recorded in the PR description once it finishes. Develop CI has known failures from the DuckDB 2.0 break (about 30) that are not attributable to this PR.

## Peer review
- writing-claims: the guide and the notebook now match the notebooks' real behavior; the changelog sentence says `spatial/06` is markdown-only.
- writing-prose: the verification documents use ASCII punctuation only.
- Scope: documentation, notebook prose and the test file; no library code and no executable notebook cell changed beyond the import smoke cell that already existed.
- Gate evidence: pytest -> 9 passed; the test file parses because pytest collected and ran it.

## Ticket-fitness exemption

Governing ticket: #1664 (the #1398 epic is context only and is not a governing ticket).

- **Reason:** #1664 predates the canonical ticket template (Context / Goal / Acceptance, a design link and Assumptions). It uses the earlier hostile-review Problem / Done-when / Falsifier narrative, so the ticket-fitness check reports a structure gap. The exemption is for ticket structure only.
- **Evidence:** the Problem (the Spark notebook promising cluster-attached execution it cannot deliver, and the notebook guide claiming `spatial/06` runs an import smoke cell), the evidence and the Done-when live in the ticket, https://github.com/siege-analytics/siege_utilities/issues/1664, and in the PR description. The reviewer verdict is https://github.com/siege-analytics/siege_utilities/issues/1664#issuecomment-6298384585.
- **Falsification:** revert the implementation (the notebook guide and notebook edits of this PR); `tests/test_1664_spark_notebook_truth.py::test_notebooks_doc_marks_spatial_06_markdown_only` goes red because the guide again says an import smoke cell executes for `spatial/06`. The latest commit of this PR is process-only; that existing regression test guards the accepted fix.

## Lead review (adversarial)
Phase A coherence: the reviewer findings (false `spatial/06` import-smoke claim, release-note placement, stale description) map to the corrected guide lines, the `[4.1.0]` entry and the refreshed description; no drift.
Phase B verification: did it fix or move the problem? Fixed: the red-first tests prove the false claims fail, and the green run proves the corrected text passes while the legitimate `engines/02` import-smoke claim stays intact. The overlap with #1786 is documented as risk R1 in the pre-mortem.

Post-mortem applicability: N/A. This is a forward content fix, not a revert or regression-fix of shipped code.

## Findings
| ID | Priority | Description | Resolution |
|----|----------|-------------|------------|
| (none open) | - | - | - |

## Quantified claims
- "0 code cells" is from `nbformat.read` on `notebooks/spatial/06_geodjango.ipynb`.
- "9 passed" is the full `test_1664_spark_notebook_truth.py` run on the synced tree.

## Restoration note
The three `docs/verification` documents for this PR were removed by commit 927be7fa and are restored from its parent, 251649079409a9003ef74802efd78209ed4384e1. They were not restored byte for byte: they were rewritten to cover the whole PR at the current head, and internal session names, absolute local paths, client names and non-ASCII punctuation were removed so that nothing internal is published.

## Evidence-predates-work
This artifact is committed in the PR branch at `docs/verification/self-review-1784.md`. The test results above were produced in the same work cycle that restored it, after the implementation commits.

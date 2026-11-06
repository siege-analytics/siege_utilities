# Self-review: #1786 GeoDjango notebook honesty (#1671)

Review-Tier: B (documentation, notebook prose and tests; corrects false capability claims; no library code change).

Scope: the PR as a whole at its current head. The diff against `develop` is `CHANGELOG.md`, `docs/NOTEBOOKS.md`, `notebooks/spatial/06_geodjango.ipynb`, `tests/test_1671_geodjango_notebook_truth.py` and `tests/test_notebooks.py`, plus these three verification documents.

## Assumptions
Working as: software engineer (implementing) and tech lead (adversarial review).
Domain(s): software engineering (documentation truthfulness, notebook governance).
Geospatial cross-cut: yes (the GeoDjango notebook is described, not executed).
Goal source: ticket #1671 and the exact-head reviews recorded on PR #1786.
Pre-author-inventory: NONE
Investigate-artifact: docs/verification/investigate-1786.md
Pre-mortem-artifact: docs/verification/pre-mortem-1786.md
Hostile-review-artifact: the pinned review on PR #1786 and the ticket #1671 review comment for the prior head (CHANGES REQUESTED on punctuation, release-note placement, a stale description and a narrow self-review); the current head addresses those points and awaits a fresh exact-head review.
Project-contribution: keeps the GeoDjango notebook, the notebook guide and the notebook test module truthful about a markdown-only schematic, and keeps the guide consistent with the open neighboring PR #1784.

## Test plan
- Red-first: the documentation-contract tests fail against the baseline notebook, which promised a complete copy-pasteable command.
- Truth basis: `nbformat.read` on `notebooks/spatial/06_geodjango.ipynb` reports 0 code cells; `importlib.util.find_spec("spatial_05_unified")` returns None.
- Green on the current tree: `python -m pytest test_1671_geodjango_notebook_truth.py` run from the `tests` directory -> 4 passed in 1.88s; together with the geodjango selection of `test_notebook_hygiene.py` -> 12 passed (Python 3.11, repository pyproject as config).
- Hosted CI at the pushed head is recorded in the PR description once it finishes. Develop CI has known failures from the DuckDB 2.0 break (about 30) that are not attributable to this PR.

## Peer review
- writing-claims: the notebook and guide describe a schematic, markdown-only notebook; no copy-paste promise remains. The guide states that PR #1784 is a separate open PR editing the same lines; this PR does not claim it landed.
- writing-prose: the notebook and these documents use ASCII punctuation only.
- Scope: five changed files plus these documents; no library code changed.
- Gate evidence: pytest -> 4 passed and 12 passed as above.

## Ticket-fitness exemption

Governing ticket: #1671 (the #1398 epic is context only and is not a governing ticket).

- **Reason:** #1671 predates the canonical ticket template (Context / Goal / Acceptance, a design link and Assumptions). It uses the earlier hostile-review Problem / Done-when / Falsifier narrative, so the ticket-fitness check reports a structure gap. The exemption is for ticket structure only.
- **Evidence:** the Problem (the GeoDjango notebook advertising a complete copy-pasteable command whose `spatial_05_unified` loader import cannot resolve), the evidence and the Done-when live in the ticket, https://github.com/siege-analytics/siege_utilities/issues/1671, and in the PR description. The reviewer verdict is https://github.com/siege-analytics/siege_utilities/issues/1671#issuecomment-6298384544.
- **Falsification:** revert the implementation (the notebook, guide and test-module edits of this PR); `tests/test_1671_geodjango_notebook_truth.py::test_unresolved_loader_is_not_advertised_as_a_runnable_recipe` goes red because the notebook again advertises a runnable recipe for an unresolved loader. Observed revert run: with the false recipe claim restored in the loader cell of `notebooks/spatial/06_geodjango.ipynb` (the cell retitled and described as a "complete, copy-pasteable management command" around the unresolved `spatial_05_unified` import), `python -m pytest test_1671_geodjango_notebook_truth.py -q`, run from the tests directory, gave 1 failed, 3 passed in 1.63s; the failed test was `test_unresolved_loader_is_not_advertised_as_a_runnable_recipe` with `AssertionError: An unresolved loader import cannot be advertised as a complete/copy-pasteable recipe`. After `git checkout -- notebooks/spatial/06_geodjango.ipynb` the same command gave 4 passed in 1.38s on the pushed head, and the worktree was clean. The latest commit of this PR is process-only.

## Lead review (adversarial)
Phase A coherence: the reviewer findings (punctuation, release-note placement, stale description, narrow self-review) map to the ASCII rewrite, the `[4.1.0]` entry, the refreshed description and this whole-PR artifact; no drift.
Phase B verification: did it fix or move the problem? Fixed: the contract tests prove the false recipe claim fails and the corrected text passes. The overlap with #1784 was reduced by making the shared guide paragraph textually identical in both PRs, which leaves only an adjacent-changelog resolution.

Post-mortem applicability: N/A. This is a forward content fix, not a revert or regression-fix of shipped code.

## Findings
| ID | Priority | Description | Resolution |
|----|----------|-------------|------------|
| (none open) | - | - | - |

## Quantified claims
- "0 code cells" is from `nbformat.read` on the notebook.
- "4 passed" is the full `test_1671_geodjango_notebook_truth.py` run; "12 passed" adds the geodjango hygiene selection.

## Restoration note
The three `docs/verification` documents for this PR were removed by commit 157d19be and are restored from its parent, 84df62a114df3c6d1c77853482b5d5e7a8e64f09. They were not restored byte for byte: they were rewritten to cover the whole PR at the current head, and internal session names, absolute local paths, client names and non-ASCII punctuation were removed so that nothing internal is published.

## Evidence-predates-work
This artifact is committed in the PR branch at `docs/verification/self-review-1786.md`. The test results above were produced in the same work cycle that restored it, after the implementation commits.

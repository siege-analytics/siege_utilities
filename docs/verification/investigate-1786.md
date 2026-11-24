---
propagation-deferred: "Repo-resident investigation for PR #1786 (#1671); travels with the PR."
---

# Investigation: #1786 GeoDjango notebook honesty (#1671)

Sources of record: the exact-head reviews recorded on PR #1786 and ticket #1671, a local nbformat code-cell count, and the regression tests in `tests/test_1671_geodjango_notebook_truth.py`.

### Verified Shapes
- PROBED: `notebooks/spatial/06_geodjango.ipynb` advertised a complete, copy-pasteable management command whose `spatial_05_unified` loader import cannot resolve. `nbformat.read` reports 0 code cells, so the notebook is markdown-only. The notebook now labels the examples as schematics, documents the missing ingestion loader and Django setup, and states that notebook validation does not exercise the loader, ORM or PostGIS.
- PROBED: an earlier head of this PR carried three em dashes (U+2014) in the notebook's markdown cell `t` (the "Why it matters" sentence and the two "Next" bullets). They were rewritten to ASCII punctuation with no change in meaning.
- PROBED: `docs/NOTEBOOKS.md` and `tests/test_notebooks.py` also changed in this PR: the guide marks `spatial/06` as markdown-only and describes `SCHEMATIC_MARKDOWN_ONLY`, and the test module tracks markdown-only schematics separately from execution groups and requires code cells in every execution notebook.
- PROBED: the neighboring PR #1784 has since landed on develop. It edited the same two `docs/NOTEBOOKS.md` locations for `spatial/06` with wording textually identical to this PR's, so the merge with develop `fbb280c7` is clean and the texts agree.
- ATTESTED: the independent reviews flagged the punctuation, the release-note placement, the stale description and a self-review that understated the diff.

### Findings
- F-1786a (medium): the notebook and guide must stay markdown-only and schematic; guarded by `tests/test_1671_geodjango_notebook_truth.py`.
- F-1786b (medium): the `#1671` release note belongs in `### Documentation` under `[Unreleased]` in `CHANGELOG.md` (the old `[4.1.0]` bucket was released as `[5.0.0]`).
- F-1786c (medium): the verification documents and the PR description must cover all changed files (eight in the original PR, plus `.github/workflows/ci.yml` and `notebooks/README.md` in the replacement) and the true status of #1784.

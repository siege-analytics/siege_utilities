---
propagation-deferred: "Repo-resident investigation for PR #1784 (#1664); travels with the PR."
---

# Investigation: #1784 Spark notebook and notebook guide honesty (#1664)

Sources of record: the exact-head reviews recorded on PR #1784 and ticket #1664, a local nbformat code-cell count, and the red-first regression tests in `tests/test_1664_spark_notebook_truth.py`.

### Verified Shapes
- PROBED: `notebooks/engines/02_distributed_spark.ipynb` section 4 promised cluster-attached execution while its Sedona SQL queried `donors` and `precincts` without defining either view, and its only executable cell checks imports. The notebook now labels the SQL schematic, documents the two view schemas and registration calls, and states the Spark, Sedona, geometry and CRS prerequisites.
- PROBED: at an earlier head of this PR, `docs/NOTEBOOKS.md` said the `spatial/06` row was "Schematic GeoDjango call shapes; only the import smoke cell executes". `nbformat.read` on `notebooks/spatial/06_geodjango.ipynb` reports 0 code cells, so nothing executes for `spatial/06`. The guide now says `spatial/06` is markdown-only while `engines/02` executes only an import smoke cell.
- PROBED: the changelog sentence for #1664 was corrected at this head: it no longer claims `spatial/06` executes an import smoke cell. It now says the GeoDjango notebook is markdown-only with no code cells.
- ATTESTED: the independent reviews flagged the false `spatial/06` claim and the release-note placement.

### Findings
- F-1784a (high): correct both `docs/NOTEBOOKS.md` spots so `spatial/06` reads markdown-only while `engines/02` keeps its import smoke cell; guarded by a regression test that filters to `spatial/06` lines.
- F-1784b (medium): the `#1664` release note belongs in the `[4.1.0]` section of `CHANGELOG.md`, not `[Unreleased]`.
- F-1784c (medium): the PR description must list `docs/NOTEBOOKS.md` among the changed files and cite current evidence.

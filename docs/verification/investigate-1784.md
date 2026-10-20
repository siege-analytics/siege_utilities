---
propagation-deferred: "Repo-resident investigation for PR #1784 (#1664) content fix; travels with the PR."
---

# Investigation — #1784 NOTEBOOKS.md content fix (#1664)

Source of record: the fair-bobcat exact-head review (#1784 CONTENT FAIL, 1 blocker)
plus a local nbformat code-cell count and a red-first regression test.

### Verified Shapes
- PROBED: docs/NOTEBOOKS.md credential-table row for Local PostGIS / spatial/06
  said "Schematic GeoDjango call shapes; only the import smoke cell executes", and
  the "Why engines/02 and spatial/06 don't execute" paragraph said "Only an import
  smoke cell executes in each notebook". nbformat.read on
  notebooks/spatial/06_geodjango.ipynb reports 0 code cells, so no import smoke
  cell executes for spatial/06.
- ATTESTED: the fair-bobcat review flagged this as a new false claim that
  conflicts with #1786's corrected markdown-only docs for the same notebook.

### Findings
- F-1784 (high): correct both NOTEBOOKS.md spots so spatial/06 reads markdown-only
  (no code cells execute) while engines/02 keeps its import smoke cell; add a
  regression test. Land before #1786 to preserve the shared markdown-only truth.

---
propagation-deferred: "Repo-resident investigation for PR #1786 (#1671) prose fix; travels with the PR."
---

# Investigation — #1786 prose-scanner fix (#1671)

Source of record: the fair-bobcat exact-head review (#1786 CONTENT PASS with a
mechanical prose-scanner hold at spatial/06_geodjango.ipynb line 22) plus local grep.

### Verified Shapes
- PROBED: notebooks/spatial/06_geodjango.ipynb markdown cell 't' contained three
  em-dashes (U+2014): the "Why it matters" sentence and the two "Next" bullets.
  grep -E for U+2014/U+2013 returned 3 matches (lines 14, 22, 23 of the JSON).
- ATTESTED: the fair-bobcat review and the linked ticket's independent exact-head
  review flagged the line 22 em-dash as a required prose-scanner violation.

### Findings
- F-1786 (medium): rewrite the em-dashes to ASCII punctuation; keep the
  markdown-only (0 code cells) schematic content so the notebook agrees with
  #1784's NOTEBOOKS.md description.

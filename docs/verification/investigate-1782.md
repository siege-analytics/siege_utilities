---
propagation-deferred: "Repo-resident investigation for PR #1782 (#1662) content fix; travels with the PR."
---

# Investigation — #1782 inbound GA-digest honesty (#1662)

Source of record: the fair-bobcat exact-head review (#1782 CONTENT FAIL, 2
blockers) plus a local red-first cross-notebook test.

### Verified Shapes
- PROBED: notebooks/analytics/01_connectors.ipynb cell 'title' Next bullet said
  "full GA pipeline landing in a branded PDF digest" and cell 'related' said
  analytics/02 "wraps the GA connector into a branded PDF digest Masai ships to a
  client weekly"; notebooks/reports/01_charts_and_pdf.ipynb cell 't' said
  analytics/02 is "Masai's weekly GA digest". analytics/02's own intro now reads
  "OFFLINE fixed-date demo" and "credentials have no effect", so the inbound
  claims are false. A cross-notebook test matching weekly/live/ships/full-ga-pipeline
  on analytics/02 lines fails (red) on the current refs.
- PROBED: docs/NOTEBOOKS.md GOOGLE_APPLICATION_CREDENTIALS row listed analytics/02
  alongside analytics/01, implying credential gating that does not apply.
- ATTESTED: the fair-bobcat review flagged both as #1782 content blockers.

### Findings
- F-1782a (high): reword the inbound refs to offline fixed-date framing (ASCII
  punctuation).
- F-1782b (high): drop analytics/02 from the GOOGLE_APPLICATION_CREDENTIALS row.

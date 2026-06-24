---
ticket: "#1032, #1033"
scope: "notebooks/analytics/04_crm_pipeline.ipynb, notebooks/analytics/05_crm_sales_reports.ipynb"
---

# Self-Review — #1032/#1033 CRM notebooks

## Junior Assessment

**#1032 — 04_crm_pipeline.ipynb:** Full pipeline demo: pull contacts
from Salesforce + HubSpot, map to canonical CRM models, run cross-CRM
dedup, extract addresses for geocoding, build pipeline chart, write-back
canonical IDs.

**#1033 — 05_crm_sales_reports.ipynb:** Sales reporting demo: pull
opportunities and accounts from Salesforce, pipeline adapter → bar chart,
timeseries adapter → line chart, tabular adapter → top accounts table,
ReportGenerator → PDF output.

## Lead Assessment

**SU-3 compliance:** All credentials from `os.environ.get()`. No
hardcoded paths. Output directory from environment variable with
fallback.

**Notebook coverage invariant:** Both notebooks exercise the new
functions: `pipeline_adapter`, `timeseries_adapter`, `geographic_adapter`,
`tabular_adapter`, `crm_dedup_pipeline`, `to_crm_contacts`,
`to_crm_accounts`, `to_crm_opportunities`. Coverage of all public
functions added in #1029/#1031.

**Structure:** Follows the existing notebook pattern (03_social_media):
markdown sections, sequential cells, imports at point of use, cleanup
at end.

## Trivial-investigation declaration

Notebooks demonstrate library capabilities. No new functions introduced.

## Trivial pre-mortem declaration

New files only. No existing notebooks modified.

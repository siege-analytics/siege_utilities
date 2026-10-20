---
propagation-deferred: "Repo-resident investigation for PR #1818 round-3 (R3-R8); travels with the PR."
---

# Investigation — PR #1818 round-3 R3-R8 (#1414)

Source of record: the round-3 FINAL (sessions/261019-light-eddy/data/su-1818-r3-FINAL.md,
azure-hawk-confirmed), azure-hawk's pre-review, and live verification on a
disposable PostgreSQL 17 + PostGIS 3.6 cluster (port 55450) plus red-first on
4c355a60.

### Verified Shapes
- PROBED: at 023bd818 the PostGIS execute_spatial_query committed owned reads via a
  single `_opened_connection` flag (no autocommit distinction), had no crs
  validation, no INERROR handling, and no transaction-control / mixed-batch
  handling; the DuckDB execute_spatial_query refused caller-owned writes
  ("Mutating queries require a connection without an active transaction"). Confirmed
  by red-first on 4c355a60: invalid crs did not raise, a mixed-control batch was not
  rejected, and `BEGIN` did not leave the connection INTRANS.
- PROBED (green at head): tests/test_1818_spatial_review_postgis.py +
  tests/test_1818_spatial_review_regressions.py = 113 passed on the live PG17
  cluster, including the 8 new R4a/R5/R6/R7 tests and the recast R2/R3 tests.
- ATTESTED: the round-3 FINAL's input->output examples for R3-R8 and azure-hawk's
  canonical probes define the contract; azure-hawk runs the scoped final review.

### Findings
- R3/R4a/R4b/R5/R6/R8 implemented in the two execute_spatial_query methods; R7 test
  added; R2 classifier test recast as Design-A characterization.
- Follow-ups: close()=#1853, R2-classifier-precision=#1855 (filed). The DuckDB
  embedded-COMMIT batch atomicity gap is resolved by R6 (no separate ticket).

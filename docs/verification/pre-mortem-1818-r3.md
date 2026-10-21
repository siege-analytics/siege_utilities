---
propagation-deferred: "Repo-resident pre-mortem for PR #1818 round-3 (R3-R8); travels with the PR."
---

# Pre-mortem — PR #1818 round-3 R3-R8 (#1414)

## What / Context
Round-3 FINAL (azure-hawk-confirmed) transaction-ownership contract for the
PostGIS/DuckDB spatial query path, additive on 023bd818.

## Approach
R3 DuckDB caller-txn join; R4a crs fail-fast; R4b ownership by transaction status;
R5 INERROR caller-owned + standalone recovery; R6 standalone transaction-control
bypass + mixed-batch reject; R8 owned rollback on any exception; R7 PG16
MERGE-without-RETURNING test; R2 characterization recast.

## Risks
### R1: ownership mis-detection
Severity: high -- mitigated: driven by live psycopg2 transaction status + autocommit;
caller-owned never finalizes; verified on live PG17 + red-first on 4c355a60.
### R2: owned transaction left open on a decode error
Severity: high -- mitigated: R8 rolls back on any exception and re-raises.
### R3: mixed-control batch non-atomic
Severity: medium -- mitigated: rejected before execution, both engines.

## Severity
Overall: high (transaction/durability contract). Verified on a disposable
PG17+PostGIS cluster; no credentials/branch/deploy.

## Launch readiness
113 passed on live PG17; red-first on 4c355a60 for R4a/R6. No tiger.

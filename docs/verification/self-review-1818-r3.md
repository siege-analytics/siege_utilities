# Self-review — PR #1818 round-3 R3-R8 (#1414) (Tier C)

Review-Tier: C (transaction-ownership and data-durability contract across the PostGIS and DuckDB spatial query paths: commit/rollback/savepoint routing, failed-transaction handling, transaction-control statements).

## Assumptions
Working as: software engineer (Junior, implementing) and tech lead (Lead, adversarial review).
Domain(s): software engineering; geospatial (PostGIS/DuckDB spatial SQL); databases (transaction ownership).
Geospatial cross-cut: yes.
Goal source: #1818 round-3 FINAL (sessions/261019-light-eddy/data/su-1818-r3-FINAL.md, azure-hawk-confirmed) + hub order.
Plan reference: /Users/dheerajchand/.craft-agent/workspaces/my-workspace/plans/pre-mortem-1818.md
Pre-author-inventory: NONE
Investigate-artifact: docs/verification/investigate-1818-r3.md
Pre-mortem-artifact: docs/verification/pre-mortem-1818-r3.md
Hostile-review-artifact: sessions/261019-azure-hawk/data/pre-review-su-1818-4c355a60.md (azure-hawk pre-review of the base; the round-3 FINAL is settled with azure-hawk; the exact-head scoped final review of the new SHA is pending).
Project-contribution: makes the spatial SQL connectors honour the caller's transaction ownership exactly -- joining a caller transaction, establishing real ownership only when idle, never finalizing a caller transaction, rejecting non-atomic mixed-control batches, and never leaving an owned transaction open on failure.

## Test plan
- R4a: an invalid crs= raises SpatialQueryError before executing, with zero side effects (observer count 0). Live PG17: test_r4a_invalid_crs_raises_before_executing passes; red-first on 4c355a60 (did not raise).
- R4b: IDLE+autocommit=False finalizes with connection.commit() and no SQL BEGIN (test_r2_1_owned_success..., test_b1_authority_lookup... with mock autocommit=False); INTRANS is caller-owned (savepoint, R1 commit routing).
- R5: INERROR is caller-owned -- a non-recovery statement raises before executing and status stays INERROR; a standalone ROLLBACK TO SAVEPOINT returns -1 and the caller's pending write survives its COMMIT. Live PG17: test_r5_inerror_is_caller_owned_until_standalone_recovery passes.
- R6: standalone COMMIT/ROLLBACK/BEGIN run directly and return -1 (COMMIT commits the caller pending, ROLLBACK discards, BEGIN leaves INTRANS); PREPARE..AS takes the normal path; a mixed-control batch is rejected before execution with zero side effects (both engines). Live PG17 passes; red-first on 4c355a60 for mixed and BEGIN.
- R8: an owned transaction rolls back on any exception and re-raises SpatialQueryError (test_r2_1_owned_volatile_select_rolls_back_on_decode_error; test_b4_unexpected_decoder_failure_rolls_back).
- R3 (DuckDB): the two-txn-id refusal is removed; a caller-owned write joins the caller transaction and the caller ROLLBACK undoes it (test_b4_caller_transaction_joins_owned_write); RETURNING yields rows; upload keeps RuntimeError.
- R7: MERGE without RETURNING writes durable state observed on a separate connection (test_r7_merge_without_returning_writes_durable_state, PG15+); MERGE...RETURNING still skips server_version_num < 170000; the PG16 lane is CI postgis:16-3.4.
- Full file runs on the disposable PG17+PostGIS cluster: tests/test_1818_spatial_review_postgis.py + tests/test_1818_spatial_review_regressions.py = 113 passed.

## Peer review (Junior)
- writing-code: four small pure-Python helpers (_sql_statement_list, _transaction_control_kind, _is_standalone_recovery, _validate_output_crs) unit-verified in isolation before wiring; the two execute_spatial_query methods branch on the real transaction status, not a flag.
- SU-1 (errors are not data): every failure raises SpatialQueryError with __cause__; the R8 broad `except Exception` re-raises (never returns an empty/valid-shaped result).
- SU-2 (CRS/geometry): crs is validated up front; the decode path is unchanged.
- Logging: each path logs; transaction-control execution logs a distinct line.
- Gate 1 Syntax: ast.parse on spatial_transformations.py and both test files -> OK.

## Lead review (adversarial)
Phase A coherence: every FINAL item (R3-R8 + R2 recast) maps to a specific code change and a test; no drift beyond the FINAL.
Phase B verification: did it fix or move the problem? Fixed. Ownership is determined by the actual psycopg2 status and autocommit before execution; caller-owned (INTRANS/INERROR) never finalizes and only uses savepoints; IDLE+autocommit uses SQL BEGIN/COMMIT (connection.commit() would not end an explicit transaction under autocommit); IDLE+non-autocommit uses connection.commit(); R8 rolls back an actually-owned transaction on any exception. R6 rejects mixed-control batches before execution and runs standalone control directly. R3 removes the DuckDB refusal so owned writes join the caller. Verified green on a live PG17+PostGIS cluster and red-first on 4c355a60.
Dismissal: the R8 handlers are broad (`except Exception`) but re-raise SpatialQueryError and are justified by the durability contract (an owned transaction must never be left open on any failure); this matches the engine-cluster reviewer's accepted "re-raising broad catch" pattern.

Post-mortem applicability: N/A -- forward reviewer-directed implementation of a settled round-3 FINAL, not a revert or regression-fix of shipped code.

## Findings
| ID | Priority | Description | Resolution |
|----|----------|-------------|------------|
| F1 | P3 | R2 write-token classifier precision (EXPLAIN-without-ANALYZE as read-only) | filed #1855 (Refs #1414); Design A makes over-commit of a read-only non-SELECT caller-owned statement develop-parity, not a blocker. |
| F2 | P3 | close() connection-ownership follow-up | filed #1853 (cited in the PR body). |

## Quantified claims
- "113 passed" -- tests/test_1818_spatial_review_postgis.py + tests/test_1818_spatial_review_regressions.py on the disposable PG17+PostGIS cluster (port 55450).
- "8 new tests pass" -- the R4a/R5/R6/R7 live-cluster tests.
- "red-first on 4c355a60" -- R4a invalid-crs, R6 mixed-batch, and R6 BEGIN all failed on the pre-round-3 source.

## Evidence-predates-work
Artifact: docs/verification/self-review-1818-r3.md, committed in the same additive work commit on 023bd818 (self-ancestor). Written post-implementation, pre-push.

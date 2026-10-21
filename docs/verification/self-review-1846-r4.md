# Self-review — #1846 B2 round 4 (D1-D5 credential redaction, Tier C)

Review-Tier: C (credentials/auth: diagnostic redaction of secret values).

## Assumptions
Working as: software engineer (Junior, implementing) and tech lead (Lead, adversarial review).
Domain(s): software engineering
Geospatial cross-cut: no
Goal source: hub FINAL round-4 re-review FAIL at a9f772d8 (D1 through D5) plus the hub ruling accepting the D3 reversal of two blessed auth-path tests.
Plan reference: docs/verification/pre-mortem-1846-r4.md
Pre-author-inventory: NONE
Investigate-artifact: docs/verification/investigate-1846-r4.md
Pre-mortem-artifact: docs/verification/pre-mortem-1846-r4.md
Hostile-review-artifact: sessions/261019-light-eddy/data/su-1846-b2-r4-FINAL.md (hub FINAL ruling at a9f772d8; exact-head re-review of the new SHA pending, NOT a review of this commit).
Project-contribution: closes the remaining credential-leak surface in CRM connector diagnostics so a configured secret cannot reach an UpsertError, a non-2xx error, a log, or an auth diagnostic, including via a short credential, a long untruncated echo, or a hostile header mapping's exception text.

## Trivial-against-state declaration
Trivial-against-state: local-only
Category: local-only
Cannot produce error: the change adds redaction to diagnostic-text construction only; it reads no shared cluster, config, topology, plan, or version state and alters no request payload, so it cannot act on an unverified external shape.
Evidence: git diff --stat shows only core/_http.py, connectors/_protocol.py, the four connector files, scripts/exception_contracts_allowlist.json, and five tests/ files plus this verification doc; no request-building or schema/config code.
Falsification: a base/head PreparedRequest-corpus diff shows any request body, header, or URL changed, which would prove redaction leaked into requests.

## Peer review (Junior — mechanics, shelves, gates)
- writing-code: no speculative abstraction; the new helpers (_safe_upstream_detail, the fail-closed sentinel) live on the existing _SecretRedactionMixin; symbols verified against each connector.
- writing-claims: counts below are grounded in same-turn test output.
- Credential-safety domain checklist: no hardcoded secrets added (all test values synthetic); redaction is value-based on the connector's own configured secrets; the short-credential and fail-closed paths emit trusted constants only.
- Error-handling (SU-1): sinks still raise typed ConnectorError subclasses; no empty-result-on-failure introduced.
- Gate 1 Syntax and behavior: pytest imports and exercises every changed module; the full connector and redaction set -> pytest -> 2166 passed, 1 skipped, 0 failed, which fails at collection on any syntax error (exit 0).
- Gate 2 Reviewer fixture: tests/test_1846_b2_r4_remaining.py -> pytest -> 96 passed; red-first on a9f772d8 (D4 alone) -> 76 failed / 20 passed.
- Gate 3 Static guard: scripts/check_exception_contracts.py --root . -> handlers flagged 207; unlisted 0; stale allow-list 0 (the new broad handler is the single allowlist addition).
- Gate 4 Doc build: N/A (no Sphinx source changed).
- Gate 5 Notebook API: N/A (no .ipynb changes).

## Lead review (adversarial)
Phase A coherence: the hub's five directives map one-to-one to the diff. D1 value-redacts every UpsertError field; D2 value-redacts every non-2xx branch, the logged URL path, and _extract_error; D3 suppresses short-credential auth detail; D4 replaces values before truncation; D5 fails closed on secret collection. No scope drift.
Phase B verification:
- Did it fix or move the problem? Fixed: the r4 fixture is red-first 76/20 after D4 alone and 96 passed after D1-D5; the header-ValueError case proves the exception chain no longer carries the secret.
- Requests untouched (item 4): only diagnostic-text construction changed; the full connector request/token/upsert suite passes unchanged, so outgoing PreparedRequests are unaffected.
- D3 reversal risk: suppression is scoped to the five auth/token sinks via _safe_upstream_detail; general request and batch paths keep self._redact, proved secret-free-preserving by test_short_credential_preserves_general_path_detail. The reversal of the two blessed assertions is hub-approved and disclosed in the PR body and commit message.
- D4: _extract_error returns self._redact(raw)[:200] and redact_secrets replaces whole values first, so the long-credential case cannot keep a prefix through truncation.
- D5: the broad except returns a sentinel built after the except (no from-None chaining), registered in the allowlist; the guard stays at unlisted 0.
Post-mortem applicability: N/A — forward security fix closing a reviewer FAIL, not a revert or regression-fix of shipped code.

## Findings
| ID | Priority | Description | Resolution |
|----|----------|-------------|------------|
| F1 | P3 | Short-credential auth suppression also drops a secret-free upstream body on the auth path (fail-closed over-redaction) | accepted: cannot distinguish a short secret from innocent text on the auth path; general paths preserve the body; hub-ruled accepted |

## Quantified claims
- "96 passed; red-first 76 failed / 20 passed after D4" — pytest tests/test_1846_b2_r4_remaining.py -> 96 passed; the same file on the D4-only tree -> 76 failed / 20 passed.
- "2166 passed, 1 skipped, 0 failed" — pytest across the 33-file connector and redaction set -> 2166 passed, 1 skipped.
- "unlisted 0; stale allow-list 0" — scripts/check_exception_contracts.py --root . -> handlers flagged 207; unlisted 0; stale allow-list 0.

## Rework ledger
| Rework trigger | Root skip | Check cost | Rework cost | Ratio |
|---|---|---|---|---|
| D3 suppression regressed a pre-existing short-token general-path test | applied suppression on general paths before scoping it to auth paths | one test run | scope the helper to auth paths | low |
| session restore reset the discipline gates mid-task | external restore, not a skip | gate re-establishment | rewrite gates for the current ticket/worktree | low |

## Evidence-predates-work
Artifact: docs/verification/self-review-1846-r4.md
First-added commit: committed in the r4 work commit on fix/crm-cluster-1 (self-ancestor); written pre-push, post-implementation.
Work commit: the r4 implementation commit on fix/crm-cluster-1.
Verification: git merge-base --is-ancestor <work-commit> <work-commit> -> 0 (a commit is its own ancestor; the artifact does not post-date the pushed head).

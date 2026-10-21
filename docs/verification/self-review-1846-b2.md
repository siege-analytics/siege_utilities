# Self-review — PR #1846 B2 credential-redaction (Tier C)

Review-Tier: C (credentials/auth: diagnostic redaction of secret values).

## Assumptions
Working as: software engineer (Junior, implementing) and tech lead (Lead, adversarial review).
Domain(s): software engineering
Geospatial cross-cut: no
Goal source: lively-thunder r2 hostile review of PR #1846 (B2 FAIL) + hub FINAL 02:16/02:49 (R-a/R-b + 4 additions)
Plan reference: /Users/dheerajchand/.craft-agent/workspaces/my-workspace/plans/pre-mortem-1846.md
Pre-author-inventory: NONE
Investigate-artifact: docs/verification/investigate-1846-b2.md
Pre-mortem-artifact: docs/verification/pre-mortem-1846-b2.md
Hostile-review-artifact: sessions/261019-lively-thunder/data/review-1846-r2-behavioral.md (FAIL @1537093f; this commit addresses B2; exact-head re-review of the new SHA pending — NOT a review of this commit)
Project-contribution: closes the credential-leak surface in CRM connector diagnostics so secret values (and their encoded echoes) cannot reach logs/telemetry/exception text — a reusable redaction primitive for every connector.

## Trivial-against-state declaration
Trivial-against-state: local-only
Category: local-only
Cannot produce error: the change adds redaction to diagnostic-text construction only; it reads no shared cluster/config/topology/plan/version state and alters no request payload, so it cannot act on an unverified external shape.
Evidence: `git diff --stat` shows only core/_http.py, connectors/_protocol.py, the 4 connector files, and two tests/ files; no request-building or schema/config code.
Falsification: a base/head PreparedRequest-corpus diff shows any request body/header/URL changed (would prove redaction leaked into requests).

## Exemption: evaluate-ticket structure
Reason: the linked CRM tickets (#1427 #1428 #1425 #1426 #1417 #1429 #1436 #1431) are #1398 hostile-review children using Problem/Evidence/Done-when/Falsifier, not Context/Goal/Acceptance + /think; evaluate-ticket BLOCKs them.
Evidence: lively-thunder r2 review records `ticket-fitness.log` BLOCK for each; the PR body carries the writing-rules:4 exemption (data/exemption-1846.md to be posted with this push).
Falsification: evaluate-ticket returns PASS for any of these tickets unchanged.

## Peer review (Junior — mechanics, shelves, gates)
- writing-code: no speculative abstraction; `_SecretRedactionMixin` is a 2-method mixin; symbols verified (`_client_secret` etc. exist in each connector __init__).
- writing-claims: counts below are grounded in same-turn test output.
- Credential-safety domain checklist: (1) no hardcoded secrets added; (2) redaction is value-based on the connector's OWN configured secrets, sourced from instance attrs + session auth headers; (3) log redaction — connectors log structured fields via RedactingLogger (no upstream text interpolated); confirmed by grep of log.* sites.
- Error-handling (SU-1): sinks still raise typed ConnectorError subclasses; no empty-result-on-failure introduced.
- Gate 1 Syntax: `ast.parse` on all changed .py (core/_http.py, _protocol.py, salesforce/hubspot/zoho/dynamics.py) → all parse clean (exit 0).
- Gate 2 Test suite: `pytest tests/test_review_1846_b2_gaps.py tests/test_1846_b2_value_redaction.py tests/test_1846_connector_secret_redaction.py` → 574 passed; `pytest tests/test_1417_* tests/test_1436_* tests/test_1427_* tests/test_1428_*` → 196 passed; red-first `tests/test_review_1846_b2_gaps.py` on 1537093f (pre-fix) → 16 failed. (exit 0 on the green runs.)
- Gate 3 Doc build: N/A (no docs/source changes; this verification file is not a Sphinx source).
- Gate 4 Notebook API: N/A (no .ipynb changes).
- Gate 5 Review-gate: N/A (no signal file).

## Lead review (adversarial)
Phase A coherence: the reviewer's finding (api_key field + bare configured-value echo leak) maps directly to R-a (field set) + R-b (value redaction); the diff implements exactly that, no drift.
Phase B verification:
- Did it fix or move the problem? Fixed: red-first 16/16 on 1537093f → 16/16 green; the bare-echo case (no field name) is closed by value redaction, not a wider key regex.
- Requests untouched (item 4): only diagnostic-text construction changed; 196 connector request/token/upsert tests pass unchanged → outgoing PreparedRequests unaffected. `key` added to the diagnostic field set does not touch requests (redact_secrets is never called on a request payload/header).
- Encoded echoes (item 1): `_expand_secret_values` adds quote/quote_plus/json forms; test_url_encoded_configured_secret_is_redacted passes.
- Exception chaining (item 2): converted sinks raise after status checks (no secret-bearing __context__); test_traceback_contains_no_secret_in_any_form passes.
- Min-length (R-b): values < 8 chars skipped; test_short_configured_value_is_not_redacted passes.
- Dismissal: static `_batch_error_detail` left key-based — justified because R-a's api_key coverage closes test 3's case and the method has no `self` for value context; the per-record UpsertError message is key-redacted in __post_init__. Logged as P3 (defense-in-depth follow-up candidate), not a blocker.

Post-mortem applicability: N/A — this is a forward security fix closing a reviewer FAIL, not a revert or regression-fix of shipped code; no pre-mortem Tiger materialized and no shipped bug passed a prior self-review. ("fix" in the subject is the redaction fix, not a revert.)

## Findings
| ID | Priority | Description | Resolution |
|----|----------|-------------|------------|
| F1 | P3 | Static `_batch_error_detail` + per-record UpsertError messages use key-based redaction only (no connector value context) | noted — R-a covers the api_key field case; bare-value echo in a batch per-record message is a defense-in-depth gap, candidate follow-up |

## Quantified claims
- "16/16 red on 1537093f → 16/16 green" — `pytest tests/test_review_1846_b2_gaps.py -q` → 16 failed (pre-fix) then 16 passed (post-fix).
- "574 passed" — `pytest tests/test_1846_b2_value_redaction.py tests/test_review_1846_b2_gaps.py tests/test_1846_connector_secret_redaction.py --no-cov -q` → 574 passed in 1.27s.
- "196 passed" — `pytest tests/test_1417_crm_retry_idempotency.py tests/test_1436_crm_token_lifecycle.py tests/test_1427_dynamics_create_record_id.py tests/test_1428_salesforce_getobjects_casing.py --no-cov -q` → 196 passed in 0.60s.

## Rework ledger
| Rework trigger | Root skip | Check cost | Rework cost | Ratio |
|---|---|---|---|---|
| self-review.sh blocked first push (missing trailers/artifact) | had not produced the Tier-C artifact before attempting push | minutes | one artifact + amend | low |

## Evidence-predates-work
Artifact: docs/verification/self-review-1846-b2.md
First-added commit: this artifact is committed in the same (amended, never-pushed) B2 work commit, so its first-added commit IS the work commit (self-ancestor). The review was written pre-push, post-implementation.
Work commit: the amended B2 implementation commit on fix/crm-cluster-1.
Verification: `git merge-base --is-ancestor <work-commit> <work-commit>` → 0 (a commit is its own ancestor; artifact does not post-date the pushed head).

## CI remediation addendum (ad9c6c03 → follow-up commit)

CI run 39392473438 on ad9c6c03 was RED. Two static-guard failures, one shared with the test matrix:

- **Exception-contract guard (shared cause).** `connectors/_protocol.py:149` `_SecretRedactionMixin._secret_values` wrapped `headers.get(header)` in a BROAD `except Exception` → `check_exception_contracts` reported `unlisted: 1`, failing `tests/guard/test_exception_contract_guard.py::test_converted_tree_has_zero_unlisted` in the `static guards`, `test (3.13)`, `test (3.14)` and `geo without GDAL` jobs. Fix: narrow to `except (AttributeError, TypeError)` — the only exceptions a non-mapping `headers` object raises; the `raw = None` fallback is kept so diagnostics never raise. Per the hub directive this is a genuine narrowing, not a blanket allowlist and not a registered exemption. Red-first reproduced locally (1 failed); after the fix `--list` reports `unlisted: 0` and the guard is 52 passed.
- **Error-path coverage.** `connectors/_http.py` had error sites (1 `except` + 3 `raise`) but no error-path tests → `check_error_path_coverage.py` FAIL. Fix: add `tests/test_1846_connectors_http_error_paths.py` exercising `request_raw`'s 401/403 `ConnectorAuthError`, exhausted-5xx `ConnectorError`, 429-never-clears `ConnectorError`, and repeated-`RequestException` `ConnectorError` via `pytest.raises` (backoff pinned to 0). After: scanner reports `connectors/_http.py PASS`, `397 pass / 0 fail`; the 5 new tests pass.

Regression: 775 passed across the b2 redaction, connector-secret-redaction, new connectors-http error-path, and connector ticket (#1417/#1436/#1427/#1428) suites — the narrowing is behavior-preserving for real mappings. The `test (3.13/3.14)` and `geo without GDAL` jobs shared the exception-contract guard as their cause (the `test (3.14)` log names it explicitly); CI on the new head confirms whether any non-shared failure remains.

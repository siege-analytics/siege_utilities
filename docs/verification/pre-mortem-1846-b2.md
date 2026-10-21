---
propagation-deferred: "Repo-resident pre-mortem for PR #1846 B2; travels with the PR."
---

# Pre-mortem — PR #1846 B2 credential redaction (#1398)

Reviewer-directed (lively-thunder) security forward-fix on fix/crm-cluster-1.
R-a (key-set extension) + R-b (value-based redaction of the connector's own
configured secrets, incl. URL/JSON-encoded forms) in diagnostic text only.

## What / Context
lively-thunder r2 FAIL @1537093f: api_key form/JSON diagnostics and bare
configured-value echoes escape redaction in str/repr/traceback/UpsertResult.

## Approach
R-a: add api_key/apikey/api-key/x-api-key/key to the diagnostic field set.
R-b: redact_secrets(values=...) replaces configured secret values + encoded
forms; _SecretRedactionMixin supplies each connector's values at the sinks.

## Risks
### R1: over-redaction touching real requests
Severity: medium — mitigated: redaction is diagnostic-text only; no
request-building touched; 196 connector request/token tests green unchanged.
### R2: short value blanks diagnostics
Severity: low — mitigated: _MIN_SECRET_VALUE_LEN=8 skip; covered by test.
### R3: secret leak via traceback/__cause__
Severity: medium — mitigated: sinks raise after status checks; traceback test green.

## Launch readiness
Implementation may proceed. 16/16 fixtures red-first on 1537093f then green;
574 redaction + 196 connector tests green. No launch-blocking tiger.

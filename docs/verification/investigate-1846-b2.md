---
propagation-deferred: "Repo-resident investigation record for PR #1846 B2; travels with the PR."
---

# Investigation — PR #1846 B2 credential redaction (#1398)

Source of record: the lively-thunder r2 hostile review
(sessions/261019-lively-thunder/data/review-1846-r2-behavioral.md), FAIL
@1537093f, plus direct code read of core/_http.py and connectors/* at 1537093f.

### Verified Shapes
- PROBED: `core/_http.py` `_SECRET_FIELDS` lacked `api_key`; `_FORM_SECRET`/`_QUOTED_SECRET` therefore left `api_key=VALUE` and `{"api_key":"VALUE"}` unredacted. Confirmed: the 16 reviewer fixtures fail 16/16 on 1537093f (`pytest tests/test_review_1846_b2_gaps.py` -> 16 failed).
- PROBED: `redact_secrets` had no configured-value context, so a bare echoed client secret (no recognised field name) survived `str(ConnectorAuthError)` — `test_configured_client_secret_absent_after_extraction` red on 1537093f for all 4 connectors.
- ATTESTED: the lively-thunder review independently reproduced the form/JSON and bare-value leaks in str, repr, formatted traceback, and `repr(UpsertResult)` across Salesforce/HubSpot/Zoho/Dynamics.

### Findings
- F-R-a (high): extend the diagnostic secret-field set with api_key/apikey/api-key/x-api-key/key.
- F-R-b (high): add value-based redaction of the connector's configured secrets (+ URL/JSON-encoded forms, min len 8) at the auth/token/request sinks via `_SecretRedactionMixin`. Static `_batch_error_detail` stays key-based (R-a covers api_key).

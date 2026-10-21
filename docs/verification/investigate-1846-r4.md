# Investigation — #1846 B2 round 4 (D1-D5 credential redaction)

Source: hub FINAL ruling (D1 through D5) plus the adopted reviewer fixture
tests/test_1846_b2_r4_remaining.py (lively-thunder r3). Tier: confirmed.

## Verified shapes
- UpsertError fields on each construction path echo provider text: Salesforce
  composite (_upsert_batch) and bulk (sf__Error), HubSpot and Zoho error loops,
  Dynamics batch (_batch_error_detail). Confirmed by grep + the red-first fixture.
- _extract_error was a staticmethod returning value-unaware redact_secrets(...)[:200],
  truncating before value redaction (D4 leak). Confirmed by the long-credential case.
- _secret_values caught only (AttributeError, TypeError); a hostile header .get raising
  ValueError leaked its secret-bearing text via the exception chain. Confirmed by the
  header-ValueError case.
- _safe_upstream_detail did not exist; short credentials (< the redactor minimum)
  were not removed by value replacement.

## Findings
- 1846-r4-D1 (high): value-redact every UpsertError message/field/code before
  construction.
- 1846-r4-D2 (high): value-redact every non-2xx branch, the logged URL path, and
  _extract_error (now an instance method returning self._redact(raw)[:200]).
- 1846-r4-D3 (medium): _safe_upstream_detail suppresses upstream detail on the five
  auth/token sinks when any cred is short; general paths keep self._redact.
- 1846-r4-D4 (medium): redact_secrets replaces whole values first, before syntax and
  truncation.
- 1846-r4-D5 (high): _secret_values uses except Exception -> fail-closed sentinel built
  after the except; broad handler registered in scripts/exception_contracts_allowlist.json.

## Verification
- Reviewer fixture tests/test_1846_b2_r4_remaining.py -> pytest -> 96 passed (red-first
  76 failed / 20 passed after D4 alone).
- Full connector and redaction set (33 files) -> pytest -> 2166 passed, 1 skipped, 0 failed.
- Exception-contract guard -> scripts/check_exception_contracts.py --root . -> unlisted 0;
  stale allow-list 0.

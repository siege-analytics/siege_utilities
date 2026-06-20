---
ticket: "#1015"
scope: "connectors/salesforce.py, connectors/__init__.py"
---

# Self-Review — #1015 Salesforce OAuth + connection management

## Junior Assessment

Added `connectors/salesforce.py` with `SalesforceConnector`:
- Web Server Flow (OAuth 2.0 authorization code)
- Username-Password Flow (direct token grant for dev/CI)
- Instance URL discovery from token response
- Token refresh via refresh_token grant
- Auto-refresh on expired tokens in `_ensure_connected()`
- Authenticated HTTP client with retry/backoff and error mapping
- Stub methods for data operations (raise NotImplementedError with ticket refs)

Uncommented `SalesforceConnector` in `connectors/__init__.py` lazy loader.

## Lead Assessment

**SU-1 compliance:** All auth failures raise `ConnectorAuthError`. The
`authenticate()` method never returns False or empty on failure. Token
exchange validates response status. Stub methods raise `NotImplementedError`
rather than returning empty DataFrames.

**Error mapping:** 401/403 → ConnectorAuthError, 429 → ConnectorRateLimitError
with `retry_after` from header, 404 → ConnectorNotFoundError, 5xx → retry
then ConnectorError. Matches ConnectorProtocol error hierarchy exactly.

**Token lifecycle:** `_token_expires_at` defaults to `issued_at + 2h`
(Salesforce's standard session timeout). `_ensure_connected()` auto-refreshes
when token is expired and a refresh_token exists. If no refresh_token,
raises `ConnectorAuthError` with clear guidance.

**Security:** Password concatenated with security_token per Salesforce's
convention. Token passed as query param in `_exchange_token()` via POST body,
not URL. Access token stored only in-memory on the session headers.

**Logging:** Auth lifecycle logged (init, authenticate, refresh) per
CLAUDE.md tactical principle 3.

## Trivial-investigation declaration

Auth flows follow Salesforce OAuth 2.0 documentation. HTTP pattern follows
established connectors (Vista Social, Instagram, X/Twitter). OAuthProvider
and OAuthIntegration already support Salesforce.

## Trivial pre-mortem declaration

New file + one-line init change. Stub methods explicitly raise
NotImplementedError — no risk of partial protocol satisfaction silently
succeeding. Existing connector imports unaffected.

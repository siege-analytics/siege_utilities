---
ticket: "#1067"
scope: "analytics/_social_protocol.py, analytics/__init__.py"
---

# Self-Review — #1067 SocialMediaProtocol definition

## Junior Assessment

Added `analytics/_social_protocol.py` with:
- `SocialMediaProtocol` — runtime-checkable Protocol with 7 read-only methods
- `SocialPost` dataclass — post with engagement metrics
- `SocialMetric` dataclass — single metric value for a time period
- Error hierarchy: `SocialMediaError`, `SocialMediaAuthError`, `SocialMediaRateLimitError`

Updated `analytics/__init__.py` to register 6 lazy imports from `._social_protocol`.

Verified: all imports resolve, runtime_checkable works, existing analytics imports unaffected.

## Lead Assessment

**Protocol shape:** Mirrors ConnectorProtocol's structure — property, authenticate, is_connected, then domain methods. Read-only (no write-back) is correct for analytics. The 7-method surface matches the ticket's acceptance criteria exactly.

**SU-1 compliance:** Error hierarchy parallels connectors/_protocol.py. `SocialMediaRateLimitError` carries `retry_after`. No silent failures.

**Existing connectors:** VistaSocialConnector and FacebookBusinessConnector don't implement this protocol yet — that's expected. They'll be adapted in follow-up tickets (#1068, #1069). The protocol defines the target shape.

**Lazy loading:** Uses same `_register()` pattern as all other analytics entries. No eager imports added.

## Trivial-investigation declaration

New protocol file following established ConnectorProtocol pattern. No behavioral changes to existing code. Verified protocol shape against existing connector methods (VistaSocialConnector.get_account_analytics, FacebookBusinessConnector).

## Trivial pre-mortem declaration

New file only. analytics/__init__.py adds 6 names to the lazy loader — no existing names affected, verified by reimporting GoogleAnalyticsConnector after the change.

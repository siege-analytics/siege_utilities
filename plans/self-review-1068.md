---
ticket: "#1068"
scope: "analytics/instagram.py, analytics/__init__.py"
---

# Self-Review — #1068 Instagram Graph API connector

## Junior Assessment

Added `analytics/instagram.py` with `InstagramConnector` implementing
`SocialMediaProtocol`. Uses `requests` directly (not `facebook_business` SDK)
against Meta Graph API v22.0. Features:

- Auto-discovers IG user ID via `/me/accounts` → `instagram_business_account`
- `get_account_info()` — username, followers, media count, biography
- `get_account_insights()` — daily time-series metrics with pivot into columns
- `get_posts()` — cursor-paginated media feed, filtered by date range
- `get_post_insights()` — per-post engagement metrics
- `get_stories_insights()` — active stories with per-story metrics (beyond protocol)
- Rate limit handling: retry on 5xx/transport, fatal on 401/403, surfaced on 429
- Profile management: create/save/load matching Facebook and GA patterns

Registered 4 lazy imports in `analytics/__init__.py`.

Verified: all imports resolve, protocol methods covered, profile creation works.

## Lead Assessment

**SU-1 compliance:** Every failure path raises. `_request_url` raises
`SocialMediaError` on non-2xx, `SocialMediaAuthError` on 401/403,
`SocialMediaRateLimitError` on 429. No silent empty returns.
`_ensure_connected()` gates all data methods — calling before `authenticate()`
raises immediately rather than returning empty data.

**Protocol conformance:** All 7 SocialMediaProtocol methods implemented.
`platform_name` is a property. `get_posts` returns DataFrame with columns
matching SocialPost fields. `get_post_insights` returns metric/value/period
columns. `get_account_insights` returns date-indexed metric columns.

**Rate limit handling:** Follows VistaSocialConnector pattern — 3 retries with
exponential backoff on 5xx/transport, no retry on auth/rate-limit. Meta's
`x-app-usage` header parsed for intelligent retry_after estimation.

**Pagination:** `get_posts` follows cursor pagination via `paging.next`. Date
filtering is client-side (Instagram API doesn't support `since`/`until` on
media endpoint). Posts are returned reverse-chronologically by the API, so
hitting a post before `start_date` terminates the scan.

**Security:** Access token passed as query parameter (Meta's convention, not
header-based). Token stored in profile JSON — same pattern as Facebook
connector. The profile management functions write to user-controlled
`config_directory`, not a system path.

## Trivial-investigation declaration

Follows established patterns: VistaSocialConnector for HTTP plumbing,
FacebookBusinessConnector for profile management, ConnectorProtocol for
error hierarchy shape. Instagram Graph API endpoints verified via Meta
developer documentation. No existing code is modified beyond adding lazy
imports to `__init__.py`.

## Trivial pre-mortem declaration

New file only. `analytics/__init__.py` adds 4 names — no existing names
affected. The connector requires a valid Meta OAuth token to function;
without one, `authenticate()` raises `SocialMediaAuthError`. No risk of
silent misbehavior.

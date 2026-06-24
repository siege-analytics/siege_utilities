---
ticket: "#1023, #1024, #1025"
scope: "connectors/zoho.py, connectors/__init__.py"
---

# Self-Review — #1023/#1024/#1025 Zoho CRM connector (auth + read + write)

## Junior Assessment

Added `connectors/zoho.py` with `ZohoConnector`:
- **Auth (#1023):** OAuth 2.0 self-client (refresh_token) and web-based flows.
  Multi-DC support (US, EU, IN, AU, JP). Authorization header uses
  `Zoho-oauthtoken` prefix per Zoho convention.
- **Read (#1024):** `list_object_types()` via settings/modules API,
  `get_objects()` with list and COQL query paths, custom module field
  discovery via `get_custom_module_fields()`, page-based pagination,
  CRM model mapping helpers.
- **Write (#1025):** Single-record create/update, batch upsert via
  `/upsert` endpoint (100 per request) with `duplicate_check_fields`,
  UpsertResult with per-record error reporting.

## Lead Assessment

**Multi-DC:** Five data centers configured with separate accounts_url and
api_url. DC selected at init time, not auto-detected. Auth header
`Zoho-oauthtoken` (not `Bearer`) matches Zoho's convention.

**COQL queries:** Filters translated to COQL syntax. String escaping via
`_coql_escape()`. Pagination via offset. Handles `more_records` flag from
response info.

**Lookup fields:** Zoho returns lookup fields as `{"id": "...", "name": "..."}`.
`_records_to_dataframe()` extracts the name as the main column value and
adds `{field}_id` as a separate column.

**Upsert:** Uses `/crm/v6/{module}/upsert` with `duplicate_check_fields`
(Zoho's match mechanism). Response includes `action` field ("insert" or
"update") for tracking created vs updated records.

**SU-1 compliance:** Create/update check for `status == "success"` in
response, raise on failure. Empty DataFrame returns zero-count UpsertResult.
All HTTP errors map to connector error hierarchy.

## Trivial-investigation declaration

Zoho CRM v6 API endpoints follow Zoho developer documentation. Multi-DC
URLs match Zoho's published data center list.

## Trivial pre-mortem declaration

New file + one-line init change. No existing code modified.

---
ticket: "#1020, #1021, #1022"
scope: "connectors/hubspot.py, connectors/__init__.py"
---

# Self-Review — #1020/#1021/#1022 HubSpot connector (auth + read + write)

## Junior Assessment

Added `connectors/hubspot.py` with `HubSpotConnector`:
- **Auth (#1020):** OAuth 2.0 authorization code flow and private app access
  token validation. Token refresh via refresh_token grant. Rate limit handling
  via ConnectorRateLimitError.
- **Read (#1021):** `list_object_types()`, `get_objects()` with property
  selection, Search API for filtered queries, cursor pagination via `after`,
  association traversal via `get_associations()`, CRM model mapping helpers.
- **Write (#1022):** Single-record create/update, batch upsert via Batch API
  (100 records per request) with UpsertResult, association create/remove,
  contact merge.

Uncommented `HubSpotConnector` in `connectors/__init__.py` lazy loader.

## Lead Assessment

**SU-1 compliance:** Auth failures raise ConnectorAuthError. Private app
tokens are validated by making a test API call — invalid tokens raise
immediately. `create_record()` checks for returned ID, raises if missing.
Empty DataFrame returns zero-count UpsertResult with warning. All HTTP
errors map to the connector error hierarchy.

**Search API:** Filters translated to HubSpot filterGroups format.
String/int → EQ operator, list → IN operator, None → NOT_HAS_PROPERTY.
Search is POST to `/crm/v3/objects/{type}/search`, list is GET to
`/crm/v3/objects/{type}` — correct per HubSpot v3 API.

**Batch operations:** 100 records per batch (HubSpot's limit).
Upsert uses `idProperty` to specify the match field. Batch failures
are caught per-batch with ConnectorError — failed batches report
all records as failures, successful batches parse individual results.

**Association management:** Standard v3 associations API. PUT for
create, DELETE for remove. Association type is optional (HubSpot
auto-infers for standard types).

**Merge:** Contacts-only merge via `/crm/v3/objects/contacts/merge`.
Primary/secondary ID pattern matches HubSpot API.

**Model mapping:** `to_crm_contacts()`, `to_crm_accounts()`,
`to_crm_opportunities()` handle HubSpot's nested `properties` structure.
Vendor-specific fields go to `metadata`. Field names mapped:
- HubSpot `firstname`/`lastname` → CRM `first_name`/`last_name`
- HubSpot `dealname` → CRM `name`
- HubSpot `dealstage` → CRM `stage`
- HubSpot `annualrevenue` → CRM `revenue` (Decimal)

**Pagination:** List uses `after` cursor from `paging.next.after`.
Search uses integer `after` offset. Both respect `limit` parameter
and truncate results.

**HTTP client:** Uses `requests` (matching Salesforce connector) not
`httpx` as the ticket suggested — consistent with codebase. Same
retry/backoff pattern as SalesforceConnector.

## Trivial-investigation declaration

HubSpot CRM v3 API endpoints follow HubSpot developer documentation.
Search API, Batch API, and Associations API are all stable v3 endpoints.

## Trivial pre-mortem declaration

New file + one-line init change. No existing code modified beyond
uncommenting the lazy-load registration.

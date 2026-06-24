---
ticket: "#1026, #1027, #1028"
scope: "connectors/dynamics.py, connectors/__init__.py"
---

# Self-Review — #1026/#1027/#1028 Dynamics 365 connector (auth + read + write)

## Junior Assessment

Added `connectors/dynamics.py` with `DynamicsConnector`:
- **Auth (#1026):** MSAL integration — ConfidentialClientApplication for
  app-only (client credentials), PublicClientApplication for delegated
  (username/password ROPC). Token auto-refresh on expiry.
- **Read (#1027):** `list_object_types()` via EntityDefinitions, `get_objects()`
  with OData $select/$filter/$top, @odata.nextLink pagination, FetchXML
  escape hatch via `fetch_xml()`, CRM model mapping helpers.
- **Write (#1028):** Single-record create/update via REST, batch upsert
  via $batch endpoint (up to 1000 per request) with multipart/mixed format,
  alternate key upsert pattern.

## Lead Assessment

**MSAL integration:** Uses `msal.ConfidentialClientApplication` for
client_secret auth and `msal.PublicClientApplication` for ROPC.
`_scope` set to `{environment_url}/.default` — correct pattern for
Dynamics 365. MSAL handles token caching internally.

**OData filter translation:** `_build_odata_filter()` handles None→null,
bool→true/false, int/float→unquoted, str→single-quoted with `''` escape,
list→OR expression. Correct OData v4 syntax.

**Pagination:** `@odata.nextLink` is a full URL. `_query_all_odata()`
strips the environment_url prefix to get a relative path, then passes
through `request()` which prepends it back.

**FetchXML:** URL-encoded and passed as query parameter. Returns raw
DataFrame from `value` array. This is the escape hatch for queries
OData can't express.

**$batch:** Multipart/mixed format with changeset boundaries per OData
batch spec. Each record is a PATCH with alternate key
`entity(match_field='value')`. Simplified response parsing (200/202 =
all success, other = all failure) — full individual response parsing
would require multipart MIME parsing which is future work if needed.

**SU-1 compliance:** Auth failures raise ConnectorAuthError. Empty
DataFrame returns zero-count UpsertResult. HTTP errors map to connector
error hierarchy. MSAL errors extracted from result dict.

**Model mapping:** Dynamics field names are lowercase with underscores.
Lookup fields use `_parentcustomerid_value` pattern. Industry is stored
as `industrycode` (integer option set) — mapped to string.

## Trivial-investigation declaration

Dataverse Web API v9.2 endpoints follow Microsoft documentation. MSAL
Python library is the official Microsoft auth SDK. $batch format follows
OData v4 batch specification.

## Trivial pre-mortem declaration

New file + one-line init change. MSAL is an optional dependency — import
check raises ImportError at init time with guidance.

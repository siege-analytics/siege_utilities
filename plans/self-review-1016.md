---
ticket: "#1016"
scope: "connectors/salesforce.py"
---

# Self-Review — #1016 Salesforce read operations

## Junior Assessment

Extended `SalesforceConnector` with:
- `list_object_types()` — hits `/services/data/v60.0/sobjects`, returns sorted
  queryable object names
- `get_objects()` — builds SOQL from (object_type, fields, filters, limit),
  executes via `/services/data/v60.0/query`, paginates via `nextRecordsUrl`,
  returns DataFrame
- SOQL builder: `_build_soql()`, `_soql_condition()`, `_soql_escape()`
- Pagination: `_query_all()` follows `nextRecordsUrl` until exhausted
- Default field sets for 8 standard objects (Contact, Account, Opportunity,
  Lead, Case, Campaign, Task, Event)
- CRM model mappers: `to_crm_contacts()`, `to_crm_accounts()`,
  `to_crm_opportunities()` — convert DataFrames to `_models.py` shapes

## Lead Assessment

**SU-1 compliance:** Empty results return an empty DataFrame with the
correct column headers (not `None`, not `pd.DataFrame()`). Zero-record
results log a warning. `_ensure_connected()` raises before any query
attempt. SOQL errors propagate via `ConnectorError` from `request()`.

**Filter translation:** `_soql_condition()` handles None → `null`,
bool → `true`/`false`, int/float → unquoted, str → single-quoted with
`_soql_escape()`, list → `IN (...)`. `_soql_escape()` escapes backslashes
first then single quotes — correct order to avoid double-escaping.
Bool check comes before int/float check (since `isinstance(True, int)`
is True in Python).

**Pagination:** `_query_all()` loops on `nextRecordsUrl` (Salesforce's
standard pagination mechanism). The next URL is an absolute path —
`request()` prefixes with `instance_url`, which works because Salesforce
returns paths like `/services/data/v60.0/query/01g...`. Each page is
logged with running totals.

**Default fields:** 8 standard objects with sensible defaults (Id, name
fields, foreign keys, timestamps). Unknown object types fall back to
`["Id"]` — callers must pass explicit fields for custom objects.

**Model mapping:** `to_crm_contacts()`, `to_crm_accounts()`,
`to_crm_opportunities()` use lazy imports to avoid circular dependency.
Vendor-specific fields go into `metadata` dict. Decimal conversion for
monetary fields matches `_models.py` contract.

**Logging:** Every query logs total record count and page sizes per
tactical principle 3.

## Trivial-investigation declaration

SOQL syntax follows Salesforce SOQL documentation. Pagination follows
Salesforce REST API query documentation. Default fields are the standard
object fields available in every Salesforce org.

## Trivial pre-mortem declaration

Additive change to existing file. Stubs for write methods (#1018/#1019)
unchanged. `list_object_types()` was a stub raising NotImplementedError,
now a real implementation. `get_objects()` was a stub, now real.
Existing auth contract and HTTP plumbing untouched.

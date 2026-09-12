# Parsons overlap reconciliation — Salesforce & Google Workspace

**Purpose:** decide, with grounded behavioral comparison, whether siege_utilities's existing Salesforce and Google Workspace connectors should coexist with Parsons's, be deprecated in favor of Parsons's, or be kept as sole implementations.

**Closes P0-5 of parent epic:** [#1148 Epic: TMC Parsons integration](https://github.com/siege-analytics/siege_utilities/issues/1148).

## Decision — TL;DR

| Overlap | Decision | Namespace |
|---|---|---|
| Salesforce | **Ship both** (option C). Different jobs, both useful. | `siege_utilities.connectors.salesforce.SalesforceConnector` (existing) + `siege_utilities.integrations.parsons.salesforce.ParsonsSalesforce` (new wrapper) |
| Google Workspace (Sheets) | **Ship both** (option A). Parsons is worksheet-and-permissions-oriented; siege is DataFrame-in-DataFrame-out. | `siege_utilities.analytics.google_sheets.*` (existing) + `siege_utilities.integrations.parsons.google_sheets.ParsonsGoogleSheets` (new wrapper) |
| Google Workspace (Docs / Slides / Drive) | **No decision needed** — Parsons has no Docs / Slides / Drive connector. Siege owns these entirely. | (siege only) |

Rationale: real behavioral differences on both sides. Neither implementation is a strict subset of the other. Deprecating either loses capability. The `ConnectorProtocol` audit below covers the ship-both risk.

---

## Salesforce — evidence + decision

### Siege's `SalesforceConnector`

Source: [`siege_utilities/connectors/salesforce.py`](../siege_utilities/connectors/salesforce.py) (1,308 LOC, 53 defs). Implements `ConnectorProtocol` from [`connectors/_protocol.py`](../siege_utilities/connectors/_protocol.py). Public method surface:

- **Query API:** `SOQLQuery` builder (`select`, `from_`, `where`, `where_raw`, `order_by`, `limit`, `offset`, `build`) + `_soql_literal(value)` codec. `soql(query: str | SOQLQuery) -> pd.DataFrame`.
- **Object introspection:** `list_object_types() -> list[str]`, `get_objects(...)`.
- **CRM-model converters:** `to_crm_contacts(df)`, `to_crm_accounts(df)`, `to_crm_opportunities(df)` — produce typed CRM objects from raw DataFrames.
- **OAuth 2.0:** `authenticate()` (client_credentials), `authenticate_with_code(code)`, `get_authorization_url()`, `refresh_access_token()`, `is_connected()`.
- **Session mgmt:** `close()`, `__enter__` / `__exit__` context manager.

Shape: **CRM-abstraction-oriented.** The API is designed around "get a DataFrame of Accounts / Contacts / Opportunities and hand them to a typed CRM model." Query construction is fluent, object conversion is typed.

### Parsons `Salesforce`

Source: [`parsons/salesforce/salesforce.py`](https://github.com/move-coop/parsons/blob/main/parsons/salesforce/salesforce.py). Public method surface (8 methods):

- **Query:** `query(soql: str)`.
- **Introspection:** `describe_object(object_type)`, `describe_fields(object_type)`.
- **Bulk operations:** `insert_record(...)`, `update_record(...)`, `upsert_record(...)`, `delete_record(...)`.
- **Session:** `client` property (raw `simple-salesforce` client).
- **Auth:** OAuth (client_credentials) OR username/password.

Shape: **SOQL + bulk-operations primitive.** The API is thin over `simple-salesforce`: SOQL string in, records in/out.

### Diff

| Capability | Siege | Parsons |
|---|:---:|:---:|
| SOQL query returning DataFrame | ✅ | ⚠️ returns records, not DataFrame |
| SOQLQuery builder (typed fluent API) | ✅ | ❌ |
| CRM-model typed converters (`to_crm_contacts`, ...) | ✅ | ❌ |
| Bulk insert / update / upsert / delete | ❌ | ✅ |
| Object schema description (`describe_*`) | ⚠️ via `list_object_types` | ✅ |
| Context manager (`with`) | ✅ | ❌ |
| OAuth authorization-code flow | ✅ | ❌ (client_credentials only) |
| Raw `simple-salesforce` client access | ❌ | ✅ (via `.client`) |
| Test coverage today | ❌ (hostile-review: 33 except/raise sites, no error-path tests) | ✅ (upstream Parsons test suite) |

**Neither is a subset of the other.**

### Decision: ship both

Two implementations with distinct jobs. Namespace boundary makes the pick unambiguous:

- `siege_utilities.connectors.salesforce.SalesforceConnector` — the CRM-abstraction path. Use for Django-style typed model workflows.
- `siege_utilities.integrations.parsons.salesforce.ParsonsSalesforce` — the bulk-operations path. Use for CDC-style bulk sync jobs where insert/update/upsert throughput matters.

Both implement `ConnectorProtocol`. Both raise the same `ConnectorError` hierarchy. Users pick based on workload, not by "which one is better."

**Consequences for the epic:**

- Ship `siege_utilities/integrations/parsons/salesforce.py` in Phase 3 alongside the other connector wrappers.
- Do NOT deprecate `siege_utilities/connectors/salesforce.py`. It stays.
- **Follow-up debt:** siege's Salesforce connector has 33 except/raise sites and no error-path tests (hostile-review §5). This is a separate SU-4b ticket, not part of this epic. Filing at follow-up time.

### ConnectorProtocol audit (per ticket acceptance criterion)

Both wrappers must implement:
- `ConnectorError` hierarchy raises (never `except Exception: return {}`).
- Constructor auth accepts kwargs (no env-var side effects; siege bridges via P0-4's `_auth.py`).
- `pd.DataFrame` return type on read methods (never `list[dict]` or raw records to the caller).

Siege's existing `SalesforceConnector`: **partially compliant** — returns DataFrames, uses typed errors, but has 33 unaudited except sites that need SU-4b remediation. The overlap decision does not fix that debt but does not make it worse.

New `ParsonsSalesforce` wrapper: **must comply from day one**. Every Parsons exception mapped to `ConnectorError` subclass via `_errors.py` (P1-3), every DataFrame conversion via `_adapter.py` (P1-2).

---

## Google Sheets — evidence + decision

### Siege's Google Sheets surface

Files: [`siege_utilities/analytics/google_sheets.py`](../siege_utilities/analytics/google_sheets.py) + [`siege_utilities/analytics/google_workspace.py`](../siege_utilities/analytics/google_workspace.py) (`GoogleWorkspaceClient` with `from_oauth`, `from_1password`, `from_service_account`, `from_account`, `from_registry`).

Public methods (Sheets-specific):
- `create_spreadsheet(...)`, `write_values(...)`, `append_rows(...)`, `read_values(...)`, `read_dataframe(...)`, `write_dataframe(...)`, `get_spreadsheet_metadata(...)`, `copy_spreadsheet(...)`, `add_sheet(...)`, `batch_update(...)`.

Shape: **DataFrame-in-DataFrame-out**, siege-native. Multi-account via `GoogleWorkspaceClient` factory methods (OAuth / 1Password / service account / registry). Focus is on treating Sheets as a persistence layer for pandas.

### Parsons `GoogleSheets`

Source: [`parsons/google/google_sheets.py`](https://github.com/move-coop/parsons/blob/main/parsons/google/google_sheets.py). Public methods (16):

- **Read:** `list_worksheets`, `get_worksheet_index`, `get_worksheet`, `read_sheet*` (3 deprecated).
- **Write:** `create_spreadsheet`, `delete_spreadsheet`, `add_sheet`, `append_to_sheet`, `paste_data_in_sheet`, `overwrite_sheet`.
- **Sharing / permissions:** `share_spreadsheet`, `get_spreadsheet_permissions`.
- **Formatting:** `format_cells`.

Shape: **worksheet-and-permissions-oriented**. Uses `gspread` under the hood. Multi-account via `subject` parameter (impersonation).

### Diff

| Capability | Siege | Parsons |
|---|:---:|:---:|
| Create spreadsheet | ✅ | ✅ |
| Write values | ✅ | ✅ |
| Append rows | ✅ | ✅ |
| Read as DataFrame | ✅ | ⚠️ read as raw records; DataFrame conversion is caller's job |
| Read/write with DataFrame semantics | ✅ | ❌ |
| Copy spreadsheet | ✅ | ❌ |
| Delete spreadsheet | ❌ | ✅ |
| Share / permissions | ❌ | ✅ |
| Cell formatting | ❌ | ✅ |
| Multi-account via factory (`GoogleWorkspaceClient.from_*`) | ✅ | ⚠️ via `subject` impersonation only |
| batch_update raw API | ✅ | ❌ |

**Neither is a subset of the other.**

### Decision: ship both (option A — differentiated capability sets)

- `siege_utilities.analytics.google_sheets.*` — DataFrame ETL workflows. Use when the sheet is a pandas persistence layer.
- `siege_utilities.integrations.parsons.google_sheets.ParsonsGoogleSheets` — worksheet operations, sharing, formatting. Use when the sheet is a user-facing artifact (permissioning, styling, share links).

Both bridged to siege credential profiles via `_auth.py` (P0-4 design).

**Consequences for the epic:**

- Ship `siege_utilities/integrations/parsons/google_sheets.py` in Phase 3 fan-out.
- Do NOT deprecate `siege_utilities/analytics/google_sheets.py`. Complementary, not redundant.
- Publish a capability-picker table in `docs/parsons_integration.md` (Phase 5) so users know when to reach for which.

### Google Docs / Slides / Drive

Parsons has **no** Docs, Slides, or Drive connector. Its `google` extra provides Sheets + BigQuery + Cloud Storage + Admin + Civic — no document authoring surface. Siege's `google_docs.py`, `google_slides.py`, and Drive access via `GoogleWorkspaceClient.drive_service` are the sole implementations.

**No decision needed.** Siege keeps ownership. This confirms the README's headline "Google Workspace write APIs (Sheets, Docs, Slides, Drive)" claim — it stays true because 3 of 4 have no Parsons alternative.

---

## Falsification for this decision doc

### Salesforce

- **Claim:** siege's `SalesforceConnector` has behavioral differences from Parsons's `Salesforce` material enough to justify ship-both.
- **Falsification:** diff of the two connectors' public method surfaces shows Parsons's is a strict superset AND siege's SOQLQuery builder + CRM-model converters are unused in siege consumers (grep siege for `SOQLQuery(`, `to_crm_contacts(`, etc., and confirm ≥1 caller). Empirical check pending — file a follow-up ticket to run this grep before Phase 3 fan-out closes.

### Google Sheets

- **Claim:** Parsons's Google Sheets has sharing / permissions / formatting features siege lacks.
- **Falsification:** feature parity check reveals siege's `batch_update` (raw Sheets API access) can express Parsons's `share_spreadsheet` / `format_cells` operations, making the Parsons wrapper redundant. Run this test in P4-2 implementation as a spike.

### Docs / Slides / Drive

- **Claim:** Parsons has no Docs / Slides / Drive connector.
- **Falsification:** next Parsons release ships one. Re-verify against `move-coop.github.io/parsons/html/stable/` connector index before Phase 5.

---

## Blocks

- Phase 4 (P4-1 Salesforce reconciliation, P4-2 Google Workspace reconciliation) — this doc IS those decisions. Phase 4 tickets implement the ship-both decisions above.
- **Does NOT block** Phase 1-3 substrate or connector wrappers.

## Follow-up tickets to file after this closes

1. **SU-4b: siege_utilities/connectors/salesforce.py error-path tests.** 33 except/raise sites, zero tests. Separate from Parsons epic; blocks the "salesforce is production-safe" claim.
2. **Feature-parity spike: does siege's `google_sheets.batch_update` express Parsons's sharing + formatting?** Falsifies Google Sheets ship-both decision if yes.
3. **Capability-picker doc row** in `docs/parsons_integration.md` (Phase 5 deliverable) — user-facing guidance on when to reach for which Salesforce / Google Sheets implementation.

## References

- Siege Salesforce: [`../siege_utilities/connectors/salesforce.py`](../siege_utilities/connectors/salesforce.py)
- Siege Google Sheets: [`../siege_utilities/analytics/google_sheets.py`](../siege_utilities/analytics/google_sheets.py)
- Siege Google Workspace client: [`../siege_utilities/analytics/google_workspace.py`](../siege_utilities/analytics/google_workspace.py)
- Parsons Salesforce: <https://github.com/move-coop/parsons/blob/main/parsons/salesforce/salesforce.py>
- Parsons Google Sheets: <https://github.com/move-coop/parsons/blob/main/parsons/google/google_sheets.py>
- ConnectorProtocol: [`../siege_utilities/connectors/_protocol.py`](../siege_utilities/connectors/_protocol.py)
- Parent epic: [#1148](https://github.com/siege-analytics/siege_utilities/issues/1148)
- Sibling P0 tickets: [#1149](https://github.com/siege-analytics/siege_utilities/issues/1149), [#1150](https://github.com/siege-analytics/siege_utilities/issues/1150), [#1151](https://github.com/siege-analytics/siege_utilities/issues/1151), [#1152](https://github.com/siege-analytics/siege_utilities/issues/1152)
- Hostile-review context: session `260819-awake-crow/plans/hostile-review-siege-utilities.md`
- This ticket: [#1153](https://github.com/siege-analytics/siege_utilities/issues/1153)

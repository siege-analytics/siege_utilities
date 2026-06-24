---
ticket: "#1018"
scope: "connectors/salesforce.py"
---

# Self-Review — #1018 Salesforce write-back

## Junior Assessment

Replaced write stubs with real implementations:
- `create_record()` — POST to `/sobjects/{type}`, returns record ID
- `update_record()` — PATCH to `/sobjects/{type}/{id}`, returns True
- `upsert_records()` — batches DataFrame into 25-record chunks, calls
  Composite SObject Collections endpoint, returns `UpsertResult`
- `_composite_upsert()` — single batch execution, parses per-record
  success/failure, builds `UpsertError` entries

## Lead Assessment

**SU-1 compliance:** `create_record()` raises `ConnectorError` when
`success` is false in the response. `update_record()` delegates to
`request()` which raises on non-2xx — never returns False silently.
`upsert_records()` returns `UpsertResult` with explicit `failure_count`
and `errors` list — callers must check `result.ok`.

**Composite API batching:** `COMPOSITE_BATCH_SIZE = 25` matches
Salesforce's limit. Records are chunked before sending. Each batch
response is parsed independently with `base_index` offset for error
tracking across batches.

**Partial success:** `allOrNone: false` in the request body means some
records can succeed while others fail. The response is a list of per-
record results. Failed records without error details still get an
`UpsertError` entry ("Record failed without error details") — no
silent failures.

**Response parsing:** Handles both list responses (standard) and dict
responses (some Salesforce versions wrap in `results` key). Defensive
but not suppressive — unknown shapes propagate the original response.

**Error detail extraction:** `fields` is a list in Salesforce errors;
we take the first field. `statusCode` maps to `UpsertError.code`.

**Logging:** Every batch logged with index and size. Final summary
logged with success/failure totals.

## Trivial-investigation declaration

Composite SObject Collections endpoint follows Salesforce REST API
documentation. Batch size of 25 is Salesforce's documented limit.

## Trivial pre-mortem declaration

Replaces three `NotImplementedError` stubs with real implementations.
Existing read operations and auth contract unchanged.

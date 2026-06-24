---
ticket: "#1019"
scope: "connectors/salesforce.py"
---

# Self-Review — #1019 Salesforce Bulk API v2

## Junior Assessment

Added Bulk API v2 support:
- `bulk_insert()` — insert via Bulk API v2 ingest job
- `_bulk_upsert()` — upsert via Bulk API v2 with external ID field
- `_bulk_job()` — full lifecycle: create → upload CSV → close → poll → collect results
- `_bulk_create_job()`, `_bulk_upload_data()`, `_bulk_close_job()` — job lifecycle steps
- `_bulk_poll_job()` — poll with timeout and progress callbacks
- `_bulk_collect_results()` — parse success/failure CSV results
- `_bulk_get_csv_results()` — retrieve and parse CSV from Bulk API endpoints
- `_dataframe_to_csv()` — DataFrame → CSV string conversion
- Auto-routing in `upsert_records()`: Composite for ≤2000 records, Bulk for >2000
- `force_bulk` parameter to bypass threshold
- `progress_callback` on both Composite and Bulk paths

## Lead Assessment

**Auto-routing:** `upsert_records()` routes to `_bulk_upsert()` when
`len(records) > BULK_THRESHOLD` (2000) or `force_bulk=True`. Below
threshold, uses Composite path via `_composite_upsert_all()`. The
threshold matches Salesforce's practical guidance (Composite for small
batches, Bulk for large).

**Job lifecycle:** Create → upload → close → poll → collect. The close
step sets state to `UploadComplete` which triggers server-side processing.
This matches Bulk API v2 documentation exactly.

**CSV upload:** Direct PUT with `text/csv` content type. Timeout
multiplied by 4 for large uploads. `_dataframe_to_csv()` uses pandas
`to_csv()` with `lineterminator="\n"` matching the `lineEnding: "LF"`
in job creation.

**Polling:** `_bulk_poll_job()` checks terminal states
(JobComplete, Failed, Aborted) and times out after 600s. Sleep interval
is 5s. Each poll logs state, processed count, failed count, and elapsed
time. Progress callback fires each iteration.

**Result collection:** Success results parsed for `sf__Id` and
`sf__Created` flag. Failure results parsed for `sf__Error`. Both use
CSV DictReader. Collection errors are logged as warnings but don't mask
the overall result — partial success reporting still works.

**SU-1 compliance:** Failed/Aborted jobs raise ConnectorError. Empty
DataFrames return zero-count UpsertResult with warning. All failures
produce UpsertError entries.

**Progress callbacks:** `(status, processed, total)` signature. Called
during both Composite batching and Bulk polling. Satisfies tactical
principle 3 (observable output).

## Trivial-investigation declaration

Bulk API v2 endpoints follow Salesforce Bulk API 2.0 documentation.
Job lifecycle (Open → UploadComplete → InProgress → JobComplete) is
standard.

## Trivial pre-mortem declaration

Additive change. Existing `upsert_records()` signature gains two optional
kwargs (`force_bulk`, `progress_callback`) — backward compatible.
`_composite_upsert_all()` extracts the previous body of `upsert_records()`
with no behavior change. Composite path unchanged.

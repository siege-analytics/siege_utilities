# CRM coverage comparison for #1453

The same `tests/test_1453_crm_coverage.py` was run against v4.0.0 (`9c3463b14aa3104e4efa2cd5236659a689d13f89`) and the fixed branch (`972ff91224035d6713d84fb84d5a73f00fae7f91`). The tag was checked out in a temporary detached worktree with only the new test module copied in. Its production code, pytest configuration, and conftest were unchanged.

Both runs used `~/.pyenv/versions/default_31111/bin/python` (Python 3.11.11, pandas 2.3.3). All connector HTTP requests used a scripted requests adapter; unmounted HTTP transport was blocked. MSAL construction was stubbed. No credentials or live API calls were used.

The v4.0.0 run used `python -m pytest tests/test_1453_crm_coverage.py --no-cov` without `-x` to record every failure. The fixed branch used `python -m pytest tests/test_1453_crm_coverage.py -x --no-cov`. JUnit output supplied the case results below.

v4.0.0: 36 failed, 46 passed. Fixed branch: 82 passed, no skips.

The COQL cases exercise unlimited paging and limits of one, two, and three records. They check returned IDs, exact offset/count clauses, and the number of HTTP calls. All four fail on v4.0.0 and pass on the fixed branch. The scripted adapter rejects requests after the limit is met.

Salesforce and Dynamics limit tests check the server-side SOQL LIMIT and OData $top contracts with responses that honor those limits. HubSpot, Zoho list, and Zoho COQL also verify client truncation of an oversized page. Dynamics partial failure is measured across two changesets: the earlier batch succeeds and every record in the failed atomic changeset fails.

The earlier stacked commits already added targeted null-mapping and error regressions. This module adds complete HTTP success flows and direct units for adapters, models, and deduplication. It tests the current corrected behavior without changing production code for #1453.

The 835 pre-batch connector tests, measured on the fixed code before including the new modules, covered 0% of `_adapters.py`, 67% of `_models.py`, and 0% of `_dedup.py`. The combined 937-test run covered 100%, 100%, and 95% respectively. Connector-package statement coverage rose from 85% to 94%. Coverage was measured with `python -m coverage run --source=siege_utilities.connectors -m pytest <modules> -x --no-cov`; the post-commit checks use plain pytest with the required `-x --no-cov` options.

| Test case | v4.0.0 | Fixed branch |
| --- | --- | --- |
| `test_canonical_mapping_mixed_null_frame[accounts-dynamics]` | FAIL | PASS |
| `test_canonical_mapping_mixed_null_frame[accounts-hubspot]` | FAIL | PASS |
| `test_canonical_mapping_mixed_null_frame[accounts-salesforce]` | FAIL | PASS |
| `test_canonical_mapping_mixed_null_frame[accounts-zoho]` | FAIL | PASS |
| `test_canonical_mapping_mixed_null_frame[contacts-dynamics]` | FAIL | PASS |
| `test_canonical_mapping_mixed_null_frame[contacts-hubspot]` | FAIL | PASS |
| `test_canonical_mapping_mixed_null_frame[contacts-salesforce]` | FAIL | PASS |
| `test_canonical_mapping_mixed_null_frame[contacts-zoho]` | FAIL | PASS |
| `test_canonical_mapping_mixed_null_frame[opportunities-dynamics]` | FAIL | PASS |
| `test_canonical_mapping_mixed_null_frame[opportunities-hubspot]` | FAIL | PASS |
| `test_canonical_mapping_mixed_null_frame[opportunities-salesforce]` | FAIL | PASS |
| `test_canonical_mapping_mixed_null_frame[opportunities-zoho]` | FAIL | PASS |
| `test_dedup_cross_crm_names_have_stable_ids_and_preserve_sources` | PASS | PASS |
| `test_dedup_custom_columns_normalizer_namespace_and_blank_names` | PASS | PASS |
| `test_dedup_empty_output_schema[frames0]` | PASS | PASS |
| `test_dedup_empty_output_schema[frames1]` | PASS | PASS |
| `test_dedup_empty_output_schema[frames2]` | PASS | PASS |
| `test_dynamics_batch_success_and_atomic_partial_failure[False]` | FAIL | PASS |
| `test_dynamics_batch_success_and_atomic_partial_failure[True]` | FAIL | PASS |
| `test_dynamics_next_link_and_server_limit[1]` | PASS | PASS |
| `test_dynamics_next_link_and_server_limit[2]` | PASS | PASS |
| `test_dynamics_next_link_and_server_limit[3]` | PASS | PASS |
| `test_dynamics_next_link_and_server_limit[None]` | PASS | PASS |
| `test_empty_adapters[geographic_adapter-columns1]` | PASS | PASS |
| `test_empty_adapters[pipeline_adapter-columns0]` | PASS | PASS |
| `test_empty_adapters[tabular_adapter-columns2]` | PASS | PASS |
| `test_geographic_address_selection_preserves_index` | PASS | PASS |
| `test_hubspot_after_cursor_and_limit_boundary[1]` | PASS | PASS |
| `test_hubspot_after_cursor_and_limit_boundary[2]` | PASS | PASS |
| `test_hubspot_after_cursor_and_limit_boundary[3]` | PASS | PASS |
| `test_hubspot_after_cursor_and_limit_boundary[None]` | PASS | PASS |
| `test_hubspot_batch_upsert_results_and_error_identity[False]` | FAIL | PASS |
| `test_hubspot_batch_upsert_results_and_error_identity[True]` | FAIL | PASS |
| `test_model_dataframes_flatten_addresses_numbers_and_dates` | PASS | PASS |
| `test_model_empty_frames_and_independent_metadata[CRMAccount-values1]` | PASS | PASS |
| `test_model_empty_frames_and_independent_metadata[CRMActivity-values3]` | PASS | PASS |
| `test_model_empty_frames_and_independent_metadata[CRMContact-values0]` | PASS | PASS |
| `test_model_empty_frames_and_independent_metadata[CRMOpportunity-values2]` | PASS | PASS |
| `test_models_reject_unknown_fields[CRMAccount-values2]` | PASS | PASS |
| `test_models_reject_unknown_fields[CRMActivity-values4]` | PASS | PASS |
| `test_models_reject_unknown_fields[CRMAddress-values0]` | PASS | PASS |
| `test_models_reject_unknown_fields[CRMContact-values1]` | PASS | PASS |
| `test_models_reject_unknown_fields[CRMOpportunity-values3]` | PASS | PASS |
| `test_pipeline_counts_rows_and_averages_known_amounts` | PASS | PASS |
| `test_pipeline_preserves_unstaged_deals_and_ordered_zero_rows` | FAIL | PASS |
| `test_salesforce_bulk_v2_lifecycle_and_csv_results[False]` | PASS | PASS |
| `test_salesforce_bulk_v2_lifecycle_and_csv_results[True]` | FAIL | PASS |
| `test_salesforce_composite_upsert_results_and_payload[False]` | FAIL | PASS |
| `test_salesforce_composite_upsert_results_and_payload[True]` | FAIL | PASS |
| `test_salesforce_next_records_url_and_server_limit[1]` | FAIL | PASS |
| `test_salesforce_next_records_url_and_server_limit[2]` | FAIL | PASS |
| `test_salesforce_next_records_url_and_server_limit[3]` | FAIL | PASS |
| `test_salesforce_next_records_url_and_server_limit[None]` | FAIL | PASS |
| `test_soql_full_query_and_http_execution` | PASS | PASS |
| `test_soql_where_rendering[kwargs0-Field = 'O\\'Reilly']` | PASS | PASS |
| `test_soql_where_rendering[kwargs1-Field != null]` | PASS | PASS |
| `test_soql_where_rendering[kwargs10-Field = 2026-10-19T12:00:00Z]` | FAIL | PASS |
| `test_soql_where_rendering[kwargs2-Field > 1 AND Field >= 2 AND Field < 10 AND Field <= 9]` | PASS | PASS |
| `test_soql_where_rendering[kwargs3-Field = true]` | PASS | PASS |
| `test_soql_where_rendering[kwargs4-Field IN ('A', 'B')]` | PASS | PASS |
| `test_soql_where_rendering[kwargs5-Field NOT IN (1, 2)]` | PASS | PASS |
| `test_soql_where_rendering[kwargs6-Field LIKE 'A%']` | PASS | PASS |
| `test_soql_where_rendering[kwargs7-Field = null]` | PASS | PASS |
| `test_soql_where_rendering[kwargs8-Field != null]` | PASS | PASS |
| `test_soql_where_rendering[kwargs9-Field = 2026-10-19]` | FAIL | PASS |
| `test_tabular_selection_rename_sort_and_limit` | PASS | PASS |
| `test_timeseries_empty_or_invalid_input_schema[frame0]` | PASS | PASS |
| `test_timeseries_empty_or_invalid_input_schema[frame1]` | PASS | PASS |
| `test_timeseries_utc_aggregation_fills_empty_periods` | FAIL | PASS |
| `test_zero_limit_never_sends_http[dynamics-contacts-fields2-columns2]` | FAIL | PASS |
| `test_zero_limit_never_sends_http[hubspot-contacts-fields0-columns0]` | FAIL | PASS |
| `test_zero_limit_never_sends_http[zoho-Contacts-fields1-columns1]` | FAIL | PASS |
| `test_zoho_coql_offset_and_limit_boundary[1]` | FAIL | PASS |
| `test_zoho_coql_offset_and_limit_boundary[2]` | FAIL | PASS |
| `test_zoho_coql_offset_and_limit_boundary[3]` | FAIL | PASS |
| `test_zoho_coql_offset_and_limit_boundary[None]` | FAIL | PASS |
| `test_zoho_page_number_and_limit_boundary[1]` | PASS | PASS |
| `test_zoho_page_number_and_limit_boundary[2]` | PASS | PASS |
| `test_zoho_page_number_and_limit_boundary[3]` | PASS | PASS |
| `test_zoho_page_number_and_limit_boundary[None]` | PASS | PASS |
| `test_zoho_upsert_results_and_payload[False]` | FAIL | PASS |
| `test_zoho_upsert_results_and_payload[True]` | FAIL | PASS |

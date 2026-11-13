---
ticket_refs:
  - siege-analytics/siege_utilities#1404: comment posted https://github.com/siege-analytics/siege_utilities/issues/1404#issuecomment-6651699934
---

# Self-review: #1404 / PR #1791, permanent client errors are not retried

Working as: software engineer, data engineer

Goal source: https://github.com/siege-analytics/siege_utilities/issues/1404#issuecomment-6259574607 (finding F1 and return criteria) and the owner scope comment https://github.com/siege-analytics/siege_utilities/issues/1404#issuecomment-6133684640
Review-Tier: C (task classifier floor: the branch diff against main includes `.github/workflows/`)
Pre-author-inventory: https://github.com/siege-analytics/siege_utilities/issues/1404#issuecomment-6651536041 (fact sheet: `api.py:255-275`, test gap at `tests/test_1404_census_dual_source_fallback.py:187-194`)
Investigate-artifact: https://github.com/siege-analytics/siege_utilities/issues/1404#issuecomment-6651536041
Pre-mortem-artifact: https://github.com/siege-analytics/siege_utilities/issues/1404#issuecomment-6651536041
Hostile-review-artifact: plans/hostile-review-1404-client-errors.md

## Ticket-fitness exemption

### #1404

Reason: #1404 predates the canonical ticket template. Its body carries Problem, Failure scenarios, Done when, Assumptions and Falsifier sections, but not the canonical Evidence section.
Evidence: those sections live in https://github.com/siege-analytics/siege_utilities/issues/1404, with the owner scope addition at https://github.com/siege-analytics/siege_utilities/issues/1404#issuecomment-6133684640; the reviewer verdict is https://github.com/siege-analytics/siege_utilities/issues/1404#issuecomment-6259574607.
Falsification: revert the implementation; `tests/test_1404_census_dual_source_fallback.py::test_server_error_falls_back` goes red because an HTTP 503 never reaches the bulk source, and `tests/test_1404_census_dual_source_fallback.py::test_client_error_does_not_fall_back` goes red because a 404 makes 5 calls with sleeps `[1, 2, 4, 8]`.
Verified 2026-11-05: with `siege_utilities/geo/census/api.py` and `siege_utilities/geo/census/dual_source.py` checked out from `origin/develop` (keeping `census_api_client.py` so the module imports), `pytest tests/test_1404_census_dual_source_fallback.py -k "test_server_error_falls_back or test_client_error_does_not_fall_back"` -> 9 failed (408/500/503/599 raise `CensusAPIError` at `api.py:264` with no bulk fallback; 400/401/403/404/422 `assert 5 == 1` calls); after `git checkout HEAD --` -> 9 passed, worktree clean.

## Assumptions

1. A 4xx other than 408 and 429 is permanent for the same request; retrying cannot change the answer.
2. HTTP 408 is a server-side request timeout and should behave like a transport timeout (retry, then fall back).
3. #1749 is an open proposal, so the release note belongs in held `[4.1.0]`.
4. Under the operator's standing rule (2026-11-06: an entry is BREAKING when code that worked on 4.0.0 now behaves differently), the #1404 entry moves from `[4.1.0]` `### Fixed` to `### BREAKING` with a Migration line. Outages and 408 now fall back instead of raising, permanent 4xx are no longer retried, and `ApiSource` retries no longer multiply. `CensusAPI.__init__` takes no retry argument, so the Migration points callers at `degraded` and at retrying around the call, not at a configuration knob. The develop `71f02b0b` merge kept both `[4.1.0]` Fixed entries (a union); develop's lines are unchanged.

## Test plan

- Red before (at `384b4f6d`, after the develop merge): `test_client_error_does_not_fall_back` for 400, 401, 403, 404 and 422 -> 5 failed, each with 5 calls and sleeps `[1, 2, 4, 8]`.
- After: `tests/test_1404_census_dual_source_fallback.py tests/test_census_api_client.py tests/test_dual_source_1375.py tests/test_summary_file_1385.py tests/test_credential_url_leak.py` -> 444 passed. Permanent 4xx make 1 call with no sleeps; 408 joins 500, 503 and 599 in the fallback test (5 calls, `[1, 2, 4, 8]`, bulk result).
- Exception-contract guard: unlisted 0, stale 0 after the edit.
- Scope note: broader census modules (`test_census_bug_fix.py`, `test_census_api_integration.py`) were not used as evidence. `test_census_bug_fix.py::test_census_function_with_invalid_state` fails in `spatial_data.get_census_boundaries`, which this PR does not touch, and the integration module is slow and network-bound.

## Peer review

- Shelves: writing-tests:1 (red before on the call count and recorded sleeps), writing-tests:2 (408 and permanent 4xx boundaries), writing-claims:2 (counts carry `Verified-by:`); siege-utilities SU-2 (CHANGELOG and guide describe the retry taxonomy).
- Syntax check: `py_compile` on 2 changed `.py` files -> all parse clean (exit 0).
- Test suite: 444 passed (exit 0).
- Findings: 5xx, transport and 429 paths unchanged; the handler's exception-contract fingerprint did not change.
- Notebook API: no notebook exercises the 4xx retry path (no notebook calls `_make_request_with_retry` or asserts retry counts). Doc build: `docs/CENSUS_DATA_GUIDE.md` updated (Markdown).

## Lead review

- F1 fixed at the retry loop, with assertions on call count and sleeps that the old test lacked.
- The hostile review's 408 inconsistency fixed rather than documented: 408 now matches the ticket's timeout-falls-back contract.
- The hosted `test (3.12)` STATIC_URL failure was never attributed to this PR; the fresh exact-head CI run after the develop merge is the evidence.
- Post-mortem: not applicable. Caught in review before merge; no published version carried it.

## Quantified claims

- 5 red before; 444 passed after; guard 0 unlisted, 0 stale.

## Rework ledger

2 hostile-review follow-ups applied (408 classification, guide text).

## Develop integration (83d3032e, 2026-11-10)

Reason for the merge: CI run 42766691710 at `7795a2bb` failed the required `test (3.13)` lane (seed 2859228993) and cancelled 3.11, 3.12 and 3.14. The 7 failures were all in `tests/test_development_runtime_introspection_contracts.py` (`ImproperlyConfigured`, STATIC_URL).

- The cause is #1882, not this PR's code. Package introspection followed a file-path check that matches every installed package on CI and evaluated Django lazy objects. This PR's `client` fixture changes a Django setting, which loads `django.contrib.staticfiles.storage`.
- The fix landed in develop as #1883 (`8d740a9a`). This merge brings it in, so fresh PR CI runs with it.
- The earlier "never attributed to this PR" note (Lead review) stands for the code: the trigger is this PR's settings-changing fixture, the defect is in `architecture.py`.

Merge: `7795a2bb772e11a5b7144ae59d409b348a6c638c` (first parent) + develop `83d3032e1e67de9d43dd7b3c8a95f52e28dadcab`. No conflicts, no manual resolution. The pure merge tree is `20b1c7cd8861fd88e4d82ff2576e1b2ccbaca285`; this section is the only addition on top of it.

- Inventory vs `83d3032e`: only this PR's 13 files differ. Every imported develop file equals landed develop.
- Inventory vs `7795a2bb`: only develop's 16 files differ, including `siege_utilities/development/architecture.py` and `tests/test_1882_architecture_module_walk.py`.
- CHANGELOG: develop's #1885 renamed the held section to `[5.0.0]`. The #1404 entry, with its Migration paragraph, now sits under `## [5.0.0]` `### BREAKING`, unchanged. The `[4.1.0]` references in Assumptions 3 and 4 above are historical.
- No feature code, test, retry/fallback taxonomy or BREAKING/Migration text changed.

Tests in the merged tree, one invocation: Python 3.11.11, pytest 8.4.2, pytest-randomly 5.0.0, Django 5.2.14, pandas 2.3.3, duckdb 1.4.4, pyproj 3.7.2.

- `pytest -p randomly --randomly-seed=2859228993` over `tests/test_1404_census_dual_source_fallback.py tests/test_census_api_client.py tests/test_dual_source_1375.py tests/test_summary_file_1385.py tests/test_credential_url_leak.py tests/test_1882_architecture_module_walk.py tests/test_architecture.py tests/guard/test_exception_contract_guard.py` -> 551 passed. The same set with a random seed also gave 551 passed.
- `scripts/check_exception_contracts.py --list` -> 0 unlisted, 0 stale.
- Boundary: the local virtualenv path does not contain `siege_utilities`, so this run does not reproduce CI's path condition. Fresh hosted CI on the merge head is the evidence for the 3.13 lane. No live Census calls; HTTP and sleep are faked, as before.

## Develop integration (79f37f4d, 2026-11-11)

Reason for the merge: after #1812 landed, develop `79f37f4d` and this branch added entries at the same place in `CHANGELOG.md`, so the pull request reported a conflict.

Merge: `8558aee2ed30f7a696c424e1216a515708be4573` (first parent) + develop `79f37f4df28059a875c8dbf84cf77ce86812bdbb`, made with `--no-ff --no-commit`. One file conflicted, `CHANGELOG.md`, with one add/add hunk under `## [5.0.0]` `### BREAKING`. Develop's #1474/#1458, #1465/#1835 and #1812 entries with their Migration paragraphs come first, then this PR's #1404 entry with its Migration paragraph, both verbatim; only the conflict markers were removed. No source or test file needed resolution.

- `CHANGELOG.md` against `79f37f4d`: 16 lines added, none removed (the #1404 entry). Against `8558aee2`: 85 added, none removed.
- Inventory against `79f37f4d`: only this PR's 13 files differ. Every imported develop file equals landed develop.
- Inventory against `8558aee2`: exactly the 24 files develop changed between `83d3032e` and `79f37f4d`, plus this section.
- Guard inputs: `scripts/exception_contracts_allowlist.json` and `scripts/check_credential_urls.py` are develop's blobs (this PR never changed them); `scripts/contracts/contract_allowlist.json` is this PR's blob with `CensusServerError` (develop never changed it). The exception allowlist has 205 keys and no duplicates.

Tests in the merged tree: Python 3.11.11, pytest 8.4.2, pytest-randomly 5.0.0.

- `pytest -p randomly --randomly-seed=1791` over `tests/test_1404_census_dual_source_fallback.py tests/test_census_api_client.py tests/test_census_api_key_warning.py tests/test_census_cache_backend.py tests/test_census_cache_django_roundtrip.py tests/test_census_catalog_cache.py tests/test_dual_source_1375.py tests/test_summary_file_1385.py tests/test_credential_url_guard.py tests/test_credential_url_leak.py tests/test_instagram_token_exchange_logging.py tests/test_public_api_surface.py tests/test_1882_architecture_module_walk.py tests/test_architecture.py tests/test_development_runtime_introspection_contracts.py tests/guard/test_exception_contract_guard.py tests/test_exception_contract_review.py` -> 1007 passed, none skipped.
- `scripts/check_exception_contracts.py --list` -> 205 handlers flagged, 0 unlisted, 0 stale.
- The credential URL scan of `siege_utilities` runs inside `tests/test_credential_url_guard.py` (`test_no_unreviewed_credential_urls`, `test_credential_url_allowlist_is_specific_and_current`), both passing.
- Boundary: no live Census calls; HTTP and sleep are faked. `tests/test_census_api_integration.py` is network-bound and was not run. PostGIS and notebook jobs are left to exact-head CI.

# Self-review: PR #1762 PL 94-171 downloader (#1488), pre-flight

Review-Tier: C (the checkout's path floor; this commit changes `siege_utilities/geo/census_files/pl_downloader.py` and its tests).

## Assumptions
Working as: software engineer (Junior) and data-integrity tech lead (Lead).
Domain(s): Census PL 94-171 file parsing and download transport.
Geospatial cross-cut: yes (GEOID construction only; no geometry).
Goal source: the #1488 Problem / Done when / Falsifier sections; ruling to complete each ticket's acceptance criteria on its PR (2010 rejected with `ValueError`, as the ticket words it).
Plan reference: https://github.com/siege-analytics/siege_utilities/issues/1488#issuecomment-6761608244
Investigate-artifact: https://github.com/siege-analytics/siege_utilities/issues/1488#issuecomment-6761608244
Pre-mortem-artifact: https://github.com/siege-analytics/siege_utilities/issues/1488#issuecomment-6761608244
Hostile-review-artifact: none yet. An independent exact-head review of the pushed commit is pending; this is NOT a pass.
Project-contribution: PL GEOIDs, tables and labels are correct, and a state is fetched once per call without holding the archive in memory.

## Investigation
- At PR head `764a32de`: items 1–3 of #1488 are implemented and tested; 2010 raises `NotImplementedError`; `get_data` calls `_get_geographic_file` and `_get_data_files`, each of which calls `_stream_download(url)` for the same state archive on a cold cache (up to four in-memory downloads per call); members are read with `read().decode('latin-1')` into `StringIO`; a missing segment returns `pd.DataFrame({'LOGRECNO': []})`; `P1_010N` and `P1_011N` carry wrong labels.
- `_stream_download_to_file(url, dest, timeout, max_bytes)` already streams to disk with the size cap and an atomic write.
- Callers of the private seams: `tests/test_pl_downloader_parsing.py` patched `_stream_download` and calls `_download_and_parse_geo/_data(url, ...)` directly. `tests/test_atomic_write_failures.py` uses the module-level `_stream_download_to_file`, which is unchanged.
- Develop `2deb6a1f` changed none of the PR's files since merge-base `7f534f6c`.

## Pre-mortem
1. Tiger (launch-blocking). Severity: P1. The temporary archive leaks on failure. Mitigation: `_ArchiveOnce.cleanup()` in `finally` in `get_data`, `_get_geographic_file`, `_get_data_files` and both `_download_and_parse_*` wrappers; tested after a width-mismatch error and a missing segment.
2. Tiger (launch-blocking). Severity: P1. The size cap is lost. Mitigation: `_download_archive` calls `_stream_download_to_file(..., max_bytes=PL_MAX_DOWNLOAD_BYTES)`; the existing cap test for that helper passes.
3. Tiger (fast-follow). Severity: P2. Encoding drift when streaming. Mitigation: `io.TextIOWrapper(member, encoding='latin-1', newline='')`; `test_latin1_geo_fields_survive_streaming`.
4. Tiger (launch-blocking for release notes). Severity: P1. Non-breaking mislabel. Mitigation: `### BREAKING` + Migration in the PR body.
5. Elephant. Severity: P3. 2010 parsing; the ticket allows rejection.

## Peer review (Junior: shelves, gates)
- Shelves: SU-1 (the missing segment raises instead of returning an empty frame); SU-2 (docstrings list the `ValueError` cases; 2010 is rejected with the error type the ticket names).
- Gate 1 (syntax/lint): flake8 on the module and test file is clean; `scripts/check_test_file_hygiene.py`: PASS.
- Gate 2 (tests): `tests/test_pl_downloader_parsing.py tests/test_pl_downloader.py tests/test_geo_census_files_pl_downloader_errors.py tests/test_geo_alignment.py tests/test_1539_1550_bulk_sites.py tests/test_atomic_write_failures.py tests/test_smoke.py tests/test_runtime_guard.py tests/test_sql_safety.py`, `--no-cov -p no:randomly`: 230 passed, 1 skipped.
- Gate 3 (docs): `get_data` and `get_pl_data` docstrings; the #1488 entry in `CHANGELOG.md` `[4.1.0]` `### BREAKING` (with Migration), mirrored exactly in the PR body block.
- Notebook impact (SU-4a): no notebook calls `get_pl_data`, `get_pl_tracts`, `get_pl_blocks` or `PLFileDownloader`.

## Lead review (adversarial)
Phase A coherence: 2010 → `_validate_parse_year`; single streamed download → `_ArchiveOnce` + `_download_archive` + member streams; item 5 → labels and the missing-segment error.
Phase B verification (`tests/test_pl_downloader_parsing.py`, 26 tests). For the two red runs the fixture temporarily fell back to the old `_stream_download` seam, still counting calls; the fallback was removed afterwards.
- Against PR head `764a32de`: 9 failed / 17 passed. Failures: the three 2010 cases and the 2010 cache case (`NotImplementedError`), single download, cleanup after a parse error, missing segment, P1 labels, and `test_old_geo_cache_is_ignored_and_new_cache_is_reused`. That last one fails only because its no-download patch targets `_download_archive`, which does not exist at that head. The latin-1 and warm-cache tests pass there as controls.
- Against `v4.0.0`: 25 failed / 1 passed (the latin-1 control).
- After: 26 passed.
- Test changes: the fixture installs archives through `_download_archive` and counts calls; the 2010 expectations change from `NotImplementedError` to `ValueError`, as #1488 requires.

## Findings
| ID | Priority | Description | Resolution |
|----|----------|-------------|------------|
| F1 | P1 | 2010 rejected with `NotImplementedError`, ticket requires `ValueError` | `ValueError`, same message |
| F2 | P1 | Archive downloaded up to four times per call, held in memory | one streamed download per call to a temporary file, member streams, cleanup in `finally` |
| F3 | P2 | Missing segment returned an empty frame | `ValueError` naming the segment and archive |
| F4 | P3 | `P1_010N`/`P1_011N` mislabelled | 2020 labels |
| F5 | P2 | PR body "Refs", Fixed, `[Unreleased]`, local interpreter path | body: "Fixes #1488", BREAKING + Migration, item-to-test map, hygiene |

Out of scope, reported only: the segment linking field is named `CHAESSION` (Census: `CHARITER`) but is dropped before merging; unknown `tables` entries are ignored silently.

## Ticket-fitness exemption

writing-rules:4 exemption for the governing ticket.

### #1488
- **Reason:** #1488 predates the canonical ticket template. It uses Problem / Evidence / Failure scenario / Done when / Assumptions / Falsifier sections.
- **Evidence:** the defects, the v4.0.0 probe and the acceptance criteria are in the #1488 body. The investigation, pre-mortem and Junior/Senior review are at https://github.com/siege-analytics/siege_utilities/issues/1488#issuecomment-6761608244.
- **Falsification:** restore `siege_utilities/geo/census_files/pl_downloader.py` from `764a32de`; `test_2010_parsing_is_explicitly_unsupported` then fails on `NotImplementedError`, and with a fixture that patches the old seam, `test_cold_cache_call_downloads_the_state_archive_once` counts more than one download. Verified on 2026-11-10.

## Test plan / Quantified claims
Interpreter: local Python 3.11.11, run from the repository root.
- Related run as in Gate 2: 230 passed, 1 skipped.
- `tests/test_pl_downloader_parsing.py`: 9 failed / 17 passed on `764a32de`; 25 failed / 1 passed on `v4.0.0`; 26 passed after.

## Rework ledger
- Pre-flight round, 2026-11-10: 2010 `ValueError`; single streamed download with cleanup; missing-segment error; P1 labels; body classification and acceptance map.

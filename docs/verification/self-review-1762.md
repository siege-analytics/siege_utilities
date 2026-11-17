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
- Fix round, 2026-11-17 (whole-PR review of `00ea3207`: two S2 findings and one S3 migration note): see the section below.

## Fix round, 2026-11-17: ragged records and UTF-8 (base `00ea3207`)

### Assumptions
- Goal: the public `get_pl_data` path must reject a PL file whose records do not all have the same field count, and must decode PL text as UTF-8. This closes the two S2 findings of the whole-PR review at `00ea3207`.
- Scope: `pl_downloader.py`, its test module, the #1488 CHANGELOG entry and this document. No develop merge.

### Findings addressed
- **S2-A, ragged records.** Both parsers read with `pd.read_csv(..., header=None)`, and the width check compared only the frame's column count. pandas takes the width from the first record and pads a later short record with missing values. So a full 152-field `pl2` record followed by a 151-field record parsed, and was cached, with `H1_003N` missing. A later long record raised a raw pandas `ParserError`.
  - Fix (final, after review round 2 below): `_ValidatedPipeText` is the single tokenizer. It is a read-only text stream over the zip member that pandas reads. It splits every non-blank line on each `|` and raises `ValueError` naming the file, the record number, the line number, the observed count and the first record's count. pandas reads only the validated records, with `quoting=csv.QUOTE_NONE`, so its fields are exactly the counted fields. Empty fields still count as fields, so legitimately empty values still parse. The exact segment width (149 / 152 / 15) is still enforced by `_assign_data_columns`, so every data record must have exactly that width. Errors are raised while pandas reads the member, before the affected file's parsed cache is written. A header or segment already parsed in the same call keeps its valid cache.
  - Geographic header: this is permissive prefix parsing, not full publisher-schema validation. The Census 2020 PL technical documentation, Chapter 2 (pp. 2-1, 2-4; Figure 2-4, pp. 2-7 to 2-10, as cited in the review), defines the full header. `GEO_COLUMNS_2020` names only its leading 37 fields (the module labels it "simplified"), and the existing tests accept header widths of 35, 37 and 40. So the header is held to a uniform record width plus the existing required named fields, rather than an exact count. A code comment records this.
- **S2-B, encoding.** Both parsers hard-coded `encoding='latin-1'`, so UTF-8 text such as an n with tilde decoded as two Latin-1 characters. Both now decode as UTF-8. The validating stream decodes strictly, and invalid bytes raise `ValueError` naming the file instead of being replaced. The UTF-8 basis is the Census 2020 PL readme, p. 2, as cited in the review. The old test that wrote a Latin-1 fixture and expected it to round-trip encoded the defect, and is replaced.
- **Cache.** `_PL_CACHE_SCHEMA_VERSION` goes from 2 to 3. v2 parsed caches may hold Latin-1-decoded text or padded short records, so they are no longer read.
- **S3, Migration text.** The CHANGELOG entry now says that geographic columns are named instead of integer-labelled, and that joined results carry one `STUSAB` (and `FILEID`, `CHAESSION`, `CIFSN`) instead of `STUSAB_x`/`STUSAB_y` pairs. It also covers UTF-8 text, the new `ValueError` for a short record, and the cache re-parse.
- The review's other S3, the generated summary appendix in the PR body, is a review-bot block that the bot maintains. It is not this PR's attribution, so no change.

### Test plan and results (local, Python 3.11.11, `pytest -o addopts="" -p no:cacheprovider --noconftest`)
- New tests in `tests/test_pl_downloader_parsing.py` (12 items):
  - ragged truncated and oversized records for `pl1`, `pl2` and `pl3` through public `get_pl_data`, with no data cache written (6);
  - ragged geographic records, with no geo cache written (2);
  - a positive control: a legitimately empty field and a trailing blank line still parse (1);
  - UTF-8 text survives parsing, the public path and the parsed-cache round trip (1);
  - invalid UTF-8 raises `ValueError` and nothing is cached (1);
  - v2 parsed caches are not reused (1).
- The review's two counterexamples are ported verbatim in substance: `test_ragged_segment_record_raises_and_is_not_cached[truncated-2]` is the 152-then-151 `pl2` case, and `test_utf8_geo_text_is_preserved_through_parse_and_cache` opens with the review's exact UTF-8 assertion.
- RED, new tests against the unchanged parser at `00ea3207`: 11 failed, 1 passed. The passing one is the positive control, which is expected to pass before and after.
- After the fix, the same 12 tests: 12 passed.
- Module set `test_pl_downloader_parsing`, `test_pl_downloader`, `test_geo_census_files_pl_downloader_errors`, `test_atomic_write_failures`: 79 passed, 0 failed, 0 skipped. Of those, 68 existed at `00ea3207`; the net change is 12 added, 1 replaced.
- Release-process and changelog-export tests (`test_release_process`, `test_user_config_export_changelog`): 25 passed.
- ruff `--select F,E9` on the module and the test file: no findings. `py_compile`: OK.
- Notebook impact: no notebook calls the PL functions (repository grep).
- Not run locally: the full suite, PostGIS tests, lint ratchet, bandit and package checks. No real Census download was made. Hosted CI on the new head is the authority.
- The counts above are for review round 1 (staged tree `0f3e143c`, never committed). Round 2 below supersedes the design, and its counts are the current ones.

### Review round 2 (delta review of `0f3e143c`): one tokenizer
- **Finding.** The round-1 validator counted raw `|`, but pandas tokenized the same bytes with CSV quoting and its own blank-line rule.
  - A record whose last two fields were wrapped in one quote pair had the right pipe count. pandas then joined them into one field and padded the last column with missing values, in all three segments and in the geographic header.
  - Whitespace-only lines, which pandas skipped in v4.0.0, were rejected as 1-field records.
  - The CHANGELOG claim "before anything is cached" was too strong: a valid geographic cache can already exist when a later segment fails.
- **Fix.**
  - `_ValidatedPipeText` replaces the separate validation pass. pandas reads only the records it validated, with `quoting=csv.QUOTE_NONE`, `keep_default_na=False` and `na_values=['']`.
  - Quote characters are data. Only an empty field becomes missing, so "NA" or "NULL" text in a geographic field stays text.
  - Whitespace-only lines are skipped (`line.strip() == ''`), as v4.0.0 skipped them. A delimiter-only line such as `||||` is a record and fails the width check.
  - Each member is read once, in bounded chunks.
- **Count fields.** `pl_downloader` returns every field as text. The in-library consumer `populate_pl_demographics` silently drops a value that `float()` rejects (pre-existing, tracked as #1947, out of scope here). So a data-segment count must be empty or ASCII digits; anything else raises `ValueError` naming the file, record, line, column and value. An empty count field still parses as a missing value, as in v4.0.0 and round 1.
- **Wording.** The CHANGELOG now says "before the affected file's parsed cache is written (a header or segment already parsed in the same call keeps its valid cache)", and covers quotes, whitespace-only lines, count fields and NA-like text.
- **New tests in `tests/test_pl_downloader_parsing.py` (22 items):**
  - whitespace-only lines (space, tab, space plus CRLF) skipped in the geographic header and each segment, through `get_pl_data` (12);
  - a delimiter-only line is a record and fails the width check, in the geographic header and `pl2` (2);
  - a quote-wrapped count and a letter in a count raise, naming the column, in each segment, with no parsed cache for that segment (6);
  - geographic text keeps quotes and "NA"/"NULL" literally through parsing, the public path and the parsed cache, while an empty field is missing (1);
  - a failing segment leaves the already valid geographic cache in place and writes no data cache (1).
- **RED and after, local Python 3.11.11:**

| Run | Against `0f3e143c` | After the fix |
|---|---|---|
| The review's delta attacks (byte-identical copy) | 12 failed, 27 passed | 39 passed |
| The 22 new tests | 19 failed, 3 passed (the delimiter-only and geo-cache tests already held, and stay as guards) | 22 passed |
| The review's original counterexamples (byte-identical copy) | | 2 passed |
| PL module set (`test_pl_downloader_parsing`, `test_pl_downloader`, `test_geo_census_files_pl_downloader_errors`, `test_atomic_write_failures`) | | 101 passed, 0 failed, 0 skipped |
| Release-process and changelog-export tests | | 25 passed |
| `test_populate_pl_demographics_errors` | | 1 skipped: "GeoDjango/GDAL not available" |

  - The temporary copies of the review's files were removed before staging.
- ruff `--select F,E9` on the module and the test file: no findings. `py_compile`: OK.

### Independent review
- A delta review of the round-2 staged tree is pending from an independent reviewer. Its link goes in the commit's `Hostile-Review` trailer.

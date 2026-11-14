# Self-review: PR #1769 google_sheets write/read (#1432), pre-flight extension

Review-Tier: C (the checkout's path floor; this commit changes `siege_utilities/analytics/google_sheets.py` and its tests).

## Assumptions
Working as: software engineer (Junior) and release tech lead (Lead).
Domain(s): Google Sheets API client wrappers, pandas I/O.
Geospatial cross-cut: no (identifier strings such as GEOIDs are carried as text only).
Goal source: the #1432 Problem / Done when / Falsifier sections; scope extension approved for this PR (complete every acceptance item, no debt; `append_rows` unchanged under item 1's second alternative).
Plan reference: https://github.com/siege-analytics/siege_utilities/issues/1432#issuecomment-6761234802
Investigate-artifact: https://github.com/siege-analytics/siege_utilities/issues/1432#issuecomment-6761234802
Pre-mortem-artifact: https://github.com/siege-analytics/siege_utilities/issues/1432#issuecomment-6761234802
Hostile-review-artifact: none yet. An independent exact-head review of the pushed commit is pending; this is NOT a pass.
Project-contribution: identifier columns survive a Sheets round trip, and sheets with omitted trailing cells can be read.

## Investigation
- `analytics/google_sheets.py` at `v4.0.0` is identical to merge-base `7f534f6c`.
- At PR head `6990023b`, items 2 and 3 are implemented and tested (22 tests, all failing on v4.0.0 per the PR's revert check). RAW is hard-coded in `write_dataframe`.
- Not covered at `6990023b`: item 4 (`read_dataframe` builds `pd.DataFrame(values[1:], columns=values[0])`, which raises on ragged rows), and item 1 as written (no parameter on `write_dataframe`; `append_rows` keeps `USER_ENTERED`).
- `write_values` passes `value_input_option` through unvalidated, and `write_dataframe` clears the tab before calling it.
- Develop `2deb6a1f` changed none of the PR's files since the merge-base.

## Pre-mortem
1. Tiger (launch-blocking). Severity: P1. An invalid `value_input_option` clears the tab, then the update fails. Mitigation: validation against `{"RAW", "USER_ENTERED"}` is the first statement in `write_dataframe`; `test_invalid_value_input_option_raises_before_any_request` asserts no clear and no update for four bad values.
2. Tiger (launch-blocking). Severity: P1. Padding misaligns data. Mitigation: right-padding only (Sheets omits trailing cells only); tests for a short header, short rows, colliding generated names and an empty header row.
3. Tiger (launch-blocking for release notes). Severity: P1. Shipped as a non-breaking fix. Mitigation: `### BREAKING` with a Migration line per change in the PR body.
4. Paper Tiger. Severity: P3. `has_header=False` behaviour drifts. Mitigation: that path is unchanged (pandas pads with `None`), with a control test.
5. Elephant. Severity: P3. Clear and update are separate requests. Disclosed in the docstring and the PR body.

## Peer review (Junior: shelves, gates)
- Shelves: SU-2 (enumerated parameter validated at the top with `ValueError`; docstrings state RAW default, opt-in and padding rules); SU-1 (the empty-sheet `pd.DataFrame()` return is the documented "no values" result, not an error path, and is unchanged).
- Gate 1 (syntax/lint): `flake8 --max-line-length=127` on the three touched Python files: clean. `scripts/check_test_file_hygiene.py`: PASS.
- Gate 2 (tests): `tests/test_google_sheets_write_dataframe.py tests/test_google_sheets_read_dataframe.py tests/test_google_workspace.py tests/test_smoke.py tests/test_runtime_guard.py tests/test_sql_safety.py` with `--no-cov -p no:randomly`: 209 passed.
- Gate 3 (docs): docstrings for `read_dataframe` and `write_dataframe`; the three #1432 entries in `CHANGELOG.md` `[4.1.0]` `### BREAKING` (each with Migration), mirrored exactly in the PR body block.
- Notebook impact (SU-4a): only `notebooks/archive/18_Google_Workspace.ipynb` calls these functions (`write_dataframe(..., sheet_name=...)`, `read_dataframe(client, spreadsheet_id, "'DataFrame Tab'")`). Both calls are compatible: the new parameter is a trailing keyword with the existing RAW default, and the tab it reads is rectangular.

## Lead review (adversarial)
Phase A coherence: item 1 maps to the new parameter and its validation; item 4 maps to `_pad_ragged`; items 2 and 3 are unchanged from the PR head.
Phase B verification (14 new tests):
- Against `v4.0.0` `google_sheets.py`: 10 failed / 4 passed. The 4 passes are the controls (rectangular sheet, header-only sheet, empty sheet, `has_header=False`).
- Against PR head `6990023b`: 9 failed / 5 passed (the RAW-by-default test also passes there, as the PR already hard-coded RAW).
- After the fix: all pass; 209 in the focused run.
- Composition: `read_dataframe` still delegates to `read_values`; the tests mock only the Sheets service, so `read_values`, `read_dataframe` and `_pad_ragged` run for real.

## Findings
| ID | Priority | Description | Resolution |
|----|----------|-------------|------------|
| F1 | P1 | #1432 item 4 (ragged read) not implemented | `_pad_ragged`; 4 failing-then-passing tests plus 4 controls |
| F2 | P2 | #1432 item 1 not met literally (no parameter) | `value_input_option="RAW"` keyword |
| F3 | P1 | Invalid option would clear the tab before failing | validation precedes the clear; tested |
| F4 | P2 | PR body: "Refs", Fixed, `[Unreleased]`, local interpreter path | body: "Fixes #1432", BREAKING + Migration, item-to-test map, hygiene |

## Ticket-fitness exemption

writing-rules:4 exemption for the governing ticket.

### #1432
- **Reason:** #1432 predates the canonical ticket template. It uses Problem / Evidence / Failure scenario / Done when / Assumptions / Falsifier sections.
- **Evidence:** the four defects, the v4.0.0 probe and the acceptance criteria are in the #1432 body. The investigation, pre-mortem and Junior/Senior review are at https://github.com/siege-analytics/siege_utilities/issues/1432#issuecomment-6761234802.
- **Falsification:** restore `siege_utilities/analytics/google_sheets.py` from `v4.0.0`. Then `tests/test_google_sheets_read_dataframe.py::test_data_row_longer_than_header_extends_header` fails with `ValueError: 2 columns passed, passed data had 3 columns`, and `tests/test_google_sheets_write_dataframe.py::test_identifier_strings_are_sent_raw_by_default` fails on `USER_ENTERED`. Verified on 2026-11-10.

## Test plan / Quantified claims
Interpreter: local Python 3.11.11, run from the repository root.
- Focused run as in Gate 2: 209 passed.
- New tests: 10 failed / 4 passed on `v4.0.0`; 9 failed / 5 passed on `6990023b`; 14 passed after.

## Rework ledger
- Pre-flight round, 2026-11-10: items 1 (second alternative) and 4 added; validation-before-clear added; body classification and acceptance map corrected.

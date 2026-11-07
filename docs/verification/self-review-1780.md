# Self-review: PR #1780 analytics/01 notebook truthfulness (#1661)

Review-Tier: C (notebook demonstrating credentialed connectors; a CI-governed notebook).

## Assumptions
Working as: software engineer (Junior) and analytics-platform tech lead (Lead).
Domain(s): software engineering (notebooks, GA4 Data API, Snowflake connector configuration).
Geospatial cross-cut: no.
Goal source: the #1661 problem statement. This round addresses two findings relayed by the coordinator for head 77d59159. First, the notebook documents `SNOWFLAKE_CONFIG_FILE` as YAML while the connector uses `json.load`, and the tests mock the factory. Second, the GA4 week window uses the host time zone instead of the property's. The branch was also CONFLICTING with develop.
Plan reference: docs/verification/self-review-1780.md#pre-mortem
Pre-author-inventory: docs/verification/self-review-1780.md#investigation
Investigate-artifact: docs/verification/self-review-1780.md
Pre-mortem-artifact: docs/verification/self-review-1780.md
Hostile-review-artifact: https://github.com/siege-analytics/siege_utilities/issues/1661#issuecomment-6257230288 (prior resolution review) and the coordinator-relayed findings recorded at https://github.com/siege-analytics/siege_utilities/issues/1661#issuecomment-6651717908. Exact-head re-review is pending; this is NOT a pass.
Project-contribution: a reader following the notebook can configure Snowflake with a file the connector actually loads, and GA4 weekly comparisons cover the property's real calendar weeks.

## Investigation
- `siege_utilities/analytics/snowflake_connector.py:99-120`: `_load_config` reads the file with `json.load` and applies `account`, `user`, `password`, `warehouse`, `database`, `schema` and `role`.
- `notebooks/analytics/01_connectors.ipynb` at 77d59159: the Prereqs and section 3 describe "a YAML config", and cell `c1` prints `config_file="snowflake.yaml"`.
- `tests/test_1661_notebook_connector_truth.py` at 77d59159: every Snowflake test patches `get_snowflake_connector` and writes `account: example` YAML, so the real loader never ran.
- Notebook cell `c2` at 77d59159 computes the window from `date.today()`. `siege_utilities/analytics/google_analytics.py:249-250` documents that GA4 dates are interpreted in the property's time zone, and the connector exposes no property-time-zone lookup.
- GitHub reported the branch CONFLICTING with develop dc7d3f76. The conflict was the Unreleased Fixed list (the PR's #1661 entry against develop's #1667 entry).

## Pre-mortem
1. Tiger (launch-blocking). Severity: P1. Silent fallback to host time. Mitigation: `GA_PROPERTY_TIMEZONE` is required on the GA path; an unset or unknown IANA name raises `ValueError` before any query; tests cover a property zone whose date differs from the host date in both directions.
2. Tiger (launch-blocking). Severity: P1. The Snowflake correction stays a text claim. Mitigation: the notebook carries a JSON example; `test_documented_snowflake_config_loads_through_the_real_connector` extracts it and runs it through the real `get_snowflake_connector` and `_load_config`, with only `execute_ddl`/`execute_query` patched.
3. Paper Tiger. Severity: P2. Existing notebook-truth tests break. Mitigation: a default `GA_PROPERTY_TIMEZONE` fixture, a patched `datetime.datetime`, and JSON configs; all 48 notebook tests pass.
4. Paper Tiger. Severity: P2. The develop sync drops the PR's #1661 entry. Mitigation: the merge keeps both entries (CHANGELOG diff vs develop: +15, the #1661 entry); the next commit moves #1661 under `[4.1.0]`.
5. Elephant. Severity: P3. Hosted CI drift (DuckDB 2.0, `gis.W001`) outside this PR. Disclosed in the PR body.

## Peer review (Junior: shelves, gates)
- Shelves: SU-1 (no silent host-time or fixture fallback); SU-2 (the documented config format matches the loader); tests exercise the real loader rather than a mocked factory.
- Gate 1 (syntax): pytest executed every edited notebook code cell and imported both test modules -> 48 passed; flake8 on the new test -> clean (the two style codes reported in `tests/test_1661_notebook_connector_truth.py` are on unchanged lines).
- Gate 2 (tests): pytest -> 306 passed (notebook-truth, calendar, temporal, notebook hygiene, capability coverage and changelog tests) on the post-merge tree.
- Gate 4 (notebook API): `tests/test_notebook_hygiene.py` and `tests/test_notebook_capability_coverage.py` pass.

## Lead review (adversarial)
Phase A coherence: finding 1 maps to the Prereqs, section 3, cell `c1` and the real-loader test. Finding 2 maps to cell `c2`, section 2 and the time-zone tests. The sync keeps both CHANGELOG sides.
Phase B verification: against the 77d59159 notebook, `tests/test_1780_property_tz_and_config.py` gives 6 failed and 1 passed (the same-zone control). After the change it gives 7 passed, and the full notebook selection gives 48 passed.

## Findings
| ID | Priority | Description | Resolution |
|----|----------|-------------|------------|
| F1 | P2 | Notebook documents YAML; connector loads JSON | JSON documented with example; real-loader test |
| F2 | P2 | GA4 window uses host date | `GA_PROPERTY_TIMEZONE` required; window computed in that zone |
| F3 | P3 | Branch CONFLICTING with develop | additive merge, both CHANGELOG sides kept; #1661 entry under `[4.1.0]` |
| F4 | P2 | Notebook leaves the Snowflake connection open (CodeRabbit 4498717759) | `try`/`finally: sf.disconnect()`; close tests on success and failure |
| F5 | P2 | Flat-traffic WoW test passes vacuously when every WoW is NaN (CodeRabbit 4498717788) | assert one WoW value before the zero check |
| F6 | P3 | Index-based cell helpers break when cells move (CodeRabbit 4498717770) | shared ID-based `tests/notebook_cells.py`, run in notebook order |
| F7 | P3 | `test_null_sessions_fail` duplicates the malformed test with a bare `ValueError` (CodeRabbit 4498717778) | removed |

## Ticket-fitness exemption

writing-rules:4 exemption for the governing ticket. The #1398 epic is context only.

### #1661
- **Reason:** #1661 predates the canonical ticket template. It is a free-form problem narrative without Context / Goal / Acceptance sections, a `/think` link or `## Assumptions`, so `evaluate-ticket.sh` does not accept it as written.
- **Evidence:** the problem (markdown cells promise live GA/Snowflake queries while the code only initialized connectors and always showed a fixture) and its done-when live in the #1661 body. The PR #1780 body's "Author exemption" section maps them to tests. Reviewer verdicts: https://github.com/siege-analytics/siege_utilities/issues/1661#issuecomment-6257230288. This round's records: https://github.com/siege-analytics/siege_utilities/issues/1661#issuecomment-6651717908.
- **Falsification:** revert the implementation (restore `notebooks/analytics/01_connectors.ipynb` from 77d59159). Then `tests/test_1780_property_tz_and_config.py::test_ga_window_uses_property_timezone_not_host_date[2026-10-12T03:00:00-America/Los_Angeles-2026-09-21-2026-10-04]` goes red, because the GA4 query asks for 2026-09-28..2026-10-11 from the host date instead of the property's previous weeks. `test_documented_snowflake_config_loads_through_the_real_connector` goes red because the notebook shows no JSON config. Verified on 2026-11-05: 6 failed and 1 passed against the 77d59159 notebook; 7 passed after.

## Test plan / Quantified claims
Interpreter: ~/.pyenv/versions/default_31111/bin/python (Python 3.11.11), snowflake-connector-python 4.3.0, run from `tests/` with `--rootdir=..`.
- `python -m pytest tests/test_1780_property_tz_and_config.py` -> 6 failed / 1 passed (77d59159 notebook); 7 passed (after).
- `python -m pytest tests/test_1780_property_tz_and_config.py tests/test_1661_notebook_connector_truth.py tests/test_1780_calendar_coverage.py tests/test_1780_temporal_boundaries.py` -> 48 passed.
- Adding `tests/test_notebook_hygiene.py tests/test_notebook_capability_coverage.py tests/test_release_process.py tests/test_user_config_export_changelog.py` -> 306 passed on the post-merge tree.

## Review round on 5242f95b (CodeRabbit comments 4308922911 and 4423908758)
- Malformed live results: `tests/test_1661_notebook_connector_truth.py` adds `test_malformed_ga_result_raises_in_processing` and `test_malformed_snowflake_result_raises_in_processing`. They cover GA empty rows, a missing `sessions` column, a missing `date` column, a null date and null sessions, plus Snowflake empty rows, a null date and null sessions. Each case runs the processing cell and asserts a `ValueError` whose message names the live source ("GA4 live query ..." / "Snowflake live query ..."), so neither the fixture nor incomplete totals are produced. All eight raise on the current notebook, so no notebook change was needed.
- Ruff SIM117: nested `with` blocks in both test modules are combined.
- Type hints: every test function and helper in both modules, including the nested `FixedDatetime.now`, `HostDate.today`, `HostDatetime.now` and `flat` helpers, now has parameter and return annotations; `ruff --select SIM117,ANN001,ANN201,ANN202,ANN206` passes.
- Tests: 314 passed (notebook-truth, property time zone, calendar, temporal, notebook hygiene, capability coverage and changelog).

## Review round on 599c1b96 (CodeRabbit comments 4498717759, 4498717788, 4498717770, 4498717778)
- **4498717759, Snowflake connection left open:**
  - Fix: cell `c3` wraps `execute_ddl` and `execute_query` in `try`/`finally: sf.disconnect()`, and section 3 says the connection is closed, also on failure.
  - `test_snowflake_connection_closes_after_the_query` asserts the call order `execute_ddl`, `execute_query`, `disconnect`.
  - `test_snowflake_connection_closes_when_the_query_fails` covers a failing `execute_ddl` and a failing `execute_query`. The error propagates and `disconnect` is called once.
  - The real-connector test spies on the real `disconnect` and asserts it was called with that connector.
  - Red: 4 failed against the 599c1b96 notebook.
- **4498717788, vacuous WoW assertion:**
  - Fix: `test_flat_live_traffic_reports_no_wow_change` asserts `len(wow) == 1` before the zero check.
  - Red: with flat traffic of 0 sessions, both weeks total 0 and the WoW is all NaN. The 599c1b96 test passed on it (vacuously); the new test fails at the length assertion.
- **4498717770, index-based cell helper:**
  - Fix: `tests/notebook_cells.py::run_cells` selects cells by nbformat `id` (`c1`, `c2`, `c3`, `c5`) and runs them in notebook order whatever order they are named in. It refuses unknown IDs (with the IDs named), non-code cells, and repeated IDs. Both test modules use it.
  - `tests/test_1780_notebook_cells_helper.py` covers the helper and that the four IDs stay code cells.
  - Red: with one markdown cell inserted at the top of the notebook, the 599c1b96 index-based tests gave 33 failed, 1 passed; the ID-based tests gave 34 passed.
  - The `exec` the reviewer's tools flag (S102) is the point of these tests: they execute the committed notebook's own source. The helper says so.
- **4498717778, duplicate malformed test:** `test_null_sessions_fail` is removed. Its three cases (empty rows, a null session, a null date) are covered by `test_malformed_snowflake_result_raises_in_processing`, which matches the message naming the live source.
- **Tests:**
  - #1661/#1780 tests, notebook hygiene, capability coverage and changelog: 319 passed.
  - The analytics/01 notebook still executes in the pure lane.
  - flake8 (127) and test hygiene are clean.

## Rework ledger
During the reorder check, the first cell insert was refused because the notebook had changed on disk since it was read (after a restore). The run that followed tested the unmodified notebook, so it was discarded. The insert was redone after re-reading the notebook, and the reorder results above come from the redone run.
Hosted CI at 5db3550b showed the real-loader test failing in the "geo without GDAL" lane with `ImportError: Snowflake connector not available`; that lane does not install the Snowflake SDK, and the real `SnowflakeConnector` refuses to construct without it. The test now calls `pytest.importorskip("snowflake.connector")` first, so it runs wherever the SDK is installed (all main test lanes) and skips elsewhere.
The first draft of the YAML assertion forbade the word "YAML" anywhere, which conflicted with the new JSON guidance that says YAML fails to load; it now targets the defective phrase "a YAML config".

## Assumptions
Working as: software engineer
Domain(s): software engineering
Geospatial cross-cut: no
Goal source: epic #1148 hostile-review 2026-08-19 flagged zoho connector as SU-4b-non-compliant; template from PR #1166 (salesforce) and PR #1169 (hubspot)
Goal source verification: TRIVIAL — ticket-based goal; evaluate-ticket.sh not present in this repo
Plan reference: session prompt (zoho-su4b subagent brief 2026-08-24)
Pre-author-inventory: NONE
Trivial-against-state: inputs-already-measured
Reason: read zoho.py source + existing test file before writing; all external state is the connector's error branches in that source file, inventoried in the same session turn
Evidence: `cat siege_utilities/connectors/zoho.py` and `cat tests/test_connectors_zoho_errors.py` read in this session before writing any new tests
Falsification: NOT trivial if the connector code was modified by another session between reading and committing; `git diff HEAD siege_utilities/connectors/zoho.py` returns empty (not touched)
Investigate-artifact: TRIVIAL (see declaration below)
Pre-mortem-artifact: TRIVIAL (see declaration below)
Hostile-review-artifact: /Users/dheerajchand/.craft-agent/workspaces/my-workspace/sessions/260824-wild-beaver/plans/hostile-review-zoho-su4b-2026-08-24.md
Project-contribution: closes the zoho gap in epic #1148 SU-4b CRM connector error-path coverage; pairs with PR #1166 (salesforce) and PR #1169 (hubspot)

## Trivial-investigation declaration

Category: local-only
Cannot produce error: this is a test-only addition; the investigation scope is the connector source file and existing test file, both read in the same session turn before writing
Evidence: `git diff HEAD -- siege_utilities/connectors/zoho.py` returns empty (no production code in diff); investigation consisted of reading zoho.py and the existing test file before writing
Falsification: NOT trivial if any production connector file appears in the diff; `git diff HEAD --name-only | grep -v "^tests/\|^plans/"` must return empty

## Trivial-premortem declaration

Category: local-only
Cannot produce error: test-only PR with no production code changes; worst case is a test that incorrectly passes (caught by code review) or a test that fails CI (no production impact)
Evidence: `git diff HEAD --name-only` shows only `tests/test_connectors_zoho_errors.py`
Falsification: NOT trivial if any non-test file appears in the diff

## Pre-implementation comprehension

1. **Current behavior**: `tests/test_connectors_zoho_errors.py` had 12 test items covering the basic HTTP status branches, constructor validation, and `_exchange_token` error paths. The `_ensure_connected` token-expiry branches, `_extract_error` fallback paths, `_exchange_token` 200-with-error-key path, write-operation API-error-status paths, and upsert empty/batch-error paths were uncovered.
2. **Intended behavior**: 26 test items covering all error branches in `zoho.py` that produce `ConnectorError`, `ConnectorAuthError`, `ConnectorNotFoundError`, or `ConnectorRateLimitError`.
3. **Steps**: read connector source, identify uncovered branches, adapt salesforce/hubspot template, add 14 new test functions, verify all 26 pass.
4. **Success criteria**: `pytest tests/test_connectors_zoho_errors.py --no-cov -v` → 26 passed; `flake8 --select=F401,F841,F541` → clean.
5. **What could go wrong**: Zoho's `_exchange_token` error-key path differs from the Salesforce shape — verified by reading source before writing test.

## Peer review

### writing-tests:1 (tests fail on revert + import module)
- File imports `from siege_utilities.connectors.zoho import ZohoConnector` — imports the module under test. PASS.
- Each test forces a specific branch in `zoho.py`; removing that branch would make the test fail. Verified per test in hostile-review artifact. PASS.

### writing-tests:2 (no cargo-cult)
- Tests adapted from salesforce/hubspot template but each new test is specific to Zoho's OAuth token-expiry flow, `_extract_error` static method, and write-operation error shapes. PASS.

### writing-tests:3 (skip messages)
- No `pytest.skip()` calls in file. N/A.

### writing-tests:4 (mock fidelity)
- `_FakeResp` exposes `status_code`, `json()`, `text`, `headers` matching `requests.Response` public surface.
- `_FakeSession.request()` returns the fake response without validating args — acceptable for error-path isolation. No `MagicMock` without `spec=`.
- `monkeypatch` used for `_session.post` on a real `requests.Session` instance. PASS.

### writing-tests:5 (every except exercised)
- `_exchange_token` except `RequestException` → `test_exchange_token_wraps_transport_error`. PASS.
- `_exchange_token` 200-with-error-key → `test_exchange_token_raises_when_error_key_in_200_response`. PASS.
- `request()` except `RequestException` → `test_request_retries_then_raises_on_request_exception`. PASS.
- `_extract_error` except `ValueError` → `test_extract_error_falls_back_to_text_for_non_json_response`. PASS.

### writing-code:12 (no duplicate imports)
- `grep "^import\|^from"` in the file: no duplicate import lines. PASS.

### writing-prose:1 (no AI typographic Unicode)
- No em-dashes, curly quotes, or other banned chars in docstring or comments. PASS.

## Lead review

**Approach fit**: test-only addition extending an established pattern (PR #1166, #1169). No source changes. Pattern matches the declared SU-4b remediation playbook.

**Blast radius**: zero — no production code modified.

**Sequencing assumption**: `develop` is the base; `test/zoho-su4b-http-coverage` branches from it. CI will run against the same connector source that tests reference.

**Standards held**:
- All 26 items pass: `~/.pyenv/versions/default_31111/bin/python -m pytest tests/test_connectors_zoho_errors.py --no-cov --override-ini="addopts=" -v` → 26 passed.
- Flake8 clean: `~/.pyenv/versions/default_31111/bin/python -m flake8 --select=F401,F841,F541 tests/test_connectors_zoho_errors.py` → no output.
- No source files modified: `git diff HEAD -- siege_utilities/` → empty.

## Findings

| ID | Priority | Description | Resolution |
|----|----------|-------------|------------|
| S3-1 | P3 | Fixture paths use /crm/v5/ not v6 | noted |
| S3-2 | P3 | _FakeSession doesn't validate outbound args | noted |

No P1 or P2 findings.

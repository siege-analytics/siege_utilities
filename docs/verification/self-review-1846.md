# Self-review: CRM connector cluster (#1846)

Scope: PR #1846 at work commit `681d28a5` (head `fce16051` is an empty marker
commit). This file adds the in-repo self-review and the ticket-fitness
exemption. It changes no connector code.

## Assumptions

Domain(s): software engineering (CRM connectors, credential redaction,
exception contracts).
Goal source: the eight linked tickets (#1417, #1425, #1426, #1427, #1428,
#1429, #1431, #1436) and the successive merge-gate reviews recorded in the PR
body, including the R-1846-7a retry_after amendment.
Base: merge base `7f534f6c` with develop; the branch is additive (no rebase,
force-push or merge).
Working as: software engineer (Junior) and tech lead (Lead); both reviews are
below.

## Peer review

- Redaction boundary: `_SecretRedactionMixin.__init_subclass__` wraps every
  public connector callable it enumerates, including `__init__`, coroutines,
  generators, async generators and property, classmethod and staticmethod
  descriptors. `tests/test_1846_r6_enumerate_boundary.py` checks the wrapping
  by enumeration.
- Strict short or failed credential policy: diagnostics carry a trusted
  constant (class name plus a validated HTTP status), never message text, and
  the logger emits the fixed constant whether or not the record has args.
- Metadata: one fail-closed read; a status is kept only when its type is
  exactly `int` in 100-599; a `retry_after` is kept only when its type is
  exactly `int` or `float` and it is non-finite or non-negative (R-1846-7a).
  Originals are never copied back onto the rebuilt error.
- Requests: the four connectors import `requests` inside
  `try/except ImportError`, set `REQUESTS_AVAILABLE`, and raise an actionable
  `ImportError` from the constructor when it is false.
- Request construction is unchanged, so outgoing bodies, headers and URLs are
  byte-identical.

## Lead review

The PR closes the credential-echo seams found by successive rounds of independent
review at one boundary rather than site by site. The remaining risks are
stated in the PR body: a constructor that inlines a caller-passed secret into
a pre-registration message is a documented limit, and an exact-head review of
`681d28a5` (including the R-1846-7a delta) is pending. The 30 scanner findings
at `fce16051` are listed in the PR body with a disposition each; none is a
reachable credential leak. No findings block this documentation commit.

## Ticket-fitness exemption

The eight governing tickets below were written before the current
evaluate-ticket structure (Problem / Evidence / Done-when / Falsifier
headings), which is the Reason for each exemption; it covers ticket structure
only. #1398 is the parent epic and #1463 is develop-sync context; neither is
governing, so neither has a revert run.

Revert runs (observed 2026-11-05, Python 3.11.11). Each ticket landed in one
implementation commit. Where reverting that commit at the head conflicts with
later rounds, the revert is taken at the point it landed: the tree of
`<impl>^` (`git archive <impl>^`) with the ticket's own test file from `<impl>`
overlaid, run with
`python -m pytest -o addopts="" --rootdir=.. -c ../pyproject.toml -p no:cacheprovider -q -p no:randomly <test file>`
from its `tests/` directory. Head counts are at `a69b4913`. Every failure
listed is an assertion or missing-raise on the ticket's behavior, not an
import or fixture error.

- **#1417** (non-idempotent retries, 429 handling, `$batch` failures).
  Node: `tests/test_1417_crm_retry_idempotency.py::test_non_idempotent_requests_are_sent_once`.
  Revert of `1451ede6` (tree of `1451ede6^`): 45 failed / 13 passed; the 16
  `test_non_idempotent_requests_are_sent_once` cases fail with
  `AssertionError: assert 3 == 1` (the POST is sent three times), and
  `test_dynamics_batch_propagates_auth_and_rate_limit[False-401-ConnectorAuthError]`
  fails with `DID NOT RAISE ConnectorAuthError`. Head: 59 passed.
- **#1425** (missing values in `to_crm_*`).
  Node: `tests/test_1425_crm_missing_values.py::test_missing_numeric_field_preserves_other_rows_and_zero[none-opportunities-probability-salesforce]`.
  Revert of `b90c7af6` (tree of `b90c7af6^`): 98 failed / 37 passed, with
  `ValueError: cannot convert float NaN to integer` (13),
  `AssertionError: assert nan is None` (9) and
  `TypeError: 'float' object cannot be interpreted as an integer` (5) among
  the observed errors. Head: 135 passed.
- **#1426** (Zoho lookup ids, probability scale, Dynamics industry).
  Node: `tests/test_1426_crm_canonical_mapping.py::test_zoho_get_objects_maps_lookup_ids[Deals-owner_id-owner-123-list]`.
  Revert of `7da4d233` (tree of `7da4d233^`): 17 failed / 10 passed; that node
  fails with `assert 'Owner Display Name' == 'owner-123'`, and the
  `account_id` cases with `assert None == 'account-456'`. Head: 27 passed.
- **#1427** (Dynamics `create_record` id).
  Node: `tests/test_1427_dynamics_create_record_id.py::test_create_record_returns_id_from_204_header[odata-entityid-opportunities]`.
  Revert of `69bdf6b9` (tree of `69bdf6b9^`): 16 failed / 18 passed; the
  header cases fail with `assert '' == '00000000-...-000000000001'`, and four
  missing-id cases with `DID NOT RAISE ConnectorError`. Head: 34 passed.
- **#1428** (Salesforce field casing and relationship paths).
  Node: `tests/test_1428_salesforce_getobjects_casing.py::test_clean_records_matches_each_segment_case_insensitively[name-Acme]`.
  Revert of `1c41d18c` (tree of `1c41d18c^`): 11 failed / 8 passed; that node
  fails with `assert [{'name': None}] == [{'name': 'Acme'}]`, and
  `test_clean_records_resolves_relationship_fields` fails. Head: 19 passed.
- **#1429** (pagination limits and continuation).
  Node: `tests/test_1429_crm_pagination.py::test_zoho_list_uses_page_token_after_2000_records`.
  Revert of `b93bbd67` (tree of `b93bbd67^`): 21 failed / 2 passed; that node
  fails with `KeyError: 'page_token'`,
  `test_zoho_coql_stops_and_truncates_at_limit` fails, and six cases fail with
  `DID NOT RAISE ConnectorError`. Head: 23 passed.
- **#1431** (authorization URL encoding).
  Node: `tests/test_1431_crm_authorization_url.py::test_authorization_parameters_round_trip`.
  Revert of `4ab25f3b` at the head (`git revert --no-commit 4ab25f3b`, test
  file and CHANGELOG restored from HEAD, then `git revert --abort`): 3 failed,
  one per provider, e.g.
  `{'client_id': ['client id']} != {'client_id': ['client+id&extra=value']}`.
  Head: 3 passed.
- **#1436** (token lifecycle).
  Node: `tests/test_1436_crm_token_lifecycle.py::test_salesforce_does_not_invent_expiry[None]`.
  Revert of `06a58628` (a head revert conflicts in all four connectors, so the
  tree of `06a58628^` is used): 76 failed / 8 passed; that node fails with
  `assert datetime(...) is None`, 32 cases with
  `AssertionError: Token clocks must use UTC`, and
  `test_dynamics_401_renews_delegated_credentials` fails. Head: 84 passed.

## Scanner dispositions (14 findings in this PR's diff hunks)

From `scan.sh --pr 1846` at `fce16051` (unchanged at `0c60517f` and after the
develop sync, which touches no connector file). Each is kept, with the
line-specific reason below; none is a reachable credential leak.

1. `writing-code-8` `requests` callsites `dynamics.py:832`, `:856`, `:945`,
   `hubspot.py:812`, `salesforce.py:1336`, `zoho.py:816` (6). Each module
   imports `requests` in `try/except ImportError` and sets
   `REQUESTS_AVAILABLE`; each constructor raises `ImportError` when it is false
   (`dynamics.py:147`, `hubspot.py:129`, `salesforce.py:318`, `zoho.py:172`).
   These callsites run only on a constructed instance, so the guard is at
   construction. Tracked in #1860.
2. `writing-code-7` `_protocol.py:342`, `:355`, `:362` (3). `except
   StopAsyncIteration: return` in the async-generator proxy ends the outer
   generator when the inner one is exhausted; letting it propagate would
   raise `RuntimeError` (PEP 525). Normal termination, not a swallowed error.
3. `writing-code-7` `_retry.py:60` (1). The inner `except (TypeError,
   ValueError, OverflowError): pass` runs after an HTTP-date parse fails;
   `delay` stays `None` and the code uses the computed backoff
   (`wait = ... fallback`), still raising `ConnectorRateLimitError`. Covered
   by `tests/test_1417_crm_retry_idempotency.py::test_retry_after_values_remain_typed_rate_limit_errors`.
4. `writing-code-7` `dynamics.py:677` (1). A non-integer `Content-ID` sets
   `invalid = True` before `continue`, and an invalid batch cannot report
   full success. Covered by
   `tests/test_1417_crm_retry_idempotency.py::test_incomplete_batch_response_cannot_report_full_success`.
5. `writing-code-7` `dynamics.py:768` (1). A non-JSON error body falls through
   to `_safe_upstream_detail(body)`, so the error still carries the status and
   a redacted detail. Covered by
   `tests/test_connectors_dynamics_errors.py::test_extract_error_falls_back_to_text_on_non_json`.
6. `writing-tests-5` `_http.py:69` and `_retry.py:23` (2). The scanner looks
   for name-matched `test__http.py` / `test__retry.py`. The `_http.py:69`
   handler (a log value provider that raises, so redaction fails closed) is
   exercised by
   `tests/test_1846_r4_runtime_sinks.py::test_logger_context_diagnostic_redaction`;
   `_retry.py` by `tests/test_1417_crm_retry_idempotency.py` and
   `tests/test_1846_connector_retry_cap.py`.

## Test plan

- At `fce16051`, Python 3.11.11: `tests/test_1846_r6_hostile.py` (136),
  `tests/test_1846_r7a_retry_after.py` (16) and the eight ticket suites above
  (384) ran as 536 passed, 0 failed.
- `scan.sh --pr 1846` at `fce16051`: exit 1, 30 findings, each listed with a
  disposition in the PR body.
- This commit adds one Markdown file, so syntax, import and notebook gates are
  N/A.

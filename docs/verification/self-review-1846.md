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

Artifacts for the per-call credential round (2026-11-11; details in that
section below):

Pre-author-inventory: https://github.com/siege-analytics/siege_utilities/pull/1846#issuecomment-6799717089 (the credential collector, both credential entry points and the shared header-name list, read before the change)
Investigate-artifact: https://github.com/siege-analytics/siege_utilities/pull/1846#issuecomment-6799717089
Pre-mortem-artifact: https://github.com/siege-analytics/siege_utilities/pull/1846#issuecomment-6799717089
Hostile-review-artifact: https://github.com/siege-analytics/siege_utilities/pull/1846#issuecomment-6800741041 (first fresh-context adversarial pass; second pass on the staged change: https://github.com/siege-analytics/siege_utilities/pull/1846#issuecomment-6801144147; third pass on the test file: https://github.com/siege-analytics/siege_utilities/pull/1846#issuecomment-6804929888; subclass round with its hostile re-check: https://github.com/siege-analytics/siege_utilities/pull/1846#issuecomment-6843497902)

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
- Per-call credential round (2026-11-11):
  - writing-code: collection only reads. The Dynamics send line is identical
    to `ec09ffa9`, and the credential-URL guard reports 0 unreviewed sites.
    The new broad handler is allow-listed (exception contracts: 215 flagged,
    0 unlisted, 0 stale).
  - writing-tests: 59 offline cases → 53 failed on `ec09ffa9` source, 59
    passed after (exit 0); PR selection plus `tests/guard` → 1999 passed.
  - writing-claims: every count is listed with its command under Quantified
    claims.
  - Syntax check: ruff on the six changed `.py` files → All checks passed.
  - Doc build: N/A. `docs/verification/` is outside the Sphinx source tree
    `docs/source/`.
  - Notebook API check: N/A (no notebook changes).

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

The falsifier for each ticket is the at-head control in the next section.
The entries below are historical context: they show each defect existed
before its fix, not that the current code still depends on the fix.

Historical revert runs (observed 2026-11-05, Python 3.11.11). Each ticket landed in one
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

## At-head controls (red on revert at 5edb9691)

Method, per ticket, in a clean worktree at `5edb9691` with the current tests:
hand-edit only that ticket's surviving implementation lines (no checkout of
pre-fix files, no archive), run the named node from `tests/` with
`python -m pytest -o addopts="" --rootdir=.. -c ../pyproject.toml -p no:cacheprovider -q -p no:randomly <file> -k <node>`,
restore with `git checkout HEAD -- <file>`, run the node again, and confirm
`git status --short` is empty. Observed 2026-11-05, Python 3.11.11.

- **#1417.** Reversed `siege_utilities/connectors/_retry.py:34` from
  `return max(1, configured) if method.upper() in {"GET", "PUT", "DELETE"} else 1`
  to `return max(1, configured)`. Node
  `tests/test_1417_crm_retry_idempotency.py::test_non_idempotent_requests_are_sent_once`:
  16 failed, all `AssertionError: assert 3 == 1` (the POST/PATCH is sent three
  times). Restored: 16 passed. Tree clean.
- **#1425.** Removed the branch
  `elif pd.api.types.is_scalar(value) and pd.isna(value): value = None` from
  `_normalize_crm_record` (`siege_utilities/connectors/_models.py:47-48`), which
  every connector's `to_crm_*` calls. Node
  `tests/test_1425_crm_missing_values.py::test_missing_numeric_field_preserves_other_rows_and_zero`:
  40 failed / 20 passed, including `AssertionError: assert nan is None` (9) and
  `ValueError: cannot convert float NaN to integer` (9), plus `int()` /
  `float()` `TypeError` on `NAType`; each is the conversion of a missing value.
  Restored: 60 passed. Tree clean.
- **#1426.** Reversed the body of `_lookup_id`
  (`siege_utilities/connectors/zoho.py:126-129`; reads `<field>_id`, else the
  raw lookup dict's `id`) to `value = record.get(field)`, the display value.
  Node `tests/test_1426_crm_canonical_mapping.py::test_zoho_get_objects_maps_lookup_ids`:
  6 failed (`assert 'Owner Display Name' == 'owner-123'` x2,
  `assert 'Account Display Name' == 'account-456'` x4). Restored: 6 passed.
  Tree clean.
- **#1427.** In the 204 branch of the Dynamics request path
  (`siege_utilities/connectors/dynamics.py:979-983`), removed the three lines
  that return `{"OData-EntityId": entity_id}`, so a 204 returns `{}` as before
  the fix. Node
  `tests/test_1427_dynamics_create_record_id.py::test_create_record_returns_id_from_204_header`:
  4 failed, each `ConnectorError: Dynamics create <entity> succeeded but
  returned no record id.` raised by `create_record` (the id is not read from
  the 204 header). Restored: 4 passed. Tree clean.
- **#1428.** In `_resolve_field`
  (`siege_utilities/connectors/salesforce.py:1182-1189`), replaced the
  exact-then-case-insensitive segment lookup with `value = value.get(segment)`.
  Node
  `tests/test_1428_salesforce_getobjects_casing.py::test_clean_records_matches_each_segment_case_insensitively`:
  5 failed, e.g. `assert [{'name': None}] == [{'name': 'Acme'}]` and
  `assert [{'account.Name': None}] == [{'account.Name': 'Parent'}]`.
  Restored: 5 passed. Tree clean.
- **#1429.** Replaced
  `if page_token: params["page_token"] = page_token else: params["page"] = page`
  (`siege_utilities/connectors/zoho.py:579-582`) with `params["page"] = page`.
  Node
  `tests/test_1429_crm_pagination.py::test_zoho_list_uses_page_token_after_2000_records`:
  1 failed, `KeyError: 'page_token'` raised by the test's own assertion
  (`tests/test_1429_crm_pagination.py:69`) because the request after record
  2000 carries no `page_token`. Restored: 1 passed. Tree clean.
- **#1431.** The head revert recorded above (`git revert --no-commit 4ab25f3b`,
  then `git revert --abort`): 3 failed, then 3 passed.
- **#1436.** Reversed `siege_utilities/connectors/salesforce.py:1274` from
  `self._token_expires_at = None` to
  `self._token_expires_at = datetime.now(timezone.utc) + timedelta(hours=2)`,
  the invented lifetime the fix removed. Node
  `tests/test_1436_crm_token_lifecycle.py::test_salesforce_does_not_invent_expiry`:
  3 failed, each `assert datetime.datetime(2026, 11, 5, ..., tzinfo=utc) is None`.
  Restored: 3 passed. Tree clean.

No fix needed isolation work beyond these lines; each surviving implementation
was present at head and reversible on its own.

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

## Review-thread round (19 unresolved threads at 83217c36)

No develop resync: the PR was MERGEABLE against develop 71f02b0b, and the
brief merges develop only for a real conflict.

Fixed in this commit (red at 83217c36, green here):

- `RedactingLogger.log` passes `stacklevel + 1`, so records keep the real
  caller's path, line and function. `_render` mirrors stdlib logging: a
  single mapping argument formats `%(name)s` templates, and a mismatched
  template logs the template plus a "could not be formatted" marker instead
  of raising into the caller. The unrendered arguments are never emitted.
  The new handler is allow-listed with its rationale.
- HubSpot `hs_deal_stage_probability` scales in `Decimal`
  (`float(Decimal(str(float(p))) * 100)`): `0.29` gives `29.0`, not
  `28.999999999999996`. The inner `float()` keeps the existing `ValueError`
  for non-numeric input.
- `_QUOTED_SECRET` body is `(?:\\.|(?!(?P=quote))[^\\])*`, so a backslash
  can only be consumed as an escape. 60 backslashes in an unterminated value
  previously never returned (the subprocess control times out at 20 s); now
  they return at once. Escaped quotes are still redacted in full.
- HubSpot and Zoho token errors with a non-object JSON body (list, string,
  number) raise `ConnectorAuthError`; before, `body.get` raised
  `AttributeError`.
- `UpsertResult.redact` is an `InitVar` kept as `_redact`, not a dataclass
  field, so `fields()`, `asdict()`, equality and `deepcopy` never carry the
  bound connector. `__deepcopy__` deep-copies the data and shares the
  redactor. The 11 constructor call sites are unchanged.
- The shared CRM factories moved to `tests/crm_connector_factories.py`
  (typed; an unknown provider now raises instead of building Dynamics). The
  14 importing suites were repointed. Three round-named files were renamed to
  behaviour names, and their docstrings no longer name review rounds or
  internal paths:
  `test_crm_short_credential_and_result_redaction.py`,
  `test_crm_configured_secret_echo_redaction.py`,
  `test_crm_api_key_and_client_secret_redaction.py`. Network and sleep
  controls stay local to each suite.
- Test annotations were added on every function the threads named. The
  `request_raw` rate-limit test now asserts `ConnectorRateLimitError` and
  exactly two sends.

Red control: the five source files were reverted to 83217c36 with the new
tests kept, giving 19 failed and 4 passed. The 4 that passed are guards that
must hold on both sides: escaped-quote redaction (2), probability `"1"`, and
the non-numeric `ValueError`. The fixes were then restored.

Already addressed (no change): the four CHANGELOG `SparkEngine.nearest`
threads were raised against superseded text. The entry is now develop's own
#1463 text (73b74f80), and its claims match
`siege_utilities/engines/dataframe_engine.py`: `index_right` rejected (:1866),
duplicate output names rejected (:1889), per-point row identity with no
checkpoint (:1902-1904). `tests/test_1463_sparkengine_nearest_rowid.py`
covers each claim. `docs/verification/crm-1846-r2.txt` was deleted at
2be5861e.

BREAKING classification: none of these changes alters working v4.0.0 caller
code. The non-object token-error path crashed with `AttributeError` in
v4.0.0. `RedactingLogger`, `_QUOTED_SECRET` and `UpsertResult.redact` do not
exist in v4.0.0. HubSpot probability scaling is already under BREAKING
(#1426); its entry now states the exact decimal result.

Verification at this commit (Python 3.11.11): 37 #1846 test files plus
`tests/guard` gave 2369 passed. The suite-wide sweep
`-k "connector or crm or redact or secret or http or credential"`, excluding
the two GeoDjango-only collection files, gave 4968 passed and 33 skipped. The
exception-contract guard reports 0 unlisted and 0 stale. Credential-URL guard
0; secret-literal and secret-repr guards 0; test-file hygiene PASS; ruff clean
on the new and rewritten files.

## CI flake at 4b6666f1 (run 42751381586)

One failure: `tests/test_1417_crm_retry_idempotency.py::test_retry_after_values_remain_typed_rate_limit_errors[date]`,
`assert sleep.call_count == 1` failing with 363. The test and the connector
were unchanged from 83217c36, whose run passed. The suite's autouse fixture
replaced the process-wide `time.sleep` with a `Mock`, so sleeps from any other
thread in the CI process were recorded as retry waits. This is a test defect,
not a connector one.

Fixed for the whole class, not just the one test.
`tests/crm_connector_factories.py::record_test_thread_sleeps` records (and
skips) only the calling thread's sleeps; other threads sleep for real. The four
suites that assert on sleep calls use it: `test_1417_crm_retry_idempotency`,
`test_1846_connector_retry_cap`, `test_1846_connector_bulk_auth` and
`test_connector_upsert_sanitization`. Suites that only silence sleeps were not
changed.

Red/green: `test_background_thread_sleeps_are_not_counted_as_retry_waits` runs
one 429 retry while a background thread loops on `time.sleep`. With the old
process-wide mock it fails ("Called 25485 times"); with the recorder it
passes. The #1846 set plus `tests/guard` gives 2370 passed.

## Per-call credential round (2026-11-11, on head `ec09ffa9`)

Goal source: independent review of head `ec09ffa9` found that credentials
supplied per call were outside the diagnostic redaction context. The
investigation, pre-mortem and checklist were posted before the change:
https://github.com/siege-analytics/siege_utilities/pull/1846#issuecomment-6799717089

Gap (read in the `ec09ffa9` source): `_secret_values` collected only the
instance's configured credentials and the session `Authorization` /
`X-Api-Key` headers. `DynamicsConnector.request(headers=...)` sends a
caller's per-call headers, and `authenticate_with_code` in HubSpot,
Salesforce and Zoho sends `code` to the token endpoint. An upstream echo of
either, without key or `Bearer` syntax, reached exception text and log
records.

Change:

- `_protocol.py`: a context-local per-call credential scope. The sync and
  coroutine public boundaries open it on the outermost public call; nested
  public calls (token refresh, `request` inside a read method) reuse it. It
  closes only after the boundary has sanitized the exception, then the
  sanitized exception is raised. `_secret_values` includes its values, and a
  failed collection returns the existing fail-closed signal. The existing
  short-credential rule then applies unchanged: a registered value under 8
  characters leaves only the trusted constant.
- `_register_request_headers` copies the caller's mapping once with
  `dict(headers)` (the same read the send path uses) and registers the values
  of recognized credential headers from that copy: the names `core/_http.py`
  already redacts by key, matched case-insensitively and ignoring surrounding
  whitespace, as text or bytes. It also registers the credential after an
  auth scheme (any whitespace), and both the latin-1 and UTF-8 decodings of a
  bytes value. Names, values and codes are copied to exact `str` first, so a
  `str` subclass's own methods never run during registration. Other headers,
  and a `None` value (which requests drops), are not registered. A mapping
  that cannot be copied, a header name that is not text or bytes, or a
  credential value that is not text or bytes fails closed for the rest of the
  call. Its broad handler and its `None` return are allow-listed with that
  rationale.
- `DynamicsConnector.request` registers its `headers` and sends that same copy
  on every attempt, so the values sent are the values registered; for a
  mapping that returns the same values on every read, the bytes sent are
  unchanged. The send line itself is unchanged. Each `authenticate_with_code`
  registers `code`; the form payload is unchanged. The values are dropped when
  the outermost call ends.

Limits:

- Generator and async-generator public methods do not open their own scope
  (their nested public calls do). An asyncio task spawned inside a public
  coroutine would share the caller's scope and keep it after the caller
  returns, and a coroutine closed from another context could fail its scope
  reset. None of the four CRM connectors defines a public generator, async
  generator or coroutine. A test fails if one is added, so this design must be
  revisited first.
- A thread started inside a call does not inherit the scope; none of them
  starts threads.
- Values registered by a nested call on another connector instance also
  redact the outer call's diagnostics (over-redaction only).
- `Dynamics.request` now reads `headers` once per call rather than once per
  attempt. A mapping that returns a different credential on each read sends
  the first one on every attempt.
- Only the whole value of a `Cookie` header is registered, not each cookie;
  the base64 text of `Basic` credentials is registered, not its decoded
  `user:password`. Credential headers outside the shared name list (for
  example `Ocp-Apim-Subscription-Key`) are not recognized.
- `raise sanitized from None` keeps the boundary frame in the traceback, and
  that frame's arguments hold the raw values. A reporter that captures frame
  locals can show them. The caller's own frame and `self` already hold them,
  so this is a residual and not new.

## Independent adversarial pass (fresh-context reviewer, 2026-11-11)

A fresh-context reviewer was given the review finding, the source and the
mechanism description (not this review's conclusions). It ran no code. Its
findings and the dispositions:

1. Medium: a `bytes` header name (`b"Authorization"`) was skipped without
   failing closed, although requests sends it. Fixed: bytes names are decoded
   and matched, and any other non-text name fails closed.
2. Low: registration read `items()` while each send read `dict(headers)`, so
   a mapping that mints values, or a `dict` subclass that overrides `items()`,
   could send a value never registered. Fixed: one copy is registered and
   sent.
3. Low: `Bearer<TAB><token>` registered only the raw string. Fixed: the
   scheme split uses any whitespace. Cookie pieces, decoded `Basic`
   credentials and unlisted credential header names are recorded as limits
   above.
4. Low: `headers={"Authorization": None}`, the requests idiom for dropping
   the session header, marked the call failed and suppressed every
   diagnostic. Fixed: a `None` value is skipped.
5. Low, residual: frame locals in the traceback (limits above).

It also checked these and found them sound: the reset in `finally` on
return, `Exception` and `BaseException`; nested refresh/replay sharing the
scope; re-entrant secret getters failing closed; registration always running
inside a boundary; emit-time log redaction; unchanged outgoing bytes; and
bounded, de-duplicated values.

A second fresh-context pass reviewed the staged change (diffs and mechanism
description, not this review's conclusions):
https://github.com/siege-analytics/siege_utilities/pull/1846#issuecomment-6801144147
A tooling restriction stopped it early, so it did not review the new test
file; its findings come from the source diffs only.

1. Medium, latent: generator and async-generator boundaries open no scope.
   No such public method exists; a new structural test fails if one is
   added (limits above).
2. Low: a `str` subclass credential could run its own `__len__`/`__eq__`
   during registration, outside the fail-closed guard. Fixed: values are
   copied to exact `str` first.
3. Low: asyncio tasks spawned by a public coroutine share and outlive its
   scope. No public coroutine exists; covered by the structural test and
   limits.
4. Low: a coroutine closed from another context could fail its scope reset.
   Same as 3.
5. Low: a UTF-8 credential sent as bytes and a header name with trailing
   whitespace were missed. Fixed. Separate cookies and decoded `Basic`
   credentials stay limits.

It found the short-value constant-only behaviour correct and bounded to the
caller's own outermost call.

A third fresh-context pass reviewed the test file itself (with the changed
and previous source):
https://github.com/siege-analytics/siege_utilities/pull/1846#issuecomment-6804929888
It confirmed that each echo test fails on `ec09ffa9` for the stated reason
and that the echoed text reaches the message. Its findings:

1. Medium: the nested-refresh test could not tell whether the nested call
   reuses the outer scope. Fixed: the refresh stub records the redaction set
   inside the nested call. A temporary mutation giving every public call a
   fresh scope failed exactly this test (1 failed, 58 passed), and the
   source was restored (sha256 re-checked).
2. Medium: Zoho's HTTP 200 `error` token path had no code-echo test. Added.
3. Low: boundary tests now also assert ordinary text and no `__cause__` /
   `__context__`.
4. Low: lifetime tests now prove registration during the call, and a test
   shows short-value and failed-collection suppression end with their call.
5. Low: added a log test for a short per-call value.
6. Low: added raw, percent-encoded and form-encoded echoes of a value with
   `/`, `+` and `=`.
7. Low: added a non-text authorization code and a non-text credential header
   value (both fail closed).
8. Low: no-context assertions (with 3).
9. Low: the replay test is kept; it still checks identical headers on both
   attempts.

No source file changed for the third pass.

Tests (`tests/test_crm_invocation_credential_redaction.py`, 59 cases,
offline, stub transports, no live auth and no MSAL install):

- Anonymous echoes of a per-call `Authorization` (`Bearer`, lowercase
  `bearer`), `Proxy-Authorization` (`Basic`) and `X-Api-Key` value on 400, 401
  and 403 are absent from `str`, `repr` and the traceback, and the ordinary
  upstream text is kept. Also covered: an exception raised by the transport at
  the public boundary, a log record emitted during the call, a replay after a
  503, and the nested token refresh after a 401.
- An OAuth code echoed by the HubSpot, Salesforce and Zoho token endpoints,
  or raised at the boundary, is absent; the form payload still carries it.
- A short per-call credential or code, and a header mapping that raises
  while being read, leave only the trusted constant.
- Positives: configured and session credentials are still redacted alongside
  a per-call header; a non-credential per-call header, or a `None` header
  value, does not suppress the ordinary message; the values are registered
  during the call and gone after it returns or raises.
- Header shapes from the independent pass: a bytes header name, a tab after
  the scheme, a bytes value, and a mapping that returns a new credential on
  every read (both attempts send the same registered value).
- Shapes from the second pass: a `str` subclass header value and
  authorization code whose own methods raise; a header name with trailing
  whitespace; a non-ASCII credential sent as UTF-8 bytes. A structural test
  checks that none of the four connectors defines a public generator, async
  generator or coroutine.

Red/green:

- On the `ec09ffa9` source: 53 failed and 6 passed. Each failure was the
  per-call value or code appearing in the exception or log text, missing
  from the redaction set during the call, or a fail-closed constant that the
  old source did not produce. The 6 that passed are the structural test (4
  connectors) and two ordinary-message positives, which must hold on both
  sides.
- With the first version of this change, the four tests added for the first
  pass's findings 1-4 failed (bytes name, tab, minting mapping, `None`
  value).
- With the staged version before the second pass, exactly the six tests for
  its findings 2 and 5 failed and the other 43 of the then 49 passed.
- With the nested-scope reuse deliberately broken, only the nested-refresh
  test failed.
- With the final change, 59 passed.

These runs put the source files back to `ec09ffa9` and to each earlier
version with the tests kept, then copied the final files back and checked
their hashes.

## Subclass collection round (2026-11-13, on head `bffee49e`)

Goal source: the reviewer's disposition of head `bffee49e` retained the hold
for one source-derived residual, not an executed leak. A `bytes` subclass
whose buffer holds the real token can override `decode()` to return an
ordinary shadow value. Registration then recorded the shadow text while the
transport sent the real buffer, so a neutral echo of the complete token
reached a 400 detail or a connector log unredacted.

Change (supersedes the "copied to exact `str` first" description above):
only exact `str` and `bytes` header names, credential values and OAuth codes
are collected, through their builtin methods. A subclass can override
`decode`, `encode` or other methods the transport calls when it sends the
value (http.client encodes text header values; urlencode encodes form
values). So what is sent cannot be known from the object, and any subclass
fails closed to the trusted constant for the rest of that call. Its own
methods never run during collection, and it is still sent unchanged. This
does not claim that one builtin call recovers what an overridden name,
`encode` or buffer would send. It refuses to guess.

Tests (65 cases in the file, 6 new or changed):

- The reviewer's case through the public `request`: a `bytes` subclass with
  a shadow `decode()`, a neutral complete-token echo in the 400 detail and in
  an in-call connector log, the constant-only message, and the sent object
  and buffer unchanged.
- A `str` value with a shadow `encode()`, and a header name that encodes as
  `Authorization`.
- An OAuth code whose `encode()` yields the real code (all three providers).
- The two earlier `str`-subclass tests now expect the constant-only result
  instead of ordinary detail. Exact `str` and `bytes` positives still keep
  ordinary detail.

Red/green on `bffee49e` source: 10 failed and 55 passed.

- 6 failures are causal: the per-call token or code is present in the
  exception text. That covers the shadow-decode `bytes` value, the
  shadow-encode `str` value and name, and the shadow-encode code (×3).
- 4 are the changed expectations for the earlier `str`-subclass tests (×1
  header, ×3 code). The old source already redacted those tokens; it fails
  only on the new constant-only assertion.
- With the change, 65 passed. Restored control: `_protocol.py` put back to
  `bffee49e` with the tests kept gave the same 10 failures. The change copied
  back (sha256 8cf9c83c) gave 65 passed.

Limits:

- A caller passing a `str` or `bytes` subclass now gets constant-only
  diagnostics for that call, bounded by the existing lifetime tests. This
  includes a subclass used as an ordinary header name (for example a
  `StrEnum` member as `Content-Type`), because a name could encode as a
  credential header.
- Credentials configured on the connector (constructor values such as an
  access token or client secret) are still collected with `isinstance(...,
  str)`. A subclass there could format or encode to a value other than the
  one registered. That path is outside this per-call round and is recorded,
  not changed, here.

A fresh-context hostile re-check of this round's diff found no high or medium
issue. It noted one test compared the sent headers with `==`, which could not
detect a swapped plain-`str` copy; that test now checks identity. It also
noted the two limits above.

## Count and test-name qualification (2026-11-11)

- Scanner disposition 6 above names `test__http.py` and `test__retry.py` only
  as the file names the scanner's name-match heuristic looks for. No files
  with those names exist and none ran; the exercising tests are the
  differently named files listed there.
- The counts "37 #1846 test files plus `tests/guard` gave 2369 passed" and
  "2370 passed" above are historical. The original file selection, command
  and log were not retained, so they are unverified and are not relied on for
  the current head. They are not claimed to be wrong.
- Current reproducible selection: the 34 `tests/test_*.py` files this PR adds
  or modifies relative to develop
  (`git diff --name-only --diff-filter=AM 79f37f4d...HEAD -- tests/`), plus
  `tests/guard`. The `ec09ffa9` tree gave 1940 passed (recorded in that merge
  commit). With this round's new file, the 35 files plus `tests/guard` give
  1999 passed.

## Quantified claims

- 59 new test cases: 53 failed / 6 passed on `ec09ffa9` source, 59 passed on
  the final: `python -m pytest --no-cov -q tests/test_crm_invocation_credential_redaction.py`.
  Earlier control runs used the file at 49 cases (6 failed / 43 passed on
  the version staged before the second pass). The nested-scope mutation
  failed 1 of 59.
- 34 PR test files: the `git diff --name-only --diff-filter=AM` command above,
  filtered to `tests/test_*.py` (34 lines).
- 1999 passed: those 34 files, the new file and `tests/guard`.
- Sweep `-k "connector or crm or redact or secret or http or credential"`:
  5185 passed, 33 skipped, 0 failed. `tests/test_boundary_manager.py` and
  `tests/test_rdh_precinct_loader.py` did not collect (GeoDjango needs GDAL,
  which this environment lacks), so they did not run.
- Exception-contract guard: 215 handlers flagged, 0 unlisted, 0 stale.
  Credential-URL guard 0 unreviewed sites; test-file hygiene PASS; ruff clean
  on the six changed Python files.
- First independent pass: 5 findings (1 medium, 4 low); 4 fixed in this
  round, and the residual and partial items recorded as limits.
- Second independent pass: 5 findings (1 medium latent, 4 low). Findings 2
  and 5 (in part) are fixed. Findings 1, 3 and 4 are enforced by the
  structural test and recorded as limits.
- Third independent pass (test file): 9 findings (2 medium, 7 low); 8
  addressed with test changes, and the replay test kept as is.
- Subclass round (2026-11-13), Python 3.11.11:
  - New file 65 cases: 10 failed / 55 passed on `bffee49e` source (6 causal
    missing-token, 4 changed constant-only expectations), 65 passed final.
  - The 34 PR test files, the new file and `tests/guard`: 2005 passed.
  - The sweep (same `-k`): 5235 passed, 6 skipped, 1 error. In this run GDAL
    was available, so the two GeoDjango files collected. The one error is
    `tests/test_rdh_precinct_loader.py::TestPrecinctLoading::test_discovers_requested_year_and_office[2024-g24sosidoe-secretary_of_state-IND-DOE]`
    (matched by `secret`). It needs a local Postgres role `postgres` that does
    not exist: environment setup, not run successfully, unrelated to this
    diff.
  - Exception contracts 215 flagged, 0 unlisted, 0 stale; credential-URL
    guard 0; test-file hygiene PASS; ruff clean.

# Credential URL redaction verification

This forward fix addresses the five required changes in
[issue #1400's independent review](https://github.com/siege-analytics/siege_utilities/issues/1400#issuecomment-6134848943).
The base is 58f7ac2d. The v4.0.0 regression baseline is 9c3463b1.

`files/remote.py` redacts download start/success, SSL retry, retry-attempt,
filename-validation, HEAD metadata, malformed-header, and downloadability
messages. HTTP failures and transport/stream exceptions are sanitized, including
the SSL fallback. Transport exceptions are fresh objects raised outside their
handlers. Retry exhaustion chains only a fresh, sanitized error. Returned file
metadata still contains the original URL; it is redacted when logged.

TAMU retains its existing query authentication because the
[v4.01 HTTP documentation](https://geoservices.tamu.edu/Services/Geocode/WebService/v04_01/Simple/HTTP/)
does not establish support for credentials in a POST body. Its terminal private
request failure is a fresh RuntimeError with redacted diagnostics, raised outside
the handler. The batch warning also redacts independently. Retry counts and
unmatched-result behavior are preserved. No live authenticated request was made.

The shared redactor adds apikey, api_key, secret, x-amz-signature and auth.
Matching is case-insensitive and percent-decoded; existing key, password,
access_token, token, sig and client_secret coverage remains.

RDH download failures retain their exception type but discard the original
request, response and context. Listing failures keep the existing ConnectionError
type and are raised outside the handler. The shared diagnostic assertion walks
cause/context, request/response URLs, urllib reason and JSON decoder document,
as well as messages, log arguments and formatted tracebacks. It covers Census,
RDH and Instagram. Census and Instagram parse failures also raise outside their
handlers to avoid retaining the original exception. Logging fixtures restore
client logger levels and enablement after Django configuration.

The blocking `test_no_unreviewed_credential_urls` scans every Python file in
`siege_utilities/` using `scripts/check_credential_urls.py`. The AST guard flags
literal/f-string sensitive query fields and urlencode dictionaries, including
assignment, update and alias forms. It requires a specific path, function and
expression exemption with a reason. Only the reviewed Census and TAMU query
construction expressions are exempt. Construction is conservatively flagged
without requiring proof of a diagnostic sink because HTTP libraries can expose
URLs in errors. This is a construction guard, not interprocedural taint analysis;
dynamically computed parameter names are outside its detection scope.

New regression tests in `tests/test_credential_url_leak.py`:

- `test_remote_download_error_redacts_token` (HTTP 403, transport, timeout,
  stream and SSL errors, with and without an initial SSL failure)
- `test_remote_download_success_redacts_token`
- `test_remote_retry_error_redacts_token`
- `test_remote_file_info_error_redacts_token`
- `test_remote_file_info_success_redacts_token`
- `test_remote_invalid_filename_redacts_token`
- `test_remote_is_downloadable_error_redacts_token`
- `test_remote_malformed_header_redacts_token`
- `test_tamu_request_error_redacts_api_key`
- `test_tamu_batch_warning_redacts_api_key`
- `test_redact_url_secrets_sensitive_parameters`

The existing RDH test adds HTTP 404 and checks detached exception objects. All
round-1 cases remain. `tests/test_credential_url_guard.py` tests the package scan,
allowlist specificity, each sensitive spelling in both construction forms,
dictionary mutations/aliases, and CLI failure followed by success on removal.

## Round 3 coverage

The redactor and independent guard also protect signature, x-goog-signature
and x-amz-security-token case-insensitively. Fragment fields use the same
redaction as query fields. Percent-encoded delimiters (%3F, %26, %23) and
separators (%3D) are recognized without decoding the surrounding diagnostic
text. Nonsecret outer fields no longer hide encoded nested URLs. Commas and
closing parentheses remain outside the redacted value.

The guard checks params= on HTTP method calls, including requests import
aliases, with the same dictionary assignment/update/alias tracking as
urlencode. Unresolved mappings require an exact expression exemption with a
reason. Function arguments remain unresolved even if another function assigns
a nonsecret dictionary with the same name. This conservative file-level scan
does not infer arbitrary function return values or perform control-flow analysis.

RDH's listing request (including the _auth_params assignment) and download
request have separate exemptions documenting query authentication, redacted
diagnostics, and fresh exceptions. Instagram's forwarding expression is also
reviewed. Twelve other existing forwarding expressions have explicit reasons
covering header authentication or public endpoint filters. These entries
document that caller-supplied secret query values are not sanitized by those
generic wrappers; they do not claim new redaction coverage there.

With the round-3 tests retained and only core/_http.py restored to 63694f9a:

```text
pytest tests/test_credential_url_leak.py --no-cov -q -k redact_url_secrets
74 failed, 61 passed, 69 deselected
```

With only scripts/check_credential_urls.py restored to 63694f9a:

```text
pytest tests/test_credential_url_guard.py --no-cov -q -k 'injected or tracks_query or unresolved_params'
44 failed, 40 passed, 4 deselected
```

Both commands exit 1 on behavioral assertions. Restoring the implementation
passes the leak, guard, and remote-error suites: 298 passed. The _http cases
live in test_credential_url_leak.py. All prior leak scenarios remain covered.
The CLI tests verify exit 1 for sensitive params dictionaries, Signature
f-strings, and unresolved authentication helpers, then exit 0 on file removal.
Notebook impact is limited to private diagnostic handling; no public contract
changes or direct notebook callers of core._http were found.

Rebase onto develop at 154589e9 retained the #1641 _force_log_capture fixture
unchanged. The client logger fixture depends on it and no longer overrides
the root DEBUG capture with INFO. The conflict was confined to these fixtures;
the remaining round-2 and round-3 changes replayed unchanged. Forcing a
CRITICAL root level and logging.disable(CRITICAL) before every leak test still
passes all 204 cases.

After rebase, the full affected-client command below passes 577 tests in a
clean detached worktree. The original worktree again produced six PyArrow
duplicate filesystem registration errors, with 571 tests passing; the clean
worktree used identical source and the same pinned interpreter. Lint ratchet
phases 1-4, test file hygiene and the blocking I/O checks pass.

## Reproduction and results

All pytest commands used `/Users/dheerajchand/.pyenv/versions/default_31111/bin/python`
with `-m pytest` and `--no-cov`. Network failures use sentinel credentials and
real requests/urllib exception classes. requests-mock is installed.

Copy the current leak test to a detached v4.0.0 worktree, then run:

```sh
python -m pytest tests/test_credential_url_leak.py --no-cov -q -k 'remote or tamu'
```

Result: `24 failed, 60 deselected`. All failures are secret-present assertions,
not imports or missing dependencies. The narrower required download/TAMU
request selection gave `13 failed, 69 deselected` before the additional cases.

An actual `siege_utilities/geo/providers/_injected_leak.py` containing an
access_token f-string URL, an exception warning and a chained exception caused
`test_no_unreviewed_credential_urls` to fail with the injected path and line 2.
After removing that file, the package guard passes. The test suite includes the
same failure/removal proof for the CLI and parametrized construction variants.

Final focused check:

```sh
python -m pytest tests/test_credential_url_leak.py tests/test_credential_url_guard.py --no-cov -q
```

Result: `127 passed` in the requested worktree.

Full affected-client check, using an identical copy of the changed Python files
in a detached worktree:

```sh
python -m pytest tests/test_credential_url_leak.py tests/test_credential_url_guard.py \
  tests/test_files_remote_errors.py tests/test_files_canonical_contracts.py \
  tests/test_tamu_batch.py tests/test_redistricting_data_hub.py \
  tests/test_analytics_instagram_errors.py tests/test_census_api_client.py \
  tests/test_census_api_key_warning.py tests/test_census_cache_backend.py \
  tests/test_dual_source_1375.py tests/test_review_fixes.py \
  tests/test_round5_class_hardening.py --no-cov -q
```

Result: `412 passed`. In the original worktree, the first combined run had
`402 passed, 6 failed`; all six failed in PyArrow with duplicate filesystem
factory registration for scheme 'file'. The same full source passes in the
clean worktree. The unchanged round-1 baseline's Census/review suites also pass
there (80 tests). No cache tests were weakened or skipped. Existing Shapely and
RDH finalizer warnings remain unrelated to URL redaction.

Changed Python files pass AST parsing and the blocking/severe/unused-name
flake8 selections. Notebook impact: public signatures, return shapes and
exception types are preserved. Archived remote examples catch the same error
types; the changed private TAMU method has no direct notebook callers.

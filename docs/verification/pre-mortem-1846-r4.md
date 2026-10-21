# Pre-mortem — siege-analytics/siege_utilities#1846 B2 round 4 (credential redaction)

Reviewer-directed (hub FINAL, re-review FAIL @a9f772d8) D1-D5 forward-fix on
fix/crm-cluster-1. Value-aware redaction at every UpsertError field and every
non-2xx, log, and auth diagnostic sink; short-credential auth suppression;
fail-closed secret collection; value replacement before truncation.

## Risks

### R1: over-redaction touching real request payloads
Severity: medium
Value replacement and path redaction could blank legitimate content or alter an
outgoing request. Mitigation: redaction runs only on diagnostic text (exception
messages and reprs, logs, UpsertError fields); no request-building code is
touched, so PreparedRequest bodies, headers, and URLs stay byte-identical. The
full connector and redaction regression set stays green (2166 passed).

### R2 (D3): short-credential auth suppression reverses a previously-blessed assertion
Severity: medium
D3 suppresses all upstream detail on the auth and token path when any configured
credential is shorter than the value-redactor minimum (it cannot be value-replaced
without blanking common short strings). This reverses the earlier
test_short_configured_value_is_not_redacted and the HubSpot non-JSON fallback test.
Mitigation: suppression is scoped to the five auth/token sinks only; general
request and batch paths keep self._redact so a secret-free body is still preserved
(proved by test_short_credential_preserves_general_path_detail). The reversal is
disclosed in the PR body with the old assertions quoted and D3 cited. Hub ruled the
reversal accepted.

### R3 (D5): secret leak via exception chain when secret collection fails
Severity: high
A caller-supplied header mapping can raise an exception whose text carries a secret.
Mitigation: _secret_values wraps collection in except Exception, returns a distinct
fail-closed sentinel built after the except (no raise chains the caught exception
into __context__), and _redact and _safe_upstream_detail emit trusted constants only
on that signal. The broad handler is registered in the exception-contract allowlist
(guard: 0 unlisted / 0 stale). Covered by the r4 fixture's header-ValueError case.

### R4: long secret survives body truncation (D4)
Severity: medium
A long secret echoed in an untruncated body could keep its prefix after a 200-char
cut. Mitigation: value replacement runs on the full text before truncation
(redact_secrets replaces values first); _extract_error returns self._redact(raw)[:200].
Covered by the r4 long-credential case.

## Launch readiness
Implementation may proceed. r4 fixture 96/96 green (red-first 76f/20p after D4);
exception-contract guard 0 unlisted / 0 stale; full connector and redaction set 2166
passed / 1 skipped / 0 failed after the two reviewer-blessed test reversals plus the
general-path preservation test. B2 closure is the reviewer's decision, not claimed here.

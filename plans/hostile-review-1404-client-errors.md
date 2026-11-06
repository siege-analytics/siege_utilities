---
ticket_refs:
  - siege-analytics/siege_utilities#1404: summarized in the self-review ticket comment
---

# Hostile review: #1404 / PR #1791 permanent 4xx retries

Reviewer: a separate read-only review agent (same model family as the implementer). The cross-family exact-head re-review by the independent PR reviewer is still required and is requested after push.
Scope: the uncommitted diff on top of the develop merge `78766d3c` (`api.py`, `tests/test_1404_census_dual_source_fallback.py`, `CHANGELOG.md`).

## Findings and dispositions

1. No blocker: `HTTPError` from `raise_for_status` always carries `response`; a hand-built one with `response=None` yields `status=None` and skips the early exit. The chained `getattr` is safe (`api.py` retry handler).
2. No blocker: `last_exception` is set before `break`, is a plain `CensusAPIError` for permanent 4xx, and its message passes through `redact_url_secrets`; `raise ... from None` drops the chain.
3. No blocker: the only other caller, `census_api_client.py:305`, forwards. `test_credential_url_leak.py::test_census_http_error_redacts_key` (403) checks only redaction, which survives. No other test pairs a non-429 4xx with five calls.
4. FOLLOW-UP, fixed: 408 retried five times but then raised a plain `CensusAPIError` with no fallback, unlike a transport timeout. 408 is now a `CensusServerError`, so it retries and falls back; it joins the 500/503/599 fallback test.
5. No blocker: the dual-source default `fallback_on` (`dual_source.py:398`) excludes plain `CensusAPIError`, so permanent 4xx still do not fall back.
6. FOLLOW-UP, fixed: `docs/CENSUS_DATA_GUIDE.md` now states that permanent 4xx are not retried and that 408 falls back.
7. FOLLOW-UP, not in scope: mapping 401/403 to `CensusAPIKeyError` predates this PR; mixed sequences (503s then a final 400) remain as before.

Verdict: no blockers.

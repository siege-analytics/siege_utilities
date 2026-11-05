# Self-review: PR #1794 Instagram paging origin boundary (#1439, refs #1833)

Review-Tier: C (credential-bearing request path; bearer token origin boundary).

## Assumptions
Working as: software engineer (Junior) and security-minded tech lead (Lead).
Domain(s): software engineering (analytics connectors, HTTP credential handling).
Geospatial cross-cut: no.
Goal source: exact-head review of 5255c7d3 on #1439 (issuecomment-6259586596), finding F1 (P1 security) and process item 2; contract source is the #1833 fix commit 47e78eef on fix/1833-instagram-paging-origin.
Plan reference: docs/verification/self-review-1794.md#pre-mortem
Pre-author-inventory: docs/verification/self-review-1794.md#investigation
Investigate-artifact: docs/verification/self-review-1794.md
Pre-mortem-artifact: docs/verification/self-review-1794.md
Hostile-review-artifact: docs/verification/self-review-1794.md (section Hostile review: reviewer F1 plus an own adversarial pass). Independent exact-head re-review of the pushed commit is pending; this is NOT a pass of this commit.
Project-contribution: closes the P1 credential-exfiltration seam the #1439 pagination work opened, so no Instagram request (first page or continuation) can carry the bearer token off the HTTPS Graph origin.

## Investigation
Investigated at 41d5a942:
- `siege_utilities/analytics/instagram.py:327-342` `_iter_pages` passed `paging.next` to `_request_url` with no scheme or host check.
- `instagram.py:104-108` the session sets `Authorization: Bearer <token>` for every request.
- `instagram.py:146` (`authenticate`) and `:196` (`get_account_insights`) reach `_iter_pages`, which #1794 introduced.
- `instagram.py:343-352` `_request` builds first-page URLs from `BASE_URL` and also calls `_request_url`, so `_request_url` is the single request sink.
- `vista_social.py:243` builds URLs only from its configured `base_url` and only reports `has_more`; it never follows a server-supplied URL.
- `google_analytics.py:281,310` pages by SDK `offset`; no URL following.
- requests 2.34.2 `sessions.py:154-176` `should_strip_auth` returns True on hostname change and `rebuild_auth` (`:309`) deletes `Authorization`, so redirects to another host do not carry the header. **Correction (exact-head review of 42c7619d/84c86703):** that protects only the header. A token in the redirect `Location` query is sent to the foreign host, and the redirect was followed by default. See "Redirect follow-up" below.

## Pre-mortem
1. Tiger (launch-blocking). Severity: P1. Look-alike or userinfo hosts (`graph.facebook.com@evil`, `graph.facebook.com.evil`) pass a substring check. Mitigation: exact frozenset membership on the urllib-lowercased hostname, any userinfo rejected, each trick tested.
2. Tiger (launch-blocking; misclassified at first). Severity: P1. A redirect forwards credentials to a foreign host. This was originally classified as a Paper Tiger because Requests strips `Authorization` on a host change. That reasoning missed that Requests followed the redirect by default and that a token in the `Location` query string reaches the foreign host. The exact-head review reproduced this at 42c7619d/84c86703. Mitigation (74387d04): `allow_redirects=False` on every request and a URL-free `SocialMediaError` on any 3xx, covered by the adapter-level `tests/test_1794_instagram_redirects.py`.
3. Paper Tiger. Severity: P2. The error leaks the token embedded in the rejected URL. Mitigation: fixed URL-free message raised `from None`; tests assert the token is absent from str, repr, traceback and logs.
4. Paper Tiger. Severity: P2. Legitimate paging with `:443` or an upper-case host breaks. Mitigation: port None/443 allowed; hostname is case-normalized; control tests.
5. Paper Tiger. Severity: P2. Divergence from #1833, which allows only graph.facebook.com. #1439's done criterion requires following next links across hosts, its tests page through graph.instagram.com, and the reviewer's fix spec lists both hosts. Mitigation: exact two-host `GRAPH_HOSTS`, disclosed in the PR body.
6. Elephant. Severity: P3. A cyclic `paging.next` loops (reviewer non-blocking). Deferred; disclosed.

## Hostile review
Reviewer F1: `_iter_pages` followed any `paging.next` scheme or host with the bearer header; a mocked probe sent the token to `example.invalid`. Fix spec: HTTPS, exact official host (graph.facebook.com / graph.instagram.com), no userinfo, no unapproved port, reject before dispatch, malicious-continuation tests for authenticate, posts and insights.
Own adversarial pass (security engineer frame): host suffix, prefix, subdomain, parent domain, trailing dot, percent-encoded dot and Unicode look-alike all fail exact membership. `host@evil`, `host:443@evil`, `evil\@host`, user-only and user:password all fail on userinfo. Ports 444, 8443, 80, non-numeric and 65536 fail (parse errors are caught and rejected). http on both hosts, ftp, scheme-relative and relative URLs fail.

## Peer review (Junior: shelves, gates)
- Shelves: SU-1 (an untrusted URL raises SocialMediaError, never an empty page); fail-closed parsing; red-first tests; real prepared requests with only `requests.Session.send` stubbed.
- Gate 1 (syntax): flake8 --max-line-length=127 on instagram.py and the new test -> exit 0.
- Gate 2 (tests): pytest -> 105 passed (new module); 396 passed (Instagram, pagination, credential and Vista selection); 1169 passed, 7 skipped (all 32 analytics-importing test files).
- Gate 3 (guards): scripts/check_credential_urls.py -> 0 unreviewed sites; scripts/check_test_file_hygiene.py -> PASS; git diff --check -> clean.
- Gate 4 (docs/notebooks): no notebook calls the private request helpers; method docstrings updated.

## Lead review (adversarial)
Phase A coherence: F1 maps to `_request_url`, the single sink for first pages and continuations, so one guard covers posts, authenticate and insights; the tests drive each entry point plus a direct call.
Phase B verification: red-first on base, green on head; the existing #1439 cross-host and cross-version paging tests still pass because both hosts are official Graph hosts.

## Findings
| ID | Priority | Description | Resolution |
|----|----------|-------------|------------|
| F1 | P1 | Bearer token follows untrusted paging.next (reviewer F1) | fixed in `_request_url` |
| F2 | P3 | Cyclic paging.next can loop (reviewer non-blocking) | deferred, disclosed in PR body |
| F3 | P3 | The #1749 convention commit 46ab1703 removed the #1439 CHANGELOG.md entry, but #1749 is an open proposal and CHANGELOG.md remains the adopted location | entry restored under [4.1.0] Fixed with the security note, mirrored in the PR body block; tests/test_release_process.py and tests/test_user_config_export_changelog.py -> 25 passed |

## Test plan / Quantified claims
Interpreter: ~/.pyenv/versions/default_31111/bin/python (Python 3.11.11), run from the worktree root.
- Red: base `instagram.py` restored in the worktree, `python -m pytest tests/test_1794_instagram_paging_origin.py --no-cov --tb=no -rA` -> 100 failed, 5 passed. The five passes are the valid Graph controls.
- Green: the same module on the fix -> 105 passed.
- `python -m pytest tests/test_1794_instagram_paging_origin.py tests/test_1439_analytics_pagination.py tests/test_analytics_instagram_errors.py tests/test_credential_url_leak.py tests/test_vista_social.py --no-cov` -> 396 passed.
- Every test file importing `siege_utilities.analytics` (32 files) -> 1169 passed, 7 skipped (live-credential checks).
All fixtures use dummy credentials and mocked transport; no live requests.

## Redirect follow-up (exact-head review of 42c7619d)

Finding: `_request_url` validated only the initial URL and then called `self._session.request(...)` with Requests' default `allow_redirects=True`. A permitted Graph response returning 302 to `https://evil.example.com/collect?access_token=...` was followed automatically. Requests strips `Authorization` on a host change, but a token in the `Location` query still reached the foreign host, and `_request_url` returned success. The 25 hostile-URL tests stub `Session.send`, so they never exercised redirect traversal.

Fix: every request in `_request_url` passes `allow_redirects=False`, and any 3xx response raises `SocialMediaError` with the status code only (no `Location`). No legitimate Graph-to-Graph redirect is followed, because the Graph API returns paging links in the body (`paging.next`), not as redirects.

Regression: `tests/test_1794_instagram_redirects.py` mounts a fake transport adapter on the connector's real session, so Requests' own redirect machinery runs, with zero network. It covers:
- Graph to foreign-host redirects with a token-bearing `Location`, for statuses 301, 302, 303, 307 and 308, through direct calls, `get_posts` and `authenticate` (15 cases). Each case asserts exactly one prepared request, to `graph.facebook.com`, and the absence of the token and foreign host from the error, repr, traceback and logs.
- A Graph-to-Graph redirect, which also raises.
- An official two-host paging control, checking that `Authorization` stays in the header and the token stays out of URLs.

Red/green: with `instagram.py` from 42c7619d (byte-identical at 84c86703; GitHub compare shows only `CHANGELOG.md` changed between them), 16 failed ("DID NOT RAISE": the foreign request is sent and the call succeeds) and the paging control passed. With the fix, 17 passed. The Instagram, pagination, credential, Vista, changelog and additional-credential-leak selection gives 459 passed. The credential URL guard's reviewed entry for `InstagramConnector._request_url` in `scripts/check_credential_urls.py` is updated to the new call expression (with `allow_redirects=False`), with the redirect rationale added. The guard reports 0 unreviewed sites, and flake8 and test hygiene pass.

## Rework ledger
The new test initially imported the new `GRAPH_HOSTS` constant; it now spells the allowlist out so the base run is a true red rather than an import error.

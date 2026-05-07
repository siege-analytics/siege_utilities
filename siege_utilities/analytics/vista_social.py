"""Vista Social analytics connector (issue #306).

Vista Social (https://vistasocial.com) is a social-media management
platform that aggregates engagement, posts, and audience metrics across
Facebook, Instagram, LinkedIn, X, TikTok, YouTube, and other channels.
This module provides a thin connector that auths against the Vista
Social REST API and exposes a few common reporting calls in the same
shape as the other connectors in this package
(``FacebookBusinessConnector``, ``DataDotWorldConnector``).

Why "thin"
----------
Vista Social's REST API documentation requires an authenticated
account; the public website does not enumerate endpoint URLs. This
connector ships with:

  * The base ``_request`` helper that handles auth headers, retries,
    and error normalization — fully tested.
  * Concrete ``account``, ``profiles``, ``posts``, ``analytics``
    methods that wrap likely endpoint paths (``/v1/accounts``,
    ``/v1/profiles``, ``/v1/posts``, ``/v1/analytics``). These are
    informed by the publicly visible URL structure on the Vista
    Social web app and are documented as "best-known" rather than
    spec-confirmed.

When you obtain real Vista Social API documentation (request access at
api@vistasocial.com), verify the endpoints against the docs and adjust
this module. The ``_request`` plumbing is correct regardless of which
endpoints exist.

The intended consumer is :mod:`siege_utilities.reporting`, which will
embed the returned analytics into a combined GA4 + social-media PDF
report (the second half of #306). That work lives in a follow-up PR.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Optional

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:  # pragma: no cover - requests is a core dep, but be defensive
    REQUESTS_AVAILABLE = False

log = logging.getLogger(__name__)

DEFAULT_BASE_URL = "https://api.vistasocial.com"
DEFAULT_TIMEOUT_SECONDS = 30
DEFAULT_RETRY_ATTEMPTS = 3
DEFAULT_RETRY_BACKOFF = 1.5  # exponential factor, seconds


__all__ = [
    "VistaSocialError",
    "VistaSocialAuthError",
    "VistaSocialRateLimitError",
    "VistaSocialResponse",
    "VistaSocialConnector",
]


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class VistaSocialError(RuntimeError):
    """Base class for all Vista Social connector failures."""


class VistaSocialAuthError(VistaSocialError):
    """Authentication failed (401/403). Token is missing, wrong, or expired."""


class VistaSocialRateLimitError(VistaSocialError):
    """API rate limit hit (429). Caller can back off and retry later."""


# ---------------------------------------------------------------------------
# Response model
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class VistaSocialResponse:
    """Structured response from a Vista Social API call.

    The connector returns this rather than the raw ``requests.Response``
    so consumers don't need to know about the underlying HTTP library.

    Attributes:
        status_code: HTTP status code (200 / 201 etc.).
        data: Parsed JSON body. Empty dict if the response had no body
            (e.g. 204 No Content) or wasn't JSON-decodable.
        headers: Response headers — useful for inspecting rate-limit
            counters (``X-RateLimit-Remaining``, ``Retry-After``).
        url: The fully-qualified URL that was called, for logging.
    """

    status_code: int
    data: Mapping[str, Any]
    headers: Mapping[str, str] = field(default_factory=dict)
    url: str = ""


# ---------------------------------------------------------------------------
# Connector
# ---------------------------------------------------------------------------

class VistaSocialConnector:
    """Bearer-token authenticated client for the Vista Social REST API.

    Usage::

        from siege_utilities.analytics.vista_social import VistaSocialConnector

        client = VistaSocialConnector(api_token=os.environ["VISTA_SOCIAL_TOKEN"])
        accounts = client.list_accounts()
        analytics = client.get_account_analytics(
            account_id=accounts[0]["id"],
            start_date="2026-01-01",
            end_date="2026-01-31",
        )

    All methods raise:

      * :class:`VistaSocialAuthError` on 401/403,
      * :class:`VistaSocialRateLimitError` on 429,
      * :class:`VistaSocialError` on other non-2xx responses or
        network failures.

    The connector follows the project's failure-mode discipline (see
    ``docs/FAILURE_MODES.md`` and the Phase-3 silent-swallow sweep in
    PR #433): no method silently returns an empty dict on failure.
    """

    def __init__(
        self,
        api_token: str,
        *,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
        retry_attempts: int = DEFAULT_RETRY_ATTEMPTS,
        retry_backoff: float = DEFAULT_RETRY_BACKOFF,
    ) -> None:
        if not REQUESTS_AVAILABLE:  # pragma: no cover
            raise ImportError(
                "VistaSocialConnector requires `requests`. Install via "
                "`pip install siege-utilities` (it's a core dependency)."
            )
        if not api_token:
            raise ValueError(
                "VistaSocialConnector requires an api_token. Pass one "
                "explicitly or read from VISTA_SOCIAL_TOKEN before "
                "constructing the client."
            )
        self._token = api_token
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._retry_attempts = max(1, retry_attempts)
        self._retry_backoff = retry_backoff
        self._session = requests.Session()
        self._session.headers.update({
            "Authorization": f"Bearer {api_token}",
            "Accept": "application/json",
            "User-Agent": "siege_utilities/VistaSocialConnector",
        })
        log.info("VistaSocialConnector initialised against %s", self._base_url)

    # ------------------------------------------------------------------
    # Low-level: HTTP plumbing (well-tested; endpoints sit on top)
    # ------------------------------------------------------------------

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: Optional[Mapping[str, Any]] = None,
        json_body: Optional[Mapping[str, Any]] = None,
    ) -> VistaSocialResponse:
        """Send an authenticated request to *path* (relative to base URL).

        Retries with exponential backoff on 5xx and on transport errors
        (``requests.exceptions.RequestException``). 401/403 is fatal —
        retry won't fix bad credentials. 429 is surfaced as
        :class:`VistaSocialRateLimitError` so callers can back off
        intelligently rather than have us double-retry into a longer
        ban.
        """
        url = f"{self._base_url}/{path.lstrip('/')}"
        last_exc: Optional[BaseException] = None

        for attempt in range(1, self._retry_attempts + 1):
            try:
                resp = self._session.request(
                    method, url,
                    params=dict(params) if params else None,
                    json=dict(json_body) if json_body is not None else None,
                    timeout=self._timeout,
                )
            except requests.exceptions.RequestException as exc:
                last_exc = exc
                log.warning(
                    "VistaSocial %s %s attempt %d/%d failed: %s",
                    method, url, attempt, self._retry_attempts, exc,
                )
                if attempt < self._retry_attempts:
                    time.sleep(self._retry_backoff ** attempt)
                continue

            if resp.status_code in (401, 403):
                raise VistaSocialAuthError(
                    f"Vista Social {method} {url} returned {resp.status_code}. "
                    "Check the api_token (expired? revoked? wrong scope?)."
                )
            if resp.status_code == 429:
                retry_after = resp.headers.get("Retry-After", "<unset>")
                raise VistaSocialRateLimitError(
                    f"Vista Social rate limit hit on {method} {url}. "
                    f"Retry-After: {retry_after}."
                )
            if 500 <= resp.status_code < 600:
                last_exc = VistaSocialError(
                    f"Vista Social {method} {url} returned {resp.status_code}."
                )
                log.warning(
                    "VistaSocial %s %s 5xx %d attempt %d/%d",
                    method, url, resp.status_code, attempt, self._retry_attempts,
                )
                if attempt < self._retry_attempts:
                    time.sleep(self._retry_backoff ** attempt)
                continue
            if not 200 <= resp.status_code < 300:
                # 4xx other than 401/403/429 — caller error, not retried.
                raise VistaSocialError(
                    f"Vista Social {method} {url} returned {resp.status_code}: "
                    f"{resp.text[:200]}"
                )

            if not resp.content:
                # 204 No Content / empty body — legitimately empty.
                data: Mapping[str, Any] = {}
            else:
                try:
                    data = resp.json()
                except ValueError as exc:
                    # 2xx with non-JSON body. Don't silently treat as
                    # empty (that violates the no-silent-swallow rule
                    # set by the Phase-3 sweep) — surface it.
                    raise VistaSocialError(
                        f"Vista Social {method} {url} returned "
                        f"{resp.status_code} with non-JSON body "
                        f"(first 200 chars: {resp.text[:200]!r})."
                    ) from exc
            return VistaSocialResponse(
                status_code=resp.status_code,
                data=data,
                headers=dict(resp.headers),
                url=url,
            )

        # Exhausted retries on transport / 5xx.
        raise VistaSocialError(
            f"Vista Social {method} {url} failed after {self._retry_attempts} "
            f"attempts. Last error: {last_exc}"
        ) from last_exc

    # ------------------------------------------------------------------
    # High-level: best-known endpoint paths (verify against real docs)
    # ------------------------------------------------------------------

    def list_accounts(self) -> List[Mapping[str, Any]]:
        """Return the list of accounts this token can access.

        Wraps ``GET /v1/accounts``. Returns the decoded ``data`` list
        from the response, or an empty list if the API returned nothing.
        Raises on auth / rate-limit / network failures (no silent
        empty-on-error).
        """
        resp = self._request("GET", "/v1/accounts")
        items = resp.data.get("data") if isinstance(resp.data, Mapping) else None
        return list(items) if items else []

    def list_profiles(self, account_id: str) -> List[Mapping[str, Any]]:
        """Return social profiles connected to *account_id*.

        Wraps ``GET /v1/accounts/{account_id}/profiles``.
        """
        if not account_id:
            raise ValueError("list_profiles requires a non-empty account_id")
        resp = self._request("GET", f"/v1/accounts/{account_id}/profiles")
        items = resp.data.get("data") if isinstance(resp.data, Mapping) else None
        return list(items) if items else []

    def get_account_analytics(
        self,
        account_id: str,
        *,
        start_date: str,
        end_date: str,
        metrics: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Fetch aggregate analytics for *account_id* over a date range.

        Args:
            account_id: Vista Social account id (string, opaque).
            start_date: ISO-8601 date (``YYYY-MM-DD``), inclusive.
            end_date: ISO-8601 date, inclusive.
            metrics: Optional list of metric names (e.g. ``["impressions",
                "engagements", "reach", "follower_count"]``). If omitted,
                Vista Social returns its default metric set.

        Wraps ``GET /v1/accounts/{account_id}/analytics``. Returns the
        decoded JSON body verbatim — Vista Social returns a structured
        document with metric breakdowns; consumers can extract what
        they need.
        """
        if not account_id:
            raise ValueError("get_account_analytics requires a non-empty account_id")
        params: Dict[str, Any] = {
            "start_date": start_date,
            "end_date": end_date,
        }
        if metrics:
            params["metrics"] = ",".join(metrics)
        resp = self._request(
            "GET", f"/v1/accounts/{account_id}/analytics", params=params,
        )
        return dict(resp.data) if isinstance(resp.data, Mapping) else {}

    def list_posts(
        self,
        account_id: str,
        *,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 100,
    ) -> List[Mapping[str, Any]]:
        """Return posts for *account_id* with optional date filtering.

        Wraps ``GET /v1/accounts/{account_id}/posts``. Pagination is
        intentionally simple here — consumers that need full enumeration
        should call repeatedly with adjusted date ranges or extend this
        connector with cursor handling once the real API spec is known.
        """
        if not account_id:
            raise ValueError("list_posts requires a non-empty account_id")
        params: Dict[str, Any] = {"limit": limit}
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        resp = self._request(
            "GET", f"/v1/accounts/{account_id}/posts", params=params,
        )
        items = resp.data.get("data") if isinstance(resp.data, Mapping) else None
        return list(items) if items else []

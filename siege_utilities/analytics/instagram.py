"""
Instagram Graph API analytics connector.

Provides read-only access to Instagram Business/Creator account metrics
via Meta's Graph API. Implements :class:`SocialMediaProtocol` for
cross-platform reporting composition.

Requires a Meta OAuth 2.0 long-lived token with scopes:
``instagram_basic``, ``instagram_manage_insights``, ``pages_show_list``.

The Instagram account must be a Business or Creator account linked to
a Facebook Page. Personal accounts are not supported by the Graph API.
"""

from __future__ import annotations

import json
import logging
import pathlib
import time
from datetime import date, datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from math import isfinite
from typing import Any, Mapping
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import pandas as pd

try:
    import requests

    REQUESTS_AVAILABLE = True
except ImportError:  # pragma: no cover
    REQUESTS_AVAILABLE = False

from siege_utilities.analytics._social_protocol import (
    SocialMediaAuthError,
    SocialMediaError,
    SocialMediaRateLimitError,
)
from siege_utilities.core._http import redact_url_secrets

from siege_utilities.files.secure_write import secure_write_text

log = logging.getLogger(__name__)

API_VERSION = "v22.0"
BASE_URL = f"https://graph.facebook.com/{API_VERSION}"
DEFAULT_TIMEOUT = 30
DEFAULT_RETRY_ATTEMPTS = 3
DEFAULT_RETRY_BACKOFF = 1.5
DEFAULT_MAX_RETRY_WAIT = 900.0

DEFAULT_ACCOUNT_FIELDS = (
    "username,name,followers_count,follows_count,media_count,"
    "biography,profile_picture_url"
)
DEFAULT_MEDIA_FIELDS = (
    "id,caption,media_type,media_url,permalink,timestamp,"
    "like_count,comments_count"
)
# Graph v22.0 defaults, reviewed against Meta's insights references 2026-10-18.
# Keep account defaults compatible with daily time_series; views/profile_views
# require total_value and cannot be mixed into this daily request.
DEFAULT_ACCOUNT_METRICS = "reach,follower_count"
DEFAULT_POST_METRICS = "views,reach,total_interactions,saved,shares"
_DEFAULT_STORY_METRICS = "views,reach,replies,navigation"
_POST_COLUMNS = [
    "id", "platform", "post_type", "text", "media_url", "published_at", "permalink",
    "like_count", "comments_count", "metrics",
]
_EXPIRED_TOKEN_MESSAGE = (
    "Instagram access token has expired. Obtain a fresh token through Facebook "
    "Login, then call refresh_access_token(access_token=...) with app_id and "
    "app_secret configured, or create a connector with the new token and expiry."
)

__all__ = [
    "InstagramConnector",
    "create_instagram_account_profile",
    "save_instagram_account_profile",
    "load_instagram_account_profile",
]


class InstagramConnector:
    """Instagram Graph API connector implementing SocialMediaProtocol.

    Long-lived Facebook user tokens expire after about 60 days. Supply the
    timezone-aware ``token_expires_at`` from the login flow to detect expiry
    before requests. If omitted, expiry is unknown until Graph reports it;
    constructing a connector does not restart the token's lifetime.

    Configure ``app_id`` and ``app_secret`` and call ``refresh_access_token()``
    to exchange an eligible, unexpired user token at ``/oauth/access_token``
    using ``fb_exchange_token``. The returned token and ``expires_in`` update
    the session and ``token_expires_at``. Persist the returned token and expiry
    in your credential store. Expired tokens require Facebook Login again;
    pass the fresh token to ``refresh_access_token(access_token=...)`` and
    call ``authenticate()``. There is no automatic renewal of expired tokens.

    Retry hints above ``max_retry_wait`` (900 seconds by default) raise
    SocialMediaRateLimitError without sleeping. Backoff waits use the same cap.

    Usage::

        from siege_utilities.analytics.instagram import InstagramConnector

        conn = InstagramConnector(access_token=os.environ["META_TOKEN"])
        conn.authenticate()
        info = conn.get_account_info()
        posts = conn.get_posts(date(2026, 1, 1), date(2026, 1, 31))
    """

    def __init__(
        self,
        access_token: str,
        *,
        ig_user_id: str | None = None,
        token_expires_at: datetime | None = None,
        app_id: str | None = None,
        app_secret: str | None = None,
        timeout: float = DEFAULT_TIMEOUT,
        retry_attempts: int = DEFAULT_RETRY_ATTEMPTS,
        retry_backoff: float = DEFAULT_RETRY_BACKOFF,
        max_retry_wait: float = DEFAULT_MAX_RETRY_WAIT,
    ) -> None:
        if not REQUESTS_AVAILABLE:  # pragma: no cover
            raise ImportError(
                "InstagramConnector requires `requests`. "
                "Install via `pip install siege-utilities`."
            )
        if not access_token:
            raise ValueError("access_token is required.")
        if token_expires_at is not None and token_expires_at.utcoffset() is None:
            raise ValueError("token_expires_at must be a timezone-aware datetime.")
        if not isfinite(max_retry_wait) or max_retry_wait < 0:
            raise ValueError("max_retry_wait must be finite and nonnegative.")
        if not isfinite(retry_backoff) or retry_backoff < 0:
            raise ValueError("retry_backoff must be finite and nonnegative.")

        self._access_token = access_token
        self._token_expires_at = token_expires_at
        self._app_id = app_id
        self._app_secret = app_secret
        self._ig_user_id = ig_user_id
        self._timeout = timeout
        self._retry_attempts = max(1, retry_attempts)
        self._retry_backoff = retry_backoff
        self._max_retry_wait = max_retry_wait
        self._authenticated = False
        self._session = requests.Session()
        self._session.headers.update({
            "Accept": "application/json",
            "User-Agent": "siege_utilities/InstagramConnector",
            "Authorization": f"Bearer {self._access_token}",
        })
        log.info("InstagramConnector initialised (API %s)", API_VERSION)

    def close(self) -> None:
        """Close the underlying HTTP session."""
        self._session.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    # ------------------------------------------------------------------
    # SocialMediaProtocol implementation
    # ------------------------------------------------------------------

    @property
    def platform_name(self) -> str:
        return "instagram"

    def authenticate(self) -> None:
        """Validate token and discover IG user ID if not provided.

        Calls ``/me/accounts`` to find the Facebook Page, then queries
        the page's ``instagram_business_account`` field.
        """
        if self._ig_user_id:
            resp = self._request("GET", f"/{self._ig_user_id}", params={
                "fields": "username,id",
            })
            self._authenticated = True
            log.info("Authenticated as IG user %s", resp.get("username", self._ig_user_id))
            return

        pages = self._request("GET", "/me/accounts", params={
            "fields": "id,name,instagram_business_account",
        })
        page_data = pages.get("data", [])
        for page in page_data:
            ig_account = page.get("instagram_business_account")
            if ig_account:
                self._ig_user_id = ig_account["id"]
                self._authenticated = True
                log.info(
                    "Discovered IG user %s via page '%s'",
                    self._ig_user_id, page.get("name"),
                )
                return

        raise SocialMediaAuthError(
            "No Instagram Business/Creator account found linked to any "
            "Facebook Page accessible with this token. Ensure the IG "
            "account is a Business or Creator account and is linked to a Page."
        )

    def is_connected(self) -> bool:
        return self._authenticated

    def get_account_info(self) -> dict[str, Any]:
        """Account metadata: username, followers, media count, biography."""
        self._ensure_connected()
        data = self._request("GET", f"/{self._ig_user_id}", params={
            "fields": DEFAULT_ACCOUNT_FIELDS,
        })
        return data

    def get_account_insights(
        self,
        start_date: date,
        end_date: date,
        metrics: list[str] | None = None,
    ) -> pd.DataFrame:
        """Daily account metrics, defaulting to reach and follower_count.

        Overrides must support daily time-series values. Missing values stay
        null; account views/profile_views require a total_value query instead.
        """
        self._ensure_connected()
        metric_str = ",".join(metrics) if metrics else DEFAULT_ACCOUNT_METRICS
        since_ts = int(datetime.combine(start_date, datetime.min.time()).timestamp())
        until_ts = int(datetime.combine(end_date, datetime.max.time()).timestamp())

        data = self._request("GET", f"/{self._ig_user_id}/insights", params={
            "metric": metric_str,
            "period": "day",
            "since": since_ts,
            "until": until_ts,
        })

        rows: list[dict[str, Any]] = []
        for metric_block in data.get("data", []):
            metric_name = metric_block["name"]
            for value_entry in metric_block.get("values", []):
                end_time = value_entry.get("end_time", "")
                dt = end_time[:10] if end_time else ""
                existing = next((r for r in rows if r["date"] == dt), None)
                if existing:
                    existing[metric_name] = value_entry.get("value")
                else:
                    rows.append({
                        "date": dt,
                        metric_name: value_entry.get("value"),
                    })

        df = pd.DataFrame(rows)
        if not df.empty and "date" in df.columns:
            df = df.sort_values("date").reset_index(drop=True)
        log.info("Retrieved %d days of account insights", len(df))
        return df

    def get_posts(
        self,
        start_date: date,
        end_date: date,
        *,
        limit: int | None = None,
    ) -> pd.DataFrame:
        """Posts published in the given date range.

        ``published_at`` is UTC-aware (NaT if unavailable); ``metrics`` holds
        available like/comment counts alongside the existing count columns.

        Return collected posts with a warning if a later page exhausts rate
        limit retries. First-page failures and other errors propagate.
        """
        self._ensure_connected()
        all_posts: list[dict[str, Any]] = []
        params: dict[str, Any] = {
            "fields": DEFAULT_MEDIA_FIELDS,
            "limit": min(limit or 50, 50),
        }

        start_dt = datetime.combine(start_date, datetime.min.time())
        end_dt = datetime.combine(end_date, datetime.max.time())

        url = f"{BASE_URL}/{self._ig_user_id}/media"
        while True:
            try:
                data = self._request_url("GET", url, params=params)
            except SocialMediaRateLimitError:
                if not all_posts:
                    raise
                log.warning(
                    "Instagram rate limit exhausted; returning partial results (%d posts)",
                    len(all_posts),
                )
                break
            for post in data.get("data", []):
                ts_str = post.get("timestamp", "")
                if ts_str:
                    try:
                        post_dt = datetime.fromisoformat(ts_str.replace("+0000", "+00:00"))
                        post_dt = post_dt.replace(tzinfo=None)
                    except ValueError:
                        post_dt = None
                else:
                    post_dt = None

                if post_dt and post_dt < start_dt:
                    return self._posts_to_dataframe(all_posts)
                if post_dt is None or (start_dt <= post_dt <= end_dt):
                    all_posts.append(post)
                    if limit and len(all_posts) >= limit:
                        return self._posts_to_dataframe(all_posts)

            paging = data.get("paging", {})
            next_url = paging.get("next")
            if not next_url:
                break
            params = {}
            url = next_url

        return self._posts_to_dataframe(all_posts)

    def get_post_insights(
        self,
        post_id: str,
        metrics: list[str] | None = None,
    ) -> pd.DataFrame:
        """Engagement metrics for a single post."""
        self._ensure_connected()
        metric_str = ",".join(metrics) if metrics else DEFAULT_POST_METRICS
        data = self._request("GET", f"/{post_id}/insights", params={
            "metric": metric_str,
        })

        rows: list[dict[str, Any]] = []
        for metric_block in data.get("data", []):
            row: dict[str, Any] = {
                "metric": metric_block["name"],
                "value": self._insight_value(metric_block),
            }
            if metric_block.get("period"):
                row["period"] = metric_block["period"]
            rows.append(row)

        return pd.DataFrame(rows)

    # ------------------------------------------------------------------
    # Extra methods (beyond protocol)
    # ------------------------------------------------------------------

    @property
    def token_expires_at(self) -> datetime | None:
        """Known token expiry, or None when no expiry metadata was supplied."""
        return self._token_expires_at

    def is_token_expired(self) -> bool:
        """Whether the known expiry has passed; unknown expiry returns False."""
        return self._token_expires_at is not None and datetime.now(timezone.utc) >= self._token_expires_at

    def refresh_access_token(self, *, access_token: str | None = None) -> str:
        """Exchange a valid Facebook user token and return the new token.

        Uses the current token unless ``access_token`` supplies a fresh login
        token. Requires constructor ``app_id`` and ``app_secret``. Updates the
        bearer header and expiry only after a valid exchange response. Raises
        SocialMediaAuthError when credentials, token or expiry are invalid.
        Transport and rate-limit errors follow the normal retry policy.
        """
        if not self._app_id or not self._app_secret:
            raise SocialMediaAuthError(
                "Instagram token exchange requires app_id and app_secret. "
                "Configure both or obtain a fresh token through Facebook Login."
            )
        if access_token is None:
            if self.is_token_expired():
                self._authenticated = False
                raise SocialMediaAuthError(_EXPIRED_TOKEN_MESSAGE)
            access_token = self._access_token
        if not access_token:
            raise SocialMediaAuthError("Instagram token exchange requires a valid login token.")

        data = self._request_url("GET", f"{BASE_URL}/oauth/access_token", params={
            "grant_type": "fb_exchange_token",
            "client_id": self._app_id,
            "client_secret": self._app_secret,
            "fb_exchange_token": access_token,
        }, _token_exchange=True)
        try:
            token = data["access_token"]
            expires_in = float(data["expires_in"])
            if not isinstance(token, str) or not token or not isfinite(expires_in) or expires_in <= 0:
                raise ValueError("Invalid token or expiry")
            expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
        except (KeyError, TypeError, ValueError, OverflowError):
            raise SocialMediaAuthError(
                "Instagram token exchange returned no valid access_token or expires_in; "
                "obtain a fresh token through Facebook Login."
            ) from None

        self._access_token = token
        self._token_expires_at = expires_at
        self._session.headers["Authorization"] = f"Bearer {token}"
        log.info("Instagram token exchanged; expires at %s", expires_at.isoformat())
        return token

    def get_stories_insights(self, metrics: list[str] | None = None) -> pd.DataFrame:
        """Active stories with overridable metrics, including total navigation.

        Navigation aggregates forward, back, exit and next-story actions.
        """
        self._ensure_connected()
        metric_str = ",".join(metrics) if metrics else _DEFAULT_STORY_METRICS
        stories_data = self._request("GET", f"/{self._ig_user_id}/stories", params={
            "fields": "id,media_type,media_url,permalink,timestamp",
        })

        rows: list[dict[str, Any]] = []
        for story in stories_data.get("data", []):
            row = dict(story)
            try:
                insights = self._request("GET", f"/{story['id']}/insights", params={
                    "metric": metric_str,
                })
                for m in insights.get("data", []):
                    row[m["name"]] = self._insight_value(m)
            except SocialMediaError:
                log.warning("Could not retrieve insights for story %s", story["id"])
            rows.append(row)

        return pd.DataFrame(rows)

    # ------------------------------------------------------------------
    # HTTP plumbing
    # ------------------------------------------------------------------

    def _ensure_connected(self) -> None:
        if not self._authenticated:
            raise SocialMediaAuthError(
                "Not authenticated. Call authenticate() first."
            )

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Send an authenticated request to the Graph API."""
        url = f"{BASE_URL}/{path.lstrip('/')}"
        return self._request_url(method, url, params=params)

    def _request_url(
        self,
        method: str,
        url: str,
        *,
        params: Mapping[str, Any] | None = None,
        _token_exchange: bool = False,
    ) -> dict[str, Any]:
        """Send an authenticated request to an absolute URL."""
        if not _token_exchange and self.is_token_expired():
            self._authenticated = False
            raise SocialMediaAuthError(_EXPIRED_TOKEN_MESSAGE)
        req_params = {
            key: value for key, value in (params or {}).items()
            if key.lower() != "access_token"
        }
        # Graph paging links can repeat the token; authenticate via the header.
        parts = urlsplit(url)
        query = [
            (key, value) for key, value in parse_qsl(parts.query, keep_blank_values=True)
            if key.lower() != "access_token"
        ]
        url = urlunsplit(parts._replace(query=urlencode(query)))
        safe_url = redact_url_secrets(url)
        last_exc: BaseException | None = None

        for attempt in range(1, self._retry_attempts + 1):
            try:
                resp = self._session.request(
                    method, url,
                    params=req_params,
                    timeout=self._timeout,
                    **({"headers": {"Authorization": None}} if _token_exchange else {}),
                )
            except requests.exceptions.RequestException as exc:
                if _token_exchange:
                    last_exc = SocialMediaError(
                        f"Instagram token exchange {type(exc).__name__} on attempt {attempt}."
                    )
                    log.warning("%s", last_exc)
                else:
                    last_exc = SocialMediaError(redact_url_secrets(str(exc)))
                    log.warning(
                        "Instagram %s %s attempt %d/%d failed: %s",
                        method, safe_url, attempt, self._retry_attempts, str(last_exc),
                    )
                if attempt < self._retry_attempts:
                    time.sleep(self._backoff_delay(attempt))
                continue

            try:
                body = resp.json()
            except ValueError:
                body = {}
            graph_error = body.get("error", {}) if isinstance(body, dict) else {}
            graph_error = graph_error if isinstance(graph_error, dict) else {}
            if graph_error.get("code") == 190:
                # A rejected replacement token says nothing about the stored token.
                if not _token_exchange or req_params.get("fb_exchange_token") == self._access_token:
                    self._authenticated = False
                    if graph_error.get("error_subcode") == 463:
                        self._token_expires_at = datetime.now(timezone.utc)
                if graph_error.get("error_subcode") == 463:
                    raise SocialMediaAuthError(_EXPIRED_TOKEN_MESSAGE)
                raise SocialMediaAuthError(
                    "Instagram access token is invalid or revoked. "
                    "Obtain a fresh token through Facebook Login."
                )

            if self._is_rate_limited(resp):
                retry_after = self._parse_retry_after(resp)
                error = SocialMediaRateLimitError(
                    f"Instagram API rate limit hit on {method} {safe_url}.",
                    retry_after=retry_after,
                )
                if attempt == self._retry_attempts or (
                    retry_after is not None and retry_after > self._max_retry_wait
                ):
                    raise error
                delay = retry_after if retry_after is not None else self._backoff_delay(attempt)
                log.warning(
                    "Instagram rate limit on %s %s attempt %d/%d; retrying in %s seconds",
                    method, safe_url, attempt, self._retry_attempts, delay,
                )
                time.sleep(delay)
                continue

            if _token_exchange and 400 <= resp.status_code < 500:
                raise SocialMediaAuthError(
                    "Instagram token exchange was rejected. Verify app_id and "
                    "app_secret, or obtain a fresh token through Facebook Login."
                )

            if resp.status_code in (401, 403):
                error_msg = self._extract_error_message(resp)
                raise SocialMediaAuthError(
                    f"Instagram API {resp.status_code}: {error_msg}"
                )

            if 500 <= resp.status_code < 600:
                last_exc = SocialMediaError(
                    f"Instagram API {resp.status_code} on {method} {safe_url}."
                )
                log.warning(
                    "Instagram %s %s 5xx %d attempt %d/%d",
                    method, safe_url, resp.status_code, attempt, self._retry_attempts,
                )
                if attempt < self._retry_attempts:
                    time.sleep(self._backoff_delay(attempt))
                continue

            if not (200 <= resp.status_code < 300):
                if _token_exchange:
                    raise SocialMediaError(
                        f"Instagram token exchange failed (HTTP {resp.status_code})."
                    )
                error_msg = self._extract_error_message(resp)
                raise SocialMediaError(
                    f"Instagram API {resp.status_code}: {error_msg}"
                )

            try:
                return resp.json()
            except ValueError:
                if _token_exchange:
                    error = SocialMediaError(
                        f"Instagram token exchange returned an unparseable response (HTTP {resp.status_code})."
                    )
                else:
                    error = SocialMediaError(
                        f"Instagram API returned non-JSON response on {method} {safe_url} (HTTP {resp.status_code})."
                    )
            raise error from None

        if _token_exchange:
            raise last_exc from None
        raise SocialMediaError(
            f"Instagram API {method} {safe_url} failed after {self._retry_attempts} "
            f"attempts: {last_exc}"
        )

    def _backoff_delay(self, attempt: int) -> float:
        try:
            return min(self._retry_backoff ** attempt, self._max_retry_wait)
        except OverflowError:
            return self._max_retry_wait

    @staticmethod
    def _extract_error_message(resp: requests.Response) -> str:
        try:
            body = resp.json()
            return redact_url_secrets(str(body.get("error", {}).get(
                "message", "No error message provided",
            )))
        except ValueError:
            return "Unparseable error response"

    @staticmethod
    def _usage_exhausted(resp: requests.Response) -> bool:
        for header in ("x-app-usage", "x-page-usage"):
            try:
                usage = json.loads(resp.headers.get(header, "{}"))
            except ValueError:
                # Usage telemetry is optional; HTTP status and error codes remain authoritative.
                usage = {}
            if isinstance(usage, dict) and any(
                isinstance(usage.get(key), (int, float)) and usage[key] >= 100
                for key in ("call_count", "total_cputime", "total_time")
            ):
                return True
        return False

    @classmethod
    def _is_rate_limited(cls, resp: requests.Response) -> bool:
        try:
            body = resp.json()
        except ValueError:
            body = {}
        error = body.get("error", {}) if isinstance(body, dict) else {}
        code = error.get("code") if isinstance(error, dict) else None
        if code is not None:
            return code in (4, 17, 32, 613, *range(80001, 80015))
        if resp.status_code == 429:
            return True
        if 200 <= resp.status_code < 300:
            return False  # Keep successful data even when its usage header reaches 100%.
        return cls._usage_exhausted(resp)

    @staticmethod
    def _parse_retry_after(resp: requests.Response) -> float | None:
        header = resp.headers.get("Retry-After")
        if header:
            try:
                delay = float(header)
            except ValueError:
                try:
                    delay = parsedate_to_datetime(header).timestamp() - time.time()
                except (ValueError, TypeError, OverflowError):
                    delay = None
            if delay is not None and isfinite(delay):
                return max(0.0, delay)
        if InstagramConnector._usage_exhausted(resp):
            return 600.0
        return None

    # ------------------------------------------------------------------
    # DataFrame helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _insight_value(metric: Mapping[str, Any]) -> Any:
        """Read Graph media values without inventing zeros for unavailable data."""
        if "total_value" in metric:
            return metric["total_value"].get("value")
        values = metric.get("values", [])
        return values[0].get("value") if values else None

    @staticmethod
    def _posts_to_dataframe(posts: list[dict[str, Any]]) -> pd.DataFrame:
        rows: list[dict[str, Any]] = []
        for p in posts:
            rows.append({
                "id": p.get("id"),
                "platform": "instagram",
                "post_type": p.get("media_type", "").lower(),
                "text": p.get("caption"),
                "media_url": p.get("media_url"),
                "published_at": p.get("timestamp"),
                "permalink": p.get("permalink"),
                "like_count": p.get("like_count", 0),
                "comments_count": p.get("comments_count", 0),
                "metrics": {key: p[key] for key in ("like_count", "comments_count") if key in p},
            })
        df = pd.DataFrame(rows, columns=_POST_COLUMNS)
        df["published_at"] = pd.to_datetime(df["published_at"], format="ISO8601", utc=True, errors="coerce")
        if not df.empty:
            log.info("Retrieved %d posts", len(df))
        return df


# ---------------------------------------------------------------------------
# Profile management (module-level functions)
# ---------------------------------------------------------------------------


def create_instagram_account_profile(
    client_id: str,
    ig_user_id: str,
    access_token: str,
    *,
    username: str | None = None,
) -> dict[str, Any]:
    """Create an Instagram account profile linked to a client."""
    return {
        "ig_account_id": f"ig_{ig_user_id}",
        "client_id": client_id,
        "ig_user_id": ig_user_id,
        "username": username,
        "access_token": access_token,
        "platform": "instagram",
        "created_at": datetime.now().isoformat(),
    }


def save_instagram_account_profile(
    profile: dict[str, Any],
    config_directory: str | None = None,
) -> str:
    """Save Instagram account profile to JSON under ~/.siege_utilities/instagram by default."""
    config_dir = (pathlib.Path(config_directory) if config_directory is not None
                  else pathlib.Path.home() / ".siege_utilities") / "instagram"

    account_id = profile["ig_account_id"]
    config_file = config_dir / f"ig_account_{account_id}.json"

    secure_write_text(config_file, json.dumps(profile, indent=2))

    log.info("Saved Instagram profile to %s", config_file)
    return str(config_file)


def load_instagram_account_profile(
    account_id: str,
    config_directory: str | None = None,
) -> dict[str, Any] | None:
    """Load Instagram account profile from JSON file."""
    config_dir = (pathlib.Path(config_directory) if config_directory is not None
                  else pathlib.Path.home() / ".siege_utilities") / "instagram"
    config_file = config_dir / f"ig_account_{account_id}.json"

    if not config_file.exists():
        return None

    with open(config_file, "r", encoding="utf-8") as f:
        return json.load(f)

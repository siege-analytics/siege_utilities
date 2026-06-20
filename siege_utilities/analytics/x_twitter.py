"""
X (Twitter) API v2 analytics connector.

Provides read-only access to X/Twitter account and tweet metrics via
the X API v2. Implements :class:`SocialMediaProtocol` for cross-platform
reporting composition.

X API uses pay-per-use pricing — reads cost $0.005/call. This connector
tracks estimated costs and supports a configurable budget cap to prevent
runaway API charges.

Requires an X API Bearer token (app-only auth) or OAuth 2.0 PKCE user
token. Basic access tier provides 100 reads/month free; pay-per-use
scales to 2M reads/month.
"""

from __future__ import annotations

import json
import logging
import pathlib
import time
from datetime import date, datetime
from typing import Any, Mapping

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

log = logging.getLogger(__name__)

BASE_URL = "https://api.x.com/2"
DEFAULT_TIMEOUT = 30
DEFAULT_RETRY_ATTEMPTS = 3
DEFAULT_RETRY_BACKOFF = 2.0
COST_PER_READ = 0.005

__all__ = [
    "XTwitterConnector",
    "create_x_account_profile",
    "save_x_account_profile",
    "load_x_account_profile",
]


class XTwitterConnector:
    """X/Twitter API v2 connector implementing SocialMediaProtocol.

    Usage::

        from siege_utilities.analytics.x_twitter import XTwitterConnector

        conn = XTwitterConnector(
            bearer_token=os.environ["X_BEARER_TOKEN"],
            username="siege_analytics",
            budget_limit=10.00,
        )
        conn.authenticate()
        info = conn.get_account_info()
        tweets = conn.get_posts(date(2026, 1, 1), date(2026, 6, 1))
        print(f"Estimated API cost: ${conn.estimated_cost:.2f}")
    """

    def __init__(
        self,
        bearer_token: str,
        *,
        username: str | None = None,
        user_id: str | None = None,
        budget_limit: float | None = None,
        timeout: float = DEFAULT_TIMEOUT,
        retry_attempts: int = DEFAULT_RETRY_ATTEMPTS,
        retry_backoff: float = DEFAULT_RETRY_BACKOFF,
    ) -> None:
        if not REQUESTS_AVAILABLE:  # pragma: no cover
            raise ImportError(
                "XTwitterConnector requires `requests`. "
                "Install via `pip install siege-utilities`."
            )
        if not bearer_token:
            raise ValueError("bearer_token is required.")

        self._bearer_token = bearer_token
        self._username = username
        self._user_id = user_id
        self._budget_limit = budget_limit
        self._estimated_cost = 0.0
        self._timeout = timeout
        self._retry_attempts = max(1, retry_attempts)
        self._retry_backoff = retry_backoff
        self._authenticated = False
        self._session = requests.Session()
        self._session.headers.update({
            "Authorization": f"Bearer {bearer_token}",
            "Accept": "application/json",
            "User-Agent": "siege_utilities/XTwitterConnector",
        })
        log.info("XTwitterConnector initialised")

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
        return "x_twitter"

    @property
    def estimated_cost(self) -> float:
        """Running total of estimated API costs in USD."""
        return self._estimated_cost

    def reset_cost_tracking(self) -> None:
        """Reset the estimated cost accumulator to zero."""
        self._estimated_cost = 0.0

    def authenticate(self) -> None:
        """Validate bearer token and resolve user ID."""
        if self._user_id:
            data = self._request("GET", f"/users/{self._user_id}", params={
                "user.fields": "username,id",
            })
            user = data.get("data", {})
            self._username = user.get("username", self._username)
            self._authenticated = True
            log.info("Authenticated as @%s (id=%s)", self._username, self._user_id)
            return

        if self._username:
            data = self._request("GET", f"/users/by/username/{self._username}", params={
                "user.fields": "id,username",
            })
            user = data.get("data", {})
            if not user:
                raise SocialMediaAuthError(
                    f"User @{self._username} not found or token lacks access."
                )
            self._user_id = user["id"]
            self._authenticated = True
            log.info("Authenticated as @%s (id=%s)", self._username, self._user_id)
            return

        data = self._request("GET", "/users/me", params={
            "user.fields": "id,username",
        })
        user = data.get("data", {})
        if not user:
            raise SocialMediaAuthError(
                "Bearer token does not support /users/me (app-only tokens "
                "require a username or user_id parameter)."
            )
        self._user_id = user["id"]
        self._username = user.get("username")
        self._authenticated = True
        log.info("Authenticated as @%s (id=%s)", self._username, self._user_id)

    def is_connected(self) -> bool:
        return self._authenticated

    def get_account_info(self) -> dict[str, Any]:
        """Account metadata: username, followers, tweet count, verified status."""
        self._ensure_connected()
        data = self._request("GET", f"/users/{self._user_id}", params={
            "user.fields": (
                "username,name,description,profile_image_url,"
                "public_metrics,verified,created_at,location,url"
            ),
        })
        user = data.get("data", {})
        metrics = user.pop("public_metrics", {})
        user.update({
            "followers_count": metrics.get("followers_count", 0),
            "following_count": metrics.get("following_count", 0),
            "tweet_count": metrics.get("tweet_count", 0),
            "listed_count": metrics.get("listed_count", 0),
            "like_count": metrics.get("like_count", 0),
        })
        return user

    def get_account_insights(
        self,
        start_date: date,
        end_date: date,
        metrics: list[str] | None = None,
    ) -> pd.DataFrame:
        """Account-level metrics snapshot.

        X API v2 does not provide historical time-series for account
        metrics. This returns a single-row DataFrame with the current
        public_metrics as a point-in-time snapshot. For trend analysis,
        call periodically and store results externally.
        """
        self._ensure_connected()
        info = self.get_account_info()
        metric_keys = metrics or [
            "followers_count", "following_count", "tweet_count",
            "listed_count", "like_count",
        ]
        row = {"date": str(date.today())}
        for k in metric_keys:
            row[k] = info.get(k, 0)
        return pd.DataFrame([row])

    def get_posts(
        self,
        start_date: date,
        end_date: date,
        *,
        limit: int | None = None,
    ) -> pd.DataFrame:
        """Tweets published in the given date range."""
        self._ensure_connected()
        all_tweets: list[dict[str, Any]] = []
        max_results = min(limit or 100, 100)

        params: dict[str, Any] = {
            "tweet.fields": "created_at,public_metrics,text,entities",
            "max_results": max_results,
            "start_time": datetime.combine(start_date, datetime.min.time()).strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            ),
            "end_time": datetime.combine(end_date, datetime.max.time()).strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            ),
        }

        next_token = None
        while True:
            if next_token:
                params["pagination_token"] = next_token

            data = self._request("GET", f"/users/{self._user_id}/tweets", params=params)
            tweets = data.get("data", [])
            if not tweets:
                break

            for tweet in tweets:
                all_tweets.append(tweet)
                if limit and len(all_tweets) >= limit:
                    return self._tweets_to_dataframe(all_tweets)

            meta = data.get("meta", {})
            next_token = meta.get("next_token")
            if not next_token:
                break

        return self._tweets_to_dataframe(all_tweets)

    def get_post_insights(
        self,
        post_id: str,
        metrics: list[str] | None = None,
    ) -> pd.DataFrame:
        """Engagement metrics for a single tweet."""
        self._ensure_connected()
        data = self._request("GET", f"/tweets/{post_id}", params={
            "tweet.fields": "public_metrics,non_public_metrics,organic_metrics,created_at",
        })
        tweet = data.get("data", {})
        public = tweet.get("public_metrics", {})

        rows: list[dict[str, Any]] = []
        metric_keys = metrics or list(public.keys())
        for key in metric_keys:
            if key in public:
                rows.append({
                    "metric": key,
                    "value": public[key],
                    "period": "lifetime",
                })

        return pd.DataFrame(rows)

    # ------------------------------------------------------------------
    # HTTP plumbing
    # ------------------------------------------------------------------

    def _ensure_connected(self) -> None:
        if not self._authenticated:
            raise SocialMediaAuthError(
                "Not authenticated. Call authenticate() first."
            )

    def _check_budget(self) -> None:
        if self._budget_limit is not None and self._estimated_cost >= self._budget_limit:
            raise SocialMediaError(
                f"API budget limit reached: ${self._estimated_cost:.2f} "
                f"(limit: ${self._budget_limit:.2f}). Call reset_cost_tracking() "
                f"to continue or increase budget_limit."
            )

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Send an authenticated request to the X API v2."""
        self._check_budget()
        url = f"{BASE_URL}/{path.lstrip('/')}"
        req_params = dict(params) if params else {}
        last_exc: BaseException | None = None

        for attempt in range(1, self._retry_attempts + 1):
            try:
                resp = self._session.request(
                    method, url,
                    params=req_params,
                    timeout=self._timeout,
                )
            except requests.exceptions.RequestException as exc:
                last_exc = exc
                log.warning(
                    "X API %s %s attempt %d/%d failed: %s",
                    method, url, attempt, self._retry_attempts, exc,
                )
                if attempt < self._retry_attempts:
                    time.sleep(self._retry_backoff ** attempt)
                continue

            self._estimated_cost += COST_PER_READ

            if resp.status_code in (401, 403):
                error_msg = self._extract_error_message(resp)
                raise SocialMediaAuthError(
                    f"X API {resp.status_code}: {error_msg}"
                )

            if resp.status_code == 429:
                retry_after = self._parse_retry_after(resp)
                raise SocialMediaRateLimitError(
                    f"X API rate limit hit on {method} {path}.",
                    retry_after=retry_after,
                )

            if 500 <= resp.status_code < 600:
                last_exc = SocialMediaError(
                    f"X API {resp.status_code} on {method} {path}."
                )
                log.warning(
                    "X API %s %s 5xx %d attempt %d/%d",
                    method, url, resp.status_code, attempt, self._retry_attempts,
                )
                if attempt < self._retry_attempts:
                    time.sleep(self._retry_backoff ** attempt)
                continue

            if not (200 <= resp.status_code < 300):
                error_msg = self._extract_error_message(resp)
                raise SocialMediaError(
                    f"X API {resp.status_code}: {error_msg}"
                )

            try:
                result = resp.json()
            except ValueError as exc:
                raise SocialMediaError(
                    f"X API returned non-JSON on {method} {path}: "
                    f"{resp.text[:200]!r}"
                ) from exc

            remaining = resp.headers.get("x-rate-limit-remaining")
            if remaining is not None:
                try:
                    r = int(remaining)
                    if r <= 5:
                        log.warning("X API rate limit nearly exhausted: %d remaining", r)
                except ValueError:
                    pass

            log.debug(
                "X API %s %s → %d (est. cost: $%.3f)",
                method, path, resp.status_code, self._estimated_cost,
            )
            return result

        raise SocialMediaError(
            f"X API {method} {path} failed after {self._retry_attempts} "
            f"attempts: {last_exc}"
        )

    @staticmethod
    def _extract_error_message(resp: requests.Response) -> str:
        try:
            body = resp.json()
            if "detail" in body:
                return body["detail"]
            errors = body.get("errors", [])
            if errors:
                return errors[0].get("message", resp.text[:200])
            return body.get("title", resp.text[:200])
        except ValueError:
            return resp.text[:200]

    @staticmethod
    def _parse_retry_after(resp: requests.Response) -> float | None:
        reset = resp.headers.get("x-rate-limit-reset")
        if reset:
            try:
                reset_ts = int(reset)
                wait = reset_ts - int(time.time())
                return max(1.0, float(wait))
            except ValueError:
                pass
        return None

    # ------------------------------------------------------------------
    # DataFrame helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _tweets_to_dataframe(tweets: list[dict[str, Any]]) -> pd.DataFrame:
        rows: list[dict[str, Any]] = []
        for t in tweets:
            metrics = t.get("public_metrics", {})
            rows.append({
                "id": t.get("id"),
                "platform": "x_twitter",
                "post_type": "tweet",
                "text": t.get("text"),
                "media_url": None,
                "published_at": t.get("created_at"),
                "permalink": f"https://x.com/i/status/{t.get('id')}" if t.get("id") else None,
                "retweet_count": metrics.get("retweet_count", 0),
                "reply_count": metrics.get("reply_count", 0),
                "like_count": metrics.get("like_count", 0),
                "quote_count": metrics.get("quote_count", 0),
                "bookmark_count": metrics.get("bookmark_count", 0),
                "impression_count": metrics.get("impression_count", 0),
            })
        df = pd.DataFrame(rows)
        if not df.empty:
            log.info("Retrieved %d tweets (est. cost: accumulated in connector)", len(df))
        return df


# ---------------------------------------------------------------------------
# Profile management
# ---------------------------------------------------------------------------


def create_x_account_profile(
    client_id: str,
    username: str,
    bearer_token: str,
) -> dict[str, Any]:
    """Create an X/Twitter account profile linked to a client."""
    return {
        "x_account_id": f"x_{username}",
        "client_id": client_id,
        "username": username,
        "bearer_token": bearer_token,
        "platform": "x_twitter",
        "created_at": datetime.now().isoformat(),
    }


def save_x_account_profile(
    profile: dict[str, Any],
    config_directory: str = "config",
) -> str:
    """Save X/Twitter account profile to JSON file."""
    config_dir = pathlib.Path(config_directory) / "x_twitter"
    config_dir.mkdir(parents=True, exist_ok=True)

    account_id = profile["x_account_id"]
    config_file = config_dir / f"x_account_{account_id}.json"

    with open(config_file, "w", encoding="utf-8") as f:
        json.dump(profile, f, indent=2)

    log.info("Saved X/Twitter profile to %s", config_file)
    return str(config_file)


def load_x_account_profile(
    account_id: str,
    config_directory: str = "config",
) -> dict[str, Any] | None:
    """Load X/Twitter account profile from JSON file."""
    config_dir = pathlib.Path(config_directory) / "x_twitter"
    config_file = config_dir / f"x_account_{account_id}.json"

    if not config_file.exists():
        return None

    with open(config_file, "r", encoding="utf-8") as f:
        return json.load(f)

"""
Salesforce CRM connector — OAuth + connection management.

Provides OAuth 2.0 authentication (Web Server Flow and Username-Password
Flow) and an authenticated HTTP client for the Salesforce REST API.
Implements the auth contract of :class:`ConnectorProtocol`; data
methods (``get_objects``, ``create_record``, etc.) are implemented in
follow-up tickets.

Two auth flows:
- **Web Server Flow** (production): interactive OAuth with redirect.
- **Username-Password Flow** (dev/CI): direct token grant.

Instance URL is discovered from the token response — callers never
hard-code ``na1.salesforce.com`` or similar.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta
from typing import Any, Mapping

import pandas as pd

try:
    import requests

    REQUESTS_AVAILABLE = True
except ImportError:  # pragma: no cover
    REQUESTS_AVAILABLE = False

from siege_utilities.connectors._protocol import (
    ConnectorAuthError,
    ConnectorError,
    ConnectorNotFoundError,
    ConnectorRateLimitError,
    UpsertResult,
)

log = logging.getLogger(__name__)

PRODUCTION_LOGIN_URL = "https://login.salesforce.com"
SANDBOX_LOGIN_URL = "https://test.salesforce.com"
API_VERSION = "v60.0"
DEFAULT_TIMEOUT = 30
DEFAULT_RETRY_ATTEMPTS = 3
DEFAULT_RETRY_BACKOFF = 2.0

__all__ = ["SalesforceConnector"]


class SalesforceConnector:
    """Salesforce CRM connector implementing ConnectorProtocol.

    Usage (Username-Password Flow)::

        from siege_utilities.connectors.salesforce import SalesforceConnector

        sf = SalesforceConnector(
            client_id=os.environ["SF_CLIENT_ID"],
            client_secret=os.environ["SF_CLIENT_SECRET"],
            username=os.environ["SF_USERNAME"],
            password=os.environ["SF_PASSWORD"],
            security_token=os.environ["SF_SECURITY_TOKEN"],
        )
        sf.authenticate()
        print(sf.instance_url)

    Usage (Web Server Flow)::

        sf = SalesforceConnector(
            client_id=os.environ["SF_CLIENT_ID"],
            client_secret=os.environ["SF_CLIENT_SECRET"],
        )
        auth_url = sf.get_authorization_url(redirect_uri="https://myapp/callback")
        # User visits auth_url, gets redirected with ?code=...
        sf.authenticate_with_code(code="...", redirect_uri="https://myapp/callback")
    """

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        *,
        username: str | None = None,
        password: str | None = None,
        security_token: str | None = None,
        login_url: str | None = None,
        sandbox: bool = False,
        timeout: float = DEFAULT_TIMEOUT,
        retry_attempts: int = DEFAULT_RETRY_ATTEMPTS,
        retry_backoff: float = DEFAULT_RETRY_BACKOFF,
    ) -> None:
        if not REQUESTS_AVAILABLE:  # pragma: no cover
            raise ImportError(
                "SalesforceConnector requires `requests`. "
                "Install via `pip install siege-utilities`."
            )
        if not client_id or not client_secret:
            raise ValueError("client_id and client_secret are required.")

        self._client_id = client_id
        self._client_secret = client_secret
        self._username = username
        self._password = password
        self._security_token = security_token or ""
        self._login_url = login_url or (SANDBOX_LOGIN_URL if sandbox else PRODUCTION_LOGIN_URL)
        self._timeout = timeout
        self._retry_attempts = max(1, retry_attempts)
        self._retry_backoff = retry_backoff

        self._access_token: str | None = None
        self._refresh_token: str | None = None
        self._instance_url: str | None = None
        self._token_expires_at: datetime | None = None
        self._authenticated = False

        self._session = requests.Session()
        self._session.headers.update({
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "siege_utilities/SalesforceConnector",
        })
        log.info("SalesforceConnector initialised (login: %s)", self._login_url)

    def close(self) -> None:
        """Close the underlying HTTP session."""
        self._session.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    # ------------------------------------------------------------------
    # ConnectorProtocol — auth contract
    # ------------------------------------------------------------------

    @property
    def provider_name(self) -> str:
        return "salesforce"

    @property
    def instance_url(self) -> str | None:
        """The Salesforce instance URL discovered during authentication."""
        return self._instance_url

    def authenticate(self) -> None:
        """Authenticate using the best available flow.

        If ``username`` and ``password`` were provided, uses the
        Username-Password Flow. Otherwise raises with guidance to use
        ``authenticate_with_code()`` for the Web Server Flow.
        """
        if self._username and self._password:
            self._authenticate_password()
        else:
            raise ConnectorAuthError(
                "No username/password provided. For the Web Server Flow, "
                "call get_authorization_url() then authenticate_with_code(). "
                "For the Username-Password Flow, provide username, password, "
                "and security_token to the constructor."
            )

    def authenticate_with_code(
        self,
        code: str,
        redirect_uri: str,
    ) -> None:
        """Complete the OAuth 2.0 Web Server Flow with an authorization code."""
        token_url = f"{self._login_url}/services/oauth2/token"
        payload = {
            "grant_type": "authorization_code",
            "code": code,
            "client_id": self._client_id,
            "client_secret": self._client_secret,
            "redirect_uri": redirect_uri,
        }
        self._exchange_token(token_url, payload)
        log.info("Authenticated via Web Server Flow (instance: %s)", self._instance_url)

    def get_authorization_url(
        self,
        redirect_uri: str,
        state: str | None = None,
    ) -> str:
        """Generate the OAuth 2.0 authorization URL for the Web Server Flow."""
        params = {
            "response_type": "code",
            "client_id": self._client_id,
            "redirect_uri": redirect_uri,
        }
        if state:
            params["state"] = state
        query = "&".join(f"{k}={v}" for k, v in params.items())
        return f"{self._login_url}/services/oauth2/authorize?{query}"

    def is_connected(self) -> bool:
        """Whether the connector has an active, authenticated session."""
        if not self._authenticated or not self._access_token:
            return False
        if self._token_expires_at and datetime.now() >= self._token_expires_at:
            return False
        return True

    def refresh_access_token(self) -> None:
        """Refresh the access token using the stored refresh token."""
        if not self._refresh_token:
            raise ConnectorAuthError(
                "No refresh token available. Re-authenticate using "
                "authenticate() or authenticate_with_code()."
            )
        token_url = f"{self._login_url}/services/oauth2/token"
        payload = {
            "grant_type": "refresh_token",
            "refresh_token": self._refresh_token,
            "client_id": self._client_id,
            "client_secret": self._client_secret,
        }
        self._exchange_token(token_url, payload)
        log.info("Access token refreshed (instance: %s)", self._instance_url)

    # ------------------------------------------------------------------
    # ConnectorProtocol — data contract (stubs for follow-up tickets)
    # ------------------------------------------------------------------

    def list_object_types(self) -> list[str]:
        """Available Salesforce object types. Implemented in #1016."""
        raise NotImplementedError("list_object_types() — see #1016")

    def get_objects(
        self,
        object_type: str,
        *,
        fields: list[str] | None = None,
        filters: dict[str, Any] | None = None,
        limit: int | None = None,
    ) -> pd.DataFrame:
        """Fetch records. Implemented in #1016."""
        raise NotImplementedError("get_objects() — see #1016")

    def create_record(
        self, object_type: str, data: dict[str, Any]
    ) -> str:
        """Create a single record. Implemented in #1018."""
        raise NotImplementedError("create_record() — see #1018")

    def update_record(
        self, object_type: str, record_id: str, data: dict[str, Any]
    ) -> bool:
        """Update a single record. Implemented in #1018."""
        raise NotImplementedError("update_record() — see #1018")

    def upsert_records(
        self,
        object_type: str,
        records: pd.DataFrame,
        match_field: str,
    ) -> UpsertResult:
        """Bulk upsert from DataFrame. Implemented in #1018/#1019."""
        raise NotImplementedError("upsert_records() — see #1018/#1019")

    # ------------------------------------------------------------------
    # HTTP plumbing
    # ------------------------------------------------------------------

    def _ensure_connected(self) -> None:
        if not self._authenticated:
            raise ConnectorAuthError("Not authenticated. Call authenticate() first.")
        if self._token_expires_at and datetime.now() >= self._token_expires_at:
            if self._refresh_token:
                log.info("Token expired, refreshing...")
                self.refresh_access_token()
            else:
                raise ConnectorAuthError("Access token expired. Re-authenticate.")

    def _authenticate_password(self) -> None:
        """Username-Password Flow."""
        token_url = f"{self._login_url}/services/oauth2/token"
        payload = {
            "grant_type": "password",
            "client_id": self._client_id,
            "client_secret": self._client_secret,
            "username": self._username,
            "password": f"{self._password}{self._security_token}",
        }
        self._exchange_token(token_url, payload)
        log.info(
            "Authenticated via Username-Password Flow as %s (instance: %s)",
            self._username, self._instance_url,
        )

    def _exchange_token(self, token_url: str, payload: dict[str, str]) -> None:
        """Exchange credentials for an access token."""
        try:
            resp = self._session.post(
                token_url,
                data=payload,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=self._timeout,
            )
        except requests.exceptions.RequestException as exc:
            raise ConnectorAuthError(f"Token request failed: {exc}") from exc

        if resp.status_code != 200:
            try:
                body = resp.json()
                error = body.get("error_description", body.get("error", resp.text[:200]))
            except ValueError:
                error = resp.text[:200]
            raise ConnectorAuthError(
                f"Salesforce auth failed ({resp.status_code}): {error}"
            )

        data = resp.json()
        self._access_token = data["access_token"]
        self._refresh_token = data.get("refresh_token", self._refresh_token)
        self._instance_url = data["instance_url"]
        self._session.headers["Authorization"] = f"Bearer {self._access_token}"
        self._authenticated = True

        issued_at = data.get("issued_at")
        if issued_at:
            try:
                issued = datetime.fromtimestamp(int(issued_at) / 1000)
                self._token_expires_at = issued + timedelta(hours=2)
            except (ValueError, OSError):
                self._token_expires_at = datetime.now() + timedelta(hours=2)
        else:
            self._token_expires_at = datetime.now() + timedelta(hours=2)

    def request(
        self,
        method: str,
        path: str,
        *,
        params: Mapping[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Send an authenticated request to the Salesforce REST API.

        Args:
            method: HTTP method (GET, POST, PATCH, DELETE).
            path: API path relative to instance URL
                (e.g., ``/services/data/v60.0/sobjects/Contact``).
            params: Query parameters.
            json_body: JSON request body.

        Returns:
            Parsed JSON response.
        """
        self._ensure_connected()
        url = f"{self._instance_url}{path}"
        last_exc: BaseException | None = None

        for attempt in range(1, self._retry_attempts + 1):
            try:
                resp = self._session.request(
                    method, url,
                    params=dict(params) if params else None,
                    json=json_body,
                    timeout=self._timeout,
                )
            except requests.exceptions.RequestException as exc:
                last_exc = exc
                log.warning(
                    "Salesforce %s %s attempt %d/%d failed: %s",
                    method, path, attempt, self._retry_attempts, exc,
                )
                if attempt < self._retry_attempts:
                    time.sleep(self._retry_backoff ** attempt)
                continue

            if resp.status_code in (401, 403):
                error_msg = self._extract_error(resp)
                raise ConnectorAuthError(
                    f"Salesforce {resp.status_code}: {error_msg}"
                )

            if resp.status_code == 429:
                retry_after = resp.headers.get("Retry-After")
                raise ConnectorRateLimitError(
                    f"Salesforce rate limit hit on {method} {path}.",
                    retry_after=float(retry_after) if retry_after else None,
                )

            if resp.status_code == 404:
                raise ConnectorNotFoundError(
                    f"Salesforce resource not found: {path}"
                )

            if 500 <= resp.status_code < 600:
                last_exc = ConnectorError(
                    f"Salesforce {resp.status_code} on {method} {path}."
                )
                log.warning(
                    "Salesforce %s %s 5xx %d attempt %d/%d",
                    method, path, resp.status_code, attempt, self._retry_attempts,
                )
                if attempt < self._retry_attempts:
                    time.sleep(self._retry_backoff ** attempt)
                continue

            if resp.status_code == 204:
                return {}

            if not (200 <= resp.status_code < 300):
                error_msg = self._extract_error(resp)
                raise ConnectorError(
                    f"Salesforce {resp.status_code}: {error_msg}"
                )

            try:
                return resp.json()
            except ValueError as exc:
                raise ConnectorError(
                    f"Salesforce returned non-JSON on {method} {path}: "
                    f"{resp.text[:200]!r}"
                ) from exc

        raise ConnectorError(
            f"Salesforce {method} {path} failed after {self._retry_attempts} "
            f"attempts: {last_exc}"
        )

    @staticmethod
    def _extract_error(resp: requests.Response) -> str:
        try:
            body = resp.json()
            if isinstance(body, list) and body:
                return body[0].get("message", str(body))
            if isinstance(body, dict):
                return body.get("message", body.get("error", resp.text[:200]))
            return resp.text[:200]
        except ValueError:
            return resp.text[:200]

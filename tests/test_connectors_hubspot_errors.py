"""Error-path coverage (SU-4b) for siege_utilities.connectors.hubspot.

Forces constructor validation, the not-authenticated guard, token-expiry
with no refresh token, the OAuth authenticate() branch, auth-required
guards for each public CRM method, and every distinct branch of the HTTP-
status handler in HubSpotConnector.request() — 401/403 →
ConnectorAuthError, 429 → ConnectorRateLimitError (with and without
Retry-After parsing), 404 → ConnectorNotFoundError, 5xx retries then
raises ConnectorError, 4xx-other with server-message extraction, 204 →
empty dict, non-JSON 2xx → ConnectorError, transport errors exhausting
all retries → ConnectorError, _extract_error text fallback, both
_exchange_token ConnectorAuthError paths (transport + non-200), and the
create_record no-ID guard.
"""

from datetime import datetime, timedelta

import pytest
import requests

from siege_utilities.connectors._protocol import (
    ConnectorAuthError,
    ConnectorError,
    ConnectorNotFoundError,
    ConnectorRateLimitError,
)
from siege_utilities.connectors.hubspot import HubSpotConnector


class _FakeResp:
    def __init__(self, status_code, *, json_body=None, text="", headers=None, json_raises=False):
        self.status_code = status_code
        self._json_body = json_body
        self.text = text
        self.headers = headers or {}
        self._json_raises = json_raises

    def json(self):
        if self._json_raises:
            raise ValueError("not json")
        return self._json_body if self._json_body is not None else {}


class _FakeSession:
    def __init__(self, *, response=None, raise_exc=None):
        self._response = response
        self._raise_exc = raise_exc
        self.headers = {}

    def request(self, method, url, **kwargs):
        if self._raise_exc is not None:
            raise self._raise_exc
        return self._response

    def close(self):
        pass


def _connector():
    """Authenticated connector (private-app token, retry_attempts=1)."""
    c = HubSpotConnector(access_token="tok", retry_attempts=1)
    c._authenticated = True
    c._token_expires_at = None
    return c


def _authed_connector(retry_attempts=1, retry_backoff=0.0):
    """Return a connector wired past _ensure_connected without live auth.

    Bypasses the OAuth handshake by seeding the connector's private auth
    state directly — the tests below exercise request() error branches,
    not authenticate().
    """
    c = HubSpotConnector(
        client_id="id",
        client_secret="secret",
        retry_attempts=retry_attempts,
        retry_backoff=retry_backoff,
    )
    c._authenticated = True
    c._access_token = "test-token"
    c._token_expires_at = None
    c._session.headers["Authorization"] = "Bearer test-token"
    return c


# ---------------------------------------------------------------------------
# Constructor validation
# ---------------------------------------------------------------------------


def test_constructor_requires_credentials():
    with pytest.raises(ValueError) as exc_info:
        HubSpotConnector()
    assert "access_token" in str(exc_info.value)


@pytest.mark.parametrize(
    "client_id,client_secret",
    [("id", ""), ("", "secret"), ("", "")],
)
def test_constructor_oauth_requires_both_client_id_and_secret(client_id, client_secret):
    with pytest.raises(ValueError) as exc_info:
        HubSpotConnector(client_id=client_id, client_secret=client_secret)
    assert "access_token" in str(exc_info.value)


# ---------------------------------------------------------------------------
# _ensure_connected guards
# ---------------------------------------------------------------------------


def test_ensure_connected_raises_when_not_authenticated():
    c = HubSpotConnector(access_token="tok")
    c._authenticated = False
    with pytest.raises(ConnectorAuthError):
        c._ensure_connected()


def test_ensure_connected_raises_when_access_token_expired_no_refresh():
    """_ensure_connected raises ConnectorAuthError when the token is expired
    and no refresh_token is available — the else branch at line 678."""
    c = HubSpotConnector(access_token="tok")
    c._authenticated = True
    c._access_token = "expired"
    c._token_expires_at = datetime.now() - timedelta(seconds=1)
    c._refresh_token = None
    with pytest.raises(ConnectorAuthError) as exc_info:
        c._ensure_connected()
    assert "expired" in str(exc_info.value).lower()


# ---------------------------------------------------------------------------
# authenticate() — OAuth mode raises immediately
# ---------------------------------------------------------------------------


def test_authenticate_raises_in_oauth_mode():
    """authenticate() in OAuth mode (no access_token) raises ConnectorAuthError
    directing the caller to use the authorization code flow."""
    c = HubSpotConnector(client_id="id", client_secret="secret")
    with pytest.raises(ConnectorAuthError) as exc_info:
        c.authenticate()
    assert "get_authorization_url" in str(exc_info.value)


# ---------------------------------------------------------------------------
# Auth-required guards for public CRM methods
# ---------------------------------------------------------------------------


def test_get_objects_requires_authentication():
    c = HubSpotConnector(access_token="tok")
    with pytest.raises(ConnectorAuthError):
        c.get_objects("contacts")


def test_get_associations_requires_authentication():
    c = HubSpotConnector(access_token="tok")
    with pytest.raises(ConnectorAuthError):
        c.get_associations("contacts", "001", "companies")


def test_create_record_requires_authentication():
    c = HubSpotConnector(access_token="tok")
    with pytest.raises(ConnectorAuthError):
        c.create_record("contacts", {"email": "x@example.com"})


def test_update_record_requires_authentication():
    c = HubSpotConnector(access_token="tok")
    with pytest.raises(ConnectorAuthError):
        c.update_record("contacts", "001", {"email": "y@example.com"})


# ---------------------------------------------------------------------------
# request() — HTTP-status matrix
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("status", [401, 403])
def test_request_raises_auth_error_on_401_403(status):
    c = _connector()
    c._session = _FakeSession(response=_FakeResp(status, json_body={"message": "bad"}))
    with pytest.raises(ConnectorAuthError):
        c.request("GET", "/crm/v3/objects/contacts")


def test_request_raises_rate_limit_on_429():
    c = _connector()
    c._session = _FakeSession(response=_FakeResp(429, headers={"Retry-After": "30"}))
    with pytest.raises(ConnectorRateLimitError):
        c.request("GET", "/crm/v3/objects/contacts")


def test_request_429_retry_after_is_parsed(monkeypatch):
    """Retry-After header value is cast to float and stored on
    ConnectorRateLimitError.retry_after."""
    c = _authed_connector()
    monkeypatch.setattr(
        c._session, "request",
        lambda *a, **k: _FakeResp(429, headers={"Retry-After": "17"}),
    )
    with pytest.raises(ConnectorRateLimitError) as exc_info:
        c.request("GET", "/crm/v3/objects/contacts")
    assert exc_info.value.retry_after == 17.0


def test_request_429_without_retry_after_header(monkeypatch):
    """429 without a Retry-After header → retry_after=None on the exception."""
    c = _authed_connector()
    monkeypatch.setattr(
        c._session, "request",
        lambda *a, **k: _FakeResp(429),
    )
    with pytest.raises(ConnectorRateLimitError) as exc_info:
        c.request("GET", "/crm/v3/objects/contacts")
    assert exc_info.value.retry_after is None


def test_request_raises_not_found_on_404():
    c = _connector()
    c._session = _FakeSession(response=_FakeResp(404))
    with pytest.raises(ConnectorNotFoundError):
        c.request("GET", "/crm/v3/objects/missing")


def test_request_5xx_retries_then_raises(monkeypatch):
    """5xx response enters the retry loop; ConnectorError fires after all
    retry_attempts are exhausted, and the loop ran exactly retry_attempts times."""
    c = _authed_connector(retry_attempts=2, retry_backoff=0.0)
    calls = []

    def _resp(*a, **k):
        calls.append(1)
        return _FakeResp(503)

    monkeypatch.setattr(c._session, "request", _resp)
    with pytest.raises(ConnectorError) as exc_info:
        c.request("GET", "/crm/v3/objects/contacts")
    assert len(calls) == 2
    assert "failed after 2 attempts" in str(exc_info.value)


def test_request_raises_error_on_4xx():
    c = _connector()
    c._session = _FakeSession(response=_FakeResp(400, json_body={"message": "bad request"}))
    with pytest.raises(ConnectorError):
        c.request("GET", "/crm/v3/objects/contacts")


def test_request_4xx_other_extracts_server_message(monkeypatch):
    """4xx other than 401/403/404/429 raises ConnectorError carrying the
    status code and the extracted server message."""
    c = _authed_connector()
    monkeypatch.setattr(
        c._session, "request",
        lambda *a, **k: _FakeResp(
            422,
            json_body={"message": "INVALID_PROPERTY: unknown field"},
        ),
    )
    with pytest.raises(ConnectorError) as exc_info:
        c.request("POST", "/crm/v3/objects/contacts/search")
    assert "422" in str(exc_info.value)
    assert "INVALID_PROPERTY" in str(exc_info.value)


def test_request_204_returns_empty_dict(monkeypatch):
    c = _authed_connector()
    monkeypatch.setattr(
        c._session, "request",
        lambda *a, **k: _FakeResp(204),
    )
    result = c.request("DELETE", "/crm/v3/objects/contacts/001")
    assert result == {}


def test_request_raises_on_non_json_2xx():
    c = _connector()
    c._session = _FakeSession(response=_FakeResp(200, json_raises=True, text="<html>"))
    with pytest.raises(ConnectorError) as exc_info:
        c.request("GET", "/crm/v3/objects/contacts")
    assert "non-JSON" in str(exc_info.value)


def test_request_retries_then_raises_on_request_exception():
    c = _connector()  # retry_attempts=1 — no backoff sleep
    c._session = _FakeSession(raise_exc=requests.exceptions.ConnectionError("boom"))
    with pytest.raises(ConnectorError) as exc_info:
        c.request("GET", "/crm/v3/objects/contacts")
    assert "failed after" in str(exc_info.value)


def test_request_transport_error_count_verified(monkeypatch):
    """Every retry_attempt fires before the final ConnectorError is raised."""
    c = _authed_connector(retry_attempts=3, retry_backoff=0.0)
    calls = []

    def _boom(*a, **k):
        calls.append(1)
        raise requests.exceptions.ConnectionError("net down")

    monkeypatch.setattr(c._session, "request", _boom)
    with pytest.raises(ConnectorError) as exc_info:
        c.request("GET", "/crm/v3/objects/contacts")
    assert len(calls) == 3
    assert "failed after 3 attempts" in str(exc_info.value)


# ---------------------------------------------------------------------------
# _extract_error fallback path
# ---------------------------------------------------------------------------


def test_extract_error_falls_back_to_text_on_non_json(monkeypatch):
    """_extract_error returns resp.text[:200] when resp.json() raises ValueError.
    Exercised through the 4xx-other path with json_raises."""
    c = _authed_connector()
    monkeypatch.setattr(
        c._session, "request",
        lambda *a, **k: _FakeResp(
            418,
            text="I'm a teapot — plain text error from a load balancer",
            json_raises=True,
        ),
    )
    with pytest.raises(ConnectorError) as exc_info:
        c.request("GET", "/crm/v3/objects/contacts")
    assert "418" in str(exc_info.value)
    assert "teapot" in str(exc_info.value)


# ---------------------------------------------------------------------------
# _exchange_token — ConnectorAuthError paths
# ---------------------------------------------------------------------------


def test_exchange_token_wraps_transport_error(monkeypatch):
    c = _connector()

    def boom(*a, **k):
        raise requests.exceptions.ConnectionError("network down")

    monkeypatch.setattr(c._session, "post", boom)
    with pytest.raises(ConnectorAuthError) as exc_info:
        c._exchange_token("https://api.hubapi.com/oauth/v1/token", {"grant_type": "refresh_token"})
    assert "Token request failed" in str(exc_info.value)


def test_exchange_token_raises_on_non_200(monkeypatch):
    c = _connector()
    monkeypatch.setattr(
        c._session, "post",
        lambda *a, **k: _FakeResp(400, json_body={"message": "bad_grant"}),
    )
    with pytest.raises(ConnectorAuthError):
        c._exchange_token("https://api.hubapi.com/oauth/v1/token", {"grant_type": "refresh_token"})


def test_exchange_token_non_200_falls_back_to_text_when_not_json(monkeypatch):
    """When _exchange_token receives a non-200 response whose body is not
    valid JSON, it falls back to resp.text[:200] in the error message."""
    c = _connector()
    monkeypatch.setattr(
        c._session, "post",
        lambda *a, **k: _FakeResp(
            503,
            text="Service Unavailable — upstream gateway timeout",
            json_raises=True,
        ),
    )
    with pytest.raises(ConnectorAuthError) as exc_info:
        c._exchange_token("https://api.hubapi.com/oauth/v1/token", {"grant_type": "refresh_token"})
    assert "503" in str(exc_info.value)
    assert "Unavailable" in str(exc_info.value)


# ---------------------------------------------------------------------------
# create_record — no-ID guard
# ---------------------------------------------------------------------------


def test_create_record_raises_when_response_has_no_id(monkeypatch):
    """create_record raises ConnectorError when the HubSpot response
    does not contain an 'id' field."""
    c = _authed_connector()
    monkeypatch.setattr(
        c._session, "request",
        lambda *a, **k: _FakeResp(200, json_body={"properties": {}}),
    )
    with pytest.raises(ConnectorError) as exc_info:
        c.create_record("contacts", {"email": "test@example.com"})
    assert "returned no ID" in str(exc_info.value)

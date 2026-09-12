"""Error-path coverage (SU-4b) for siege_utilities.connectors.dynamics.

Forces constructor validation, both MSAL auth-failure paths
(client-credentials and username/password), the no-credentials guard in
authenticate(), the not-authenticated guard, the token-expiry
re-authentication branch, auth-required guards for every public CRM
method, and every distinct branch of the HTTP-status handler in
DynamicsConnector.request() -- 401/403 -> ConnectorAuthError, 429 ->
ConnectorRateLimitError (with and without Retry-After parsing), 404 ->
ConnectorNotFoundError, 5xx retries-then-raises with exact call-count
verification, 4xx-other with OData error extraction, 204 -> empty dict,
non-JSON 2xx -> ConnectorError, transport errors exhausting all retries ->
ConnectorError with retry count, and all three _extract_error branches
(OData dict, non-dict error value, non-JSON body). Uses real exception
classes and a real-shape fake session/response (writing-tests:4).
"""

from datetime import datetime, timedelta
from unittest.mock import MagicMock

import pytest
import requests

pytest.importorskip("msal")  # DynamicsConnector requires msal at construction

from siege_utilities.connectors._protocol import (  # noqa: E402
    ConnectorAuthError,
    ConnectorError,
    ConnectorNotFoundError,
    ConnectorRateLimitError,
)
from siege_utilities.connectors.dynamics import DynamicsConnector  # noqa: E402


class _FakeResp:
    def __init__(
        self, status_code, *, json_body=None, text="", headers=None, json_raises=False
    ):
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
        self.headers = {}  # _set_token() writes Authorization here

    def request(self, method, url, **kwargs):
        if self._raise_exc is not None:
            raise self._raise_exc
        return self._response

    def close(self):
        pass


def _connector(*, authenticated=True, retry_attempts=1, retry_backoff=0.0):
    """Bypass MSAL construction; seed only attributes request()/_ensure_connected() need.

    Uses DynamicsConnector.__new__() to skip the constructor so tests run
    without a live Azure tenant. The _msal_app stub is a MagicMock so
    authenticate() tests can configure return_value without network I/O.
    """
    c = DynamicsConnector.__new__(DynamicsConnector)
    c._environment_url = "https://example.crm.dynamics.com"
    c._timeout = 30
    c._retry_attempts = max(1, retry_attempts)
    c._retry_backoff = retry_backoff
    c._authenticated = authenticated
    c._token_expires_at = None
    c._access_token = "tok" if authenticated else None
    c._client_secret = "secret"
    c._username = None
    c._password = None
    c._scope = ["https://example.crm.dynamics.com/.default"]
    c._msal_app = MagicMock()
    c._session = _FakeSession()
    return c


# ---------------------------------------------------------------------------
# Constructor validation
# ---------------------------------------------------------------------------


def test_constructor_requires_core_args():
    """environment_url='' trips the ValueError before MSAL app construction."""
    with pytest.raises(ValueError) as exc_info:
        DynamicsConnector(environment_url="", tenant_id="t", client_id="c")
    assert "are required" in str(exc_info.value)


def test_constructor_requires_tenant_id():
    """tenant_id='' also triggers the required-args ValueError."""
    with pytest.raises(ValueError) as exc_info:
        DynamicsConnector(
            environment_url="https://org.crm.dynamics.com",
            tenant_id="",
            client_id="c",
        )
    assert "are required" in str(exc_info.value)


# ---------------------------------------------------------------------------
# authenticate() -- no-credentials guard
# ---------------------------------------------------------------------------


def test_authenticate_raises_with_no_credentials():
    """authenticate() with neither client_secret nor username/password raises
    ConnectorAuthError naming both accepted auth modes."""
    c = _connector()
    c._client_secret = None
    c._username = None
    c._password = None
    with pytest.raises(ConnectorAuthError) as exc_info:
        c.authenticate()
    msg = str(exc_info.value)
    assert "client_secret" in msg or "username" in msg


# ---------------------------------------------------------------------------
# MSAL auth-failure paths
# ---------------------------------------------------------------------------


def test_auth_client_credentials_failure_raises_auth_error():
    """_auth_client_credentials() raises ConnectorAuthError when MSAL returns
    a result without access_token (error path at line ~303)."""
    c = _connector()
    c._msal_app.acquire_token_for_client.return_value = {
        "error": "invalid_client",
        "error_description": "No application found.",
    }
    with pytest.raises(ConnectorAuthError) as exc_info:
        c._auth_client_credentials()
    assert "No application found" in str(exc_info.value)


def test_auth_username_password_failure_raises_auth_error():
    """_auth_username_password() raises ConnectorAuthError when MSAL returns
    a result without access_token (error path at line ~315)."""
    c = _connector()
    c._username = "user@example.com"
    c._password = "bad-password"
    c._msal_app.acquire_token_by_username_password.return_value = {
        "error": "invalid_grant",
        "error_description": "AADSTS50126: Invalid credentials.",
    }
    with pytest.raises(ConnectorAuthError) as exc_info:
        c._auth_username_password()
    assert "AADSTS50126" in str(exc_info.value)


# ---------------------------------------------------------------------------
# _ensure_connected guards
# ---------------------------------------------------------------------------


def test_ensure_connected_raises_when_not_authenticated():
    c = _connector(authenticated=False)
    with pytest.raises(ConnectorAuthError):
        c._ensure_connected()


def test_ensure_connected_triggers_reauth_on_expired_token():
    """When the token has expired _ensure_connected() calls authenticate(),
    which calls _auth_client_credentials(). The MSAL mock returns a fresh
    token so the connector re-authenticates cleanly."""
    c = _connector()
    c._token_expires_at = datetime.now() - timedelta(seconds=1)
    c._msal_app.acquire_token_for_client.return_value = {
        "access_token": "new-tok",
        "expires_in": 3600,
    }
    c._ensure_connected()
    assert c._access_token == "new-tok"


# ---------------------------------------------------------------------------
# Auth-required guards for public CRM methods
# ---------------------------------------------------------------------------


def test_list_object_types_requires_authentication():
    c = _connector(authenticated=False)
    with pytest.raises(ConnectorAuthError):
        c.list_object_types()


def test_get_objects_requires_authentication():
    c = _connector(authenticated=False)
    with pytest.raises(ConnectorAuthError):
        c.get_objects("contacts")


def test_create_record_requires_authentication():
    c = _connector(authenticated=False)
    with pytest.raises(ConnectorAuthError):
        c.create_record("contacts", {"firstname": "Ada"})


def test_update_record_requires_authentication():
    c = _connector(authenticated=False)
    with pytest.raises(ConnectorAuthError):
        c.update_record("contacts", "abc-123", {"firstname": "Grace"})


# ---------------------------------------------------------------------------
# request() -- every HTTP-status branch forced to fire
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("status", [401, 403])
def test_request_raises_auth_error_on_401_403(status):
    c = _connector()
    c._session = _FakeSession(
        response=_FakeResp(status, json_body={"error": {"message": "bad token"}})
    )
    with pytest.raises(ConnectorAuthError):
        c.request("GET", "/api/data/v9.2/accounts")


def test_request_429_retry_after_is_parsed():
    """Retry-After header value is cast to float and stored on
    ConnectorRateLimitError.retry_after."""
    c = _connector()
    c._session = _FakeSession(
        response=_FakeResp(429, headers={"Retry-After": "17"})
    )
    with pytest.raises(ConnectorRateLimitError) as exc_info:
        c.request("GET", "/api/data/v9.2/accounts")
    assert exc_info.value.retry_after == 17.0


def test_request_429_without_retry_after_header():
    """429 with no Retry-After header -> retry_after=None on the exception."""
    c = _connector()
    c._session = _FakeSession(response=_FakeResp(429))
    with pytest.raises(ConnectorRateLimitError) as exc_info:
        c.request("GET", "/api/data/v9.2/accounts")
    assert exc_info.value.retry_after is None


def test_request_raises_not_found_on_404():
    c = _connector()
    c._session = _FakeSession(response=_FakeResp(404))
    with pytest.raises(ConnectorNotFoundError):
        c.request("GET", "/api/data/v9.2/missing")


def test_request_5xx_retries_exact_count():
    """5xx path enters the retry loop; ConnectorError fires after all
    retry_attempts are exhausted, and the response handler ran exactly
    retry_attempts times."""
    call_log = []

    class _CountingSession:
        def request(self, method, url, **kwargs):
            call_log.append(1)
            return _FakeResp(503)

        def close(self):
            pass

    c = _connector(retry_attempts=2, retry_backoff=0.0)
    c._session = _CountingSession()
    with pytest.raises(ConnectorError) as exc_info:
        c.request("GET", "/api/data/v9.2/accounts")
    assert len(call_log) == 2
    assert "failed after 2 attempts" in str(exc_info.value)


def test_request_4xx_extracts_odata_error_message():
    """4xx other than 401/403/404/429 raises ConnectorError carrying the
    status code and the OData error.message field."""
    c = _connector()
    c._session = _FakeSession(
        response=_FakeResp(
            400,
            json_body={"error": {"code": "0x80040265", "message": "Required field missing"}},
        )
    )
    with pytest.raises(ConnectorError) as exc_info:
        c.request("POST", "/api/data/v9.2/contacts")
    assert "400" in str(exc_info.value)
    assert "Required field missing" in str(exc_info.value)


def test_request_204_returns_empty_dict():
    """204 No Content returns {} without attempting to parse a body."""
    c = _connector()
    c._session = _FakeSession(response=_FakeResp(204))
    result = c.request("PATCH", "/api/data/v9.2/contacts(abc-123)")
    assert result == {}


def test_request_raises_on_non_json_2xx():
    c = _connector()
    c._session = _FakeSession(response=_FakeResp(200, json_raises=True, text="<html>"))
    with pytest.raises(ConnectorError) as exc_info:
        c.request("GET", "/api/data/v9.2/accounts")
    assert "non-JSON" in str(exc_info.value)


def test_request_retries_then_raises_on_request_exception():
    """Single-attempt connector exhausts immediately and reports failed after
    1 attempt."""
    c = _connector(retry_attempts=1)
    c._session = _FakeSession(
        raise_exc=requests.exceptions.ConnectionError("boom")
    )
    with pytest.raises(ConnectorError) as exc_info:
        c.request("GET", "/api/data/v9.2/accounts")
    assert "failed after" in str(exc_info.value)


def test_request_transport_error_count_verified():
    """All retry_attempts fire before the final ConnectorError is raised."""
    call_log = []

    class _BoomSession:
        def request(self, method, url, **kwargs):
            call_log.append(1)
            raise requests.exceptions.ConnectionError("net down")

        def close(self):
            pass

    c = _connector(retry_attempts=3, retry_backoff=0.0)
    c._session = _BoomSession()
    with pytest.raises(ConnectorError) as exc_info:
        c.request("GET", "/api/data/v9.2/accounts")
    assert len(call_log) == 3
    assert "failed after 3 attempts" in str(exc_info.value)


# ---------------------------------------------------------------------------
# _extract_error -- all three branches
# ---------------------------------------------------------------------------


def test_extract_error_falls_back_to_text_on_non_json():
    """_extract_error returns resp.text[:200] when resp.json() raises ValueError.
    Exercised through the 4xx-other path with json_raises=True."""
    c = _connector()
    c._session = _FakeSession(
        response=_FakeResp(
            418,
            text="I'm a teapot -- plain text from a load balancer",
            json_raises=True,
        )
    )
    with pytest.raises(ConnectorError) as exc_info:
        c.request("GET", "/api/data/v9.2/accounts")
    assert "418" in str(exc_info.value)
    assert "teapot" in str(exc_info.value)


def test_extract_error_odata_non_dict_error_value():
    """When body["error"] is not a dict (e.g. a plain string),
    _extract_error falls through to str(error) or resp.text[:200]."""
    c = _connector()
    c._session = _FakeSession(
        response=_FakeResp(
            400,
            json_body={"error": "SOME_CODE"},
            text="SOME_CODE",
        )
    )
    with pytest.raises(ConnectorError) as exc_info:
        c.request("GET", "/api/data/v9.2/accounts")
    assert "400" in str(exc_info.value)


def test_extract_error_non_dict_body():
    """When resp.json() returns a list (not a dict), _extract_error returns
    resp.text[:200], falling through to the outer `return resp.text[:200]`."""
    c = _connector()
    c._session = _FakeSession(
        response=_FakeResp(
            400,
            json_body=[{"code": "ERR_001", "detail": "bad payload"}],
            text="bad payload",
        )
    )
    with pytest.raises(ConnectorError) as exc_info:
        c.request("GET", "/api/data/v9.2/accounts")
    assert "400" in str(exc_info.value)

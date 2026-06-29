"""Error-path coverage (SU-4b) for siege_utilities.connectors.dynamics.

Forces constructor validation, the not-authenticated guard, the full
request() HTTP status matrix, the non-JSON guard, and the
RequestException retry-exhaustion path. Uses real exception classes and a
real-shape fake session/response (writing-tests:4).
"""

import pytest
import requests

pytest.importorskip("msal")  # DynamicsConnector requires msal at construction

from siege_utilities.connectors._protocol import (
    ConnectorAuthError,
    ConnectorError,
    ConnectorNotFoundError,
    ConnectorRateLimitError,
)
from siege_utilities.connectors.dynamics import DynamicsConnector


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

    def request(self, method, url, **kwargs):
        if self._raise_exc is not None:
            raise self._raise_exc
        return self._response

    def close(self):
        pass


def _connector(*, authenticated=True):
    # DynamicsConnector.__init__ builds an MSAL app that performs network
    # authority discovery, which is unavailable (and undesirable) in a unit
    # test. Construct the instance directly and set only the attributes that
    # request()/_ensure_connected() touch, so the real method logic is
    # exercised without the MSAL handshake.
    c = DynamicsConnector.__new__(DynamicsConnector)
    c._environment_url = "https://example.crm.dynamics.com"
    c._timeout = 30
    c._retry_attempts = 1  # no backoff sleep on the RequestException path
    c._retry_backoff = 2.0
    c._authenticated = authenticated
    c._token_expires_at = None
    c._access_token = "tok"
    return c


def test_constructor_requires_core_args():
    # environment_url="" trips the ValueError before any MSAL app is built.
    with pytest.raises(ValueError) as exc_info:
        DynamicsConnector(environment_url="", tenant_id="t", client_id="c")
    assert "are required" in str(exc_info.value)


def test_ensure_connected_raises_when_not_authenticated():
    c = _connector(authenticated=False)
    with pytest.raises(ConnectorAuthError):
        c._ensure_connected()


@pytest.mark.parametrize("status", [401, 403])
def test_request_raises_auth_error_on_401_403(status):
    c = _connector()
    c._session = _FakeSession(response=_FakeResp(status, json_body={"error": {"message": "bad"}}))
    with pytest.raises(ConnectorAuthError):
        c.request("GET", "/api/data/v9.2/accounts")


def test_request_raises_rate_limit_on_429():
    c = _connector()
    c._session = _FakeSession(response=_FakeResp(429, headers={"Retry-After": "30"}))
    with pytest.raises(ConnectorRateLimitError):
        c.request("GET", "/api/data/v9.2/accounts")


def test_request_raises_not_found_on_404():
    c = _connector()
    c._session = _FakeSession(response=_FakeResp(404))
    with pytest.raises(ConnectorNotFoundError):
        c.request("GET", "/api/data/v9.2/missing")


def test_request_raises_error_on_4xx():
    c = _connector()
    c._session = _FakeSession(response=_FakeResp(400, json_body={"error": {"message": "bad request"}}))
    with pytest.raises(ConnectorError):
        c.request("GET", "/api/data/v9.2/accounts")


def test_request_raises_on_non_json_2xx():
    c = _connector()
    c._session = _FakeSession(response=_FakeResp(200, json_raises=True, text="<html>"))
    with pytest.raises(ConnectorError) as exc_info:
        c.request("GET", "/api/data/v9.2/accounts")
    assert "non-JSON" in str(exc_info.value)


def test_request_retries_then_raises_on_request_exception():
    c = _connector()  # retry_attempts=1 -> no backoff sleep
    c._session = _FakeSession(raise_exc=requests.exceptions.ConnectionError("boom"))
    with pytest.raises(ConnectorError) as exc_info:
        c.request("GET", "/api/data/v9.2/accounts")
    assert "failed after" in str(exc_info.value)

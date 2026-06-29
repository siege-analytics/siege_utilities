"""Error-path coverage (SU-4b) for siege_utilities.connectors.hubspot.

Forces constructor validation, the not-authenticated guard, the full
request() HTTP status matrix, the non-JSON guard, the RequestException
retry-exhaustion path, and both _exchange_token ConnectorAuthError paths.
"""

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
    c = HubSpotConnector(access_token="tok", retry_attempts=1)
    c._authenticated = True
    c._token_expires_at = None
    return c


def test_constructor_requires_credentials():
    with pytest.raises(ValueError) as exc_info:
        HubSpotConnector()
    assert "access_token" in str(exc_info.value)


def test_ensure_connected_raises_when_not_authenticated():
    c = HubSpotConnector(access_token="tok")
    c._authenticated = False
    with pytest.raises(ConnectorAuthError):
        c._ensure_connected()


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


def test_request_raises_not_found_on_404():
    c = _connector()
    c._session = _FakeSession(response=_FakeResp(404))
    with pytest.raises(ConnectorNotFoundError):
        c.request("GET", "/crm/v3/objects/missing")


def test_request_raises_error_on_4xx():
    c = _connector()
    c._session = _FakeSession(response=_FakeResp(400, json_body={"message": "bad request"}))
    with pytest.raises(ConnectorError):
        c.request("GET", "/crm/v3/objects/contacts")


def test_request_raises_on_non_json_2xx():
    c = _connector()
    c._session = _FakeSession(response=_FakeResp(200, json_raises=True, text="<html>"))
    with pytest.raises(ConnectorError) as exc_info:
        c.request("GET", "/crm/v3/objects/contacts")
    assert "non-JSON" in str(exc_info.value)


def test_request_retries_then_raises_on_request_exception():
    c = _connector()  # retry_attempts=1 -> no backoff sleep
    c._session = _FakeSession(raise_exc=requests.exceptions.ConnectionError("boom"))
    with pytest.raises(ConnectorError) as exc_info:
        c.request("GET", "/crm/v3/objects/contacts")
    assert "failed after" in str(exc_info.value)


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

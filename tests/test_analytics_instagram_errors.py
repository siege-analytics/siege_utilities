"""Error-path coverage (SU-4b) for siege_utilities.analytics.instagram.

Forces the constructor validation, the not-authenticated guard, the HTTP
status-code raises in _request_url, the non-JSON guard, and the
``except requests.exceptions.RequestException`` retry-exhaustion path.
"""

import pytest
import requests

from siege_utilities.analytics.instagram import (
    InstagramConnector,
    SocialMediaAuthError,
    SocialMediaError,
    SocialMediaRateLimitError,
)


class _FakeResp:
    """Minimal stand-in for requests.Response used by _request_url."""

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
    """Stand-in for requests.Session.request: returns a response or raises."""

    def __init__(self, *, response=None, raise_exc=None):
        self._response = response
        self._raise_exc = raise_exc
        self.closed = False

    def request(self, method, url, **kwargs):
        if self._raise_exc is not None:
            raise self._raise_exc
        return self._response

    def close(self):
        self.closed = True


def _connector():
    c = InstagramConnector("tok", retry_attempts=1)
    return c


def test_constructor_rejects_empty_access_token():
    with pytest.raises(ValueError) as exc_info:
        InstagramConnector("")
    assert "access_token is required" in str(exc_info.value)


def test_ensure_connected_raises_when_not_authenticated():
    c = _connector()
    with pytest.raises(SocialMediaAuthError) as exc_info:
        c._ensure_connected()
    assert "Not authenticated" in str(exc_info.value)


@pytest.mark.parametrize("status", [401, 403])
def test_request_url_raises_auth_error_on_401_403(status):
    c = _connector()
    c._session = _FakeSession(response=_FakeResp(status, json_body={"error": {"message": "bad token"}}))
    with pytest.raises(SocialMediaAuthError):
        c._request_url("GET", "https://graph.facebook.com/v1/me")


def test_request_url_raises_rate_limit_on_429():
    c = _connector()
    c._session = _FakeSession(response=_FakeResp(429, headers={"Retry-After": "30"}))
    with pytest.raises(SocialMediaRateLimitError):
        c._request_url("GET", "https://graph.facebook.com/v1/me")


def test_request_url_raises_error_on_4xx():
    c = _connector()
    c._session = _FakeSession(response=_FakeResp(400, json_body={"error": {"message": "bad request"}}))
    with pytest.raises(SocialMediaError):
        c._request_url("GET", "https://graph.facebook.com/v1/me")


def test_request_url_raises_on_non_json_200():
    c = _connector()
    c._session = _FakeSession(response=_FakeResp(200, json_raises=True, text="<html>not json</html>"))
    with pytest.raises(SocialMediaError) as exc_info:
        c._request_url("GET", "https://graph.facebook.com/v1/me")
    assert "non-JSON" in str(exc_info.value)


def test_request_url_retries_then_raises_on_request_exception():
    c = _connector()  # retry_attempts=1 -> no backoff sleep
    c._session = _FakeSession(raise_exc=requests.exceptions.ConnectionError("boom"))
    with pytest.raises(SocialMediaError) as exc_info:
        c._request_url("GET", "https://graph.facebook.com/v1/me")
    assert "failed after" in str(exc_info.value)

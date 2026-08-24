"""Error-path coverage (SU-4b) for siege_utilities.connectors.salesforce.

Forces the constructor validation, the not-authenticated guard, both
ConnectorAuthError paths in _exchange_token (transport + non-200), the
access-token-expired branch of _ensure_connected, the SOQLQuery
validation, and every distinct branch of the HTTP-status handler in
SalesforceConnector.request() — 401/403 → ConnectorAuthError, 429 →
ConnectorRateLimitError (with Retry-After parsing), 404 →
ConnectorNotFoundError, 5xx retries then raises ConnectorError, 4xx
(other) → ConnectorError with extracted server message, 204 → empty
dict, non-JSON 2xx → ConnectorError, transport errors exhausting all
retries → ConnectorError.
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
from siege_utilities.connectors.salesforce import (
    SOQLQuery,
    SalesforceConnector,
)


class _FakeResp:
    def __init__(
        self, status_code, *, json_body=None, text="", json_raises=False, headers=None
    ):
        self.status_code = status_code
        self._json_body = json_body
        self.text = text
        self._json_raises = json_raises
        self.headers = headers or {}

    def json(self):
        if self._json_raises:
            raise ValueError("not json")
        return self._json_body if self._json_body is not None else {}


def _connector():
    return SalesforceConnector(client_id="id", client_secret="secret", retry_attempts=1)


def _authed_connector(retry_attempts=1, retry_backoff=0.01):
    """Return a connector wired past _ensure_connected without live auth.

    Bypasses the OAuth handshake by seeding the connector's private auth
    state directly — the tests below exercise request() error branches,
    not authenticate().
    """
    c = SalesforceConnector(
        client_id="id",
        client_secret="secret",
        retry_attempts=retry_attempts,
        retry_backoff=retry_backoff,
    )
    c._authenticated = True
    c._access_token = "test-token"
    c._instance_url = "https://na1.salesforce.test"
    # No expiry → skip the token-refresh branch.
    c._token_expires_at = None
    return c


@pytest.mark.parametrize(
    "client_id,client_secret",
    [("", "secret"), ("id", ""), ("", "")],
)
def test_constructor_requires_client_id_and_secret(client_id, client_secret):
    with pytest.raises(ValueError) as exc_info:
        SalesforceConnector(client_id=client_id, client_secret=client_secret)
    assert "client_id and client_secret are required" in str(exc_info.value)


def test_ensure_connected_raises_when_not_authenticated():
    c = _connector()
    with pytest.raises(ConnectorAuthError) as exc_info:
        c._ensure_connected()
    assert "Not authenticated" in str(exc_info.value)


# NOTE (writing-tests:1 retroactive-fix corollary): these four methods were
# NotImplementedError stubs at this PR's original base. The CRM workstream
# (#1015-1033) reimplemented them; they now route through request() ->
# _ensure_connected(), so on an unauthenticated connector each raises
# ConnectorAuthError. Tests rewritten to assert the new contract (auth is
# enforced before any data call) and renamed to match; coverage preserved.
def test_list_object_types_requires_authentication():
    with pytest.raises(ConnectorAuthError):
        _connector().list_object_types()


def test_get_objects_requires_authentication():
    with pytest.raises(ConnectorAuthError):
        _connector().get_objects("Account")


def test_create_record_requires_authentication():
    with pytest.raises(ConnectorAuthError):
        _connector().create_record("Account", {"Name": "Acme"})


def test_update_record_requires_authentication():
    with pytest.raises(ConnectorAuthError):
        _connector().update_record("Account", "001", {"Name": "Acme"})


def test_exchange_token_wraps_transport_error(monkeypatch):
    c = _connector()

    def boom(*a, **k):
        raise requests.exceptions.ConnectionError("network down")

    monkeypatch.setattr(c._session, "post", boom)
    with pytest.raises(ConnectorAuthError) as exc_info:
        c._exchange_token("https://login.test/token", {"grant_type": "password"})
    assert "Token request failed" in str(exc_info.value)


def test_exchange_token_raises_on_non_200(monkeypatch):
    c = _connector()

    monkeypatch.setattr(
        c._session, "post",
        lambda *a, **k: _FakeResp(400, json_body={"error_description": "invalid_grant"}),
    )
    with pytest.raises(ConnectorAuthError) as exc_info:
        c._exchange_token("https://login.test/token", {"grant_type": "password"})
    assert "auth failed (400)" in str(exc_info.value)


def test_ensure_connected_raises_when_access_token_expired():
    """_ensure_connected raises ConnectorAuthError when the token expired
    and there's no refresh_token — the alternative branch to the refresh
    path at line 1147."""
    c = _connector()
    c._authenticated = True
    c._access_token = "expired"
    c._token_expires_at = datetime.now() - timedelta(seconds=1)
    c._refresh_token = None
    with pytest.raises(ConnectorAuthError) as exc_info:
        c._ensure_connected()
    assert "Access token expired" in str(exc_info.value)


# ---------------------------------------------------------------------------
# SOQLQuery — build validation raises
# ---------------------------------------------------------------------------


def test_soql_query_build_requires_from():
    q = SOQLQuery().select("Id", "Name")
    with pytest.raises(ValueError) as exc_info:
        q.build()
    assert "from_()" in str(exc_info.value)


def test_soql_query_build_requires_at_least_one_field():
    q = SOQLQuery().from_("Account")
    with pytest.raises(ValueError) as exc_info:
        q.build()
    assert "at least one field" in str(exc_info.value)


# ---------------------------------------------------------------------------
# request() — every HTTP-status branch forced to fire
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("status", [401, 403])
def test_request_401_or_403_maps_to_auth_error(monkeypatch, status):
    c = _authed_connector()
    monkeypatch.setattr(
        c._session, "request",
        lambda *a, **k: _FakeResp(status, json_body={"message": "bad token"}),
    )
    with pytest.raises(ConnectorAuthError) as exc_info:
        c.request("GET", "/services/data/v60.0/sobjects/Account")
    assert str(status) in str(exc_info.value)


def test_request_429_maps_to_rate_limit_with_retry_after(monkeypatch):
    c = _authed_connector()
    monkeypatch.setattr(
        c._session, "request",
        lambda *a, **k: _FakeResp(429, headers={"Retry-After": "17"}),
    )
    with pytest.raises(ConnectorRateLimitError) as exc_info:
        c.request("GET", "/services/data/v60.0/sobjects/Account")
    assert exc_info.value.retry_after == 17.0


def test_request_429_without_retry_after_header(monkeypatch):
    c = _authed_connector()
    monkeypatch.setattr(
        c._session, "request",
        lambda *a, **k: _FakeResp(429),
    )
    with pytest.raises(ConnectorRateLimitError) as exc_info:
        c.request("GET", "/services/data/v60.0/sobjects/Account")
    assert exc_info.value.retry_after is None


def test_request_404_maps_to_not_found(monkeypatch):
    c = _authed_connector()
    monkeypatch.setattr(
        c._session, "request",
        lambda *a, **k: _FakeResp(404),
    )
    with pytest.raises(ConnectorNotFoundError) as exc_info:
        c.request("GET", "/services/data/v60.0/sobjects/Unknown")
    assert "Unknown" in str(exc_info.value)


def test_request_5xx_retries_then_raises(monkeypatch):
    """5xx path enters the retry loop, then raises ConnectorError when
    attempts are exhausted (the final `raise ConnectorError(...)` after
    the for-loop at line 1293)."""
    c = _authed_connector(retry_attempts=2, retry_backoff=0.0)
    calls = []

    def _resp(*a, **k):
        calls.append(1)
        return _FakeResp(503)

    monkeypatch.setattr(c._session, "request", _resp)
    with pytest.raises(ConnectorError) as exc_info:
        c.request("GET", "/services/data/v60.0/sobjects/Account")
    # Should have hit the 5xx branch retry_attempts times.
    assert len(calls) == 2
    assert "failed after 2 attempts" in str(exc_info.value)


def test_request_4xx_other_raises_connector_error_with_extracted_message(
    monkeypatch,
):
    c = _authed_connector()
    monkeypatch.setattr(
        c._session, "request",
        lambda *a, **k: _FakeResp(
            422,
            json_body=[{"message": "MALFORMED_QUERY: line 1 col 5"}],
        ),
    )
    with pytest.raises(ConnectorError) as exc_info:
        c.request("GET", "/services/data/v60.0/query")
    # Non-401/404/429/5xx path names the status and extracted message.
    assert "422" in str(exc_info.value)
    assert "MALFORMED_QUERY" in str(exc_info.value)


def test_request_204_returns_empty_dict(monkeypatch):
    c = _authed_connector()
    monkeypatch.setattr(
        c._session, "request",
        lambda *a, **k: _FakeResp(204),
    )
    result = c.request("DELETE", "/services/data/v60.0/sobjects/Account/001")
    assert result == {}


def test_request_2xx_non_json_raises_connector_error(monkeypatch):
    c = _authed_connector()
    monkeypatch.setattr(
        c._session, "request",
        lambda *a, **k: _FakeResp(200, text="<html>oops</html>", json_raises=True),
    )
    with pytest.raises(ConnectorError) as exc_info:
        c.request("GET", "/services/data/v60.0/sobjects/Account")
    assert "non-JSON" in str(exc_info.value)


def test_request_transport_error_exhausted_raises_connector_error(monkeypatch):
    """All attempts raise a RequestException — after retry_attempts the
    final `raise ConnectorError(... "failed after ... attempts")` fires."""
    c = _authed_connector(retry_attempts=3, retry_backoff=0.0)
    calls = []

    def _boom(*a, **k):
        calls.append(1)
        raise requests.exceptions.ConnectionError("network down")

    monkeypatch.setattr(c._session, "request", _boom)
    with pytest.raises(ConnectorError) as exc_info:
        c.request("GET", "/services/data/v60.0/sobjects/Account")
    assert len(calls) == 3
    assert "failed after 3 attempts" in str(exc_info.value)


def test_extract_error_falls_back_to_text_on_non_json(monkeypatch):
    """_extract_error's ValueError branch when resp.json() raises returns
    resp.text[:200]. Exercised through the 4xx-other path with
    json_raises."""
    c = _authed_connector()
    monkeypatch.setattr(
        c._session, "request",
        lambda *a, **k: _FakeResp(
            418,
            text="I'm a teapot — long HTML error page from an intermediary",
            json_raises=True,
        ),
    )
    with pytest.raises(ConnectorError) as exc_info:
        c.request("GET", "/anything")
    assert "418" in str(exc_info.value)
    assert "teapot" in str(exc_info.value)

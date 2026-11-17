"""Regression coverage for CRM token renewal and UTC expiry (#1436)."""

import json
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
import requests

from siege_utilities.connectors import dynamics, hubspot, salesforce, zoho
from siege_utilities.connectors._protocol import ConnectorAuthError, ConnectorError


NOW = datetime(2026, 11, 1, 7, 0, tzinfo=timezone.utc)
MODULES = {"salesforce": salesforce, "hubspot": hubspot, "zoho": zoho, "dynamics": dynamics}


def response(status=200, body=None):
    resp = requests.Response()
    resp.status_code = status
    resp._content = json.dumps(body if body is not None else {}).encode()
    return resp


class CachedClient:
    """Model MSAL returning a cached token until it is evicted."""

    def __init__(self):
        self.cached = "old-token"
        self.remove_tokens_for_client = Mock(side_effect=self.clear)
        self.acquire_token_for_client = Mock(side_effect=self.acquire)
        self.acquire_token_by_username_password = Mock(return_value={
            "access_token": "new-token", "expires_in": 3600,
        })

    def clear(self):
        self.cached = None

    def acquire(self, *, scopes):
        return {"access_token": self.cached or "new-token", "expires_in": 3600}


@pytest.fixture(params=MODULES)
def connector(request, monkeypatch):
    provider = request.param
    if provider == "dynamics":
        app = CachedClient()
        monkeypatch.setattr(dynamics, "MSAL_AVAILABLE", True)
        monkeypatch.setattr(dynamics, "msal", SimpleNamespace(
            ConfidentialClientApplication=Mock(return_value=app),
        ), raising=False)
        c = dynamics.DynamicsConnector(
            environment_url="https://dynamics.example.test",
            tenant_id="tenant", client_id="id", client_secret="secret",
            retry_attempts=1,
        )
    else:
        cls = {
            "salesforce": salesforce.SalesforceConnector,
            "hubspot": hubspot.HubSpotConnector,
            "zoho": zoho.ZohoConnector,
        }[provider]
        c = cls(client_id="id", client_secret="secret", retry_attempts=1)
        c._refresh_token = "refresh-token"
    if provider == "salesforce":
        c._instance_url = "https://salesforce.example.test"
    c._authenticated = True
    c._access_token = "old-token"
    c._session.headers["Authorization"] = (
        "Zoho-oauthtoken old-token" if provider == "zoho" else "Bearer old-token"
    )
    c._session.post = Mock(return_value=response(body={
        "access_token": "new-token", "expires_in": 3600,
        "instance_url": "https://salesforce.example.test",
        "issued_at": str(int(NOW.timestamp() * 1000)),
    }))
    c._session.request = Mock(return_value=response(body={"records": [1]}))
    monkeypatch.setattr("time.sleep", Mock())
    yield provider, c
    c.close()


def assert_renewals(provider, c, count):
    if provider == "dynamics":
        assert c._msal_app.acquire_token_for_client.call_count == count
        assert c._msal_app.remove_tokens_for_client.call_count == count
    else:
        assert c._session.post.call_count == count
        if count:
            assert c._session.post.call_args.kwargs["data"]["grant_type"] == "refresh_token"


@pytest.mark.parametrize("method", ["GET", "POST", "PATCH"])
def test_401_refreshes_once_and_replays_with_new_token(connector, method):
    provider, c = connector
    authorizations = []
    responses = iter([response(401), response(body={"records": [1]})])

    def send(*args, **kwargs):
        authorizations.append(c._session.headers["Authorization"])
        return next(responses)

    c._session.request.side_effect = send
    kwargs = {"params": {"page": 1}, "json_body": {"name": "Acme"}}
    if provider == "dynamics":
        kwargs["headers"] = {"Prefer": "return=representation"}
    assert c.request(method, "/records", **kwargs) == {"records": [1]}
    assert c._session.request.call_count == 2
    first, second = c._session.request.call_args_list
    assert first == second
    assert first.args[0] == method
    assert first.kwargs["params"] == kwargs["params"]
    assert first.kwargs["json"] == kwargs["json_body"]
    if provider == "dynamics":
        assert first.kwargs["headers"] == kwargs["headers"]
    scheme = "Zoho-oauthtoken" if provider == "zoho" else "Bearer"
    assert authorizations == [f"{scheme} old-token", f"{scheme} new-token"]
    assert_renewals(provider, c, 1)


def test_repeated_401_stops_after_one_refresh(connector):
    provider, c = connector
    c._retry_attempts = 3
    c._session.request.return_value = response(401)
    with pytest.raises(ConnectorAuthError):
        c.request("GET", "/records")
    assert c._session.request.call_count == 2
    assert_renewals(provider, c, 1)


def test_403_does_not_refresh(connector):
    provider, c = connector
    c._session.request.return_value = response(403)
    with pytest.raises(ConnectorAuthError):
        c.request("GET", "/records")
    c._session.request.assert_called_once()
    assert_renewals(provider, c, 0)


def test_401_without_refresh_capability_raises_once(connector):
    provider, c = connector
    if provider == "dynamics":
        c._client_secret = None
    else:
        c._refresh_token = None
    c._session.request.return_value = response(401)
    with pytest.raises(ConnectorAuthError):
        c.request("GET", "/records")
    c._session.request.assert_called_once()
    assert_renewals(provider, c, 0)


def test_failed_refresh_does_not_replay(connector):
    provider, c = connector
    if provider == "dynamics":
        c._msal_app.acquire_token_for_client.side_effect = None
        c._msal_app.acquire_token_for_client.return_value = {"error": "invalid_client"}
    else:
        c._session.post.return_value = response(400, {"error": "invalid_grant"})
    c._session.request.return_value = response(401)
    with pytest.raises(ConnectorAuthError):
        c.request("GET", "/records")
    c._session.request.assert_called_once()
    assert_renewals(provider, c, 1)


@pytest.mark.parametrize("method", ["POST", "PATCH"])
@pytest.mark.parametrize("failure", ["timeout", "server_error"])
def test_auth_replay_preserves_write_retry_limits(connector, method, failure):
    provider, c = connector
    c._retry_attempts = 3
    c._session.request.side_effect = [
        response(401), requests.Timeout() if failure == "timeout" else response(503),
    ]
    with pytest.raises(ConnectorError):
        c.request(method, "/records")
    assert c._session.request.call_count == 2
    assert_renewals(provider, c, 1)


def test_refresh_limit_survives_server_error_retry(connector):
    provider, c = connector
    c._retry_attempts = 3
    c._session.request.side_effect = [response(401), response(503), response(401)]
    with pytest.raises(ConnectorAuthError):
        c.request("GET", "/records")
    assert c._session.request.call_count == 3
    assert_renewals(provider, c, 1)


def freeze_clock(monkeypatch, provider):
    class UTCClock(datetime):
        @classmethod
        def now(cls, tz=None):
            assert tz is timezone.utc, "Token clocks must use UTC"
            return NOW

    monkeypatch.setattr(MODULES[provider], "datetime", UTCClock)


@pytest.mark.parametrize("seconds", [-1, 30, 60, 61])
def test_utc_expiry_has_sixty_second_refresh_margin(connector, monkeypatch, seconds):
    provider, c = connector
    freeze_clock(monkeypatch, provider)
    c._token_expires_at = NOW + timedelta(seconds=seconds)
    assert c.is_connected() is (seconds > 60)
    assert c.request("GET", "/records") == {"records": [1]}
    c._session.request.assert_called_once()
    assert_renewals(provider, c, int(seconds <= 60))


def test_dst_fallback_cannot_revive_expired_token(connector, monkeypatch):
    provider, c = connector
    freeze_clock(monkeypatch, provider)
    # 01:30 at UTC-05 was half an hour ago, even though the local clock
    # has fallen back to 01:00 at UTC-06.
    c._token_expires_at = datetime(
        2026, 11, 1, 1, 30, tzinfo=timezone(timedelta(hours=-5)),
    )
    assert not c.is_connected()
    c._ensure_connected()
    assert_renewals(provider, c, 1)


@pytest.mark.parametrize("expires_in", [0, 3600, "3600"])
def test_token_expiry_is_utc_and_matches_provider_lifetime(connector, monkeypatch, expires_in):
    provider, c = connector
    freeze_clock(monkeypatch, provider)
    data = {"access_token": "new-token", "expires_in": expires_in,
            "instance_url": "https://salesforce.example.test"}
    if provider == "dynamics":
        c._set_token(data)
    else:
        c._session.post.return_value = response(body=data)
        c.refresh_access_token()
    if provider == "salesforce":
        assert c._token_expires_at is None
    else:
        assert c._token_expires_at.tzinfo is timezone.utc
        assert c._token_expires_at == NOW + timedelta(seconds=int(expires_in))


@pytest.mark.parametrize("issued_at", [None, "invalid", "1793502000000"])
def test_salesforce_does_not_invent_expiry(issued_at):
    c = salesforce.SalesforceConnector(client_id="id", client_secret="secret")
    c._token_expires_at = NOW - timedelta(hours=1)
    data = {"access_token": "new-token", "instance_url": "https://salesforce.example.test"}
    if issued_at is not None:
        data["issued_at"] = issued_at
    c._session.post = Mock(return_value=response(body=data))
    c.authenticate_with_code("code", "https://app.example.test/callback")
    assert c._token_expires_at is None
    assert c.is_connected()
    c.close()


def test_dynamics_401_renews_delegated_credentials(monkeypatch):
    app = CachedClient()
    monkeypatch.setattr(dynamics, "MSAL_AVAILABLE", True)
    monkeypatch.setattr(dynamics, "msal", SimpleNamespace(
        PublicClientApplication=Mock(return_value=app),
    ), raising=False)
    c = dynamics.DynamicsConnector(
        environment_url="https://dynamics.example.test", tenant_id="tenant",
        client_id="id", username="user", password="password", retry_attempts=1,
    )
    c._authenticated = True
    c._access_token = "old-token"
    c._session.request = Mock(side_effect=[response(401), response(body={"records": [1]})])
    assert c.request("GET", "/records") == {"records": [1]}
    assert c._access_token == "new-token"
    app.acquire_token_by_username_password.assert_called_once()
    app.remove_tokens_for_client.assert_not_called()
    c.close()

"""Error-path coverage (SU-4b) for siege_utilities.connectors.zoho.

Forces constructor validation (missing creds + unknown data center), the
not-authenticated guard, the full request() HTTP status matrix (401/403,
429, 404, 4xx-other, 5xx retry exhaustion, 204, non-JSON 2xx),
RequestException retry-exhaustion, both _exchange_token ConnectorAuthError
paths, the error-key-in-200 path, token-expiry refresh/no-refresh guards,
authenticate() without refresh token, _extract_error fallback paths,
create_record/update_record API-error-status paths, and upsert_records
empty-DataFrame and batch-ConnectorError handling.
"""

from datetime import datetime

import pandas as pd
import pytest
import requests

from siege_utilities.connectors._protocol import (
    ConnectorAuthError,
    ConnectorError,
    ConnectorNotFoundError,
    ConnectorRateLimitError,
)
from siege_utilities.connectors.zoho import ZohoConnector


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
    c = ZohoConnector(client_id="id", client_secret="secret", retry_attempts=1)
    c._authenticated = True
    c._token_expires_at = None
    return c


# ---------------------------------------------------------------------------
# Constructor validation
# ---------------------------------------------------------------------------

def test_constructor_requires_client_credentials():
    with pytest.raises(ValueError) as exc_info:
        ZohoConnector(client_id="", client_secret="secret")
    assert "client_id and client_secret are required" in str(exc_info.value)


def test_constructor_rejects_unknown_data_center():
    with pytest.raises(ValueError) as exc_info:
        ZohoConnector(client_id="id", client_secret="secret", data_center="mars")
    assert "data center" in str(exc_info.value).lower()


# ---------------------------------------------------------------------------
# Authentication guards
# ---------------------------------------------------------------------------

def test_ensure_connected_raises_when_not_authenticated():
    c = ZohoConnector(client_id="id", client_secret="secret")
    c._authenticated = False
    with pytest.raises(ConnectorAuthError):
        c._ensure_connected()


def test_ensure_connected_raises_when_token_expired_no_refresh():
    c = ZohoConnector(client_id="id", client_secret="secret")
    c._authenticated = True
    c._token_expires_at = datetime(2000, 1, 1)  # expired; no refresh_token
    with pytest.raises(ConnectorAuthError) as exc_info:
        c._ensure_connected()
    assert "expired" in str(exc_info.value).lower()


def test_ensure_connected_refreshes_when_token_expired_with_refresh_token(monkeypatch):
    c = ZohoConnector(client_id="id", client_secret="secret", refresh_token="tok")
    c._authenticated = True
    c._token_expires_at = datetime(2000, 1, 1)  # expired

    refreshed = []

    def fake_refresh():
        refreshed.append(True)
        c._token_expires_at = None

    monkeypatch.setattr(c, "_refresh_access", fake_refresh)
    c._ensure_connected()  # must not raise
    assert refreshed, "_refresh_access should have been called for an expired token"


def test_authenticate_raises_without_refresh_token():
    c = ZohoConnector(client_id="id", client_secret="secret")
    with pytest.raises(ConnectorAuthError) as exc_info:
        c.authenticate()
    assert "refresh token" in str(exc_info.value).lower()


def test_list_object_types_requires_authentication():
    c = ZohoConnector(client_id="id", client_secret="secret")
    c._authenticated = False
    with pytest.raises(ConnectorAuthError):
        c.list_object_types()


# ---------------------------------------------------------------------------
# request() HTTP status matrix
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("status", [401, 403])
def test_request_raises_auth_error_on_401_403(status):
    c = _connector()
    c._session = _FakeSession(response=_FakeResp(status, json_body={"message": "bad"}))
    with pytest.raises(ConnectorAuthError):
        c.request("GET", "/crm/v5/Contacts")


def test_request_raises_rate_limit_on_429():
    c = _connector()
    c._session = _FakeSession(response=_FakeResp(429, headers={"Retry-After": "30"}))
    with pytest.raises(ConnectorRateLimitError):
        c.request("GET", "/crm/v5/Contacts")


def test_request_raises_not_found_on_404():
    c = _connector()
    c._session = _FakeSession(response=_FakeResp(404))
    with pytest.raises(ConnectorNotFoundError):
        c.request("GET", "/crm/v5/Missing")


def test_request_raises_error_on_4xx():
    c = _connector()
    c._session = _FakeSession(response=_FakeResp(400, json_body={"message": "bad request"}))
    with pytest.raises(ConnectorError):
        c.request("GET", "/crm/v5/Contacts")


def test_request_returns_empty_dict_on_204():
    c = _connector()
    c._session = _FakeSession(response=_FakeResp(204))
    result = c.request("DELETE", "/crm/v6/Contacts/123")
    assert result == {}


def test_request_raises_on_non_json_2xx():
    c = _connector()
    c._session = _FakeSession(response=_FakeResp(200, json_raises=True, text="<html>"))
    with pytest.raises(ConnectorError) as exc_info:
        c.request("GET", "/crm/v5/Contacts")
    assert "non-JSON" in str(exc_info.value)


def test_request_retries_then_raises_on_request_exception():
    c = _connector()  # retry_attempts=1 -> no backoff sleep
    c._session = _FakeSession(raise_exc=requests.exceptions.ConnectionError("boom"))
    with pytest.raises(ConnectorError) as exc_info:
        c.request("GET", "/crm/v5/Contacts")
    assert "failed after" in str(exc_info.value)


def test_request_retries_then_raises_on_5xx():
    c = _connector()  # retry_attempts=1 -> exhausted after one attempt
    c._session = _FakeSession(response=_FakeResp(500, text="internal error"))
    with pytest.raises(ConnectorError) as exc_info:
        c.request("GET", "/crm/v6/Contacts")
    assert "failed after" in str(exc_info.value)


# ---------------------------------------------------------------------------
# _extract_error fallback paths
# ---------------------------------------------------------------------------

def test_extract_error_falls_back_to_text_for_unknown_dict_keys():
    resp = _FakeResp(400, json_body={"code": "REQUIRED_FIELD_MISSING"}, text="fallback text")
    result = ZohoConnector._extract_error(resp)
    assert result == "fallback text"


def test_extract_error_falls_back_to_text_for_non_dict_json():
    resp = _FakeResp(400, json_body=["error", "list"], text="list fallback")
    result = ZohoConnector._extract_error(resp)
    assert result == "list fallback"


def test_extract_error_falls_back_to_text_for_non_json_response():
    resp = _FakeResp(400, json_raises=True, text="plain error text")
    result = ZohoConnector._extract_error(resp)
    assert result == "plain error text"


# ---------------------------------------------------------------------------
# _exchange_token paths
# ---------------------------------------------------------------------------

def test_exchange_token_wraps_transport_error(monkeypatch):
    c = _connector()

    def boom(*a, **k):
        raise requests.exceptions.ConnectionError("network down")

    monkeypatch.setattr(c._session, "post", boom)
    with pytest.raises(ConnectorAuthError) as exc_info:
        c._exchange_token("https://accounts.zoho.com/oauth/v2/token", {"grant_type": "refresh_token"})
    assert "Token request failed" in str(exc_info.value)


def test_exchange_token_raises_on_non_200(monkeypatch):
    c = _connector()
    monkeypatch.setattr(
        c._session, "post",
        lambda *a, **k: _FakeResp(400, json_body={"error": "invalid_client"}),
    )
    with pytest.raises(ConnectorAuthError):
        c._exchange_token("https://accounts.zoho.com/oauth/v2/token", {"grant_type": "refresh_token"})


def test_exchange_token_raises_when_error_key_in_200_response(monkeypatch):
    c = _connector()
    monkeypatch.setattr(
        c._session, "post",
        lambda *a, **k: _FakeResp(
            200,
            json_body={"error": "INVALID_TOKEN", "access_token": None},
        ),
    )
    with pytest.raises(ConnectorAuthError) as exc_info:
        c._exchange_token("https://accounts.zoho.com/oauth/v2/token", {"grant_type": "refresh_token"})
    assert "INVALID_TOKEN" in str(exc_info.value)


# ---------------------------------------------------------------------------
# Write-operation error paths
# ---------------------------------------------------------------------------

def test_create_record_raises_on_api_error_status():
    c = _connector()
    resp_body = {"data": [{"status": "error", "message": "Required field missing"}]}
    c._session = _FakeSession(response=_FakeResp(200, json_body=resp_body))
    with pytest.raises(ConnectorError) as exc_info:
        c.create_record("Contacts", {"First_Name": "Test"})
    assert "Failed to create" in str(exc_info.value)


def test_update_record_raises_on_api_error_status():
    c = _connector()
    resp_body = {"data": [{"status": "error", "message": "Record not found"}]}
    c._session = _FakeSession(response=_FakeResp(200, json_body=resp_body))
    with pytest.raises(ConnectorError) as exc_info:
        c.update_record("Contacts", "ABC123", {"First_Name": "Test"})
    assert "Failed to update" in str(exc_info.value)


def test_upsert_records_returns_zero_counts_for_empty_dataframe():
    c = _connector()
    result = c.upsert_records("Contacts", pd.DataFrame(), match_field="Email")
    assert result.success_count == 0
    assert result.failure_count == 0


def test_upsert_records_wraps_connector_error_as_upsert_error():
    c = _connector()
    # 5xx forces ConnectorError after retry exhaustion; upsert must absorb it
    c._session = _FakeSession(response=_FakeResp(500, text="server error"))
    df = pd.DataFrame({"Email": ["a@b.com"], "First_Name": ["Alice"]})
    result = c.upsert_records("Contacts", df, match_field="Email")
    assert result.failure_count == 1
    assert result.success_count == 0
    assert result.errors, "UpsertError entries must be populated"

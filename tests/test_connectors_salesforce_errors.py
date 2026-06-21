"""Error-path coverage (SU-4b) for siege_utilities.connectors.salesforce.

Forces the constructor validation, the not-authenticated guard, the
not-yet-implemented stubs, and both ConnectorAuthError paths in
_exchange_token (transport failure and non-200 response).
"""

import pytest
import requests

from siege_utilities.connectors._protocol import ConnectorAuthError
from siege_utilities.connectors.salesforce import SalesforceConnector


class _FakeResp:
    def __init__(self, status_code, *, json_body=None, text="", json_raises=False):
        self.status_code = status_code
        self._json_body = json_body
        self.text = text
        self._json_raises = json_raises

    def json(self):
        if self._json_raises:
            raise ValueError("not json")
        return self._json_body if self._json_body is not None else {}


def _connector():
    return SalesforceConnector(client_id="id", client_secret="secret", retry_attempts=1)


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


def test_list_object_types_not_implemented():
    with pytest.raises(NotImplementedError):
        _connector().list_object_types()


def test_get_objects_not_implemented():
    with pytest.raises(NotImplementedError):
        _connector().get_objects("Account")


def test_create_record_not_implemented():
    with pytest.raises(NotImplementedError):
        _connector().create_record("Account", {"Name": "Acme"})


def test_update_record_not_implemented():
    with pytest.raises(NotImplementedError):
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

"""Regression coverage for Dataverse create IDs, with no HTTP or Azure calls."""

import pytest
from requests.structures import CaseInsensitiveDict

from siege_utilities.connectors._protocol import ConnectorError
from siege_utilities.connectors.dynamics import DynamicsConnector


RECORD_ID = "00000000-0000-0000-0000-000000000001"
ENVIRONMENT_URL = "https://org.crm.dynamics.com"


class _FakeResponse:
    def __init__(self, status_code, *, headers=None, body=None):
        self.status_code = status_code
        self.headers = CaseInsensitiveDict(headers or {})
        self._body = body

    def json(self):
        assert self.status_code != 204, "A 204 response has no JSON body"
        return self._body


class _FakeSession:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def request(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        return self.response


def _connector(response):
    # Bypass MSAL construction and install the fake HTTP transport.
    connector = DynamicsConnector.__new__(DynamicsConnector)
    connector._environment_url = ENVIRONMENT_URL
    connector._authenticated = True
    connector._token_expires_at = None
    connector._timeout = 30
    connector._retry_attempts = 1
    connector._session = _FakeSession(response)
    return connector


@pytest.mark.parametrize("object_type", ["opportunities", "accounts"])
@pytest.mark.parametrize("header_name", ["OData-EntityId", "odata-entityid"])
def test_create_record_returns_id_from_204_header(object_type, header_name):
    entity_url = f"{ENVIRONMENT_URL}/api/data/v9.2/{object_type}"
    connector = _connector(_FakeResponse(
        204, headers={header_name: f"{entity_url}({RECORD_ID})"},
    ))
    data = {"name": "Created record"}

    assert connector.create_record(object_type, data) == RECORD_ID
    assert connector._session.calls == [(
        "POST", entity_url, {"params": None, "json": data, "timeout": 30},
    )]


@pytest.mark.parametrize("status_code", [200, 201])
@pytest.mark.parametrize("object_type,id_attribute", [
    ("contacts", "contactid"),
    ("accounts", "accountid"),
    ("opportunities", "opportunityid"),
    ("leads", "leadid"),
    ("tasks", "activityid"),
    ("appointments", "activityid"),
    ("incidents", "incidentid"),
])
def test_create_record_returns_standard_entity_body_id(
    status_code, object_type, id_attribute,
):
    connector = _connector(_FakeResponse(
        status_code, body={id_attribute: RECORD_ID, "name": "Created record"},
    ))

    assert connector.create_record(object_type, {"name": "Created record"}) == RECORD_ID


@pytest.mark.parametrize("link_prefix", ["", f"{ENVIRONMENT_URL}/api/data/v9.2/"])
@pytest.mark.parametrize("object_type", ["opportunities", "new_widgets"])
def test_create_record_returns_id_from_edit_link(link_prefix, object_type):
    connector = _connector(_FakeResponse(200, body={
        "@odata.editLink": f"{link_prefix}{object_type}({RECORD_ID})",
    }))

    assert connector.create_record(object_type, {"name": "Created record"}) == RECORD_ID


def test_create_record_keeps_custom_entity_body_fallback():
    connector = _connector(_FakeResponse(200, body={"new_widgetid": RECORD_ID}))

    assert connector.create_record("new_widgets", {"name": "Created record"}) == RECORD_ID


@pytest.mark.parametrize("status_code,headers,body", [
    (204, {}, None),
    (204, {"OData-EntityId": "opportunities()"}, None),
    (204, {"OData-EntityId": f"opportunities({RECORD_ID}"}, None),
    (200, {}, {}),
    (200, {}, {"@odata.editLink": None, "opportunityid": None}),
])
def test_create_record_raises_when_id_is_missing(status_code, headers, body):
    connector = _connector(_FakeResponse(status_code, headers=headers, body=body))

    with pytest.raises(ConnectorError, match="opportunities.*record id"):
        connector.create_record("opportunities", {"name": "Created record"})
    assert len(connector._session.calls) == 1


def test_request_surfaces_204_entity_id_header():
    entity_id = f"{ENVIRONMENT_URL}/api/data/v9.2/opportunities({RECORD_ID})"
    connector = _connector(_FakeResponse(204, headers={"OData-EntityId": entity_id}))

    assert connector.request("POST", "/api/data/v9.2/opportunities") == {
        "OData-EntityId": entity_id,
    }


@pytest.mark.parametrize("method", ["POST", "PATCH", "DELETE"])
def test_request_keeps_empty_dict_for_204_without_header(method):
    connector = _connector(_FakeResponse(204))

    assert connector.request(method, "/api/data/v9.2/opportunities") == {}


@pytest.mark.parametrize("status_code", [200, 201])
def test_request_keeps_non_204_body_unchanged(status_code):
    body = {"opportunityid": RECORD_ID, "name": "Created record"}
    connector = _connector(_FakeResponse(
        status_code, headers={"OData-EntityId": "ignored"}, body=body,
    ))

    assert connector.request("POST", "/api/data/v9.2/opportunities") == body

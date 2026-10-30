"""Regression tests for CRM pagination boundaries (#1429)."""

from unittest.mock import Mock
from urllib.parse import parse_qs, quote, urlparse
import xml.etree.ElementTree as ET

import pytest
import requests

from siege_utilities.connectors._protocol import ConnectorError
from siege_utilities.connectors.dynamics import DynamicsConnector
from siege_utilities.connectors.hubspot import HubSpotConnector
from siege_utilities.connectors.zoho import ZohoConnector


def connector(provider):
    if provider == "hubspot":
        c = HubSpotConnector(access_token="token")
    elif provider == "zoho":
        c = ZohoConnector(client_id="id", client_secret="secret")
    else:
        c = DynamicsConnector.__new__(DynamicsConnector)
    c._authenticated = True
    c._token_expires_at = None
    return c


def test_zoho_coql_stops_and_truncates_at_limit():
    c = connector("zoho")
    c.request = Mock(side_effect=[
        {"data": [{"id": str(i)} for i in range(75)], "info": {"more_records": True}},
        {"data": [{"id": "extra"}], "info": {"more_records": False}},
    ])
    df = c.get_objects("Contacts", fields=["id"], filters={"Last_Name": "Smith"}, limit=50)
    assert list(df.id) == [str(i) for i in range(50)]
    c.request.assert_called_once()


@pytest.mark.parametrize("limit", [250, None])
def test_zoho_coql_pages_with_offset_and_remaining_count(limit):
    c = connector("zoho")
    c.request = Mock(side_effect=[
        {"data": [{"id": str(i)} for i in range(200)], "info": {"more_records": True}},
        {"data": [{"id": str(i)} for i in range(200, 275)], "info": {"more_records": False}},
    ])
    df = c.get_objects("Contacts", fields=["id"], filters={"Last_Name": "Smith"}, limit=limit)
    assert len(df) == (250 if limit is not None else 275)
    queries = [call.kwargs["json_body"]["select_query"] for call in c.request.call_args_list]
    assert queries[0].endswith("limit 0, 200")
    assert queries[1].endswith(f"limit 200, {50 if limit is not None else 200}")


def test_zoho_list_uses_page_token_after_2000_records():
    c = connector("zoho")
    pages = []
    for page in range(10):
        info = {"more_records": True}
        if page == 9:
            info["next_page_token"] = "token-2000"
        pages.append({"data": [{"id": str(i)} for i in range(page * 200, (page + 1) * 200)], "info": info})
    pages += [
        {"data": [{"id": "2000"}], "info": {"more_records": True, "next_page_token": "token-2001"}},
        {"data": [{"id": "2001"}], "info": {"more_records": False}},
    ]
    c.request = Mock(side_effect=pages)
    df = c.get_objects("Contacts", fields=["id"])
    assert len(df) == 2002
    for call, token in zip(c.request.call_args_list[10:], ["token-2000", "token-2001"]):
        assert call.kwargs["params"]["page_token"] == token
        assert "page" not in call.kwargs["params"]


@pytest.mark.parametrize("provider", ["hubspot", "zoho", "dynamics"])
@pytest.mark.parametrize("filters", [None, {"name": "Acme"}])
def test_zero_limit_returns_empty_without_data_requests(provider, filters):
    c = connector(provider)
    c.request = Mock(return_value={"results": [{"id": "1"}], "data": [{"id": "1"}], "value": [{"id": "1"}]})
    result = c.get_objects("contacts", fields=["name"], filters=filters, limit=0)
    assert result.empty
    assert "name" in result.columns
    c.request.assert_not_called()


def test_fetchxml_follows_encoded_cookie():
    c = connector("dynamics")
    cookie = '<cookie page="1"><contactid last="abc" first="abc" /></cookie>'
    wrapper = f'<cookie pagenumber="2" pagingcookie="{quote(quote(cookie, safe=""), safe="")}" istracking="False" />'
    c.request = Mock(side_effect=[
        {
            "value": [{"contactid": "a"}],
            "@Microsoft.Dynamics.CRM.morerecords": True,
            "@Microsoft.Dynamics.CRM.fetchxmlpagingcookie": wrapper,
        },
        {"value": [{"contactid": "b"}], "@Microsoft.Dynamics.CRM.morerecords": False},
    ])
    df = c.fetch_xml("contacts", '<fetch count="1"><entity name="contact" /></fetch>')
    assert list(df.contactid) == ["a", "b"]
    second = c.request.call_args_list[1]
    query = parse_qs(urlparse(second.args[1]).query).get("fetchXml")
    xml = query[0] if query else second.kwargs["params"]["fetchXml"]
    root = ET.fromstring(xml)
    assert root.get("page") == "2"
    assert root.get("paging-cookie") == cookie
    assert root.get("count") == "1"
    for call in c.request.call_args_list:
        prefer = call.kwargs["headers"]["Prefer"]
        assert "Microsoft.Dynamics.CRM.fetchxmlpagingcookie" in prefer
        assert "Microsoft.Dynamics.CRM.morerecords" in prefer
        assert "OData.Community.Display.V1.FormattedValue" in prefer


def test_fetchxml_requests_paging_annotations_over_http(monkeypatch):
    c = connector("dynamics")
    c._environment_url = "https://dynamics.example.test"
    c._timeout = 30
    c._retry_attempts = 1
    c._session = requests.Session()
    response = requests.Response()
    response.status_code = 200
    response._content = b'{"value": [{"id": "1"}], "@Microsoft.Dynamics.CRM.morerecords": false}'
    send = Mock(return_value=response)
    monkeypatch.setattr(requests.Session, "send", send)
    assert len(c.fetch_xml("contacts", '<fetch><entity name="contact" /></fetch>')) == 1
    sent = send.call_args.args[0]
    assert "Microsoft.Dynamics.CRM.fetchxmlpagingcookie" in sent.headers["Prefer"]
    assert "Microsoft.Dynamics.CRM.morerecords" in sent.headers["Prefer"]


@pytest.mark.parametrize("cookie", [
    "not xml", '<cookie pagenumber="1" />', '<cookie pagenumber="2" />',
    '<cookie pagenumber="2" pagingcookie="bad" />',
])
def test_fetchxml_invalid_cookie_raises(cookie):
    c = connector("dynamics")
    c.request = Mock(return_value={
        "value": [{"id": "1"}],
        "@Microsoft.Dynamics.CRM.morerecords": True,
        "@Microsoft.Dynamics.CRM.fetchxmlpagingcookie": cookie,
    })
    with pytest.raises(ConnectorError, match="[Cc]ookie"):
        c.fetch_xml("contacts", '<fetch><entity name="contact" /></fetch>')
    c.request.assert_called_once()


def test_fetchxml_repeated_cookie_raises():
    c = connector("dynamics")
    c.request = Mock(return_value={
        "value": [{"id": "1"}],
        "@Microsoft.Dynamics.CRM.morerecords": True,
        "@Microsoft.Dynamics.CRM.fetchxmlpagingcookie": '<cookie page="1"><id last="1" /></cookie>',
    })
    with pytest.raises(ConnectorError, match="[Cc]ookie"):
        c.fetch_xml("contacts", '<fetch><entity name="contact" /></fetch>')
    assert c.request.call_count == 2


def test_fetchxml_more_records_without_cookie_is_not_silent():
    c = connector("dynamics")
    c.request = Mock(return_value={"value": [{"id": "1"}], "@Microsoft.Dynamics.CRM.morerecords": True})
    with pytest.raises(ConnectorError, match="[Cc]ookie"):
        c.fetch_xml("contacts", '<fetch><entity name="contact" /></fetch>')


@pytest.mark.parametrize("after", ["10000", "10001"])
def test_hubspot_search_rejects_paging_past_cap(after):
    c = connector("hubspot")
    c.request = Mock(side_effect=[
        {"results": [{"id": "1"}], "paging": {"next": {"after": after}}},
        {"results": []},
    ])
    with pytest.raises(ConnectorError, match="10,?000"):
        c.get_objects("contacts", filters={"name": "Acme"})
    c.request.assert_called_once()


def test_hubspot_search_satisfied_limit_does_not_follow_cap_cursor():
    c = connector("hubspot")
    c.request = Mock(return_value={"results": [{"id": "1"}], "paging": {"next": {"after": "10000"}}})
    assert len(c.get_objects("contacts", filters={"name": "Acme"}, limit=1)) == 1
    c.request.assert_called_once()


def test_hubspot_search_can_return_exactly_10000_rows():
    c = connector("hubspot")
    c.request = Mock(side_effect=[
        {"results": [{"id": str(i)} for i in range(page * 100, (page + 1) * 100)],
         "paging": {"next": {"after": str((page + 1) * 100)}}}
        for page in range(100)
    ])
    df = c.get_objects("contacts", filters={"name": "Acme"}, limit=10000)
    assert len(df) == 10000
    assert c.request.call_count == 100
    assert c.request.call_args.kwargs["json_body"]["after"] == 9900


def test_hubspot_search_page_size_stays_inside_cap():
    c = connector("hubspot")
    c.request = Mock(side_effect=[
        {"results": [{"id": "first"}], "paging": {"next": {"after": "9999"}}},
        {"results": [{"id": "last"}]},
    ])
    assert len(c.get_objects("contacts", filters={"name": "Acme"})) == 2
    assert c.request.call_args.kwargs["json_body"]["limit"] == 1

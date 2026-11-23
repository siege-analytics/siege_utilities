"""Regression tests for encoded CRM OAuth parameters (#1431)."""

from urllib.parse import parse_qs, urlsplit

import pytest

from siege_utilities.connectors.hubspot import HubSpotConnector
from siege_utilities.connectors.salesforce import SalesforceConnector
from siege_utilities.connectors.zoho import ZohoConnector


@pytest.mark.parametrize("provider,cls", [
    ("salesforce", SalesforceConnector),
    ("hubspot", HubSpotConnector),
    ("zoho", ZohoConnector),
])
def test_authorization_parameters_round_trip(provider, cls):
    client_id = "client+id&extra=value"
    redirect_uri = "https://app.example.test/callback?a=b&x=1"
    state = "nonce&injected=value = + / ü"
    c = cls(client_id=client_id, client_secret="secret")
    kwargs = {"redirect_uri": redirect_uri, "state": state}
    expected = {"client_id": [client_id], "redirect_uri": [redirect_uri], "state": [state]}
    if provider == "hubspot":
        scopes = ["crm.objects.contacts.read", "crm.objects.companies.read"]
        kwargs["scopes"] = scopes
        expected["scope"] = [" ".join(scopes)]
    elif provider == "zoho":
        scopes = ["ZohoCRM.modules.ALL", "ZohoCRM.settings.ALL"]
        kwargs["scopes"] = scopes
        expected.update(scope=[",".join(scopes)], response_type=["code"], access_type=["offline"])
    else:
        expected["response_type"] = ["code"]
    url = c.get_authorization_url(**kwargs)
    parsed = urlsplit(url)
    assert parse_qs(parsed.query) == expected
    assert not parsed.fragment
    assert " " not in url
    assert "%2B" in parsed.query
    if provider == "hubspot":
        assert "scope=crm.objects.contacts.read%20crm.objects.companies.read" in parsed.query
    c.close()

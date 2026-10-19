"""Offline regressions for regional CRM endpoints (#1440)."""

import json
from unittest.mock import Mock
from urllib.parse import urlparse

import pytest
import requests

from siege_utilities.connectors import dynamics
from siege_utilities.connectors.zoho import ZohoConnector


@pytest.fixture
def sent(monkeypatch):
    calls = []

    def send(session, request, **kwargs):
        calls.append(request)
        response = requests.Response()
        response.status_code = 200
        response._content = json.dumps(
            {"access_token": "offline-token", "expires_in": 3600}
            if request.url.endswith("/oauth/v2/token") else {"data": []}
        ).encode()
        return response

    monkeypatch.setattr(requests.Session, "send", send)
    return calls


@pytest.mark.parametrize("region,accounts,api", [
    ("ca", "accounts.zohocloud.ca", "www.zohoapis.ca"),
    ("sa", "accounts.zoho.sa", "www.zohoapis.sa"),
    ("cn", "accounts.zoho.com.cn", "www.zohoapis.com.cn"),
])
def test_zoho_regional_endpoints(region, accounts, api, sent):
    with ZohoConnector(client_id="id", client_secret="secret",
                       refresh_token="refresh", data_center=region) as connector:
        connector.authenticate()
        connector.request("GET", "/crm/v6/Contacts")
    assert [urlparse(request.url).hostname for request in sent] == [accounts, api]


@pytest.mark.parametrize("flow", ["refresh", "code"])
def test_zoho_token_api_domain_controls_request_host(flow, monkeypatch):
    sent = []
    payloads = iter([
        {"access_token": "first", "api_domain": "https://www.zohoapis.ca/"},
        {"data": []},
        {"access_token": "second", "api_domain": "https://www.zohoapis.sa"},
        {"data": []},
    ])

    def send(session, request, **kwargs):
        sent.append(request)
        response = requests.Response()
        response.status_code = 200
        response._content = json.dumps(next(payloads)).encode()
        return response

    monkeypatch.setattr(requests.Session, "send", send)
    with ZohoConnector(client_id="id", client_secret="secret",
                       refresh_token="refresh") as connector:
        if flow == "code":
            connector.authenticate_with_code(code="code", redirect_uri="https://app.test/callback")
        else:
            connector.authenticate()
        connector.request("GET", "/crm/v6/Contacts")
        connector.refresh_access_token()
        connector.request("GET", "/crm/v6/Contacts")
    assert sent[1].url == "https://www.zohoapis.ca/crm/v6/Contacts"
    assert sent[3].url == "https://www.zohoapis.sa/crm/v6/Contacts"
    with ZohoConnector(client_id="id", client_secret="secret") as other:
        assert other._dc["api_url"] == "https://www.zohoapis.com"


def test_zoho_without_api_domain_keeps_configured_host(sent):
    with ZohoConnector(client_id="id", client_secret="secret",
                       refresh_token="refresh", data_center="eu") as connector:
        connector.authenticate()
        connector.request("GET", "/crm/v6/Contacts")
    assert sent[-1].url == "https://www.zohoapis.eu/crm/v6/Contacts"


@pytest.mark.parametrize("environment,login", [
    ("https://org.crm.microsoftdynamics.us/", "login.microsoftonline.us"),
    ("https://org.crm.appsplatform.us", "login.microsoftonline.us"),
    ("https://org.crm.dynamics.cn", "login.chinacloudapi.cn"),
    ("https://org.crm.dynamics.com", "login.microsoftonline.com"),
])
@pytest.mark.parametrize("secret", [None, "secret"])
def test_dynamics_environment_selects_authority(environment, login, secret, monkeypatch):
    confidential, public = Mock(), Mock()
    monkeypatch.setattr(dynamics.msal, "ConfidentialClientApplication", confidential)
    monkeypatch.setattr(dynamics.msal, "PublicClientApplication", public)
    with dynamics.DynamicsConnector(environment_url=environment, tenant_id="tenant",
                                    client_id="id", client_secret=secret) as connector:
        factory = confidential if secret else public
        assert factory.call_args.kwargs["authority"] == f"https://{login}/tenant"
        assert connector._scope == [f"{environment.rstrip('/')}/.default"]

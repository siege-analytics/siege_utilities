"""CRM mappings must retain lookup IDs, probability units, and labels (#1426)."""

import json
from unittest.mock import Mock

import pandas as pd
import pytest
import requests

from siege_utilities.connectors.dynamics import DynamicsConnector
from siege_utilities.connectors.hubspot import HubSpotConnector
from siege_utilities.connectors.salesforce import SalesforceConnector
from siege_utilities.connectors.zoho import ZohoConnector


FORMATTED_INDUSTRY = "industrycode@OData.Community.Display.V1.FormattedValue"
FORMATTED_PREFERENCE = 'odata.include-annotations="OData.Community.Display.V1.FormattedValue"'


@pytest.mark.parametrize("filtered", [False, True], ids=["list", "coql"])
@pytest.mark.parametrize("module,field,expected", [
    ("Deals", "owner_id", "owner-123"),
    ("Deals", "account_id", "account-456"),
    ("Contacts", "account_id", "account-456"),
])
def test_zoho_get_objects_maps_lookup_ids(filtered, module, field, expected):
    connector = ZohoConnector.__new__(ZohoConnector)
    connector.request = Mock(return_value={"data": [
        {
            "id": "linked", "Deal_Name": "Renewal", "First_Name": "Ada",
            "Owner": {"id": "owner-123", "name": "Owner Display Name"},
            "Account_Name": {"id": "account-456", "name": "Account Display Name"},
        },
        {
            "id": "unlinked", "Deal_Name": "New deal", "First_Name": "Grace",
            "Owner": None, "Account_Name": None,
        },
    ]})
    frame = connector.get_objects(module, filters={"id": "linked"} if filtered else None)
    # Exercise the actual flattening boundary, where names and IDs separate.
    assert frame.iloc[0]["Account_Name"] == "Account Display Name"
    assert frame.iloc[0]["Account_Name_id"] == "account-456"

    mapper = connector.to_crm_opportunities if module == "Deals" else connector.to_crm_contacts
    linked, unlinked = mapper(frame)

    assert getattr(linked, field) == expected
    assert getattr(unlinked, field) is None
    assert "Account_Name_id" not in linked.metadata
    if module == "Deals":
        assert "Owner_id" not in linked.metadata


@pytest.mark.parametrize("kind", ["contacts", "opportunities"])
@pytest.mark.parametrize("flattened", [False, True], ids=["raw", "companion_id"])
def test_zoho_supports_raw_lookups_and_prefers_companion_ids(kind, flattened):
    connector = ZohoConnector.__new__(ZohoConnector)
    row = {
        "id": "record-1", "Deal_Name": "Renewal",
        "Account_Name": {"id": "raw-account", "name": "Account Display Name"},
        "Owner": {"id": "raw-owner", "name": "Owner Display Name"},
    }
    if flattened:
        row.update(Account_Name_id="flat-account", Owner_id="flat-owner")

    record, = getattr(connector, f"to_crm_{kind}")(pd.DataFrame([row]))

    assert record.account_id == ("flat-account" if flattened else "raw-account")
    if kind == "opportunities":
        assert record.owner_id == ("flat-owner" if flattened else "raw-owner")


@pytest.mark.parametrize("missing", [None, float("nan"), pd.NA])
def test_zoho_display_names_without_ids_are_not_canonical_ids(missing):
    connector = ZohoConnector.__new__(ZohoConnector)
    frame = pd.DataFrame([{
        "id": "record-1", "Deal_Name": "Renewal",
        "Account_Name": "Account Display Name", "Account_Name_id": missing,
        "Owner": "Owner Display Name", "Owner_id": missing,
    }])

    record, = connector.to_crm_opportunities(frame)

    assert record.account_id is None
    assert record.owner_id is None


@pytest.mark.parametrize("percent", [0, 80, 100, None])
def test_get_objects_probabilities_share_percentage_scale(percent):
    fraction = None if percent is None else str(percent / 100)
    cases = [
        (SalesforceConnector, "Opportunity", {"records": [
            {"Id": "deal-1", "Name": "Renewal", "Probability": percent},
        ], "done": True}),
        (HubSpotConnector, "deals", {"results": [
            {"id": "deal-1", "properties": {
                "dealname": "Renewal", "hs_deal_stage_probability": fraction,
            }},
        ]}),
        (ZohoConnector, "Deals", {"data": [
            {"id": "deal-1", "Deal_Name": "Renewal", "Probability": percent},
        ]}),
        (DynamicsConnector, "opportunities", {"value": [
            {"opportunityid": "deal-1", "name": "Renewal", "closeprobability": percent},
        ]}),
    ]
    probabilities = []
    for cls, object_type, response in cases:
        connector = cls.__new__(cls)
        connector._authenticated = True
        connector._token_expires_at = None
        connector.request = Mock(return_value=response)

        record, = connector.to_crm_opportunities(connector.get_objects(object_type))

        probabilities.append(record.probability)
    assert probabilities == [percent] * len(cases)


@pytest.mark.parametrize("fraction,expected", [(0, 0), (0.8, 80), (1, 100), (None, None)])
def test_hubspot_nested_properties_use_percentage_scale(fraction, expected):
    connector = HubSpotConnector.__new__(HubSpotConnector)
    frame = pd.DataFrame([{"id": "deal-1", "properties": {
        "dealname": "Renewal", "hs_deal_stage_probability": fraction,
    }}])

    record, = connector.to_crm_opportunities(frame)

    assert record.probability == expected


def test_dynamics_maps_formatted_industry_label():
    connector = DynamicsConnector.__new__(DynamicsConnector)
    frame = pd.DataFrame([{
        "accountid": "account-1", "name": "Acme", "industrycode": 7,
        FORMATTED_INDUSTRY: "Consulting",
    }])

    account, = connector.to_crm_accounts(frame)

    assert account.industry == "Consulting"
    assert FORMATTED_INDUSTRY not in account.metadata


@pytest.mark.parametrize("annotation", [None, float("nan"), pd.NA, ""])
def test_dynamics_falls_back_to_industry_code_without_label(annotation):
    connector = DynamicsConnector.__new__(DynamicsConnector)
    frame = pd.DataFrame([{
        "accountid": "account-1", "name": "Acme", "industrycode": 7,
        FORMATTED_INDUSTRY: annotation,
    }])

    account, = connector.to_crm_accounts(frame)

    assert account.industry == "7"


def test_dynamics_requests_formatted_values_on_every_page(monkeypatch):
    # Keep real constructor/session/request handling; only replace auth setup
    # and the HTTP transport so the outgoing preference is observable.
    monkeypatch.setattr("siege_utilities.connectors.dynamics.MSAL_AVAILABLE", True)
    monkeypatch.setattr("siege_utilities.connectors.dynamics.msal", Mock(), raising=False)
    connector = DynamicsConnector(
        environment_url="https://dynamics.example.test", tenant_id="test-tenant",
        client_id="test-id", client_secret="test-secret", retry_attempts=1,
    )
    connector._authenticated = True
    responses = []
    for page, label in [(1, "Consulting"), (2, "Manufacturing")]:
        body = {"value": [{
            "accountid": f"account-{page}", "name": f"Account {page}",
            "industrycode": page, FORMATTED_INDUSTRY: label,
        }]}
        if page == 1:
            body["@odata.nextLink"] = f"{connector._environment_url}/api/data/v9.2/accounts?$skiptoken=next"
        response = requests.Response()
        response.status_code = 200
        response._content = json.dumps(body).encode("utf-8")
        responses.append(response)
    send = Mock(side_effect=responses)
    monkeypatch.setattr(requests.Session, "send", send)

    frame = connector.get_objects("accounts")

    assert send.call_count == 2
    for call in send.call_args_list:
        request = call.args[0]
        assert request.headers.get("Prefer") == FORMATTED_PREFERENCE
    assert [record.industry for record in connector.to_crm_accounts(frame)] == [
        "Consulting", "Manufacturing",
    ]

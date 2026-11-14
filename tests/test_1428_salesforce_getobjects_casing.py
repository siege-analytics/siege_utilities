"""Regression coverage for Salesforce field resolution (#1428)."""

from unittest.mock import Mock

import pytest

from siege_utilities.connectors.salesforce import SalesforceConnector


@pytest.fixture
def record():
    return {
        "attributes": {"type": "Contact"},
        "Name": "Acme",
        "Account": {
            "attributes": {"type": "Account"},
            "Name": "Parent",
        },
    }


def test_clean_records_resolves_relationship_fields(record):
    assert SalesforceConnector._clean_records(
        [record], ["Name", "Account.Name"]
    ) == [{"Name": "Acme", "Account.Name": "Parent"}]


@pytest.mark.parametrize(
    "field,expected",
    [
        ("name", "Acme"),
        ("NAME", "Acme"),
        ("account.Name", "Parent"),
        ("Account.name", "Parent"),
        ("aCcOuNt.nAmE", "Parent"),
    ],
)
def test_clean_records_matches_each_segment_case_insensitively(record, field, expected):
    assert SalesforceConnector._clean_records([record], [field]) == [{field: expected}]


def test_clean_records_resolves_multiple_relationship_levels():
    record = {"Account": {"Owner": {"Name": "Ada"}}}
    field = "account.OWNER.name"

    assert SalesforceConnector._clean_records([record], [field]) == [{field: "Ada"}]


@pytest.mark.parametrize(
    "record,field",
    [
        ({"Name": "Acme"}, "Missing"),
        ({"Name": "Acme"}, "Account.Name"),
        ({"Account": {}}, "Account.Name"),
        ({"Account": None}, "account.Name"),
        ({"Account": "not a relationship object"}, "Account.Name"),
        ({"Account": {"Owner": None}}, "Account.Owner.Name"),
    ],
)
def test_clean_records_returns_none_for_missing_fields_or_relationships(record, field):
    assert SalesforceConnector._clean_records([record], [field]) == [{field: None}]


@pytest.mark.parametrize("value", [0, False, "", None])
def test_clean_records_preserves_falsy_values(value):
    record = {"Custom__c": value, "Account": {"Custom__c": value}}
    fields = ["Custom__c", "custom__c", "account.custom__c"]

    assert SalesforceConnector._clean_records([record], fields) == [
        {field: value for field in fields}
    ]


@pytest.mark.parametrize("empty", [False, True])
def test_get_objects_preserves_requested_columns(monkeypatch, record, empty):
    session = Mock()
    session.request.return_value = Mock(
        status_code=200,
        json=Mock(return_value={"records": [] if empty else [record], "done": True}),
    )
    monkeypatch.setattr("siege_utilities.connectors.salesforce.requests.Session", lambda: session)
    connector = SalesforceConnector(client_id="test-id", client_secret="test-secret")
    connector._authenticated = True
    connector._access_token = "test-token"
    connector._instance_url = "https://salesforce.test"
    fields = ["name", "aCcOuNt.nAmE", "Missing"]

    result = connector.get_objects("Contact", fields=fields)

    assert list(result.columns) == fields
    assert result.to_dict("records") == (
        [] if empty else [{"name": "Acme", "aCcOuNt.nAmE": "Parent", "Missing": None}]
    )
    session.request.assert_called_once()
    assert session.request.call_args.kwargs["params"] == {
        "q": "SELECT name, aCcOuNt.nAmE, Missing FROM Contact"
    }

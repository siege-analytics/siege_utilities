"""Identifier injection regressions for structured CRM query builders."""

from unittest.mock import Mock

import pytest

from siege_utilities.connectors.dynamics import DynamicsConnector
from siege_utilities.connectors.salesforce import SalesforceConnector, SOQLQuery
from siege_utilities.connectors.zoho import ZohoConnector


@pytest.mark.parametrize("identifier", [None, b"Name", 42, [], {}])
def test_identifier_validator_rejects_non_strings(identifier):
    from siege_utilities.connectors._query_utils import _validate_identifier

    with pytest.raises(ValueError, match="identifier"):
        _validate_identifier(identifier, allow_dotted=True)


@pytest.mark.parametrize("value", [None, True, 42, ["x"], "x"])
def test_dynamics_identifier_injection(value):
    with pytest.raises(ValueError, match="identifier"):
        DynamicsConnector._build_odata_filter(
            {"fullname eq 'a' or 1 eq 1 or fullname": value}
        )


@pytest.mark.parametrize("position", ["match_field", "entity_set"])
def test_dynamics_batch_identifier_injection(position):
    connector = DynamicsConnector.__new__(DynamicsConnector)
    connector._ensure_connected = Mock()
    connector._session = Mock()
    args = {"entity_set": "contacts", "match_field": "name"}
    args[position] = "name='x',accountnumber"

    with pytest.raises(ValueError, match="identifier"):
        connector._batch_upsert(records=[{"name": "x"}], **args)

    connector._ensure_connected.assert_not_called()
    connector._session.post.assert_not_called()


@pytest.mark.parametrize("position", ["filter", "module", "fields"])
def test_zoho_identifier_injection(position):
    connector = ZohoConnector.__new__(ZohoConnector)
    connector.request = Mock(return_value={"data": []})
    malicious = "Last_Name = 'a' or 1 = 1 or Last_Name"
    args = {"module": "Contacts", "fields": ["Last_Name"], "filters": {"Last_Name": "x"}}
    if position == "filter":
        args["filters"] = {malicious: "x"}
    elif position == "fields":
        args["fields"] = ["Last_Name", malicious]
    else:
        args["module"] = malicious

    with pytest.raises(ValueError, match="identifier"):
        connector._coql_query(**args, limit=None)

    connector.request.assert_not_called()


@pytest.mark.parametrize("position", ["filter", "object_type", "fields"])
def test_salesforce_identifier_injection(position):
    connector = SalesforceConnector.__new__(SalesforceConnector)
    malicious = "Name = 'a' OR Id != null OR Name"
    args = {"object_type": "Contact", "fields": ["Name"], "filters": {"Name": "x"}}
    if position == "filter":
        args["filters"] = {malicious: "x"}
    elif position == "fields":
        args["fields"] = ["Name", malicious]
    else:
        args["object_type"] = malicious

    with pytest.raises(ValueError, match="identifier"):
        connector._build_soql(**args)


@pytest.mark.parametrize("method", ["select", "from_", "where", "order_by"])
def test_soql_builder_identifier_injection(method):
    query = SOQLQuery().select("Id").from_("Contact")
    kwargs = {"eq": "x"} if method == "where" else {}

    with pytest.raises(ValueError, match="identifier"):
        getattr(query, method)("Name DESC LIMIT 1", **kwargs)


@pytest.mark.parametrize(
    "identifier",
    ["", "1Name", "Name ", "Name\n", "Name\r\n", "A..B", ".Name", "Name.",
     "Name=Id", "Name'", 'Name"', "COUNT(Id)", "A/B", "Name%27", "Nämé", None],
)
@pytest.mark.parametrize("connector", ["dynamics", "zoho", "salesforce"])
def test_malformed_identifier_rejected(identifier, connector):
    with pytest.raises(ValueError, match="identifier"):
        if connector == "dynamics":
            DynamicsConnector._build_odata_filter({identifier: "x"})
        elif connector == "zoho":
            zoho = ZohoConnector.__new__(ZohoConnector)
            zoho.request = Mock(return_value={"data": []})
            zoho._coql_query("Contacts", [identifier], {}, None)
        else:
            SOQLQuery().where(identifier, eq="x")


def test_dynamics_valid_identifiers():
    assert DynamicsConnector._build_odata_filter(
        {"_parentcustomerid_value": "x", "Custom__c": "y", "name2": "z"}
    ) == "_parentcustomerid_value eq 'x' and Custom__c eq 'y' and name2 eq 'z'"
    with pytest.raises(ValueError, match="identifier"):
        DynamicsConnector._build_odata_filter({"Account.Name": "x"})


def test_zoho_valid_relationship_identifiers():
    connector = ZohoConnector.__new__(ZohoConnector)
    connector.request = Mock(return_value={"data": []})
    connector._coql_query(
        "Custom_Module", ["Account.Name", "Custom__c", "A.B.C"],
        {"Account.Owner.Name": "Alice", "_custom2": None}, None,
    )
    assert connector.request.call_args.kwargs["json_body"]["select_query"] == (
        "select Account.Name, Custom__c, A.B.C from Custom_Module "
        "where Account.Owner.Name = 'Alice' and _custom2 is null"
    )


def test_salesforce_valid_relationship_identifiers():
    connector = SalesforceConnector.__new__(SalesforceConnector)
    fields = ["Account.Name", "Custom__c", "Parent__r.Owner.Name"]
    assert connector._build_soql(
        "Custom_Object__c", fields=fields, filters={"Parent__r.Name": "Alice"},
    ) == (
        "SELECT Account.Name, Custom__c, Parent__r.Owner.Name FROM Custom_Object__c "
        "WHERE Parent__r.Name = 'Alice'"
    )
    assert (
        SOQLQuery().select(*fields).from_("Custom_Object__c")
        .where("Parent__r.Name", eq="Alice").order_by("Account.Name").build()
    ) == (
        "SELECT Account.Name, Custom__c, Parent__r.Owner.Name FROM Custom_Object__c "
        "WHERE Parent__r.Name = 'Alice' ORDER BY Account.Name ASC"
    )

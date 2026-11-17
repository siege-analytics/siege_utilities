"""Regression coverage for connector filter literals without live CRM services."""

import re
from unittest.mock import Mock
from urllib.parse import quote, unquote, urlsplit

import pytest

from siege_utilities.connectors.dynamics import DynamicsConnector
from siege_utilities.connectors.zoho import ZohoConnector


@pytest.mark.parametrize("as_list", [False, True], ids=["scalar", "list"])
@pytest.mark.parametrize(
    ("value", "literal"),
    [
        ("O'Brien", "'O''Brien'"),
        ("Smith", "'Smith'"),
        ("", "''"),
        ("'quoted'", "'''quoted'''"),
        (r"folder\name", r"'folder\name'"),
    ],
    ids=["apostrophe", "plain", "empty", "surrounding-quotes", "backslash"],
)
def test_dynamics_string_filter(value, literal, as_list):
    result = DynamicsConnector._build_odata_filter(
        {"name": [value] if as_list else value}
    )

    expected = f"name eq {literal}"
    assert result == (f"({expected})" if as_list else expected)


@pytest.mark.parametrize("as_list", [False, True], ids=["scalar", "list"])
def test_dynamics_injection_stays_inside_one_literal(as_list):
    value = "x' or 1 eq 1 or name eq 'y"

    result = DynamicsConnector._build_odata_filter(
        {"name": [value] if as_list else value}
    )

    expected = "name eq 'x'' or 1 eq 1 or name eq ''y'"
    assert result == (f"({expected})" if as_list else expected)
    # Remove complete OData string literals, including doubled quote escapes.
    outside_literals = re.sub(r"'(?:[^']|'')*'", "''", result)
    assert "or 1 eq 1" not in outside_literals
    assert outside_literals == ("(name eq '')" if as_list else "name eq ''")


def test_dynamics_multiple_values_preserve_filter_structure():
    result = DynamicsConnector._build_odata_filter(
        {"name": ["O'Brien", "Smith"], "city": "O'Fallon"}
    )

    assert result == "(name eq 'O''Brien' or name eq 'Smith') and city eq 'O''Fallon'"


@pytest.mark.parametrize(
    ("value", "literal"),
    [(None, "null"), (True, "true"), (False, "false"), (42, "42"), (1.5, "1.5")],
)
def test_dynamics_typed_filter_values(value, literal):
    assert DynamicsConnector._build_odata_filter({"field": value}) == f"field eq {literal}"


@pytest.fixture
def dynamics_batch_connector():
    connector = DynamicsConnector.__new__(DynamicsConnector)
    connector._ensure_connected = Mock()
    connector._environment_url = "https://example.crm.dynamics.com"
    connector._access_token = "test-token"
    connector._timeout = 30
    connector._session = Mock()
    connector._session.post.return_value.status_code = 202
    return connector


@pytest.mark.parametrize(
    ("value", "literal"),
    [
        ("O'Brien", "'O''Brien'"),
        ("x' or 1 eq 1 or name eq 'y", "'x'' or 1 eq 1 or name eq ''y'"),
        ("Smith", "'Smith'"),
    ],
    ids=["apostrophe", "injection", "plain"],
)
def test_dynamics_batch_alternate_key_literal(value, literal, dynamics_batch_connector):
    connector = dynamics_batch_connector

    connector._batch_upsert("contacts", [{"name": value}], "name")

    body = connector._session.post.call_args.kwargs["data"]
    request_lines = [line for line in body.split("\r\n") if line.startswith("PATCH ")]
    encoded_literal = quote(literal, safe="")
    assert request_lines == [
        f"PATCH https://example.crm.dynamics.com/api/data/v9.2/contacts(name={encoded_literal}) HTTP/1.1"
    ]


@pytest.mark.parametrize(
    "value",
    ["x%27,accountnumber=%27A-1", "A#1", "Alice Smith", "Bob\r\nIf-Match: *"],
    ids=["percent-quote", "fragment", "space", "header-injection"],
)
def test_dynamics_batch_uri_smuggling(value, dynamics_batch_connector):
    connector = dynamics_batch_connector
    connector._batch_upsert("contacts", [{"name": value}], "name")

    body = connector._session.post.call_args.kwargs["data"]
    lines = body.split("\r\n")
    request_lines = [line for line in lines if line.startswith("PATCH ")]
    assert len(request_lines) == 1
    request = re.fullmatch(r"PATCH (\S+) HTTP/1\.1", request_lines[0])
    assert request is not None, "Alternate key must not split the request line"
    assert not any(line.startswith("If-Match:") for line in lines)
    uri = urlsplit(request[1])
    assert not uri.fragment
    assert not uri.query

    # Decode once, as the server does, then parse exactly one OData literal.
    key = re.fullmatch(
        r"/api/data/v9\.2/contacts\(name=('(?:[^']|'')*')\)",
        unquote(uri.path),
    )
    assert key is not None, "Alternate key must remain a single string literal"
    assert key[1][1:-1].replace("''", "'") == value


@pytest.mark.parametrize("as_list", [False, True], ids=["scalar", "list"])
@pytest.mark.parametrize(
    ("value", "escaped"),
    [
        ("Smith", "Smith"),
        ("O'Brien", r"O\'Brien"),
        (r"folder\name", r"folder\\name"),
        ("name (west)", r"name \(west\)"),
        (r"folder\O'Brien (west)", r"folder\\O\'Brien \(west\)"),
        (r"\(west\)", r"\\\(west\\\)"),
        ("trailing\\", r"trailing\\"),
        (r"x\' or 1 = 1 or Last_Name = 'y", r"x\\\' or 1 = 1 or Last_Name = \'y"),
    ],
    ids=[
        "plain", "apostrophe", "backslash", "parentheses", "combined",
        "backslash-before-parentheses", "trailing-backslash", "injection",
    ],
)
def test_zoho_query_escapes_criteria_values(value, escaped, as_list, monkeypatch):
    connector = ZohoConnector.__new__(ZohoConnector)
    request = Mock(return_value={"data": []})
    monkeypatch.setattr(connector, "request", request)

    connector.get_objects(
        "Contacts",
        fields=["Last_Name"],
        filters={"Last_Name": [value] if as_list else value},
    )

    criteria = f"Last_Name in ('{escaped}')" if as_list else f"Last_Name = '{escaped}'"
    query = request.call_args.kwargs["json_body"]["select_query"]
    assert query == f"select Last_Name from Contacts where {criteria} limit 0, 200"

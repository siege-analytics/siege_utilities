"""SOQL date literals and finite numeric values for both builders (#1430)."""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest

from siege_utilities.connectors.salesforce import (
    SOQLQuery, SalesforceConnector, _soql_literal,
)


def test_ticket_modified_since_probe():
    query = (SOQLQuery().select("Id").from_("Contact")
             .where("LastModifiedDate", gt=datetime(2024, 1, 1, tzinfo=timezone.utc))
             .where("CloseDate", lte=date(2024, 3, 31)))

    assert query.build() == (
        "SELECT Id FROM Contact WHERE LastModifiedDate > 2024-01-01T00:00:00Z"
        " AND CloseDate <= 2024-03-31"
    )


def test_filter_builder_renders_exact_soql():
    connector = SalesforceConnector(client_id="id", client_secret="secret")
    assert connector._build_soql("Opportunity", fields=["Id"], filters={
        "LastModifiedDate": datetime(2024, 1, 1, tzinfo=timezone.utc),
        "CloseDate": date(2024, 3, 31),
    }) == (
        "SELECT Id FROM Opportunity WHERE LastModifiedDate = 2024-01-01T00:00:00Z"
        " AND CloseDate = 2024-03-31"
    )


@pytest.mark.parametrize("value,expected", [
    (datetime(2024, 1, 1, tzinfo=timezone.utc), "2024-01-01T00:00:00Z"),
    (datetime(2024, 1, 1, 1, 30, tzinfo=timezone(timedelta(hours=5, minutes=30))),
     "2023-12-31T20:00:00Z"),
    (datetime(2024, 1, 1, microsecond=123000, tzinfo=timezone.utc),
     "2024-01-01T00:00:00.123000Z"),
    (date(2024, 3, 31), "2024-03-31"),
    (None, "null"), (True, "true"), (False, "false"), (42, "42"), (1.25, "1.25"),
    (r"O'Brien\folder", r"'O\'Brien\\folder'"),
    ("2024-03-31", "'2024-03-31'"), (Decimal("1.25"), "'1.25'"),
])
def test_literals_and_conditions(value, expected):
    assert _soql_literal(value) == expected
    assert SalesforceConnector._soql_condition("Field", value) == f"Field = {expected}"


@pytest.mark.parametrize("operator,symbol", [
    ("eq", "="), ("ne", "!="), ("gt", ">"), ("gte", ">="),
    ("lt", "<"), ("lte", "<="), ("in_", "IN"), ("not_in", "NOT IN"),
])
def test_all_fluent_operators(operator, symbol):
    value = date(2024, 3, 31)
    is_list = operator in ("in_", "not_in")
    query = SOQLQuery().select("Id").from_("Opportunity").where(
        "CloseDate", **{operator: [value] if is_list else value},
    )
    literal = "(2024-03-31)" if is_list else "2024-03-31"
    assert query.build() == f"SELECT Id FROM Opportunity WHERE CloseDate {symbol} {literal}"


def test_filter_list_uses_typed_literals():
    assert SalesforceConnector._soql_condition("CloseDate", [date(2024, 3, 31)]) == (
        "CloseDate IN (2024-03-31)"
    )
    assert SalesforceConnector._soql_condition("LastModifiedDate", [
        datetime(2024, 1, 1, tzinfo=timezone.utc),
    ]) == "LastModifiedDate IN (2024-01-01T00:00:00Z)"


@pytest.mark.parametrize("value,match", [
    (float("nan"), "finite"), (float("inf"), "finite"), (float("-inf"), "finite"),
    (datetime(2024, 1, 1), "timezone-aware"),
])
@pytest.mark.parametrize("builder", ["literal", "condition", "in", "not_in", "filter_list"])
def test_invalid_values_rejected(value, match, builder):
    with pytest.raises(ValueError, match=match):
        if builder == "literal":
            _soql_literal(value)
        elif builder == "condition":
            SalesforceConnector._soql_condition("Field", value)
        elif builder == "filter_list":
            SalesforceConnector._soql_condition("Field", [value])
        else:
            SOQLQuery().select("Id").from_("Contact").where(
                "Field", **{"in_" if builder == "in" else "not_in": [value]},
            ).build()

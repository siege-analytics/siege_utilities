"""Missing DataFrame values must not abort canonical CRM mapping (#1425)."""

from datetime import date
from decimal import Decimal

import pandas as pd
import pytest

from siege_utilities.connectors.dynamics import DynamicsConnector
from siege_utilities.connectors.hubspot import HubSpotConnector
from siege_utilities.connectors.salesforce import SalesforceConnector
from siege_utilities.connectors.zoho import ZohoConnector


CANONICAL_FIELDS = {
    "accounts": ("id", "name", "industry", "website", "revenue", "employee_count", "street"),
    "opportunities": ("id", "name", "stage", "amount", "probability", "close_date", "owner_id"),
    "contacts": ("id", "first_name", "last_name", "email", "phone", "title", "street"),
}
VENDOR_FIELDS = {
    "salesforce": {
        "accounts": ("Id", "Name", "Industry", "Website", "AnnualRevenue", "NumberOfEmployees", "BillingStreet"),
        "opportunities": ("Id", "Name", "StageName", "Amount", "Probability", "CloseDate", "OwnerId"),
        "contacts": ("Id", "FirstName", "LastName", "Email", "Phone", "Title", "MailingStreet"),
    },
    "hubspot": {
        "accounts": ("id", "name", "industry", "website", "annualrevenue", "numberofemployees", "address"),
        "opportunities": ("id", "dealname", "dealstage", "amount", "hs_deal_stage_probability", "closedate", "hubspot_owner_id"),
        "contacts": ("id", "firstname", "lastname", "email", "phone", "jobtitle", "address"),
    },
    "zoho": {
        "accounts": ("id", "Account_Name", "Industry", "Website", "Annual_Revenue", "Employees", "Billing_Street"),
        "opportunities": ("id", "Deal_Name", "Stage", "Amount", "Probability", "Closing_Date", "Owner"),
        "contacts": ("id", "First_Name", "Last_Name", "Email", "Phone", "Title", "Mailing_Street"),
    },
    "dynamics": {
        "accounts": ("accountid", "name", "industrycode", "websiteurl", "revenue", "numberofemployees", "address1_line1"),
        "opportunities": ("opportunityid", "name", "stepname", "estimatedvalue", "closeprobability", "estimatedclosedate", "_ownerid_value"),
        "contacts": ("contactid", "firstname", "lastname", "emailaddress1", "telephone1", "jobtitle", "address1_line1"),
    },
}
CONNECTORS = {
    "salesforce": SalesforceConnector,
    "hubspot": HubSpotConnector,
    "zoho": ZohoConnector,
    "dynamics": DynamicsConnector,
}
VARIANTS = [*CONNECTORS, "hubspot_nested"]
MISSING = [None, float("nan"), pd.NA, pd.NaT]
MISSING_IDS = ["none", "nan", "pd_na", "nat"]
VALID = {
    "accounts": ("valid", "Acme", "7", "https://example.test", 125.5, 12, "1 Main St"),
    "opportunities": ("valid", "Renewal", "Open", 250.5, 0.0, "2026-10-18", "owner-1"),
    "contacts": ("valid", "Ada", "Lovelace", "ada@example.test", "555-0100", "Engineer", "1 Main St"),
}


def _frame(variant, kind, rows):
    provider = variant.removesuffix("_nested")
    fields = dict(zip(CANONICAL_FIELDS[kind], VENDOR_FIELDS[provider][kind]))
    records = [{fields.get(key, key): value for key, value in row.items()} for row in rows]
    if variant == "hubspot_nested":
        records = [{"id": row.pop("id"), "properties": row} for row in records]
    return pd.DataFrame(records)


def _convert(variant, kind, frame):
    cls = CONNECTORS[variant.removesuffix("_nested")]
    # Mapping needs no authentication, HTTP transport, or MSAL initialization.
    connector = cls.__new__(cls)
    return getattr(connector, f"to_crm_{kind}")(frame)


@pytest.mark.parametrize("variant", VARIANTS)
@pytest.mark.parametrize("kind,field", [
    ("accounts", "employee_count"), ("accounts", "revenue"),
    ("opportunities", "amount"), ("opportunities", "probability"),
])
@pytest.mark.parametrize("missing", MISSING[:3], ids=MISSING_IDS[:3])
def test_missing_numeric_field_preserves_other_rows_and_zero(variant, kind, field, missing):
    valid = dict(zip(CANONICAL_FIELDS[kind], VALID[kind]))
    frame = _frame(variant, kind, [
        {**valid, "id": "missing", field: missing}, valid,
        {**valid, "id": "zero", field: 0},
    ])
    original = frame.copy(deep=True)

    records = _convert(variant, kind, frame)

    assert [record.id for record in records] == ["missing", "valid", "zero"]
    assert getattr(records[0], field) is None
    assert getattr(records[1], field) == valid[field]
    assert getattr(records[2], field) == 0
    pd.testing.assert_frame_equal(frame, original)


@pytest.mark.parametrize("variant", VARIANTS)
@pytest.mark.parametrize("kind", CANONICAL_FIELDS)
@pytest.mark.parametrize("missing", MISSING, ids=MISSING_IDS)
def test_missing_fields_and_names_do_not_abort_the_list(variant, kind, missing):
    valid = dict(zip(CANONICAL_FIELDS[kind], VALID[kind]))
    missing_row = {field: missing for field in CANONICAL_FIELDS[kind]}
    missing_row["id"] = "missing"
    frame = _frame(variant, kind, [missing_row, valid])

    records = _convert(variant, kind, frame)

    assert [record.id for record in records] == ["missing", "valid"]
    for field in CANONICAL_FIELDS[kind][1:]:
        if field == "street":
            assert records[0].address.street is None
            assert records[1].address.street == valid[field]
        elif field == "name":
            assert records[0].name == ""
            assert records[1].name == valid[field]
        else:
            assert getattr(records[0], field) is None
            expected = date(2026, 10, 18) if field == "close_date" else valid[field]
            assert getattr(records[1], field) == expected
    if kind == "accounts":
        assert records[1].revenue == Decimal("125.5")
    elif kind == "opportunities":
        assert records[1].amount == Decimal("250.5")


@pytest.mark.parametrize("variant", VARIANTS)
@pytest.mark.parametrize("kind", ["accounts", "opportunities"])
def test_absent_name_uses_empty_string_fallback(variant, kind):
    frame = _frame(variant, kind, [{"id": "unnamed"}])

    record, = _convert(variant, kind, frame)

    assert record.name == ""


@pytest.mark.parametrize("variant", VARIANTS)
def test_datetime_column_with_nat_maps_to_optional_date(variant):
    frame = _frame(variant, "opportunities", [
        {"id": "missing", "name": "Unknown date", "close_date": pd.NaT},
        {"id": "dated", "name": "Known date", "close_date": pd.Timestamp("2026-10-18")},
    ])

    records = _convert(variant, "opportunities", frame)

    assert records[0].close_date is None
    assert records[1].close_date == date(2026, 10, 18)

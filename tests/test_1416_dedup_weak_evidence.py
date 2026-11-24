"""Weak or ambiguous evidence must not merge namesakes in CRM deduplication (#1416).

A merge at confidence 1.0 must rest on a real shared identifier: a placeholder
value, a street line without a locality, or a record that links two people
whose emails conflict is not one.
"""

import pandas as pd
import pytest

from siege_utilities.connectors._dedup import crm_dedup_pipeline
from siege_utilities.identifiers.normalize import normalize_address_v1


def _smith(source_id, **fields):
    return {
        "first_name": "John",
        "last_name": "Smith",
        "source_system": f"crm_{source_id}",
        "source_id": source_id,
        **fields,
    }


def _canonical_ids(rows, **kwargs):
    return crm_dedup_pipeline([pd.DataFrame(rows)], **kwargs).set_index("source_id")["canonical_id"]


LOCALITY = {"address_city": "Austin", "address_state": "TX", "address_postal_code": "78701"}


@pytest.mark.parametrize("fields", [
    {"email": "n/a"},
    {"email": "N/A"},
    {"email": "unknown"},
    {"email": "TBD"},
    {"email": "none@none.com"},
    {"email": "Unknown@Unknown.com"},
    {"phone": "000-000-0000"},
    {"phone": "(111) 111-1111"},
    {"phone": "999.999.9999"},
    {"address_street": "N/A", **LOCALITY},
    {"address_street": "Unknown", **LOCALITY},
])
def test_namesakes_sharing_only_a_placeholder_do_not_merge(fields):
    ids = _canonical_ids([_smith("a", **fields), _smith("b", **fields)])

    assert ids.nunique() == 2


def test_placeholder_filter_keeps_real_values_that_contain_placeholder_words():
    rows = [
        _smith("a", email="unknown.smith@example.com", phone="512-555-0100"),
        _smith("b", email="unknown.smith@example.com", phone="000-000-0000"),
        _smith("c", phone="000-000-0000"),
    ]

    ids = _canonical_ids(rows)

    # A real email merges a and b; c shares only placeholders with b and stays apart.
    assert ids["a"] == ids["b"]
    assert ids["c"] != ids["a"]


def test_street_line_without_a_locality_is_not_an_address_match():
    street_only = [
        _smith("a", address_street="100 Main St"),
        _smith("b", address_street="100 Main Street"),
    ]
    street_and_city = [
        _smith("a", address_street="100 Main St", address_city="Austin"),
        _smith("b", address_street="100 Main Street", address_city="Austin"),
    ]
    with_zip = [
        _smith("a", address_street="100 Main St", address_postal_code="78701"),
        _smith("b", address_street="100 Main Street", address_postal_code="78701-1234"),
    ]
    with_city_and_state = [
        _smith("a", address_street="100 Main St", address_city="Austin", address_state="TX"),
        _smith("b", address_street="100 Main Street", address_city="AUSTIN", address_state="Texas"),
    ]

    assert _canonical_ids(street_only).nunique() == 2
    assert _canonical_ids(street_and_city).nunique() == 2
    assert _canonical_ids(with_zip).nunique() == 1
    assert _canonical_ids(with_city_and_state).nunique() == 1


def test_all_zero_postal_code_is_not_a_locality():
    rows = [
        _smith("a", address_street="100 Main St", address_postal_code="00000"),
        _smith("b", address_street="100 Main St", address_postal_code="00000"),
    ]

    assert _canonical_ids(rows).nunique() == 2


@pytest.mark.parametrize("email_column", ["email_address", "Email", "work_EMAIL"])
def test_email_conflict_is_detected_whatever_the_email_column_is_called(email_column):
    rows = [
        _smith("a", **{email_column: "john.a@example.com"}, phone="512-555-0100"),
        _smith("b", **{email_column: "john.b@example.com"}, phone="(512) 555-0100"),
    ]

    result = crm_dedup_pipeline(
        [pd.DataFrame(rows)], identifier_columns=[email_column, "phone"],
    ).set_index("source_id")

    assert result["canonical_id"].nunique() == 2
    # Kept apart by an email conflict: probably different people.
    assert result["match_confidence"].eq(1.0).all()


def test_record_linking_two_conflicting_people_stays_unattached_whatever_the_emails_sort_as():
    def run(first_email):
        rows = [
            _smith("a", email=first_email, phone="512-555-0100"),
            _smith("c", email="john.c@example.com", phone="512-555-0100"),
            _smith("b", phone="512-555-0100"),
        ]
        return crm_dedup_pipeline([pd.DataFrame(rows)]).set_index("source_id")

    for result in (run("john.a@example.com"), run("zed@example.com")):
        ids = result["canonical_id"]
        assert ids.nunique() == 3
        assert ids["b"] not in {ids["a"], ids["c"]}
        # The phone proves nothing about which person b is: a review candidate.
        assert result.loc["b", "match_confidence"] < 1.0

    assert run("john.a@example.com").loc["b", "canonical_id"] == run("zed@example.com").loc["b", "canonical_id"]

    # Control: a record without an email that reaches only one person still
    # joins that person, also through another record without an email.
    chain = [
        _smith("a", email="john@example.com", phone="512-555-0100"),
        _smith("b", phone="512-555-0100", address_street="9 Oak St", **LOCALITY),
        _smith("c", address_street="9 Oak Street", **LOCALITY),
    ]
    assert _canonical_ids(chain).nunique() == 1


@pytest.mark.parametrize("left, right", [
    ("100 Main St Apt 2", "100 Main St Apt #2"),
    ("100 Main St Suite 200", "100 Main St Suite #200"),
    ("100 Main St Unit 5", "100 Main St Unit #5"),
])
def test_unit_designator_followed_by_hash_matches_the_bare_designator(left, right):
    assert normalize_address_v1(left, "Austin", "TX", "78701") == normalize_address_v1(right, "Austin", "TX", "78701")

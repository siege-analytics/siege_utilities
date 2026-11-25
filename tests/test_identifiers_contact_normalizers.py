"""Phone and address normalizers used as CRM identity evidence (#1416)."""

import pytest

from siege_utilities.identifiers.normalize import (
    NORMALIZER_VERSIONS,
    normalize_address_v1,
    normalize_phone_v1,
)


@pytest.mark.parametrize("value", [
    "(512) 555-0100", "512-555-0100", "+1 512 555 0100", "1.512.555.0100",
    "512-555-0100 x12", "512-555-0100 ext. 12", "512 555 0100 extension 7",
])
def test_phone_variants_normalize_to_ten_digits(value):
    assert normalize_phone_v1(value) == "5125550100"


@pytest.mark.parametrize("value", [None, "", "   ", "ext 12", "555-01", "+1"])
def test_phone_without_enough_digits_is_not_evidence(value):
    assert normalize_phone_v1(value) == ""


def test_distinct_phones_stay_distinct():
    assert normalize_phone_v1("512-555-0100") != normalize_phone_v1("512-555-0101")


def test_eleven_digits_without_us_prefix_are_kept():
    assert normalize_phone_v1("+44 20 7946 0958") == "442079460958"


@pytest.mark.parametrize("left, right", [
    (("100 Congress Avenue",), ("100 congress ave.",)),
    (("100 North Main Street, Suite 4",), ("100 N Main St #4",)),
    (("100 Congress Ave", "Austin", "Texas", "78701-1234"), ("100 CONGRESS AVE", "AUSTIN", "TX", "78701")),
    (("12 Elm Rd., Apartment 3B",), ("12 elm road unit 3b",)),
    (("1 Main St", "Boston", "Massachusetts", "2134"), ("1 Main St", "Boston", "MA", "02134")),
    (("5 Oak Ln", "Albany", "New York", ""), ("5 Oak Lane", "albany", "ny", "")),
])
def test_address_variants_normalize_equal(left, right):
    assert normalize_address_v1(*left) == normalize_address_v1(*right)


@pytest.mark.parametrize("left, right", [
    (("100 Congress Ave",), ("101 Congress Ave",)),
    (("100 N Main St",), ("100 S Main St",)),
    (("100 Main St Apt 1",), ("100 Main St Apt 2",)),
    (("100 Congress Ave", "Austin", "TX", "78701"), ("100 Congress Ave", "Austin", "TX", "78702")),
])
def test_distinct_addresses_stay_distinct(left, right):
    assert normalize_address_v1(*left) != normalize_address_v1(*right)


def test_state_names_in_the_street_line_are_not_rewritten():
    # "West Virginia Ave" is a street name, not the state.
    assert normalize_address_v1("10 West Virginia Ave").startswith("10 w virginia ave")
    assert normalize_address_v1("10 West Virginia Ave") != normalize_address_v1("10 WV Ave")


def test_street_number_is_not_mistaken_for_a_zip():
    assert normalize_address_v1("12345 6789 Rd") == "12345 6789 rd |  |  | "


@pytest.mark.parametrize("street", [None, "", "  ,.  "])
def test_address_without_a_street_is_empty(street):
    assert normalize_address_v1(street, "Austin", "TX", "78701") == ""


def test_new_normalizers_are_registered_versions():
    assert {"normalize_phone_v1", "normalize_address_v1"} <= set(NORMALIZER_VERSIONS)

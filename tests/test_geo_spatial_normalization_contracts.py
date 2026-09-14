import pytest

from siege_utilities import normalize_fips_code
from siege_utilities import normalize_state_abbreviation
from siege_utilities import normalize_state_input
from siege_utilities import normalize_state_name


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("  ca  ", "CA"),
        ("CAlifornia", "CALIFORNIA"),
        ("6", "06"),
        ("06", "06"),
        ("", ""),
    ],
)
def test_normalize_state_input_trims_uppercases_and_pads_numeric(raw, expected):
    assert normalize_state_input(raw) == expected


def test_normalize_state_name_delegates_to_state_input_rules():
    assert normalize_state_name("  New York ") == "NEW YORK"
    assert normalize_state_name("texas") == "TEXAS"


def test_normalize_state_abbreviation_delegates_to_state_input_rules():
    assert normalize_state_abbreviation(" tx ") == "TX"
    assert normalize_state_abbreviation("dc") == "DC"


@pytest.mark.parametrize(
    "raw,expected",
    [
        (6, "06"),
        ("6", "06"),
        (" 12 ", "12"),
        ("ca", "CA"),
    ],
)
def test_normalize_fips_code_pads_numeric_and_uppercases_non_numeric(raw, expected):
    assert normalize_fips_code(raw) == expected

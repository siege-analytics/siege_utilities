"""Root-import contracts for state/FIPS reference lookups."""

from siege_utilities import get_available_state_fips
from siege_utilities import get_comprehensive_state_info
from siege_utilities import get_state_abbreviation
from siege_utilities import get_state_abbreviations
from siege_utilities import get_state_by_abbreviation
from siege_utilities import get_state_by_name
from siege_utilities import get_state_name
from siege_utilities import get_unified_fips_data
from siege_utilities import validate_state_fips


def test_get_state_name_maps_fips_to_name():
    assert get_state_name("06") == "California"
    assert get_state_name("36") == "New York"
    assert get_state_name("11") == "District of Columbia"
    assert get_state_name("99") is None


def test_get_state_abbreviation_maps_fips_to_abbr():
    assert get_state_abbreviation("06") == "CA"
    assert get_state_abbreviation("48") == "TX"
    assert get_state_abbreviation("11") == "DC"
    assert get_state_abbreviation("99") is None


def test_validate_state_fips_requires_known_two_digit_code():
    assert validate_state_fips("06") is True
    assert validate_state_fips("99") is False
    # FIPS must be the zero-padded two-digit form; "6" is not valid.
    assert validate_state_fips("6") is False


def test_get_state_by_abbreviation_case_insensitive_and_guards():
    assert get_state_by_abbreviation("ca") == {
        "fips": "06",
        "name": "California",
        "abbreviation": "CA",
    }
    assert get_state_by_abbreviation("DC") == {
        "fips": "11",
        "name": "District of Columbia",
        "abbreviation": "DC",
    }
    assert get_state_by_abbreviation("ZZ") is None
    # Length guard: an abbreviation must be exactly two characters.
    assert get_state_by_abbreviation("C") is None


def test_get_state_by_name_partial_match_and_ordering():
    assert get_state_by_name("California") == {
        "fips": "06",
        "name": "California",
        "abbreviation": "CA",
    }
    # Partial case-insensitive match; "Virginia" resolves to Virginia (51),
    # not West Virginia (54), because FIPS 51 is encountered first.
    assert get_state_by_name("Virginia") == {
        "fips": "51",
        "name": "Virginia",
        "abbreviation": "VA",
    }
    assert get_state_by_name("") is None


def test_get_available_state_fips_and_abbreviations_mappings():
    names = get_available_state_fips()
    assert names["06"] == "California"
    assert names["11"] == "District of Columbia"
    abbrs = get_state_abbreviations()
    assert abbrs["06"] == "CA"
    assert abbrs["11"] == "DC"


def test_get_comprehensive_state_info_entry_shape():
    info = get_comprehensive_state_info()
    assert info["06"] == {
        "name": "California",
        "abbreviation": "CA",
        "fips": "06",
    }


def test_get_unified_fips_data_matches_comprehensive_and_covers_states():
    unified = get_unified_fips_data()
    # Documented invariant: unified is the comprehensive state info.
    assert unified == get_comprehensive_state_info()
    # 50 states + DC + territories.
    assert len(unified) == 57
    assert sorted(unified["06"].keys()) == ["abbreviation", "fips", "name"]

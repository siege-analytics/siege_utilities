"""Tests for state FIPS codes, abbreviations, and identifier normalization.

Covers: STATE_FIPS_CODES, STATEFIPS_LOOKUP_DICT, FIPS_TO_STATE, STATE_NAMES,
        normalize_state_identifier, get_fips_info
"""

import pytest

from siege_utilities.config.census_registry import (
    FIPS_TO_STATE,
    STATE_FIPS_CODES,
    STATE_NAMES,
    STATEFIPS_LOOKUP_DICT,
    get_fips_info,
    normalize_state_identifier,
)


# ---------------------------------------------------------------------------
# Dictionary completeness
# ---------------------------------------------------------------------------

class TestStateDictionaries:

    def test_50_states_plus_dc(self):
        # 50 states + DC + 6 territories = 57
        # (PR, VI, AS, GU, MP, UM)
        assert len(STATE_FIPS_CODES) >= 57

    def test_all_fips_zero_padded(self):
        for abbrev, fips in STATE_FIPS_CODES.items():
            assert len(fips) == 2, f"{abbrev} has non-2-digit FIPS: {fips}"
            assert fips.isdigit(), f"{abbrev} has non-numeric FIPS: {fips}"

    def test_all_abbreviations_two_letters(self):
        for abbrev in STATE_FIPS_CODES:
            assert len(abbrev) == 2, f"Abbreviation not 2 letters: {abbrev}"
            assert abbrev.isalpha(), f"Non-alpha abbreviation: {abbrev}"
            assert abbrev.isupper(), f"Lowercase abbreviation: {abbrev}"

    def test_fips_to_state_is_reverse(self):
        for abbrev, fips in STATE_FIPS_CODES.items():
            assert FIPS_TO_STATE[fips] == abbrev

    def test_state_names_covers_all_abbreviations(self):
        for abbrev in STATE_FIPS_CODES:
            assert abbrev in STATE_NAMES, f"Missing name for {abbrev}"

    def test_alias_is_same_object(self):
        assert STATEFIPS_LOOKUP_DICT is STATE_FIPS_CODES

    def test_dc_present(self):
        assert "DC" in STATE_FIPS_CODES
        assert STATE_FIPS_CODES["DC"] == "11"

    def test_territories_present(self):
        territories = {"PR": "72", "VI": "78", "AS": "60", "GU": "66", "MP": "69"}
        for abbrev, fips in territories.items():
            assert STATE_FIPS_CODES.get(abbrev) == fips, f"Missing territory: {abbrev}"

    def test_spot_check_states(self):
        checks = {
            "CA": "06", "TX": "48", "NY": "36", "FL": "12",
            "AL": "01", "WY": "56", "HI": "15", "AK": "02",
        }
        for abbrev, expected_fips in checks.items():
            assert STATE_FIPS_CODES[abbrev] == expected_fips


# ---------------------------------------------------------------------------
# normalize_state_identifier
# ---------------------------------------------------------------------------

class TestNormalizeStateIdentifier:

    def test_fips_code_passthrough(self):
        assert normalize_state_identifier("48") == "48"

    def test_fips_zero_padded(self):
        assert normalize_state_identifier("06") == "06"
        assert normalize_state_identifier("01") == "01"

    def test_abbreviation(self):
        assert normalize_state_identifier("TX") == "48"
        assert normalize_state_identifier("CA") == "06"

    def test_case_insensitive_abbreviation(self):
        assert normalize_state_identifier("tx") == "48"
        assert normalize_state_identifier("Tx") == "48"

    def test_full_name(self):
        assert normalize_state_identifier("Texas") == "48"
        assert normalize_state_identifier("California") == "06"

    def test_case_insensitive_name(self):
        assert normalize_state_identifier("texas") == "48"
        assert normalize_state_identifier("TEXAS") == "48"

    def test_dc(self):
        assert normalize_state_identifier("DC") == "11"
        assert normalize_state_identifier("11") == "11"
        assert normalize_state_identifier("District of Columbia") == "11"

    def test_territory(self):
        assert normalize_state_identifier("PR") == "72"
        assert normalize_state_identifier("Puerto Rico") == "72"

    def test_whitespace_stripped(self):
        assert normalize_state_identifier("  TX  ") == "48"

    def test_unknown_raises(self):
        with pytest.raises(ValueError, match="Unrecognized"):
            normalize_state_identifier("ZZ")

    def test_empty_raises(self):
        with pytest.raises(ValueError):
            normalize_state_identifier("")

    def test_round_trip_all_states(self):
        for abbrev, fips in STATE_FIPS_CODES.items():
            assert normalize_state_identifier(abbrev) == fips
            assert normalize_state_identifier(fips) == fips


# ---------------------------------------------------------------------------
# get_fips_info
# ---------------------------------------------------------------------------

class TestGetFipsInfo:

    def test_by_abbreviation(self):
        info = get_fips_info("CA")
        assert info == {"fips": "06", "abbreviation": "CA", "name": "California"}

    def test_by_fips(self):
        info = get_fips_info("48")
        assert info == {"fips": "48", "abbreviation": "TX", "name": "Texas"}

    def test_by_name(self):
        info = get_fips_info("New York")
        assert info == {"fips": "36", "abbreviation": "NY", "name": "New York"}

    def test_dc(self):
        info = get_fips_info("DC")
        assert info["fips"] == "11"
        assert info["name"] == "District of Columbia"

    def test_territory(self):
        info = get_fips_info("GU")
        assert info["fips"] == "66"
        assert info["name"] == "Guam"

    def test_unknown_raises(self):
        with pytest.raises(ValueError):
            get_fips_info("XX")

"""Tests for NAICS/SOC crosswalk and normalization module."""

import pytest

from siege_utilities.data.naics_soc_crosswalk import (
    NAICS_SECTORS,
    SOC_MAJOR_GROUPS,
    crosswalk_naics,
    fuzzy_match_naics,
    naics_ancestors,
    naics_to_sector,
    parse_naics,
    parse_soc,
    soc_to_major_group,
)


# ---------------------------------------------------------------------------
# NAICS parsing
# ---------------------------------------------------------------------------

class TestParseNAICS:

    def test_sector(self):
        code = parse_naics("54")
        assert code.code == "54"
        assert code.level == 2
        assert code.parent_code is None
        assert code.sector == "54"

    def test_subsector(self):
        code = parse_naics("541")
        assert code.level == 3
        assert code.parent_code == "54"

    def test_six_digit(self):
        code = parse_naics("541511")
        assert code.level == 6
        assert code.parent_code == "54151"
        assert code.sector == "54"

    def test_invalid_short(self):
        with pytest.raises(ValueError, match="Invalid NAICS"):
            parse_naics("5")

    def test_invalid_long(self):
        with pytest.raises(ValueError, match="Invalid NAICS"):
            parse_naics("5415111")

    def test_invalid_alpha(self):
        with pytest.raises(ValueError, match="Invalid NAICS"):
            parse_naics("54AB")

    def test_strips_whitespace(self):
        code = parse_naics("  54  ")
        assert code.code == "54"


class TestNAICSAncestors:

    def test_six_digit(self):
        result = naics_ancestors("541511")
        assert result == ["54", "541", "5415", "54151", "541511"]

    def test_two_digit(self):
        result = naics_ancestors("54")
        assert result == ["54"]


class TestNAICSToSector:

    def test_known(self):
        code, title = naics_to_sector("541511")
        assert code == "54"
        assert "Professional" in title

    def test_manufacturing(self):
        code, title = naics_to_sector("31")
        assert title == "Manufacturing"

    def test_unknown(self):
        _, title = naics_to_sector("99")
        assert title == "Unknown Sector"


# ---------------------------------------------------------------------------
# NAICS crosswalks
# ---------------------------------------------------------------------------

class TestCrosswalkNAICS:

    def test_2017_to_2022_known(self):
        result = crosswalk_naics("454110", from_year=2017, to_year=2022)
        assert result == ["455110"]

    def test_2017_to_2022_unchanged(self):
        result = crosswalk_naics("423990", from_year=2017, to_year=2022)
        assert result == ["423990"]

    def test_2017_to_2022_unknown_passthrough(self):
        result = crosswalk_naics("999999", from_year=2017, to_year=2022)
        assert result == ["999999"]

    def test_2012_to_2022_chained(self):
        result = crosswalk_naics("517110", from_year=2012, to_year=2022)
        assert isinstance(result, list)
        assert len(result) >= 1

    def test_unsupported_years(self):
        with pytest.raises(ValueError, match="Unsupported"):
            crosswalk_naics("541511", from_year=2007, to_year=2012)


# ---------------------------------------------------------------------------
# SOC parsing
# ---------------------------------------------------------------------------

class TestParseSOC:

    def test_major_group(self):
        code = parse_soc("11")
        assert code.level == "major"
        assert code.major_group == "11"
        assert "Management" in code.title

    def test_detailed(self):
        code = parse_soc("11-1011")
        assert code.level == "detailed"
        assert code.major_group == "11"

    def test_broad(self):
        code = parse_soc("11-1010")
        assert code.level == "broad"

    def test_invalid(self):
        with pytest.raises(ValueError, match="Invalid SOC"):
            parse_soc("11-10")

    def test_strips_whitespace(self):
        code = parse_soc("  15  ")
        assert code.code == "15"


class TestSOCToMajorGroup:

    def test_known(self):
        code, title = soc_to_major_group("15-1256")
        assert code == "15"
        assert "Computer" in title

    def test_unknown(self):
        _, title = soc_to_major_group("99-0000")
        assert title == "Unknown"


# ---------------------------------------------------------------------------
# Fuzzy matching
# ---------------------------------------------------------------------------

class TestFuzzyMatch:

    def test_exact_sector(self):
        matches = fuzzy_match_naics("Manufacturing")
        assert len(matches) >= 1
        assert any("Manufacturing" in m[1] for m in matches)

    def test_partial_match(self):
        matches = fuzzy_match_naics("Health Care", threshold=0.3)
        assert len(matches) >= 1

    def test_no_match(self):
        matches = fuzzy_match_naics("xyzzyplugh", threshold=0.5)
        assert len(matches) == 0

    def test_custom_candidates(self):
        candidates = {"99": "Fictional Industry"}
        matches = fuzzy_match_naics("Fictional Industry", candidates=candidates)
        assert len(matches) == 1
        assert matches[0][0] == "99"
        assert matches[0][2] == 1.0

    def test_sorted_by_score(self):
        matches = fuzzy_match_naics("Transportation and Warehousing", threshold=0.2)
        if len(matches) >= 2:
            assert matches[0][2] >= matches[1][2]


# ---------------------------------------------------------------------------
# Reference data completeness
# ---------------------------------------------------------------------------

class TestReferenceData:

    def test_naics_sectors_count(self):
        assert len(NAICS_SECTORS) >= 20

    def test_soc_major_groups_count(self):
        assert len(SOC_MAJOR_GROUPS) >= 22

    def test_naics_sectors_all_two_digit(self):
        for code in NAICS_SECTORS:
            assert len(code) == 2
            assert code.isdigit()

    def test_soc_groups_all_two_digit(self):
        for code in SOC_MAJOR_GROUPS:
            assert len(code) == 2
            assert code.isdigit()

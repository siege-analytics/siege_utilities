"""Tests for NAICS/SOC integration enhancements (SU#619)."""

from __future__ import annotations

import pytest

from siege_utilities.geo.providers.nlrb_clients import NLRBCaseRecord

# Load the module file directly to avoid reference/__init__.py
# which eagerly imports pandas via sample_data
import importlib.util as _ilu
import pathlib as _pl
import sys as _sys

_mod_name = "siege_utilities.reference.naics_soc_crosswalk"
_spec = _ilu.spec_from_file_location(
    _mod_name,
    _pl.Path(__file__).resolve().parent.parent
    / "siege_utilities" / "reference" / "naics_soc_crosswalk.py",
)
_nsc = _ilu.module_from_spec(_spec)
_sys.modules[_mod_name] = _nsc
_spec.loader.exec_module(_nsc)

NAICS_SECTORS = _nsc.NAICS_SECTORS
NAICS_SUBSECTORS = _nsc.NAICS_SUBSECTORS
SOC_MAJOR_GROUPS = _nsc.SOC_MAJOR_GROUPS
SOC_MINOR_GROUPS = _nsc.SOC_MINOR_GROUPS
filter_by_naics = _nsc.filter_by_naics
filter_by_naics_sector = _nsc.filter_by_naics_sector
get_naics_lookup = _nsc.get_naics_lookup
get_soc_lookup = _nsc.get_soc_lookup
group_by_naics_sector = _nsc.group_by_naics_sector
naics_title = _nsc.naics_title
soc_title = _nsc.soc_title


# ---------------------------------------------------------------------------
# Bundled lookup table tests
# ---------------------------------------------------------------------------


class TestNAICSSubsectors:
    def test_has_entries(self):
        assert len(NAICS_SUBSECTORS) > 80

    def test_hospitals(self):
        assert NAICS_SUBSECTORS["622"] == "Hospitals"

    def test_ambulatory(self):
        assert NAICS_SUBSECTORS["621"] == "Ambulatory Health Care Services"

    def test_trucking(self):
        assert NAICS_SUBSECTORS["484"] == "Truck Transportation"

    def test_all_codes_are_3_digit(self):
        for code in NAICS_SUBSECTORS:
            assert len(code) == 3, f"Code {code} is not 3 digits"
            assert code.isdigit(), f"Code {code} is not numeric"


class TestSOCMinorGroups:
    def test_has_entries(self):
        assert len(SOC_MINOR_GROUPS) > 70

    def test_top_executives(self):
        assert SOC_MINOR_GROUPS["11-1000"] == "Top Executives"

    def test_nurses(self):
        assert "Healthcare" in SOC_MINOR_GROUPS["29-1000"]

    def test_construction(self):
        assert "Construction" in SOC_MINOR_GROUPS["47-2000"]


class TestGetNAICSLookup:
    def test_combines_sectors_and_subsectors(self):
        lookup = get_naics_lookup()
        assert len(lookup) == len(NAICS_SECTORS) + len(NAICS_SUBSECTORS)

    def test_includes_sector(self):
        lookup = get_naics_lookup()
        assert "62" in lookup

    def test_includes_subsector(self):
        lookup = get_naics_lookup()
        assert "622" in lookup


class TestGetSOCLookup:
    def test_combines_major_and_minor(self):
        lookup = get_soc_lookup()
        assert len(lookup) == len(SOC_MAJOR_GROUPS) + len(SOC_MINOR_GROUPS)

    def test_includes_major(self):
        lookup = get_soc_lookup()
        assert "11" in lookup

    def test_includes_minor(self):
        lookup = get_soc_lookup()
        assert "11-1000" in lookup


# ---------------------------------------------------------------------------
# Title lookup tests
# ---------------------------------------------------------------------------


class TestNAICSTitle:
    def test_sector_code(self):
        assert naics_title("62") == "Health Care and Social Assistance"

    def test_subsector_code(self):
        assert naics_title("622") == "Hospitals"

    def test_longer_code_falls_back_to_sector(self):
        title = naics_title("622110")
        assert title == "Health Care and Social Assistance"

    def test_unknown_code(self):
        assert naics_title("99") == "Unknown"

    def test_whitespace_stripped(self):
        assert naics_title(" 622 ") == "Hospitals"


class TestSOCTitle:
    def test_major_group(self):
        assert soc_title("11") == "Management"

    def test_minor_group(self):
        assert soc_title("11-1000") == "Top Executives"

    def test_detailed_falls_back_to_major(self):
        assert soc_title("11-1011") == "Management"

    def test_unknown(self):
        assert soc_title("99") == "Unknown"


# ---------------------------------------------------------------------------
# Query interface tests
# ---------------------------------------------------------------------------


def _make_cases():
    return [
        NLRBCaseRecord(case_number="1", case_type="RC", naics_code="622110"),
        NLRBCaseRecord(case_number="2", case_type="RC", naics_code="622210"),
        NLRBCaseRecord(case_number="3", case_type="CA", naics_code="445110"),
        NLRBCaseRecord(case_number="4", case_type="RC", naics_code="621111"),
        NLRBCaseRecord(case_number="5", case_type="CA", naics_code=""),
    ]


class TestFilterByNAICS:
    def test_filter_hospitals(self):
        cases = _make_cases()
        matches = filter_by_naics(cases, "622")
        assert len(matches) == 2
        assert all(c.naics_code.startswith("622") for c in matches)

    def test_filter_health_care_sector(self):
        cases = _make_cases()
        matches = filter_by_naics(cases, "62")
        assert len(matches) == 3

    def test_filter_exact_code(self):
        cases = _make_cases()
        matches = filter_by_naics(cases, "622110")
        assert len(matches) == 1

    def test_no_matches(self):
        cases = _make_cases()
        matches = filter_by_naics(cases, "999")
        assert len(matches) == 0

    def test_empty_naics_excluded(self):
        cases = _make_cases()
        matches = filter_by_naics(cases, "")
        assert len(matches) == 0

    def test_works_with_dicts(self):
        records = [
            {"case_number": "1", "naics_code": "622110"},
            {"case_number": "2", "naics_code": "445110"},
        ]
        matches = filter_by_naics(records, "622")
        assert len(matches) == 1

    def test_whitespace_stripped(self):
        cases = _make_cases()
        matches = filter_by_naics(cases, " 622 ")
        assert len(matches) == 2


class TestFilterByNAICSSector:
    def test_filter_by_sector(self):
        cases = _make_cases()
        matches = filter_by_naics_sector(cases, "62")
        assert len(matches) == 3

    def test_longer_code_truncated(self):
        cases = _make_cases()
        matches = filter_by_naics_sector(cases, "622")
        assert len(matches) == 3


class TestGroupByNAICSSector:
    def test_groups_correctly(self):
        cases = _make_cases()
        groups = group_by_naics_sector(cases)
        assert len(groups["62"]) == 3
        assert len(groups["44"]) == 1
        assert len(groups[""]) == 1

    def test_empty_input(self):
        groups = group_by_naics_sector([])
        assert groups == {}

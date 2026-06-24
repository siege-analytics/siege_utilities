"""Tests for NLRB region boundary integration (SU#620)."""

from __future__ import annotations


from siege_utilities.geo.providers.nlrb_clients import NLRBCaseRecord
from siege_utilities.geo.providers.nlrb_regions import (
    NLRB_REGIONS,
    aggregate_by_region,
    assign_region,
    lookup_region_by_state,
    region_summary,
)


# ---------------------------------------------------------------------------
# Region registry tests
# ---------------------------------------------------------------------------


class TestNLRBRegions:
    def test_has_expected_regions(self):
        assert len(NLRB_REGIONS) >= 26

    def test_all_have_office(self):
        for num, info in NLRB_REGIONS.items():
            assert info["office"], f"Region {num} missing office"

    def test_all_have_states(self):
        for num, info in NLRB_REGIONS.items():
            assert len(info["states"]) > 0, f"Region {num} has no states"

    def test_region_numbers_in_range(self):
        for num in NLRB_REGIONS:
            assert 1 <= num <= 31

    def test_known_region(self):
        assert NLRB_REGIONS[13]["office"] == "Chicago"
        assert "IL" in NLRB_REGIONS[13]["states"]


# ---------------------------------------------------------------------------
# State → Region lookup tests
# ---------------------------------------------------------------------------


class TestStateToRegions:
    def test_single_region_state(self):
        regions = lookup_region_by_state("FL")
        assert 12 in regions

    def test_multi_region_state(self):
        regions = lookup_region_by_state("NY")
        assert len(regions) > 1
        assert 2 in regions
        assert 3 in regions
        assert 29 in regions

    def test_case_insensitive(self):
        assert lookup_region_by_state("il") == lookup_region_by_state("IL")

    def test_unknown_state(self):
        assert lookup_region_by_state("XX") == []

    def test_whitespace_stripped(self):
        assert lookup_region_by_state(" TX ") == lookup_region_by_state("TX")

    def test_all_states_covered(self):
        all_states = set()
        for info in NLRB_REGIONS.values():
            all_states.update(info["states"])
        assert len(all_states) > 40


# ---------------------------------------------------------------------------
# assign_region tests
# ---------------------------------------------------------------------------


class TestAssignRegion:
    def test_from_case_number_region(self):
        case = NLRBCaseRecord(
            case_number="05-RC-123456", case_type="RC", region=5
        )
        assert assign_region(case) == 5

    def test_from_state_fallback(self):
        case = NLRBCaseRecord(
            case_number="test", case_type="RC", state="TX"
        )
        assert assign_region(case) == 16

    def test_region_takes_priority(self):
        case = NLRBCaseRecord(
            case_number="test", case_type="RC", region=13, state="TX"
        )
        assert assign_region(case) == 13

    def test_no_info_returns_none(self):
        case = NLRBCaseRecord(
            case_number="test", case_type="RC"
        )
        assert assign_region(case) is None

    def test_works_with_dict(self):
        d = {"region": 5, "state": "MD"}
        assert assign_region(d) == 5

    def test_dict_state_fallback(self):
        d = {"state": "FL"}
        assert assign_region(d) == 12

    def test_dict_no_info(self):
        d = {"case_number": "test"}
        assert assign_region(d) is None


# ---------------------------------------------------------------------------
# aggregate_by_region tests
# ---------------------------------------------------------------------------


class TestAggregateByRegion:
    def test_groups_cases(self):
        cases = [
            NLRBCaseRecord(case_number="1", case_type="RC", region=5),
            NLRBCaseRecord(case_number="2", case_type="CA", region=5),
            NLRBCaseRecord(case_number="3", case_type="RC", region=13),
        ]
        groups = aggregate_by_region(cases)
        assert len(groups[5]) == 2
        assert len(groups[13]) == 1

    def test_unknown_region_grouped_under_zero(self):
        cases = [
            NLRBCaseRecord(case_number="1", case_type="RC"),
        ]
        groups = aggregate_by_region(cases)
        assert 0 in groups
        assert len(groups[0]) == 1

    def test_empty_input(self):
        assert aggregate_by_region([]) == {}


# ---------------------------------------------------------------------------
# region_summary tests
# ---------------------------------------------------------------------------


class TestRegionSummary:
    def test_basic_summary(self):
        cases = [
            NLRBCaseRecord(case_number="1", case_type="RC", region=5),
            NLRBCaseRecord(case_number="2", case_type="CA", region=5),
            NLRBCaseRecord(case_number="3", case_type="RC", region=13),
        ]
        summary = region_summary(cases)
        assert len(summary) == 2

        r5 = next(s for s in summary if s["region_number"] == 5)
        assert r5["office"] == "Baltimore"
        assert r5["case_count"] == 2

        r13 = next(s for s in summary if s["region_number"] == 13)
        assert r13["office"] == "Chicago"
        assert r13["case_count"] == 1

    def test_sorted_by_region(self):
        cases = [
            NLRBCaseRecord(case_number="1", case_type="RC", region=13),
            NLRBCaseRecord(case_number="2", case_type="RC", region=5),
        ]
        summary = region_summary(cases)
        assert summary[0]["region_number"] < summary[1]["region_number"]

    def test_unknown_region_labeled(self):
        cases = [
            NLRBCaseRecord(case_number="1", case_type="RC"),
        ]
        summary = region_summary(cases)
        assert summary[0]["office"] == "Unknown"
        assert summary[0]["region_number"] == 0

    def test_empty_input(self):
        assert region_summary([]) == []

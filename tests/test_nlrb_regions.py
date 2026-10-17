"""Tests for NLRB region boundary integration (SU#620)."""

from __future__ import annotations

import pytest

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
        assert set(NLRB_REGIONS) == {
            1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 12, 13, 14, 15, 16,
            18, 19, 20, 21, 22, 25, 27, 28, 29, 31, 32,
        }

    @pytest.mark.parametrize("number,office,states", [
        (20, "San Francisco", ["CA", "HI"]),
        (21, "Los Angeles", ["CA"]),
        (27, "Denver", ["CO", "UT", "WY"]),
        (28, "Phoenix", ["AZ", "NM", "NV"]),
        (32, "Oakland", ["CA", "NV"]),
    ])
    def test_corrected_state_lists(self, number, office, states):
        assert NLRB_REGIONS[number] == {"office": office, "states": states}

    def test_all_have_office(self):
        for num, info in NLRB_REGIONS.items():
            assert info["office"], f"Region {num} missing office"

    def test_all_have_states(self):
        for num, info in NLRB_REGIONS.items():
            assert len(info["states"]) > 0, f"Region {num} has no states"

    def test_region_numbers_in_range(self):
        for num in NLRB_REGIONS:
            assert 1 <= num <= 32

    def test_known_region(self):
        assert NLRB_REGIONS[13]["office"] == "Chicago"
        assert "IL" in NLRB_REGIONS[13]["states"]


# ---------------------------------------------------------------------------
# State → Region lookup tests
# ---------------------------------------------------------------------------


class TestStateToRegions:
    @pytest.mark.parametrize("state,regions", [
        ("AR", [15]),
        ("IA", [14]),
        ("KS", [14]),
        ("NE", [14]),
        ("OK", [14]),
        ("WY", [27]),
        ("AZ", [28]),
        ("NM", [28]),
        ("NV", [28, 32]),
        ("HI", [20]),
        ("CA", [20, 21, 31, 32]),
    ])
    def test_corrected_state_lookups(self, state, regions):
        assert lookup_region_by_state(state) == regions
        assert assign_region({"state": state}) == regions[0]

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

    def test_all_states_and_covered_territories_have_regions(self):
        # Independent of the registry so removing an entry cannot hide lost coverage.
        states = (
            "AL AK AZ AR CA CO CT DE FL GA HI ID IL IN IA KS KY LA ME MD MA MI "
            "MN MS MO MT NE NV NH NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT "
            "VT VA WA WV WI WY DC PR VI"
        ).split()
        uncovered = [state for state in states if not lookup_region_by_state(state)]
        assert uncovered == [], f"States without an NLRB region: {uncovered}"


# ---------------------------------------------------------------------------
# assign_region tests
# ---------------------------------------------------------------------------


class TestAssignRegion:
    @pytest.mark.parametrize("subregion,parent", [
        (11, 10), (17, 14), (24, 12), (26, 15), (30, 18), (37, 20),
    ])
    def test_subregional_prefix_rolls_up_to_parent(self, subregion, parent):
        case = NLRBCaseRecord(
            case_number=f"{subregion:02d}-RC-123456", case_type="RC", region=subregion,
        )
        assert assign_region(case) == parent
        assert assign_region({"region": str(subregion), "state": "TX"}) == parent

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
    @pytest.mark.parametrize("subregion,parent,office", [
        (11, 10, "Atlanta"),
        (17, 14, "St. Louis"),
        (24, 12, "Tampa"),
        (26, 15, "New Orleans"),
        (30, 18, "Minneapolis"),
        (37, 20, "San Francisco"),
    ])
    def test_subregion_and_parent_share_summary(self, subregion, parent, office):
        cases = [{"region": subregion}, {"region": parent}]
        assert region_summary(cases) == [{
            "region_number": parent, "office": office, "case_count": 2,
        }]

    @pytest.mark.parametrize("region", [33, 34, 36])
    def test_unverified_prefix_remains_unknown(self, region):
        case = {"region": region, "state": "TX"}
        assert assign_region(case) == region
        assert region_summary([case]) == [{
            "region_number": region, "office": "Unknown", "case_count": 1,
        }]

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

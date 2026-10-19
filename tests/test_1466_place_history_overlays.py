"""Regression tests for the TX/48201 place-history probe in issue #1466."""

from dataclasses import replace
from datetime import date

import pytest

from siege_utilities.geo.overlays.election_results import (
    DictElectionDataProvider,
    ElectionReturn,
)
from siege_utilities.geo.overlays.redistricting import (
    DictRedistrictingDataProvider,
    DistrictAssignment,
    RedistrictingOverlayResult,
)
from siege_utilities.geo.overlays.seats import SeatAssignment, SeatsOverlayResult


@pytest.mark.parametrize("provider_name", ["election", "redistricting"])
def test_state_fips_matches_state_abbreviations(provider_name: str) -> None:
    if provider_name == "election":
        provider = DictElectionDataProvider()
        texas = ElectionReturn(
            precinct_id="48201", election_year=2016, state="TX",
        )
        provider.add(texas)
        provider.add(replace(texas, state="CA"))
        records = provider.get_election_returns("48201", 2010, 2020, state_fips="48")
    else:
        provider = DictRedistrictingDataProvider()
        texas = DistrictAssignment(
            plan_id="C2100", district_id="TX-18", state="TX",
            from_date=date(2013, 1, 3), to_date=date(2023, 1, 3),
        )
        provider.add(texas)
        provider.add(replace(texas, state="CA"))
        records = provider.get_district_assignments("48201", 2010, 2020, state_fips="48")

    assert records == [texas]


@pytest.mark.parametrize("provider_name", ["election", "redistricting"])
def test_reversed_range_returns_in_range_records(provider_name: str) -> None:
    if provider_name == "election":
        provider = DictElectionDataProvider()
        election = ElectionReturn(
            precinct_id="48201", election_year=2016, state="TX",
        )
        provider.add(replace(election, election_year=2008))
        provider.add(election)
        provider.add(replace(election, election_year=2024))
        forward = provider.get_election_returns("48201", 2010, 2020)
        reverse = provider.get_election_returns("48201", 2020, 2010)
        expected = [election]
    else:
        provider = DictRedistrictingDataProvider()
        old_plan = DistrictAssignment(
            plan_id="C2100", district_id="TX-18", state="TX",
            from_date=date(2013, 1, 3), to_date=date(2023, 1, 3),
        )
        provider.add(replace(
            old_plan, plan_id="previous", from_date=None, to_date=date(2009, 12, 31),
        ))
        provider.add(old_plan)
        provider.add(replace(
            old_plan, plan_id="C2193", from_date=date(2023, 1, 3), to_date=None,
        ))
        forward = provider.get_district_assignments("48201", 2010, 2020)
        reverse = provider.get_district_assignments("48201", 2020, 2010)
        expected = [old_plan]

    assert forward == expected
    assert reverse == expected


def test_current_districts_keeps_ongoing_assignment_per_office() -> None:
    senate = SeatAssignment(
        seat_label="TX SD-15", office="STATE_UPPER", district_label="15",
        state_fips="48", from_year=2022, to_year=None,
    )
    old_house = SeatAssignment(
        seat_label="US House TX-18 (2013)", office="US_HOUSE", district_label="18",
        state_fips="48", from_year=2013, to_year=2024,
    )
    house = replace(old_house, seat_label="US House TX-18 (2025)", from_year=2025, to_year=None)
    result = SeatsOverlayResult("48201", [senate, old_house, house])

    assert result.current_districts == [senate, house]
    assert len({seat.office for seat in result.current_districts}) == 2


def test_active_at_handover_date_selects_only_new_plan() -> None:
    old_plan = DistrictAssignment(
        plan_id="C2100", district_id="TX-18", state="TX",
        from_date=date(2013, 1, 3), to_date=date(2023, 1, 3),
    )
    new_plan = replace(
        old_plan, plan_id="C2193", from_date=date(2023, 1, 3), to_date=None,
    )
    result = RedistrictingOverlayResult("48201", [old_plan, new_plan])

    assert result.active_at(date(2023, 1, 3)) == [new_plan]
    assert result.active_at(date(2023, 1, 2)) == [old_plan]
    assert result.active_at(date(2013, 1, 3)) == [old_plan]
    assert result.active_at(date(2013, 1, 2)) == []
    assert result.active_at(date(2030, 1, 3)) == [new_plan]

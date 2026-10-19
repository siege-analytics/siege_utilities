"""Regression tests for the TX/48201 place-history probe in issue #1466."""

from dataclasses import replace
from datetime import date

import pytest

from siege_utilities.geo.overlay_registry import OverlayRegistry
from siege_utilities.geo.overlays.election_results import (
    DictElectionDataProvider,
    ElectionResultsOverlay,
    ElectionReturn,
)
from siege_utilities.geo.overlays.redistricting import (
    DictRedistrictingDataProvider,
    DistrictAssignment,
    RedistrictingOverlay,
    RedistrictingOverlayResult,
)
from siege_utilities.geo.overlays.seats import (
    DictSeatsProvider,
    SeatAssignment,
    SeatsOverlay,
    SeatsOverlayResult,
    _current_districts_at,
)
from siege_utilities.geo.place_history import DictCrosswalkProvider, place_history


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


@pytest.mark.parametrize("to_year", [2030, None], ids=["finite", "ongoing"])
@pytest.mark.parametrize("reverse", [False, True], ids=["forward", "reverse"])
def test_current_districts_preserves_split_districts(
    to_year: int | None, reverse: bool,
) -> None:
    assignments = [
        SeatAssignment(
            seat_label="US House IL-7", office="US_HOUSE", district_label=district,
            state_fips="17", plan_name="2020 Plan", plan_year=2022,
            from_year=2020, to_year=to_year, containment_pct=containment,
        )
        for district, containment in [("7", 0.7), ("4", 0.3)]
    ]
    if reverse:
        assignments.reverse()
    provider = DictSeatsProvider()
    for assignment in assignments:
        provider.add(assignment)

    result = SeatsOverlay(provider).fetch("A", 2020, 2025)

    assert result.current_districts == assignments
    assert sum(a.containment_pct for a in result.current_districts) == pytest.approx(1.0)


@pytest.mark.parametrize(
    ("old_start", "old_end", "new_end"),
    [(2012, 2021, None), (2012, None, None), (2012, 2030, 2030), (None, None, None)],
    ids=["competing-history", "ongoing-periods", "overlapping-periods", "unknown-start"],
)
def test_current_districts_selects_newest_applicable_period(
    old_start: int | None, old_end: int | None, new_end: int | None,
) -> None:
    old = SeatAssignment(
        office="US_HOUSE", district_label="5", from_year=old_start, to_year=old_end,
    )
    new = replace(old, district_label="7", from_year=2022, to_year=new_end)
    result = SeatsOverlayResult("48201", [old, new])

    assert result.current_districts == [new]


def test_current_districts_keeps_finite_rows_in_ongoing_period() -> None:
    finite = SeatAssignment(
        office="US_HOUSE", district_label="4", from_year=2022, to_year=2030,
        containment_pct=0.3,
    )
    ongoing = replace(finite, district_label="7", to_year=None, containment_pct=0.7)
    assignments = [finite, ongoing]
    result = SeatsOverlayResult("48201", assignments)

    assert result.current_districts == assignments
    assert sum(a.containment_pct for a in result.current_districts) == pytest.approx(1.0)


def test_current_districts_preserves_ongoing_seat_over_later_finite_period() -> None:
    ongoing = SeatAssignment(
        office="STATE_UPPER", district_label="15", from_year=2022, to_year=None,
    )
    ended = replace(ongoing, district_label="16", from_year=2023, to_year=2024)

    assert SeatsOverlayResult("48201", [ongoing, ended]).current_districts == [ongoing]


@pytest.mark.parametrize("reverse", [False, True], ids=["forward", "reverse"])
@pytest.mark.parametrize(
    ("reference_year", "periods", "expected_districts"),
    [
        pytest.param(
            2024, [("15", 2022, None, 1.0), ("16", 2023, 2024, 1.0)], ["15"],
            id="ongoing-at-finite-end",
        ),
        pytest.param(
            2026, [("15", 2022, None, 1.0), ("16", 2023, 2024, 1.0)], ["15"],
            id="ongoing-after-finite-end",
        ),
        pytest.param(
            2015, [("15", 2022, None, 1.0), ("9", 2012, 2016, 1.0)], ["9"],
            id="past-reference-excludes-future-ongoing",
        ),
        pytest.param(
            2025, [("4", 2022, None, 0.3), ("7", 2022, None, 0.7)], ["4", "7"],
            id="ongoing-split",
        ),
        pytest.param(
            2025, [("4", 2022, 2030, 0.3), ("7", 2022, 2030, 0.7)], ["4", "7"],
            id="finite-split",
        ),
        pytest.param(
            2022, [("5", 2012, 2021, 1.0), ("7", 2022, None, 1.0)], ["7"],
            id="history",
        ),
    ],
)
def test_current_districts_at_reference(
    reference_year: int,
    periods: list[tuple[str, int, int | None, float]],
    expected_districts: list[str],
    reverse: bool,
) -> None:
    assignments = [
        SeatAssignment(
            office="STATE_UPPER", district_label=district,
            from_year=start, to_year=end, containment_pct=containment,
        )
        for district, start, end, containment in periods
    ]
    if reverse:
        assignments.reverse()
        expected_districts = list(reversed(expected_districts))

    current = _current_districts_at(assignments, reference_year)

    assert [a.district_label for a in current] == expected_districts
    assert sum(a.containment_pct for a in current) == pytest.approx(1.0)


def test_empty_redistricting_span_never_applies() -> None:
    when = date(2023, 6, 1)
    assignment = DistrictAssignment(plan_id="empty", from_date=when, to_date=when)
    provider = DictRedistrictingDataProvider()
    provider.add(assignment)
    result = RedistrictingOverlayResult("48201", [assignment])

    assert result.active_at(when) == []
    assert provider.get_district_assignments("48201", 2023, 2023) == []
    assert RedistrictingOverlay(provider).fetch("48201", 2023, 2023).plan_count == 0


@pytest.mark.parametrize("query", ["provider", "active_at"])
def test_inverted_redistricting_span_raises(query: str) -> None:
    assignment = DistrictAssignment(
        plan_id="inverted", from_date=date(2023, 6, 2), to_date=date(2023, 6, 1),
    )
    provider = DictRedistrictingDataProvider()
    provider.add(assignment)
    result = RedistrictingOverlayResult("48201", [assignment])

    with pytest.raises(ValueError, match="from_date.*to_date"):
        if query == "provider":
            provider.get_district_assignments("48201", 2023, 2023)
        else:
            result.active_at(date(2023, 6, 1))


@pytest.mark.parametrize(
    ("from_year", "to_year", "expected_years"),
    [(2010, 2020, [2010, 2016, 2020]), (2020, 2010, [2010, 2016, 2020]), (2020, 2020, [2020])],
)
def test_election_range_includes_both_endpoint_years(
    from_year: int, to_year: int, expected_years: list[int],
) -> None:
    provider = DictElectionDataProvider()
    for year in [2008, 2010, 2016, 2020, 2024]:
        provider.add(ElectionReturn(precinct_id="48201", election_year=year, state="TX"))

    records = provider.get_election_returns("48201", from_year, to_year)

    assert [record.election_year for record in records] == expected_years


def test_redistricting_year_range_respects_exclusive_assignment_end() -> None:
    provider = DictRedistrictingDataProvider()
    ended = DistrictAssignment(state="TX", from_date=None, to_date=date(2020, 1, 1))
    first_day = replace(ended, plan_id="first-day", to_date=date(2020, 1, 2))
    last_day = replace(ended, plan_id="last-day", from_date=date(2020, 12, 31), to_date=None)
    future = replace(last_day, plan_id="future", from_date=date(2021, 1, 1))
    for assignment in [ended, first_day, last_day, future]:
        provider.add(assignment)

    assert provider.get_district_assignments("48201", 2020, 2020) == [first_day, last_day]
    result = RedistrictingOverlayResult("48201", [ended, first_day])
    assert result.active_at(date(2020, 1, 1)) == [first_day]


def test_place_history_combines_fips_filter_with_reversed_range() -> None:
    elections = DictElectionDataProvider()
    election = ElectionReturn(precinct_id="48201", election_year=2016, state="TX")
    elections.add(election)
    elections.add(replace(election, state="CA"))
    districts = DictRedistrictingDataProvider()
    old_plan = DistrictAssignment(
        plan_id="C2100", district_id="TX-18", state="TX",
        from_date=date(2013, 1, 3), to_date=date(2023, 1, 3),
    )
    districts.add(old_plan)
    districts.add(replace(old_plan, state="CA"))
    districts.add(replace(old_plan, plan_id="C2193", from_date=date(2023, 1, 3), to_date=None))
    registry = OverlayRegistry()
    registry.register_instance("election_results", ElectionResultsOverlay(elections))
    registry.register_instance("redistricting", RedistrictingOverlay(districts))

    result = place_history(
        "48201", 2020, 2010, state_fips="48",
        overlays=["election_results", "redistricting"], overlay_registry=registry,
        provider=DictCrosswalkProvider(),
    )

    assert result.errors == []
    assert result.direction == "reverse"
    assert result.overlays["election_results"].returns == [election]
    assert result.overlays["redistricting"].assignments == [old_plan]


@pytest.mark.parametrize("reverse", [False, True], ids=["forward", "reverse"])
def test_current_districts_omits_office_not_covering_shared_reference(reverse: bool) -> None:
    ended = SeatAssignment(
        office="STATE_UPPER", district_label="3", from_year=2012, to_year=2016,
    )
    ongoing = SeatAssignment(
        office="US_HOUSE", district_label="8", from_year=2018, to_year=None,
    )
    assignments = [ended, ongoing]
    if reverse:
        assignments.reverse()

    current = SeatsOverlayResult("48201", assignments).current_districts

    assert current == [ongoing]
    assert all(assignment.office != ended.office for assignment in current)


@pytest.mark.parametrize("ref", [2012, 2016], ids=["at-from-year", "at-to-year"])
def test_covers_ref_is_inclusive_at_year_boundaries(ref: int) -> None:
    d9 = SeatAssignment(
        office="US_HOUSE", district_label="9", from_year=2012, to_year=2016,
    )

    assert _current_districts_at([d9], ref) == [d9]


@pytest.mark.parametrize("reverse", [False, True], ids=["forward", "reverse"])
def test_mixed_finite_and_ongoing_same_period_keeps_both(reverse: bool) -> None:
    finite = SeatAssignment(
        office="US_HOUSE", district_label="4", from_year=2020, to_year=2030,
        containment_pct=0.3,
    )
    ongoing = replace(finite, district_label="7", to_year=None, containment_pct=0.7)
    assignments = [finite, ongoing]
    if reverse:
        assignments.reverse()

    current = _current_districts_at(assignments, 2025)

    assert current == assignments
    assert sum(a.containment_pct for a in current) == pytest.approx(1.0)
    assert SeatsOverlayResult("48201", assignments).current_districts == assignments


@pytest.mark.parametrize("reverse", [False, True], ids=["forward", "reverse"])
def test_current_districts_at_2020_omits_office_without_candidates(reverse: bool) -> None:
    ended = SeatAssignment(
        office="X", district_label="3", from_year=2012, to_year=2016,
    )
    ongoing = SeatAssignment(
        office="Y", district_label="8", from_year=2018, to_year=None,
    )
    assignments = [ended, ongoing]
    if reverse:
        assignments.reverse()
    result = SeatsOverlayResult("48201", assignments)

    current = [
        assignment
        for office in result.offices
        for assignment in _current_districts_at(result.for_office(office), 2020)
    ]

    assert current == [ongoing]
    assert _current_districts_at(result.for_office("X"), 2020) == []
    assert result.current_districts == [ongoing]

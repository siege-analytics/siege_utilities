"""Tests for seats overlay (SU#609)."""

from __future__ import annotations

import pytest

from siege_utilities.geo.overlay_registry import OverlayRegistry, PlaceHistoryOverlay
from siege_utilities.geo.overlays.seats import (
    DictSeatsProvider,
    SeatAssignment,
    SeatsOverlay,
    SeatsOverlayResult,
)


def _sa(
    seat_label="US House IL-7",
    office="US_HOUSE",
    district_label="7",
    state_fips="17",
    plan_name="2020 Plan",
    plan_year=2022,
    from_year=2022,
    to_year=2032,
    containment_pct=1.0,
):
    return SeatAssignment(
        seat_label=seat_label,
        office=office,
        district_label=district_label,
        state_fips=state_fips,
        plan_name=plan_name,
        plan_year=plan_year,
        from_year=from_year,
        to_year=to_year,
        containment_pct=containment_pct,
    )


# ---------------------------------------------------------------------------
# SeatAssignment dataclass
# ---------------------------------------------------------------------------


class TestSeatAssignment:
    def test_defaults(self):
        a = SeatAssignment()
        assert a.seat_label == ""
        assert a.containment_pct == 1.0

    def test_fields(self):
        a = _sa()
        assert a.office == "US_HOUSE"
        assert a.district_label == "7"
        assert a.plan_year == 2022


# ---------------------------------------------------------------------------
# SeatsOverlayResult
# ---------------------------------------------------------------------------


class TestSeatsOverlayResult:
    def test_empty_result(self):
        r = SeatsOverlayResult(geoid="A")
        assert r.current_districts == []
        assert r.offices == []

    def test_current_districts(self):
        r = SeatsOverlayResult(
            geoid="A",
            assignments=[
                _sa(from_year=2012, to_year=2022, plan_name="2010 Plan"),
                _sa(from_year=2022, to_year=2032, plan_name="2020 Plan"),
            ],
        )
        current = r.current_districts
        assert len(current) == 1
        assert current[0].plan_name == "2020 Plan"

    def test_offices(self):
        r = SeatsOverlayResult(
            geoid="A",
            assignments=[
                _sa(office="US_HOUSE"),
                _sa(office="STATE_UPPER"),
                _sa(office="US_HOUSE"),
            ],
        )
        assert r.offices == ["STATE_UPPER", "US_HOUSE"]

    def test_for_office(self):
        r = SeatsOverlayResult(
            geoid="A",
            assignments=[
                _sa(office="US_HOUSE", district_label="7"),
                _sa(office="STATE_UPPER", district_label="3"),
                _sa(office="US_HOUSE", district_label="4"),
            ],
        )
        house = r.for_office("US_HOUSE")
        assert len(house) == 2
        assert all(a.office == "US_HOUSE" for a in house)


# ---------------------------------------------------------------------------
# DictSeatsProvider
# ---------------------------------------------------------------------------


class TestDictSeatsProvider:
    def test_empty(self):
        p = DictSeatsProvider()
        assert p.get_assignments("A", 2000, 2020) == []

    def test_add_and_get(self):
        p = DictSeatsProvider()
        p.add(_sa(from_year=2012, to_year=2022))
        results = p.get_assignments("A", 2010, 2025)
        assert len(results) == 1

    def test_time_range_filtering(self):
        p = DictSeatsProvider()
        p.add(_sa(from_year=2012, to_year=2022))
        p.add(_sa(from_year=2022, to_year=2032))

        assert len(p.get_assignments("A", 2010, 2015)) == 1
        assert len(p.get_assignments("A", 2010, 2025)) == 2
        assert len(p.get_assignments("A", 2025, 2030)) == 1

    def test_state_fips_filtering(self):
        p = DictSeatsProvider()
        p.add(_sa(state_fips="17", from_year=2020, to_year=2030))
        p.add(_sa(state_fips="06", from_year=2020, to_year=2030))

        results = p.get_assignments("A", 2020, 2025, state_fips="17")
        assert len(results) == 1
        assert results[0].state_fips == "17"

    def test_sorted_by_from_year(self):
        p = DictSeatsProvider()
        p.add(_sa(from_year=2022, to_year=2032))
        p.add(_sa(from_year=2012, to_year=2022))
        results = p.get_assignments("A", 2010, 2030)
        assert results[0].from_year == 2012
        assert results[1].from_year == 2022

    def test_reverse_year_range(self):
        p = DictSeatsProvider()
        p.add(_sa(from_year=2015, to_year=2025))
        results = p.get_assignments("A", 2025, 2015)
        assert len(results) == 1


# ---------------------------------------------------------------------------
# SeatsOverlay
# ---------------------------------------------------------------------------


class TestSeatsOverlay:
    def test_is_overlay(self):
        o = SeatsOverlay(provider=DictSeatsProvider())
        assert isinstance(o, PlaceHistoryOverlay)
        assert o.name == "seats"

    def test_fetch_returns_result(self):
        p = DictSeatsProvider()
        p.add(_sa(from_year=2020, to_year=2030))
        o = SeatsOverlay(provider=p)

        result = o.fetch("17031010100", 2020, 2025)
        assert isinstance(result, SeatsOverlayResult)
        assert result.geoid == "17031010100"
        assert len(result.assignments) == 1

    def test_fetch_empty(self):
        p = DictSeatsProvider()
        o = SeatsOverlay(provider=p)
        result = o.fetch("A", 2000, 2020)
        assert result.assignments == []

    def test_no_provider_raises(self):
        o = SeatsOverlay(provider=None)
        with pytest.raises(RuntimeError, match="No seats data provider"):
            o.fetch("A", 2000, 2020)

    def test_fetch_multiple_offices(self):
        p = DictSeatsProvider()
        p.add(_sa(office="US_HOUSE", from_year=2020, to_year=2030))
        p.add(_sa(office="STATE_UPPER", from_year=2020, to_year=2030))
        o = SeatsOverlay(provider=p)

        result = o.fetch("A", 2020, 2025)
        assert len(result.assignments) == 2

    def test_fetch_passes_state_fips(self):
        p = DictSeatsProvider()
        p.add(_sa(state_fips="17", from_year=2020, to_year=2030))
        p.add(_sa(state_fips="06", from_year=2020, to_year=2030))
        o = SeatsOverlay(provider=p)

        result = o.fetch("A", 2020, 2025, state_fips="17")
        assert len(result.assignments) == 1

    def test_multi_plan_timeline(self):
        p = DictSeatsProvider()
        p.add(_sa(plan_name="2010 Plan", from_year=2012, to_year=2022))
        p.add(_sa(plan_name="2020 Plan", from_year=2022, to_year=2032))
        o = SeatsOverlay(provider=p)

        result = o.fetch("A", 2010, 2030)
        assert len(result.assignments) == 2
        assert result.assignments[0].plan_name == "2010 Plan"
        assert result.assignments[1].plan_name == "2020 Plan"

    def test_registry_integration(self):
        registry = OverlayRegistry()
        p = DictSeatsProvider()
        p.add(_sa(from_year=2020, to_year=2030))
        registry.register_instance("seats", SeatsOverlay(provider=p))

        overlay = registry.get("seats")
        assert overlay is not None
        result = overlay.fetch("A", 2020, 2025)
        assert isinstance(result, SeatsOverlayResult)

    def test_partial_containment(self):
        p = DictSeatsProvider()
        p.add(_sa(containment_pct=0.7, district_label="7", from_year=2020, to_year=2030))
        p.add(_sa(containment_pct=0.3, district_label="4", from_year=2020, to_year=2030))
        o = SeatsOverlay(provider=p)

        result = o.fetch("A", 2020, 2025)
        assert len(result.assignments) == 2
        assert sum(a.containment_pct for a in result.assignments) == pytest.approx(1.0)

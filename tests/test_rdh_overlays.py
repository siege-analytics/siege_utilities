"""Tests for RDH overlays — redistricting + election results (SU#636)."""

from __future__ import annotations

from datetime import date

import pytest

from siege_utilities.geo.overlay_registry import OverlayRegistry
from siege_utilities.geo.overlays.redistricting import (
    DictRedistrictingDataProvider,
    DistrictAssignment,
    RedistrictingOverlay,
    RedistrictingOverlayResult,
)
from siege_utilities.geo.overlays.election_results import (
    DictElectionDataProvider,
    ElectionDataProvider,
    ElectionResultsOverlay,
    ElectionResultsOverlayResult,
    ElectionReturn,
)


def _da(plan_id="P1", plan_name="Plan 2022", plan_type="congressional",
        district_id="TX-28", state="TX", from_date="2022-01-01",
        to_date=None, enacted_by="legislature", court_case="", **kw):
    return DistrictAssignment(
        plan_id=plan_id, plan_name=plan_name, plan_type=plan_type,
        district_id=district_id, state=state,
        from_date=date.fromisoformat(from_date) if isinstance(from_date, str) else from_date,
        to_date=date.fromisoformat(to_date) if isinstance(to_date, str) and to_date else to_date,
        enacted_by=enacted_by, court_case=court_case, **kw,
    )


def _er(precinct_id="PCT-1", year=2022, office="US_HOUSE", candidate="Smith",
        party="DEM", votes=100, total_votes=200, state="TX", **kw):
    return ElectionReturn(
        precinct_id=precinct_id, election_year=year, office=office,
        candidate=candidate, party=party, votes=votes,
        total_votes=total_votes, vote_share=votes / total_votes if total_votes else 0,
        state=state, **kw,
    )


# ---- Redistricting Overlay ----

class TestDistrictAssignment:
    def test_defaults(self):
        a = DistrictAssignment()
        assert a.plan_id == ""
        assert a.from_date is None

    def test_fields(self):
        a = _da()
        assert a.plan_id == "P1"
        assert a.from_date == date(2022, 1, 1)


class TestRedistrictingOverlayResult:
    def test_empty(self):
        r = RedistrictingOverlayResult(geoid="48453")
        assert r.plan_count == 0
        assert not r.had_court_intervention

    def test_plan_count(self):
        r = RedistrictingOverlayResult(assignments=[
            _da(plan_id="P1"), _da(plan_id="P2"),
        ])
        assert r.plan_count == 2

    def test_had_court_intervention(self):
        r = RedistrictingOverlayResult(assignments=[
            _da(court_case="Allen v. Milligan"),
        ])
        assert r.had_court_intervention

    def test_plan_types(self):
        r = RedistrictingOverlayResult(assignments=[
            _da(plan_type="congressional"),
            _da(plan_type="state_senate"),
            _da(plan_type="congressional"),
        ])
        assert r.plan_types == ["congressional", "state_senate"]

    def test_for_plan_type(self):
        r = RedistrictingOverlayResult(assignments=[
            _da(plan_type="congressional"),
            _da(plan_type="state_senate"),
        ])
        assert len(r.for_plan_type("congressional")) == 1

    def test_active_at(self):
        r = RedistrictingOverlayResult(assignments=[
            _da(plan_id="P1", from_date="2012-01-01", to_date="2021-12-31"),
            _da(plan_id="P2", from_date="2022-01-01"),
        ])
        active = r.active_at(date(2015, 6, 1))
        assert len(active) == 1
        assert active[0].plan_id == "P1"

    def test_active_at_open_ended(self):
        r = RedistrictingOverlayResult(assignments=[
            _da(from_date="2022-01-01", to_date=None),
        ])
        assert len(r.active_at(date(2025, 1, 1))) == 1


class TestDictRedistrictingProvider:
    def test_empty(self):
        p = DictRedistrictingDataProvider()
        assert p.get_district_assignments("G1", 2020, 2024) == []

    def test_time_range_filter(self):
        p = DictRedistrictingDataProvider()
        p.add(_da(from_date="2012-01-01", to_date="2021-12-31"))
        p.add(_da(plan_id="P2", from_date="2022-01-01"))

        assert len(p.get_district_assignments("G1", 2020, 2024)) == 2
        assert len(p.get_district_assignments("G1", 2023, 2024)) == 1

    def test_state_filter(self):
        p = DictRedistrictingDataProvider()
        p.add(_da(state="TX"))
        p.add(_da(state="CA"))
        assert len(p.get_district_assignments("G1", 2020, 2024, state_fips="TX")) == 1


class TestRedistrictingOverlay:
    def test_name(self):
        ov = RedistrictingOverlay()
        assert ov.name == "redistricting"

    def test_no_provider(self):
        ov = RedistrictingOverlay()
        result = ov.fetch("48453", 2020, 2024)
        assert result.geoid == "48453"
        assert result.assignments == []

    def test_is_available(self):
        assert not RedistrictingOverlay().is_available()
        assert RedistrictingOverlay(DictRedistrictingDataProvider()).is_available()

    def test_fetch(self):
        p = DictRedistrictingDataProvider()
        p.add(_da(plan_id="P1", from_date="2012-01-01", to_date="2021-12-31"))
        p.add(_da(plan_id="P2", from_date="2022-01-01"))

        ov = RedistrictingOverlay(provider=p)
        result = ov.fetch("48453", 2020, 2024)
        assert len(result.assignments) == 2
        assert result.assignments[0].plan_id == "P1"

    def test_registers_with_registry(self):
        reg = OverlayRegistry()
        p = DictRedistrictingDataProvider()
        ov = RedistrictingOverlay(provider=p)
        reg.register_instance("redistricting", ov)
        assert reg.is_registered("redistricting")
        assert reg.get("redistricting").name == "redistricting"

    def test_court_order_scenario(self):
        p = DictRedistrictingDataProvider()
        p.add(_da(
            plan_id="AL-CD-2021", from_date="2022-01-01", to_date="2023-06-08",
            state="AL", court_case="",
        ))
        p.add(_da(
            plan_id="AL-CD-2023-COURT", from_date="2023-10-05",
            state="AL", court_case="Allen v. Milligan",
            enacted_by="court",
        ))

        ov = RedistrictingOverlay(provider=p)
        result = ov.fetch("01001", 2022, 2024, state_fips="AL")
        assert result.plan_count == 2
        assert result.had_court_intervention


# ---- Election Results Overlay ----

class TestElectionReturn:
    def test_defaults(self):
        r = ElectionReturn()
        assert r.votes == 0
        assert r.reconciliation_method == "direct"

    def test_fields(self):
        r = _er()
        assert r.vote_share == pytest.approx(0.5)


class TestElectionResultsOverlayResult:
    def test_empty(self):
        r = ElectionResultsOverlayResult(geoid="48453")
        assert r.election_years == []
        assert r.offices == []

    def test_election_years(self):
        r = ElectionResultsOverlayResult(returns=[
            _er(year=2020), _er(year=2022), _er(year=2020),
        ])
        assert r.election_years == [2020, 2022]

    def test_offices(self):
        r = ElectionResultsOverlayResult(returns=[
            _er(office="US_HOUSE"), _er(office="US_PRESIDENT"),
        ])
        assert r.offices == ["US_HOUSE", "US_PRESIDENT"]

    def test_for_year(self):
        r = ElectionResultsOverlayResult(returns=[
            _er(year=2020), _er(year=2022),
        ])
        assert len(r.for_year(2020)) == 1

    def test_for_office(self):
        r = ElectionResultsOverlayResult(returns=[
            _er(office="US_HOUSE"), _er(office="GOVERNOR"),
        ])
        assert len(r.for_office("US_HOUSE")) == 1

    def test_for_year_office(self):
        r = ElectionResultsOverlayResult(returns=[
            _er(year=2022, office="US_HOUSE"),
            _er(year=2022, office="GOVERNOR"),
            _er(year=2020, office="US_HOUSE"),
        ])
        assert len(r.for_year_office(2022, "US_HOUSE")) == 1

    def test_party_totals(self):
        r = ElectionResultsOverlayResult(returns=[
            _er(year=2022, office="US_HOUSE", party="DEM", votes=100),
            _er(year=2022, office="US_HOUSE", party="REP", votes=80),
            _er(year=2022, office="US_HOUSE", party="DEM", votes=50),
        ])
        totals = r.party_totals(2022, "US_HOUSE")
        assert totals["DEM"] == 150
        assert totals["REP"] == 80


class TestDictElectionDataProvider:
    def test_empty(self):
        p = DictElectionDataProvider()
        assert p.get_election_returns("G1", 2020, 2024) == []

    def test_year_filter(self):
        p = DictElectionDataProvider()
        p.add(_er(year=2020))
        p.add(_er(year=2022))
        p.add(_er(year=2024))
        assert len(p.get_election_returns("G1", 2021, 2023)) == 1

    def test_state_filter(self):
        p = DictElectionDataProvider()
        p.add(_er(state="TX"))
        p.add(_er(state="CA"))
        assert len(p.get_election_returns("G1", 2020, 2024, state_fips="TX")) == 1


class TestElectionResultsOverlay:
    def test_name(self):
        ov = ElectionResultsOverlay()
        assert ov.name == "election_results"

    def test_no_provider(self):
        ov = ElectionResultsOverlay()
        result = ov.fetch("48453", 2020, 2024)
        assert result.geoid == "48453"
        assert result.returns == []

    def test_is_available(self):
        assert not ElectionResultsOverlay().is_available()
        assert ElectionResultsOverlay(DictElectionDataProvider()).is_available()

    def test_fetch(self):
        p = DictElectionDataProvider()
        p.add(_er(year=2020, party="DEM"))
        p.add(_er(year=2022, party="REP"))

        ov = ElectionResultsOverlay(provider=p)
        result = ov.fetch("48453", 2020, 2024)
        assert len(result.returns) == 2
        assert result.returns[0].election_year == 2020

    def test_registers_with_registry(self):
        reg = OverlayRegistry()
        ov = ElectionResultsOverlay(provider=DictElectionDataProvider())
        reg.register_instance("election_results", ov)
        assert reg.is_registered("election_results")

    def test_sorted_output(self):
        p = DictElectionDataProvider()
        p.add(_er(year=2022, office="GOVERNOR", party="DEM"))
        p.add(_er(year=2020, office="US_HOUSE", party="REP"))
        p.add(_er(year=2022, office="US_HOUSE", party="DEM"))

        ov = ElectionResultsOverlay(provider=p)
        result = ov.fetch("48453", 2020, 2024)
        years = [r.election_year for r in result.returns]
        assert years == sorted(years)

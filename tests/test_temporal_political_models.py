"""Tests for temporal political models and schemas (Phase A/B/C)."""

from __future__ import annotations

from datetime import date, datetime

import pytest

from siege_utilities.geo.schemas.temporal_political import (
    CongressionalTermSchema,
    SeatSchema,
    StateElectionCalendarSchema,
)
from siege_utilities.geo.schemas.temporal_events import (
    RaceSchema,
    RaceEventSchema,
    ReturnSnapshotSchema,
    SpatioTemporalEventSchema,
)


# ---------------------------------------------------------------------------
# CongressionalTermSchema
# ---------------------------------------------------------------------------

class TestCongressionalTermSchema:

    def test_basic_creation(self):
        schema = CongressionalTermSchema(
            congress_number=119,
            start_date=date(2025, 1, 3),
            end_date=date(2027, 1, 3),
            election_year=2024,
            is_presidential=True,
            senate_classes_up=[2],
        )
        assert schema.congress_number == 119
        assert schema.start_date == date(2025, 1, 3)
        assert schema.end_date == date(2027, 1, 3)
        assert schema.election_year == 2024
        assert schema.is_presidential is True
        assert schema.senate_classes_up == [2]

    def test_defaults(self):
        schema = CongressionalTermSchema(
            congress_number=1,
            start_date=date(1789, 3, 4),
            end_date=date(1791, 3, 4),
            election_year=1788,
        )
        assert schema.is_presidential is False
        assert schema.senate_classes_up == []

    def test_congress_number_bounds(self):
        with pytest.raises(Exception):
            CongressionalTermSchema(
                congress_number=0,
                start_date=date(2025, 1, 3),
                end_date=date(2027, 1, 3),
                election_year=2024,
            )

    def test_congress_number_upper_bound(self):
        with pytest.raises(Exception):
            CongressionalTermSchema(
                congress_number=201,
                start_date=date(2025, 1, 3),
                end_date=date(2027, 1, 3),
                election_year=2024,
            )


# ---------------------------------------------------------------------------
# SeatSchema
# ---------------------------------------------------------------------------

class TestSeatSchema:

    def test_house_seat(self):
        schema = SeatSchema(
            office="US_HOUSE",
            state_fips="06",
            district_label="12",
        )
        assert schema.office == "US_HOUSE"
        assert schema.state_fips == "06"
        assert schema.district_label == "12"
        assert schema.senate_class is None
        assert schema.is_active is True

    def test_senate_seat(self):
        schema = SeatSchema(
            office="US_SENATE",
            state_fips="48",
            senate_class=2,
        )
        assert schema.office == "US_SENATE"
        assert schema.senate_class == 2
        assert schema.district_label == ""

    def test_president_seat(self):
        schema = SeatSchema(office="PRESIDENT")
        assert schema.state_fips is None
        assert schema.district_label == ""

    def test_senate_class_bounds(self):
        with pytest.raises(Exception):
            SeatSchema(
                office="US_SENATE",
                state_fips="06",
                senate_class=4,
            )

    def test_inactive_seat(self):
        schema = SeatSchema(
            office="US_HOUSE",
            state_fips="06",
            district_label="53",
            is_active=False,
        )
        assert schema.is_active is False


# ---------------------------------------------------------------------------
# StateElectionCalendarSchema
# ---------------------------------------------------------------------------

class TestStateElectionCalendarSchema:

    def test_full_calendar(self):
        schema = StateElectionCalendarSchema(
            state_fips="06",
            congress_number=119,
            primary_date=date(2024, 3, 5),
            primary_type="top_two",
            general_date=date(2024, 11, 5),
            registration_deadline=date(2024, 10, 21),
            early_voting_start=date(2024, 10, 7),
            early_voting_end=date(2024, 11, 4),
            certification_deadline=date(2024, 12, 11),
        )
        assert schema.state_fips == "06"
        assert schema.primary_type == "top_two"
        assert schema.general_date == date(2024, 11, 5)

    def test_minimal_calendar(self):
        schema = StateElectionCalendarSchema(
            state_fips="48",
            congress_number=119,
        )
        assert schema.primary_date is None
        assert schema.general_date is None
        assert schema.certification_deadline is None


# ---------------------------------------------------------------------------
# RaceSchema
# ---------------------------------------------------------------------------

class TestRaceSchema:

    def test_regular_race(self):
        schema = RaceSchema(
            seat_id=1,
            congress_number=119,
        )
        assert schema.is_special is False
        assert schema.cause_of_special == ""

    def test_special_election(self):
        schema = RaceSchema(
            seat_id=42,
            congress_number=118,
            is_special=True,
            cause_of_special="resignation",
        )
        assert schema.is_special is True
        assert schema.cause_of_special == "resignation"


# ---------------------------------------------------------------------------
# SpatioTemporalEventSchema
# ---------------------------------------------------------------------------

class TestSpatioTemporalEventSchema:

    def test_court_ruling(self):
        schema = SpatioTemporalEventSchema(
            feature_id="rucho-v-common-cause",
            name="Rucho v. Common Cause",
            vintage_year=2019,
            event_start=datetime(2019, 6, 27, 10, 0),
            event_category="COURT_RULING",
            description="Supreme Court ruled partisan gerrymandering claims non-justiciable",
        )
        assert schema.event_category == "COURT_RULING"
        assert schema.event_end is None

    def test_natural_disaster(self):
        schema = SpatioTemporalEventSchema(
            feature_id="hurricane-helene-2024",
            name="Hurricane Helene",
            vintage_year=2024,
            event_start=datetime(2024, 9, 24),
            event_end=datetime(2024, 9, 28),
            event_category="NATURAL_DISASTER",
        )
        assert schema.event_end == datetime(2024, 9, 28)


# ---------------------------------------------------------------------------
# RaceEventSchema
# ---------------------------------------------------------------------------

class TestRaceEventSchema:

    def test_general_election_event(self):
        schema = RaceEventSchema(
            race_id=1,
            event_type="GENERAL",
            event_date=date(2024, 11, 5),
            event_start=datetime(2024, 11, 5, 6, 0),
            event_end=datetime(2024, 11, 5, 20, 0),
        )
        assert schema.event_type == "GENERAL"
        assert schema.notes == ""

    def test_court_ruling_event(self):
        schema = RaceEventSchema(
            race_id=1,
            event_type="COURT_RULING",
            event_date=date(2024, 9, 15),
            external_event_id=42,
            notes="District map invalidated by state supreme court",
        )
        assert schema.external_event_id == 42


# ---------------------------------------------------------------------------
# ReturnSnapshotSchema
# ---------------------------------------------------------------------------

class TestReturnSnapshotSchema:

    def test_partial_reporting(self):
        schema = ReturnSnapshotSchema(
            race_id=1,
            timestamp=datetime(2024, 11, 5, 22, 30),
            source="ap",
            precincts_reporting=1200,
            total_precincts=2400,
            pct_reporting=50.0,
            total_ballots_counted=150000,
            results={
                "candidate_a": {"votes": 80000, "pct": 53.3, "party": "DEM"},
                "candidate_b": {"votes": 70000, "pct": 46.7, "party": "REP"},
            },
        )
        assert schema.pct_reporting == 50.0
        assert schema.is_final is False
        assert len(schema.results) == 2

    def test_final_result(self):
        schema = ReturnSnapshotSchema(
            race_id=1,
            timestamp=datetime(2024, 12, 10, 12, 0),
            source="state_sos",
            pct_reporting=100.0,
            is_final=True,
            results={"candidate_a": {"votes": 160000, "pct": 53.0, "party": "DEM"}},
        )
        assert schema.is_final is True
        assert schema.source == "state_sos"

    def test_pct_reporting_bounds(self):
        with pytest.raises(Exception):
            ReturnSnapshotSchema(
                race_id=1,
                timestamp=datetime(2024, 11, 5, 22, 0),
                source="ap",
                pct_reporting=101.0,
            )

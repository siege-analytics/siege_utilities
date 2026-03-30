"""ORM-level tests for temporal political models (Phase A/B/C).

These tests exercise the actual Django models against a PostGIS database,
verifying CRUD operations, FK relationships, constraints, and model methods.

Requires: PostGIS database (see scripts/setup_test_db.sh)
    export SIEGE_TEST_DB_PASSWORD=postgres
    pytest tests/test_django_temporal_models_orm.py -v
"""

from datetime import date, datetime, timezone

import pytest

try:
    from django.contrib.gis.geos import (
        GeometryCollection,
        MultiPolygon,
        Point,
        Polygon,
    )
    from django.db import IntegrityError

    HAS_GDAL = True
except Exception:
    HAS_GDAL = False

pytestmark = [
    pytest.mark.django_db,
    pytest.mark.requires_gdal,
    pytest.mark.skipif(not HAS_GDAL, reason="GDAL/PostGIS not available"),
]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_polygon():
    """Simple test polygon."""
    return MultiPolygon(Polygon(((0, 0), (1, 0), (1, 1), (0, 1), (0, 0))))


@pytest.fixture
def state(db):
    from siege_utilities.geo.django.models import State

    return State.objects.create(
        geoid="06",
        name="California",
        vintage_year=2020,
        geometry=_make_polygon(),
        state_fips="06",
    )


@pytest.fixture
def state_tx(db):
    from siege_utilities.geo.django.models import State

    return State.objects.create(
        geoid="48",
        name="Texas",
        vintage_year=2020,
        geometry=_make_polygon(),
        state_fips="48",
    )


@pytest.fixture
def term(db):
    from siege_utilities.geo.django.models import CongressionalTerm

    return CongressionalTerm.objects.create(
        congress_number=119,
        start_date=date(2025, 1, 3),
        end_date=date(2027, 1, 3),
        election_year=2024,
        is_presidential=True,
        senate_classes_up=[2],
    )


@pytest.fixture
def seat(db, state):
    from siege_utilities.geo.django.models import Seat

    return Seat.objects.create(
        office="US_HOUSE",
        state=state,
        district_label="12",
    )


@pytest.fixture
def race(db, seat, term):
    from siege_utilities.geo.django.models import Race

    return Race.objects.create(
        seat=seat,
        congressional_term=term,
    )


# ---------------------------------------------------------------------------
# CongressionalTerm
# ---------------------------------------------------------------------------

class TestCongressionalTermORM:

    def test_create_and_read(self, term):
        from siege_utilities.geo.django.models import CongressionalTerm

        obj = CongressionalTerm.objects.get(congress_number=119)
        assert obj.election_year == 2024
        assert obj.is_presidential is True
        assert obj.senate_classes_up == [2]

    def test_str_ordinal(self, term):
        assert "119th" in str(term)
        assert "2024" in str(term)

    def test_ordinal_edge_cases(self):
        from siege_utilities.geo.django.models import CongressionalTerm

        assert CongressionalTerm._ordinal(1) == "1st"
        assert CongressionalTerm._ordinal(2) == "2nd"
        assert CongressionalTerm._ordinal(3) == "3rd"
        assert CongressionalTerm._ordinal(11) == "11th"
        assert CongressionalTerm._ordinal(12) == "12th"
        assert CongressionalTerm._ordinal(13) == "13th"
        assert CongressionalTerm._ordinal(21) == "21st"
        assert CongressionalTerm._ordinal(22) == "22nd"
        assert CongressionalTerm._ordinal(23) == "23rd"
        assert CongressionalTerm._ordinal(111) == "111th"

    def test_unique_congress_number(self, term):
        from siege_utilities.geo.django.models import CongressionalTerm

        with pytest.raises(IntegrityError):
            CongressionalTerm.objects.create(
                congress_number=119,
                start_date=date(2025, 1, 3),
                end_date=date(2027, 1, 3),
                election_year=2024,
            )

    def test_ordering(self, db):
        from siege_utilities.geo.django.models import CongressionalTerm

        CongressionalTerm.objects.create(
            congress_number=118, start_date=date(2023, 1, 3),
            end_date=date(2025, 1, 3), election_year=2022,
        )
        CongressionalTerm.objects.create(
            congress_number=120, start_date=date(2027, 1, 3),
            end_date=date(2029, 1, 3), election_year=2026,
        )
        CongressionalTerm.objects.create(
            congress_number=119, start_date=date(2025, 1, 3),
            end_date=date(2027, 1, 3), election_year=2024,
        )
        nums = list(
            CongressionalTerm.objects.values_list("congress_number", flat=True)
        )
        assert nums == [118, 119, 120]


# ---------------------------------------------------------------------------
# Seat
# ---------------------------------------------------------------------------

class TestSeatORM:

    def test_create_house_seat(self, seat):
        assert seat.office == "US_HOUSE"
        assert seat.state.geoid == "06"
        assert seat.district_label == "12"
        assert seat.is_active is True

    def test_create_senate_seat(self, db, state):
        from siege_utilities.geo.django.models import Seat

        s = Seat.objects.create(
            office="US_SENATE", state=state, senate_class=2,
        )
        assert s.senate_class == 2
        assert s.district_label == ""

    def test_create_president_no_state(self, db):
        from siege_utilities.geo.django.models import Seat

        s = Seat.objects.create(office="PRESIDENT")
        assert s.state is None

    def test_str_output(self, seat):
        s = str(seat)
        assert "U.S. House" in s

    def test_unique_together(self, seat, state):
        from siege_utilities.geo.django.models import Seat

        with pytest.raises(IntegrityError):
            Seat.objects.create(
                office="US_HOUSE", state=state, district_label="12",
            )


# ---------------------------------------------------------------------------
# StateElectionCalendar
# ---------------------------------------------------------------------------

class TestStateElectionCalendarORM:

    def test_create_calendar(self, db, state, term):
        from siege_utilities.geo.django.models import StateElectionCalendar

        cal = StateElectionCalendar.objects.create(
            state=state,
            congressional_term=term,
            primary_date=date(2024, 3, 5),
            primary_type="top_two",
            general_date=date(2024, 11, 5),
        )
        assert cal.primary_type == "top_two"
        assert cal.general_date == date(2024, 11, 5)

    def test_str_output(self, db, state, term):
        from siege_utilities.geo.django.models import StateElectionCalendar

        cal = StateElectionCalendar.objects.create(
            state=state, congressional_term=term,
        )
        s = str(cal)
        assert "California" in s or "06" in s

    def test_unique_together(self, db, state, term):
        from siege_utilities.geo.django.models import StateElectionCalendar

        StateElectionCalendar.objects.create(
            state=state, congressional_term=term,
        )
        with pytest.raises(IntegrityError):
            StateElectionCalendar.objects.create(
                state=state, congressional_term=term,
            )


# ---------------------------------------------------------------------------
# Race
# ---------------------------------------------------------------------------

class TestRaceORM:

    def test_create_regular_race(self, race):
        assert race.is_special is False
        assert race.cause_of_special == ""

    def test_create_special_election(self, db, seat, term):
        from siege_utilities.geo.django.models import Race

        r = Race.objects.create(
            seat=seat, congressional_term=term,
            is_special=True, cause_of_special="resignation",
        )
        assert r.is_special is True
        assert r.cause_of_special == "resignation"

    def test_fk_relationships(self, race):
        assert race.seat.office == "US_HOUSE"
        assert race.congressional_term.congress_number == 119

    def test_str_output(self, race):
        s = str(race)
        assert "119th" in s


# ---------------------------------------------------------------------------
# SpatioTemporalEvent
# ---------------------------------------------------------------------------

class TestSpatioTemporalEventORM:

    def test_create_with_geometry(self, db):
        from siege_utilities.geo.django.models import SpatioTemporalEvent

        gc = GeometryCollection(Point(0, 0))
        evt = SpatioTemporalEvent.objects.create(
            feature_id="hurricane-helene-2024",
            name="Hurricane Helene",
            vintage_year=2024,
            event_start=datetime(2024, 9, 24, tzinfo=timezone.utc),
            event_end=datetime(2024, 9, 28, tzinfo=timezone.utc),
            event_category="NATURAL_DISASTER",
            geometry=gc,
        )
        assert evt.event_category == "NATURAL_DISASTER"
        assert evt.geometry is not None

    def test_create_without_geometry(self, db):
        from siege_utilities.geo.django.models import SpatioTemporalEvent

        evt = SpatioTemporalEvent.objects.create(
            feature_id="court-ruling-2019",
            name="Rucho v. Common Cause",
            vintage_year=2019,
            event_start=datetime(2019, 6, 27, tzinfo=timezone.utc),
            event_category="COURT_RULING",
        )
        assert evt.geometry is None

    def test_m2m_affected_boundaries(self, db, state, state_tx):
        from siege_utilities.geo.django.models import SpatioTemporalEvent

        evt = SpatioTemporalEvent.objects.create(
            feature_id="multi-state-event",
            name="Multi-State Event",
            vintage_year=2024,
            event_start=datetime(2024, 1, 1, tzinfo=timezone.utc),
            event_category="OTHER",
        )
        evt.affected_boundaries.add(state, state_tx)
        assert evt.affected_boundaries.count() == 2

    def test_is_current_property(self, db):
        from siege_utilities.geo.django.models import SpatioTemporalEvent

        evt = SpatioTemporalEvent.objects.create(
            feature_id="current-event",
            name="Current Event",
            vintage_year=2024,
            event_start=datetime(2024, 1, 1, tzinfo=timezone.utc),
            event_category="OTHER",
        )
        assert evt.is_current is True  # valid_to is None


# ---------------------------------------------------------------------------
# RaceEvent
# ---------------------------------------------------------------------------

class TestRaceEventORM:

    def test_create_general_election(self, db, race):
        from siege_utilities.geo.django.models import RaceEvent

        evt = RaceEvent.objects.create(
            race=race,
            event_type="GENERAL",
            event_date=date(2024, 11, 5),
        )
        assert evt.event_type == "GENERAL"
        assert evt.external_event is None

    def test_with_external_event(self, db, race):
        from siege_utilities.geo.django.models import RaceEvent, SpatioTemporalEvent

        ext = SpatioTemporalEvent.objects.create(
            feature_id="court-order",
            name="Map Invalidation",
            vintage_year=2024,
            event_start=datetime(2024, 9, 1, tzinfo=timezone.utc),
            event_category="COURT_RULING",
        )
        evt = RaceEvent.objects.create(
            race=race,
            event_type="COURT_RULING",
            event_date=date(2024, 9, 1),
            external_event=ext,
        )
        assert evt.external_event.name == "Map Invalidation"

    def test_ordering(self, db, race):
        from siege_utilities.geo.django.models import RaceEvent

        RaceEvent.objects.create(
            race=race, event_type="GENERAL", event_date=date(2024, 11, 5),
        )
        RaceEvent.objects.create(
            race=race, event_type="PRIMARY", event_date=date(2024, 3, 5),
        )
        dates = list(
            RaceEvent.objects.values_list("event_date", flat=True)
        )
        assert dates == [date(2024, 3, 5), date(2024, 11, 5)]


# ---------------------------------------------------------------------------
# ReturnSnapshot
# ---------------------------------------------------------------------------

class TestReturnSnapshotORM:

    def test_progressive_reporting(self, db, race):
        from siege_utilities.geo.django.models import ReturnSnapshot

        snap = ReturnSnapshot.objects.create(
            race=race,
            timestamp=datetime(2024, 11, 5, 22, 30, tzinfo=timezone.utc),
            source="ap",
            pct_reporting=50.0,
            results={
                "candidate_a": {"votes": 80000, "pct": 53.3, "party": "DEM"},
            },
        )
        assert snap.is_final is False
        assert snap.results["candidate_a"]["votes"] == 80000

    def test_final_result(self, db, race):
        from siege_utilities.geo.django.models import ReturnSnapshot

        snap = ReturnSnapshot.objects.create(
            race=race,
            timestamp=datetime(2024, 12, 10, 12, 0, tzinfo=timezone.utc),
            source="state_sos",
            pct_reporting=100.0,
            is_final=True,
            results={"winner": {"votes": 160000}},
        )
        assert snap.is_final is True

    def test_str_final_vs_partial(self, db, race):
        from siege_utilities.geo.django.models import ReturnSnapshot

        partial = ReturnSnapshot.objects.create(
            race=race,
            timestamp=datetime(2024, 11, 5, 22, 0, tzinfo=timezone.utc),
            source="ap",
            pct_reporting=50.0,
        )
        final = ReturnSnapshot.objects.create(
            race=race,
            timestamp=datetime(2024, 12, 10, tzinfo=timezone.utc),
            source="state_sos",
            is_final=True,
        )
        assert "FINAL" in str(final)
        assert "50.0%" in str(partial)


# ---------------------------------------------------------------------------
# PlanDistrictAssignment (Phase C — GenericFK)
# ---------------------------------------------------------------------------

class TestPlanDistrictAssignmentORM:

    def test_create_with_generic_fk(self, db, state, seat):
        from django.contrib.contenttypes.models import ContentType

        from siege_utilities.geo.django.models import (
            CongressionalDistrict,
            PlanDistrictAssignment,
            RedistrictingPlan,
        )

        plan = RedistrictingPlan.objects.create(
            state=state, state_fips="06", chamber="congress",
            cycle_year=2020, plan_name="CA_2020_enacted", num_districts=52,
        )
        cd = CongressionalDistrict.objects.create(
            geoid="0612", name="CA-12", vintage_year=2020,
            geometry=_make_polygon(), state_fips="06",
        )
        ct = ContentType.objects.get_for_model(CongressionalDistrict)

        assignment = PlanDistrictAssignment.objects.create(
            plan=plan,
            seat=seat,
            boundary_content_type=ct,
            boundary_object_id=cd.pk,
        )
        assert assignment.boundary == cd
        assert str(assignment) == f"{plan} → {seat}"

    def test_unique_together_plan_seat(self, db, state, seat):
        from siege_utilities.geo.django.models import (
            PlanDistrictAssignment,
            RedistrictingPlan,
        )

        plan = RedistrictingPlan.objects.create(
            state=state, state_fips="06", chamber="congress",
            cycle_year=2020, plan_name="CA_2020_v2", num_districts=52,
        )
        PlanDistrictAssignment.objects.create(
            plan=plan, seat=seat,
            boundary_content_type_id=1, boundary_object_id=1,
        )
        with pytest.raises(IntegrityError):
            PlanDistrictAssignment.objects.create(
                plan=plan, seat=seat,
                boundary_content_type_id=1, boundary_object_id=2,
            )

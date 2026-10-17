"""GEOID identity and legacy migration regressions for #1560 (test-postgis)."""

import os

import pytest

# Collection also runs in the no-GDAL lane. Gate before importing GeoDjango;
# an opted-in PostGIS lane must still fail if its GIS dependencies are missing.
if os.environ.get("SIEGE_TEST_POSTGIS") != "1":
    pytest.skip(
        "Set SIEGE_TEST_POSTGIS=1 and SIEGE_TEST_DB_* for live PostGIS tests.",
        allow_module_level=True,
    )

from django.contrib.contenttypes.models import ContentType
from django.contrib.gis.geos import MultiPolygon, Polygon
from django.db import IntegrityError, transaction

from siege_utilities.geo.django.managers import BoundaryQuerySet
from siege_utilities.geo.django.models import County, ZCTA
from siege_utilities.geo.django.models.demographics import DemographicSnapshot

pytestmark = pytest.mark.postgis


@pytest.fixture
def colliding_boundaries(db):
    geometry = MultiPolygon(Polygon.from_bbox((-119, 33, -118, 34)), srid=4326)
    county = County.objects.create(
        pk=11, geoid="06037", state_fips="06", county_fips="037",
        vintage_year=2020, geometry=geometry,
    )
    County.objects.create(
        pk=6037, geoid="13001", state_fips="13", county_fips="001",
        vintage_year=2020, geometry=geometry,
    )
    zcta = ZCTA.objects.create(
        pk=12, geoid="06037", zcta5="06037", vintage_year=2020, geometry=geometry,
    )
    for boundary, population in ((county, 10_000_000), (zcta, 20_000)):
        DemographicSnapshot.objects.create(
            content_type=ContentType.objects.get_for_model(boundary),
            object_id=boundary.geoid, dataset="acs5", year=2022,
            total_population=population,
        )
    return county, zcta


def test_population_does_not_cross_geography(colliding_boundaries):
    """Runs unchanged on v4.0.0: equal GEOIDs must have distinct populations."""
    county, zcta = colliding_boundaries
    assert BoundaryQuerySet(County).filter(pk=county.pk).by_population(year=2022).get().population == 10_000_000
    assert BoundaryQuerySet(ZCTA).filter(pk=zcta.pk).by_population(year=2022).get().population == 20_000


def test_content_object_resolves_geoid_not_integer_pk(colliding_boundaries):
    """Runs unchanged on v4.0.0: County(pk=6037) is deliberately the wrong county."""
    for boundary in colliding_boundaries:
        snapshot = DemographicSnapshot.objects.get(
            content_type=ContentType.objects.get_for_model(boundary),
            object_id="06037", year=2022, dataset="acs5",
        )
        assert snapshot.content_object == boundary


def test_population_dataset_latest_year_and_reverse_helper(colliding_boundaries):
    county, zcta = colliding_boundaries
    content_type = ContentType.objects.get_for_model(county)
    DemographicSnapshot.objects.create(
        content_type=content_type, object_id=county.geoid, dataset="dec_pl",
        year=2022, total_population=900,
    )
    latest = DemographicSnapshot.objects.create(
        content_type=content_type, geoid=county.geoid, dataset="acs5",
        year=2023, total_population=11_000_000,
    )
    counties = County.objects.filter(pk=county.pk)
    assert counties.by_population(year=2022).get().population == 10_000_000
    assert counties.by_population(year=2022, dataset="dec_pl").get().population == 900
    assert counties.by_population().get().population == 11_000_000
    assert counties.by_population(year=1990).get().population is None
    assert County.objects.by_population().get(pk=county.pk).population == 11_000_000
    assert list(counties.snapshots(dataset="acs5", year=2023)) == [latest]
    assert counties.snapshots().count() == 3
    assert ZCTA.objects.snapshots().get().total_population == 20_000
    assert ZCTA.objects.filter(pk=zcta.pk).by_population(dataset="dec_pl").get().population is None


@pytest.mark.parametrize("series", [False, True], ids=["snapshot", "series"])
def test_geoid_create_shim_vintages_and_unique_constraint(colliding_boundaries, series):
    from siege_utilities.geo.django.models.demographics import DemographicTimeSeries

    county, _ = colliding_boundaries
    model = DemographicTimeSeries if series else DemographicSnapshot
    kwargs = dict(variable_code="B01001_001E", start_year=2020, end_year=2022,
                  years=[2020, 2022], values=[10, 20]) if series else dict(year=2021)
    with pytest.warns(DeprecationWarning, match="removed in v4.2.0"):
        row = model.objects.create(content_object=county, dataset="acs5", **kwargs)
    row.refresh_from_db()
    assert row.object_id == row.geoid == county.geoid
    assert row.get_boundary() == county
    with pytest.warns(DeprecationWarning, match="removed in v4.2.0"):
        assert row.content_object == county
    newer = County.objects.create(
        geoid=county.geoid, state_fips="06", county_fips="037",
        vintage_year=2024, geometry=county.geometry,
    )
    assert row.get_boundary() == newer
    assert row.get_boundary(vintage_year=2020) == county
    assert row.get_boundary(vintage_year=1990) is None
    with pytest.raises(IntegrityError), transaction.atomic():
        model.objects.create(content_type=row.content_type, geoid=row.geoid, dataset="acs5", **kwargs)
    row.geoid = "99999"
    assert row.get_boundary() is None


def test_plan_assignment_accepts_big_boundary_pk(colliding_boundaries):
    from siege_utilities.geo.django.models.redistricting import PlanDistrictAssignment, RedistrictingPlan
    from siege_utilities.geo.django.models import Seat, State

    county, _ = colliding_boundaries
    boundary = County.objects.create(
        pk=2**31 + 5, geoid="06001", state_fips="06", county_fips="001",
        vintage_year=2020, geometry=county.geometry,
    )
    plan = RedistrictingPlan.objects.create(
        plan_name="Big PK plan", state_fips="06", chamber="congress", cycle_year=2020,
        num_districts=1,
    )
    state = State.objects.create(geoid="06", state_fips="06", vintage_year=2020, geometry=county.geometry)
    seat = Seat.objects.create(state=state, office="US_HOUSE", district_label="01")
    assignment = PlanDistrictAssignment.objects.create(plan=plan, seat=seat, boundary=boundary)
    assignment.refresh_from_db()
    assert assignment.boundary_object_id == boundary.pk
    assert assignment.boundary == boundary

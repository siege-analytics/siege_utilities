"""Behavior regressions for #1570 (writing-tests:1 retroactive-fix corollary).

Replace signature/source inspection with public manager calls, PostGIS results,
and JSON round trips per writing-tests:6. Live tests run in test-postgis; opt in
locally with SIEGE_TEST_POSTGIS=1 and the SIEGE_TEST_DB_* settings.
"""

import json
import os

import pytest
from django.apps import apps
from django.contrib.gis.geos import MultiPolygon, Point, Polygon

from siege_utilities.geo.django.managers import BoundaryManager, BoundaryQuerySet
from siege_utilities.geo.django.models import County, Tract
from siege_utilities.geo.django.models.base import TemporalBoundary
from siege_utilities.geo.django.models.redistricting import (
    RedistrictingPlan,
    RedistrictingPlanManager,
)
from siege_utilities.geo.django.serializers.boundary_serializers import (
    BoundaryWithDemographicsSerializer,
)


@pytest.mark.parametrize(
    "model",
    [
        model for model in apps.get_app_config("siege_geo").get_models()
        if issubclass(model, TemporalBoundary)
    ],
    ids=lambda model: model.__name__,
)
def test_boundary_models_inherit_spatial_queryset(model):
    """#1570; writing-tests:1 retroactive-fix corollary: test the attached API."""
    queryset = model.objects.for_year(2020)
    assert isinstance(model.objects, BoundaryManager)
    assert isinstance(queryset, BoundaryQuerySet)
    assert queryset.model is model
    assert model.objects.use_in_migrations is False


def test_redistricting_plan_keeps_its_own_manager():
    """#1570: the attach point must leave non-boundary plan management intact."""
    assert isinstance(RedistrictingPlan.objects, RedistrictingPlanManager)
    assert not isinstance(RedistrictingPlan.objects, BoundaryManager)


def test_demographics_serializer_emits_geometry_object():
    """#1570; writing-tests:1 retroactive-fix corollary: assert serialized data."""
    county = County(
        geoid="06001", name="Containing", vintage_year=2020,
        geometry=MultiPolygon(Polygon.from_bbox((-118.21, 33.99, -118.19, 34.01)), srid=4326),
    )
    serializer = BoundaryWithDemographicsSerializer(county)
    geometry = json.loads(json.dumps(serializer.data))["geometry"]
    assert isinstance(geometry, dict)
    assert geometry == json.loads(county.geometry.json)
    assert serializer.get_geometry(county) == geometry


@pytest.fixture
def boundary_rows(db):
    """Use pytest-django's isolated test DB, only in the live PostGIS lane."""
    for geoid, name, west, east in (
        ("06001", "Containing", -118.21, -118.19),
        # About 46 km east: inside 50 km but outside a 50000/111000 degree radius.
        ("06003", "Nearby", -117.70, -117.69),
        ("06005", "Outside", -117.50, -117.49),
    ):
        County.objects.create(
            geoid=geoid, name=name, state_fips="06", county_fips=geoid[2:],
            vintage_year=2020, area_land=100, area_water=0,
            geometry=MultiPolygon(Polygon.from_bbox((west, 33.99, east, 34.01)), srid=4326),
        )


@pytest.mark.postgis
@pytest.mark.skipif(
    os.environ.get("SIEGE_TEST_POSTGIS") != "1",
    reason=(
        "Set SIEGE_TEST_POSTGIS=1 and SIEGE_TEST_DB_NAME/USER/PASSWORD/HOST/PORT "
        "for a PostGIS test database; see docs/testing/postgis.md."
    ),
)
@pytest.mark.usefixtures("boundary_rows")
class TestBoundaryManagerPostGIS:
    """#1570: actual database results replace the old inspection assertions."""

    @pytest.mark.parametrize(
        "radius,expected",
        [
            (0, ["06001"]),
            (50000, ["06001", "06003"]),
            (70000, ["06001", "06003", "06005"]),
        ],
    )
    def test_within_distance_returns_boundaries_in_meters(self, radius, expected):
        """#1570; writing-tests:1 retroactive-fix corollary: execute dwithin."""
        queryset = County.objects.within_distance(Point(-118.2, 34.0, srid=4326), radius)
        queryset.query.sql_with_params()
        assert list(queryset.order_by("geoid").values_list("geoid", flat=True)) == expected

    @pytest.mark.parametrize("input_srid", [None, 4326, 3857])
    def test_nearest_limits_meters_and_honors_tuple_srid(self, input_srid):
        """#1570; writing-tests:1 retroactive-fix corollary: call the SRID API."""
        point = Point(-118.2, 34.0, srid=4326)
        kwargs = {}
        if input_srid is not None:
            point.transform(input_srid)
            point = point.coords
            kwargs["srid"] = input_srid
        queryset = County.objects.nearest(point, max_distance_m=50000, **kwargs)
        queryset.query.sql_with_params()
        counties = list(queryset)
        assert [county.geoid for county in counties] == ["06001", "06003"]
        assert counties[0].distance.m == pytest.approx(0)
        assert 45000 < counties[1].distance.m < 48000

    def test_nearest_without_limit_returns_all_by_distance(self):
        """#1570; writing-tests:1 retroactive-fix corollary: verify the default."""
        counties = list(County.objects.nearest((-118.2, 34.0)))
        assert [county.geoid for county in counties] == ["06001", "06003", "06005"]
        assert counties[2].distance.m > 60000

    @pytest.mark.parametrize("input_srid", [None, 4326, 3857])
    def test_containing_point_filters_geometry_and_year(self, input_srid):
        """#1570; writing-tests:1 retroactive-fix corollary: execute containment."""
        county = County.objects.get(geoid="06001")
        tract = Tract.objects.create(
            geoid="06001000100", name="Containing tract", state_fips="06",
            county_fips="001", tract_code="000100", vintage_year=2020,
            geometry=county.geometry,
        )
        point = Point(-118.2, 34.0, srid=4326)
        kwargs = {}
        if input_srid is not None:
            point.transform(input_srid)
            point = point.coords
            kwargs["srid"] = input_srid
        assert list(Tract.objects.containing_point(point, **kwargs).for_year(2020)) == [tract]
        assert not Tract.objects.containing_point(point, **kwargs).for_year(2010).exists()

    def test_state_and_year_filters_chain_on_manager(self):
        """#1570: the README's for_state/for_year chain selects both fields."""
        geometry = County.objects.get(geoid="06001").geometry
        County.objects.create(geoid="06001", state_fips="06", vintage_year=2010, geometry=geometry)
        County.objects.create(geoid="32001", state_fips="32", vintage_year=2020, geometry=geometry)
        queryset = County.objects.for_state("06").for_year(2020)
        assert list(queryset.order_by("geoid").values_list("geoid", flat=True)) == [
            "06001", "06003", "06005",
        ]

    def test_geojson_round_trip_contains_geometry_object(self):
        """#1570; writing-tests:1 retroactive-fix corollary: assert GeoJSON data."""
        queryset = County.objects.filter(geoid="06001")
        collection = json.loads(json.dumps(queryset.geojson()))
        assert collection["type"] == "FeatureCollection"
        assert len(collection["features"]) == 1
        feature = collection["features"][0]
        assert feature["type"] == "Feature"
        assert isinstance(feature["geometry"], dict)
        assert feature["geometry"] == json.loads(queryset.get().geometry.json)
        assert feature["properties"]["geoid"] == "06001"
        serialized = json.loads(json.dumps(BoundaryWithDemographicsSerializer(queryset.get()).data))
        assert isinstance(serialized["geometry"], dict)
        assert serialized["geometry"] == feature["geometry"]

    @pytest.mark.parametrize("input_srid", [None, 3857])
    def test_bulk_create_geodataframe_preserves_geometry_with_srid(self, input_srid):
        """#1570; writing-tests:1 retroactive-fix corollary: exercise bulk SRID."""
        import geopandas as gpd
        from shapely.geometry import box

        frame = gpd.GeoDataFrame(
            {"GEOID": ["06099"], "NAME": ["Imported"]},
            geometry=[box(-118.21, 33.99, -118.19, 34.01)], crs=4326,
        )
        kwargs = {}
        if input_srid is not None:
            frame = frame.to_crs(input_srid)
            kwargs["srid"] = input_srid
        created = County.objects.bulk_create_from_geodataframe(frame, 2020, **kwargs)
        assert len(created) == 1
        county = County.objects.get(geoid="06099", vintage_year=2020)
        assert county.state_fips == "06"
        assert county.county_fips == "099"
        assert county.geometry.srid == 4326
        assert county.geometry.extent == pytest.approx((-118.21, 33.99, -118.19, 34.01))

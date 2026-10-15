"""Regression tests for boundary downloads and real parent FKs (#1620).

ORM tests require PostGIS; configure SIEGE_TEST_DB_* as documented in
tests/django_project/settings.py. Only the Census fetch is mocked.
"""

import os
from unittest.mock import patch

import geopandas as gpd
import pytest
from shapely.geometry import Polygon

from django.core.exceptions import ImproperlyConfigured

try:
    from django.contrib.gis.geos import GEOSGeometry, MultiPolygon
except (ImportError, ImproperlyConfigured, OSError):
    pytest.skip(
        "Install GDAL/GEOS and configure GDAL_LIBRARY_PATH/GEOS_LIBRARY_PATH "
        "to run the boundary population regressions",
        allow_module_level=True,
    )

from siege_utilities.geo.boundary_result import (
    BoundaryDownloadError,
    BoundaryFetchResult,
    BoundaryRetrievalError,
)
from siege_utilities.geo.django import models
from siege_utilities.geo.django.management.commands.populate_boundaries import Command
from siege_utilities.geo.django.services.population_service import (
    BoundaryPopulationService,
)


pytestmark = pytest.mark.requires_gdal


POSTGIS_REMEDIATION = (
    "Set SIEGE_TEST_POSTGIS=1 with SIEGE_TEST_DB_HOST/PORT/NAME/USER/PASSWORD "
    "pointing to a reachable PostGIS test database, then run "
    "pytest tests/test_boundary_population_service.py -m postgis --no-cov."
)


def live_postgis(test):
    """Route real ORM tests to the service lane; keep pure tests generic."""
    test = pytest.mark.postgis(test)
    return pytest.mark.skipif(
        os.environ.get("SIEGE_TEST_POSTGIS") != "1", reason=POSTGIS_REMEDIATION
    )(test)


@pytest.fixture
def county_gdf():
    return gpd.GeoDataFrame(
        {
            # CensusDataSource._standardize_census_columns lowercases TIGER names.
            "geoid": ["06037", "06059"],
            "name": ["Los Angeles", "Orange"],
            "statefp": ["06", "06"],
            "countyfp": ["037", "059"],
            "aland": [100, 200],
            "awater": [10, 20],
        },
        geometry=[
            Polygon([(0, 0), (1, 0), (1, 1), (0, 0)]),
            Polygon([(1, 1), (2, 1), (2, 2), (1, 1)]),
        ],
        crs="EPSG:4326",
    )


@pytest.fixture
def fetch():
    # Autospec enforces the public API signature; use its real result type.
    with patch("siege_utilities.geo.fetch_geographic_boundaries", autospec=True) as mock:
        yield mock


@live_postgis
@pytest.mark.django_db
@pytest.mark.parametrize("column_case", ["lower", "upper"])
def test_populate_county_creates_two_rows_from_fetch_result(fetch, county_gdf, column_case):
    if column_case == "upper":
        county_gdf = county_gdf.rename(
            columns={column: column.upper() for column in county_gdf if column != "geometry"}
        )
    fetch.return_value = BoundaryFetchResult.ok(county_gdf)

    result = BoundaryPopulationService().populate("county", 2020, "06")

    assert result.success, result.errors
    assert result.records_created == 2
    assert result.records_updated == result.records_skipped == 0
    assert list(models.County.objects.values_list("geoid", "name")) == [
        ("06037", "Los Angeles"), ("06059", "Orange")
    ]
    county = models.County.objects.get(geoid="06037", vintage_year=2020)
    assert (county.state_fips, county.county_fips) == ("06", "037")
    assert county.geometry.geom_type == "MultiPolygon"
    fetch.assert_called_once_with(year=2020, geographic_level="county", state_fips="06")


@pytest.mark.parametrize(
    "geography_type,level",
    [
        ("state", "state"), ("county", "county"), ("tract", "tract"),
        ("blockgroup", "block_group"), ("block", "block"), ("place", "place"),
        ("zcta", "zcta"), ("cd", "cd"), ("sldu", "sldu"), ("sldl", "sldl"),
        ("vtd", "vtd"), ("cbsa", "cbsa"), ("urbanarea", "uac"),
        ("elsd", "elsd"), ("scsd", "scsd"), ("unsd", "unsd"),
    ],
)
def test_download_maps_advertised_type_to_fetch_level(
    fetch, county_gdf, geography_type, level
):
    fetch.return_value = BoundaryFetchResult.ok(county_gdf)

    actual = BoundaryPopulationService()._download_boundaries(geography_type, 2020, "06")

    assert actual is county_gdf
    fetch.assert_called_once_with(year=2020, geographic_level=level, state_fips="06")


def test_every_command_type_has_a_fetch_level():
    assert set(Command.GEOGRAPHY_TYPES) == set(BoundaryPopulationService.GEOGRAPHIC_LEVELS)


@live_postgis
@pytest.mark.django_db
def test_populate_raises_download_failure_with_diagnostics(fetch):
    fetch.return_value = BoundaryFetchResult.fail(
        error_code="DOWNLOAD_FAILED",
        error_stage="download",
        message="Census download timed out",
        context={"year": 2020, "state_fips": "06", "attempts": 3},
    )

    with pytest.raises(BoundaryDownloadError, match="Census download timed out") as exc:
        BoundaryPopulationService().populate("county", 2020, "06")

    assert exc.value.stage == "download"
    assert exc.value.context == {"year": 2020, "state_fips": "06", "attempts": 3}
    assert models.County.objects.count() == 0


@live_postgis
@pytest.mark.django_db
@pytest.mark.parametrize("missing", ["result", "geodataframe", "empty"])
def test_populate_raises_on_missing_boundaries_before_normalizing(fetch, county_gdf, missing):
    if missing == "result":
        fetch.return_value = None
    elif missing == "geodataframe":
        fetch.return_value = BoundaryFetchResult(success=True, geodataframe=None)
    else:
        fetch.return_value = BoundaryFetchResult.ok(county_gdf.iloc[:0])
    service = BoundaryPopulationService()

    with patch.object(service, "_normalize_geodataframe", autospec=True) as normalize:
        with pytest.raises(BoundaryRetrievalError, match="No boundar") as exc:
            service.populate("county", 2020, "06")

    normalize.assert_not_called()
    assert exc.value.context == {
        "year": 2020, "geographic_level": "county", "state_fips": "06"
    }
    assert models.County.objects.count() == 0


@live_postgis
@pytest.mark.django_db
@pytest.mark.parametrize("error_type", [TypeError, OSError, ImportError])
def test_populate_propagates_fetch_exceptions(fetch, error_type):
    fetch.side_effect = error_type("fetch failed")

    with pytest.raises(error_type, match="fetch failed"):
        BoundaryPopulationService().populate("county", 2020, "06")


@live_postgis
@pytest.mark.django_db
def test_populate_propagates_normalization_type_error(fetch, county_gdf):
    fetch.return_value = BoundaryFetchResult.ok(county_gdf)
    service = BoundaryPopulationService()

    with patch.object(service, "_normalize_geodataframe", side_effect=TypeError("bad schema")):
        with pytest.raises(TypeError, match="bad schema"):
            service.populate("county", 2020, "06")


@live_postgis
@pytest.mark.django_db
@pytest.mark.parametrize(
    "geography_type,message",
    [("unknown", "Unknown geography type"), ("precinct", "no Census fetch level")],
)
def test_populate_raises_for_unknown_or_unsupported_type(fetch, geography_type, message):
    with pytest.raises(ValueError, match=message):
        BoundaryPopulationService().populate(geography_type, 2020, "06")
    fetch.assert_not_called()


@pytest.fixture
def make_boundary(db, county_gdf):
    def create(model, geoid, year=2020, **kwargs):
        return model.objects.create(
            geoid=geoid,
            vintage_year=year,
            name=geoid,
            geometry=MultiPolygon(GEOSGeometry(county_gdf.geometry.iloc[0].wkt), srid=4326),
            **model.parse_geoid(geoid),
            **kwargs,
        )
    return create


@pytest.fixture
def parents(make_boundary):
    state = make_boundary(models.State, "06")
    county = make_boundary(models.County, "06037", state=state)
    tract = make_boundary(models.Tract, "06037101100", state=state, county=county)
    return {
        "state": state,
        "county": county,
        "tract": tract,
        "block_group_ref": make_boundary(
            models.BlockGroup, "060371011001", state=state, county=county, tract=tract
        ),
    }


@live_postgis
def test_link_block_parents_uses_real_fk_and_links_all_parents(make_boundary, parents):
    block = make_boundary(models.Block, "060371011001001")
    other_state = make_boundary(models.Block, "480371011001001")
    other_year = make_boundary(models.Block, "060371011001001", year=2021)
    service = BoundaryPopulationService()

    assert service.link_parent_relationships("block", 2020, "06") == 4

    block.refresh_from_db()
    for field, parent in parents.items():
        assert getattr(block, field) == parent
    for untouched in (other_state, other_year):
        untouched.refresh_from_db()
        assert untouched.state_id is None
        assert untouched.county_id is None
        assert untouched.tract_id is None
        assert untouched.block_group_ref_id is None
    assert service.link_parent_relationships("block", 2020, "06") == 0


@live_postgis
@pytest.mark.parametrize(
    "geography_type,model,geoid,parent_fields",
    [
        ("county", models.County, "06059", ("state",)),
        ("tract", models.Tract, "06037101200", ("state", "county")),
        ("blockgroup", models.BlockGroup, "060371011002", ("state", "county", "tract")),
        ("place", models.Place, "0644000", ("state",)),
        ("cd", models.CongressionalDistrict, "0614", ("state",)),
        ("sldu", models.StateLegislativeUpper, "06001", ("state",)),
        ("sldl", models.StateLegislativeLower, "06001", ("state",)),
        ("vtd", models.VTD, "06037001234", ("state", "county")),
        ("precinct", models.Precinct, "06037001234", ("state", "county")),
        ("elsd", models.SchoolDistrictElementary, "0600001", ("state",)),
        ("scsd", models.SchoolDistrictSecondary, "0600001", ("state",)),
        ("unsd", models.SchoolDistrictUnified, "0600001", ("state",)),
    ],
)
def test_link_all_fips_parents(
    make_boundary, parents, geography_type, model, geoid, parent_fields
):
    child = make_boundary(model, geoid)
    assert BoundaryPopulationService().link_parent_relationships(
        geography_type, 2020, "06"
    ) == len(parent_fields)
    child.refresh_from_db()
    for field in parent_fields:
        assert getattr(child, field) == parents[field]


@live_postgis
def test_link_missing_state_preserves_existing_county(make_boundary, parents):
    tract = make_boundary(models.Tract, "06037101200", county=parents["county"])

    assert BoundaryPopulationService().link_parent_relationships("TRACT", 2020, "06") == 1

    tract.refresh_from_db()
    assert tract.state == parents["state"]
    assert tract.county == parents["county"]


@live_postgis
def test_link_missing_parents_does_not_use_another_vintage(make_boundary):
    make_boundary(models.State, "06", year=2019)
    county = make_boundary(models.County, "06037")

    assert BoundaryPopulationService().link_parent_relationships("county", 2020, "06") == 0

    county.refresh_from_db()
    assert county.state is None


def test_link_parents_raises_for_unknown_type():
    with pytest.raises(ValueError, match="Unknown geography type: unknown"):
        BoundaryPopulationService().link_parent_relationships("unknown", 2020, "06")

"""PostGIS-lane twins for #1539 and #1550: the same assertions on real rows.

Only the Census/TIGER/NCES downloads are mocked. Inserts, unique conflicts
(``ON CONFLICT DO NOTHING``) and CHECK constraints are PostgreSQL's own.
Run with SIEGE_TEST_POSTGIS=1 and SIEGE_TEST_DB_* pointing at PostGIS.
"""

import io
import os
from unittest.mock import MagicMock, patch

import geopandas as gpd
import pandas as pd
import pytest
from django.core.exceptions import ImproperlyConfigured
from shapely.geometry import Polygon

try:
    from django.contrib.gis.geos import GEOSGeometry, MultiPolygon
except (ImportError, ImproperlyConfigured, OSError):
    pytest.skip(
        "Install GDAL/GEOS and configure GDAL_LIBRARY_PATH/GEOS_LIBRARY_PATH",
        allow_module_level=True,
    )

from siege_utilities.geo.django import models as gm
from siege_utilities.geo.django.services.demographic_service import (
    DemographicPopulationService,
)
from siege_utilities.geo.django.services.nces_service import NCESPopulationService
from siege_utilities.geo.django.services.population_service import (
    BoundaryPopulationService,
)

pytestmark = [
    pytest.mark.requires_gdal,
    pytest.mark.postgis,
    pytest.mark.django_db,
    pytest.mark.skipif(
        os.environ.get("SIEGE_TEST_POSTGIS") != "1",
        reason="Set SIEGE_TEST_POSTGIS=1 with SIEGE_TEST_DB_* for a live PostGIS database",
    ),
]

TRACT = "06001400100"
SQUARE = Polygon([(0, 0), (1, 0), (1, 1), (0, 0)])


def _demographics(df, group, **kw):
    svc = DemographicPopulationService(api_key="dummy")
    svc._client = MagicMock(fetch_data=MagicMock(return_value=df))
    return svc.populate("tract", 2022, "06", variable_group=group, **kw)


def test_second_group_merges_into_real_snapshot_without_update():
    first = _demographics(
        pd.DataFrame({"GEOID": [TRACT], "NAME": ["Tract 4001"], "B01001_001E": ["3000"]}),
        "total_population",
    )
    second = _demographics(
        pd.DataFrame({"GEOID": [TRACT], "NAME": ["Tract 4001"], "B19013_001E": ["85000"]}),
        "income",
    )
    assert (first.records_created, second.records_updated, second.records_skipped) == (1, 1, 0)
    snap = gm.DemographicSnapshot.objects.get(object_id=TRACT, year=2022, dataset="acs5")
    assert snap.values == {"B01001_001E": 3000, "B19013_001E": 85000}
    assert (snap.total_population, snap.median_household_income) == (3000, 85000)

    again = _demographics(
        pd.DataFrame({"GEOID": [TRACT], "B19013_001E": ["1"]}), "income"
    )
    assert (again.records_updated, again.records_skipped) == (0, 1)
    snap.refresh_from_db()
    assert snap.values["B19013_001E"] == 85000, "held keys change only with update_existing"


def test_sentinels_store_null_on_bulk_and_update_paths():
    created = _demographics(
        pd.DataFrame({"GEOID": [TRACT], "B01001_001E": ["0"], "B19013_001E": ["-666666666"]}),
        "income",
    )
    assert created.errors == [] and created.records_created == 1
    snap = gm.DemographicSnapshot.objects.get(object_id=TRACT)
    assert (snap.total_population, snap.median_household_income) == (0, None)

    updated = _demographics(
        pd.DataFrame({"GEOID": [TRACT], "B19013_001E": ["-999999999"]}),
        "income", update_existing=True,
    )
    assert updated.errors == [] and updated.records_updated == 1
    snap.refresh_from_db()
    assert snap.median_household_income is None
    assert snap.values["B19013_001E"] == -999999999


def test_boundary_and_demographic_bulk_paths_set_derived_fields_on_real_rows():
    gdf = gpd.GeoDataFrame(
        {"GEOID": ["06037", "06059"], "NAME": ["Los Angeles", "Orange"],
         "STATEFP": ["06", "06"], "COUNTYFP": ["037", "059"], "ALAND": [1, 2], "AWATER": [0, 0]},
        geometry=[SQUARE, SQUARE], crs="EPSG:4269",
    )
    with patch.object(BoundaryPopulationService, "_download_boundaries", return_value=gdf):
        BoundaryPopulationService().populate("county", 2020, state_fips="06")
    assert list(
        gm.County.objects.order_by("geoid").values_list("feature_id", "boundary_id", "source")
    ) == [("06037", "06037", "TIGER/Line"), ("06059", "06059", "TIGER/Line")]

    # A repeated GEOID in one response is dropped by ON CONFLICT DO NOTHING.
    df = pd.DataFrame({"GEOID": ["06037", "06059", "06059"],
                       "B01001_001E": ["1000", "2000", "2001"]})
    svc = DemographicPopulationService(api_key="dummy")
    svc._client = MagicMock(fetch_data=MagicMock(return_value=df))
    result = svc.populate("county", 2022, "06", variable_group="total_population")
    assert result.records_created == 2
    assert list(
        gm.DemographicSnapshot.objects.order_by("object_id").values_list(
            "object_id", "total_population"
        )
    ) == [("06037", 1000), ("06059", 2000)]


def test_nces_locale_bulk_path_on_real_rows():
    gdf = gpd.GeoDataFrame(
        {"locale_code": [11, 11, 12], "locale_category": ["City", "City", "City"]},
        geometry=[SQUARE] * 3, crs="EPSG:4269",
    )
    svc = NCESPopulationService()
    downloader = MagicMock(download_locale_boundaries=MagicMock(return_value=gdf))
    with patch.object(svc, "_get_downloader", return_value=downloader):
        result = svc.populate_locale_boundaries(year=2023)
    assert result.records_created == 2
    assert list(
        gm.NCESLocaleBoundary.objects.order_by("locale_code").values_list(
            "feature_id", "boundary_id"
        )
    ) == [("nces_locale_11_2023", "nces_locale_11_2023"),
          ("nces_locale_12_2023", "nces_locale_12_2023")]


def test_backfill_derived_fields_repairs_legacy_bulk_rows():
    from django.contrib.contenttypes.models import ContentType
    from django.core.management import call_command

    geometry = MultiPolygon(GEOSGeometry(SQUARE.wkt, srid=4326))
    # Rows as the pre-#1539 loaders wrote them: bulk_create, no save().
    gm.County.objects.bulk_create([
        gm.County(geoid="06037", name="Los Angeles", vintage_year=2020, geometry=geometry,
                  state_fips="06", county_fips="037"),
    ])
    gm.DemographicSnapshot.objects.bulk_create([
        gm.DemographicSnapshot(
            content_type=ContentType.objects.get_for_model(gm.County), object_id="06037",
            year=2022, dataset="acs5",
            values={"NAME": "Los Angeles County", "B01001_001E": 1000, "B19013_001E": -666666666},
        ),
    ])

    out = io.StringIO()
    call_command("backfill_derived_fields", "--dry-run", "--strip-name", stdout=out)
    assert "siege_geo.County: 1 rows would be updated" in out.getvalue()
    assert "siege_geo.DemographicSnapshot: 1 rows would be updated" in out.getvalue()
    assert gm.County.objects.get().feature_id == ""

    call_command("backfill_derived_fields", "--strip-name", stdout=io.StringIO())
    county = gm.County.objects.get()
    assert (county.feature_id, county.boundary_id, county.source) == ("06037", "06037", "TIGER/Line")
    snap = gm.DemographicSnapshot.objects.get()
    assert (snap.total_population, snap.median_household_income) == (1000, None)
    assert "NAME" not in snap.values

    out = io.StringIO()
    call_command("backfill_derived_fields", "--strip-name", stdout=out)
    assert "Done: updated 0 rows." in out.getvalue()

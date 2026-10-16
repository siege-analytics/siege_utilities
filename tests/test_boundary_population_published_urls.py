"""#1620 follow-up: every advertised --type must request a file Census publishes.

URL tests are pure: no database, no network. Command/ORM cases use PostGIS.
The TIGER directory listings below are copied from www2.census.gov/geo/tiger.
Every expected URL returned HTTP 200 on 2026-10-15.
"""

import os
from io import BytesIO, StringIO
from unittest.mock import patch

import geopandas as gpd
import pytest
from shapely.geometry import Polygon
from requests import Response
from django.core.management import call_command
from django.core.exceptions import ImproperlyConfigured

try:
    from django.contrib.gis.geos import GEOSGeometry  # noqa: F401
except (ImportError, ImproperlyConfigured, OSError):
    pytest.skip(
        "Install GDAL/GEOS and configure GDAL_LIBRARY_PATH/GEOS_LIBRARY_PATH "
        "to run the boundary population URL regressions",
        allow_module_level=True,
    )

from siege_utilities.geo import spatial_data as sd
from siege_utilities.geo.boundary_result import BoundaryUrlValidationError
from siege_utilities.geo.django.services.population_service import (
    BoundaryPopulationService,
)

T = "https://www2.census.gov/geo/tiger"
TIGER_DIRS = {
    2010: "BG CBSA CD COUNTY ELSD PLACE SCSD SLDL SLDU STATE TABBLOCK TRACT UA UNSD VTD ZCTA5",
    2019: "BG CBSA CD COUNTY ELSD PLACE SCSD SLDL SLDU STATE TABBLOCK TRACT UAC UNSD ZCTA5",
    2020: "BG CBSA CD COUNTY ELSD PLACE SCSD SLDL SLDU STATE TABBLOCK TABBLOCK20 TRACT UAC UNSD ZCTA5 ZCTA520",
    2023: "BG CBSA CD COUNTY ELSD PLACE SCSD SLDL SLDU STATE TABBLOCK20 TRACT UAC UNSD ZCTA520",
    2026: "BG CBSA CD COUNTY ELSD PLACE SCSD SLDL SLDU STATE TABBLOCK20 TRACT UAC20 UNSD ZCTA520",
}

PUBLISHED = [
    # Controls: these already pass on develop.
    ("county", 2020, f"{T}/TIGER2020/COUNTY/tl_2020_us_county.zip"),
    ("tract", 2023, f"{T}/TIGER2023/TRACT/tl_2023_06_tract.zip"),
    # 2010 files live in a vintage subdirectory with a 10 suffix.
    ("county", 2010, f"{T}/TIGER2010/COUNTY/2010/tl_2010_us_county10.zip"),
    ("tract", 2010, f"{T}/TIGER2010/TRACT/2010/tl_2010_06_tract10.zip"),
    # Blocks are published as tabblock10 / tabblock20, never "block".
    ("block", 2019, f"{T}/TIGER2019/TABBLOCK/tl_2019_06_tabblock10.zip"),
    ("block", 2020, f"{T}/TIGER2020/TABBLOCK20/tl_2020_06_tabblock20.zip"),
    ("block", 2023, f"{T}/TIGER2023/TABBLOCK20/tl_2023_06_tabblock20.zip"),
    # Urban areas carry a uac10 / uac20 suffix; the directory is UAC20 from 2024.
    ("urbanarea", 2019, f"{T}/TIGER2019/UAC/tl_2019_us_uac10.zip"),
    ("urbanarea", 2023, f"{T}/TIGER2023/UAC/tl_2023_us_uac20.zip"),
    ("urbanarea", 2026, f"{T}/TIGER2026/UAC20/tl_2026_us_uac20.zip"),
    # School districts are published per state only.
    ("elsd", 2020, f"{T}/TIGER2020/ELSD/tl_2020_06_elsd.zip"),
    ("scsd", 2023, f"{T}/TIGER2023/SCSD/tl_2023_06_scsd.zip"),
    ("unsd", 2026, f"{T}/TIGER2026/UNSD/tl_2026_06_unsd.zip"),
    # TIGER2026 ships cd120 (develop previously mapped it to 119).
    ("cd", 2026, f"{T}/TIGER2026/CD/tl_2026_06_cd120.zip"),
]


@pytest.fixture
def requested_urls():
    urls = []
    gdf = gpd.GeoDataFrame(
        {"geoid": ["06037"], "statefp": ["06"], "name": ["x"]},
        geometry=[Polygon([(0, 0), (1, 0), (1, 1), (0, 0)])],
        crs="EPSG:4326",
    )

    def download(self, url, level):
        urls.append(url)
        return gdf.copy()

    D = sd.CensusDirectoryDiscovery
    with patch.object(D, "get_year_directory_contents",
                      lambda self, year, *a, **k: TIGER_DIRS[year].split()), \
         patch.object(D, "get_available_years",
                      lambda self, *a, **k: sorted(TIGER_DIRS)), \
         patch.object(D, "validate_download_url", lambda self, url: True), \
         patch.object(sd.CensusDataSource, "_download_and_process_tiger", download):
        yield urls


@pytest.mark.parametrize("gtype,year,url", PUBLISHED, ids=lambda v: str(v)[-32:])
def test_download_requests_the_published_census_file(requested_urls, gtype, year, url):
    BoundaryPopulationService()._download_boundaries(gtype, year, "06")
    assert requested_urls == [url]


def test_vtd_2020_is_loadable_or_not_advertised(requested_urls):
    from siege_utilities.geo.django.management.commands.populate_boundaries import Command

    if "vtd" not in Command.GEOGRAPHY_TYPES:
        return
    BoundaryPopulationService()._download_boundaries("vtd", 2020, "48")
    assert requested_urls == [
        f"{T}/TIGER2020PL/STATE/48_TEXAS/48/tl_2020_48_vtd20.zip"
    ]


@pytest.mark.parametrize("gtype,year", [
    ("vtd", 2010), ("vtd", 2019), ("vtd", 2026), ("cbsa", 2022),
    ("block", 2018), ("urbanarea", 2011), ("zcta", 2011),
    ("county", 2009), ("county", 2027),
])
def test_unsupported_pair_fails_before_network(gtype, year):
    with patch("requests.sessions.Session.request", autospec=True) as request:
        with pytest.raises(ValueError, match=f"^{gtype} not supported for year {year}$"):
            BoundaryPopulationService()._download_boundaries(gtype, year, "48")
    request.assert_not_called()


@pytest.mark.parametrize("gtype", ["place", "elsd", "scsd", "unsd", "vtd", "cd"])
def test_missing_state_fails_before_network(gtype):
    with patch("requests.sessions.Session.request", autospec=True) as request:
        with pytest.raises(ValueError, match="State FIPS required"):
            BoundaryPopulationService()._download_boundaries(gtype, 2023 if gtype == "cd" else 2020)
    request.assert_not_called()


# These command cases use the real service transaction and ORM. The URL
# cases above remain independent of both a database and the network.
def live_postgis(test):
    test = pytest.mark.postgis(test)
    return pytest.mark.skipif(
        os.environ.get("SIEGE_TEST_POSTGIS") != "1",
        reason="Set SIEGE_TEST_POSTGIS=1 and SIEGE_TEST_DB_* to a reachable PostGIS test database.",
    )(test)


_REAL_VALIDATE_URL = sd.CensusDirectoryDiscovery.validate_download_url


@live_postgis
@pytest.mark.django_db
@pytest.mark.parametrize("state,abbreviation", [("06", "CA"), ("15", "HI"), ("41", "OR")])
def test_unpublished_vtd_is_skipped_with_warning_and_exit_zero(state, abbreviation):
    from siege_utilities.geo.django import models

    with patch("requests.sessions.Session.request", autospec=True) as request:
        result = BoundaryPopulationService().populate("vtd", 2020, state)
        output = StringIO()
        call_command(
            "populate_boundaries", "--year", "2020", "--type", "vtd",
            "--state", state, "--link-parents", stdout=output,
        )
    assert result.success and result.errors == []
    assert result.sources_skipped == 1
    assert result.records_created == result.records_updated == result.records_skipped == 0
    warning = f"VTD 2020 not published for {abbreviation} by Census"
    assert result.warnings == [warning]
    assert warning in output.getvalue()
    assert "0 created, 0 updated, 1 skipped, 0 errors" in output.getvalue()
    assert models.VTD.objects.count() == 0
    request.assert_not_called()


@pytest.fixture
def missing_vtd_url(requested_urls):
    wrong_url = f"{T}/TIGER2020PL/STATE/48_TEXAS/48/mangled_vtd20.zip"
    response = Response()
    response.status_code = 404
    response.url = wrong_url
    response.raw = BytesIO(b"Not Found")
    with (
        patch.object(sd.CensusDirectoryDiscovery, "_construct_vtd_pl_url", return_value=wrong_url),
        patch.object(sd.CensusDirectoryDiscovery, "validate_download_url", _REAL_VALIDATE_URL),
        patch.object(sd.requests, "get", autospec=True, return_value=response) as request,
    ):
        yield wrong_url, request


def test_published_vtd_404_preserves_url_and_status(missing_vtd_url, requested_urls):
    wrong_url, request = missing_vtd_url
    with pytest.raises(BoundaryUrlValidationError, match="HTTP 404") as exc:
        BoundaryPopulationService()._download_boundaries("vtd", 2020, "48")
    assert exc.value.context["http_status"] == 404
    assert exc.value.context["url"] == wrong_url
    assert request.call_args.args == (wrong_url,)
    assert requested_urls == []


@live_postgis
@pytest.mark.django_db(transaction=True)
def test_published_vtd_wrong_url_is_failure_with_nonzero_exit(missing_vtd_url, requested_urls):
    from siege_utilities.geo.django.management.commands.populate_boundaries import Command

    wrong_url, request = missing_vtd_url
    output, error = StringIO(), StringIO()
    command = Command(stdout=output, stderr=error)
    with pytest.raises(SystemExit) as exc:
        command.run_from_argv([
            "manage.py", "populate_boundaries", "--year", "2020",
            "--type", "vtd", "--state", "48",
        ])
    assert exc.value.code == 1
    assert request.call_args.args == (wrong_url,)
    assert "HTTP 404" in error.getvalue()
    assert wrong_url in error.getvalue()
    assert "not published" not in output.getvalue()
    assert requested_urls == []


@live_postgis
@pytest.mark.django_db
def test_published_vtd_texas_loads(requested_urls):
    from siege_utilities.geo.django import models

    frame = gpd.GeoDataFrame(
        {"geoid20": ["48001000001"], "name20": ["District 1"]},
        geometry=[Polygon([(0, 0), (1, 0), (1, 1), (0, 0)])],
        crs="EPSG:4326",
    )

    def download(self, url, level):
        requested_urls.append(url)
        return frame

    with patch.object(sd.CensusDataSource, "_download_and_process_tiger", download):
        result = BoundaryPopulationService().populate("vtd", 2020, "48")
    assert result.success and result.records_created == 1
    assert result.sources_skipped == result.records_skipped == 0
    assert requested_urls == [f"{T}/TIGER2020PL/STATE/48_TEXAS/48/tl_2020_48_vtd20.zip"]
    assert list(models.VTD.objects.values_list("geoid", flat=True)) == ["48001000001"]


ADDITIONAL_PUBLISHED = [
    ("state", 2010, "STATE/2010/tl_2010_us_state10.zip"),
    ("blockgroup", 2010, "BG/2010/tl_2010_06_bg10.zip"),
    ("block", 2010, "TABBLOCK/2010/tl_2010_06_tabblock10.zip"),
    ("place", 2010, "PLACE/2010/tl_2010_06_place10.zip"),
    ("zcta", 2010, "ZCTA5/2010/tl_2010_us_zcta510.zip"),
    ("cd", 2010, "CD/111/tl_2010_us_cd111.zip"),
    ("sldu", 2010, "SLDU/2010/tl_2010_06_sldu10.zip"),
    ("sldl", 2010, "SLDL/2010/tl_2010_06_sldl10.zip"),
    ("cbsa", 2010, "CBSA/2010/tl_2010_us_cbsa10.zip"),
    ("urbanarea", 2010, "UA/2010/tl_2010_us_uac10.zip"),
    ("elsd", 2010, "ELSD/2010/tl_2010_06_elsd10.zip"),
    ("scsd", 2010, "SCSD/2010/tl_2010_06_scsd10.zip"),
    ("unsd", 2010, "UNSD/2010/tl_2010_06_unsd10.zip"),
    ("block", 2011, "TABBLOCK/tl_2011_06_tabblock.zip"),
    ("block", 2012, "TABBLOCK/tl_2012_06_tabblock.zip"),
    ("block", 2013, "TABBLOCK/tl_2013_06_tabblock.zip"),
    ("urbanarea", 2020, "UAC/tl_2020_us_uac20.zip"),
    ("urbanarea", 2021, "UAC/tl_2021_us_uac10.zip"),
    ("urbanarea", 2022, "UAC/tl_2022_us_uac20.zip"),
    ("urbanarea", 2024, "UAC20/tl_2024_us_uac20.zip"),
]


@pytest.mark.parametrize("gtype,year,path", ADDITIONAL_PUBLISHED)
def test_other_vintage_urls_are_published(requested_urls, gtype, year, path):
    # The extra rows use the fallback inventory as well as the real builder.
    with (
        patch.object(sd.CensusDirectoryDiscovery, "get_year_directory_contents",
                     lambda self, year: sd._known_tiger_directories_for_year(year)),
        patch.object(sd.CensusDirectoryDiscovery, "get_available_years",
                     lambda self: list(range(2010, 2027))),
    ):
        BoundaryPopulationService()._download_boundaries(gtype, year, "06")
    assert requested_urls == [f"{T}/TIGER{year}/{path}"]


@pytest.mark.parametrize("gtype,year,url", PUBLISHED)
def test_published_urls_with_fallback_inventory(requested_urls, gtype, year, url):
    with patch.object(
        sd.CensusDirectoryDiscovery, "get_year_directory_contents",
        lambda self, year: sd._known_tiger_directories_for_year(year),
    ):
        BoundaryPopulationService()._download_boundaries(gtype, year, "06")
    assert requested_urls == [url]

import pytest

from siege_utilities import construct_download_url
from siege_utilities import discover_boundary_types
from siege_utilities import download_data
from siege_utilities import get_available_boundary_types
from siege_utilities import get_geographic_boundaries
from siege_utilities import get_optimal_year
from siege_utilities import validate_download_url


class FakeCensusSource:
    def __init__(self):
        self.calls = []

    def discover_boundary_types(self, year):
        self.calls.append(("discover_boundary_types", year))
        return {"county": "COUNTY", "tract": "TRACT"}

    def get_available_boundary_types(self, year):
        self.calls.append(("get_available_boundary_types", year))
        return {"state": "STATE", "zcta": "ZCTA520"}

    def get_optimal_year(self, year, geographic_level):
        self.calls.append(("get_optimal_year", year, geographic_level))
        return 2020

    def construct_download_url(self, year, geographic_level, state_fips=None):
        self.calls.append(("construct_download_url", year, geographic_level, state_fips))
        return f"https://example.test/{year}/{geographic_level}/{state_fips or 'national'}.zip"

    def validate_download_url(self, url):
        self.calls.append(("validate_download_url", url))
        return url.startswith("https://")

    def get_geographic_boundaries(self, year, geographic_level, state_fips=None, state_identifier=None):
        self.calls.append(
            ("get_geographic_boundaries", year, geographic_level, state_fips, state_identifier)
        )
        return {"fake": "geodataframe"}


@pytest.fixture
def fake_census_source(monkeypatch):
    source = FakeCensusSource()
    monkeypatch.setattr(
        "siege_utilities.geo.spatial_data._get_census_source", lambda: source
    )
    monkeypatch.setattr(
        "siege_utilities.geo.spatial_data.reproject_if_needed",
        lambda gdf, crs=None: {"reprojected": gdf, "crs": crs},
    )
    return source


def test_discover_boundary_types_delegates_to_census_source(fake_census_source):
    assert discover_boundary_types(2020) == {"county": "COUNTY", "tract": "TRACT"}
    assert fake_census_source.calls == [("discover_boundary_types", 2020)]


def test_get_available_boundary_types_delegates_to_census_source(fake_census_source):
    assert get_available_boundary_types(2022) == {"state": "STATE", "zcta": "ZCTA520"}
    assert fake_census_source.calls == [("get_available_boundary_types", 2022)]


def test_get_optimal_year_uses_preferred_year_and_geographic_level(fake_census_source):
    assert get_optimal_year("county", preferred_year=2019) == 2020
    assert fake_census_source.calls == [("get_optimal_year", 2019, "county")]


def test_construct_and_validate_download_url_delegate(fake_census_source):
    url = construct_download_url(2020, "tract", "06")

    assert url == "https://example.test/2020/tract/06.zip"
    assert validate_download_url(url) is True
    assert fake_census_source.calls == [
        ("construct_download_url", 2020, "tract", "06"),
        ("validate_download_url", url),
    ]


def test_download_data_reprojects_source_boundaries(fake_census_source):
    result = download_data(2020, "county", crs="EPSG:3857")

    assert result == {"reprojected": {"fake": "geodataframe"}, "crs": "EPSG:3857"}
    assert fake_census_source.calls == [
        ("get_geographic_boundaries", 2020, "county", None, None)
    ]


def test_get_geographic_boundaries_warns_and_reprojects(fake_census_source):
    with pytest.warns(DeprecationWarning, match="get_geographic_boundaries"):
        result = get_geographic_boundaries(
            2020,
            "tract",
            state_fips="06",
            state_identifier="CA",
            crs="EPSG:3310",
        )

    assert result == {"reprojected": {"fake": "geodataframe"}, "crs": "EPSG:3310"}
    assert fake_census_source.calls == [
        ("get_geographic_boundaries", 2020, "tract", "06", "CA")
    ]

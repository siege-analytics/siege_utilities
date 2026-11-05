"""Reviewer pre-check for #1482. Offline; real fetch logic on dummy TIGER-shaped frames."""
import inspect
from unittest.mock import patch

import geopandas as gpd
import pytest
from shapely.geometry import box

from siege_utilities.geo import spatial_data as sd

LISTING = "BG CBSA COUNTY STATE TRACT TTRACT ZCTA520"
AVAILABLE = [2020, 2023]  # 2024/2025 not published in this stub


def _tiger(**cols):
    n = len(next(iter(cols.values())))
    return gpd.GeoDataFrame(cols, geometry=[box(i, 0, i + 1, 1) for i in range(n)], crs="EPSG:4269")


FRAMES = {
    "tract": _tiger(STATEFP=["06", "06"], COUNTYFP=["037", "001"], GEOID=["06037101100", "06001400100"]),
    "cbsa": _tiger(CBSAFP=["26420", "31080"], GEOID=["26420", "31080"], NAME=["Houston", "LA"]),
    # national-only in the URL builder but missing from the post-download filter set
    "ttract": _tiger(STATEFP=["06", "48"], GEOID=["T1", "T2"]),
}


@pytest.fixture
def source():
    D = sd.CensusDirectoryDiscovery
    with patch.object(D, "get_available_years", lambda self, *a, **k: list(AVAILABLE)), \
         patch.object(D, "get_year_directory_contents", lambda self, y, *a, **k: LISTING.split()), \
         patch.object(D, "validate_download_url", lambda self, url: True), \
         patch.object(sd.CensusDataSource, "_download_and_process_tiger",
                      lambda self, url, level: self._standardize_census_columns(FRAMES[level].copy(), level)):
        yield sd.CensusDataSource()


def test_county_fips_filters_or_is_not_accepted(source):
    if "county_fips" not in inspect.signature(source.fetch_geographic_boundaries).parameters:
        return  # removed from the signature: accepted alternative
    r = source.fetch_geographic_boundaries(2020, "tract", "06", county_fips="037")
    assert r.success and set(r.geodataframe["countyfp"]) == {"037"}


@pytest.mark.parametrize("level", ["cbsa", "ttract"])
def test_unapplied_state_filter_is_not_success(source, level):
    r = source.fetch_geographic_boundaries(2020, level, "48")
    if r.success:
        assert r.context.get("state_filter_applied") is True
        assert set(r.geodataframe["statefp"]) == {"48"}


def test_substituted_vintage_is_not_silent_success(source):
    r = source.fetch_geographic_boundaries(2025, "tract", "06")
    assert r.context.get("served_year") == 2023
    assert not r.success, r.message


def test_census_year_column_holds_the_served_vintage(source):
    r = source.fetch_geographic_boundaries(2020, "tract", "06")
    assert r.success
    assert list(r.geodataframe["census_year"]) == [2020, 2020]
    assert r.context.get("served_year") == 2020


# ---------------------------------------------------------------------------
# Additional coverage beyond the reviewer pre-check above.
# ---------------------------------------------------------------------------


def test_nearest_year_is_served_only_when_explicitly_allowed(source):
    r = source.fetch_geographic_boundaries(2025, "tract", "06", allow_nearest_year=True)
    assert r.success, r.message
    assert r.context["served_year"] == 2023
    assert "TIGER2023/TRACT/tl_2023_06_tract.zip" in r.context["download_url"]
    # The rows carry the vintage served, not the vintage requested.
    assert list(r.geodataframe["census_year"]) == [2023, 2023]


def test_unpublished_vintage_fails_before_any_download(source):
    with patch.object(sd.CensusDataSource, "_download_and_process_tiger") as download:
        r = source.fetch_geographic_boundaries(2025, "tract", "06")
    assert r.error_code == "VINTAGE_NOT_PUBLISHED"
    assert r.error_stage == "discovery"
    assert "allow_nearest_year" in r.message
    download.assert_not_called()


def test_unfilterable_national_layer_reports_state_filter_not_applied(source):
    r = source.fetch_geographic_boundaries(2020, "cbsa", "48")
    assert not r.success
    assert r.error_code == "STATE_FILTER_UNAVAILABLE"
    assert r.context["state_filter_applied"] is False


def test_national_layer_without_state_is_returned_whole(source):
    r = source.fetch_geographic_boundaries(2020, "cbsa")
    assert r.success
    assert len(r.geodataframe) == 2
    assert "state_filter_applied" not in r.context


def test_county_fips_on_layer_without_countyfp_fails(source):
    r = source.fetch_geographic_boundaries(2020, "ttract", "48", county_fips="201")
    assert not r.success
    assert r.error_code == "COUNTY_FILTER_UNAVAILABLE"
    assert r.context["county_filter_applied"] is False


@pytest.mark.parametrize("kwargs", [
    {"state_fips": None, "county_fips": "037"},
    {"state_fips": "06", "county_fips": "06037"},
    {"state_fips": "06", "county_fips": "37"},
])
def test_county_fips_input_is_validated(source, kwargs):
    r = source.fetch_geographic_boundaries(2020, "county", **kwargs)
    assert not r.success
    assert r.error_code == "INVALID_PARAMETERS"


def test_module_wrapper_forwards_county_fips_and_allow_nearest_year(source):
    with patch.object(sd, "_get_census_source", lambda: source):
        r = sd.fetch_geographic_boundaries(
            2025, "tract", "06", county_fips="037", allow_nearest_year=True,
        )
    assert r.success, r.message
    assert set(r.geodataframe["countyfp"]) == {"037"}
    assert r.context["served_year"] == 2023


def test_module_wrapper_does_not_substitute_by_default(source):
    with patch.object(sd, "_get_census_source", lambda: source):
        r = sd.fetch_geographic_boundaries(2025, "tract", "06")
    assert r.error_code == "VINTAGE_NOT_PUBLISHED"

"""Reviewer pre-check for #1464. Directory listings stubbed (no network)."""
from unittest.mock import patch

import pytest

from siege_utilities.geo import spatial_data as sd
from siege_utilities.geo.boundary_result import BoundaryConfigurationError, BoundaryDiscoveryError

T = "https://www2.census.gov/geo/tiger"
LISTING = {
    2010: "ANRC BG CD CONCITY COUNTY COUSUB ELSD PLACE SCSD STATE TABBLOCK TRACT UA UNSD VTD ZCTA5",
    2019: ("ADDRFEAT ANRC AREAWATER BG CD CONCITY COUNTY COUSUB EDGES ELSD LINEARWATER PLACE "
           "ROADS SCSD STATE TABBLOCK TRACT UAC UNSD ZCTA5"),
    2024: "BG CD COUNTY ELSD PLACE SCSD STATE TABBLOCK20 TRACT UAC20 UNSD ZCTA520",
}


@pytest.fixture
def discovery():
    D = sd.CensusDirectoryDiscovery
    with patch.object(D, "get_year_directory_contents",
                      lambda self, year, *a, **k: LISTING[year].split()), \
         patch.object(D, "get_available_years", lambda self, *a, **k: sorted(LISTING)):
        yield D(timeout=1)


PUBLISHED = [
    # controls: fixed on develop by 7b7302bb
    (2010, "county", None, f"{T}/TIGER2010/COUNTY/2010/tl_2010_us_county10.zip"),
    (2010, "tract", "01", f"{T}/TIGER2010/TRACT/2010/tl_2010_01_tract10.zip"),
    (2010, "cd", None, f"{T}/TIGER2010/CD/111/tl_2010_us_cd111.zip"),
    (2019, "block", "01", f"{T}/TIGER2019/TABBLOCK/tl_2019_01_tabblock10.zip"),
    (2019, "unsd", "06", f"{T}/TIGER2019/UNSD/tl_2019_06_unsd.zip"),
    (2019, "uac", None, f"{T}/TIGER2019/UAC/tl_2019_us_uac10.zip"),
    # still open
    (2019, "anrc", None, f"{T}/TIGER2019/ANRC/tl_2019_02_anrc.zip"),
    (2024, "cd119", "06", f"{T}/TIGER2024/CD/tl_2024_06_cd119.zip"),
]


@pytest.mark.parametrize("year,layer,state,url", PUBLISHED, ids=lambda v: str(v))
def test_builder_emits_published_path(discovery, year, layer, state, url):
    if layer.startswith("cd1") and layer not in sd.BOUNDARY_TYPE_CATALOG:
        pytest.skip("cdNNN removed from the catalog: accepted alternative")
    assert discovery.construct_download_url(year, layer, state) == url


@pytest.mark.parametrize("layer", ["place", "concity"])
def test_state_only_layers_refuse_a_national_request(discovery, layer):
    with pytest.raises(BoundaryConfigurationError):
        discovery.construct_download_url(2019, layer, None)


@pytest.mark.parametrize("layer", ["linear_water", "area_water", "roads", "edges", "address_features"])
def test_per_county_layers_are_built_per_county_or_not_advertised(discovery, layer):
    if layer not in sd.BOUNDARY_TYPE_CATALOG:
        return
    # A state-only request cannot name a per-county file: it must refuse.
    with pytest.raises((BoundaryConfigurationError, BoundaryDiscoveryError)):
        discovery.construct_download_url(2019, layer, "01")


def test_403_fallback_lists_only_real_tiger_directories():
    dirs = set(sd._known_tiger_directories_for_year(2019))
    assert {"COUSUB", "ADDRFEAT"} <= dirs
    assert not dirs & {"COUNTYSUB", "SDELM", "SDSEC", "SDUNI", "UAC10"}


# ---------------------------------------------------------------------------
# Additional coverage beyond the reviewer pre-check above.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("layer", ["address_features", "area_water", "edges", "linear_water", "roads"])
@pytest.mark.parametrize("state", ["01", None])
def test_per_county_layers_always_refuse(discovery, layer, state):
    # The pre-check test above returns early once a layer leaves the
    # catalog; the builder must still refuse it.
    assert layer not in sd.BOUNDARY_TYPE_CATALOG
    with pytest.raises(BoundaryConfigurationError, match="per-county"):
        discovery.construct_download_url(2019, layer, state)


def test_anrc_outside_alaska_is_refused(discovery):
    assert discovery.construct_download_url(2019, "anrc", "02") == f"{T}/TIGER2019/ANRC/tl_2019_02_anrc.zip"
    with pytest.raises(BoundaryConfigurationError, match="Alaska"):
        discovery.construct_download_url(2019, "anrc", "06")


def test_concity_is_built_per_state(discovery):
    assert discovery.construct_download_url(2019, "concity", "13") == f"{T}/TIGER2019/CONCITY/tl_2019_13_concity.zip"


@pytest.mark.parametrize("year,layer,state,url", [
    (2010, "cd111", None, f"{T}/TIGER2010/CD/111/tl_2010_us_cd111.zip"),
    (2019, "cd116", None, f"{T}/TIGER2019/CD/tl_2019_us_cd116.zip"),
    (2024, "cd118", "06", f"{T}/TIGER2024/CD/tl_2024_06_cd118.zip"),
])
def test_cd_congress_aliases_resolve_to_the_cd_directory(discovery, year, layer, state, url):
    assert discovery.construct_download_url(year, layer, state) == url


def test_every_congress_is_aliased_when_cd_is_listed(discovery):
    types = discovery.discover_boundary_types(2024)
    for congress in set(sd.YEAR_TO_CONGRESS.values()):
        assert types[f"cd{congress}"] == "CD"

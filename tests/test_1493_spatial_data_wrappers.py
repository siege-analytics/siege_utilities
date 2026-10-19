"""Offline regressions for the public Census wrappers in #1493."""

from unittest.mock import Mock

import geopandas as gpd
import pytest
from shapely.geometry import Point

from siege_utilities.geo import spatial_data as sd
from siege_utilities.geo.boundary_result import BoundaryFetchResult


@pytest.fixture
def stubbed_source(monkeypatch):
    # Keep the real legacy adapter, but bypass discovery and all network I/O.
    source = sd.CensusDataSource.__new__(sd.CensusDataSource)
    frame = gpd.GeoDataFrame(geometry=[Point(-120, 35)], crs="EPSG:4326")
    source.fetch_geographic_boundaries = Mock(
        return_value=BoundaryFetchResult(success=True, geodataframe=frame)
    )
    source.get_geographic_boundaries = Mock(wraps=source.get_geographic_boundaries)
    monkeypatch.setattr(sd, "_get_census_source", lambda: source)
    return source, frame


@pytest.mark.parametrize("level,identifier,expected_fips", [
    ("tract", "CA", "06"),
    ("county", "TX", "48"),
    ("tract", "06", "06"),
    ("tract", "6", "06"),
    ("tract", "California", "06"),
    ("county", " texas ", "48"),
])
def test_state_identifier_reaches_fetch_as_fips(
    stubbed_source, level, identifier, expected_fips,
):
    source, frame = stubbed_source

    with pytest.warns(DeprecationWarning, match="get_geographic_boundaries"):
        result = sd.get_geographic_boundaries(2020, level, state_identifier=identifier)

    source.fetch_geographic_boundaries.assert_called_once_with(
        year=2020, geographic_level=level, state_fips=expected_fips,
        county_fips=None, congress_number=None,
    )
    source.get_geographic_boundaries.assert_called_once_with(
        year=2020, geographic_level=level, state_fips=expected_fips,
    )
    assert result is frame


@pytest.mark.parametrize("state_fips", [None, "06", "48"])
def test_state_fips_and_national_requests_are_preserved(stubbed_source, state_fips):
    source, frame = stubbed_source

    with pytest.warns(DeprecationWarning, match="get_geographic_boundaries"):
        result = sd.get_geographic_boundaries(2020, "county", state_fips=state_fips)

    assert result is frame
    assert source.fetch_geographic_boundaries.call_args.kwargs["state_fips"] == state_fips
    assert source.fetch_geographic_boundaries.call_args.kwargs["county_fips"] is None


def test_state_identifier_keeps_precedence(stubbed_source):
    source, frame = stubbed_source

    with pytest.warns(DeprecationWarning, match="get_geographic_boundaries"):
        result = sd.get_geographic_boundaries(
            2020, "county", state_fips="06", state_identifier="TX",
        )

    assert result is frame
    assert source.fetch_geographic_boundaries.call_args.kwargs["state_fips"] == "48"


def test_invalid_state_identifier_fails_before_fetch(stubbed_source):
    source, _ = stubbed_source

    with pytest.warns(DeprecationWarning, match="get_geographic_boundaries"):
        with pytest.raises(ValueError, match="state identifier"):
            sd.get_geographic_boundaries(2020, "county", state_identifier="Not a state")

    source.fetch_geographic_boundaries.assert_not_called()


@pytest.mark.parametrize("state_fips", [None, "06"])
def test_download_dataset_delegates_to_fetch(stubbed_source, state_fips):
    source, frame = stubbed_source

    result = sd.download_dataset(2020, "county", state_fips=state_fips)

    assert "download_dataset" in sd.__all__
    assert result is frame
    source.fetch_geographic_boundaries.assert_called_once_with(
        year=2020, geographic_level="county", state_fips=state_fips,
        county_fips=None, congress_number=None, allow_nearest_year=False,
    )


@pytest.mark.parametrize("wrapper", ["get_geographic_boundaries", "download_dataset"])
def test_wrappers_honor_output_crs(stubbed_source, wrapper):
    _, frame = stubbed_source

    result = getattr(sd, wrapper)(2020, "county", state_fips="06", crs="EPSG:3857")

    assert result.crs.to_epsg() == 3857
    assert result.geometry.x.iloc[0] == pytest.approx(-13358338.895, abs=0.001)
    assert frame.crs.to_epsg() == 4326


@pytest.mark.parametrize("wrapper", ["get_geographic_boundaries", "download_dataset"])
def test_wrappers_return_none_on_fetch_failure(stubbed_source, wrapper):
    source, _ = stubbed_source
    source.fetch_geographic_boundaries.return_value = BoundaryFetchResult(
        success=False, error_stage="download", message="stubbed download failure",
    )

    result = getattr(sd, wrapper)(2020, "county")

    assert result is None

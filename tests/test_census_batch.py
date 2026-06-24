"""Tests for Census batch geocoder backend (SU#623)."""

from __future__ import annotations

from unittest.mock import patch


from siege_utilities.geo.providers.batch_geocoder import MatchQuality
from siege_utilities.geo.providers.census_batch import (
    CensusBatchGeocoder,
    _census_result_to_geocoding_result,
)


# ---------------------------------------------------------------------------
# Mock CensusGeocodeResult
# ---------------------------------------------------------------------------


class _MockCensusResult:
    def __init__(self, **kwargs):
        self.matched = kwargs.get("matched", True)
        self.input_address = kwargs.get("input_address", "123 Main St")
        self.input_id = kwargs.get("input_id", "1")
        self.matched_address = kwargs.get("matched_address", "123 MAIN ST")
        self.lat = kwargs.get("lat", 41.8781)
        self.lon = kwargs.get("lon", -87.6298)
        self.match_type = kwargs.get("match_type", "Exact")
        self.state_fips = kwargs.get("state_fips", "17")
        self.county_fips = kwargs.get("county_fips", "031")
        self.tract = kwargs.get("tract", "010100")
        self.block = kwargs.get("block", "1001")

    @property
    def state_geoid(self):
        return self.state_fips

    @property
    def county_geoid(self):
        return f"{self.state_fips}{self.county_fips}" if self.state_fips and self.county_fips else ""

    @property
    def tract_geoid(self):
        if self.state_fips and self.county_fips and self.tract:
            return f"{self.state_fips}{self.county_fips}{self.tract}"
        return ""

    @property
    def block_geoid(self):
        if self.state_fips and self.county_fips and self.tract and self.block:
            return f"{self.state_fips}{self.county_fips}{self.tract}{self.block}"
        return ""


# ---------------------------------------------------------------------------
# Converter tests
# ---------------------------------------------------------------------------


class TestCensusResultConverter:
    def test_exact_match(self):
        cr = _MockCensusResult(match_type="Exact")
        gr = _census_result_to_geocoding_result(cr)
        assert gr.match_quality == MatchQuality.EXACT.value
        assert gr.matched
        assert gr.block_geoid == "170310101001001"
        assert gr.backend == "census"

    def test_non_exact(self):
        cr = _MockCensusResult(match_type="Non_Exact")
        gr = _census_result_to_geocoding_result(cr)
        assert gr.match_quality == MatchQuality.INTERPOLATED.value
        assert gr.matched

    def test_no_match(self):
        cr = _MockCensusResult(
            matched=False,
            match_type="No_Match",
            lat=None,
            lon=None,
            state_fips="",
            county_fips="",
            tract="",
            block="",
        )
        gr = _census_result_to_geocoding_result(cr)
        assert not gr.matched
        assert gr.block_geoid == ""

    def test_preserves_input_id(self):
        cr = _MockCensusResult(input_id="MY-ID-123")
        gr = _census_result_to_geocoding_result(cr)
        assert gr.input_id == "MY-ID-123"

    def test_geoid_hierarchy(self):
        cr = _MockCensusResult()
        gr = _census_result_to_geocoding_result(cr)
        assert gr.state_geoid == "17"
        assert gr.county_geoid == "17031"
        assert gr.tract_geoid == "17031010100"
        assert gr.has_block
        assert gr.has_tract


# ---------------------------------------------------------------------------
# CensusBatchGeocoder tests
# ---------------------------------------------------------------------------


class TestCensusBatchGeocoder:
    def test_backend_name(self):
        g = CensusBatchGeocoder()
        assert g.backend_name == "census"

    def test_empty_input(self):
        g = CensusBatchGeocoder()
        result = g.geocode([])
        assert result.total == 0

    @patch("siege_utilities.geo.providers.census_geocoder.geocode_batch_chunked")
    def test_geocode_strings(self, mock_chunked):
        mock_chunked.return_value = [
            _MockCensusResult(input_address="123 Main St", input_id="0"),
        ]
        g = CensusBatchGeocoder()
        result = g.geocode(["123 Main St, Chicago, IL"])
        assert result.total == 1
        assert result.results[0].matched
        mock_chunked.assert_called_once()

    @patch("siege_utilities.geo.providers.census_geocoder.geocode_batch_chunked")
    def test_geocode_dicts(self, mock_chunked):
        mock_chunked.return_value = [
            _MockCensusResult(input_address="123 Main St", input_id="ABC"),
        ]
        g = CensusBatchGeocoder()
        result = g.geocode([
            {"street": "123 Main St", "city": "Chicago", "state": "IL", "zipcode": "60601", "id": "ABC"},
        ])
        assert result.total == 1
        call_args = mock_chunked.call_args[0][0]
        assert call_args[0]["id"] == "ABC"

    @patch("siege_utilities.geo.providers.census_geocoder.geocode_batch_chunked")
    def test_handles_api_error(self, mock_chunked):
        mock_chunked.side_effect = RuntimeError("API down")
        g = CensusBatchGeocoder()
        result = g.geocode(["123 Main St"])
        assert len(result.errors) == 1
        assert "Census batch geocode error" in result.errors[0]

    @patch("siege_utilities.geo.providers.census_geocoder.geocode_batch_chunked")
    def test_multiple_results(self, mock_chunked):
        mock_chunked.return_value = [
            _MockCensusResult(input_id="0", match_type="Exact"),
            _MockCensusResult(input_id="1", match_type="No_Match", matched=False,
                              lat=None, lon=None, state_fips="", county_fips="",
                              tract="", block=""),
        ]
        g = CensusBatchGeocoder()
        result = g.geocode(["addr1", "addr2"])
        assert result.total == 2
        assert result.matched_count == 1
        assert abs(result.match_rate - 0.5) < 0.01

    @patch("siege_utilities.geo.providers.census_geocoder.geocode_batch_chunked")
    def test_custom_chunk_size(self, mock_chunked):
        mock_chunked.return_value = []
        g = CensusBatchGeocoder(chunk_size=5000)
        g.geocode(["addr"])
        _, kwargs = mock_chunked.call_args
        assert kwargs["chunk_size"] == 5000

    def test_is_available(self):
        g = CensusBatchGeocoder()
        assert g.is_available()

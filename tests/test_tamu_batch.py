"""Tests for TAMU batch geocoder backend (SU#625)."""

from __future__ import annotations

import json
from unittest.mock import patch, MagicMock

import pytest

from siege_utilities.geo.providers.batch_geocoder import MatchQuality
from siege_utilities.geo.providers.tamu_batch import (
    DEFAULT_RATE_LIMIT,
    ENV_API_KEY,
    TAMUBatchGeocoder,
)


def _tamu_response(
    lat="41.8781",
    lon="-87.6298",
    matched_address="123 MAIN ST, CHICAGO, IL 60601",
    match_type="Exact",
    state_fips="17",
    county_fips="031",
    tract="010100",
    block="1001",
):
    """Build a mock TAMU JSON response."""
    return {
        "OutputGeocodes": [
            {
                "OutputGeocode": {
                    "Latitude": lat,
                    "Longitude": lon,
                    "MatchedAddress": matched_address,
                    "MatchType": match_type,
                },
                "CensusValues": [
                    {
                        "CensusValue1": {
                            "CensusStateFips": state_fips,
                            "CensusCountyFips": county_fips,
                            "CensusTract": tract,
                            "CensusBlock": block,
                        }
                    }
                ],
            }
        ]
    }


def _mock_urlopen(response_data):
    """Create a mock urlopen context manager returning given JSON data."""
    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps(response_data).encode()
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    return mock_resp


class TestTAMUBatchGeocoderConfig:
    def test_backend_name(self):
        g = TAMUBatchGeocoder(api_key="test-key")
        assert g.backend_name == "tamu"

    def test_is_available_with_key(self):
        g = TAMUBatchGeocoder(api_key="test-key")
        assert g.is_available()

    def test_not_available_without_key(self):
        g = TAMUBatchGeocoder(api_key="")
        assert not g.is_available()

    @patch.dict("os.environ", {ENV_API_KEY: "env-key"})
    def test_api_key_from_env(self):
        g = TAMUBatchGeocoder()
        assert g._api_key == "env-key"
        assert g.is_available()

    def test_explicit_key_overrides_env(self):
        g = TAMUBatchGeocoder(api_key="explicit")
        assert g._api_key == "explicit"

    def test_default_rate_limit(self):
        g = TAMUBatchGeocoder(api_key="k")
        assert g._rate_limit == DEFAULT_RATE_LIMIT

    def test_custom_rate_limit(self):
        g = TAMUBatchGeocoder(api_key="k", rate_limit=1.0)
        assert g._rate_limit == 1.0

    def test_default_census_year(self):
        g = TAMUBatchGeocoder(api_key="k")
        assert g._census_year == "2020"

    def test_custom_census_year(self):
        g = TAMUBatchGeocoder(api_key="k", census_year="2010")
        assert g._census_year == "2010"


class TestTAMUBatchGeocoderGeocode:
    def test_empty_input(self):
        g = TAMUBatchGeocoder(api_key="k")
        result = g.geocode([])
        assert result.total == 0

    def test_no_api_key_returns_error(self):
        g = TAMUBatchGeocoder(api_key="")
        result = g.geocode(["123 Main St"])
        assert len(result.errors) == 1
        assert "API key" in result.errors[0]

    @patch("siege_utilities.geo.providers.tamu_batch.time.sleep")
    @patch.object(TAMUBatchGeocoder, "_tamu_request")
    def test_single_match(self, mock_request, mock_sleep):
        mock_request.return_value = GeocodingResult(
            input_address="123 Main St, Chicago, IL",
            input_id="0",
            matched_address="123 MAIN ST",
            lat=41.8781,
            lon=-87.6298,
            match_quality=MatchQuality.EXACT.value,
            state_geoid="17",
            county_geoid="17031",
            tract_geoid="17031010100",
            block_geoid="170310101001001",
            backend="tamu",
        )
        g = TAMUBatchGeocoder(api_key="k", rate_limit=0.0)
        result = g.geocode(["123 Main St, Chicago, IL"])

        assert result.total == 1
        assert result.results[0].matched
        assert result.results[0].lat == 41.8781
        assert result.results[0].backend == "tamu"
        assert result.results[0].block_geoid == "170310101001001"

    @patch("siege_utilities.geo.providers.tamu_batch.time.sleep")
    @patch.object(TAMUBatchGeocoder, "_tamu_request")
    def test_no_match(self, mock_request, mock_sleep):
        mock_request.return_value = None
        g = TAMUBatchGeocoder(api_key="k", rate_limit=0.0)
        result = g.geocode(["fake address"])

        assert result.total == 1
        assert not result.results[0].matched

    @patch("siege_utilities.geo.providers.tamu_batch.time.sleep")
    @patch.object(TAMUBatchGeocoder, "_tamu_request")
    def test_multiple_results(self, mock_request, mock_sleep):
        gr_match = GeocodingResult(
            input_address="a", input_id="0",
            lat=41.0, lon=-87.0,
            match_quality=MatchQuality.EXACT.value, backend="tamu",
        )
        mock_request.side_effect = [gr_match, None, gr_match]
        g = TAMUBatchGeocoder(api_key="k", rate_limit=0.0)
        result = g.geocode(["a", "b", "c"])

        assert result.total == 3
        assert result.matched_count == 2

    @patch("siege_utilities.geo.providers.tamu_batch.time.sleep")
    @patch.object(TAMUBatchGeocoder, "_tamu_request")
    def test_handles_exception(self, mock_request, mock_sleep):
        mock_request.side_effect = Exception("API error")
        g = TAMUBatchGeocoder(api_key="k", rate_limit=0.0)
        result = g.geocode(["123 Main St"])

        assert result.total == 1
        assert not result.results[0].matched

    @patch("siege_utilities.geo.providers.tamu_batch.time.sleep")
    @patch.object(TAMUBatchGeocoder, "_tamu_request")
    def test_empty_query_returns_no_match(self, mock_request, mock_sleep):
        g = TAMUBatchGeocoder(api_key="k", rate_limit=0.0)
        result = g.geocode([{"street": "", "city": "", "state": "", "zipcode": ""}])
        assert result.total == 1
        assert not result.results[0].matched
        mock_request.assert_not_called()


# Need to import GeocodingResult for test construction
from siege_utilities.geo.providers.batch_geocoder import GeocodingResult


class TestTAMUParseResponse:
    """Tests for the TAMU response parser."""

    def _make_geocoder(self):
        return TAMUBatchGeocoder(api_key="test-key", rate_limit=0.0)

    def _make_addr(self):
        from siege_utilities.geo.providers.batch_geocoder import AddressInput
        return AddressInput(
            street="123 Main St", city="Chicago", state="IL",
            zipcode="60601", input_id="test-1",
        )

    def test_exact_match(self):
        g = self._make_geocoder()
        addr = self._make_addr()
        data = _tamu_response(match_type="Exact")
        result = g._parse_response(data, addr)

        assert result is not None
        assert result.lat == 41.8781
        assert result.lon == -87.6298
        assert result.match_quality == MatchQuality.EXACT.value
        assert result.state_geoid == "17"
        assert result.county_geoid == "17031"
        assert result.tract_geoid == "17031010100"
        assert result.block_geoid == "170310101001001"

    def test_interpolated_match(self):
        g = self._make_geocoder()
        addr = self._make_addr()
        data = _tamu_response(match_type="Interpolated")
        result = g._parse_response(data, addr)

        assert result is not None
        assert result.match_quality == MatchQuality.INTERPOLATED.value

    def test_approximate_match(self):
        g = self._make_geocoder()
        addr = self._make_addr()
        data = _tamu_response(match_type="Approximate")
        result = g._parse_response(data, addr)

        assert result is not None
        assert result.match_quality == MatchQuality.APPROXIMATE.value

    def test_nearexact_maps_to_exact(self):
        g = self._make_geocoder()
        addr = self._make_addr()
        data = _tamu_response(match_type="NearExact")
        result = g._parse_response(data, addr)

        assert result is not None
        assert result.match_quality == MatchQuality.EXACT.value

    def test_empty_geocodes(self):
        g = self._make_geocoder()
        addr = self._make_addr()
        result = g._parse_response({"OutputGeocodes": []}, addr)
        assert result is None

    def test_missing_lat_lon(self):
        g = self._make_geocoder()
        addr = self._make_addr()
        data = _tamu_response(lat="", lon="")
        result = g._parse_response(data, addr)
        assert result is None

    def test_zero_lat_lon_treated_as_no_match(self):
        g = self._make_geocoder()
        addr = self._make_addr()
        data = _tamu_response(lat="0.0", lon="0.0")
        result = g._parse_response(data, addr)
        assert result is None

    def test_no_census_values(self):
        g = self._make_geocoder()
        addr = self._make_addr()
        data = _tamu_response()
        data["OutputGeocodes"][0]["CensusValues"] = []
        result = g._parse_response(data, addr)

        assert result is not None
        assert result.lat == 41.8781
        assert result.state_geoid == ""
        assert result.block_geoid == ""

    def test_partial_geoid_hierarchy(self):
        g = self._make_geocoder()
        addr = self._make_addr()
        data = _tamu_response(tract="", block="")
        result = g._parse_response(data, addr)

        assert result is not None
        assert result.state_geoid == "17"
        assert result.county_geoid == "17031"
        assert result.tract_geoid == ""
        assert result.block_geoid == ""

    def test_preserves_input_id(self):
        g = self._make_geocoder()
        addr = self._make_addr()
        data = _tamu_response()
        result = g._parse_response(data, addr)
        assert result.input_id == "test-1"

    def test_matched_address_preserved(self):
        g = self._make_geocoder()
        addr = self._make_addr()
        data = _tamu_response(matched_address="123 MAIN ST, CHICAGO IL")
        result = g._parse_response(data, addr)
        assert result.matched_address == "123 MAIN ST, CHICAGO IL"


class TestTAMURequest:
    """Tests for the low-level _tamu_request method."""

    @patch("siege_utilities.geo.providers.tamu_batch.urllib.request.urlopen")
    def test_successful_request(self, mock_urlopen):
        mock_urlopen.return_value = _mock_urlopen(_tamu_response())
        g = TAMUBatchGeocoder(api_key="test-key", rate_limit=0.0)
        from siege_utilities.geo.providers.batch_geocoder import AddressInput
        addr = AddressInput(
            street="123 Main St", city="Chicago", state="IL",
            zipcode="60601", input_id="0",
        )
        result = g._tamu_request(addr)
        assert result is not None
        assert result.lat == 41.8781

    @patch("siege_utilities.geo.providers.tamu_batch.time.sleep")
    @patch("siege_utilities.geo.providers.tamu_batch.urllib.request.urlopen")
    def test_retries_on_failure(self, mock_urlopen, mock_sleep):
        mock_urlopen.side_effect = [
            Exception("timeout"),
            _mock_urlopen(_tamu_response()),
        ]
        g = TAMUBatchGeocoder(api_key="test-key", rate_limit=0.0, max_retries=2)
        from siege_utilities.geo.providers.batch_geocoder import AddressInput
        addr = AddressInput(
            street="123 Main St", city="Chicago", state="IL",
            zipcode="60601", input_id="0",
        )
        result = g._tamu_request(addr)
        assert result is not None
        assert mock_urlopen.call_count == 2

    @patch("siege_utilities.geo.providers.tamu_batch.time.sleep")
    @patch("siege_utilities.geo.providers.tamu_batch.urllib.request.urlopen")
    def test_raises_after_max_retries(self, mock_urlopen, mock_sleep):
        mock_urlopen.side_effect = Exception("persistent failure")
        g = TAMUBatchGeocoder(api_key="test-key", rate_limit=0.0, max_retries=1)
        from siege_utilities.geo.providers.batch_geocoder import AddressInput
        addr = AddressInput(
            street="123 Main St", city="Chicago", state="IL",
            zipcode="60601", input_id="0",
        )
        with pytest.raises(Exception, match="persistent failure"):
            g._tamu_request(addr)
        assert mock_urlopen.call_count == 2

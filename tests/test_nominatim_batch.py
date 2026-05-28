"""Tests for Nominatim batch geocoder backend (SU#624)."""

from __future__ import annotations

from unittest.mock import patch, MagicMock

import pytest

from siege_utilities.geo.providers.batch_geocoder import MatchQuality
from siege_utilities.geo.providers.nominatim_batch import (
    DEFAULT_RATE_LIMIT,
    NominatimBatchGeocoder,
    PUBLIC_NOMINATIM_URL,
    SELF_HOSTED_RATE_LIMIT,
)


class TestNominatimBatchGeocoder:
    def test_backend_name(self):
        g = NominatimBatchGeocoder()
        assert g.backend_name == "nominatim"

    def test_default_rate_limit_public(self):
        g = NominatimBatchGeocoder()
        assert g._rate_limit == DEFAULT_RATE_LIMIT

    def test_self_hosted_rate_limit(self):
        g = NominatimBatchGeocoder(server_url="http://my-nominatim:8080")
        assert g._rate_limit == SELF_HOSTED_RATE_LIMIT

    def test_custom_rate_limit(self):
        g = NominatimBatchGeocoder(rate_limit=0.5)
        assert g._rate_limit == 0.5

    def test_empty_input(self):
        g = NominatimBatchGeocoder()
        result = g.geocode([])
        assert result.total == 0

    @patch("siege_utilities.geo.providers.nominatim_batch.time.sleep")
    @patch.object(NominatimBatchGeocoder, "_nominatim_request")
    def test_geocode_single_match(self, mock_request, mock_sleep):
        mock_request.return_value = (41.8781, -87.6298)
        g = NominatimBatchGeocoder(rate_limit=0.0)
        result = g.geocode(["123 Main St, Chicago, IL"])

        assert result.total == 1
        assert result.results[0].matched
        assert result.results[0].lat == 41.8781
        assert result.results[0].lon == -87.6298
        assert result.results[0].backend == "nominatim"

    @patch("siege_utilities.geo.providers.nominatim_batch.time.sleep")
    @patch.object(NominatimBatchGeocoder, "_nominatim_request")
    def test_geocode_no_match(self, mock_request, mock_sleep):
        mock_request.return_value = None
        g = NominatimBatchGeocoder(rate_limit=0.0)
        result = g.geocode(["fake address nowhere"])

        assert result.total == 1
        assert not result.results[0].matched

    @patch("siege_utilities.geo.providers.nominatim_batch.time.sleep")
    @patch.object(NominatimBatchGeocoder, "_nominatim_request")
    def test_geocode_multiple(self, mock_request, mock_sleep):
        mock_request.side_effect = [
            (41.8781, -87.6298),
            None,
            (42.3601, -71.0589),
        ]
        g = NominatimBatchGeocoder(rate_limit=0.0)
        result = g.geocode(["addr1", "addr2", "addr3"])

        assert result.total == 3
        assert result.matched_count == 2

    @patch("siege_utilities.geo.providers.nominatim_batch.time.sleep")
    @patch.object(NominatimBatchGeocoder, "_nominatim_request")
    def test_handles_exception(self, mock_request, mock_sleep):
        mock_request.side_effect = Exception("network error")
        g = NominatimBatchGeocoder(rate_limit=0.0)
        result = g.geocode(["123 Main St"])

        assert result.total == 1
        assert not result.results[0].matched

    @patch("siege_utilities.geo.providers.nominatim_batch.time.sleep")
    @patch.object(NominatimBatchGeocoder, "_nominatim_request")
    def test_match_quality_is_approximate(self, mock_request, mock_sleep):
        mock_request.return_value = (41.0, -87.0)
        g = NominatimBatchGeocoder(rate_limit=0.0)
        result = g.geocode(["test"])
        assert result.results[0].match_quality == MatchQuality.APPROXIMATE.value

    @patch("siege_utilities.geo.providers.nominatim_batch.time.sleep")
    @patch.object(NominatimBatchGeocoder, "_nominatim_request")
    def test_no_block_geoid(self, mock_request, mock_sleep):
        mock_request.return_value = (41.0, -87.0)
        g = NominatimBatchGeocoder(rate_limit=0.0)
        result = g.geocode(["test"])
        assert result.results[0].block_geoid == ""

    def test_default_country_codes(self):
        g = NominatimBatchGeocoder()
        assert g._country_codes == ["us"]

    def test_is_available(self):
        g = NominatimBatchGeocoder()
        assert g.is_available()

    def test_default_server_url(self):
        g = NominatimBatchGeocoder()
        assert g._server_url == PUBLIC_NOMINATIM_URL

    def test_custom_server_url(self):
        g = NominatimBatchGeocoder(server_url="http://local:8080")
        assert g._server_url == "http://local:8080"

    def test_custom_country_codes(self):
        g = NominatimBatchGeocoder(country_codes=["de", "at"])
        assert g._country_codes == ["de", "at"]

    @patch("siege_utilities.geo.providers.nominatim_batch.time.sleep")
    @patch.object(NominatimBatchGeocoder, "_nominatim_request")
    def test_empty_query_returns_no_match(self, mock_request, mock_sleep):
        g = NominatimBatchGeocoder(rate_limit=0.0)
        result = g.geocode([{"street": "", "city": "", "state": "", "zipcode": ""}])
        assert result.total == 1
        assert not result.results[0].matched
        mock_request.assert_not_called()


class TestNominatimRequest:
    """Tests for the low-level _nominatim_request method."""

    @patch("siege_utilities.geo.providers.nominatim_batch.urllib.request.urlopen")
    def test_successful_response(self, mock_urlopen):
        import json
        resp_data = json.dumps([{"lat": "41.8781", "lon": "-87.6298"}]).encode()
        mock_resp = MagicMock()
        mock_resp.read.return_value = resp_data
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        g = NominatimBatchGeocoder(rate_limit=0.0)
        result = g._nominatim_request("123 Main St, Chicago, IL")
        assert result == (41.8781, -87.6298)

    @patch("siege_utilities.geo.providers.nominatim_batch.urllib.request.urlopen")
    def test_empty_response(self, mock_urlopen):
        import json
        resp_data = json.dumps([]).encode()
        mock_resp = MagicMock()
        mock_resp.read.return_value = resp_data
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        g = NominatimBatchGeocoder(rate_limit=0.0)
        result = g._nominatim_request("nonexistent place")
        assert result is None

    @patch("siege_utilities.geo.providers.nominatim_batch.time.sleep")
    @patch("siege_utilities.geo.providers.nominatim_batch.urllib.request.urlopen")
    def test_retries_on_failure(self, mock_urlopen, mock_sleep):
        import json
        resp_data = json.dumps([{"lat": "41.0", "lon": "-87.0"}]).encode()
        mock_resp = MagicMock()
        mock_resp.read.return_value = resp_data
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)

        mock_urlopen.side_effect = [
            Exception("timeout"),
            mock_resp,
        ]
        g = NominatimBatchGeocoder(rate_limit=0.0, max_retries=2)
        result = g._nominatim_request("test")
        assert result == (41.0, -87.0)
        assert mock_urlopen.call_count == 2

    @patch("siege_utilities.geo.providers.nominatim_batch.time.sleep")
    @patch("siege_utilities.geo.providers.nominatim_batch.urllib.request.urlopen")
    def test_raises_after_max_retries(self, mock_urlopen, mock_sleep):
        mock_urlopen.side_effect = Exception("persistent failure")
        g = NominatimBatchGeocoder(rate_limit=0.0, max_retries=1)
        with pytest.raises(Exception, match="persistent failure"):
            g._nominatim_request("test")
        assert mock_urlopen.call_count == 2

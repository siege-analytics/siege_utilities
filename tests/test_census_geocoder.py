"""Tests for siege_utilities.geo.census_geocoder module."""

import json
import pytest
from unittest.mock import patch, MagicMock

from siege_utilities.geo.census_geocoder import (
    CensusGeocodeError,
    CensusGeocodeResult,
    CensusVintage,
    _safe_float,
    geocode_batch,
    geocode_batch_chunked,
    geocode_single,
    select_vintage_for_cycle,
)


# --- CensusVintage ---


class TestCensusVintage:
    def test_enum_values(self):
        assert CensusVintage.CENSUS_2010.value == "Census2010_Census2010"
        assert CensusVintage.CENSUS_2020.value == "Census2020_Census2020"
        assert CensusVintage.CURRENT.value == "Public_Current"

    def test_benchmark_property(self):
        assert CensusVintage.CENSUS_2010.benchmark == "Census2010"
        assert CensusVintage.CENSUS_2020.benchmark == "Census2020"
        assert CensusVintage.CURRENT.benchmark == "Public"

    def test_vintage_property(self):
        assert CensusVintage.CENSUS_2010.vintage == "Census2010"
        assert CensusVintage.CENSUS_2020.vintage == "Census2020"
        assert CensusVintage.CURRENT.vintage == "Current"

    def test_is_string_enum(self):
        assert isinstance(CensusVintage.CURRENT, str)


# --- select_vintage_for_cycle ---


class TestSelectVintageForCycle:
    def test_current_cycle(self):
        assert select_vintage_for_cycle(2024) == CensusVintage.CURRENT
        assert select_vintage_for_cycle(2020) == CensusVintage.CURRENT
        assert select_vintage_for_cycle(2026) == CensusVintage.CURRENT

    def test_census_2020_era(self):
        assert select_vintage_for_cycle(2012) == CensusVintage.CENSUS_2020
        assert select_vintage_for_cycle(2018) == CensusVintage.CENSUS_2020
        assert select_vintage_for_cycle(2019) == CensusVintage.CENSUS_2020

    def test_census_2010_era(self):
        assert select_vintage_for_cycle(1980) == CensusVintage.CENSUS_2010
        assert select_vintage_for_cycle(2000) == CensusVintage.CENSUS_2010
        assert select_vintage_for_cycle(2010) == CensusVintage.CENSUS_2010
        assert select_vintage_for_cycle(2011) == CensusVintage.CENSUS_2010

    def test_pre_1980_fallback(self):
        assert select_vintage_for_cycle(1970) == CensusVintage.CENSUS_2010


# --- CensusGeocodeResult ---


class TestCensusGeocodeResult:
    def test_default_is_unmatched(self):
        r = CensusGeocodeResult()
        assert not r.matched
        assert r.match_type == "No_Match"

    def test_geoid_construction(self):
        r = CensusGeocodeResult(
            matched=True,
            state_fips="48",
            county_fips="453",
            tract="001234",
            block="5678",
        )
        assert r.state_geoid == "48"
        assert r.county_geoid == "48453"
        assert r.tract_geoid == "48453001234"
        assert r.block_geoid == "484530012345678"
        assert r.block_group_geoid == "484530012345"

    def test_empty_geoids_when_missing(self):
        r = CensusGeocodeResult()
        assert r.state_geoid == ""
        assert r.county_geoid == ""
        assert r.tract_geoid == ""
        assert r.block_geoid == ""
        assert r.block_group_geoid == ""

    def test_partial_geoids(self):
        r = CensusGeocodeResult(state_fips="48", county_fips="453")
        assert r.state_geoid == "48"
        assert r.county_geoid == "48453"
        assert r.tract_geoid == ""
        assert r.block_geoid == ""


# --- geocode_single (mocked) ---


class TestGeocodeSingle:
    @patch("siege_utilities.geo.census_geocoder._get_geocoder")
    def test_successful_match(self, mock_get_geocoder):
        mock_cg = MagicMock()
        mock_cg.onelineaddress.return_value = {
            "result": {
                "addressMatches": [{
                    "matchedAddress": "1600 PENNSYLVANIA AVE NW, WASHINGTON, DC, 20500",
                    "coordinates": {"x": -77.0365, "y": 38.8977},
                    "geographies": {
                        "Census Blocks": [{
                            "STATE": "11",
                            "COUNTY": "001",
                            "TRACT": "006202",
                            "BLOCK": "1031",
                        }]
                    },
                    "addressComponents": {"side": "L", "tigerLineId": "12345"},
                }]
            }
        }
        mock_get_geocoder.return_value = mock_cg

        result = geocode_single(
            "1600 Pennsylvania Ave NW", "Washington", "DC", "20500"
        )

        assert result.matched
        assert result.lat == pytest.approx(38.8977)
        assert result.lon == pytest.approx(-77.0365)
        assert result.state_fips == "11"
        assert result.county_fips == "001"
        assert result.tract == "006202"
        assert result.block == "1031"
        assert result.state_geoid == "11"
        assert result.county_geoid == "11001"
        assert result.tract_geoid == "11001006202"

    @patch("siege_utilities.geo.census_geocoder._get_geocoder")
    def test_no_match(self, mock_get_geocoder):
        mock_cg = MagicMock()
        mock_cg.onelineaddress.return_value = {
            "result": {"addressMatches": []}
        }
        mock_get_geocoder.return_value = mock_cg

        result = geocode_single("123 Fake St", "Nowhere", "XX", "00000")
        assert not result.matched
        assert result.input_address == "123 Fake St, Nowhere, XX 00000"

    @patch("siege_utilities.geo.census_geocoder._get_geocoder")
    def test_api_error_raises_census_geocode_error(self, mock_get_geocoder):
        """API failure now raises CensusGeocodeError instead of faking an
        unmatched result — see ELE-2420 FAILURE_MODES.md CC1."""
        mock_cg = MagicMock()
        mock_cg.onelineaddress.side_effect = Exception("API timeout")
        mock_get_geocoder.return_value = mock_cg

        with pytest.raises(CensusGeocodeError):
            geocode_single("1600 Pennsylvania Ave", "Washington", "DC", "20500")


# --- geocode_batch (mocked) ---


class TestGeocodeBatch:
    def test_empty_input(self):
        assert geocode_batch([]) == []

    def test_exceeds_max_raises(self):
        with pytest.raises(ValueError, match="max 10,000"):
            geocode_batch([{"id": str(i)} for i in range(10_001)])

    @patch("siege_utilities.geo.census_geocoder._get_geocoder")
    def test_batch_results(self, mock_get_geocoder):
        mock_cg = MagicMock()
        mock_cg.addressbatch.return_value = [
            {
                "id": "1",
                "is_match": "Match",
                "match_type": "Exact",
                "address": "1600 Pennsylvania Ave, Washington, DC 20500",
                "match_address": "1600 PENNSYLVANIA AVE NW, WASHINGTON, DC, 20500",
                "lat": "38.8977",
                "lon": "-77.0365",
                "statefp": "11",
                "countyfp": "001",
                "tract": "006202",
                "block": "1031",
                "tigerlineid": "12345",
                "side": "L",
            },
            {
                "id": "2",
                "is_match": "No_Match",
                "address": "123 Fake St, Nowhere, XX 00000",
            },
        ]
        mock_get_geocoder.return_value = mock_cg

        addresses = [
            {"id": "1", "street": "1600 Pennsylvania Ave", "city": "Washington", "state": "DC", "zipcode": "20500"},
            {"id": "2", "street": "123 Fake St", "city": "Nowhere", "state": "XX", "zipcode": "00000"},
        ]
        results = geocode_batch(addresses)

        assert len(results) == 2
        assert results[0].matched
        assert results[0].state_fips == "11"
        assert results[0].lat == pytest.approx(38.8977)
        assert not results[1].matched


# --- geocode_batch_chunked ---


class TestGeocodeBatchChunked:
    @patch("siege_utilities.geo.census_geocoder.geocode_batch")
    def test_chunks_correctly(self, mock_batch):
        mock_batch.return_value = [CensusGeocodeResult(input_id="0")]

        addresses = [{"id": str(i), "street": "x"} for i in range(25_000)]
        geocode_batch_chunked(addresses, chunk_size=10_000)

        assert mock_batch.call_count == 3
        assert len(mock_batch.call_args_list[0][0][0]) == 10_000
        assert len(mock_batch.call_args_list[1][0][0]) == 10_000
        assert len(mock_batch.call_args_list[2][0][0]) == 5_000


# --- _safe_float ---


class TestSafeFloat:
    def test_valid_float(self):
        assert _safe_float("38.8977") == pytest.approx(38.8977)

    def test_none(self):
        assert _safe_float(None) is None

    def test_empty_string(self):
        assert _safe_float("") is None

    def test_non_numeric(self):
        assert _safe_float("abc") is None

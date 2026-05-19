"""Tests for the typed exception hierarchy in geo.census_geocoder (ELE-2420)."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from siege_utilities.geo.census_geocoder import (
    CensusGeocodeError,
    CensusGeocodeResult,
    geocode_batch,
    geocode_single,
)


class TestExceptionHierarchy:
    def test_is_runtime_error(self):
        assert issubclass(CensusGeocodeError, RuntimeError)


class TestGeocodeSingle:
    def test_api_failure_raises(self):
        fake = MagicMock()
        fake.onelineaddress.side_effect = ConnectionError("network down")
        with patch(
            "siege_utilities.geo.providers.census_geocoder._get_geocoder",
            return_value=fake,
        ):
            with pytest.raises(CensusGeocodeError) as exc_info:
                geocode_single("1600 Pennsylvania Ave", "Washington", "DC", "20500")
        assert isinstance(exc_info.value.__cause__, ConnectionError)
        assert "1600 Pennsylvania Ave" in str(exc_info.value)

    def test_no_match_returns_unmatched_result_not_error(self):
        """No match is a return-value concern, not an exception."""
        fake = MagicMock()
        fake.onelineaddress.return_value = {"result": {"addressMatches": []}}
        with patch(
            "siege_utilities.geo.providers.census_geocoder._get_geocoder",
            return_value=fake,
        ):
            result = geocode_single("garbage", "nowhere", "ZZ", "00000")
        assert isinstance(result, CensusGeocodeResult)
        assert result.matched is False
        assert result.input_address == "garbage, nowhere, ZZ 00000"


class TestGeocodeBatch:
    def test_api_failure_raises(self):
        fake = MagicMock()
        fake.addressbatch.side_effect = ConnectionError("network down")
        addresses = [
            {"id": "1", "street": "a", "city": "b", "state": "c", "zipcode": "d"},
            {"id": "2", "street": "e", "city": "f", "state": "g", "zipcode": "h"},
        ]
        with patch(
            "siege_utilities.geo.providers.census_geocoder._get_geocoder",
            return_value=fake,
        ):
            with pytest.raises(CensusGeocodeError) as exc_info:
                geocode_batch(addresses)
        assert isinstance(exc_info.value.__cause__, ConnectionError)
        assert "2 addresses" in str(exc_info.value)

    def test_oversize_batch_still_raises_value_error(self):
        """Input-validation ValueError should not be swallowed or converted."""
        with pytest.raises(ValueError):
            geocode_batch([{"id": str(i)} for i in range(10_001)])

    def test_empty_batch_returns_empty_list(self):
        """Empty input is a legitimate empty-success path."""
        assert geocode_batch([]) == []

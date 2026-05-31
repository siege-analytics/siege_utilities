"""Tests for the typed exception path in geo.geocoding (#800).

Mirrors the test pattern from ``test_census_geocoder_errors.py`` so the
two geocoders document and enforce the same SU-1 contract:

* "No match" is a return-value outcome (``None``), not an exception.
* Network, service, and parse failures raise ``GeocodingError`` with the
  underlying cause attached via ``__cause__``.
* Empty input is a precondition violation and raises ``ValueError``.
"""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

geopy = pytest.importorskip("geopy")
from geopy.exc import GeocoderServiceError, GeocoderTimedOut

from siege_utilities.geo.geocoding import (
    GeocodingError,
    get_coordinates,
    use_nominatim_geocoder,
)


def _fake_geocoder_returning(result):
    """Build a Nominatim-like mock whose ``geocode`` returns ``result``."""
    fake = MagicMock()
    fake.geocode.return_value = result
    return fake


def _fake_geocoder_raising(exc):
    """Build a Nominatim-like mock whose ``geocode`` raises ``exc`` every call."""
    fake = MagicMock()
    fake.geocode.side_effect = exc
    return fake


class TestExceptionHierarchy:
    def test_is_runtime_error(self):
        assert issubclass(GeocodingError, RuntimeError)


class TestUseNominatimGeocoder:
    def test_empty_address_raises_value_error(self):
        with pytest.raises(ValueError):
            use_nominatim_geocoder("")

    def test_none_address_raises_value_error(self):
        with pytest.raises(ValueError):
            use_nominatim_geocoder(None)

    def test_no_match_returns_none(self):
        """A legitimate 'no result found' keeps the None return contract."""
        fake = _fake_geocoder_returning(None)
        with patch(
            "siege_utilities.geo.geocoding.Nominatim", return_value=fake,
        ), patch("siege_utilities.geo.geocoding.time.sleep"):
            result = use_nominatim_geocoder(
                "garbage address", server_url="http://x",
            )
        assert result is None

    def test_timeout_after_retries_raises(self):
        fake = _fake_geocoder_raising(GeocoderTimedOut("timeout"))
        with patch(
            "siege_utilities.geo.geocoding.Nominatim", return_value=fake,
        ), patch("siege_utilities.geo.geocoding.time.sleep"):
            with pytest.raises(GeocodingError) as exc_info:
                use_nominatim_geocoder(
                    "1600 Pennsylvania Ave", max_retries=2,
                    server_url="http://x",
                )
        assert isinstance(exc_info.value.__cause__, GeocoderTimedOut)
        assert "1600 Pennsylvania Ave" in str(exc_info.value)

    def test_service_error_after_retries_raises(self):
        fake = _fake_geocoder_raising(GeocoderServiceError("503"))
        with patch(
            "siege_utilities.geo.geocoding.Nominatim", return_value=fake,
        ), patch("siege_utilities.geo.geocoding.time.sleep"):
            with pytest.raises(GeocodingError) as exc_info:
                use_nominatim_geocoder(
                    "addr", max_retries=1, server_url="http://x",
                )
        assert isinstance(exc_info.value.__cause__, GeocoderServiceError)

    def test_unexpected_exception_raises(self):
        fake = _fake_geocoder_raising(RuntimeError("kaboom"))
        with patch(
            "siege_utilities.geo.geocoding.Nominatim", return_value=fake,
        ), patch("siege_utilities.geo.geocoding.time.sleep"):
            with pytest.raises(GeocodingError) as exc_info:
                use_nominatim_geocoder("addr", server_url="http://x")
        assert isinstance(exc_info.value.__cause__, RuntimeError)

    def test_match_returns_json(self):
        match = MagicMock()
        match.raw = {"display_name": "1600 Pennsylvania Ave"}
        match.latitude = 38.8977
        match.longitude = -77.0365
        fake = _fake_geocoder_returning(match)
        with patch(
            "siege_utilities.geo.geocoding.Nominatim", return_value=fake,
        ), patch("siege_utilities.geo.geocoding.time.sleep"):
            result = use_nominatim_geocoder(
                "1600 Pennsylvania Ave", server_url="http://x",
            )
        assert result is not None
        data = json.loads(result)
        assert data["nominatim_lat"] == 38.8977
        assert data["nominatim_lng"] == -77.0365


class TestGetCoordinates:
    def test_timeout_propagates_geocoding_error(self):
        """Previously this swallowed every exception and returned None."""
        fake = _fake_geocoder_raising(GeocoderTimedOut("timeout"))
        with patch(
            "siege_utilities.geo.geocoding.Nominatim", return_value=fake,
        ), patch("siege_utilities.geo.geocoding.time.sleep"):
            with pytest.raises(GeocodingError):
                get_coordinates(
                    "addr", max_retries=1, server_url="http://x",
                )

    def test_no_match_returns_none(self):
        fake = _fake_geocoder_returning(None)
        with patch(
            "siege_utilities.geo.geocoding.Nominatim", return_value=fake,
        ), patch("siege_utilities.geo.geocoding.time.sleep"):
            assert get_coordinates("garbage", server_url="http://x") is None

    def test_match_returns_tuple(self):
        match = MagicMock()
        match.raw = {}
        match.latitude = 12.34
        match.longitude = 56.78
        fake = _fake_geocoder_returning(match)
        with patch(
            "siege_utilities.geo.geocoding.Nominatim", return_value=fake,
        ), patch("siege_utilities.geo.geocoding.time.sleep"):
            assert get_coordinates("addr", server_url="http://x") == (12.34, 56.78)

    def test_empty_address_raises_value_error(self):
        with pytest.raises(ValueError):
            get_coordinates("")

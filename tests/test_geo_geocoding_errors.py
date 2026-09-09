"""Error-path coverage (SU-4b) for siege_utilities.geo.geocoding.

Forces the empty-address ValueError and the GeocodingError raised by
get_coordinates on an unparseable / incomplete Nominatim response, with the
geocoder layer monkeypatched (no network).
"""

import pytest

import siege_utilities.geo.geocoding as geocoding
from siege_utilities.geo.geocoding import (
    GeocodingError,
    get_coordinates,
    use_nominatim_geocoder,
)


def test_use_nominatim_geocoder_rejects_empty_address():
    with pytest.raises(ValueError) as exc_info:
        use_nominatim_geocoder("")
    assert "non-empty string" in str(exc_info.value)


def test_get_coordinates_rejects_empty_address():
    with pytest.raises(ValueError):
        get_coordinates("")


def test_get_coordinates_raises_on_non_json_response(monkeypatch):
    monkeypatch.setattr(geocoding, "use_nominatim_geocoder", lambda *a, **k: "<<not json>>")
    with pytest.raises(GeocodingError) as exc_info:
        get_coordinates("123 Main St")
    assert "Could not parse" in str(exc_info.value)


def test_get_coordinates_raises_on_missing_latlng(monkeypatch):
    monkeypatch.setattr(geocoding, "use_nominatim_geocoder", lambda *a, **k: '{"other": 1}')
    with pytest.raises(GeocodingError) as exc_info:
        get_coordinates("123 Main St")
    assert "missing lat/lng" in str(exc_info.value)

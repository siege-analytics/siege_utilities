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


def test_get_coordinates_accepts_numeric_string_coordinates(monkeypatch):
    monkeypatch.setattr(
        geocoding,
        "use_nominatim_geocoder",
        lambda *a, **k: '{"nominatim_lat": "38.9", "nominatim_lng": "-77.0"}',
    )
    assert get_coordinates("1600 Pennsylvania Ave") == (38.9, -77.0)


@pytest.mark.parametrize(
    "payload",
    [
        '{"nominatim_lat": "bad", "nominatim_lng": "-77.0"}',
        '{"nominatim_lat": "38.9", "nominatim_lng": "bad"}',
        '{"nominatim_lat": 999, "nominatim_lng": 0}',
        '{"nominatim_lat": 0, "nominatim_lng": 999}',
        '{"nominatim_lat": NaN, "nominatim_lng": 0}',
    ],
)
def test_get_coordinates_wraps_invalid_provider_coordinates(monkeypatch, payload):
    monkeypatch.setattr(geocoding, "use_nominatim_geocoder", lambda *a, **k: payload)
    with pytest.raises(GeocodingError):
        get_coordinates("123 Main St")


@pytest.mark.parametrize("max_retries", [False, True, 0, -1, "3", 3.5, None])
def test_use_nominatim_geocoder_validates_max_retries_before_geocoder(monkeypatch, max_retries):
    def fail_if_called(*args, **kwargs):
        raise AssertionError("Nominatim should not be constructed for invalid max_retries")

    monkeypatch.setattr(geocoding, "Nominatim", fail_if_called)
    with pytest.raises(ValueError, match="positive integer"):
        use_nominatim_geocoder("123 Main St", max_retries=max_retries)


@pytest.mark.parametrize("payload", ["[]", '"string"', "123"])
def test_get_coordinates_wraps_non_object_json_payload(monkeypatch, payload):
    monkeypatch.setattr(geocoding, "use_nominatim_geocoder", lambda *a, **k: payload)
    with pytest.raises(GeocodingError, match="must be an object"):
        get_coordinates("123 Main St")

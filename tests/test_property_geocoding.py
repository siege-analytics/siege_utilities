"""Property tests for geocoding — SU-1 invariants.

These tests verify that geocoding functions handle arbitrary inputs
without crashing and that outputs satisfy domain invariants.
"""

import pytest

hypothesis = pytest.importorskip("hypothesis")
from hypothesis import given, assume, settings, HealthCheck
import hypothesis.strategies as st


# Valid WGS84 coordinate ranges
latitudes = st.floats(min_value=-90, max_value=90, allow_nan=False, allow_infinity=False)
longitudes = st.floats(min_value=-180, max_value=180, allow_nan=False, allow_infinity=False)


class TestGetCoordinatesProperties:
    """Property tests for get_coordinates."""

    @given(st.text(max_size=200))
    @settings(suppress_health_check=[HealthCheck.too_slow], max_examples=50, deadline=None)
    def test_never_crashes_on_arbitrary_input(self, address):
        """get_coordinates must not raise unexpected exceptions on any string."""
        from siege_utilities.geo.geocoding import get_coordinates, GeocodingError

        try:
            get_coordinates(address)
        except (ValueError, TypeError, KeyError, AttributeError, GeocodingError):
            # GeocodingError is the documented typed failure (network/service
            # error, e.g. a 400 on a malformed query) -- graceful, not a crash.
            pass

    @given(latitudes, longitudes)
    @settings(max_examples=30, deadline=None)
    def test_coordinate_string_does_not_crash(self, lat, lon):
        """Coordinate-like strings should not crash the function."""
        from siege_utilities.geo.geocoding import get_coordinates, GeocodingError

        try:
            get_coordinates(f"{lat}, {lon}")
        except (ValueError, TypeError, KeyError, AttributeError, GeocodingError):
            # GeocodingError is the documented typed failure (network/service
            # error, e.g. a 400 on a malformed query) -- graceful, not a crash.
            pass


class TestNominatimGeocoderProperties:
    """Property tests for use_nominatim_geocoder."""

    @given(st.text(min_size=1, max_size=100))
    @settings(suppress_health_check=[HealthCheck.too_slow], max_examples=30, deadline=None)
    def test_never_crashes_on_arbitrary_query(self, query):
        """use_nominatim_geocoder must not raise unexpected exceptions."""
        from siege_utilities.geo.geocoding import use_nominatim_geocoder, GeocodingError

        try:
            use_nominatim_geocoder(query)
        except (ValueError, TypeError, KeyError, AttributeError, GeocodingError):
            # GeocodingError is the documented typed failure (network/service
            # error, e.g. a 400 on a malformed query) -- graceful, not a crash.
            pass

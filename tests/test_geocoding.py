# ================================================================
# FILE: test_geocoding.py
# ================================================================
"""
Tests for siege_utilities.geo.geocoding module.
These tests expose issues with geocoding functions.
"""
import pytest
import json
from unittest.mock import patch, Mock
import siege_utilities

# Skip tests if geopy is not available
pytest.importorskip("geopy", reason="geopy not available")


class TestGeocodingFunctions:
    """Test geocoding functionality and expose bugs."""

    def test_concatenate_addresses_full_address(self):
        """Test address concatenation with all components."""
        result = siege_utilities.concatenate_addresses(
            street="123 Main St",
            city="New York",
            state_province_area="NY",
            postal_code="10001",
            country="USA"
        )

        expected = "123 Main St, New York, NY, 10001, USA"
        assert result == expected

    def test_concatenate_addresses_partial_components(self):
        """Test address concatenation with missing components."""
        result = siege_utilities.concatenate_addresses(
            street="456 Oak Ave",
            city="Boston",
            country="USA"
            # Missing state and postal code
        )

        expected = "456 Oak Ave, Boston, USA"
        assert result == expected

    @patch('geopy.geocoders.Nominatim.geocode')
    @patch('time.sleep')
    def test_use_nominatim_geocoder_success(self, mock_sleep, mock_geocode):
        """Test successful geocoding with Nominatim."""
        # Create mock geocoding result
        mock_result = Mock()
        mock_result.latitude = 40.7128
        mock_result.longitude = -74.0060
        mock_result.raw = {
            'place_id': '123456',
            'display_name': 'New York, NY, USA',
            'lat': '40.7128',
            'lon': '-74.0060'
        }
        mock_geocode.return_value = mock_result

        address = "New York, NY"
        result = siege_utilities.use_nominatim_geocoder(address)

        assert result is not None

        # Parse the JSON result
        parsed = json.loads(result)
        assert parsed['nominatim_lat'] == 40.7128
        assert parsed['nominatim_lng'] == -74.0060
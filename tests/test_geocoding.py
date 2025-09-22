# ================================================================
# FILE: test_geocoding.py
# ================================================================
"""
Tests for siege_utilities.geo.geocoding module.
These tests expose issues with geocoding functions and test new country code functionality.
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


class TestCountryCodeFunctions:
    """Test new country code utility functions."""

    def test_get_country_name_valid_codes(self):
        """Test getting country names from valid country codes."""
        # Test major countries
        assert siege_utilities.get_country_name('us') == 'United States'
        assert siege_utilities.get_country_name('ca') == 'Canada'
        assert siege_utilities.get_country_name('gb') == 'United Kingdom'
        assert siege_utilities.get_country_name('de') == 'Germany'
        assert siege_utilities.get_country_name('fr') == 'France'
        assert siege_utilities.get_country_name('jp') == 'Japan'
        assert siege_utilities.get_country_name('au') == 'Australia'

    def test_get_country_name_case_insensitive(self):
        """Test that country code lookup is case insensitive."""
        assert siege_utilities.get_country_name('US') == 'United States'
        assert siege_utilities.get_country_name('Ca') == 'Canada'
        assert siege_utilities.get_country_name('GB') == 'United Kingdom'

    def test_get_country_name_invalid_code(self):
        """Test getting country name for invalid code returns the code."""
        assert siege_utilities.get_country_name('xx') == 'xx'
        assert siege_utilities.get_country_name('invalid') == 'invalid'

    def test_get_country_code_valid_names(self):
        """Test getting country codes from valid country names."""
        assert siege_utilities.get_country_code('United States') == 'us'
        assert siege_utilities.get_country_code('Canada') == 'ca'
        assert siege_utilities.get_country_code('United Kingdom') == 'gb'
        assert siege_utilities.get_country_code('Germany') == 'de'
        assert siege_utilities.get_country_code('France') == 'fr'
        assert siege_utilities.get_country_code('Japan') == 'jp'
        assert siege_utilities.get_country_code('Australia') == 'au'

    def test_get_country_code_case_insensitive(self):
        """Test that country name lookup is case insensitive."""
        assert siege_utilities.get_country_code('united states') == 'us'
        assert siege_utilities.get_country_code('CANADA') == 'ca'
        assert siege_utilities.get_country_code('United Kingdom') == 'gb'

    def test_get_country_code_invalid_name(self):
        """Test getting country code for invalid name returns None."""
        assert siege_utilities.get_country_code('Invalid Country') is None
        assert siege_utilities.get_country_code('NonExistent') is None

    def test_list_countries_returns_dict(self):
        """Test that list_countries returns a dictionary."""
        countries = siege_utilities.list_countries()
        assert isinstance(countries, dict)
        assert len(countries) > 100  # Should have many countries

    def test_list_countries_contains_major_countries(self):
        """Test that list_countries contains major countries."""
        countries = siege_utilities.list_countries()
        assert 'us' in countries
        assert 'ca' in countries
        assert 'gb' in countries
        assert 'de' in countries
        assert 'fr' in countries
        assert 'jp' in countries
        assert 'au' in countries

    def test_list_countries_values_are_strings(self):
        """Test that all country values are strings."""
        countries = siege_utilities.list_countries()
        for code, name in countries.items():
            assert isinstance(code, str)
            assert isinstance(name, str)
            assert len(code) == 2  # Country codes should be 2 characters

    def test_country_code_consistency(self):
        """Test that country code lookups are consistent."""
        countries = siege_utilities.list_countries()
        
        # Test that get_country_name and get_country_code are inverse operations
        for code, name in countries.items():
            assert siege_utilities.get_country_name(code) == name
            assert siege_utilities.get_country_code(name) == code


class TestGetCoordinatesFunction:
    """Test the new get_coordinates function."""

    @patch('geopy.geocoders.Nominatim.geocode')
    @patch('time.sleep')
    def test_get_coordinates_success(self, mock_sleep, mock_geocode):
        """Test successful coordinate retrieval."""
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

        # Mock the use_nominatim_geocoder to return JSON
        with patch('siege_utilities.geo.geocoding.use_nominatim_geocoder') as mock_geocoder:
            mock_geocoder.return_value = json.dumps({
                'nominatim_lat': 40.7128,
                'nominatim_lng': -74.0060
            })

            coords = siege_utilities.get_coordinates('New York, NY')
            assert coords == (40.7128, -74.0060)

    @patch('siege_utilities.geo.geocoding.use_nominatim_geocoder')
    def test_get_coordinates_with_country_code(self, mock_geocoder):
        """Test coordinate retrieval with specific country code."""
        mock_geocoder.return_value = json.dumps({
            'nominatim_lat': 43.6532,
            'nominatim_lng': -79.3832
        })

        coords = siege_utilities.get_coordinates('Toronto', country_codes='ca')
        assert coords == (43.6532, -79.3832)
        mock_geocoder.assert_called_once_with('Toronto', country_codes='ca', max_retries=3)

    @patch('siege_utilities.geo.geocoding.use_nominatim_geocoder')
    def test_get_coordinates_no_result(self, mock_geocoder):
        """Test coordinate retrieval when no result is found."""
        mock_geocoder.return_value = None

        coords = siege_utilities.get_coordinates('NonExistentCity')
        assert coords is None

    @patch('siege_utilities.geo.geocoding.use_nominatim_geocoder')
    def test_get_coordinates_invalid_json(self, mock_geocoder):
        """Test coordinate retrieval with invalid JSON response."""
        mock_geocoder.return_value = "invalid json"

        coords = siege_utilities.get_coordinates('TestCity')
        assert coords is None

    @patch('siege_utilities.geo.geocoding.use_nominatim_geocoder')
    def test_get_coordinates_missing_coordinates(self, mock_geocoder):
        """Test coordinate retrieval when coordinates are missing from response."""
        mock_geocoder.return_value = json.dumps({
            'place_id': '123456',
            'display_name': 'Test City'
            # Missing nominatim_lat and nominatim_lng
        })

        coords = siege_utilities.get_coordinates('TestCity')
        assert coords is None

    @patch('siege_utilities.geo.geocoding.use_nominatim_geocoder')
    def test_get_coordinates_exception_handling(self, mock_geocoder):
        """Test coordinate retrieval exception handling."""
        mock_geocoder.side_effect = Exception("Geocoding service error")

        coords = siege_utilities.get_coordinates('TestCity')
        assert coords is None


class TestGeocodingWithCountryCodes:
    """Test geocoding functionality with different country codes."""

    @patch('geopy.geocoders.Nominatim.geocode')
    @patch('time.sleep')
    def test_geocoding_us_cities(self, mock_sleep, mock_geocode):
        """Test geocoding US cities."""
        mock_result = Mock()
        mock_result.latitude = 38.8951
        mock_result.longitude = -77.0364
        mock_result.raw = {'place_id': '123', 'lat': '38.8951', 'lon': '-77.0364'}
        mock_geocode.return_value = mock_result

        result = siege_utilities.use_nominatim_geocoder('Washington, DC', country_codes='us')
        assert result is not None
        parsed = json.loads(result)
        assert parsed['nominatim_lat'] == 38.8951
        assert parsed['nominatim_lng'] == -77.0364

    @patch('geopy.geocoders.Nominatim.geocode')
    @patch('time.sleep')
    def test_geocoding_canadian_cities(self, mock_sleep, mock_geocode):
        """Test geocoding Canadian cities."""
        mock_result = Mock()
        mock_result.latitude = 43.6532
        mock_result.longitude = -79.3832
        mock_result.raw = {'place_id': '456', 'lat': '43.6532', 'lon': '-79.3832'}
        mock_geocode.return_value = mock_result

        result = siege_utilities.use_nominatim_geocoder('Toronto', country_codes='ca')
        assert result is not None
        parsed = json.loads(result)
        assert parsed['nominatim_lat'] == 43.6532
        assert parsed['nominatim_lng'] == -79.3832

    @patch('geopy.geocoders.Nominatim.geocode')
    @patch('time.sleep')
    def test_geocoding_uk_cities(self, mock_sleep, mock_geocode):
        """Test geocoding UK cities."""
        mock_result = Mock()
        mock_result.latitude = 51.5074
        mock_result.longitude = -0.1278
        mock_result.raw = {'place_id': '789', 'lat': '51.5074', 'lon': '-0.1278'}
        mock_geocode.return_value = mock_result

        result = siege_utilities.use_nominatim_geocoder('London', country_codes='gb')
        assert result is not None
        parsed = json.loads(result)
        assert parsed['nominatim_lat'] == 51.5074
        assert parsed['nominatim_lng'] == -0.1278

    def test_default_country_code(self):
        """Test that the default country code is US."""
        from siege_utilities.geo.geocoding import DEFAULT_COUNTRY_CODE
        assert DEFAULT_COUNTRY_CODE == 'us'

    def test_geocoder_config_uses_default_country(self):
        """Test that the geocoder config uses the default country code."""
        from siege_utilities.geo.geocoding import GEOCODER_CONFIG, DEFAULT_COUNTRY_CODE
        assert GEOCODER_CONFIG['country_codes'] == DEFAULT_COUNTRY_CODE
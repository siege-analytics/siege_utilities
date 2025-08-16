"""
Comprehensive tests for enhanced Census utilities.

Tests the dynamic discovery system, data source functionality, and all new features.
"""

import pytest
import sys
import os
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from siege_utilities.geo.spatial_data import (
    CensusDirectoryDiscovery, 
    CensusDataSource,
    SpatialDataSource
)


class TestCensusDirectoryDiscovery:
    """Test the Census directory discovery functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.discovery = CensusDirectoryDiscovery()
        self.mock_html_content = """
        <html>
            <body>
                <a href="TIGER1990/">TIGER1990</a>
                <a href="TIGER2000/">TIGER2000</a>
                <a href="TIGER2010/">TIGER2010</a>
                <a href="TIGER2020/">TIGER2020</a>
                <a href="TIGER2024/">TIGER2024</a>
                <a href="GENZ2010/">GENZ2010</a>
                <a href="GENZ2020/">GENZ2020</a>
                <a href="TGRGDB13/">TGRGDB13</a>
                <a href="TGRGDB24/">TGRGDB24</a>
                <a href="TGRGPKG24/">TGRGPKG24</a>
                <a href="TGRGPKG25/">TGRGPKG25</a>
                <a href="other_dir/">other_dir</a>
            </body>
        </html>
        """
    
    @patch('requests.get')
    def test_get_available_years_success(self, mock_get):
        """Test successful year discovery."""
        mock_response = Mock()
        mock_response.content = self.mock_html_content.encode()
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        years = self.discovery.get_available_years()
        
        assert 1990 in years
        assert 2000 in years
        assert 2010 in years
        assert 2020 in years
        assert 2024 in years
        assert 2013 in years  # TGRGDB13 -> 2013
        assert 2024 in years  # TGRGDB24 -> 2024
        assert 2024 in years  # TGRGPKG24 -> 2024
        assert 2025 in years  # TGRGPKG25 -> 2025
        assert len(years) > 0
        assert years == sorted(years)  # Should be sorted
    
    @patch('requests.get')
    def test_get_available_years_fallback(self, mock_get):
        """Test fallback when discovery fails."""
        mock_get.side_effect = Exception("Network error")
        
        years = self.discovery.get_available_years()
        
        # Should fall back to known years
        assert len(years) > 0
        assert all(2010 <= year <= 2025 for year in years)
    
    @patch('requests.get')
    def test_get_year_directory_contents(self, mock_get):
        """Test getting directory contents for a specific year."""
        mock_response = Mock()
        mock_response.content = """
        <html>
            <body>
                <a href="../">../</a>
                <a href="STATE/">STATE</a>
                <a href="COUNTY/">COUNTY</a>
                <a href="TRACT/">TRACT</a>
                <a href="BG/">BG</a>
                <a href="TABBLOCK20/">TABBLOCK20</a>
                <a href="PLACE/">PLACE</a>
                <a href="ZCTA5/">ZCTA5</a>
            </body>
        </html>
        """.encode()
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        contents = self.discovery.get_year_directory_contents(2020)
        
        assert 'STATE' in contents
        assert 'COUNTY' in contents
        assert 'TRACT' in contents
        assert 'BG' in contents
        assert 'TABBLOCK20' in contents
        assert 'PLACE' in contents
        assert 'ZCTA5' in contents
        assert '../' not in contents  # Should exclude parent directory
    
    def test_discover_boundary_types(self):
        """Test boundary type discovery."""
        # Mock the directory contents
        self.discovery.get_year_directory_contents = Mock(return_value=[
            'STATE', 'COUNTY', 'TRACT', 'BG', 'TABBLOCK20', 'PLACE', 'ZCTA5'
        ])
        
        boundary_types = self.discovery.discover_boundary_types(2020)
        
        assert 'state' in boundary_types
        assert 'county' in boundary_types
        assert 'tract' in boundary_types
        assert 'block_group' in boundary_types
        assert 'tabblock20' in boundary_types
        assert 'place' in boundary_types
        assert 'zcta' in boundary_types
    
    def test_construct_download_url_national(self):
        """Test URL construction for national-level boundaries."""
        # Mock available boundary types
        self.discovery.discover_boundary_types = Mock(return_value={
            'state': 'STATE',
            'county': 'COUNTY',
            'place': 'PLACE'
        })
        
        # Test state boundaries
        url = self.discovery.construct_download_url(2020, 'state')
        assert url == "https://www2.census.gov/geo/tiger/TIGER2020/STATE/tl_2020_us_state.zip"
        
        # Test county boundaries
        url = self.discovery.construct_download_url(2020, 'county')
        assert url == "https://www2.census.gov/geo/tiger/TIGER2020/COUNTY/tl_2020_us_county.zip"
    
    def test_construct_download_url_state_specific(self):
        """Test URL construction for state-specific boundaries."""
        # Mock available boundary types
        self.discovery.discover_boundary_types = Mock(return_value={
            'tract': 'TRACT',
            'block_group': 'BG',
            'tabblock20': 'TABBLOCK20'
        })
        
        # Test tract boundaries for California (FIPS 06)
        url = self.discovery.construct_download_url(2020, 'tract', state_fips='06')
        assert url == "https://www2.census.gov/geo/tiger/TIGER2020/TRACT/tl_2020_06_tract.zip"
        
        # Test block groups for Texas (FIPS 48)
        url = self.discovery.construct_download_url(2020, 'block_group', state_fips='48')
        assert url == "https://www2.census.gov/geo/tiger/TIGER2020/BG/tl_2020_48_block_group.zip"
    
    def test_construct_download_url_congressional_districts(self):
        """Test URL construction for congressional districts."""
        # Mock available boundary types
        self.discovery.discover_boundary_types = Mock(return_value={
            'cd': 'CD',
            'cd118': 'CD118'
        })
        
        # Test with congress number parameter
        url = self.discovery.construct_download_url(2020, 'cd', congress_number=118)
        assert url == "https://www2.census.gov/geo/tiger/TIGER2020/CD/tl_2020_us_cd118.zip"
        
        # Test with specific congress number in boundary type
        url = self.discovery.construct_download_url(2020, 'cd118')
        assert url == "https://www2.census.gov/geo/tiger/TIGER2020/CD118/tl_2020_us_cd118.zip"
    
    def test_construct_download_url_unknown_type(self):
        """Test URL construction for unknown boundary types."""
        # Mock available boundary types
        self.discovery.discover_boundary_types = Mock(return_value={
            'custom': 'CUSTOM'
        })
        
        # Test custom boundary type
        url = self.discovery.construct_download_url(2020, 'custom')
        assert url == "https://www2.census.gov/geo/tiger/TIGER2020/CUSTOM/tl_2020_us_custom.zip"
    
    def test_get_optimal_year(self):
        """Test finding the optimal year when requested year isn't available."""
        # Mock available years
        self.discovery.get_available_years = Mock(return_value=[2010, 2015, 2020, 2024])
        
        # Request 2018, should get 2020 (closest)
        optimal = self.discovery.get_optimal_year(2018, 'county')
        assert optimal == 2020
        
        # Request 2012, should get 2010 (closest)
        optimal = self.discovery.get_optimal_year(2012, 'county')
        assert optimal == 2010
        
        # Request 2025, should get 2024 (closest)
        optimal = self.discovery.get_optimal_year(2025, 'county')
        assert optimal == 2024
    
    @patch('requests.head')
    def test_validate_download_url_success(self, mock_head):
        """Test successful URL validation."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_head.return_value = mock_response
        
        is_valid = self.discovery.validate_download_url("https://example.com/test.zip")
        assert is_valid is True
    
    @patch('requests.head')
    def test_validate_download_url_failure(self, mock_head):
        """Test failed URL validation."""
        mock_head.side_effect = Exception("Network error")
        
        is_valid = self.discovery.validate_download_url("https://example.com/test.zip")
        assert is_valid is False


class TestCensusDataSource:
    """Test the Census data source functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.census = CensusDataSource()
    
    def test_initialization(self):
        """Test CensusDataSource initialization."""
        assert self.census.name == "Census Bureau"
        assert self.census.base_url == "https://www2.census.gov/geo/tiger"
        assert hasattr(self.census, 'discovery')
        assert hasattr(self.census, 'available_years')
        assert hasattr(self.census, 'state_required_levels')
        assert hasattr(self.census, 'national_levels')
    
    def test_get_available_state_fips(self):
        """Test getting available state FIPS codes."""
        fips_codes = self.census.get_available_state_fips()
        
        assert '06' in fips_codes  # California
        assert '48' in fips_codes  # Texas
        assert '36' in fips_codes  # New York
        assert fips_codes['06'] == 'California'
        assert fips_codes['48'] == 'Texas'
        assert fips_codes['36'] == 'New York'
    
    def test_validate_state_fips(self):
        """Test state FIPS validation."""
        assert self.census.validate_state_fips('06') is True   # California
        assert self.census.validate_state_fips('48') is True   # Texas
        assert self.census.validate_state_fips('99') is False  # Invalid
        assert self.census.validate_state_fips('ABC') is False # Invalid
    
    def test_get_state_name(self):
        """Test getting state name from FIPS code."""
        assert self.census.get_state_name('06') == 'California'
        assert self.census.get_state_name('48') == 'Texas'
        assert self.census.get_state_name('99') is None  # Invalid
    
    def test_get_available_boundary_types(self):
        """Test getting available boundary types for a year."""
        # Mock the discovery method
        self.census.discovery.discover_boundary_types = Mock(return_value={
            'state': 'STATE',
            'county': 'COUNTY',
            'tract': 'TRACT'
        })
        
        boundary_types = self.census.get_available_boundary_types(2020)
        
        assert 'state' in boundary_types
        assert 'county' in boundary_types
        assert 'tract' in boundary_types
    
    def test_parameter_validation_valid(self):
        """Test parameter validation with valid parameters."""
        # Mock discovery to return valid boundary types
        self.census.discovery.discover_boundary_types = Mock(return_value={
            'county': 'COUNTY'
        })
        
        # This should not raise an exception
        self.census._validate_census_parameters(2020, 'county', None)
    
    def test_parameter_validation_invalid_year(self):
        """Test parameter validation with invalid year."""
        with pytest.raises(ValueError, match="Year 1800 is outside valid range"):
            self.census._validate_census_parameters(1800, 'county', None)
    
    def test_parameter_validation_missing_state_fips(self):
        """Test parameter validation when state FIPS is required but missing."""
        with pytest.raises(ValueError, match="State FIPS required for tract-level data"):
            self.census._validate_census_parameters(2020, 'tract', None)
    
    def test_parameter_validation_invalid_state_fips(self):
        """Test parameter validation with invalid state FIPS."""
        with pytest.raises(ValueError, match="Invalid state FIPS code: 99"):
            self.census._validate_census_parameters(2020, 'tract', '99')
    
    def test_parameter_validation_invalid_geographic_level(self):
        """Test parameter validation with invalid geographic level."""
        # Mock discovery to return limited boundary types
        self.census.discovery.discover_boundary_types = Mock(return_value={
            'state': 'STATE',
            'county': 'COUNTY'
        })
        
        with pytest.raises(ValueError, match="Invalid geographic level: invalid_level"):
            self.census._validate_census_parameters(2020, 'invalid_level', None)
    
    def test_refresh_discovery_cache(self):
        """Test refreshing the discovery cache."""
        # Mock the discovery methods
        self.census.discovery.cache = {'test': 'data'}
        self.census.discovery.get_available_years = Mock(return_value=[2020, 2024])
        
        self.census.refresh_discovery_cache()
        
        # Cache should be cleared
        assert self.census.discovery.cache == {}
        # Available years should be refreshed
        assert self.census.available_years == [2020, 2024]


class TestSpatialDataSource:
    """Test the base spatial data source class."""
    
    def test_initialization(self):
        """Test SpatialDataSource initialization."""
        source = SpatialDataSource("Test Source", "https://example.com")
        
        assert source.name == "Test Source"
        assert source.base_url == "https://example.com"
        assert source.api_key is None
    
    def test_initialization_with_api_key(self):
        """Test SpatialDataSource initialization with API key."""
        source = SpatialDataSource("Test Source", "https://example.com", "test_key")
        
        assert source.name == "Test Source"
        assert source.base_url == "https://example.com"
        assert source.api_key == "test_key"
    
    def test_download_data_not_implemented(self):
        """Test that download_data raises NotImplementedError."""
        source = SpatialDataSource("Test Source", "https://example.com")
        
        with pytest.raises(NotImplementedError):
            source.download_data()


# Integration tests
class TestCensusIntegration:
    """Integration tests for Census utilities."""
    
    @pytest.mark.integration
    def test_full_census_workflow(self):
        """Test the complete Census data workflow."""
        # This test would require actual network access
        # Marked as integration test to be run separately
        pass
    
    @pytest.mark.integration
    def test_census_discovery_real_data(self):
        """Test Census discovery with real Census Bureau data."""
        # This test would require actual network access
        # Marked as integration test to be run separately
        pass


if __name__ == "__main__":
    pytest.main([__file__])

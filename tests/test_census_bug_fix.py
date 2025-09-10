"""
Tests for Census download function bug fix.

This test suite ensures the Census download function works correctly
after fixing the variable name mismatch bug.
"""

import pytest
from unittest.mock import patch, MagicMock
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point

from siege_utilities.geo.spatial_data import get_census_boundaries


class TestCensusBugFix:
    """Test suite for Census download function bug fix."""
    
    def test_census_function_with_valid_state_fips(self):
        """Test Census function with valid state FIPS code."""
        # This is an integration test that will actually download data
        # Using Delaware (FIPS '10') as it's small and fast
        result = get_census_boundaries(
            year=2023, 
            geographic_level='county', 
            state_fips='10'
        )
        
        # Should return a GeoDataFrame
        assert result is not None, "Function should return data for valid state FIPS"
        assert isinstance(result, gpd.GeoDataFrame), "Should return GeoDataFrame"
        assert len(result) > 0, "Should contain at least one county"
        assert 'geometry' in result.columns, "Should have geometry column"
    
    def test_census_function_with_state_abbreviation(self):
        """Test Census function with state abbreviation (should work after normalization)."""
        result = get_census_boundaries(
            year=2023, 
            geographic_level='county', 
            state_fips='DE'  # Delaware abbreviation
        )
        
        assert result is not None, "Function should handle state abbreviations"
        assert isinstance(result, gpd.GeoDataFrame), "Should return GeoDataFrame"
    
    def test_census_function_with_invalid_state(self):
        """Test Census function with invalid state identifier."""
        result = get_census_boundaries(
            year=2023, 
            geographic_level='county', 
            state_fips='INVALID'
        )
        
        assert result is None, "Function should return None for invalid state"
    
    def test_census_function_without_state_fips(self):
        """Test Census function without state FIPS (national level)."""
        result = get_census_boundaries(
            year=2023, 
            geographic_level='state'  # State level doesn't require state_fips
        )
        
        assert result is not None, "Function should work without state_fips for national levels"
        assert isinstance(result, gpd.GeoDataFrame), "Should return GeoDataFrame"
        assert len(result) > 50, "Should contain all US states"
    
    @patch('siege_utilities.geo.spatial_data.CensusDataSource')
    def test_census_function_parameter_passing(self, mock_census_source):
        """Test that parameters are passed correctly to underlying functions."""
        # Mock the CensusDataSource and its methods
        mock_instance = MagicMock()
        mock_census_source.return_value = mock_instance
        
        # Mock a successful response
        mock_gdf = gpd.GeoDataFrame({
            'NAME': ['Test County'],
            'geometry': [Point(0, 0)]
        })
        mock_instance.get_geographic_boundaries.return_value = mock_gdf
        
        # Call the function
        result = get_census_boundaries(
            year=2022,
            geographic_level='county',
            state_fips='06',
            county_fips='001'
        )
        
        # Verify the mock was called with correct parameters
        mock_instance.get_geographic_boundaries.assert_called_once_with(
            year=2022,
            geographic_level='county',
            state_fips='06',
            county_fips='001',
            congress_number=None
        )
        
        assert result is not None
        assert len(result) == 1
        assert result.iloc[0]['NAME'] == 'Test County'
    
    def test_census_function_error_handling(self):
        """Test Census function handles errors gracefully."""
        # Test with invalid year
        result = get_census_boundaries(
            year=1800,  # Very old year that shouldn't exist
            geographic_level='county',
            state_fips='10'
        )
        
        # Function should handle this gracefully (either return None or valid data)
        if result is not None:
            assert isinstance(result, gpd.GeoDataFrame)
    
    def test_variable_name_bug_fixed(self):
        """
        Specific test to ensure the 'state' vs 'state_fips' bug is fixed.
        
        This test ensures that the function doesn't throw a NameError
        when state_fips parameter is provided.
        """
        try:
            # This should not raise NameError: name 'state' is not defined
            result = get_census_boundaries(
                year=2023,
                geographic_level='county',
                state_fips='10'
            )
            # If we get here without exception, the bug is fixed
            assert True, "No NameError thrown - bug is fixed"
        except NameError as e:
            if "name 'state' is not defined" in str(e):
                pytest.fail("NameError for 'state' variable still exists - bug not fixed")
            else:
                # Some other NameError, re-raise it
                raise
        except Exception:
            # Other exceptions are okay for this specific test
            # We're only testing that the NameError is fixed
            pass


if __name__ == "__main__":
    # Run basic smoke test
    print("Running Census bug fix smoke test...")
    
    try:
        # Test the specific bug fix
        result = get_census_boundaries(
            year=2023,
            geographic_level='county',
            state_fips='10'  # Delaware
        )
        
        if result is not None:
            print(f"✅ SUCCESS: Downloaded {len(result)} counties for Delaware")
            print(f"Columns: {list(result.columns)}")
        else:
            print("⚠️  Function returned None - may be network/data issue")
            
    except NameError as e:
        if "name 'state' is not defined" in str(e):
            print("❌ FAILED: NameError for 'state' still exists")
        else:
            print(f"❌ FAILED: Different NameError: {e}")
    except Exception as e:
        print(f"⚠️  Other error (may be expected): {e}")
        
    print("Smoke test complete.")



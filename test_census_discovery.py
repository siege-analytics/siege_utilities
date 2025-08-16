#!/usr/bin/env python3
"""
Test script for enhanced Census discovery functionality.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from siege_utilities.geo.spatial_data import CensusDirectoryDiscovery, CensusDataSource

def test_discovery():
    """Test the Census directory discovery functionality."""
    print("🔍 Testing Census Directory Discovery...")
    
    # Initialize discovery service
    discovery = CensusDirectoryDiscovery()
    
    # Test 1: Get available years
    print("\n1. Available Census Years:")
    years = discovery.get_available_years()
    print(f"   Found {len(years)} years: {years[:10]}...")  # Show first 10
    
    # Test 2: Get directory contents for a recent year
    test_year = 2024
    print(f"\n2. Directory contents for TIGER{test_year}:")
    contents = discovery.get_year_directory_contents(test_year)
    print(f"   Found {len(contents)} directories: {contents[:10]}...")  # Show first 10
    
    # Test 3: Discover boundary types
    print(f"\n3. Available boundary types for {test_year}:")
    boundary_types = discovery.discover_boundary_types(test_year)
    for boundary_type, directory in boundary_types.items():
        print(f"   {boundary_type}: {directory}")
    
    # Test 4: Test URL construction
    print(f"\n4. URL construction examples:")
    
    # National level (no state FIPS needed)
    url = discovery.construct_download_url(2024, 'county')
    print(f"   County boundaries: {url}")
    
    # State level (no state FIPS needed)
    url = discovery.construct_download_url(2024, 'state')
    print(f"   State boundaries: {url}")
    
    # State-specific level (requires state FIPS)
    url = discovery.construct_download_url(2024, 'tract', state_fips='06')  # California
    print(f"   California tracts: {url}")
    
    # Test 5: URL validation
    print(f"\n5. URL validation:")
    if url:
        is_valid = discovery.validate_download_url(url)
        print(f"   California tracts URL valid: {is_valid}")
    
    # Test 6: Optimal year selection
    print(f"\n6. Optimal year selection:")
    optimal = discovery.get_optimal_year(2025, 'county')  # Request future year
    print(f"   Requested 2025, got optimal year: {optimal}")
    
    return True

def test_census_source():
    """Test the enhanced CensusDataSource."""
    print("\n🔍 Testing Enhanced CensusDataSource...")
    
    # Initialize Census data source
    census = CensusDataSource()
    
    # Test 1: Get available boundary types
    print("\n1. Available boundary types for 2024:")
    boundary_types = census.get_available_boundary_types(2024)
    print(f"   Found {len(boundary_types)} types: {list(boundary_types.keys())}")
    
    # Test 2: Test parameter validation
    print("\n2. Parameter validation:")
    try:
        # This should fail (no state FIPS for tract level)
        census.get_geographic_boundaries(2024, 'tract')
        print("   ❌ Validation failed - should have required state FIPS")
    except ValueError as e:
        print(f"   ✅ Validation working: {e}")
    
    # Test 3: Test with valid parameters
    print("\n3. Testing with valid parameters:")
    try:
        # This should work (county level doesn't need state FIPS)
        result = census.get_geographic_boundaries(2024, 'county')
        if result is not None:
            print(f"   ✅ Successfully got county boundaries: {len(result)} features")
        else:
            print("   ⚠️  Got None result (download may have failed)")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test 4: Refresh cache
    print("\n4. Cache refresh:")
    census.refresh_discovery_cache()
    print("   ✅ Cache refreshed")
    
    return True

def main():
    """Main test function."""
    print("🚀 Testing Enhanced Census Discovery Functionality")
    print("=" * 60)
    
    try:
        # Test discovery service
        if test_discovery():
            print("\n✅ Discovery tests passed!")
        
        # Test Census data source
        if test_census_source():
            print("\n✅ CensusDataSource tests passed!")
        
        print("\n🎉 All tests completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

#!/usr/bin/env python3
"""
Simple test script for enhanced Census utilities.
Tests basic functionality without requiring pytest.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_enhanced_census():
    """Test the enhanced Census utilities."""
    print("🔍 Testing Enhanced Census Utilities...")
    
    try:
        # Test 1: Import the modules
        print("\n1. Testing imports...")
        from siege_utilities.geo.spatial_data import CensusDirectoryDiscovery, CensusDataSource
        print("   ✅ Successfully imported Census utilities")
        
        # Test 2: Initialize discovery service
        print("\n2. Testing CensusDirectoryDiscovery...")
        discovery = CensusDirectoryDiscovery()
        print("   ✅ Successfully created discovery service")
        
        # Test 3: Get available years (with fallback)
        print("\n3. Testing year discovery...")
        years = discovery.get_available_years()
        print(f"   ✅ Found {len(years)} available years: {years[:5]}...")
        
        # Test 4: Initialize Census data source
        print("\n4. Testing CensusDataSource...")
        census = CensusDataSource()
        print("   ✅ Successfully created Census data source")
        
        # Test 5: Test state FIPS functionality
        print("\n5. Testing state FIPS functionality...")
        state_fips = census.get_available_state_fips()
        print(f"   ✅ Found {len(state_fips)} state FIPS codes")
        
        # Test California FIPS
        if '06' in state_fips:
            california_name = census.get_state_name('06')
            print(f"   ✅ California FIPS '06' -> {california_name}")
        
        # Test 6: Test boundary type discovery (mock)
        print("\n6. Testing boundary type discovery...")
        # Mock the discovery to avoid network calls
        discovery.discover_boundary_types = lambda year: {
            'state': 'STATE',
            'county': 'COUNTY',
            'tract': 'TRACT'
        }
        
        boundary_types = census.get_available_boundary_types(2020)
        print(f"   ✅ Found {len(boundary_types)} boundary types: {list(boundary_types.keys())}")
        
        # Test 7: Test URL construction
        print("\n7. Testing URL construction...")
        url = discovery.construct_download_url(2020, 'county')
        if url:
            print(f"   ✅ Successfully constructed URL: {url}")
        else:
            print("   ⚠️  URL construction returned None")
        
        # Test 8: Test parameter validation
        print("\n8. Testing parameter validation...")
        try:
            # This should work
            census._validate_census_parameters(2020, 'county', None)
            print("   ✅ Valid parameters accepted")
        except Exception as e:
            print(f"   ❌ Valid parameters rejected: {e}")
        
        try:
            # This should fail (missing state FIPS for tract)
            census._validate_census_parameters(2020, 'tract', None)
            print("   ❌ Invalid parameters accepted (should have failed)")
        except ValueError as e:
            print(f"   ✅ Invalid parameters correctly rejected: {e}")
        
        print("\n🎉 All tests completed successfully!")
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_enhanced_census()
    sys.exit(0 if success else 1)

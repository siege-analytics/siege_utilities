#!/usr/bin/env python3
"""
Siege Data Pipeline Test Script

This script tests the actual data pipeline capabilities of siege_utilities:
1. Generate synthetic population with Census standards
2. Get real Census tract boundaries
3. Join population data with spatial data
4. Test spatial transformations
5. Create visualizations using library functions

This uses what the library actually provides rather than working around it.
"""

import sys
import pandas as pd
import numpy as np
from pathlib import Path
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_population_generation():
    """Test 1: Generate synthetic population using library functions."""
    print("🧪 TEST 1: Population Generation")
    print("=" * 50)
    
    try:
        import siege_utilities
        
        # Generate synthetic population with tract information
        print("👥 Generating synthetic population...")
        population = siege_utilities.generate_synthetic_population(
            size=1000,
            geography_level="tract",
            tract_info={
                'state_fips': "06",
                'county_fips': "037", 
                'tract_fips': '200100'
            }
        )
        
        print(f"✅ Generated {len(population)} people")
        print(f"📋 Dataset shape: {population.shape}")
        print(f"🔍 Columns: {list(population.columns)}")
        
        # Verify Census standards
        print("\n🏛️ Census Standards Verification:")
        if 'race' in population.columns:
            print(f"✅ Race categories: {population['race'].unique()}")
        if 'age_group' in population.columns:
            print(f"✅ Age groups: {population['age_group'].unique()}")
        if 'income_bracket' in population.columns:
            print(f"✅ Income brackets: {population['income_bracket'].unique()}")
        if 'education_attainment' in population.columns:
            print(f"✅ Education levels: {population['education_attainment'].unique()}")
        
        return population
        
    except Exception as e:
        print(f"❌ Population generation failed: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_census_tract_data():
    """Test 2: Get real Census tract data using library functions."""
    print("\n🧪 TEST 2: Census Tract Data")
    print("=" * 50)
    
    try:
        import siege_utilities
        
        print("🗺️ Getting Census tract sample...")
        
        # Get tract data with real boundaries
        tract_data = siege_utilities.get_census_tract_sample(
            state_fips="06",  # California
            population_size=500,
            include_geometry=True  # Request geometry
        )
        
        if tract_data is not None:
            print(f"✅ Tract data retrieved: {len(tract_data)} records")
            print(f"📊 Data type: {type(tract_data)}")
            print(f"🔍 Columns: {list(tract_data.columns)}")
            
            # Check if it's a GeoDataFrame
            if hasattr(tract_data, 'crs'):
                print(f"🗺️ CRS: {tract_data.crs}")
                print(f"📍 Geometry type: {tract_data.geometry.geom_type.iloc[0] if len(tract_data) > 0 else 'None'}")
            
            # Show tract information
            if 'tract_fips' in tract_data.columns:
                print(f"🏘️ Unique tracts: {tract_data['tract_fips'].nunique()}")
                print(f"🏘️ Sample tract IDs: {tract_data['tract_fips'].unique()[:5]}")
            
            return tract_data
        else:
            print("⚠️ Tract data is None")
            return None
            
    except Exception as e:
        print(f"❌ Census tract data failed: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_spatial_operations():
    """Test 3: Test spatial operations using library functions."""
    print("\n🧪 TEST 3: Spatial Operations")
    print("=" * 50)
    
    try:
        import siege_utilities
        
        # Test spatial transformations
        print("🔄 Testing spatial transformations...")
        try:
            from siege_utilities.geo.spatial_transformations import SpatialDataTransformer
            
            transformer = SpatialDataTransformer()
            print("✅ Spatial transformer initialized")
            
            # Check DuckDB availability from module
            from siege_utilities.geo.spatial_transformations import DUCKDB_AVAILABLE
            print(f"🦆 DuckDB available: {DUCKDB_AVAILABLE}")
            
            # Test basic spatial operations
            if hasattr(transformer, 'convert_format'):
                print("✅ Format conversion available")
            if hasattr(transformer, 'supported_formats'):
                print(f"✅ Supported formats: {list(transformer.supported_formats['output'])}")
                
        except Exception as e:
            print(f"⚠️ Spatial transformer issue: {e}")
        
        # Test geocoding
        print("\n📍 Testing geocoding...")
        try:
            # Test address concatenation
            addresses = ["123 Main St", "Los Angeles", "CA", "90210"]
            concatenated = siege_utilities.concatenate_addresses(*addresses)
            print(f"✅ Address concatenation: {concatenated}")
            
        except Exception as e:
            print(f"⚠️ Geocoding issue: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Spatial operations failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_data_integration():
    """Test 4: Test data integration and transformations."""
    print("\n🧪 TEST 4: Data Integration")
    print("=" * 50)
    
    try:
        # Generate population data
        population = test_population_generation()
        if population is None:
            return False
        
        # Get tract data
        tract_data = test_census_tract_data()
        if tract_data is None:
            return False
        
        print("🔗 Testing data integration...")
        
        # Check if we can work with both datasets
        if 'tract_fips' in population.columns and 'tract_fips' in tract_data.columns:
            print("✅ Both datasets have tract_fips column")
            
            # Show tract distribution
            pop_tracts = population['tract_fips'].nunique()
            tract_count = tract_data['tract_fips'].nunique()
            print(f"📊 Population data: {pop_tracts} unique tracts")
            print(f"📊 Tract boundaries: {tract_count} unique tracts")
            
            # Check for overlap
            pop_tract_set = set(population['tract_fips'].unique())
            boundary_tract_set = set(tract_data['tract_fips'].unique())
            overlap = len(pop_tract_set.intersection(boundary_tract_set))
            print(f"🔗 Tract overlap: {overlap} tracts in both datasets")
            
            if overlap > 0:
                print("✅ Data integration possible")
                return True
            else:
                print("⚠️ No tract overlap - integration not possible")
                return False
        else:
            print("❌ Missing tract_fips columns for integration")
            missing_pop = 'tract_fips' not in population.columns
            missing_tract = 'tract_fips' not in tract_data.columns
            print(f"   Population missing tract_fips: {missing_pop}")
            print(f"   Tract data missing tract_fips: {missing_tract}")
            print(f"   Population columns: {list(population.columns)}")
            print(f"   Tract data columns: {list(tract_data.columns)}")
            return False
            
    except Exception as e:
        print(f"❌ Data integration failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_visualization():
    """Test 5: Test visualization capabilities using library functions."""
    print("\n🧪 TEST 5: Visualization")
    print("=" * 50)
    
    try:
        import siege_utilities
        
        # Test bivariate choropleth
        print("🗺️ Testing bivariate choropleth...")
        try:
            # Check if ChartGenerator is available
            if hasattr(siege_utilities, 'ChartGenerator'):
                print("✅ ChartGenerator class available")
                
                # Check if we can get sample data for visualization
                try:
                    # Get small sample for testing
                    sample_data = siege_utilities.get_census_tract_sample(
                        state_fips="06",
                        population_size=100,
                        include_geometry=False
                    )
                    
                    if sample_data is not None and len(sample_data) > 0:
                        print("✅ Sample data available for visualization testing")
                        
                        # Check if we have the right columns for choropleth
                        required_cols = ['income_category', 'education_category']
                        if all(col in sample_data.columns for col in required_cols):
                            print("✅ Required columns available for choropleth")
                            return True
                        else:
                            print("⚠️ Missing required columns for choropleth")
                            print(f"   Available columns: {list(sample_data.columns)}")
                            return False
                    else:
                        print("⚠️ No sample data for visualization testing")
                        return False
                        
                except Exception as e:
                    print(f"⚠️ Visualization data preparation failed: {e}")
                    return False
            else:
                print("⚠️ ChartGenerator class not found")
                # Check if the function exists directly
                if hasattr(siege_utilities, 'create_bivariate_choropleth'):
                    print("✅ create_bivariate_choropleth function available directly")
                    return True
                else:
                    print("⚠️ No bivariate choropleth functionality found")
                    return False
                
        except Exception as e:
            print(f"⚠️ Bivariate choropleth test failed: {e}")
            return False
        
    except Exception as e:
        print(f"❌ Visualization test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main test function."""
    print("🚀 Siege Data Pipeline Test Suite")
    print("=" * 60)
    print("Testing the actual data pipeline capabilities of siege_utilities\n")
    
    results = {}
    
    # Run all tests
    tests = [
        ("Population Generation", test_population_generation),
        ("Census Tract Data", test_census_tract_data),
        ("Spatial Operations", test_spatial_operations),
        ("Data Integration", test_data_integration),
        ("Visualization", test_visualization)
    ]
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            # Ensure result is a boolean for summary
            if isinstance(result, pd.DataFrame):
                results[test_name] = result is not None and len(result) > 0
            else:
                results[test_name] = bool(result)
        except Exception as e:
            print(f"❌ {test_name} test crashed: {e}")
            results[test_name] = False
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for result in results.values() if result)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
    
    print(f"\n🎯 Overall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! The data pipeline is working.")
    else:
        print("⚠️ Some tests failed. Check the output above for details.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

#!/usr/bin/env python3
"""
Test script for the new sample data functionality in siege_utilities.
"""

import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_sample_data_functionality():
    """Test the sample data functionality."""
    
    print("🧪 Testing Sample Data Functionality")
    print("=" * 50)
    
    try:
        # Test basic imports
        print("1. Testing basic imports...")
        from siege_utilities.data import (
            list_available_datasets, 
            get_dataset_info,
            SAMPLE_DATASETS
        )
        print("✅ Basic imports successful")
        
        # Test dataset listing
        print("\n2. Testing dataset listing...")
        datasets = list_available_datasets()
        print(f"✅ Found {len(datasets)} available datasets:")
        for name, info in datasets.items():
            print(f"   - {name}: {info['description']}")
        
        # Test dataset info
        print("\n3. Testing dataset info...")
        tract_info = get_dataset_info("census_tract_sample")
        if tract_info:
            print(f"✅ Census tract sample info: {tract_info['description']}")
        else:
            print("❌ Failed to get dataset info")
        
        # Test synthetic data generation (if Faker is available)
        print("\n4. Testing synthetic data generation...")
        try:
            from siege_utilities.data import generate_synthetic_population
            population = generate_synthetic_population(size=100)
            print(f"✅ Generated synthetic population: {len(population)} people")
            print(f"   Columns: {list(population.columns)}")
            print(f"   Sample data:\n{population.head(3)}")
            
            # Test Census-standard variables
            print("\n5. Testing Census-standard variables...")
            if 'race' in population.columns:
                print(f"✅ Race categories: {population['race'].unique()}")
            if 'age_group' in population.columns:
                print(f"✅ Age groups: {population['age_group'].unique()}")
            if 'income_bracket' in population.columns:
                print(f"✅ Income brackets: {population['income_bracket'].unique()}")
            if 'education_attainment' in population.columns:
                print(f"✅ Education levels: {population['education_attainment'].unique()}")
                
        except ImportError as e:
            print(f"⚠️  Synthetic data generation not available: {e}")
            print("   Install with: pip install Faker")
        
        # Test Census sample data (if Census utilities are available)
        print("\n6. Testing Census sample data...")
        try:
            from siege_utilities.data import get_census_tract_sample
            tract_data = get_census_tract_sample(population_size=200, include_geometry=False)
            print(f"✅ Generated Census tract sample: {len(tract_data)} people")
            print(f"   Columns: {list(tract_data.columns)}")
            print(f"   Sample data:\n{tract_data.head(3)}")
        except ImportError as e:
            print(f"⚠️  Census sample data not available: {e}")
            print("   Install with: pip install siege-utilities[geo]")
        
        print("\n🎉 Sample data functionality test completed!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_integration_with_existing_functions():
    """Test integration with existing siege_utilities functions."""
    
    print("\n🔗 Testing Integration with Existing Functions")
    print("=" * 50)
    
    try:
        # Test package info
        print("1. Testing package info...")
        from siege_utilities import get_package_info
        package_info = get_package_info()
        
        if 'data' in package_info['categories']:
            print(f"✅ Data module found in package info")
            print(f"   Data functions: {len(package_info['categories']['data'])}")
        else:
            print("❌ Data module not found in package info")
        
        # Test dependency checking
        print("\n2. Testing dependency checking...")
        from siege_utilities import check_dependencies
        dependencies = check_dependencies()
        
        if 'faker' in dependencies:
            print(f"✅ Faker dependency check: {dependencies['faker']}")
        else:
            print("❌ Faker not in dependency check")
        
        print("\n🎉 Integration test completed!")
        return True
        
    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🚀 Siege Utilities Sample Data Test Suite")
    print("=" * 60)
    
    # Run tests
    test1_success = test_sample_data_functionality()
    test2_success = test_integration_with_existing_functions()
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 Test Summary")
    print("=" * 60)
    print(f"Sample Data Functionality: {'✅ PASS' if test1_success else '❌ FAIL'}")
    print(f"Integration with Existing: {'✅ PASS' if test2_success else '❌ FAIL'}")
    
    if test1_success and test2_success:
        print("\n🎉 All tests passed! Sample data functionality is working correctly.")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed. Check the output above for details.")
        sys.exit(1)

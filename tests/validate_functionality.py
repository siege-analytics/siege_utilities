#!/usr/bin/env python3
"""
Simple validation script for siege_utilities key functionality.
Tests core functions without external dependencies.
"""

import sys
import os
from pathlib import Path

# Add the parent directory to the path so we can import the modules
sys.path.insert(0, str(Path(__file__).parent.parent))

def test_basic_import():
    """Test basic import functionality."""
    print("Testing basic import...")
    try:
        import siege_utilities as su
        print("✅ siege_utilities imported successfully")
        return True
    except Exception as e:
        print(f"❌ Failed to import siege_utilities: {e}")
        return False

def test_dynamic_function_registry():
    """Test the dynamic function registry."""
    print("\nTesting dynamic function registry...")
    try:
        import siege_utilities as su
        info = su.get_package_info()
        
        if 'total_functions' not in info:
            print("❌ Missing total_functions in package info")
            return False
            
        if info['total_functions'] < 200:
            print(f"❌ Expected 200+ functions, got {info['total_functions']}")
            return False
            
        if 'categories' not in info:
            print("❌ Missing categories in package info")
            return False
            
        print(f"✅ Found {info['total_functions']} functions in {len(info['categories'])} categories")
        return True
    except Exception as e:
        print(f"❌ Dynamic function registry test failed: {e}")
        return False

def test_core_functions():
    """Test core utility functions."""
    print("\nTesting core functions...")
    try:
        import siege_utilities as su
        
        # Test logging functions
        su.log_info("Test logging message")
        print("✅ Logging functions work")
        
        # Test string utils
        result = su.remove_wrapping_quotes_and_trim('"hello world"')
        if result != "hello world":
            print(f"❌ String utils failed: expected 'hello world', got '{result}'")
            return False
        print("✅ String utilities work")
        
        # Test file operations
        file_exists = su.check_if_file_exists_at_path(__file__)
        if not file_exists:
            print("❌ File existence check failed")
            return False
        print("✅ File operations work")
        
        return True
    except Exception as e:
        print(f"❌ Core functions test failed: {e}")
        return False

def test_dependency_wrappers():
    """Test that dependency wrappers give helpful messages."""
    print("\nTesting dependency wrapper functions...")
    try:
        import siege_utilities as su
        
        # Test a function that should have a dependency wrapper
        try:
            # This should give a helpful error message instead of failing
            su.get_census_data()
            print("❌ Expected dependency error message")
            return False
        except ImportError as e:
            if "pandas" in str(e) or "geopandas" in str(e):
                print("✅ Dependency wrapper gives helpful error message")
                return True
            else:
                print(f"❌ Dependency wrapper error not helpful: {e}")
                return False
                
    except Exception as e:
        print(f"❌ Dependency wrapper test failed: {e}")
        return False

def test_fips_data_structure():
    """Test FIPS data structure functions."""
    print("\nTesting FIPS data structure...")
    try:
        import siege_utilities as su
        
        # Test FIPS functions that should work without pandas
        try:
            # These should give dependency errors but be discoverable
            su.get_unified_fips_data()
        except ImportError as e:
            if "pandas" in str(e):
                print("✅ FIPS functions properly wrapped with dependency checks")
                return True
            else:
                print(f"❌ FIPS function error not expected: {e}")
                return False
                
    except Exception as e:
        print(f"❌ FIPS data structure test failed: {e}")
        return False

def run_all_tests():
    """Run all validation tests."""
    print("🧪 Siege Utilities Functionality Validation")
    print("=" * 50)
    
    tests = [
        test_basic_import,
        test_dynamic_function_registry,
        test_core_functions,
        test_dependency_wrappers,
        test_fips_data_structure
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
    
    print("\n" + "=" * 50)
    print(f"Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Functionality is working correctly.")
        return True
    else:
        print(f"❌ {total - passed} tests failed. Please check the issues above.")
        return False

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)

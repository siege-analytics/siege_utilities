#!/usr/bin/env python3
"""
Test script for siege_utilities enhanced auto-discovery system
Run this to verify that your changes are working correctly.
"""

import sys
import traceback
from pathlib import Path


def test_basic_imports():
    """Test that the package can be imported without errors."""
    print("🔄 Testing basic imports...")

    try:
        import siege_utilities
        print("✅ Main package imported successfully")
        return True
    except Exception as e:
        print(f"❌ Failed to import main package: {e}")
        traceback.print_exc()
        return False


def test_logging_availability():
    """Test that logging functions are available."""
    print("\n🔄 Testing logging availability...")

    try:
        import siege_utilities

        # Test logging functions exist
        required_log_funcs = ['log_info', 'log_error', 'log_warning', 'log_debug', 'init_logger']
        missing_funcs = []

        for func_name in required_log_funcs:
            if not hasattr(siege_utilities, func_name):
                missing_funcs.append(func_name)

        if missing_funcs:
            print(f"❌ Missing logging functions: {missing_funcs}")
            return False

        # Test that logging actually works
        siege_utilities.log_info("✅ Logging system working correctly")
        print("✅ All logging functions available and working")
        return True

    except Exception as e:
        print(f"❌ Logging test failed: {e}")
        traceback.print_exc()
        return False


def test_subpackage_imports():
    """Test that subpackages can be imported."""
    print("\n🔄 Testing subpackage imports...")

    results = {}
    subpackages = ['core', 'files', 'distributed', 'geo']

    for subpackage in subpackages:
        try:
            module = __import__(f'siege_utilities.{subpackage}', fromlist=[subpackage])
            print(f"✅ {subpackage} package imported successfully")
            results[subpackage] = True
        except ImportError as e:
            print(f"⚠️  {subpackage} package not available (likely missing dependencies): {e}")
            results[subpackage] = False
        except Exception as e:
            print(f"❌ {subpackage} package import failed: {e}")
            results[subpackage] = False

    return results


def test_function_discovery():
    """Test that functions are being discovered properly."""
    print("\n🔄 Testing function discovery...")

    try:
        import siege_utilities

        # Check if diagnostic functions are available
        if hasattr(siege_utilities, 'get_package_info'):
            info = siege_utilities.get_package_info()
            print(f"✅ Discovered {info['total_functions']} functions")
            print(f"✅ Loaded {info['total_modules']} modules")

            if info['failed_imports']:
                print(f"⚠️  {len(info['failed_imports'])} modules failed to import:")
                for module, error in info['failed_imports'].items():
                    print(f"   - {module}: {error}")

            return True
        else:
            print("❌ Diagnostic functions not available")
            return False

    except Exception as e:
        print(f"❌ Function discovery test failed: {e}")
        traceback.print_exc()
        return False


def test_mutual_availability():
    """Test that functions are mutually available across modules."""
    print("\n🔄 Testing mutual function availability...")

    try:
        import siege_utilities

        # Test if we can call functions from different modules
        test_cases = [
            ('log_info', 'Logging function'),
            ('check_if_file_exists_at_path', 'File operations'),
            ('remove_wrapping_quotes_and_trim', 'String utilities'),
        ]

        available_functions = []
        missing_functions = []

        for func_name, description in test_cases:
            if hasattr(siege_utilities, func_name):
                available_functions.append((func_name, description))
                print(f"✅ {description}: {func_name} available")
            else:
                missing_functions.append((func_name, description))
                print(f"❌ {description}: {func_name} missing")

        if missing_functions:
            print(f"❌ {len(missing_functions)} core functions missing")
            return False

        # Test calling a function to ensure it works
        try:
            siege_utilities.log_info("Testing function call from main package")
            print("✅ Function calls working correctly")
        except Exception as e:
            print(f"❌ Function call failed: {e}")
            return False

        return True

    except Exception as e:
        print(f"❌ Mutual availability test failed: {e}")
        traceback.print_exc()
        return False


def test_specific_functionality():
    """Test specific functionality to ensure it works."""
    print("\n🔄 Testing specific functionality...")

    try:
        import siege_utilities
        from pathlib import Path
        import tempfile

        # Test string utilities
        if hasattr(siege_utilities, 'remove_wrapping_quotes_and_trim'):
            test_string = '  "hello world"  '
            result = siege_utilities.remove_wrapping_quotes_and_trim(test_string)
            expected = 'hello world'

            if result == expected:
                print("✅ String utilities working correctly")
            else:
                print(f"❌ String utilities failed: expected '{expected}', got '{result}'")
                return False

        # Test file utilities if available
        if hasattr(siege_utilities, 'check_if_file_exists_at_path'):
            # Create a temporary file
            with tempfile.NamedTemporaryFile(delete=False) as tmp:
                tmp_path = Path(tmp.name)

            # Test file existence check
            exists = siege_utilities.check_if_file_exists_at_path(tmp_path)
            if exists:
                print("✅ File utilities working correctly")
                # Clean up
                tmp_path.unlink()
            else:
                print("❌ File utilities not working correctly")
                return False

        return True

    except Exception as e:
        print(f"❌ Specific functionality test failed: {e}")
        traceback.print_exc()
        return False


def test_dependencies():
    """Test optional dependencies status."""
    print("\n🔄 Testing optional dependencies...")

    try:
        import siege_utilities

        if hasattr(siege_utilities, 'check_dependencies'):
            deps = siege_utilities.check_dependencies()

            print("📊 Dependency Status:")
            for dep, available in deps.items():
                status = "✅ Available" if available else "❌ Missing"
                print(f"   {dep}: {status}")

            return True
        else:
            print("⚠️  Dependency check function not available")
            return False

    except Exception as e:
        print(f"❌ Dependency test failed: {e}")
        return False


def run_comprehensive_test():
    """Run all tests and provide a summary."""
    print("🚀 Starting Siege Utilities Enhanced Auto-Discovery Test Suite")
    print("=" * 60)

    tests = [
        ("Basic Imports", test_basic_imports),
        ("Logging Availability", test_logging_availability),
        ("Subpackage Imports", test_subpackage_imports),
        ("Function Discovery", test_function_discovery),
        ("Mutual Availability", test_mutual_availability),
        ("Specific Functionality", test_specific_functionality),
        ("Dependencies", test_dependencies),
    ]

    results = {}

    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"❌ {test_name} test crashed: {e}")
            results[test_name] = False

    # Summary
    print("\n" + "=" * 60)
    print("📋 TEST SUMMARY")
    print("=" * 60)

    passed = sum(1 for result in results.values() if result is True)
    total = len(results)

    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")

    print(f"\n🎯 Overall: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All tests passed! Your enhanced auto-discovery system is working perfectly!")
    elif passed > total * 0.7:
        print("⚠️  Most tests passed. Some optional features may not be available.")
    else:
        print("🚨 Multiple test failures. Your system needs debugging.")

    return passed == total


if __name__ == "__main__":
    success = run_comprehensive_test()
    sys.exit(0 if success else 1)
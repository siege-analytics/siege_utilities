#!/usr/bin/env python3
"""
Comprehensive test runner for siege_utilities.
Provides easy access to different test scenarios and configurations.
"""

import sys
import subprocess
import argparse
import pathlib
from typing import List, Optional


def run_command(cmd: List[str], description: str) -> bool:
    """Run a command and return success status."""
    print(f"\n{'='*60}")
    print(f"🚀 {description}")
    print(f"{'='*60}")
    print(f"Running: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=False)
        print(f"✅ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed with exit code {e.returncode}")
        return False
    except FileNotFoundError:
        print(f"❌ Command not found: {cmd[0]}")
        print("   Make sure pytest is installed: pip install pytest")
        return False


def run_basic_tests() -> bool:
    """Run basic test suite."""
    return run_command(
        ["pytest", "tests/", "-v"],
        "Basic Test Suite"
    )


def run_client_connection_tests() -> bool:
    """Run client and connection configuration tests."""
    return run_command(
        ["pytest", "tests/test_client_and_connection_config.py", "-v", "-s"],
        "Client & Connection Configuration Tests"
    )


def run_core_tests() -> bool:
    """Run core utility tests."""
    return run_command(
        ["pytest", "tests/test_core_logging.py", "tests/test_string_utils.py", "-v"],
        "Core Utility Tests"
    )


def run_file_tests() -> bool:
    """Run file operation tests."""
    return run_command(
        ["pytest", "tests/test_file_operations.py", "tests/test_paths.py", "-v"],
        "File Operation Tests"
    )


def run_distributed_tests() -> bool:
    """Run distributed computing tests."""
    return run_command(
        ["pytest", "tests/test_spark_utils.py", "-v", "-m", "not slow"],
        "Distributed Computing Tests"
    )


def run_geo_tests() -> bool:
    """Run geospatial tests."""
    return run_command(
        ["pytest", "tests/test_geocoding.py", "-v"],
        "Geospatial Tests"
    )


def run_with_coverage() -> bool:
    """Run tests with coverage reporting."""
    return run_command(
        ["pytest", "tests/", "--cov=siege_utilities", "--cov-report=term-missing", "--cov-report=html"],
        "Tests with Coverage Reporting"
    )


def run_fast_tests() -> bool:
    """Run only fast tests (exclude slow ones)."""
    return run_command(
        ["pytest", "tests/", "-v", "-m", "not slow"],
        "Fast Tests Only (Excluding Slow Tests)"
    )


def run_specific_test(test_path: str) -> bool:
    """Run a specific test file or test function."""
    return run_command(
        ["pytest", test_path, "-v", "-s"],
        f"Specific Test: {test_path}"
    )


def run_parallel_tests() -> bool:
    """Run tests in parallel for faster execution."""
    return run_command(
        ["pytest", "tests/", "-n", "auto", "-v"],
        "Parallel Test Execution"
    )


def run_debug_tests() -> bool:
    """Run tests with debug options."""
    return run_command(
        ["pytest", "tests/", "-v", "-s", "--tb=long", "--maxfail=1"],
        "Debug Test Execution"
    )


def check_test_environment() -> bool:
    """Check if the test environment is properly set up."""
    print("\n🔍 Checking Test Environment")
    print("="*40)
    
    # Check if pytest is available
    try:
        import pytest
        print(f"✅ pytest {pytest.__version__} available")
    except ImportError:
        print("❌ pytest not available")
        return False
    
    # Check if test directory exists
    test_dir = pathlib.Path("tests")
    if test_dir.exists():
        print(f"✅ Test directory found: {test_dir}")
        test_files = list(test_dir.glob("test_*.py"))
        print(f"✅ Found {len(test_files)} test files")
    else:
        print("❌ Test directory not found")
        return False
    
    # Check if siege_utilities is importable
    try:
        import siege_utilities
        print(f"✅ siege_utilities package importable")
        
        # Check package info
        if hasattr(siege_utilities, 'get_package_info'):
            info = siege_utilities.get_package_info()
            print(f"✅ Package has {info['total_functions']} functions across {info['total_modules']} modules")
        else:
            print("⚠️  Package info function not available")
            
    except ImportError as e:
        print(f"❌ Cannot import siege_utilities: {e}")
        return False
    
    return True


def show_test_summary() -> None:
    """Show a summary of available test options."""
    print("\n📋 Available Test Options")
    print("="*40)
    print("1.  Basic tests (all tests)")
    print("2.  Client & Connection tests")
    print("3.  Core utility tests")
    print("4.  File operation tests")
    print("5.  Distributed computing tests")
    print("6.  Geospatial tests")
    print("7.  Tests with coverage")
    print("8.  Fast tests only")
    print("9.  Parallel test execution")
    print("10. Debug test execution")
    print("11. Check test environment")
    print("12. Run specific test")
    print("13. Show this help")
    print("0.  Exit")


def main():
    """Main test runner function."""
    parser = argparse.ArgumentParser(description="Comprehensive test runner for siege_utilities")
    parser.add_argument("--test", help="Run specific test file or function")
    parser.add_argument("--coverage", action="store_true", help="Run tests with coverage")
    parser.add_argument("--fast", action="store_true", help="Run only fast tests")
    parser.add_argument("--parallel", action="store_true", help="Run tests in parallel")
    parser.add_argument("--debug", action="store_true", help="Run tests with debug options")
    parser.add_argument("--check", action="store_true", help="Check test environment")
    
    args = parser.parse_args()
    
    # If command line arguments provided, run specific tests
    if args.test:
        run_specific_test(args.test)
        return
    
    if args.coverage:
        run_with_coverage()
        return
    
    if args.fast:
        run_fast_tests()
        return
    
    if args.parallel:
        run_parallel_tests()
        return
    
    if args.debug:
        run_debug_tests()
        return
    
    if args.check:
        check_test_environment()
        return
    
    # Interactive mode
    print("🧪 Siege Utilities Test Runner")
    print("="*40)
    
    if not check_test_environment():
        print("\n❌ Test environment check failed. Please fix issues before running tests.")
        return
    
    while True:
        show_test_summary()
        
        try:
            choice = input("\nSelect test option (0-13): ").strip()
            
            if choice == "0":
                print("👋 Goodbye!")
                break
            elif choice == "1":
                run_basic_tests()
            elif choice == "2":
                run_client_connection_tests()
            elif choice == "3":
                run_core_tests()
            elif choice == "4":
                run_file_tests()
            elif choice == "5":
                run_distributed_tests()
            elif choice == "6":
                run_geo_tests()
            elif choice == "7":
                run_with_coverage()
            elif choice == "8":
                run_fast_tests()
            elif choice == "9":
                run_parallel_tests()
            elif choice == "10":
                run_debug_tests()
            elif choice == "11":
                check_test_environment()
            elif choice == "12":
                test_path = input("Enter test path (e.g., tests/test_file.py::TestClass::test_method): ").strip()
                if test_path:
                    run_specific_test(test_path)
            elif choice == "13":
                continue
            else:
                print("❌ Invalid choice. Please select 0-13.")
                
        except KeyboardInterrupt:
            print("\n\n👋 Test runner interrupted. Goodbye!")
            break
        except Exception as e:
            print(f"\n❌ Unexpected error: {e}")


if __name__ == "__main__":
    main()
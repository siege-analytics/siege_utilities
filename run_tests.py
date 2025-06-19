# ================================================================
# FILE: run_tests.py
# ================================================================
# !/usr/bin/env python3
"""
Test runner script for siege-utilities.
This script provides an easy way to run different test suites.
"""

import sys
import os
import subprocess
import argparse
from pathlib import Path


def run_command(cmd, description):
    """Run a command and handle errors."""
    print(f"\n🔄 {description}")
    print(f"Running: {' '.join(cmd)}")
    print("-" * 60)

    result = subprocess.run(cmd, capture_output=False)

    if result.returncode == 0:
        print(f"✅ {description} completed successfully")
    else:
        print(f"❌ {description} failed with return code {result.returncode}")

    return result.returncode == 0


def main():
    parser = argparse.ArgumentParser(description="Run siege-utilities tests")

    parser.add_argument(
        "--mode",
        choices=["smoke", "unit", "integration", "all", "coverage", "fast"],
        default="smoke",
        help="Test mode to run"
    )

    parser.add_argument(
        "--module",
        choices=["core", "files", "distributed", "geo", "discovery"],
        help="Run tests for specific module only"
    )

    parser.add_argument(
        "--parallel",
        action="store_true",
        help="Run tests in parallel (requires pytest-xdist)"
    )

    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Verbose output"
    )

    parser.add_argument(
        "--install-deps",
        action="store_true",
        help="Install test dependencies first"
    )

    args = parser.parse_args()

    # Ensure we're in the right directory
    if not Path("siege_utilities").exists():
        print("❌ Error: siege_utilities directory not found!")
        print("Please run this script from the project root directory.")
        sys.exit(1)

    # Create reports directory
    Path("reports").mkdir(exist_ok=True)

    # Install dependencies if requested
    if args.install_deps:
        print("📦 Installing test dependencies...")
        subprocess.run([
            sys.executable, "-m", "pip", "install", "-r", "test_requirements.txt"
        ])

    # Build pytest command
    cmd = [sys.executable, "-m", "pytest"]

    # Add verbosity
    if args.verbose:
        cmd.extend(["-vv", "-s"])

    # Add parallel execution
    if args.parallel:
        cmd.extend(["-n", "auto"])

    # Configure based on mode
    if args.mode == "smoke":
        print("🔥 Running SMOKE TESTS - Quick tests to find broken functions")
        cmd.extend([
            "--maxfail=10",  # Stop after 10 failures
            "--tb=short",
            "-x"  # Stop on first failure for quick feedback
        ])

    elif args.mode == "fast":
        print("⚡ Running FAST TESTS - Skip slow tests")
        cmd.extend([
            "-m", "not slow",
            "--maxfail=5"
        ])

    elif args.mode == "unit":
        print("🧪 Running UNIT TESTS")
        cmd.extend(["-m", "unit or not integration"])

    elif args.mode == "coverage":
        print("📊 Running COVERAGE ANALYSIS")
        cmd.extend([
            "--cov=siege_utilities",
            "--cov-report=html:htmlcov",
            "--cov-report=term-missing",
            "--cov-report=xml:coverage.xml",
            "--cov-fail-under=60"  # Fail if coverage below 60%
        ])

    elif args.mode == "all":
        print("🎯 Running ALL TESTS")
        # No additional filters

    # Filter by module if specified
    if args.module:
        print(f"🎯 Filtering tests for module: {args.module}")
        if args.module == "core":
            cmd.append("tests/test_core_*.py")
        elif args.module == "files":
            cmd.append("tests/test_*file*.py")
        elif args.module == "distributed":
            cmd.append("tests/test_*spark*.py")
        elif args.module == "geo":
            cmd.append("tests/test_*geo*.py")
        elif args.module == "discovery":
            cmd.append("tests/test_package_discovery.py")

    # Run the tests
    success = run_command(cmd, f"siege-utilities {args.mode.upper()} tests")

    if success:
        print("\n🎉 Tests completed successfully!")

        # Show coverage report location if generated
        if args.mode == "coverage" or "cov" in cmd:
            if Path("htmlcov").exists():
                print(f"📊 Coverage report: file://{Path('htmlcov/index.html').absolute()}")

        # Show test report location
        if Path("reports/pytest_report.html").exists():
            print(f"📋 Test report: file://{Path('reports/pytest_report.html').absolute()}")

    else:
        print("\n❌ Some tests failed!")
        print("\nDebugging tips:")
        print("1. Check the test output above for specific errors")
        print("2. Run with --verbose for more details")
        print("3. Run specific test files: pytest tests/test_specific_file.py")
        print("4. Run a single test: pytest tests/test_file.py::TestClass::test_method")
        sys.exit(1)


def quick_smoke_test():
    """Run a very quick smoke test to check basic functionality."""
    print("🔥 Quick Smoke Test - Testing basic imports and functions")

    try:
        import siege_utilities
        print("✅ Package imports successfully")

        # Test basic functions
        info = siege_utilities.get_package_info()
        print(f"✅ Package info: {info['total_functions']} functions found")

        # Test logging
        siege_utilities.log_info("Smoke test message")
        print("✅ Logging works")

        # Test string utils
        result = siege_utilities.remove_wrapping_quotes_and_trim('"test"')
        assert result == "test"
        print("✅ String utilities work")

        print("\n🎉 Basic smoke test PASSED!")
        return True

    except Exception as e:
        print(f"\n❌ Basic smoke test FAILED: {e}")
        return False


if __name__ == "__main__":
    if len(sys.argv) == 1:
        # No arguments - run quick smoke test
        success = quick_smoke_test()
        if not success:
            print("\n💡 Try running: python run_tests.py --mode smoke")
        sys.exit(0 if success else 1)
    else:
        main()

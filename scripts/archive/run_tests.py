#!/usr/bin/env python3
"""
Comprehensive test runner for siege_utilities.
Provides easy access to different test scenarios and configurations.

Updated 2026-02-28 to match actual test files after su#113 cleanup.
"""

import sys
import subprocess
import argparse
import pathlib
from typing import List


# =============================================================================
# TEST FILE GROUPS (must match actual files in tests/)
# =============================================================================

CORE_TESTS = [
    "tests/test_core_logging.py",
    "tests/test_string_utils.py",
    "tests/test_sql_safety.py",
    "tests/test_settings.py",
    "tests/test_environment.py",
]

GEO_TESTS = [
    "tests/test_census_api_client.py",
    "tests/test_census_api_integration.py",
    "tests/test_census_bug_fix.py",
    "tests/test_census_cache_backend.py",
    "tests/test_census_data_selector_bonus.py",
    "tests/test_enhanced_census_utilities.py",
    "tests/test_geo_alignment.py",
    "tests/test_geographic_levels.py",
    "tests/test_geoid_slugs.py",
    "tests/test_geoid_utils.py",
    "tests/test_geoid_validator.py",
    "tests/test_boundary_catalog.py",
    "tests/test_boundary_manager.py",
    "tests/test_review_fixes.py",
]

CHOROPLETH_TESTS = [
    "tests/test_choropleth.py",
    "tests/test_chart_generator.py",
]

CROSSWALK_TESTS = [
    "tests/test_crosswalk.py",
    "tests/test_crosswalk_analytics.py",
    "tests/test_areal_interpolation.py",
]

TIMESERIES_TESTS = [
    "tests/test_timeseries.py",
    "tests/test_timeseries_rollup_services.py",
]

NCES_TESTS = [
    "tests/test_nces_download.py",
    "tests/test_nces_service.py",
    "tests/test_locale.py",
    "tests/test_urbanicity_service.py",
]

DISTRIBUTED_TESTS = [
    "tests/test_distributed.py",
]

DJANGO_TESTS = [
    "tests/test_temporal_boundary.py",
    "tests/test_pydantic_schemas.py",
    "tests/test_pydantic_v1_compat.py",
]

MISC_TESTS = [
    "tests/test_credential_manager.py",
    "tests/test_person_actor.py",
    "tests/test_hydra_integration.py",
]

DATABRICKS_TESTS = [
    "tests/test_databricks_auth_session_secrets.py",
    "tests/test_databricks_dataframe_bridge.py",
    "tests/test_databricks_fallback.py",
    "tests/test_databricks_lakebase_unity.py",
]


# =============================================================================
# RUNNER
# =============================================================================

def run_command(cmd: List[str], description: str) -> bool:
    """Run a command and return success status."""
    print(f"\n{'='*60}")
    print(f"  {description}")
    print(f"{'='*60}")
    print(f"Running: {' '.join(cmd)}")

    try:
        result = subprocess.run(cmd, check=True, capture_output=False)
        print(f"  {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"  {description} failed with exit code {e.returncode}")
        return False
    except FileNotFoundError:
        print(f"  Command not found: {cmd[0]}")
        print("   Make sure pytest is installed: pip install pytest")
        return False


def _run_group(files: List[str], description: str, extra_args: List[str] = None) -> bool:
    """Run a group of test files."""
    existing = [f for f in files if pathlib.Path(f).exists()]
    if not existing:
        print(f"  No test files found for: {description}")
        return False
    cmd = ["pytest"] + existing + ["-v"] + (extra_args or [])
    return run_command(cmd, description)


# =============================================================================
# PUBLIC TEST FUNCTIONS
# =============================================================================

def run_all_tests() -> bool:
    """Run the entire test suite."""
    return run_command(["pytest", "tests/", "-v"], "Full Test Suite")


def run_core_tests() -> bool:
    """Run core utility tests (logging, strings, sql_safety, settings)."""
    return _run_group(CORE_TESTS, "Core Utility Tests")


def run_geo_tests() -> bool:
    """Run geospatial / Census API tests."""
    return _run_group(GEO_TESTS, "Geospatial & Census Tests")


def run_choropleth_tests() -> bool:
    """Run choropleth and chart generation tests."""
    return _run_group(CHOROPLETH_TESTS, "Choropleth & Chart Tests")


def run_crosswalk_tests() -> bool:
    """Run crosswalk and areal interpolation tests."""
    return _run_group(CROSSWALK_TESTS, "Crosswalk & Interpolation Tests")


def run_timeseries_tests() -> bool:
    """Run time-series and rollup service tests."""
    return _run_group(TIMESERIES_TESTS, "Time-Series Tests")


def run_nces_tests() -> bool:
    """Run NCES / urbanicity tests."""
    return _run_group(NCES_TESTS, "NCES & Urbanicity Tests")


def run_distributed_tests() -> bool:
    """Run distributed computing tests."""
    return _run_group(DISTRIBUTED_TESTS, "Distributed Computing Tests")


def run_django_tests() -> bool:
    """Run Django model and Pydantic schema tests."""
    return _run_group(DJANGO_TESTS, "Django & Pydantic Tests")


def run_databricks_tests() -> bool:
    """Run Databricks integration tests."""
    return _run_group(DATABRICKS_TESTS, "Databricks Tests")


def run_misc_tests() -> bool:
    """Run miscellaneous tests (credentials, person/actor, hydra)."""
    return _run_group(MISC_TESTS, "Miscellaneous Tests")


def run_with_coverage() -> bool:
    """Run tests with coverage reporting."""
    return run_command(
        ["pytest", "tests/", "--cov=siege_utilities",
         "--cov-report=term-missing", "--cov-report=html"],
        "Tests with Coverage Reporting"
    )


def run_fast_tests() -> bool:
    """Run only fast tests (exclude slow ones)."""
    return run_command(
        ["pytest", "tests/", "-v", "-m", "not slow"],
        "Fast Tests Only"
    )


def run_parallel_tests() -> bool:
    """Run tests in parallel (requires pytest-xdist)."""
    return run_command(
        ["pytest", "tests/", "-n", "auto", "-v"],
        "Parallel Test Execution"
    )


def run_debug_tests() -> bool:
    """Run tests with debug options (long traceback, stop on first failure)."""
    return run_command(
        ["pytest", "tests/", "-v", "-s", "--tb=long", "--maxfail=1"],
        "Debug Test Execution"
    )


def run_specific_test(test_path: str) -> bool:
    """Run a specific test file or test function."""
    return run_command(
        ["pytest", test_path, "-v", "-s"],
        f"Specific Test: {test_path}"
    )


# =============================================================================
# ENVIRONMENT CHECK
# =============================================================================

def check_test_environment() -> bool:
    """Check if the test environment is properly set up."""
    print("\n  Checking Test Environment")
    print("=" * 40)

    try:
        import pytest
        print(f"  pytest {pytest.__version__} available")
    except ImportError:
        print("  pytest not available")
        return False

    test_dir = pathlib.Path("tests")
    if not test_dir.exists():
        print("  Test directory not found")
        return False

    test_files = sorted(test_dir.glob("test_*.py"))
    print(f"  Found {len(test_files)} test files:")
    for f in test_files:
        print(f"    {f.name}")

    try:
        import siege_utilities
        print(f"\n  siege_utilities package importable")
    except ImportError as e:
        print(f"  Cannot import siege_utilities: {e}")
        return False

    return True


# =============================================================================
# INTERACTIVE MENU
# =============================================================================

def show_menu() -> None:
    """Show available test options."""
    print("\n  Available Test Options")
    print("=" * 50)
    print("BY MODULE:")
    print("  1.  All tests")
    print("  2.  Core (logging, strings, sql_safety, settings)")
    print("  3.  Geo / Census API")
    print("  4.  Choropleth & Charts")
    print("  5.  Crosswalk & Interpolation")
    print("  6.  Time-Series")
    print("  7.  NCES & Urbanicity")
    print("  8.  Distributed Computing")
    print("  9.  Django & Pydantic")
    print(" 10.  Databricks")
    print(" 11.  Miscellaneous (credentials, person/actor, hydra)")
    print()
    print("EXECUTION OPTIONS:")
    print(" 12.  Tests with coverage")
    print(" 13.  Fast tests only (skip @slow)")
    print(" 14.  Parallel execution (pytest-xdist)")
    print(" 15.  Debug mode (stop on first failure)")
    print(" 16.  Run specific test path")
    print(" 17.  Check test environment")
    print("  0.  Exit")


def main():
    """Main test runner function."""
    parser = argparse.ArgumentParser(
        description="Comprehensive test runner for siege_utilities"
    )
    parser.add_argument("--test", help="Run specific test file or function")
    parser.add_argument("--all", action="store_true", help="Run all tests")
    parser.add_argument("--core", action="store_true", help="Run core tests")
    parser.add_argument("--geo", action="store_true", help="Run geo/Census tests")
    parser.add_argument("--choropleth", action="store_true", help="Run choropleth tests")
    parser.add_argument("--crosswalk", action="store_true", help="Run crosswalk tests")
    parser.add_argument("--timeseries", action="store_true", help="Run time-series tests")
    parser.add_argument("--nces", action="store_true", help="Run NCES tests")
    parser.add_argument("--distributed", action="store_true", help="Run distributed tests")
    parser.add_argument("--django", action="store_true", help="Run Django/Pydantic tests")
    parser.add_argument("--databricks", action="store_true", help="Run Databricks tests")
    parser.add_argument("--coverage", action="store_true", help="Run with coverage")
    parser.add_argument("--fast", action="store_true", help="Fast tests only")
    parser.add_argument("--parallel", action="store_true", help="Run in parallel")
    parser.add_argument("--debug", action="store_true", help="Debug mode")
    parser.add_argument("--check", action="store_true", help="Check environment")

    args = parser.parse_args()

    # CLI dispatch
    dispatch = {
        'test': lambda: run_specific_test(args.test),
        'all': run_all_tests,
        'core': run_core_tests,
        'geo': run_geo_tests,
        'choropleth': run_choropleth_tests,
        'crosswalk': run_crosswalk_tests,
        'timeseries': run_timeseries_tests,
        'nces': run_nces_tests,
        'distributed': run_distributed_tests,
        'django': run_django_tests,
        'databricks': run_databricks_tests,
        'coverage': run_with_coverage,
        'fast': run_fast_tests,
        'parallel': run_parallel_tests,
        'debug': run_debug_tests,
        'check': check_test_environment,
    }

    for flag, func in dispatch.items():
        if getattr(args, flag, None):
            func()
            return

    # Interactive mode
    print("  Siege Utilities Test Runner")
    print("=" * 50)

    if not check_test_environment():
        print("\n  Test environment check failed. Fix issues before running tests.")
        return

    menu_dispatch = {
        "1": run_all_tests,
        "2": run_core_tests,
        "3": run_geo_tests,
        "4": run_choropleth_tests,
        "5": run_crosswalk_tests,
        "6": run_timeseries_tests,
        "7": run_nces_tests,
        "8": run_distributed_tests,
        "9": run_django_tests,
        "10": run_databricks_tests,
        "11": run_misc_tests,
        "12": run_with_coverage,
        "13": run_fast_tests,
        "14": run_parallel_tests,
        "15": run_debug_tests,
        "17": check_test_environment,
    }

    while True:
        show_menu()
        try:
            choice = input("\nSelect option (0-17): ").strip()
            if choice == "0":
                break
            elif choice == "16":
                path = input("Enter test path: ").strip()
                if path:
                    run_specific_test(path)
            elif choice in menu_dispatch:
                menu_dispatch[choice]()
            else:
                print("  Invalid choice.")
        except KeyboardInterrupt:
            print("\n\n  Interrupted. Goodbye!")
            break
        except Exception as e:
            print(f"\n  Unexpected error: {e}")


if __name__ == "__main__":
    main()

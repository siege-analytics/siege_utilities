#!/usr/bin/env python3
"""
Integrated test runner script for siege-utilities.
This script is now a thin wrapper around siege_utilities testing functions.
"""

import sys
import argparse
from pathlib import Path


def main():
    """Main test runner using siege_utilities integrated functions."""
    parser = argparse.ArgumentParser(
        description="Run siege-utilities tests using integrated testing functions",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_tests.py                          # Quick smoke test
  python run_tests.py --mode smoke --verbose   # Verbose smoke test  
  python run_tests.py --mode distributed       # Test Spark functionality
  python run_tests.py --mode all --parallel    # Full test suite in parallel
  python run_tests.py --comprehensive          # Complete diagnostic + test suite
  python run_tests.py --diagnose               # Environment diagnostics only
        """
    )

    parser.add_argument(
        "--mode",
        choices=["smoke", "unit", "integration", "all", "coverage", "fast"],
        default="smoke",
        help="Test mode to run (default: smoke)"
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

    parser.add_argument(
        "--setup-env",
        action="store_true",
        default=True,
        help="Set up environment before running tests (default: True)"
    )

    parser.add_argument(
        "--no-setup-env",
        action="store_true",
        help="Skip environment setup"
    )

    parser.add_argument(
        "--diagnose",
        action="store_true",
        help="Run environment diagnostics only"
    )

    parser.add_argument(
        "--comprehensive",
        action="store_true",
        help="Run comprehensive test suite (diagnostics + smoke + unit tests)"
    )

    parser.add_argument(
        "--report",
        action="store_true",
        help="Generate detailed test report"
    )

    args = parser.parse_args()

    # Determine environment setup preference
    setup_environment = args.setup_env and not args.no_setup_env

    # Ensure we're in the right directory
    if not Path("siege_utilities").exists():
        print("❌ Error: siege_utilities directory not found!")
        print("Please run this script from the project root directory.")
        sys.exit(1)

    try:
        # Import siege_utilities to use integrated functions
        import siege_utilities
        print("✅ siege_utilities package loaded successfully")

    except ImportError as e:
        print(f"❌ Could not import siege_utilities: {e}")
        print("💡 Try: pip install -e .")
        sys.exit(1)

    # Handle special modes first
    if args.diagnose:
        print("🔍 Running environment diagnostics...")
        success = siege_utilities.diagnose_environment()
        sys.exit(0 if success else 1)

    if args.comprehensive:
        print("🎯 Running comprehensive test suite...")
        success = siege_utilities.run_comprehensive_test()
        sys.exit(0 if success else 1)

    if args.report:
        print("📊 Generating test report...")
        report = siege_utilities.get_test_report()

        print("\n" + "=" * 60)
        print("TEST REPORT")
        print("=" * 60)
        print(f"Environment healthy: {report['environment_healthy']}")
        print(f"Smoke test passed: {report['smoke_test_passed']}")

        print(f"\nDependencies ({len(report['dependencies'])} total):")
        for dep, available in report['dependencies'].items():
            status = "✅" if available else "❌"
            print(f"  {status} {dep}")

        if report.get('suggestions'):
            print(f"\nSuggestions:")
            for suggestion in report['suggestions']:
                print(f"  💡 {suggestion}")

        # Show system info if verbose
        if args.verbose:
            print(f"\nSystem Information:")
            for key, value in report['system_info'].items():
                print(f"  {key}: {value}")

        sys.exit(0)

    # Run standard test suite
    print(f"🚀 Running {args.mode} tests using siege_utilities integrated functions...")

    success = siege_utilities.run_test_suite(
        mode=args.mode,
        module=args.module,
        parallel=args.parallel,
        verbose=args.verbose,
        install_deps=args.install_deps,
        setup_environment=setup_environment
    )

    if success:
        print("\n🎉 Test run completed successfully!")
        print("\n💡 More options:")
        print("  python run_tests.py --comprehensive  # Full diagnostic suite")
        print("  python run_tests.py --report         # Detailed report")
        print("  python run_tests.py --diagnose       # Environment check only")
    else:
        print("\n❌ Test run failed!")
        print("\n🔍 Debugging options:")
        print("  python run_tests.py --diagnose       # Check environment")
        print("  python run_tests.py --report         # Get detailed report")
        print("  python run_tests.py --verbose        # More detailed output")

    sys.exit(0 if success else 1)


def quick_run():
    """Quick smoke test when script is run without arguments."""
    try:
        import siege_utilities
        print("🔥 Running quick smoke test...")

        success = siege_utilities.quick_smoke_test()

        if success:
            print("\n✅ Quick smoke test PASSED!")
            print("\n💡 More test options:")
            print("  python run_tests.py --mode all       # Run all tests")
            print("  python run_tests.py --comprehensive  # Full diagnostic suite")
            print("  python run_tests.py --help           # See all options")
        else:
            print("\n❌ Quick smoke test FAILED!")
            print("\n🔍 Try these debugging steps:")
            print("  python run_tests.py --diagnose       # Check environment")
            print("  python run_tests.py --report         # Get detailed report")
            print("  python run_tests.py --mode smoke --verbose  # Verbose smoke test")

        return success

    except ImportError as e:
        print(f"❌ Could not import siege_utilities: {e}")
        print("💡 Installation suggestions:")
        print("  pip install -e .                     # Install in development mode")
        print("  pip install pyspark                  # Install PySpark if missing")
        return False

    except Exception as e:
        print(f"❌ Quick smoke test failed: {e}")
        return False


if __name__ == "__main__":
    if len(sys.argv) == 1:
        # No arguments - run quick smoke test
        success = quick_run()
        sys.exit(0 if success else 1)
    else:
        # Arguments provided - run main function
        main()
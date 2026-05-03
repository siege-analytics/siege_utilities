"""
Test runner utilities for siege_utilities.
Provides functions for running different test suites with proper environment setup.
"""

import sys
import subprocess
from pathlib import Path
from typing import List, Optional, Dict, Any

# Import logging functions from main package
try:
    from siege_utilities.core.logging import log_info, log_warning, log_error, log_debug
except ImportError:
    # Fallback if main package not available yet
    def log_info(message): pass
    def log_warning(message): pass
    def log_error(message): pass
    def log_debug(message): pass


def run_command(cmd: List[str], description: str, log_file: Optional[str] = None) -> bool:
    """
    Run a command with proper logging and error handling.

    Args:
        cmd: Command to run as list of strings
        description: Human-readable description for logging
        log_file: Optional log file path to write output

    Returns:
        True if command succeeded, False otherwise

    Example:
        >>> import siege_utilities
        >>> success = siege_utilities.run_command(
        >>>     ["python", "-m", "pytest", "tests/"],
        >>>     "Running tests"
        >>> )
    """
    log_info(f"\n{description}")
    log_info(f"Running: {' '.join(cmd)}")
    log_info("-" * 60)

    if log_file:
        with open(log_file, "w") as f:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            for line in process.stdout:
                log_info(line.rstrip())
                f.write(line)
            _, stderr = process.communicate()
            if stderr:
                log_error(stderr)
                f.write(stderr)
            returncode = process.returncode
    else:
        process = subprocess.run(cmd)
        returncode = process.returncode

    if returncode == 0:
        log_info(f"{description} completed successfully")
    else:
        log_error(f"{description} failed with return code {returncode}")

    return returncode == 0


def quick_smoke_test() -> bool:
    """
    Run a very quick smoke test to check basic functionality.

    Returns:
        True if smoke test passes, False otherwise

    Example:
        >>> import siege_utilities
        >>> if siege_utilities.quick_smoke_test():
        >>>     print("Basic functionality working!")
    """
    log_info("Quick Smoke Test - Testing basic imports and functions")

    try:
        import siege_utilities
        log_info("Package imports successfully")

        # Test basic functions
        info = siege_utilities.get_package_info()
        log_info(f"Package info: {info['total_functions']} functions found")

        # Test logging
        siege_utilities.log_info("Smoke test message")
        log_info("Logging works")

        # Test string utils
        result = siege_utilities.remove_wrapping_quotes_and_trim('"test"')
        assert result == "test"
        log_info("String utilities work")

        # Test dependencies
        deps = siege_utilities.check_dependencies()
        available_deps = [dep for dep, available in deps.items() if available]
        log_info(f"Dependencies check: {len(available_deps)}/{len(deps)} available")

        log_info("\nBasic smoke test PASSED!")
        return True

    except Exception as e:
        log_error(f"\nBasic smoke test FAILED: {e}")
        return False


def build_pytest_command(
        mode: str = "smoke",
        module: Optional[str] = None,
        parallel: bool = False,
        verbose: bool = False
) -> List[str]:
    """
    Build pytest command based on parameters.

    Args:
        mode: Test mode (smoke, unit, integration, all, coverage, fast)
        module: Specific module to test (core, files, distributed, geo, discovery)
        parallel: Whether to run tests in parallel
        verbose: Whether to use verbose output

    Returns:
        List of command arguments for pytest

    Example:
        >>> import siege_utilities
        >>> cmd = siege_utilities.build_pytest_command(
        >>>     mode="smoke",
        >>>     module="distributed",
        >>>     verbose=True
        >>> )
        >>> print(cmd)
    """
    cmd = [sys.executable, "-m", "pytest"]

    # Add verbosity
    if verbose:
        cmd.extend(["-vv", "-s", "--tb=long"])

    # Add parallel execution
    if parallel:
        cmd.extend(["-n", "auto"])

    # Configure based on mode
    if mode == "smoke":
        log_info("Running SMOKE TESTS - Quick tests to find broken functions")
        cmd.extend([
            "--maxfail=10",  # Stop after 10 failures
            "--tb=short",
            "-x"  # Stop on first failure for quick feedback
        ])

    elif mode == "fast":
        log_info("Running FAST TESTS - Skip slow tests")
        cmd.extend([
            "-m", "not slow",
            "--maxfail=5"
        ])

    elif mode == "unit":
        log_info("Running UNIT TESTS")
        cmd.extend(["-m", "unit or not integration"])

    elif mode == "coverage":
        log_info("Running COVERAGE ANALYSIS")
        cmd.extend([
            "--cov=siege_utilities",
            "--cov-report=html:htmlcov",
            "--cov-report=term-missing",
            "--cov-report=xml:coverage.xml",
            "--cov-fail-under=60"  # Fail if coverage below 60%
        ])

    elif mode == "all":
        log_info("Running ALL TESTS")
        # No additional filters

    # Filter by module if specified
    if module:
        log_info(f"Filtering tests for module: {module}")
        if module == "core":
            cmd.append("tests/test_core_*.py")
        elif module == "files":
            cmd.append("tests/test_*file*.py")
        elif module == "distributed":
            cmd.append("tests/test_*spark*.py")
        elif module == "geo":
            cmd.append("tests/test_*geo*.py")
        elif module == "discovery":
            cmd.append("tests/test_package_discovery.py")

    return cmd


def run_test_suite(
        mode: str = "smoke",
        module: Optional[str] = None,
        parallel: bool = False,
        verbose: bool = False,
        install_deps: bool = False,
        setup_environment: bool = True
) -> bool:
    """
    Run a complete test suite with proper environment setup.

    Args:
        mode: Test mode to run
        module: Specific module to test (optional)
        parallel: Run tests in parallel
        verbose: Verbose output
        install_deps: Install test dependencies first
        setup_environment: Set up environment before running tests

    Returns:
        True if all tests pass, False otherwise

    Example:
        >>> import siege_utilities
        >>> success = siege_utilities.run_test_suite(
        >>>     mode="distributed",
        >>>     verbose=True,
        >>>     setup_environment=True
        >>> )
    """
    log_info("Starting siege-utilities test suite...")

    # Ensure we're in the right directory
    if not Path("siege_utilities").exists():
        log_error("Error: siege_utilities directory not found!")
        log_error("Please run this from the project root directory.")
        return False

    # Create reports directory
    Path("reports").mkdir(exist_ok=True)

    # Set up environment if requested
    if setup_environment:
        log_info("Setting up environment...")
        try:
            import siege_utilities
            if not siege_utilities.setup_spark_environment():
                log_warning("Environment setup had issues, continuing anyway...")
        except Exception as e:
            log_error(f"Environment setup failed: {e}")
            return False

    # Install dependencies if requested
    if install_deps:
        log_info("Installing test dependencies...")
        success = run_command([
            sys.executable, "-m", "pip", "install", "-e", ".[dev]"
        ], "Installing test dependencies")

        if not success:
            log_error("Failed to install test dependencies")
            return False

    # Build and run pytest command
    cmd = build_pytest_command(mode, module, parallel, verbose)
    success = run_command(cmd, f"siege-utilities {mode.upper()} tests")

    # Report results
    if success:
        log_info("\nTests completed successfully!")

        # Show coverage report location if generated
        if mode == "coverage" or "cov" in cmd:
            if Path("htmlcov").exists():
                log_info(f"Coverage report: file://{Path('htmlcov/index.html').absolute()}")

        # Show test report location
        if Path("reports/pytest_report.html").exists():
            log_info(f"Test report: file://{Path('reports/pytest_report.html').absolute()}")

    else:
        log_error("\nSome tests failed!")
        log_info("\nDebugging tips:")
        log_info("1. Check the test output above for specific errors")
        log_info("2. Run with verbose=True for more details")
        log_info("3. Run specific test files: pytest tests/test_specific_file.py")
        log_info("4. Run a single test: pytest tests/test_file.py::TestClass::test_method")

    return success


def get_test_report() -> Dict[str, Any]:
    """
    Generate a comprehensive test report.

    Returns:
        Dictionary with test results and system information

    Example:
        >>> import siege_utilities
        >>> report = siege_utilities.get_test_report()
        >>> print(f"Environment healthy: {report['environment_healthy']}")
    """
    report = {
        'timestamp': str(Path.cwd()),
        'environment_healthy': False,
        'smoke_test_passed': False,
        'dependencies': {},
        'system_info': {},
        'suggestions': []
    }

    try:
        # Get system info
        import siege_utilities
        report['system_info'] = siege_utilities.get_system_info()

        # Check environment health
        report['environment_healthy'] = siege_utilities.diagnose_environment()

        # Run smoke test
        report['smoke_test_passed'] = quick_smoke_test()

        # Check dependencies
        report['dependencies'] = siege_utilities.check_dependencies()

        # Generate suggestions
        if not report['environment_healthy']:
            report['suggestions'].append("Run siege_utilities.setup_spark_environment()")

        if not report['smoke_test_passed']:
            report['suggestions'].append("Check package installation and imports")

        missing_deps = [dep for dep, available in report['dependencies'].items()
                        if not available and dep in ['pyspark']]
        if missing_deps:
            report['suggestions'].append(f"Install missing dependencies: {missing_deps}")

    except Exception as e:
        report['error'] = str(e)
        report['suggestions'].append("Check siege_utilities package installation")

    return report


def run_comprehensive_test() -> bool:
    """
    Run comprehensive testing including environment, smoke tests, and full test suite.

    Returns:
        True if all tests pass, False otherwise

    Example:
        >>> import siege_utilities
        >>> if siege_utilities.run_comprehensive_test():
        >>>     print("Everything is working perfectly!")
    """
    log_info("Running comprehensive test suite...")

    all_passed = True

    # Step 1: Environment diagnostics
    log_info("\nStep 1: Environment Diagnostics")
    try:
        import siege_utilities
        env_healthy = siege_utilities.diagnose_environment()
        if not env_healthy:
            log_warning("Environment issues detected, but continuing...")
            all_passed = False
    except Exception as e:
        log_error(f"Environment diagnostics failed: {e}")
        all_passed = False

    # Step 2: Smoke test
    log_info("\nStep 2: Smoke Test")
    smoke_passed = quick_smoke_test()
    if not smoke_passed:
        log_error("Smoke test failed - stopping comprehensive test")
        return False

    # Step 3: Dependency check
    log_info("\nStep 3: Dependency Check")
    try:
        import siege_utilities
        deps = siege_utilities.check_dependencies()
        available = sum(1 for available in deps.values() if available)
        total = len(deps)
        log_info(f"Dependencies: {available}/{total} available")

        if not deps.get('pyspark', False):
            log_warning("PySpark not available - some tests may be skipped")
    except Exception as e:
        log_error(f"Dependency check failed: {e}")
        all_passed = False

    # Step 4: Run test suites
    test_modes = ["smoke", "unit"]

    for mode in test_modes:
        log_info(f"\nStep 4.{test_modes.index(mode) + 1}: {mode.upper()} Tests")
        test_passed = run_test_suite(mode=mode, verbose=False, setup_environment=False)
        if not test_passed:
            log_error(f"{mode.upper()} tests failed")
            all_passed = False

    # Final report
    log_info("\n" + "=" * 60)
    if all_passed:
        log_info("COMPREHENSIVE TEST PASSED!")
        log_info("Environment is healthy")
        log_info("All smoke tests passed")
        log_info("All unit tests passed")
    else:
        log_warning("COMPREHENSIVE TEST HAD ISSUES")
        log_info("Check the logs above for specific problems")
        log_info("Run siege_utilities.get_test_report() for detailed analysis")

    return all_passed

"""
Environment management utilities for siege_utilities.
Handles environment variable setup, Java/Spark environment detection, etc.
"""

import os
import sys
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Import logging functions from main package
try:
    from siege_utilities.core.logging import log_info, log_warning, log_error, log_debug
except ImportError:
    # Fallback if main package not available yet
    def log_info(message): pass
    def log_warning(message): pass
    def log_error(message): pass
    def log_debug(message): pass


def _get_sdkman_root() -> Optional[str]:
    """
    Find SDKMAN installation directory across platforms.

    Checks multiple locations:
    - Standard Linux/macOS: ~/.sdkman/candidates
    - macOS Homebrew: /opt/homebrew/opt/sdkman-cli/libexec/candidates
    - Custom SDKMAN_DIR environment variable

    Returns:
        Path to SDKMAN candidates directory or None if not found
    """
    candidates = [
        os.path.expanduser("~/.sdkman/candidates"),  # Linux/macOS standard
        "/opt/homebrew/opt/sdkman-cli/libexec/candidates",  # macOS Homebrew
        "/usr/local/sdkman/candidates",  # Alternative install location
    ]

    # Check custom SDKMAN_DIR first
    sdkman_dir = os.environ.get("SDKMAN_DIR")
    if sdkman_dir:
        custom_path = os.path.join(sdkman_dir, "candidates")
        candidates.insert(0, custom_path)

    for path in candidates:
        if os.path.exists(path):
            return path

    return None


def _get_system_java_paths() -> List[str]:
    """
    Get common system Java installation paths for Linux.

    Returns:
        List of paths to check for Java installations
    """
    return [
        "/usr/lib/jvm/java-17-openjdk-amd64",
        "/usr/lib/jvm/java-17-openjdk",
        "/usr/lib/jvm/java-11-openjdk-amd64",
        "/usr/lib/jvm/java-11-openjdk",
        "/usr/lib/jvm/java-8-openjdk-amd64",
        "/usr/lib/jvm/java-8-openjdk",
        "/usr/lib/jvm/default-java",
        "/usr/java/latest",
        "/usr/java/default",
    ]


def _get_system_spark_paths() -> List[str]:
    """
    Get common system Spark installation paths.

    Returns:
        List of paths to check for Spark installations
    """
    return [
        "/opt/spark",
        "/usr/local/spark",
        "/usr/share/spark",
        os.path.expanduser("~/spark"),
    ]


def _get_system_hadoop_paths() -> List[str]:
    """
    Get common system Hadoop installation paths.

    Returns:
        List of paths to check for Hadoop installations
    """
    return [
        "/opt/hadoop",
        "/usr/local/hadoop",
        "/usr/share/hadoop",
        os.path.expanduser("~/hadoop"),
    ]


def ensure_env_vars(required_vars: List[str]) -> Dict[str, Optional[str]]:
    """
    Ensure required environment variables are set.
    Checks SDKMAN on Linux and macOS, falls back to system paths.

    Args:
        required_vars: List of environment variable names to check/set

    Returns:
        Dictionary mapping variable names to their resolved values (or None if not found)

    Example:
        >>> import siege_utilities
        >>> resolved = siege_utilities.ensure_env_vars(["JAVA_HOME", "SPARK_HOME"])
        >>> print(f"Java: {resolved['JAVA_HOME']}")
    """
    sdk_root = _get_sdkman_root()
    resolved = {}

    for var in required_vars:
        if os.environ.get(var):
            resolved[var] = os.environ[var]
            log_info(f"{var} already set: {os.environ[var]}")
            continue

        # Try to auto-detect common tools
        if var == "JAVA_HOME":
            java_home = None
            # Try SDKMAN first
            if sdk_root:
                sdkman_java = os.path.join(sdk_root, "java", "current")
                if os.path.exists(sdkman_java):
                    java_home = sdkman_java
            # Fall back to system paths
            if not java_home:
                for sys_path in _get_system_java_paths():
                    if os.path.exists(sys_path):
                        java_home = sys_path
                        break

            if java_home:
                os.environ[var] = java_home
                resolved[var] = java_home
                log_info(f"Auto-detected {var}: {java_home}")
            else:
                resolved[var] = None
                log_warning(f"{var} not found")

        elif var == "SPARK_HOME":
            spark_home = None
            # Try SDKMAN first
            if sdk_root:
                sdkman_spark = os.path.join(sdk_root, "spark", "current")
                if os.path.exists(sdkman_spark):
                    spark_home = sdkman_spark
            # Fall back to system paths
            if not spark_home:
                for sys_path in _get_system_spark_paths():
                    if os.path.exists(sys_path):
                        spark_home = sys_path
                        break

            if spark_home:
                os.environ[var] = spark_home
                resolved[var] = spark_home
                log_info(f"Auto-detected {var}: {spark_home}")
            else:
                resolved[var] = None
                log_warning(f"{var} not found")

        elif var == "HADOOP_HOME":
            hadoop_home = None
            # Try SDKMAN first
            if sdk_root:
                sdkman_hadoop = os.path.join(sdk_root, "hadoop", "current")
                if os.path.exists(sdkman_hadoop):
                    hadoop_home = sdkman_hadoop
            # Fall back to system paths
            if not hadoop_home:
                for sys_path in _get_system_hadoop_paths():
                    if os.path.exists(sys_path):
                        hadoop_home = sys_path
                        break

            if hadoop_home:
                os.environ[var] = hadoop_home
                resolved[var] = hadoop_home
                log_info(f"Auto-detected {var}: {hadoop_home}")
            else:
                resolved[var] = None
                log_warning(f"{var} not found")

        elif var == "SCALA_HOME":
            scala_home = None
            if sdk_root:
                sdkman_scala = os.path.join(sdk_root, "scala", "current")
                if os.path.exists(sdkman_scala):
                    scala_home = sdkman_scala
                    os.environ[var] = scala_home
                    resolved[var] = scala_home
                    log_info(f"Auto-detected {var}: {scala_home}")
                else:
                    resolved[var] = None
                    log_warning(f"{var} not found")
            else:
                resolved[var] = None
                log_warning(f"{var} not found (SDKMAN not available)")

        else:
            resolved[var] = None  # Unknown env var
            log_warning(f"Unknown environment variable: {var}")

    return resolved


def check_java_version() -> Tuple[Optional[str], bool]:
    """
    Check Java version and compatibility.

    Returns:
        Tuple of (version_string, is_compatible)

    Example:
        >>> import siege_utilities
        >>> version, compatible = siege_utilities.check_java_version()
        >>> if compatible:
        >>>     print(f"Java {version} is compatible")
    """
    try:
        result = subprocess.run(['java', '-version'],
                                capture_output=True, text=True)
        java_output = result.stderr

        if 'version "17.' in java_output:
            return "17", True
        elif 'version "11.' in java_output:
            return "11", True
        elif 'version "8.' in java_output:
            return "8", True
        else:
            # Extract version number
            import re
            version_match = re.search(r'version "([^"]+)"', java_output)
            version = version_match.group(1) if version_match else "unknown"
            return version, False

    except Exception as e:
        log_error(f"Could not check Java version: {e}")
        return None, False


def setup_spark_environment() -> bool:
    """
    Set up optimal Spark environment based on current system.

    Returns:
        True if setup successful, False otherwise

    Example:
        >>> import siege_utilities
        >>> if siege_utilities.setup_spark_environment():
        >>>     print("Spark environment ready!")
    """
    log_info("Setting up Spark environment...")

    # Ensure required environment variables
    required_vars = ["JAVA_HOME", "SPARK_HOME"]
    ensure_env_vars(required_vars)

    # Check Java compatibility
    java_version, java_compatible = check_java_version()
    if not java_compatible:
        log_error(f"Java version {java_version} may not be compatible with Spark")
        log_info("Try switching to Java 11 or 17: sdk use java 11.0.27.fx-zulu")
        return False

    log_info(f"Java {java_version} is compatible")

    # Check dependencies
    try:
        import siege_utilities
        deps = siege_utilities.check_dependencies()

        if not deps['pyspark']:
            log_error("PySpark not available")
            log_info("Install with: pip install pyspark")
            return False

        log_info("PySpark is available")

        if deps['apache-sedona']:
            log_info("Apache Sedona is available")
        else:
            log_warning("Apache Sedona not available (optional)")

    except Exception as e:
        log_error(f"Could not check dependencies: {e}")
        return False

    log_info("Spark environment setup complete!")
    return True


def get_system_info() -> Dict[str, str]:
    """
    Get comprehensive system information for debugging.

    Returns:
        Dictionary with system information

    Example:
        >>> import siege_utilities
        >>> info = siege_utilities.get_system_info()
        >>> for key, value in info.items():
        >>>     print(f"{key}: {value}")
    """
    info = {
        'python_version': sys.version,
        'python_executable': sys.executable,
        'platform': sys.platform,
        'working_directory': str(Path.cwd()),
    }

    # Add environment variables
    env_vars = ['JAVA_HOME', 'SPARK_HOME', 'HADOOP_HOME', 'SCALA_HOME', 'PYTHONPATH']
    for var in env_vars:
        info[var] = os.environ.get(var, 'Not set')

    # Add Java version
    java_version, _ = check_java_version()
    info['java_version'] = java_version or 'Not available'

    # Add package info
    try:
        import siege_utilities
        package_info = siege_utilities.get_package_info()
        info['siege_utilities_functions'] = str(package_info['total_functions'])
        info['siege_utilities_modules'] = str(package_info['total_modules'])
    except Exception as e:
        info['siege_utilities_status'] = f'Error: {e}'

    return info


def diagnose_environment() -> bool:
    """
    Run comprehensive environment diagnostics.

    Returns:
        True if environment is healthy, False if issues found

    Example:
        >>> import siege_utilities
        >>> if siege_utilities.diagnose_environment():
        >>>     print("Environment is healthy!")
        >>> else:
        >>>     print("Issues found - check logs")
    """
    log_info("Running environment diagnostics...")

    issues_found = []

    # Check system info
    try:
        info = get_system_info()
        log_info(f"Python: {info['python_version']}")
        log_info(f"Platform: {info['platform']}")
        log_info(f"Working directory: {info['working_directory']}")
    except Exception as e:
        issues_found.append(f"Could not get system info: {e}")

    # Check environment variables
    try:
        required_vars = ["JAVA_HOME", "SPARK_HOME"]
        resolved = ensure_env_vars(required_vars)

        for var, value in resolved.items():
            if value is None:
                issues_found.append(f"Missing environment variable: {var}")
    except Exception as e:
        issues_found.append(f"Environment variable check failed: {e}")

    # Check Java
    try:
        java_version, java_compatible = check_java_version()
        if not java_version:
            issues_found.append("Java not available")
        elif not java_compatible:
            issues_found.append(f"Java version {java_version} may be incompatible")
    except Exception as e:
        issues_found.append(f"Java check failed: {e}")

    # Check dependencies
    try:
        import siege_utilities
        deps = siege_utilities.check_dependencies()

        critical_deps = ['pyspark']
        for dep in critical_deps:
            if not deps.get(dep, False):
                issues_found.append(f"Missing critical dependency: {dep}")

    except Exception as e:
        issues_found.append(f"Dependency check failed: {e}")

    # Report results
    if issues_found:
        log_error(f"Environment diagnostics found {len(issues_found)} issues:")
        for issue in issues_found:
            log_error(f"   {issue}")

        log_info("\nSuggested fixes:")
        log_info("   - Ensure Java 11 or 17 is installed: sdk list java")
        log_info("   - Install missing dependencies: pip install pyspark")
        log_info("   - Set environment variables manually if auto-detection fails")

        return False
    else:
        log_info("Environment diagnostics passed - no issues found!")
        return True


def quick_environment_setup() -> bool:
    """
    One-command environment setup for common scenarios.

    Returns:
        True if setup successful, False otherwise

    Example:
        >>> import siege_utilities
        >>> if siege_utilities.quick_environment_setup():
        >>>     print("Ready to go!")
    """
    log_info("Quick environment setup...")

    try:
        # Step 1: Environment variables
        if not setup_spark_environment():
            return False

        # Step 2: Test basic functionality
        log_info("Testing basic functionality...")
        import siege_utilities

        # Test package import
        info = siege_utilities.get_package_info()
        log_info(f"Package loaded: {info['total_functions']} functions available")

        # Test logging
        siege_utilities.log_info("Environment setup test message")
        log_info("Logging system working")

        # Test string utilities
        result = siege_utilities.remove_wrapping_quotes_and_trim('"test"')
        assert result == "test"
        log_info("String utilities working")

        log_info("Quick environment setup complete!")
        return True

    except Exception as e:
        log_error(f"Quick setup failed: {e}")
        return False

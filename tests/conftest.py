# ================================================================
# FILE: conftest.py
# ================================================================
"""
Shared pytest configuration and fixtures for siege-utilities tests.

The pytest_configure hook runs BEFORE any imports of siege_utilities,
setting environment variables that prevent paths.py from trying to
create directories that don't exist on the current platform.
"""
import pytest
import tempfile
import os
import sys
import shutil
from unittest.mock import Mock

# Add the package to Python path for testing
sys.path.insert(0, os.path.abspath('.'))

# ================================================================
# EARLY HOOKS — run before siege_utilities is imported
# ================================================================

# Module-level temp base so pytest_configure and pytest_unconfigure can share it.
_TEMP_BASE = None


def pytest_configure(config):
    """Set up temp directories and disable auto-init BEFORE siege_utilities imports."""
    global _TEMP_BASE
    _TEMP_BASE = tempfile.mkdtemp(prefix='siege_test_')

    # Prevent paths.py from auto-creating real directories
    os.environ['SIEGE_AUTO_INIT_DIRS'] = 'false'

    # Point all path env vars into the temp tree
    _subdirs = {
        'SIEGE_UTILITIES': 'siege_utilities',
        'SIEGE_UTILITIES_TEST': 'siege_utilities_test',
        'SIEGE': 'siege_analytics',
        'SIEGE_CACHE': 'cache',
        'SPARK_CACHE': 'spark_cache',
        'SIEGE_TEMP': 'temp',
        'SIEGE_OUTPUT': 'output',
        'SIEGE_REPORTS': 'output/reports',
        'SIEGE_CHARTS': 'output/charts',
        'SIEGE_MAPS': 'output/maps',
        'SIEGE_DATA': 'data',
        'CENSUS_DATA': 'data/census',
        'NCES_DATA': 'data/nces',
        'SAMPLE_DATA': 'data/samples',
        'SIEGE_CONFIG': 'config',
        'SIEGE_LOG_DIR': 'logs',
        'SIEGE_BACKUP': 'backups',
    }
    for env_var, subdir in _subdirs.items():
        path = os.path.join(_TEMP_BASE, subdir)
        os.makedirs(path, exist_ok=True)
        os.environ[env_var] = path


def pytest_unconfigure(config):
    """Clean up the temp directory tree and reset singletons after the session."""
    global _TEMP_BASE
    if _TEMP_BASE and os.path.isdir(_TEMP_BASE):
        shutil.rmtree(_TEMP_BASE, ignore_errors=True)
    _TEMP_BASE = None

    # Reset Settings singleton so it doesn't leak between test runs
    from siege_utilities.conf import Settings
    Settings._reset()


@pytest.fixture(autouse=True, scope='session')
def _siege_test_directories():
    """Ensure the standard directory tree exists under the temp base.

    Runs once per session after pytest_configure has set up the env vars.
    """
    base = os.environ.get('SIEGE_UTILITIES', '')
    if base:
        for subdir in ['config', 'data', 'logs', 'output', 'cache']:
            os.makedirs(os.path.join(base, subdir), exist_ok=True)
    yield


@pytest.fixture
def api_credentials():
    """Load connector API credentials from a developer-local YAML file.

    Looked up at ``~/.siege-test-credentials.yaml`` (or the path in the
    ``SIEGE_TEST_CREDENTIALS`` env var). When the file is absent, tests
    decorated with ``@pytest.mark.requires_api_key`` and consuming this
    fixture are skipped — by design, Sprint B's strategy is
    developer-local creds, not CI secrets. CI is expected to run only
    the mock unit tests; the live-API path is opt-in via
    ``pytest -m requires_api_key``.

    Returns the parsed dict; individual connectors look up their own
    sub-keys (e.g. ``creds["snowflake"]["account"]``) and skip if
    their section is missing.
    """
    import yaml  # local import — yaml is in extras_require, not core

    path = os.environ.get("SIEGE_TEST_CREDENTIALS") or os.path.expanduser(
        "~/.siege-test-credentials.yaml"
    )
    if not os.path.exists(path):
        pytest.skip(
            f"requires_api_key: no credentials file at {path}. "
            "Create one with the per-connector keys you want to exercise; "
            "see docs/testing/sprint-b-credentials.md for the schema."
        )
    try:
        with open(path) as f:
            return yaml.safe_load(f) or {}
    except yaml.YAMLError as exc:
        # A malformed file is a real configuration error, not a missing
        # one — surface it as a skip with the parser error so the
        # developer fixes the file rather than chasing an opaque
        # uncaught exception during fixture setup.
        pytest.skip(
            f"requires_api_key: credentials file at {path} is not valid "
            f"YAML — {exc}. Fix the syntax and re-run."
        )


@pytest.fixture
def mock_spark_session():
    """Mock Spark session for distributed computing tests."""
    mock_spark = Mock()
    mock_spark.sparkContext.setLogLevel = Mock()
    mock_spark.read.parquet = Mock(return_value=Mock())
    mock_spark.createDataFrame = Mock(return_value=Mock())
    mock_spark.sql = Mock(return_value=Mock())
    # Builder pattern for create_spark_session tests
    mock_spark.builder = Mock()
    mock_spark.builder.appName.return_value = mock_spark.builder
    mock_spark.builder.master.return_value = mock_spark.builder
    mock_spark.builder.config.return_value = mock_spark.builder
    mock_spark.builder.getOrCreate.return_value = mock_spark
    # Conf for Sedona settings
    mock_spark.conf = Mock()
    mock_spark.conf.set = Mock()
    return mock_spark

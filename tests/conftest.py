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
from pathlib import Path
from unittest.mock import Mock

REPO_ROOT = Path(__file__).resolve().parents[1]

try:
    from hypothesis import settings as hyp_settings
    from hypothesis.database import DirectoryBasedExampleDatabase

    # Tests run in a per-test cwd (see _isolated_cwd), so the example database
    # needs an absolute home to keep replaying failures across runs.
    _hyp_db = DirectoryBasedExampleDatabase(str(REPO_ROOT / ".hypothesis" / "examples"))
    hyp_settings.register_profile("ci", max_examples=100, database=_hyp_db)
    hyp_settings.register_profile("dev", max_examples=50, database=_hyp_db)
    hyp_settings.register_profile("thorough", max_examples=1000, database=_hyp_db)
    hyp_settings.load_profile(os.environ.get("HYPOTHESIS_PROFILE", "ci"))
except (ImportError, RuntimeError):
    pass

# Add the package to Python path for testing
sys.path.insert(0, os.path.abspath('.'))

# ================================================================
# EARLY HOOKS -- run before siege_utilities is imported
# ================================================================

# Module-level temp base so pytest_configure and pytest_unconfigure can share it.
_TEMP_BASE = None
_SAVED_HOME_ENV = {}

# Tool state the suite needs from the real home: the DuckDB extensions CI
# prepares, Java/Spark discovery (siege_utilities/testing/environment.py), the
# Spark jar caches, git identity, and the Jupyter kernels CI registers with
# `ipykernel install --user` (Linux and macOS data dirs). Everything else in
# HOME starts empty (#1693).
_HOME_PASSTHROUGH = (
    '.duckdb', '.sdkman', 'spark', 'hadoop', '.ivy2', '.m2', '.gitconfig', '.config/git',
    '.local/share/jupyter', 'Library/Jupyter',
)


def _isolate_home(base: str) -> None:
    """Point HOME at an empty directory so library defaults under Path.home() stay out of it.

    pytest-django imports parts of siege_utilities before this runs; none of
    them read Path.home() at import time, and anything imported later sees
    the isolated HOME.
    """
    # xdist workers inherit the parent's isolated HOME; keep the original.
    real_home = Path(os.environ.get('SIEGE_TEST_REAL_HOME') or Path.home())
    fake_home = Path(base) / 'home'
    fake_home.mkdir()
    for name in _HOME_PASSTHROUGH:
        source = real_home / name
        if source.exists():
            link = fake_home / name
            link.parent.mkdir(parents=True, exist_ok=True)
            link.symlink_to(source, target_is_directory=source.is_dir())
    for var in ('HOME', 'USERPROFILE', 'SIEGE_TEST_REAL_HOME'):
        _SAVED_HOME_ENV[var] = os.environ.get(var)
    os.environ['SIEGE_TEST_REAL_HOME'] = str(real_home)
    os.environ['HOME'] = str(fake_home)
    if sys.platform == 'win32':
        os.environ['USERPROFILE'] = str(fake_home)


def _restore_home() -> None:
    for var, value in _SAVED_HOME_ENV.items():
        if value is None:
            os.environ.pop(var, None)
        else:
            os.environ[var] = value
    _SAVED_HOME_ENV.clear()


# Test-run controls (database targets, credentials file, the real home). CI
# sets these and the library never reads them.
_SIEGE_TEST_CONTROL_PREFIXES = ('SIEGE_TEST_', 'SIEGE_UTILITIES_TEST_PG_DSN')
_SAVED_SIEGE_ENV = {}


def _drop_inherited_siege_env() -> None:
    """Unset every inherited SIEGE_* variable except the test-run controls.

    The library reads SIEGE_<NAME> for every setting (conf/__init__.py) and
    honours SIEGE_USER_CONFIG_DIR, SIEGE_SETTINGS_FILE and other directory
    overrides, so anything inherited from the developer's shell would point
    the suite at their real config (#1717). pytest_configure sets the
    variables the suite needs afterwards.
    """
    for var in [v for v in os.environ if v.startswith('SIEGE_')]:
        if var.startswith(_SIEGE_TEST_CONTROL_PREFIXES):
            continue
        _SAVED_SIEGE_ENV[var] = os.environ.pop(var)


def _restore_siege_env() -> None:
    for var in [v for v in os.environ if v.startswith('SIEGE_')]:
        if not var.startswith(_SIEGE_TEST_CONTROL_PREFIXES):
            os.environ.pop(var)
    os.environ.update(_SAVED_SIEGE_ENV)
    _SAVED_SIEGE_ENV.clear()


@pytest.hookimpl(tryfirst=True)
def pytest_configure(config):
    """Set up temp directories and disable auto-init BEFORE siege_utilities imports."""
    global _TEMP_BASE
    _TEMP_BASE = tempfile.mkdtemp(prefix='siege_test_')
    _drop_inherited_siege_env()
    _isolate_home(_TEMP_BASE)

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
    _restore_home()
    _restore_siege_env()
    if _TEMP_BASE and os.path.isdir(_TEMP_BASE):
        # Unlink the HOME passthrough symlinks first so cleanup can never
        # reach into the real home they point at.
        for dirpath, dirnames, filenames in os.walk(_TEMP_BASE):
            for name in dirnames + filenames:
                entry = os.path.join(dirpath, name)
                if os.path.islink(entry):
                    os.unlink(entry)
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


@pytest.fixture(autouse=True)
def _isolated_cwd(tmp_path_factory: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch) -> None:
    """Run each test from an empty directory of its own.

    Library defaults such as Path.cwd() / "reports" otherwise land in the
    checkout (#1693). This is a sibling of tmp_path, not tmp_path itself, so
    tests that assert on their tmp_path contents are unaffected.
    """
    monkeypatch.chdir(tmp_path_factory.mktemp("cwd"))


@pytest.fixture
def api_credentials():
    """Load connector API credentials from a developer-local YAML file.

    Looked up at ``~/.siege-test-credentials.yaml`` (or the path in the
    ``SIEGE_TEST_CREDENTIALS`` env var). When the file is absent, tests
    decorated with ``@pytest.mark.requires_api_key`` and consuming this
    fixture are skipped -- credentials are developer-local, not in CI.
    CI runs the mock unit tests; the live-API path is opt-in via
    ``pytest -m requires_api_key``.

    Returns the parsed dict; individual connectors look up their own
    sub-keys (e.g. ``creds["snowflake"]["account"]``) and skip if
    their section is missing.
    """
    import yaml  # local import -- yaml is in extras_require, not core

    # HOME points at the isolated test home, so look in the real one.
    real_home = os.environ.get("SIEGE_TEST_REAL_HOME") or os.path.expanduser("~")
    path = os.environ.get("SIEGE_TEST_CREDENTIALS") or os.path.join(
        real_home, ".siege-test-credentials.yaml"
    )
    if not os.path.exists(path):
        pytest.skip(
            f"requires_api_key: no credentials file at {path}. "
            "Create one with the per-connector keys you want to exercise; "
            "see docs/testing/sprint-b-credentials.md for the schema."
        )
    with open(path) as f:
        try:
            return yaml.safe_load(f) or {}
        except yaml.YAMLError as exc:
            # A malformed creds file is a configuration error; failing
            # makes it visible. The previous behaviour (silent skip)
            # let CI stay green with the live-API smoke runs silently
            # never executing.
            pytest.fail(
                f"requires_api_key: credentials file at {path} is not "
                f"valid YAML: {exc}. Fix the syntax and re-run."
            )


@pytest.fixture(scope="session")
def real_spark_session():
    """Real SparkSession for cross-engine property tests.

    Skips the requesting test cleanly when pyspark isn't installed.
    Session-scoped so the JVM startup cost (5-10 seconds) only happens
    once per pytest run; tests share the session.

    Pins PYSPARK_PYTHON and PYSPARK_DRIVER_PYTHON to the running
    interpreter so Spark workers don't pick up a different Python off
    the PATH and fail with PYTHON_VERSION_MISMATCH. This bites pyenv
    setups where homebrew's python3.14 is first on PATH but the
    driver runs under pyenv's python3.11.
    """
    pytest.importorskip("pyspark")
    os.environ.setdefault("PYSPARK_PYTHON", sys.executable)
    os.environ.setdefault("PYSPARK_DRIVER_PYTHON", sys.executable)
    from pyspark.sql import SparkSession

    spark = (
        SparkSession.builder
        .appName("siege_utilities_property_tests")
        .master("local[2]")
        .config("spark.sql.shuffle.partitions", "2")
        .config("spark.default.parallelism", "2")
        .config("spark.driver.memory", "1g")
        .config("spark.ui.showConsoleProgress", "false")
        .getOrCreate()
    )
    spark.sparkContext.setLogLevel("ERROR")
    yield spark
    spark.stop()


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

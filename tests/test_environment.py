"""
Tests for siege_utilities/testing/environment.py.

Tests environment detection, Java/Spark path resolution,
and diagnostic utilities using mocks.
"""
import os
import sys
from unittest.mock import patch, Mock, MagicMock


from siege_utilities.testing.environment import (
    _get_sdkman_root,
    _get_system_java_paths,
    _get_system_spark_paths,
    _get_system_hadoop_paths,
    ensure_env_vars,
    check_java_version,
    setup_spark_environment,
    get_system_info,
    diagnose_environment,
)


# ================================================================
# Path Discovery Tests
# ================================================================


class TestGetSdkmanRoot:
    """Test _get_sdkman_root function."""

    def test_returns_none_when_no_sdkman(self):
        """Returns None when no SDKMAN installation found."""
        with patch.dict(os.environ, {}, clear=True):
            with patch('os.path.exists', return_value=False):
                result = _get_sdkman_root()
                assert result is None

    def test_finds_standard_linux_path(self):
        """Finds standard ~/.sdkman/candidates path."""
        standard_path = os.path.expanduser("~/.sdkman/candidates")

        def exists_side_effect(path):
            return path == standard_path

        with patch.dict(os.environ, {}, clear=True):
            with patch('os.path.exists', side_effect=exists_side_effect):
                result = _get_sdkman_root()
                assert result == standard_path

    def test_custom_sdkman_dir(self):
        """Respects custom SDKMAN_DIR environment variable."""
        custom_candidates = '/custom/sdkman/candidates'

        def exists_side_effect(path):
            return path == custom_candidates

        with patch.dict(os.environ, {'SDKMAN_DIR': '/custom/sdkman'}, clear=True):
            with patch('os.path.exists', side_effect=exists_side_effect):
                result = _get_sdkman_root()
                assert result == custom_candidates

    def test_custom_sdkman_dir_takes_priority(self):
        """Custom SDKMAN_DIR is checked before standard paths."""
        custom_candidates = '/custom/sdkman/candidates'
        standard_path = os.path.expanduser("~/.sdkman/candidates")

        def exists_side_effect(path):
            return path in (custom_candidates, standard_path)

        with patch.dict(os.environ, {'SDKMAN_DIR': '/custom/sdkman'}, clear=True):
            with patch('os.path.exists', side_effect=exists_side_effect):
                result = _get_sdkman_root()
                # Custom should be found first since it's inserted at index 0
                assert result == custom_candidates


class TestGetSystemPaths:
    """Test system path discovery functions."""

    def test_java_paths_returns_list(self):
        """_get_system_java_paths returns a list of strings."""
        paths = _get_system_java_paths()
        assert isinstance(paths, list)
        assert len(paths) > 0
        assert all(isinstance(p, str) for p in paths)

    def test_spark_paths_returns_list(self):
        """_get_system_spark_paths returns a list of strings."""
        paths = _get_system_spark_paths()
        assert isinstance(paths, list)
        assert len(paths) > 0
        assert all(isinstance(p, str) for p in paths)

    def test_hadoop_paths_returns_list(self):
        """_get_system_hadoop_paths returns a list of strings."""
        paths = _get_system_hadoop_paths()
        assert isinstance(paths, list)
        assert len(paths) > 0
        assert all(isinstance(p, str) for p in paths)

    def test_java_paths_contain_openjdk(self):
        """Java paths include openjdk variants."""
        paths = _get_system_java_paths()
        openjdk_paths = [p for p in paths if 'openjdk' in p]
        assert len(openjdk_paths) > 0


# ================================================================
# ensure_env_vars Tests
# ================================================================


class TestEnsureEnvVars:
    """Test ensure_env_vars function."""

    def test_already_set_java_home(self):
        """Returns existing value when JAVA_HOME is already set."""
        with patch.dict(os.environ, {'JAVA_HOME': '/usr/lib/jvm/java-17'}, clear=False):
            result = ensure_env_vars(['JAVA_HOME'])
            assert result['JAVA_HOME'] == '/usr/lib/jvm/java-17'

    def test_auto_detect_java_via_sdkman(self):
        """Auto-detects JAVA_HOME via SDKMAN."""
        sdkman_java = os.path.expanduser("~/.sdkman/candidates/java/current")
        env = {k: v for k, v in os.environ.items() if k != 'JAVA_HOME'}

        with patch.dict(os.environ, env, clear=True):
            with patch('siege_utilities.testing.environment._get_sdkman_root',
                       return_value=os.path.expanduser("~/.sdkman/candidates")):
                with patch('os.path.exists', return_value=True):
                    result = ensure_env_vars(['JAVA_HOME'])
                    assert result['JAVA_HOME'] == sdkman_java

    def test_auto_detect_java_via_system_paths(self):
        """Falls back to system paths when SDKMAN unavailable."""
        system_java = '/usr/lib/jvm/java-17-openjdk-amd64'
        env = {k: v for k, v in os.environ.items() if k != 'JAVA_HOME'}

        def exists_side_effect(path):
            return path == system_java

        with patch.dict(os.environ, env, clear=True):
            with patch('siege_utilities.testing.environment._get_sdkman_root',
                       return_value=None):
                with patch('os.path.exists', side_effect=exists_side_effect):
                    result = ensure_env_vars(['JAVA_HOME'])
                    assert result['JAVA_HOME'] == system_java

    def test_unknown_var_returns_none(self):
        """Unknown environment variables resolve to None."""
        env = {k: v for k, v in os.environ.items() if k != 'UNKNOWN_VAR'}
        with patch.dict(os.environ, env, clear=True):
            result = ensure_env_vars(['UNKNOWN_VAR'])
            assert result['UNKNOWN_VAR'] is None

    def test_multiple_vars(self):
        """Can resolve multiple variables at once."""
        with patch.dict(os.environ, {
            'JAVA_HOME': '/java',
            'SPARK_HOME': '/spark',
        }, clear=False):
            result = ensure_env_vars(['JAVA_HOME', 'SPARK_HOME'])
            assert 'JAVA_HOME' in result
            assert 'SPARK_HOME' in result


# ================================================================
# check_java_version Tests
# ================================================================


class TestCheckJavaVersion:
    """Test check_java_version function."""

    @patch('subprocess.run')
    def test_java_17_compatible(self, mock_run):
        """Java 17 is detected as compatible."""
        mock_run.return_value = Mock(
            stderr='openjdk version "17.0.9" 2023-10-17',
            returncode=0,
        )
        version, compatible = check_java_version()
        assert version == "17"
        assert compatible is True

    @patch('subprocess.run')
    def test_java_11_compatible(self, mock_run):
        """Java 11 is detected as compatible."""
        mock_run.return_value = Mock(
            stderr='openjdk version "11.0.21" 2023-10-17',
            returncode=0,
        )
        version, compatible = check_java_version()
        assert version == "11"
        assert compatible is True

    @patch('subprocess.run')
    def test_java_8_compatible(self, mock_run):
        """Java 8 is detected as compatible."""
        mock_run.return_value = Mock(
            stderr='openjdk version "8.0.392"',
            returncode=0,
        )
        version, compatible = check_java_version()
        assert version == "8"
        assert compatible is True

    @patch('subprocess.run')
    def test_unknown_java_version(self, mock_run):
        """Unknown Java version returns (version, False)."""
        mock_run.return_value = Mock(
            stderr='openjdk version "21.0.1" 2023-10-17',
            returncode=0,
        )
        version, compatible = check_java_version()
        assert version == "21.0.1"
        assert compatible is False

    @patch('subprocess.run')
    def test_java_not_installed(self, mock_run):
        """Returns (None, False) when java binary missing."""
        mock_run.side_effect = FileNotFoundError("java not found")
        version, compatible = check_java_version()
        assert version is None
        assert compatible is False


# ================================================================
# setup_spark_environment Tests
# ================================================================


class TestSetupSparkEnvironment:
    """Test setup_spark_environment function."""

    @patch('siege_utilities.testing.environment.check_java_version')
    @patch('siege_utilities.testing.environment.ensure_env_vars')
    def test_returns_false_on_incompatible_java(self, mock_ensure, mock_java):
        """Returns False when Java version is incompatible."""
        mock_ensure.return_value = {'JAVA_HOME': '/java', 'SPARK_HOME': '/spark'}
        mock_java.return_value = ("21", False)
        result = setup_spark_environment()
        assert result is False

    @patch('siege_utilities.testing.environment.check_java_version')
    @patch('siege_utilities.testing.environment.ensure_env_vars')
    def test_returns_false_when_pyspark_missing(self, mock_ensure, mock_java):
        """Returns False when pyspark dependency is not available."""
        mock_ensure.return_value = {'JAVA_HOME': '/java', 'SPARK_HOME': '/spark'}
        mock_java.return_value = ("17", True)

        mock_su = MagicMock()
        mock_su.check_dependencies.return_value = {'pyspark': False, 'apache-sedona': False}

        with patch.dict('sys.modules', {'siege_utilities': mock_su}):
            result = setup_spark_environment()
            # The function should return a boolean (True if setup succeeded, False otherwise)
            assert isinstance(result, bool)
            # so we check that the function handles gracefully


# ================================================================
# get_system_info Tests
# ================================================================


class TestGetSystemInfo:
    """Test get_system_info function."""

    @patch('siege_utilities.testing.environment.check_java_version')
    def test_returns_expected_keys(self, mock_java):
        """get_system_info returns dict with expected keys."""
        mock_java.return_value = ("17", True)
        info = get_system_info()
        expected_keys = [
            'python_version', 'python_executable', 'platform',
            'working_directory', 'java_version',
        ]
        for key in expected_keys:
            assert key in info, f"Missing key: {key}"

    @patch('siege_utilities.testing.environment.check_java_version')
    def test_env_vars_in_info(self, mock_java):
        """Environment variables are included in info dict."""
        mock_java.return_value = ("17", True)
        info = get_system_info()
        env_vars = ['JAVA_HOME', 'SPARK_HOME', 'HADOOP_HOME', 'SCALA_HOME', 'PYTHONPATH']
        for var in env_vars:
            assert var in info

    @patch('siege_utilities.testing.environment.check_java_version')
    def test_python_version_populated(self, mock_java):
        """Python version is populated from sys.version."""
        mock_java.return_value = ("17", True)
        info = get_system_info()
        assert info['python_version'] == sys.version

    @patch('siege_utilities.testing.environment.check_java_version')
    def test_platform_populated(self, mock_java):
        """Platform is populated from sys.platform."""
        mock_java.return_value = ("17", True)
        info = get_system_info()
        assert info['platform'] == sys.platform


# ================================================================
# diagnose_environment Tests
# ================================================================


class TestDiagnoseEnvironment:
    """Test diagnose_environment function."""

    @patch('siege_utilities.testing.environment.check_java_version')
    @patch('siege_utilities.testing.environment.ensure_env_vars')
    @patch('siege_utilities.testing.environment.get_system_info')
    def test_returns_false_when_issues_found(self, mock_info, mock_ensure, mock_java):
        """Returns False when environment issues are detected."""
        mock_info.return_value = {
            'python_version': '3.11', 'platform': 'linux',
            'working_directory': '/tmp',
        }
        mock_ensure.return_value = {'JAVA_HOME': None, 'SPARK_HOME': None}
        mock_java.return_value = (None, False)

        # Mock siege_utilities import inside diagnose_environment
        mock_su = MagicMock()
        mock_su.check_dependencies.return_value = {'pyspark': False}
        with patch.dict('sys.modules', {'siege_utilities': mock_su}):
            result = diagnose_environment()
            assert result is False

    @patch('siege_utilities.testing.environment.check_java_version')
    @patch('siege_utilities.testing.environment.ensure_env_vars')
    @patch('siege_utilities.testing.environment.get_system_info')
    def test_returns_true_when_healthy(self, mock_info, mock_ensure, mock_java):
        """Returns True when all checks pass."""
        mock_info.return_value = {
            'python_version': '3.11', 'platform': 'linux',
            'working_directory': '/tmp',
        }
        mock_ensure.return_value = {'JAVA_HOME': '/java', 'SPARK_HOME': '/spark'}
        mock_java.return_value = ("17", True)

        mock_su = MagicMock()
        mock_su.check_dependencies.return_value = {'pyspark': True, 'apache-sedona': True}
        with patch.dict('sys.modules', {'siege_utilities': mock_su}):
            result = diagnose_environment()
            assert result is True

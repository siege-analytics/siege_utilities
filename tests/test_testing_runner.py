# ================================================================
# FILE: test_testing_runner.py
# ================================================================
"""
Tests for siege_utilities.testing.runner module.

Covers:
- run_command (subprocess execution with and without log files)
- build_pytest_command (mode/module/flag combinations)
- run_test_suite (environment setup, dependency install, reporting)
- quick_smoke_test (basic import and function checks)
- get_test_report (report structure and error handling)
- run_comprehensive_test (multi-step orchestration)
"""

import sys
from unittest.mock import patch, MagicMock, mock_open

from siege_utilities.testing.runner import (
    run_command,
    build_pytest_command,
    run_test_suite,
    quick_smoke_test,
    get_test_report,
    run_comprehensive_test,
)


# ----------------------------------------------------------------
# run_command
# ----------------------------------------------------------------


class TestRunCommand:
    """Tests for run_command()."""

    @patch("siege_utilities.testing.runner.subprocess.run")
    def test_success_without_log_file(self, mock_run):
        """Successful command returns True when no log file is specified."""
        mock_run.return_value = MagicMock(returncode=0)
        result = run_command(["echo", "hello"], "Echo test")
        assert result is True
        mock_run.assert_called_once_with(["echo", "hello"])

    @patch("siege_utilities.testing.runner.subprocess.run")
    def test_failure_without_log_file(self, mock_run):
        """Failed command returns False when no log file is specified."""
        mock_run.return_value = MagicMock(returncode=1)
        result = run_command(["false"], "Should fail")
        assert result is False

    @patch("siege_utilities.testing.runner.subprocess.Popen")
    @patch("builtins.open", new_callable=mock_open)
    def test_success_with_log_file(self, mock_file, mock_popen):
        """Successful command with log file writes output and returns True."""
        proc = MagicMock()
        proc.stdout = iter(["line1\n", "line2\n"])
        proc.communicate.return_value = ("", "")
        proc.returncode = 0
        mock_popen.return_value = proc

        result = run_command(["echo", "hello"], "Echo test", log_file="/tmp/test.log")

        assert result is True
        mock_file.assert_called_once_with("/tmp/test.log", "w")
        handle = mock_file()
        assert handle.write.call_count == 2

    @patch("siege_utilities.testing.runner.subprocess.Popen")
    @patch("builtins.open", new_callable=mock_open)
    def test_log_file_captures_stderr(self, mock_file, mock_popen):
        """When log file is specified, stderr is captured and written."""
        proc = MagicMock()
        proc.stdout = iter([])
        proc.communicate.return_value = ("", "some error output")
        proc.returncode = 1
        mock_popen.return_value = proc

        result = run_command(["bad_cmd"], "Failing cmd", log_file="/tmp/err.log")

        assert result is False
        handle = mock_file()
        # stderr should be written to the log file
        handle.write.assert_called_with("some error output")

    @patch("siege_utilities.testing.runner.subprocess.Popen")
    @patch("builtins.open", new_callable=mock_open)
    def test_log_file_no_stderr(self, mock_file, mock_popen):
        """When there is no stderr, only stdout lines are written."""
        proc = MagicMock()
        proc.stdout = iter(["output\n"])
        proc.communicate.return_value = ("", "")
        proc.returncode = 0
        mock_popen.return_value = proc

        result = run_command(["ok"], "OK cmd", log_file="/tmp/ok.log")

        assert result is True
        handle = mock_file()
        # Only the one stdout line
        handle.write.assert_called_once_with("output\n")


# ----------------------------------------------------------------
# build_pytest_command
# ----------------------------------------------------------------


class TestBuildPytestCommand:
    """Tests for build_pytest_command()."""

    def test_smoke_mode_defaults(self):
        """Smoke mode adds --maxfail, --tb=short, and -x."""
        cmd = build_pytest_command(mode="smoke")
        assert sys.executable in cmd[0]
        assert "-m" in cmd and "pytest" in cmd
        assert "--maxfail=10" in cmd
        assert "--tb=short" in cmd
        assert "-x" in cmd

    def test_fast_mode(self):
        """Fast mode filters slow tests."""
        cmd = build_pytest_command(mode="fast")
        # Find the pytest marker -m (not the module -m for python -m pytest)
        # The marker -m comes after "pytest" in the command
        pytest_idx = cmd.index("pytest")
        marker_indices = [i for i in range(pytest_idx + 1, len(cmd)) if cmd[i] == "-m"]
        assert len(marker_indices) == 1
        assert cmd[marker_indices[0] + 1] == "not slow"
        assert "--maxfail=5" in cmd

    def test_unit_mode(self):
        """Unit mode uses correct marker expression."""
        cmd = build_pytest_command(mode="unit")
        pytest_idx = cmd.index("pytest")
        marker_indices = [i for i in range(pytest_idx + 1, len(cmd)) if cmd[i] == "-m"]
        assert len(marker_indices) == 1
        assert cmd[marker_indices[0] + 1] == "unit or not integration"

    def test_coverage_mode(self):
        """Coverage mode adds cov flags."""
        cmd = build_pytest_command(mode="coverage")
        assert "--cov=siege_utilities" in cmd
        assert "--cov-report=html:htmlcov" in cmd
        assert "--cov-report=term-missing" in cmd
        assert "--cov-report=xml:coverage.xml" in cmd
        assert "--cov-fail-under=60" in cmd

    def test_all_mode(self):
        """All mode does not add extra filters."""
        cmd = build_pytest_command(mode="all")
        # Should just be the base command without mode-specific flags
        assert "--maxfail=10" not in cmd
        assert "--cov=siege_utilities" not in cmd

    def test_verbose_flag(self):
        """Verbose adds -vv, -s, --tb=long."""
        cmd = build_pytest_command(mode="all", verbose=True)
        assert "-vv" in cmd
        assert "-s" in cmd
        assert "--tb=long" in cmd

    def test_parallel_flag(self):
        """Parallel adds -n auto."""
        cmd = build_pytest_command(mode="all", parallel=True)
        assert "-n" in cmd
        assert "auto" in cmd

    def test_module_core(self):
        """Module 'core' appends correct test path pattern."""
        cmd = build_pytest_command(mode="all", module="core")
        assert "tests/test_core_*.py" in cmd

    def test_module_files(self):
        """Module 'files' appends correct test path pattern."""
        cmd = build_pytest_command(mode="all", module="files")
        assert "tests/test_*file*.py" in cmd

    def test_module_distributed(self):
        """Module 'distributed' appends correct test path pattern."""
        cmd = build_pytest_command(mode="all", module="distributed")
        assert "tests/test_*spark*.py" in cmd

    def test_module_geo(self):
        """Module 'geo' appends correct test path pattern."""
        cmd = build_pytest_command(mode="all", module="geo")
        assert "tests/test_*geo*.py" in cmd

    def test_module_discovery(self):
        """Module 'discovery' appends correct test path pattern."""
        cmd = build_pytest_command(mode="all", module="discovery")
        assert "tests/test_package_discovery.py" in cmd

    def test_no_module(self):
        """No module means no test path appended."""
        cmd = build_pytest_command(mode="all", module=None)
        assert not any("tests/" in arg for arg in cmd)

    def test_combined_flags(self):
        """Verbose + parallel + module combine correctly."""
        cmd = build_pytest_command(
            mode="smoke", module="geo", parallel=True, verbose=True
        )
        assert "-vv" in cmd
        assert "-n" in cmd
        assert "tests/test_*geo*.py" in cmd
        assert "--maxfail=10" in cmd


# ----------------------------------------------------------------
# run_test_suite
# ----------------------------------------------------------------


class TestRunTestSuite:
    """Tests for run_test_suite()."""

    @patch("siege_utilities.testing.runner.run_command", return_value=True)
    @patch("siege_utilities.testing.runner.build_pytest_command", return_value=["pytest"])
    @patch("siege_utilities.testing.runner.Path")
    def test_missing_project_dir_returns_false(self, mock_path_cls, mock_build, mock_run):
        """Returns False when siege_utilities directory doesn't exist."""
        instance = MagicMock()
        instance.exists.return_value = False
        mock_path_cls.side_effect = lambda x: instance if x == "siege_utilities" else MagicMock()

        result = run_test_suite(setup_environment=False)
        assert result is False

    @patch("siege_utilities.testing.runner.run_command", return_value=True)
    @patch("siege_utilities.testing.runner.build_pytest_command", return_value=["pytest"])
    @patch("siege_utilities.testing.runner.Path")
    def test_successful_run(self, mock_path_cls, mock_build, mock_run):
        """Successful test run returns True."""
        path_instances = {}

        def path_factory(arg):
            if arg not in path_instances:
                m = MagicMock()
                m.exists.return_value = True if arg == "siege_utilities" else False
                m.mkdir = MagicMock()
                path_instances[arg] = m
            return path_instances[arg]

        mock_path_cls.side_effect = path_factory

        result = run_test_suite(setup_environment=False)
        assert result is True

    @patch("siege_utilities.testing.runner.run_command")
    @patch("siege_utilities.testing.runner.build_pytest_command", return_value=["pytest"])
    @patch("siege_utilities.testing.runner.Path")
    def test_install_deps_failure_returns_false(self, mock_path_cls, mock_build, mock_run):
        """Returns False when dependency installation fails."""
        path_instances = {}

        def path_factory(arg):
            if arg not in path_instances:
                m = MagicMock()
                m.exists.return_value = True if arg == "siege_utilities" else False
                m.mkdir = MagicMock()
                path_instances[arg] = m
            return path_instances[arg]

        mock_path_cls.side_effect = path_factory
        # First call (install deps) fails
        mock_run.return_value = False

        result = run_test_suite(setup_environment=False, install_deps=True)
        assert result is False

    @patch("siege_utilities.testing.runner.run_command")
    @patch("siege_utilities.testing.runner.build_pytest_command", return_value=["pytest"])
    @patch("siege_utilities.testing.runner.Path")
    def test_setup_environment_exception(self, mock_path_cls, mock_build, mock_run):
        """Returns False when setup_spark_environment raises."""
        path_instances = {}

        def path_factory(arg):
            if arg not in path_instances:
                m = MagicMock()
                m.exists.return_value = True if arg == "siege_utilities" else False
                m.mkdir = MagicMock()
                path_instances[arg] = m
            return path_instances[arg]

        mock_path_cls.side_effect = path_factory

        with patch("siege_utilities.testing.runner.log_info"), \
             patch("siege_utilities.testing.runner.log_error"):
            with patch.dict("sys.modules", {"siege_utilities": MagicMock(
                setup_spark_environment=MagicMock(side_effect=RuntimeError("boom"))
            )}):
                result = run_test_suite(setup_environment=True)
                assert result is False


# ----------------------------------------------------------------
# quick_smoke_test
# ----------------------------------------------------------------


class TestQuickSmokeTest:
    """Tests for quick_smoke_test()."""

    @patch("siege_utilities.testing.runner.log_info")
    def test_smoke_test_success(self, mock_log):
        """Smoke test returns True when all checks pass."""
        mock_su = MagicMock()
        mock_su.get_package_info.return_value = {"total_functions": 42}
        mock_su.remove_wrapping_quotes_and_trim.return_value = "test"
        mock_su.check_dependencies.return_value = {"pyspark": True, "pandas": True}

        with patch.dict("sys.modules", {"siege_utilities": mock_su}):
            result = quick_smoke_test()
        assert result is True

    @patch("siege_utilities.testing.runner.log_error")
    @patch("siege_utilities.testing.runner.log_info")
    def test_smoke_test_failure(self, mock_log_info, mock_log_error):
        """Smoke test returns False when an exception is raised."""
        mock_su = MagicMock()
        mock_su.get_package_info.side_effect = RuntimeError("broken")

        with patch.dict("sys.modules", {"siege_utilities": mock_su}):
            result = quick_smoke_test()
        assert result is False

    @patch("siege_utilities.testing.runner.log_error")
    @patch("siege_utilities.testing.runner.log_info")
    def test_smoke_test_assertion_failure(self, mock_log_info, mock_log_error):
        """Smoke test returns False when string util assertion fails."""
        mock_su = MagicMock()
        mock_su.get_package_info.return_value = {"total_functions": 10}
        # Return wrong value so assertion fails
        mock_su.remove_wrapping_quotes_and_trim.return_value = "wrong"
        mock_su.check_dependencies.return_value = {}

        with patch.dict("sys.modules", {"siege_utilities": mock_su}):
            result = quick_smoke_test()
        assert result is False


# ----------------------------------------------------------------
# get_test_report
# ----------------------------------------------------------------


class TestGetTestReport:
    """Tests for get_test_report()."""

    @patch("siege_utilities.testing.runner.quick_smoke_test", return_value=True)
    def test_report_structure_success(self, mock_smoke):
        """Report has expected keys when everything succeeds."""
        mock_su = MagicMock()
        mock_su.get_system_info.return_value = {"python": "3.11"}
        mock_su.diagnose_environment.return_value = True
        mock_su.check_dependencies.return_value = {"pyspark": True}

        with patch.dict("sys.modules", {"siege_utilities": mock_su}):
            report = get_test_report()

        assert report["environment_healthy"] is True
        assert report["smoke_test_passed"] is True
        assert report["dependencies"] == {"pyspark": True}
        assert report["system_info"] == {"python": "3.11"}
        assert report["suggestions"] == []

    @patch("siege_utilities.testing.runner.quick_smoke_test", return_value=False)
    def test_report_unhealthy_environment(self, mock_smoke):
        """Report generates suggestions when environment is unhealthy."""
        mock_su = MagicMock()
        mock_su.get_system_info.return_value = {}
        mock_su.diagnose_environment.return_value = False
        mock_su.check_dependencies.return_value = {"pyspark": False}

        with patch.dict("sys.modules", {"siege_utilities": mock_su}):
            report = get_test_report()

        assert report["environment_healthy"] is False
        assert report["smoke_test_passed"] is False
        assert any("setup_spark_environment" in s for s in report["suggestions"])
        assert any("imports" in s for s in report["suggestions"])
        assert any("pyspark" in s for s in report["suggestions"])

    @patch("siege_utilities.testing.runner.quick_smoke_test", return_value=True)
    def test_report_handles_exception(self, mock_smoke):
        """Report captures exception info when siege_utilities is broken."""
        with patch.dict("sys.modules", {"siege_utilities": MagicMock(
            get_system_info=MagicMock(side_effect=ImportError("no module"))
        )}):
            report = get_test_report()

        assert "error" in report
        assert "no module" in report["error"]
        assert any("installation" in s for s in report["suggestions"])


# ----------------------------------------------------------------
# run_comprehensive_test
# ----------------------------------------------------------------


class TestRunComprehensiveTest:
    """Tests for run_comprehensive_test()."""

    @patch("siege_utilities.testing.runner.run_test_suite", return_value=True)
    @patch("siege_utilities.testing.runner.quick_smoke_test", return_value=True)
    def test_all_pass(self, mock_smoke, mock_suite):
        """Returns True when environment, smoke, and suite all pass."""
        mock_su = MagicMock()
        mock_su.diagnose_environment.return_value = True
        mock_su.check_dependencies.return_value = {"pyspark": True}

        with patch.dict("sys.modules", {"siege_utilities": mock_su}):
            result = run_comprehensive_test()

        assert result is True
        # Should run smoke and unit suites
        assert mock_suite.call_count == 2

    @patch("siege_utilities.testing.runner.run_test_suite", return_value=True)
    @patch("siege_utilities.testing.runner.quick_smoke_test", return_value=False)
    def test_smoke_failure_stops_early(self, mock_smoke, mock_suite):
        """Returns False immediately when smoke test fails."""
        mock_su = MagicMock()
        mock_su.diagnose_environment.return_value = True

        with patch.dict("sys.modules", {"siege_utilities": mock_su}):
            result = run_comprehensive_test()

        assert result is False
        # Should NOT have run the test suites
        mock_suite.assert_not_called()

    @patch("siege_utilities.testing.runner.run_test_suite")
    @patch("siege_utilities.testing.runner.quick_smoke_test", return_value=True)
    def test_test_suite_failure(self, mock_smoke, mock_suite):
        """Returns False when one of the test suites fails."""
        # smoke suite passes, unit suite fails
        mock_suite.side_effect = [True, False]
        mock_su = MagicMock()
        mock_su.diagnose_environment.return_value = True
        mock_su.check_dependencies.return_value = {"pyspark": True}

        with patch.dict("sys.modules", {"siege_utilities": mock_su}):
            result = run_comprehensive_test()

        assert result is False

    @patch("siege_utilities.testing.runner.run_test_suite", return_value=True)
    @patch("siege_utilities.testing.runner.quick_smoke_test", return_value=True)
    def test_environment_diagnostics_failure(self, mock_smoke, mock_suite):
        """Returns False when environment diagnostics returns unhealthy."""
        mock_su = MagicMock()
        mock_su.diagnose_environment.return_value = False
        mock_su.check_dependencies.return_value = {"pyspark": True}

        with patch.dict("sys.modules", {"siege_utilities": mock_su}):
            result = run_comprehensive_test()

        # all_passed should be False due to env issues, even though suites pass
        assert result is False

    @patch("siege_utilities.testing.runner.run_test_suite", return_value=True)
    @patch("siege_utilities.testing.runner.quick_smoke_test", return_value=True)
    def test_environment_exception(self, mock_smoke, mock_suite):
        """Handles exception during environment diagnostics gracefully."""
        mock_su = MagicMock()
        mock_su.diagnose_environment.side_effect = RuntimeError("env broke")
        mock_su.check_dependencies.return_value = {}

        with patch.dict("sys.modules", {"siege_utilities": mock_su}):
            result = run_comprehensive_test()

        assert result is False

    @patch("siege_utilities.testing.runner.run_test_suite", return_value=True)
    @patch("siege_utilities.testing.runner.quick_smoke_test", return_value=True)
    def test_dependency_check_exception(self, mock_smoke, mock_suite):
        """Handles exception during dependency check gracefully."""
        mock_su = MagicMock()
        mock_su.diagnose_environment.return_value = True
        mock_su.check_dependencies.side_effect = RuntimeError("deps broke")

        with patch.dict("sys.modules", {"siege_utilities": mock_su}):
            result = run_comprehensive_test()

        # all_passed becomes False from dep check failure, but suites still run
        assert result is False

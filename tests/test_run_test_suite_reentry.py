"""Re-entrancy guard for the test runner (#1342).

run_test_suite / run_comprehensive_test launch a subprocess pytest over the
whole suite. Called from inside a running pytest, that subprocess re-runs every
test -- including the caller -- and recurses combinatorially (observed during
the #1199 sweep: calling run_comprehensive_test collected 7000+ items and began
re-executing the suite).

The guard lives in run_command (the subprocess seam) and fires only for a
pytest spawn while PYTEST_CURRENT_TEST is set. This is deliberately narrow:
non-pytest subprocesses (pip install, etc.) are unaffected, and tests that mock
run_command never reach the guard, so run_test_suite / run_comprehensive_test
remain fully testable via mocks. These tests patch subprocess so the real
guard runs without ever launching a nested suite.
"""

from unittest.mock import patch

import siege_utilities.testing.runner as runner


class TestRunCommandReentryGuard:
    def test_run_command_refuses_pytest_spawn_inside_pytest(self):
        # PYTEST_CURRENT_TEST is set by pytest for every running test, so the
        # guard condition holds here without us setting anything. subprocess
        # is patched to prove the guard returns BEFORE any spawn.
        with patch.object(runner.subprocess, "run") as mock_run, \
                patch.object(runner.subprocess, "Popen") as mock_popen:
            result = runner.run_command(
                ["python", "-m", "pytest", "tests/"], "nested pytest"
            )
        assert result is False
        mock_run.assert_not_called()
        mock_popen.assert_not_called()

    def test_run_command_allows_non_pytest_subprocess(self):
        # A non-pytest command (e.g. pip) must NOT be blocked by the guard;
        # the real subprocess is reached (patched here to avoid a real call).
        with patch.object(runner.subprocess, "run") as mock_run:
            mock_run.return_value.returncode = 0
            result = runner.run_command(
                ["python", "-m", "pip", "list"], "pip list"
            )
        assert result is True
        mock_run.assert_called_once()

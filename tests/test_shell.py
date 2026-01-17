# ================================================================
# FILE: test_shell.py
# ================================================================
"""
Tests for siege_utilities.files.shell module.
These tests expose issues with shell command execution.
"""
import pytest
import subprocess
from unittest.mock import patch, Mock
import siege_utilities


class TestShellOperations:
    """Test shell command execution and expose bugs."""

    @patch('subprocess.Popen')
    def test_run_subprocess_success(self, mock_popen):
        """Test successful subprocess execution."""
        # Mock successful process
        mock_process = Mock()
        mock_process.communicate.return_value = (b'output data', b'')
        mock_process.returncode = 0
        mock_popen.return_value = mock_process

        command = ['echo', 'hello']
        result = siege_utilities.run_subprocess(command)

        assert result == 'output data'

        # Check that Popen was called correctly (shell=False for security)
        mock_popen.assert_called_once_with(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=False
        )

    @patch('subprocess.Popen')
    def test_run_subprocess_error(self, mock_popen):
        """Test subprocess execution with error (using allowed command)."""
        # Mock failed process
        mock_process = Mock()
        mock_process.communicate.return_value = (b'', b'error message')
        mock_process.returncode = 1
        mock_popen.return_value = mock_process

        # Use an allowed command that would fail in execution
        command = ['ls', '/nonexistent/path']
        result = siege_utilities.run_subprocess(command)

        assert result == 'error message'

    def test_run_subprocess_security_blocks_invalid_command(self):
        """Test that security validation blocks non-allowed commands."""
        from siege_utilities.files.shell import SecurityError

        command = ['invalid_command']
        with pytest.raises(SecurityError):
            siege_utilities.run_subprocess(command)

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

        # Check that Popen was called correctly
        mock_popen.assert_called_once_with(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=True
        )

    @patch('subprocess.Popen')
    def test_run_subprocess_error(self, mock_popen):
        """Test subprocess execution with error."""
        # Mock failed process
        mock_process = Mock()
        mock_process.communicate.return_value = (b'', b'error message')
        mock_process.returncode = 1
        mock_popen.return_value = mock_process

        command = ['invalid_command']
        result = siege_utilities.run_subprocess(command)

        assert result == 'error message'

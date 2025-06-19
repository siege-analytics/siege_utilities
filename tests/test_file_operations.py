# ================================================================
# FILE: test_file_operations.py
# ================================================================
"""
Tests for siege_utilities.files.operations module.
These tests are designed to expose bugs in file operation functions.
"""
import pytest
import pathlib
import subprocess
import io
from unittest.mock import patch, Mock
import siege_utilities


class TestFileOperations:
    """Test file operation functions and expose bugs."""

    def test_check_if_file_exists_at_path_exists(self, sample_file):
        """Test file existence check with existing file."""
        result = siege_utilities.check_if_file_exists_at_path(sample_file)
        assert result == True

    def test_check_if_file_exists_at_path_missing(self, temp_directory):
        """Test file existence check with missing file."""
        missing_file = temp_directory / "missing.txt"
        result = siege_utilities.check_if_file_exists_at_path(missing_file)
        assert result == False

    def test_delete_existing_file_and_replace_it_with_an_empty_file_existing(self, temp_directory):
        """Test file deletion and replacement with existing file."""
        test_file = temp_directory / "test_replace.txt"
        original_content = "original content"
        test_file.write_text(original_content)

        result = siege_utilities.delete_existing_file_and_replace_it_with_an_empty_file(test_file)

        assert result == test_file
        assert test_file.exists()
        assert test_file.read_text() == ""

    def test_count_total_rows_in_file_pythonically_bug(self, sample_file):
        """Test Python-based row counting - this should expose a bug."""
        # The function has a bug: it uses `target_file_path` in the loop instead of `f`
        # This will likely cause a TypeError or unexpected behavior

        with pytest.raises(Exception):
            # This should fail due to the bug in the implementation
            count = siege_utilities.count_total_rows_in_file_pythonically(sample_file)

    @patch('subprocess.run')
    def test_count_duplicate_rows_in_file_using_awk_success(self, mock_run, sample_file):
        """Test awk-based duplicate row counting with successful execution."""
        mock_run.return_value = Mock(
            returncode=0,
            stdout="5",
            stderr=None
        )

        count = siege_utilities.count_duplicate_rows_in_file_using_awk(sample_file)
        assert count == 5
        mock_run.assert_called_once()

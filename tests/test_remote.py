# ================================================================
# FILE: test_remote.py
# ================================================================
"""
Tests for siege_utilities.files.remote module.
These tests expose issues with remote file operations.
"""
import pytest
import pathlib
from unittest.mock import patch, Mock, mock_open, MagicMock
import siege_utilities


class TestRemoteOperations:
    """Test remote file operations and expose bugs."""

    def test_generate_local_path_from_url_basic(self, temp_directory):
        """Test generating local path from URL."""
        url = "https://example.com/path/to/file.txt"
        result = siege_utilities.generate_local_path_from_url(url, temp_directory)

        expected = str(temp_directory / "file.txt")
        assert result == expected
        assert isinstance(result, str)  # as_string=True by default

    def test_generate_local_path_from_url_as_path(self, temp_directory):
        """Test generating local path as Path object."""
        url = "https://example.com/file.csv"
        result = siege_utilities.generate_local_path_from_url(
            url, temp_directory, as_string=False
        )

        expected = temp_directory / "file.csv"
        assert result == expected
        assert isinstance(result, pathlib.Path)

    @patch('requests.get')
    def test_download_file_success(self, mock_get, temp_directory):
        """Test successful file download."""
        # Create mock response
        mock_response = Mock()
        mock_response.ok = True
        mock_response.headers = {'content-length': '1024'}
        mock_response.iter_content.return_value = [b'chunk1', b'chunk2', b'chunk3']
        mock_get.return_value.__enter__.return_value = mock_response

        url = "https://example.com/test.txt"
        local_file = temp_directory / "downloaded.txt"

        # Mock tqdm to avoid import issues
        with patch('siege_utilities.files.remote.tqdm') as mock_tqdm:
            mock_tqdm.return_value.__enter__.return_value.update = Mock()

            result = siege_utilities.download_file(url, str(local_file))

        assert result == str(local_file)
        assert local_file.exists()

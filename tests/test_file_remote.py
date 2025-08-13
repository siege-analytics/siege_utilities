"""
Comprehensive tests for the modernized remote file module.
Tests all functionality including file downloads, path generation, and retry logic.
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock, Mock
import requests
from requests.exceptions import Timeout, RequestException

from siege_utilities.files.remote import (
    download_file, generate_local_path_from_url, download_file_with_retry,
    get_file_info, is_downloadable
)


class TestDownloadFile:
    """Test download_file function."""
    
    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.test_file = self.temp_dir / "test.txt"
        self.test_file.write_text("Test content")
    
    def teardown_method(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    @patch('requests.get')
    def test_download_file_success(self, mock_get):
        """Test successful file download."""
        # Mock successful response
        mock_response = Mock()
        mock_response.ok = True
        mock_response.headers = {'content-length': '100'}
        mock_response.iter_content.return_value = [b"Test content"]
        
        mock_get.return_value.__enter__.return_value = mock_response
        
        # Test download
        result = download_file("https://example.com/test.txt", self.temp_dir / "downloaded.txt")
        
        assert result is not False
        assert Path(result).exists()
        assert Path(result).read_text() == "Test content"
    
    @patch('requests.get')
    def test_download_file_http_error(self, mock_get):
        """Test download with HTTP error."""
        # Mock failed response
        mock_response = Mock()
        mock_response.ok = False
        mock_response.status_code = 404
        mock_response.reason = "Not Found"
        
        mock_get.return_value.__enter__.return_value = mock_response
        
        # Test download
        result = download_file("https://example.com/test.txt", self.temp_dir / "downloaded.txt")
        
        assert result is False
    
    @patch('requests.get')
    def test_download_file_timeout(self, mock_get):
        """Test download with timeout."""
        mock_get.side_effect = Timeout("Request timed out")
        
        # Test download
        result = download_file("https://example.com/test.txt", self.temp_dir / "downloaded.txt")
        
        assert result is False
    
    @patch('requests.get')
    def test_download_file_request_exception(self, mock_get):
        """Test download with request exception."""
        mock_get.side_effect = RequestException("Network error")
        
        # Test download
        result = download_file("https://example.com/test.txt", self.temp_dir / "downloaded.txt")
        
        assert result is False
    
    @patch('requests.get')
    def test_download_file_unknown_size(self, mock_get):
        """Test download with unknown file size."""
        # Mock response with no content-length
        mock_response = Mock()
        mock_response.ok = True
        mock_response.headers = {}
        mock_response.iter_content.return_value = [b"Test content"]
        
        mock_get.return_value.__enter__.return_value = mock_response
        
        # Test download
        result = download_file("https://example.com/test.txt", self.temp_dir / "downloaded.txt")
        
        assert result is not False
        assert Path(result).exists()
    
    @patch('requests.get')
    def test_download_file_custom_chunk_size(self, mock_get):
        """Test download with custom chunk size."""
        # Mock successful response
        mock_response = Mock()
        mock_response.ok = True
        mock_response.headers = {'content-length': '100'}
        mock_response.iter_content.return_value = [b"Test content"]
        
        mock_get.return_value.__enter__.return_value = mock_response
        
        # Test download with custom chunk size
        result = download_file("https://example.com/test.txt", self.temp_dir / "downloaded.txt", chunk_size=2048)
        
        assert result is not False
        assert Path(result).exists()
    
    @patch('requests.get')
    def test_download_file_custom_timeout(self, mock_get):
        """Test download with custom timeout."""
        # Mock successful response
        mock_response = Mock()
        mock_response.ok = True
        mock_response.headers = {'content-length': '100'}
        mock_response.iter_content.return_value = [b"Test content"]
        
        mock_get.return_value.__enter__.return_value = mock_response
        
        # Test download with custom timeout
        result = download_file("https://example.com/test.txt", self.temp_dir / "downloaded.txt", timeout=60)
        
        assert result is not False
        assert Path(result).exists()
    
    @patch('requests.get')
    def test_download_file_verify_ssl_false(self, mock_get):
        """Test download with SSL verification disabled."""
        # Mock successful response
        mock_response = Mock()
        mock_response.ok = True
        mock_response.headers = {'content-length': '100'}
        mock_response.iter_content.return_value = [b"Test content"]
        
        mock_get.return_value.__enter__.return_value = mock_response
        
        # Test download with SSL verification disabled
        result = download_file("https://example.com/test.txt", self.temp_dir / "downloaded.txt", verify_ssl=False)
        
        assert result is not False
        assert Path(result).exists()
    
    def test_download_file_creates_parent_directories(self):
        """Test that download_file creates parent directories."""
        deep_path = self.temp_dir / "deep" / "nested" / "downloaded.txt"
        
        with patch('requests.get') as mock_get:
            # Mock successful response
            mock_response = Mock()
            mock_response.ok = True
            mock_response.headers = {'content-length': '100'}
            mock_response.iter_content.return_value = [b"Test content"]
            
            mock_get.return_value.__enter__.return_value = mock_response
            
            # Test download
            result = download_file("https://example.com/test.txt", deep_path)
            
            assert result is not False
            assert deep_path.exists()
            assert deep_path.parent.exists()


class TestGenerateLocalPathFromUrl:
    """Test generate_local_path_from_url function."""
    
    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
    
    def teardown_method(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_generate_local_path_from_url_simple(self):
        """Test simple URL path generation."""
        result = generate_local_path_from_url("https://example.com/file.txt", self.temp_dir)
        
        assert result is not False
        expected_path = self.temp_dir / "file.txt"
        assert result == str(expected_path)
    
    def test_generate_local_path_from_url_complex(self):
        """Test complex URL path generation."""
        result = generate_local_path_from_url("https://example.com/path/to/file.zip", self.temp_dir)
        
        assert result is not False
        expected_path = self.temp_dir / "file.zip"
        assert result == str(expected_path)
    
    def test_generate_local_path_from_url_no_filename(self):
        """Test URL with no filename."""
        result = generate_local_path_from_url("https://example.com/", self.temp_dir)
        
        assert result is False
    
    def test_generate_local_path_from_url_empty_filename(self):
        """Test URL with empty filename."""
        result = generate_local_path_from_url("https://example.com//", self.temp_dir)
        
        assert result is False
    
    def test_generate_local_path_from_url_as_path_object(self):
        """Test returning Path object instead of string."""
        result = generate_local_path_from_url("https://example.com/file.txt", self.temp_dir, as_string=False)
        
        assert result is not False
        assert isinstance(result, Path)
        expected_path = self.temp_dir / "file.txt"
        assert result == expected_path
    
    def test_generate_local_path_from_url_creates_directory(self):
        """Test that function creates directory if it doesn't exist."""
        new_dir = self.temp_dir / "new_dir"
        
        result = generate_local_path_from_url("https://example.com/file.txt", new_dir)
        
        assert result is not False
        assert new_dir.exists()


class TestDownloadFileWithRetry:
    """Test download_file_with_retry function."""
    
    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
    
    def teardown_method(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    @patch('siege_utilities.files.remote.download_file')
    def test_download_file_with_retry_success_first_try(self, mock_download):
        """Test successful download on first try."""
        mock_download.return_value = "success.txt"
        
        result = download_file_with_retry("https://example.com/file.txt", self.temp_dir / "downloaded.txt")
        
        assert result == "success.txt"
        mock_download.assert_called_once()
    
    @patch('siege_utilities.files.remote.download_file')
    def test_download_file_with_retry_success_after_retries(self, mock_download):
        """Test successful download after retries."""
        # First two attempts fail, third succeeds
        mock_download.side_effect = [False, False, "success.txt"]
        
        result = download_file_with_retry("https://example.com/file.txt", self.temp_dir / "downloaded.txt", max_retries=3)
        
        assert result == "success.txt"
        assert mock_download.call_count == 3
    
    @patch('time.sleep')
    @patch('siege_utilities.files.remote.download_file')
    def test_download_file_with_retry_delay(self, mock_download, mock_sleep):
        """Test that retry delay is respected."""
        mock_download.side_effect = [False, False, False, False]
        
        result = download_file_with_retry("https://example.com/file.txt", self.temp_dir / "downloaded.txt", 
                                        max_retries=3, retry_delay=2)
        
        assert result is False
        assert mock_download.call_count == 4
        # Should sleep between retries
        assert mock_sleep.call_count == 3
    
    @patch('siege_utilities.files.remote.download_file')
    def test_download_file_with_retry_all_failures(self, mock_download):
        """Test that all retry attempts fail."""
        mock_download.return_value = False
        
        result = download_file_with_retry("https://example.com/file.txt", self.temp_dir / "downloaded.txt", 
                                        max_retries=2)
        
        assert result is False
        assert mock_download.call_count == 3  # Initial + 2 retries
    
    @patch('siege_utilities.files.remote.download_file')
    def test_download_file_with_retry_exception_handling(self, mock_download):
        """Test that exceptions during retries are handled."""
        mock_download.side_effect = [Exception("Network error"), Exception("Timeout"), "success.txt"]
        
        result = download_file_with_retry("https://example.com/file.txt", self.temp_dir / "downloaded.txt", 
                                        max_retries=3)
        
        assert result == "success.txt"
        assert mock_download.call_count == 3


class TestGetFileInfo:
    """Test get_file_info function."""
    
    @patch('requests.head')
    def test_get_file_info_success(self, mock_head):
        """Test successful file info retrieval."""
        # Mock successful response
        mock_response = Mock()
        mock_response.ok = True
        mock_response.headers = {
            'content-length': '1024',
            'content-type': 'text/plain',
            'last-modified': 'Wed, 21 Oct 2015 07:28:00 GMT',
            'etag': '"abc123"'
        }
        
        mock_head.return_value = mock_response
        
        result = get_file_info("https://example.com/file.txt")
        
        assert result is not None
        assert result['url'] == "https://example.com/file.txt"
        assert result['size'] == 1024
        assert result['content_type'] == 'text/plain'
        assert result['last_modified'] == 'Wed, 21 Oct 2015 07:28:00 GMT'
        assert result['etag'] == '"abc123"'
    
    @patch('requests.head')
    def test_get_file_info_http_error(self, mock_head):
        """Test file info retrieval with HTTP error."""
        # Mock failed response
        mock_response = Mock()
        mock_response.ok = False
        mock_response.status_code = 404
        
        mock_head.return_value = mock_response
        
        result = get_file_info("https://example.com/file.txt")
        
        assert result is None
    
    @patch('requests.head')
    def test_get_file_info_exception(self, mock_head):
        """Test file info retrieval with exception."""
        mock_head.side_effect = Exception("Network error")
        
        result = get_file_info("https://example.com/file.txt")
        
        assert result is None
    
    @patch('requests.head')
    def test_get_file_info_custom_timeout(self, mock_head):
        """Test file info retrieval with custom timeout."""
        # Mock successful response
        mock_response = Mock()
        mock_response.ok = True
        mock_response.headers = {'content-length': '1024'}
        
        mock_head.return_value = mock_response
        
        result = get_file_info("https://example.com/file.txt", timeout=30)
        
        assert result is not None
        mock_head.assert_called_once()
        # Check that timeout was passed
        call_args = mock_head.call_args
        assert call_args[1]['timeout'] == 30


class TestIsDownloadable:
    """Test is_downloadable function."""
    
    @patch('siege_utilities.files.remote.get_file_info')
    def test_is_downloadable_with_size(self, mock_get_info):
        """Test downloadable check with file size."""
        mock_get_info.return_value = {'size': 1024}
        
        result = is_downloadable("https://example.com/file.txt")
        
        assert result is True
    
    @patch('siege_utilities.files.remote.get_file_info')
    @patch('requests.get')
    def test_is_downloadable_no_size_but_accessible(self, mock_get, mock_get_info):
        """Test downloadable check with no size but accessible content."""
        mock_get_info.return_value = {'size': 0}
        
        # Mock successful GET request
        mock_response = Mock()
        mock_response.ok = True
        mock_get.return_value = mock_response
        
        result = is_downloadable("https://example.com/file.txt")
        
        assert result is True
    
    @patch('siege_utilities.files.remote.get_file_info')
    @patch('requests.get')
    def test_is_downloadable_not_accessible(self, mock_get, mock_get_info):
        """Test downloadable check with inaccessible content."""
        mock_get_info.return_value = {'size': 0}
        
        # Mock failed GET request
        mock_response = Mock()
        mock_response.ok = False
        mock_get.return_value = mock_response
        
        result = is_downloadable("https://example.com/file.txt")
        
        assert result is False
    
    @patch('siege_utilities.files.remote.get_file_info')
    def test_is_downloadable_exception(self, mock_get_info):
        """Test downloadable check with exception."""
        mock_get_info.side_effect = Exception("Network error")
        
        result = is_downloadable("https://example.com/file.txt")
        
        assert result is False


class TestIntegration:
    """Test integration scenarios."""
    
    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
    
    def teardown_method(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    @patch('requests.get')
    def test_full_download_workflow(self, mock_get):
        """Test complete download workflow."""
        # Mock successful response
        mock_response = Mock()
        mock_response.ok = True
        mock_response.headers = {'content-length': '100'}
        mock_response.iter_content.return_value = [b"Test content"]
        
        mock_get.return_value.__enter__.return_value = mock_response
        
        # Generate path
        local_path = generate_local_path_from_url("https://example.com/file.txt", self.temp_dir)
        assert local_path is not False
        
        # Download file
        result = download_file("https://example.com/file.txt", local_path)
        assert result is not False
        
        # Verify file exists and has content
        assert Path(result).exists()
        assert Path(result).read_text() == "Test content"
    
    @patch('requests.head')
    @patch('requests.get')
    def test_download_with_info_check(self, mock_get, mock_head):
        """Test download with prior info check."""
        # Mock info response
        mock_head_response = Mock()
        mock_head_response.ok = True
        mock_head_response.headers = {'content-length': '100'}
        mock_head.return_value = mock_head_response
        
        # Mock download response
        mock_get_response = Mock()
        mock_get_response.ok = True
        mock_get_response.headers = {'content-length': '100'}
        mock_get_response.iter_content.return_value = [b"Test content"]
        mock_get.return_value.__enter__.return_value = mock_get_response
        
        # Check if downloadable
        assert is_downloadable("https://example.com/file.txt") is True
        
        # Get file info
        info = get_file_info("https://example.com/file.txt")
        assert info is not None
        assert info['size'] == 100
        
        # Download file
        result = download_file("https://example.com/file.txt", self.temp_dir / "downloaded.txt")
        assert result is not False


if __name__ == "__main__":
    pytest.main([__file__])

# ================================================================
# FILE: test_paths.py
# ================================================================
"""
Tests for siege_utilities.files.paths module.
These tests expose issues with path manipulation functions.
"""
import pytest
import pathlib
import zipfile
import siege_utilities


class TestPathOperations:
    """Test path utility functions and expose bugs."""

    def test_ensure_path_exists_new_directory(self, temp_directory):
        """Test creating new directory."""
        new_dir = temp_directory / "new_directory"
        result = siege_utilities.ensure_path_exists(new_dir)

        assert result == new_dir
        assert new_dir.exists()
        assert new_dir.is_dir()

        # Check for .gitkeep file
        gitkeep_file = new_dir / ".gitkeep"
        assert gitkeep_file.exists()
        assert gitkeep_file.read_text() == ""

    def test_unzip_file_to_its_own_directory_basic(self, sample_zip_file):
        """Test basic unzipping functionality."""
        result = siege_utilities.unzip_file_to_directory(sample_zip_file)

        assert result is not False
        assert result.exists()
        assert result.is_dir()

        # Check that files were extracted
        assert (result / "file1.txt").exists()
        assert (result / "dir" / "file2.txt").exists()

        # Verify content
        assert (result / "file1.txt").read_text() == "Content of file 1"
        assert (result / "dir" / "file2.txt").read_text() == "Content of file 2"

    def test_unzip_invalid_file(self, temp_directory):
        """Test unzipping invalid/non-zip file."""
        invalid_file = temp_directory / "not_a_zip.txt"
        invalid_file.write_text("This is not a zip file")

        result = siege_utilities.unzip_file_to_directory(invalid_file)
        assert result is None

"""
Comprehensive tests for the modernized file operations module.
Tests all functionality including file manipulation, directory operations, and command execution.
"""

import pytest
import tempfile
import shutil
from pathlib import Path
import subprocess
from unittest.mock import patch, MagicMock

from siege_utilities.files.operations import (
    remove_tree, file_exists, touch_file, count_lines,
    copy_file, move_file, get_file_size, list_directory,
    run_command
)


class TestFileOperations:
    """Test file operation functions."""
    
    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.test_file = self.temp_dir / "test.txt"
        self.test_dir = self.temp_dir / "test_dir"
        
        # Create test file
        self.test_file.write_text("Line 1\nLine 2\nLine 3\n")
        
        # Create test directory
        self.test_dir.mkdir()
        (self.test_dir / "file1.txt").write_text("Content 1")
        (self.test_dir / "file2.txt").write_text("Content 2")
    
    def teardown_method(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_remove_tree_file(self):
        """Test removing a file with remove_tree."""
        assert self.test_file.exists()
        
        result = remove_tree(self.test_file)
        assert result is True
        assert not self.test_file.exists()
    
    def test_remove_tree_directory(self):
        """Test removing a directory with remove_tree."""
        assert self.test_dir.exists()
        
        result = remove_tree(self.test_dir)
        assert result is True
        assert not self.test_dir.exists()
    
    def test_remove_tree_nonexistent(self):
        """Test removing non-existent path with remove_tree."""
        nonexistent = self.temp_dir / "nonexistent"
        
        result = remove_tree(nonexistent)
        assert result is False
    
    def test_file_exists_true(self):
        """Test file_exists with existing file."""
        result = file_exists(self.test_file)
        assert result is True
    
    def test_file_exists_false(self):
        """Test file_exists with non-existent file."""
        nonexistent = self.temp_dir / "nonexistent.txt"
        result = file_exists(nonexistent)
        assert result is False
    
    def test_file_exists_with_string_path(self):
        """Test file_exists with string path."""
        result = file_exists(str(self.test_file))
        assert result is True
    
    def test_touch_file_new(self):
        """Test touch_file creating new file."""
        new_file = self.temp_dir / "new_file.txt"
        
        result = touch_file(new_file)
        assert result is True
        assert new_file.exists()
        assert new_file.stat().st_size == 0
    
    def test_touch_file_existing(self):
        """Test touch_file with existing file."""
        result = touch_file(self.test_file)
        assert result is True
        assert self.test_file.exists()
    
    def test_touch_file_with_parents(self):
        """Test touch_file creating parent directories."""
        deep_file = self.temp_dir / "deep" / "nested" / "file.txt"
        
        result = touch_file(deep_file, create_parents=True)
        assert result is True
        assert deep_file.exists()
        assert deep_file.parent.exists()
    
    def test_touch_file_without_parents(self):
        """Test touch_file without creating parents."""
        deep_file = self.temp_dir / "deep" / "nested" / "file.txt"
        
        result = touch_file(deep_file, create_parents=False)
        assert result is False  # Should fail without parents
    
    def test_count_lines(self):
        """Test count_lines function."""
        result = count_lines(self.test_file)
        assert result == 3
    
    def test_count_lines_nonexistent(self):
        """Test count_lines with non-existent file."""
        nonexistent = self.temp_dir / "nonexistent.txt"
        result = count_lines(nonexistent)
        assert result is None
    
    def test_count_lines_not_file(self):
        """Test count_lines with directory."""
        result = count_lines(self.test_dir)
        assert result is None
    
    def test_count_lines_with_encoding(self):
        """Test count_lines with specific encoding."""
        # Create file with special characters
        special_file = self.temp_dir / "special.txt"
        special_file.write_text("Line 1\nLine 2\n", encoding='utf-8')
        
        result = count_lines(special_file, encoding='utf-8')
        assert result == 2
    
    def test_copy_file(self):
        """Test copy_file function."""
        dest_file = self.temp_dir / "copied.txt"
        
        result = copy_file(self.test_file, dest_file)
        assert result is True
        assert dest_file.exists()
        assert dest_file.read_text() == self.test_file.read_text()
    
    def test_copy_file_nonexistent_source(self):
        """Test copy_file with non-existent source."""
        nonexistent = self.temp_dir / "nonexistent.txt"
        dest_file = self.temp_dir / "dest.txt"
        
        result = copy_file(nonexistent, dest_file)
        assert result is False
    
    def test_copy_file_source_is_directory(self):
        """Test copy_file with directory as source."""
        dest_file = self.temp_dir / "dest.txt"
        
        result = copy_file(self.test_dir, dest_file)
        assert result is False
    
    def test_copy_file_destination_exists_no_overwrite(self):
        """Test copy_file with existing destination and no overwrite."""
        dest_file = self.temp_dir / "dest.txt"
        dest_file.write_text("Original content")
        
        result = copy_file(self.test_file, dest_file, overwrite=False)
        assert result is False
        assert dest_file.read_text() == "Original content"
    
    def test_copy_file_destination_exists_with_overwrite(self):
        """Test copy_file with existing destination and overwrite."""
        dest_file = self.temp_dir / "dest.txt"
        dest_file.write_text("Original content")
        
        result = copy_file(self.test_file, dest_file, overwrite=True)
        assert result is True
        assert dest_file.read_text() == self.test_file.read_text()
    
    def test_copy_file_creates_dest_parents(self):
        """Test copy_file creates destination parent directories."""
        dest_file = self.temp_dir / "deep" / "nested" / "copied.txt"
        
        result = copy_file(self.test_file, dest_file)
        assert result is True
        assert dest_file.exists()
        assert dest_file.parent.exists()
    
    def test_move_file(self):
        """Test move_file function."""
        dest_file = self.temp_dir / "moved.txt"
        
        result = move_file(self.test_file, dest_file)
        assert result is True
        assert dest_file.exists()
        assert not self.test_file.exists()
        assert dest_file.read_text() == "Line 1\nLine 2\nLine 3\n"
    
    def test_move_file_nonexistent_source(self):
        """Test move_file with non-existent source."""
        nonexistent = self.temp_dir / "nonexistent.txt"
        dest_file = self.temp_dir / "dest.txt"
        
        result = move_file(nonexistent, dest_file)
        assert result is False
    
    def test_move_file_source_is_directory(self):
        """Test move_file with directory as source."""
        dest_file = self.temp_dir / "dest.txt"
        
        result = move_file(self.test_dir, dest_file)
        assert result is False
    
    def test_move_file_destination_exists_no_overwrite(self):
        """Test move_file with existing destination and no overwrite."""
        dest_file = self.temp_dir / "dest.txt"
        dest_file.write_text("Original content")
        
        result = move_file(self.test_file, dest_file, overwrite=False)
        assert result is False
        assert dest_file.read_text() == "Original content"
        assert self.test_file.exists()  # Source should still exist
    
    def test_move_file_destination_exists_with_overwrite(self):
        """Test move_file with existing destination and overwrite."""
        dest_file = self.temp_dir / "dest.txt"
        dest_file.write_text("Original content")
        
        result = move_file(self.test_file, dest_file, overwrite=True)
        assert result is True
        assert dest_file.read_text() == "Line 1\nLine 2\nLine 3\n"
        assert not self.test_file.exists()  # Source should be moved
    
    def test_get_file_size(self):
        """Test get_file_size function."""
        result = get_file_size(self.test_file)
        assert result == 21  # "Line 1\nLine 2\nLine 3\n" = 21 bytes
    
    def test_get_file_size_nonexistent(self):
        """Test get_file_size with non-existent file."""
        nonexistent = self.temp_dir / "nonexistent.txt"
        result = get_file_size(nonexistent)
        assert result is None
    
    def test_get_file_size_not_file(self):
        """Test get_file_size with directory."""
        result = get_file_size(self.test_dir)
        assert result is None
    
    def test_list_directory(self):
        """Test list_directory function."""
        result = list_directory(self.temp_dir)
        
        assert result is not None
        assert len(result) >= 2  # test.txt and test_dir
        assert self.test_file in result
        assert self.test_dir in result
    
    def test_list_directory_nonexistent(self):
        """Test list_directory with non-existent directory."""
        nonexistent = self.temp_dir / "nonexistent"
        result = list_directory(nonexistent)
        assert result is None
    
    def test_list_directory_not_directory(self):
        """Test list_directory with file."""
        result = list_directory(self.test_file)
        assert result is None
    
    def test_list_directory_with_pattern(self):
        """Test list_directory with glob pattern."""
        result = list_directory(self.temp_dir, pattern="*.txt")
        
        assert result is not None
        assert len(result) >= 1
        assert all(f.name.endswith('.txt') for f in result)
    
    def test_list_directory_files_only(self):
        """Test list_directory with files only."""
        result = list_directory(self.temp_dir, include_dirs=False, include_files=True)
        
        assert result is not None
        assert all(f.is_file() for f in result)
    
    def test_list_directory_dirs_only(self):
        """Test list_directory with directories only."""
        result = list_directory(self.temp_dir, include_dirs=True, include_files=False)
        
        assert result is not None
        assert all(f.is_dir() for f in result)
    
    def test_list_directory_recursive(self):
        """Test list_directory with recursive search."""
        # Create nested structure
        nested_dir = self.temp_dir / "nested"
        nested_dir.mkdir()
        (nested_dir / "deep_file.txt").write_text("Deep content")
        
        # Note: list_directory doesn't support recursive search yet
        # This test documents the current limitation
        result = list_directory(self.temp_dir, pattern="*.txt")
        
        assert result is not None
        # Should only find files in the current directory, not nested
        assert len(result) >= 1  # test.txt
        assert all("deep_file.txt" not in str(f) for f in result)
    
    def test_list_directory_recursive_not_supported(self):
        """Test that recursive search is not yet supported."""
        with pytest.raises(TypeError):
            list_directory(self.temp_dir, pattern="*.txt", recursive=True)
    
    def test_run_command_string(self):
        """Test run_command with string command."""
        result = run_command("echo 'Hello World'")
        
        assert result is not None
        assert result.returncode == 0
        assert "Hello World" in result.stdout
    
    def test_run_command_list(self):
        """Test run_command with list command."""
        result = run_command(["echo", "Hello World"])
        
        assert result is not None
        assert result.returncode == 0
        assert "Hello World" in result.stdout
    
    def test_run_command_with_cwd(self):
        """Test run_command with working directory."""
        result = run_command("pwd", cwd=self.temp_dir)
        
        assert result is not None
        assert result.returncode == 0
        assert str(self.temp_dir) in result.stdout
    
    def test_run_command_with_timeout(self):
        """Test run_command with timeout."""
        result = run_command("sleep 2", timeout=1)
        
        assert result is None  # Should timeout
    
    def test_run_command_failed(self):
        """Test run_command with failing command."""
        result = run_command("nonexistent_command")
        
        assert result is not None
        assert result.returncode != 0
    
    def test_run_command_no_capture(self):
        """Test run_command without capturing output."""
        result = run_command("echo 'Hello'", capture_output=False)
        
        assert result is not None
        assert result.returncode == 0


class TestBackwardCompatibility:
    """Test backward compatibility aliases."""
    
    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.test_file = self.temp_dir / "test.txt"
        self.test_file.write_text("Test content")
    
    def teardown_method(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_rmtree_alias(self):
        """Test rmtree alias for remove_tree."""
        from siege_utilities.files.operations import rmtree
        
        assert self.test_file.exists()
        result = rmtree(self.test_file)
        assert result is True
        assert not self.test_file.exists()
    
    def test_check_if_file_exists_at_path_alias(self):
        """Test check_if_file_exists_at_path alias for file_exists."""
        from siege_utilities.files.operations import check_if_file_exists_at_path
        
        result = check_if_file_exists_at_path(self.test_file)
        assert result is True
    
    def test_delete_existing_file_and_replace_it_with_an_empty_file_alias(self):
        """Test delete_existing_file_and_replace_it_with_an_empty_file alias for touch_file."""
        from siege_utilities.files.operations import delete_existing_file_and_replace_it_with_an_empty_file
        
        result = delete_existing_file_and_replace_it_with_an_empty_file(self.test_file)
        assert result is True
        assert self.test_file.stat().st_size == 0
    
    def test_count_total_rows_in_file_pythonically_alias(self):
        """Test count_total_rows_in_file_pythonically alias for count_lines."""
        from siege_utilities.files.operations import count_total_rows_in_file_pythonically
        
        result = count_total_rows_in_file_pythonically(self.test_file)
        assert result == 1


if __name__ == "__main__":
    pytest.main([__file__])

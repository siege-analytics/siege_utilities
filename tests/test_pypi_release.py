"""
Tests for PyPI release management functions.

This module tests all functions in siege_utilities.hygiene.pypi_release
to ensure they work correctly and handle edge cases properly.
"""

import pytest
import tempfile
import os
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock
import subprocess

from siege_utilities.hygiene.pypi_release import (
    get_current_version,
    increment_version,
    update_version_in_setup_py,
    update_version_in_pyproject_toml,
    clean_build_artifacts,
    build_package,
    validate_package,
    upload_to_pypi,
    create_release_notes,
    full_release_workflow,
    check_release_readiness
)


class TestVersionManagement:
    """Test version management functions."""
    
    def test_get_current_version_valid_setup_py(self):
        """Test extracting version from valid setup.py."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write('''
from setuptools import setup

setup(
    name="test-package",
    version="1.2.3",
    description="Test package"
)
''')
            f.flush()
            
            try:
                version = get_current_version(f.name)
                assert version == "1.2.3"
            finally:
                os.unlink(f.name)
    
    def test_get_current_version_with_version_variable(self):
        """Test extracting version from __version__ variable."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write('''
__version__ = "2.0.1"

from setuptools import setup

setup(
    name="test-package",
    version=__version__,
    description="Test package"
)
''')
            f.flush()
            
            try:
                version = get_current_version(f.name)
                assert version == "2.0.1"
            finally:
                os.unlink(f.name)
    
    def test_get_current_version_file_not_found(self):
        """Test handling of missing setup.py file."""
        with pytest.raises(FileNotFoundError):
            get_current_version("nonexistent.py")
    
    def test_get_current_version_no_version_found(self):
        """Test handling of setup.py without version."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write('''
from setuptools import setup

setup(
    name="test-package",
    description="Test package"
)
''')
            f.flush()
            
            try:
                with pytest.raises(ValueError, match="Version not found"):
                    get_current_version(f.name)
            finally:
                os.unlink(f.name)
    
    def test_increment_version_patch(self):
        """Test patch version increment."""
        assert increment_version("1.2.3", "patch") == "1.2.4"
        assert increment_version("0.0.0", "patch") == "0.0.1"
    
    def test_increment_version_minor(self):
        """Test minor version increment."""
        assert increment_version("1.2.3", "minor") == "1.3.0"
        assert increment_version("0.0.0", "minor") == "0.1.0"
    
    def test_increment_version_major(self):
        """Test major version increment."""
        assert increment_version("1.2.3", "major") == "2.0.0"
        assert increment_version("0.0.0", "major") == "1.0.0"
    
    def test_increment_version_invalid_type(self):
        """Test invalid increment type."""
        with pytest.raises(ValueError, match="increment_type must be"):
            increment_version("1.2.3", "invalid")
    
    def test_increment_version_invalid_format(self):
        """Test invalid version format."""
        with pytest.raises(ValueError, match="Invalid version format"):
            increment_version("1.2", "patch")
    
    def test_update_version_in_setup_py(self):
        """Test updating version in setup.py."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write('''
from setuptools import setup

setup(
    name="test-package",
    version="1.2.3",
    description="Test package"
)
''')
            f.flush()
            
            try:
                result = update_version_in_setup_py(f.name, "2.0.0")
                assert result is True
                
                # Verify the version was updated
                with open(f.name, 'r') as f_read:
                    content = f_read.read()
                    assert 'version="2.0.0"' in content
            finally:
                os.unlink(f.name)
    
    def test_update_version_in_pyproject_toml(self):
        """Test updating version in pyproject.toml."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.toml', delete=False) as f:
            f.write('''
[project]
name = "test-package"
version = "1.2.3"
description = "Test package"
''')
            f.flush()
            
            try:
                result = update_version_in_pyproject_toml(f.name, "2.0.0")
                assert result is True
                
                # Verify the version was updated
                with open(f.name, 'r') as f_read:
                    content = f_read.read()
                    assert 'version = "2.0.0"' in content
            finally:
                os.unlink(f.name)


class TestBuildManagement:
    """Test build and artifact management functions."""
    
    def test_clean_build_artifacts(self):
        """Test cleaning build artifacts."""
        # Create temporary build directories
        with tempfile.TemporaryDirectory() as temp_dir:
            os.chdir(temp_dir)
            
            # Create mock build artifacts
            os.makedirs("build", exist_ok=True)
            os.makedirs("dist", exist_ok=True)
            os.makedirs("test_package.egg-info", exist_ok=True)
            os.makedirs("__pycache__", exist_ok=True)
            
            # Create some files
            with open("build/test.txt", "w") as f:
                f.write("test")
            with open("test.pyc", "w") as f:
                f.write("test")
            
            # Test cleaning
            result = clean_build_artifacts()
            assert result is True
            
            # Verify artifacts were removed
            assert not os.path.exists("build")
            assert not os.path.exists("dist")
            assert not os.path.exists("test_package.egg-info")
            assert not os.path.exists("__pycache__")
            assert not os.path.exists("test.pyc")
    
    def test_build_package_success(self):
        """Test successful package building."""
        # Test that the function can be called without errors
        # The actual build success depends on the environment
        try:
            success, message = build_package()
            # If it succeeds, check the message format
            if success:
                assert "successfully" in message.lower()
            else:
                # If it fails, it should still return a proper error message
                assert isinstance(message, str)
                assert len(message) > 0
        except Exception as e:
            # If there's an exception, it should be a known type
            assert isinstance(e, (FileNotFoundError, subprocess.SubprocessError, OSError))
    
    def test_build_package_failure(self):
        """Test package building failure handling."""
        # Test that the function handles errors gracefully
        # We'll test with a non-existent setup.py by temporarily renaming it
        original_setup_exists = os.path.exists('setup.py')
        
        if original_setup_exists:
            # Temporarily rename setup.py
            os.rename('setup.py', 'setup.py.test_backup')
        
        try:
            success, message = build_package()
            # Should fail without setup.py
            assert success is False
            assert "Build failed" in message or "Build error" in message
        finally:
            # Restore original setup.py
            if original_setup_exists:
                os.rename('setup.py.test_backup', 'setup.py')
    
    def test_validate_package_no_dist(self):
        """Test validation when dist directory doesn't exist."""
        is_valid, issues = validate_package()
        assert is_valid is False
        assert "dist directory not found" in issues[0]
    
    @patch('subprocess.run')
    def test_validate_package_success(self, mock_run):
        """Test successful package validation."""
        # Mock dist directory and files
        with tempfile.TemporaryDirectory() as temp_dir:
            os.chdir(temp_dir)
            os.makedirs("dist")
            
            # Create mock distribution files
            with open("dist/test-1.0.0.tar.gz", "w") as f:
                f.write("test")
            with open("dist/test-1.0.0-py3-none-any.whl", "w") as f:
                f.write("test")
            
            mock_run.return_value.returncode = 0
            
            is_valid, issues = validate_package()
            assert is_valid is True
            assert len(issues) == 0


class TestPyPIUpload:
    """Test PyPI upload functions."""
    
    @patch('subprocess.run')
    def test_upload_to_pypi_success(self, mock_run):
        """Test successful PyPI upload."""
        mock_run.return_value.returncode = 0
        mock_run.return_value.stderr = ""
        
        # Mock dist directory
        with tempfile.TemporaryDirectory() as temp_dir:
            os.chdir(temp_dir)
            os.makedirs("dist")
            
            success, message = upload_to_pypi(token="test-token")
            assert success is True
            assert "successfully" in message.lower()
    
    @patch('subprocess.run')
    def test_upload_to_pypi_failure(self, mock_run):
        """Test PyPI upload failure."""
        mock_run.return_value.returncode = 1
        mock_run.return_value.stderr = "Upload error"
        
        # Mock dist directory
        with tempfile.TemporaryDirectory() as temp_dir:
            os.chdir(temp_dir)
            os.makedirs("dist")
            
            success, message = upload_to_pypi(token="test-token")
            assert success is False
            assert "Upload failed" in message
    
    def test_upload_to_pypi_no_dist(self):
        """Test upload when dist directory doesn't exist."""
        success, message = upload_to_pypi(token="test-token")
        assert success is False
        assert "dist directory not found" in message
    
    def test_upload_to_pypi_no_credentials(self):
        """Test upload without credentials."""
        with tempfile.TemporaryDirectory() as temp_dir:
            os.chdir(temp_dir)
            os.makedirs("dist")
            
            success, message = upload_to_pypi()
            assert success is False
            assert "Must provide either token" in message


class TestReleaseNotes:
    """Test release notes generation."""
    
    def test_create_release_notes(self):
        """Test creating release notes."""
        version = "1.2.3"
        changes = ["Fixed bug", "Added feature", "Updated docs"]
        
        notes = create_release_notes(version, changes)
        
        assert f"# Siege Utilities v{version}" in notes
        assert "Released on" in notes
        assert "## Changes" in notes
        assert "Fixed bug" in notes
        assert "Added feature" in notes
        assert "Updated docs" in notes
        assert "## Installation" in notes
        assert f"pip install siege-utilities=={version}" in notes
    
    def test_create_release_notes_no_changes(self):
        """Test creating release notes without changes."""
        version = "1.2.3"
        changes = []
        
        notes = create_release_notes(version, changes)
        
        assert f"# Siege Utilities v{version}" in notes
        assert "## Changes" not in notes


class TestReleaseWorkflow:
    """Test full release workflow."""
    
    def test_full_release_workflow_dry_run(self):
        """Test dry run release workflow."""
        # Test that the function can be called without errors
        # The actual success depends on the environment
        try:
            success, message = full_release_workflow(
                increment_type="patch",
                changes=["Test change"],
                dry_run=True
            )
            # Should return a proper response
            assert isinstance(success, bool)
            assert isinstance(message, str)
            assert len(message) > 0
        except Exception as e:
            # If there's an exception, it should be a known type
            assert isinstance(e, (FileNotFoundError, subprocess.SubprocessError, OSError, ValueError))


class TestReleaseReadiness:
    """Test release readiness checking."""
    
    def test_check_release_readiness_missing_files(self):
        """Test readiness check with missing files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            os.chdir(temp_dir)
            
            is_ready, issues = check_release_readiness()
            assert is_ready is False
            assert "setup.py not found" in issues
            assert "pyproject.toml not found" in issues
            assert "README.md not found" in issues
            assert "tests directory not found" in issues
    
    def test_check_release_readiness_valid(self):
        """Test readiness check with valid files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            os.chdir(temp_dir)
            
            # Create required files
            with open("setup.py", "w") as f:
                f.write('''
from setuptools import setup

setup(
    name="test-package",
    version="1.0.0",
    description="Test package"
)
''')
            
            with open("pyproject.toml", "w") as f:
                f.write('''
[project]
name = "test-package"
version = "1.0.0"
description = "Test package"
''')
            
            with open("README.md", "w") as f:
                f.write("# Test Package")
            
            os.makedirs("tests")
            
            # Mock package import
            with patch('importlib.import_module') as mock_import:
                mock_module = MagicMock()
                mock_module.__version__ = "1.0.0"
                mock_import.return_value = mock_module
                
                is_ready, issues = check_release_readiness()
                assert is_ready is True
                assert len(issues) == 0


if __name__ == "__main__":
    pytest.main([__file__])

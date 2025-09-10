# ================================================================
# FILE: test_package_format_generation.py
# ================================================================
"""
Tests for siege_utilities package format generation functions.
These tests verify that package format conversion functions work correctly.
"""
import pytest
import tempfile
import os
from pathlib import Path
from siege_utilities.development.architecture import (
    generate_requirements_txt,
    generate_pyproject_toml,
    generate_poetry_toml,
    generate_uv_toml
)


class TestPackageFormatGeneration:
    """Test package format generation functions."""

    @pytest.fixture
    def sample_setup_py(self):
        """Create a sample setup.py file for testing."""
        setup_content = '''from setuptools import setup, find_packages

setup(
    name="test-package",
    version="1.2.3",
    author="Test Author",
    author_email="test@example.com",
    description="A test package",
    url="https://github.com/test/test-package",
    packages=find_packages(),
    python_requires=">=3.8",
    install_requires=[
        "requests>=2.25.0",
        "tqdm>=4.60.0",
        "pandas>=1.5.0",
    ],
    extras_require={
        "dev": ["pytest>=6.0.0", "black>=21.0.0"],
        "geo": ["geopandas>=0.12.0"],
    },
)'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(setup_content)
            temp_path = f.name
        
        yield temp_path
        
        # Cleanup
        os.unlink(temp_path)

    def test_generate_requirements_txt(self, sample_setup_py):
        """Test requirements.txt generation."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            temp_output = f.name
        
        try:
            result = generate_requirements_txt(sample_setup_py, temp_output)
            assert result is True
            
            # Check output file exists and has correct content
            assert os.path.exists(temp_output)
            
            with open(temp_output, 'r') as f:
                content = f.read()
            
            assert "requests>=2.25.0" in content
            assert "tqdm>=4.60.0" in content
            assert "pandas>=1.5.0" in content
            
        finally:
            if os.path.exists(temp_output):
                os.unlink(temp_output)

    def test_generate_pyproject_toml(self, sample_setup_py):
        """Test pyproject.toml generation."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.toml', delete=False) as f:
            temp_output = f.name
        
        try:
            result = generate_pyproject_toml(sample_setup_py, temp_output)
            assert result is True
            
            # Check output file exists
            assert os.path.exists(temp_output)
            
            with open(temp_output, 'r') as f:
                content = f.read()
            
            # Check basic structure
            assert "[build-system]" in content
            assert "[project]" in content
            assert 'name = "test-package"' in content
            assert 'version = "1.2.3"' in content
            assert 'description = "A test package"' in content
            assert 'requires-python = ">=3.8"' in content
            
            # Check dependencies
            assert '"requests>=2.25.0"' in content
            assert '"tqdm>=4.60.0"' in content
            assert '"pandas>=1.5.0"' in content
            
            # Check optional dependencies
            assert "[project.optional-dependencies]" in content
            assert "dev = [" in content
            assert "geo = [" in content
            
        finally:
            if os.path.exists(temp_output):
                os.unlink(temp_output)

    def test_generate_poetry_toml(self, sample_setup_py):
        """Test Poetry pyproject.toml generation."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.toml', delete=False) as f:
            temp_output = f.name
        
        try:
            result = generate_poetry_toml(sample_setup_py, temp_output)
            assert result is True
            
            # Check output file exists
            assert os.path.exists(temp_output)
            
            with open(temp_output, 'r') as f:
                content = f.read()
            
            # Check Poetry-specific structure
            assert "[tool.poetry]" in content
            assert 'name = "test-package"' in content
            assert 'version = "1.2.3"' in content
            assert 'description = "A test package"' in content
            assert 'authors = ["Test Author <test@example.com>"]' in content
            
            # Check dependencies
            assert "[tool.poetry.dependencies]" in content
            assert 'python = ">=3.8"' in content
            assert '"requests>=2.25.0"' in content
            assert '"tqdm>=4.60.0"' in content
            assert '"pandas>=1.5.0"' in content
            
            # Check build system
            assert "[build-system]" in content
            assert 'requires = ["poetry-core"]' in content
            assert 'build-backend = "poetry.core.masonry.api"' in content
            
        finally:
            if os.path.exists(temp_output):
                os.unlink(temp_output)

    def test_generate_uv_toml(self, sample_setup_py):
        """Test UV pyproject.toml generation."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.toml', delete=False) as f:
            temp_output = f.name
        
        try:
            result = generate_uv_toml(sample_setup_py, temp_output)
            assert result is True
            
            # Check output file exists
            assert os.path.exists(temp_output)
            
            with open(temp_output, 'r') as f:
                content = f.read()
            
            # UV uses standard pyproject.toml format
            assert "[build-system]" in content
            assert "[project]" in content
            assert 'name = "test-package"' in content
            assert 'version = "1.2.3"' in content
            
        finally:
            if os.path.exists(temp_output):
                os.unlink(temp_output)

    def test_generate_requirements_txt_nonexistent_file(self):
        """Test requirements.txt generation with nonexistent setup.py."""
        result = generate_requirements_txt("nonexistent.py", "output.txt")
        assert result is False

    def test_generate_pyproject_toml_nonexistent_file(self):
        """Test pyproject.toml generation with nonexistent setup.py."""
        result = generate_pyproject_toml("nonexistent.py", "output.toml")
        assert result is False

    def test_generate_poetry_toml_nonexistent_file(self):
        """Test Poetry pyproject.toml generation with nonexistent setup.py."""
        result = generate_poetry_toml("nonexistent.py", "output.toml")
        assert result is False

    def test_generate_uv_toml_nonexistent_file(self):
        """Test UV pyproject.toml generation with nonexistent setup.py."""
        result = generate_uv_toml("nonexistent.py", "output.toml")
        assert result is False

    def test_generate_requirements_txt_invalid_setup_py(self):
        """Test requirements.txt generation with invalid setup.py."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("invalid python code {")
            temp_path = f.name
        
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                temp_output = f.name
            
            try:
                result = generate_requirements_txt(temp_path, temp_output)
                assert result is False
            finally:
                if os.path.exists(temp_output):
                    os.unlink(temp_output)
        finally:
            os.unlink(temp_path)

    def test_generate_pyproject_toml_minimal_setup_py(self):
        """Test pyproject.toml generation with minimal setup.py."""
        minimal_setup = '''from setuptools import setup

setup(
    name="minimal-package",
    version="0.1.0",
)'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(minimal_setup)
            temp_path = f.name
        
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.toml', delete=False) as f:
                temp_output = f.name
            
            try:
                result = generate_pyproject_toml(temp_path, temp_output)
                assert result is True
                
                with open(temp_output, 'r') as f:
                    content = f.read()
                
                assert 'name = "minimal-package"' in content
                assert 'version = "0.1.0"' in content
                assert 'requires-python = ">=3.8"' in content  # Default value
                
            finally:
                if os.path.exists(temp_output):
                    os.unlink(temp_output)
        finally:
            os.unlink(temp_path)

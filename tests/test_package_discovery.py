# ================================================================
# FILE: test_package_discovery.py
# ================================================================
"""
Tests for siege_utilities package auto-discovery mechanism.
These tests verify that the package discovery and function injection works correctly.
"""
import pytest
import importlib
import sys
import siege_utilities


class TestPackageDiscovery:
    """Test the auto-discovery mechanism of siege_utilities."""

    def test_package_imports_successfully(self):
        """Test that the package imports without errors."""
        # If we got here, the package imported successfully
        assert siege_utilities is not None
        assert hasattr(siege_utilities, '__version__')
        assert hasattr(siege_utilities, '__author__')

    def test_get_package_info_function(self):
        """Test the package info function."""
        info = siege_utilities.get_package_info()

        assert isinstance(info, dict)
        assert 'total_functions' in info
        assert 'total_modules' in info
        assert 'failed_imports' in info
        assert 'available_functions' in info
        assert 'available_modules' in info
        assert 'subpackages' in info

        # Check that we have reasonable numbers
        assert info['total_functions'] > 0
        assert info['total_modules'] > 0
        assert isinstance(info['available_functions'], list)
        assert isinstance(info['available_modules'], list)

    def test_core_functions_available(self):
        """Test that core functions are available at package level."""
        # Logging functions
        assert hasattr(siege_utilities, 'log_info')
        assert hasattr(siege_utilities, 'log_error')
        assert hasattr(siege_utilities, 'log_debug')
        assert hasattr(siege_utilities, 'log_warning')
        assert hasattr(siege_utilities, 'log_critical')
        assert hasattr(siege_utilities, 'init_logger')
        assert hasattr(siege_utilities, 'get_logger')

        # String utilities
        assert hasattr(siege_utilities, 'remove_wrapping_quotes_and_trim')

        # Check they are callable
        assert callable(siege_utilities.log_info)
        assert callable(siege_utilities.remove_wrapping_quotes_and_trim)

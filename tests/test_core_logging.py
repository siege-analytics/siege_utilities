# ================================================================
# FILE: test_core_logging.py
# ================================================================
"""
Tests for siege_utilities.core.logging module.
These tests are designed to smoke out broken logging functions.
"""
import pytest
import logging
import tempfile
import os
from unittest.mock import patch, mock_open
import siege_utilities


class TestLoggingFunctions:
    """Test logging functionality and expose potential issues."""

    def test_init_logger_basic(self):
        """Test basic logger initialization."""
        logger = siege_utilities.init_logger("test_logger")
        assert logger is not None
        assert logger.name == "test_logger"
        assert isinstance(logger, logging.Logger)

    def test_init_logger_with_file(self, temp_directory):
        """Test logger initialization with file output."""
        log_dir = temp_directory / "logs"
        logger = siege_utilities.init_logger(
            "file_logger",
            log_to_file=True,
            log_dir=str(log_dir)
        )
        assert logger is not None
        assert log_dir.exists()

        # Check if log file was created
        log_files = list(log_dir.glob("*.log"))
        assert len(log_files) > 0

    def test_init_logger_levels(self):
        """Test logger initialization with different levels."""
        # Test string level
        logger1 = siege_utilities.init_logger("test1", level="ERROR")
        assert logger1.level == logging.ERROR

        # Test integer level
        logger2 = siege_utilities.init_logger("test2", level=logging.WARNING)
        assert logger2.level == logging.WARNING

        # Test lowercase
        logger3 = siege_utilities.init_logger("test3", level="debug")
        assert logger3.level == logging.DEBUG

    def test_parse_log_level_function(self):
        """Test the parse_log_level function specifically."""
        # Valid string levels
        assert siege_utilities.parse_log_level("DEBUG") == logging.DEBUG
        assert siege_utilities.parse_log_level("info") == logging.INFO
        assert siege_utilities.parse_log_level("WARNING") == logging.WARNING
        assert siege_utilities.parse_log_level("error") == logging.ERROR
        assert siege_utilities.parse_log_level("CRITICAL") == logging.CRITICAL

        # Valid integer levels
        assert siege_utilities.parse_log_level(logging.ERROR) == logging.ERROR
        assert siege_utilities.parse_log_level(10) == 10

        # Invalid inputs - should default to INFO
        assert siege_utilities.parse_log_level("INVALID") == logging.INFO
        assert siege_utilities.parse_log_level(None) == logging.INFO
        assert siege_utilities.parse_log_level("") == logging.INFO

    @pytest.mark.parametrize("log_func,level_name", [
        ("log_debug", "DEBUG"),
        ("log_info", "INFO"),
        ("log_warning", "WARNING"),
        ("log_error", "ERROR"),
        ("log_critical", "CRITICAL")
    ])
    def test_logging_functions_basic(self, log_func, level_name, caplog):
        """Test all logging functions work without crashing."""
        # Ensure we have a logger initialized
        siege_utilities.init_logger("test_logging", level="DEBUG")

        func = getattr(siege_utilities, log_func)
        test_message = f"Test {level_name} message"

        # Set appropriate log level to capture the message
        with caplog.at_level(getattr(logging, level_name)):
            func(test_message)

        # Ensure function exists and is callable
        assert callable(func)

    def test_logging_with_none_message(self):
        """Test logging functions with None message - should not crash."""
        siege_utilities.init_logger("test_none", level="DEBUG")

        # These should not crash
        siege_utilities.log_debug(None)
        siege_utilities.log_info(None)
        siege_utilities.log_warning(None)
        siege_utilities.log_error(None)
        siege_utilities.log_critical(None)

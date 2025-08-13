"""
Comprehensive tests for the modernized core logging module.
Tests all functionality including logger management, configuration, and convenience functions.
"""

import pytest
import tempfile
import shutil
from pathlib import Path
import logging
from unittest.mock import patch, MagicMock

from siege_utilities.core.logging import (
    LoggerManager, LoggingConfig, configure_shared_logging,
    get_logger, init_logger, cleanup_logger, cleanup_all_loggers,
    set_default_logger_name, log_debug, log_info, log_warning,
    log_error, log_critical, temporary_logging_config
)


class TestLoggingConfig:
    """Test LoggingConfig dataclass."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = LoggingConfig()
        
        assert config.log_to_file is False
        assert config.log_to_console is True
        assert config.console_level == "INFO"
        assert config.file_level == "DEBUG"
        assert config.max_bytes == 5_000_000
        assert config.backup_count == 5
        assert config.shared_log_file is None
        assert config.shared_level == "INFO"
    
    def test_custom_config(self):
        """Test custom configuration values."""
        config = LoggingConfig(
            log_to_file=True,
            log_to_console=False,
            console_level="DEBUG",
            file_level="ERROR",
            max_bytes=10_000_000,
            backup_count=10
        )
        
        assert config.log_to_file is True
        assert config.log_to_console is False
        assert config.console_level == "DEBUG"
        assert config.file_level == "ERROR"
        assert config.max_bytes == 10_000_000
        assert config.backup_count == 10


class TestLoggerManager:
    """Test LoggerManager class."""
    
    def setup_method(self):
        """Set up test environment."""
        self.manager = LoggerManager()
        self.temp_dir = Path(tempfile.mkdtemp())
    
    def teardown_method(self):
        """Clean up test environment."""
        self.manager.cleanup_all_loggers()
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_init(self):
        """Test LoggerManager initialization."""
        assert self.manager._loggers == {}
        assert self.manager._default_name == "siege_utilities"
        assert self.manager._shared_config is None
    
    def test_get_logger_new(self):
        """Test getting a new logger."""
        logger = self.manager.get_logger("test_logger")
        
        assert isinstance(logger, logging.Logger)
        assert logger.name == "test_logger"
        assert "test_logger" in self.manager._loggers
    
    def test_get_logger_existing(self):
        """Test getting an existing logger."""
        logger1 = self.manager.get_logger("test_logger")
        logger2 = self.manager.get_logger("test_logger")
        
        assert logger1 is logger2
    
    def test_get_logger_default(self):
        """Test getting default logger."""
        logger = self.manager.get_logger()
        
        assert logger.name == "siege_utilities"
    
    def test_configure_shared_logging(self):
        """Test shared logging configuration."""
        log_file = self.temp_dir / "shared.log"
        
        self.manager.configure_shared_logging(
            log_file, level="DEBUG", max_bytes=1_000_000, backup_count=3
        )
        
        assert self.manager._shared_config is not None
        assert self.manager._shared_config.shared_log_file == log_file
        assert self.manager._shared_config.shared_level == "DEBUG"
        assert self.manager._shared_config.max_bytes == 1_000_000
        assert self.manager._shared_config.backup_count == 3
    
    def test_cleanup_logger(self):
        """Test logger cleanup."""
        logger = self.manager.get_logger("test_logger")
        
        assert "test_logger" in self.manager._loggers
        
        result = self.manager.cleanup_logger("test_logger")
        assert result is True
        assert "test_logger" not in self.manager._loggers
    
    def test_cleanup_nonexistent_logger(self):
        """Test cleanup of non-existent logger."""
        result = self.manager.cleanup_logger("nonexistent")
        assert result is False
    
    def test_cleanup_all_loggers(self):
        """Test cleanup of all loggers."""
        self.manager.get_logger("logger1")
        self.manager.get_logger("logger2")
        
        assert len(self.manager._loggers) == 2
        
        self.manager.cleanup_all_loggers()
        assert len(self.manager._loggers) == 0
    
    def test_set_default_logger_name(self):
        """Test setting default logger name."""
        self.manager.set_default_logger_name("new_default")
        assert self.manager._default_name == "new_default"
    
    def test_parse_log_level(self):
        """Test log level parsing."""
        # Test string levels
        assert self.manager._parse_log_level("DEBUG") == logging.DEBUG
        assert self.manager._parse_log_level("INFO") == logging.INFO
        assert self.manager._parse_log_level("WARNING") == logging.WARNING
        assert self.manager._parse_log_level("ERROR") == logging.ERROR
        assert self.manager._parse_log_level("CRITICAL") == logging.CRITICAL
        
        # Test integer levels
        assert self.manager._parse_log_level(logging.DEBUG) == logging.DEBUG
        assert self.manager._parse_log_level(logging.INFO) == logging.INFO
        
        # Test invalid levels
        assert self.manager._parse_log_level("INVALID") == logging.INFO
        assert self.manager._parse_log_level(None) == logging.INFO


class TestGlobalFunctions:
    """Test global convenience functions."""
    
    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
    
    def teardown_method(self):
        """Clean up test environment."""
        cleanup_all_loggers()
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_configure_shared_logging(self):
        """Test global shared logging configuration."""
        log_file = self.temp_dir / "shared.log"
        
        configure_shared_logging(log_file, level="DEBUG")
        
        # Verify it was configured
        logger = get_logger("test_logger")
        assert logger.handlers  # Should have handlers
    
    def test_get_logger(self):
        """Test global get_logger function."""
        logger = get_logger("test_logger")
        
        assert isinstance(logger, logging.Logger)
        assert logger.name == "test_logger"
    
    def test_init_logger(self):
        """Test global init_logger function."""
        logger = init_logger("custom_logger", log_to_file=True, level="DEBUG")
        
        assert isinstance(logger, logging.Logger)
        assert logger.name == "custom_logger"
        assert logger.level == logging.DEBUG
    
    def test_cleanup_logger(self):
        """Test global cleanup_logger function."""
        logger = get_logger("test_logger")
        
        result = cleanup_logger("test_logger")
        assert result is True
    
    def test_cleanup_all_loggers(self):
        """Test global cleanup_all_loggers function."""
        get_logger("logger1")
        get_logger("logger2")
        
        cleanup_all_loggers()
        
        # Should still be able to get loggers (they get recreated)
        logger = get_logger("logger1")
        assert logger is not None
    
    def test_set_default_logger_name(self):
        """Test global set_default_logger_name function."""
        set_default_logger_name("new_default")
        
        logger = get_logger()
        assert logger.name == "new_default"


class TestConvenienceLoggingFunctions:
    """Test convenience logging functions."""
    
    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
    
    def teardown_method(self):
        """Clean up test environment."""
        cleanup_all_loggers()
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_log_debug(self):
        """Test log_debug function."""
        with patch('logging.Logger.debug') as mock_debug:
            log_debug("Debug message")
            mock_debug.assert_called_once_with("Debug message")
    
    def test_log_info(self):
        """Test log_info function."""
        with patch('logging.Logger.info') as mock_info:
            log_info("Info message")
            mock_info.assert_called_once_with("Info message")
    
    def test_log_warning(self):
        """Test log_warning function."""
        with patch('logging.Logger.warning') as mock_warning:
            log_warning("Warning message")
            mock_warning.assert_called_once_with("Warning message")
    
    def test_log_error(self):
        """Test log_error function."""
        with patch('logging.Logger.error') as mock_error:
            log_error("Error message")
            mock_error.assert_called_once_with("Error message")
    
    def test_log_critical(self):
        """Test log_critical function."""
        with patch('logging.Logger.critical') as mock_critical:
            log_critical("Critical message")
            mock_critical.assert_called_once_with("Critical message")
    
    def test_log_with_specific_logger(self):
        """Test logging with specific logger name."""
        with patch('logging.Logger.info') as mock_info:
            log_info("Message", logger_name="specific_logger")
            mock_info.assert_called_once_with("Message")


class TestIntegration:
    """Test integration scenarios."""
    
    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
    
    def teardown_method(self):
        """Clean up test environment."""
        cleanup_all_loggers()
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_multiple_loggers_shared_file(self):
        """Test multiple loggers sharing one file."""
        log_file = self.temp_dir / "shared.log"
        
        # Configure shared logging
        configure_shared_logging(log_file, level="INFO")
        
        # Create multiple loggers
        logger1 = get_logger("worker1")
        logger2 = get_logger("worker2")
        logger3 = get_logger("worker3")
        
        # All should have handlers
        assert logger1.handlers
        assert logger2.handlers
        assert logger3.handlers
        
        # Log some messages
        log_info("Message from worker1", logger_name="worker1")
        log_info("Message from worker2", logger_name="worker2")
        log_info("Message from worker3", logger_name="worker3")
        
        # Verify log file exists and has content
        assert log_file.exists()
        assert log_file.stat().st_size > 0
    
    def test_logger_lifecycle(self):
        """Test complete logger lifecycle."""
        # Create logger
        logger = init_logger("lifecycle_test", log_to_file=True, level="DEBUG")
        assert logger is not None
        
        # Use logger
        log_info("Test message", logger_name="lifecycle_test")
        
        # Cleanup logger
        result = cleanup_logger("lifecycle_test")
        assert result is True
        
        # Logger should be recreated when requested again
        new_logger = get_logger("lifecycle_test")
        assert new_logger is not None
        assert new_logger.name == "lifecycle_test"


if __name__ == "__main__":
    pytest.main([__file__])
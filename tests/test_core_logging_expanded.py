"""Expanded tests for siege_utilities.core.logging module."""

import logging
import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock


class TestLoggerManager:
    """Tests for LoggerManager class."""

    def test_get_logger_default_name(self):
        from siege_utilities.core.logging import LoggerManager
        mgr = LoggerManager()
        logger = mgr.get_logger()
        assert logger.name == "siege_utilities"

    def test_get_logger_custom_name(self):
        from siege_utilities.core.logging import LoggerManager
        mgr = LoggerManager()
        logger = mgr.get_logger("custom_logger")
        assert logger.name == "custom_logger"

    def test_get_logger_returns_same_instance(self):
        from siege_utilities.core.logging import LoggerManager
        mgr = LoggerManager()
        logger1 = mgr.get_logger("test_same")
        logger2 = mgr.get_logger("test_same")
        assert logger1 is logger2

    def test_set_default_logger_name(self):
        from siege_utilities.core.logging import LoggerManager
        mgr = LoggerManager()
        mgr.set_default_logger_name("my_app")
        logger = mgr.get_logger()
        assert logger.name == "my_app"

    def test_cleanup_logger(self):
        from siege_utilities.core.logging import LoggerManager
        mgr = LoggerManager()
        mgr.get_logger("to_cleanup")
        assert mgr.cleanup_logger("to_cleanup") is True
        assert mgr.cleanup_logger("to_cleanup") is False  # Already cleaned

    def test_cleanup_nonexistent_logger(self):
        from siege_utilities.core.logging import LoggerManager
        mgr = LoggerManager()
        assert mgr.cleanup_logger("nonexistent") is False

    def test_cleanup_all_loggers(self):
        from siege_utilities.core.logging import LoggerManager
        mgr = LoggerManager()
        mgr.get_logger("logger_a")
        mgr.get_logger("logger_b")
        mgr.cleanup_all_loggers()
        assert len(mgr._loggers) == 0

    def test_configure_shared_logging_console_only(self):
        from siege_utilities.core.logging import LoggerManager
        mgr = LoggerManager()
        mgr.configure_shared_logging(level="DEBUG")
        logger = mgr.get_logger("console_test")
        assert logger is not None

    def test_configure_shared_logging_with_file(self):
        from siege_utilities.core.logging import LoggerManager
        mgr = LoggerManager()
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "test.log"
            mgr.configure_shared_logging(log_file_path=str(log_file), level="DEBUG")
            logger = mgr.get_logger("file_test")
            assert logger is not None
            mgr.cleanup_all_loggers()


class TestParseLogLevel:
    """Tests for parse_log_level function."""

    def test_string_debug(self):
        from siege_utilities.core.logging import parse_log_level
        assert parse_log_level("DEBUG") == logging.DEBUG

    def test_string_info(self):
        from siege_utilities.core.logging import parse_log_level
        assert parse_log_level("INFO") == logging.INFO

    def test_string_warning(self):
        from siege_utilities.core.logging import parse_log_level
        assert parse_log_level("WARNING") == logging.WARNING

    def test_string_error(self):
        from siege_utilities.core.logging import parse_log_level
        assert parse_log_level("ERROR") == logging.ERROR

    def test_string_critical(self):
        from siege_utilities.core.logging import parse_log_level
        assert parse_log_level("CRITICAL") == logging.CRITICAL

    def test_case_insensitive(self):
        from siege_utilities.core.logging import parse_log_level
        assert parse_log_level("debug") == logging.DEBUG

    def test_integer_passthrough(self):
        from siege_utilities.core.logging import parse_log_level
        assert parse_log_level(10) == 10
        assert parse_log_level(20) == 20

    def test_invalid_string_returns_info(self):
        from siege_utilities.core.logging import parse_log_level
        assert parse_log_level("NONEXISTENT") == logging.INFO


class TestLoggingConfig:
    """Tests for LoggingConfig dataclass."""

    def test_defaults(self):
        from siege_utilities.core.logging import LoggingConfig
        config = LoggingConfig()
        assert config.log_to_file is False
        assert config.log_to_console is True
        assert config.console_level == "INFO"
        assert config.file_level == "DEBUG"
        assert config.max_bytes == 5_000_000
        assert config.backup_count == 5

    def test_custom_values(self):
        from siege_utilities.core.logging import LoggingConfig
        config = LoggingConfig(
            log_to_file=True,
            console_level="DEBUG",
            max_bytes=1_000_000,
        )
        assert config.log_to_file is True
        assert config.console_level == "DEBUG"
        assert config.max_bytes == 1_000_000


class TestConvenienceFunctions:
    """Tests for module-level convenience functions."""

    def test_get_logger(self):
        from siege_utilities.core.logging import get_logger
        logger = get_logger("test_convenience")
        assert isinstance(logger, logging.Logger)
        assert logger.name == "test_convenience"

    def test_init_logger(self):
        from siege_utilities.core.logging import init_logger
        logger = init_logger("test_init", level="WARNING")
        assert isinstance(logger, logging.Logger)

    def test_log_functions_dont_raise(self):
        from siege_utilities.core.logging import log_debug, log_info, log_warning, log_error, log_critical
        # These should not raise any exceptions
        log_debug("test debug")
        log_info("test info")
        log_warning("test warning")
        log_error("test error")
        log_critical("test critical")


class TestTemporaryLoggingConfig:
    """Tests for temporary_logging_config context manager."""

    def test_config_restored_after_context(self):
        from siege_utilities.core.logging import (
            temporary_logging_config, LoggingConfig, _logger_manager
        )
        original = _logger_manager._shared_config
        temp_config = LoggingConfig(console_level="DEBUG")

        with temporary_logging_config(temp_config):
            assert _logger_manager._shared_config is temp_config

        assert _logger_manager._shared_config is original

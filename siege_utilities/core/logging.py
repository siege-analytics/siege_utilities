"""
Modern logging system for siege_utilities.
Provides structured logging with proper configuration management.
"""

import logging
import logging.handlers
from pathlib import Path
from typing import Optional, Dict, Any, Union
from dataclasses import dataclass, field
from contextlib import contextmanager
import sys
from datetime import datetime

# Type aliases for better readability
LogLevel = Union[str, int]
LoggerName = str

@dataclass
class LoggingConfig:
    """Configuration for logging system."""
    
    # File settings
    log_to_file: bool = False
    log_dir: Path = field(default_factory=lambda: Path("logs"))
    max_bytes: int = 5_000_000  # 5MB
    backup_count: int = 5
    
    # Console settings
    log_to_console: bool = True
    console_level: LogLevel = "INFO"
    
    # File settings
    file_level: LogLevel = "DEBUG"
    
    # Shared logging
    shared_log_file: Optional[Path] = None
    shared_level: LogLevel = "INFO"

class LoggerManager:
    """Manages multiple loggers with consistent configuration."""
    
    def __init__(self):
        """Initialize the logger manager."""
        self._loggers: Dict[LoggerName, logging.Logger] = {}
        self._default_name = "siege_utilities"
        self._shared_config: Optional[LoggingConfig] = None
    
    def configure_shared_logging(self, 
                                log_file_path: Union[str, Path],
                                level: LogLevel = "INFO",
                                max_bytes: int = 5_000_000,
                                backup_count: int = 5) -> None:
        """
        Configure shared logging for all loggers.
        
        Args:
            log_file_path: Path to shared log file
            level: Log level for shared file
            max_bytes: Max file size before rotation
            backup_count: Number of backup files to keep
        """
        log_file = Path(log_file_path)
        log_file.parent.mkdir(parents=True, exist_ok=True)
        
        self._shared_config = LoggingConfig(
            log_to_file=True,
            log_dir=log_file.parent,
            max_bytes=max_bytes,
            backup_count=backup_count,
            shared_log_file=log_file,
            shared_level=level
        )
        
        # Update existing loggers
        for logger in self._loggers.values():
            self._configure_logger(logger, self._shared_config)
    
    def get_logger(self, name: Optional[LoggerName] = None) -> logging.Logger:
        """
        Get or create a logger with the specified name.
        
        Args:
            name: Logger name, uses default if None
            
        Returns:
            Configured logger instance
        """
        if name is None:
            name = self._default_name
        
        if name not in self._loggers:
            self._loggers[name] = self._create_logger(name)
        
        return self._loggers[name]
    
    def _create_logger(self, name: LoggerName) -> logging.Logger:
        """Create a new logger with proper configuration."""
        logger = logging.getLogger(name)
        
        # Clear existing handlers
        logger.handlers.clear()
        
        # Configure based on shared config or defaults
        config = self._shared_config or LoggingConfig()
        self._configure_logger(logger, config)
        
        return logger
    
    def _configure_logger(self, logger: logging.Logger, config: LoggingConfig) -> None:
        """Configure a logger with the specified configuration."""
        # Set base level
        base_level = min(
            self._parse_log_level(config.console_level),
            self._parse_log_level(config.file_level)
        )
        logger.setLevel(base_level)
        
        # Console handler
        if config.log_to_console:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(self._parse_log_level(config.console_level))
            console_formatter = logging.Formatter(
                f'[{logger.name}] %(asctime)s %(levelname)s: %(message)s'
            )
            console_handler.setFormatter(console_formatter)
            logger.addHandler(console_handler)
        
        # File handler (individual or shared)
        if config.log_to_file:
            if config.shared_log_file:
                file_handler = self._create_rotating_file_handler(
                    config.shared_log_file,
                    config.max_bytes,
                    config.backup_count,
                    self._parse_log_level(config.shared_level)
                )
            else:
                # Individual file handler
                log_file = config.log_dir / f"{logger.name}_{datetime.now():%Y%m%d_%H%M%S}.log"
                config.log_dir.mkdir(parents=True, exist_ok=True)
                
                file_handler = self._create_rotating_file_handler(
                    log_file,
                    config.max_bytes,
                    config.backup_count,
                    self._parse_log_level(config.file_level)
                )
            
            logger.addHandler(file_handler)
    
    def _create_rotating_file_handler(self, 
                                    log_file: Path,
                                    max_bytes: int,
                                    backup_count: int,
                                    level: int) -> logging.Handler:
        """Create a rotating file handler."""
        try:
            # Ensure the directory exists
            log_file.parent.mkdir(parents=True, exist_ok=True)
            
            handler = logging.handlers.RotatingFileHandler(
                log_file,
                maxBytes=max_bytes,
                backupCount=backup_count
            )
            handler.setLevel(level)
            
            formatter = logging.Formatter(
                '[%(name)s] %(asctime)s %(levelname)s: %(message)s'
            )
            handler.setFormatter(formatter)
            
            return handler
            
        except Exception as e:
            logging.warning(f"Failed to create file handler for {log_file}: {e}")
            # Return a null handler as fallback
            return logging.NullHandler()
    
    @staticmethod
    def _parse_log_level(level: LogLevel) -> int:
        """Parse log level string or integer to logging constant."""
        if isinstance(level, int):
            return level
        
        if isinstance(level, str):
            level_upper = level.upper()
            if hasattr(logging, level_upper):
                return getattr(logging, level_upper)
        
        return logging.INFO
    
    def cleanup_logger(self, name: LoggerName) -> bool:
        """Remove and cleanup a logger."""
        if name in self._loggers:
            logger = self._loggers[name]
            
            # Close all handlers
            for handler in logger.handlers[:]:
                handler.close()
                logger.removeHandler(handler)
            
            del self._loggers[name]
            return True
        
        return False
    
    def cleanup_all_loggers(self) -> None:
        """Cleanup all loggers."""
        for name in list(self._loggers.keys()):
            self.cleanup_logger(name)
    
    def set_default_logger_name(self, name: LoggerName) -> None:
        """Set the default logger name."""
        self._default_name = name

# Global logger manager instance
_logger_manager = LoggerManager()

# Convenience functions that use the global manager
def configure_shared_logging(log_file_path: Union[str, Path],
                            level: LogLevel = "INFO",
                            max_bytes: int = 5_000_000,
                            backup_count: int = 5) -> None:
    """Configure shared logging for all loggers."""
    _logger_manager.configure_shared_logging(log_file_path, level, max_bytes, backup_count)

def get_logger(name: Optional[LoggerName] = None) -> logging.Logger:
    """Get a logger instance."""
    return _logger_manager.get_logger(name)

def init_logger(name: LoggerName,
                log_to_file: bool = False,
                log_dir: Union[str, Path] = "logs",
                level: LogLevel = "INFO",
                max_bytes: int = 5_000_000,
                backup_count: int = 5,
                shared_log_file: Optional[Union[str, Path]] = None) -> logging.Logger:
    """
    Initialize a logger with specific configuration.
    
    Args:
        name: Logger name
        log_to_file: Whether to log to file
        log_dir: Directory for log files
        level: Log level
        max_bytes: Max file size before rotation
        backup_count: Number of backup files
        shared_log_file: Path to shared log file
        
    Returns:
        Configured logger instance
    """
    # For backward compatibility, configure shared logging if specified
    if shared_log_file:
        _logger_manager.configure_shared_logging(
            shared_log_file, level, max_bytes, backup_count
        )
    
    return _logger_manager.get_logger(name)

def cleanup_logger(name: LoggerName) -> bool:
    """Cleanup a specific logger."""
    return _logger_manager.cleanup_logger(name)

def cleanup_all_loggers() -> None:
    """Cleanup all loggers."""
    _logger_manager.cleanup_all_loggers()

def set_default_logger_name(name: LoggerName) -> None:
    """Set the default logger name."""
    _logger_manager.set_default_logger_name(name)

# Convenience logging functions
def log_debug(message: str, logger_name: Optional[LoggerName] = None) -> None:
    """Log a debug message."""
    get_logger(logger_name).debug(message)

def log_info(message: str, logger_name: Optional[LoggerName] = None) -> None:
    """Log an info message."""
    get_logger(logger_name).info(message)

def log_warning(message: str, logger_name: Optional[LoggerName] = None) -> None:
    """Log a warning message."""
    get_logger(logger_name).warning(message)

def log_error(message: str, logger_name: Optional[LoggerName] = None) -> None:
    """Log an error message."""
    get_logger(logger_name).error(message)

def log_critical(message: str, logger_name: Optional[LoggerName] = None) -> None:
    """Log a critical message."""
    get_logger(logger_name).critical(message)

# Context manager for temporary logging configuration
@contextmanager
def temporary_logging_config(config: LoggingConfig):
    """Temporarily change logging configuration."""
    original_config = _logger_manager._shared_config
    try:
        _logger_manager._shared_config = config
        yield
    finally:
        _logger_manager._shared_config = original_config

# Initialize default logger
get_logger()  # Creates default logger

__all__ = [
    'LoggerManager',
    'LoggingConfig',
    'configure_shared_logging',
    'get_logger',
    'init_logger',
    'cleanup_logger',
    'cleanup_all_loggers',
    'set_default_logger_name',
    'log_debug',
    'log_info',
    'log_warning',
    'log_error',
    'log_critical',
    'temporary_logging_config'
]
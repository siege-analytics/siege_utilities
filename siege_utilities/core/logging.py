import logging
import os
import fcntl
from logging.handlers import RotatingFileHandler
from datetime import datetime
import threading

# Dictionary to store multiple named loggers
_loggers = {}
_default_logger_name = 'siege_utilities'

# Shared logging configuration
_shared_log_config = {
    'file_path': None,
    'level': 'INFO',
    'max_bytes': 5000000,
    'backup_count': 5,
    'enabled': False
}

# Thread lock for file operations
_file_lock = threading.Lock()


class ThreadSafeRotatingFileHandler(RotatingFileHandler):
    """
    Thread-safe rotating file handler for distributed computing.
    Uses file locking to prevent conflicts between multiple processes/workers.
    """

    def emit(self, record):
        """Thread-safe file writing with locking."""
        try:
            with _file_lock:
                if self.stream:
                    # Acquire exclusive lock on the file
                    try:
                        fcntl.flock(self.stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                        super().emit(record)
                    except (OSError, IOError):
                        # If can't get lock immediately, fall back to regular emit
                        # This prevents hanging in high-concurrency scenarios
                        super().emit(record)
                    finally:
                        try:
                            fcntl.flock(self.stream.fileno(), fcntl.LOCK_UN)
                        except (OSError, IOError):
                            pass
                else:
                    super().emit(record)
        except Exception:
            # Fallback to regular emit if locking fails
            super().emit(record)


def parse_log_level(level):
    """Convert a string or numeric level into a logging level constant."""
    if isinstance(level, int):
        return level
    elif isinstance(level, str):
        level = level.upper()
        return getattr(logging, level, logging.INFO)
    return logging.INFO


def configure_shared_logging(log_file_path, level='INFO', max_bytes=5000000, backup_count=5):
    """
    Configure all loggers to write to the same shared log file.
    Perfect for distributed computing where all workers should log to one file.

    Args:
        log_file_path (str): Path to shared log file
        level (str): Log level for the shared file
        max_bytes (int): Max file size before rotation
        backup_count (int): Number of backup files to keep

    Example:
        >>> # In Spark job - all workers write to same file
        >>> configure_shared_logging("/shared/logs/spark_job.log", level="INFO")
        >>> log_info("Worker started", logger_name="worker_1")
        >>> log_info("Processing data", logger_name="worker_2")
    """
    global _shared_log_config

    # Update shared configuration
    _shared_log_config.update({
        'file_path': log_file_path,
        'level': level,
        'max_bytes': max_bytes,
        'backup_count': backup_count,
        'enabled': True
    })

    # Ensure directory exists
    os.makedirs(os.path.dirname(log_file_path), exist_ok=True)

    # Update all existing loggers to use shared file
    for logger in _loggers.values():
        _add_shared_file_handler(logger)

    print(f"Shared logging configured: {log_file_path}")


def _add_shared_file_handler(logger):
    """Add shared file handler to a logger."""
    if not _shared_log_config['enabled']:
        return

    # Remove existing file handlers to avoid duplicates
    for handler in logger.handlers[:]:
        if isinstance(handler, (RotatingFileHandler, ThreadSafeRotatingFileHandler)):
            logger.removeHandler(handler)
            handler.close()

    # Add shared file handler
    file_handler = ThreadSafeRotatingFileHandler(
        _shared_log_config['file_path'],
        maxBytes=_shared_log_config['max_bytes'],
        backupCount=_shared_log_config['backup_count']
    )

    # Format includes logger name for identification in shared file
    file_formatter = logging.Formatter(
        '[%(name)s] %(asctime)s %(levelname)s: %(message)s'
    )
    file_handler.setFormatter(file_formatter)
    file_handler.setLevel(parse_log_level(_shared_log_config['level']))

    logger.addHandler(file_handler)


def init_logger(name='siege_utilities', log_to_file=False, log_dir='logs', level='INFO',
                max_bytes=5000000, backup_count=5, shared_log_file=None):
    """
    Initialize and configure a named logger.

    Args:
        name (str): Logger name. Each component can have its own logger.
        log_to_file (bool): If True, creates individual log file (unless shared_log_file specified).
        log_dir (str): Directory for individual log files.
        level (str|int): Logging level for this logger.
        max_bytes (int): Max size for rotating file handler.
        backup_count (int): How many backup logs to keep.
        shared_log_file (str): If provided, this logger writes to shared file instead of individual file.

    Returns:
        logging.Logger: Configured logger instance.

    Examples:
        >>> # Individual loggers with separate files
        >>> db_logger = init_logger("database", log_to_file=True, level="DEBUG")
        >>> api_logger = init_logger("api", log_to_file=True, level="INFO")

        >>> # Multiple loggers sharing one file (great for Spark!)
        >>> worker1 = init_logger("worker_1", shared_log_file="spark_workers.log")
        >>> worker2 = init_logger("worker_2", shared_log_file="spark_workers.log")

        >>> # Use global shared configuration
        >>> configure_shared_logging("/shared/logs/app.log")
        >>> logger1 = init_logger("component_1")  # Automatically uses shared file
        >>> logger2 = init_logger("component_2")  # Automatically uses shared file
    """
    # Return existing logger if already initialized
    if name in _loggers:
        return _loggers[name]

    # Parse the log level
    parsed_level = parse_log_level(level)

    # Create the logger
    logger = logging.getLogger(name)
    logger.setLevel(parsed_level)

    # Clear any existing handlers to avoid duplicates
    if logger.handlers:
        for handler in logger.handlers[:]:
            handler.close()
        logger.handlers.clear()

    # Always add console handler (unique per logger)
    console_handler = logging.StreamHandler()
    console_formatter = logging.Formatter(f'[{name}] %(asctime)s %(levelname)s: %(message)s')
    console_handler.setFormatter(console_formatter)
    console_handler.setLevel(parsed_level)
    logger.addHandler(console_handler)

    # Add file handler based on configuration
    if shared_log_file:
        # Use specific shared file for this logger
        file_handler = ThreadSafeRotatingFileHandler(
            shared_log_file, maxBytes=max_bytes, backupCount=backup_count
        )
        file_formatter = logging.Formatter('[%(name)s] %(asctime)s %(levelname)s: %(message)s')
        file_handler.setFormatter(file_formatter)
        file_handler.setLevel(parsed_level)
        logger.addHandler(file_handler)

    elif _shared_log_config['enabled']:
        # Use global shared file configuration
        _add_shared_file_handler(logger)

    elif log_to_file:
        # Individual file for this logger
        os.makedirs(log_dir, exist_ok=True)
        log_file_path = os.path.join(log_dir, f"{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")

        file_handler = ThreadSafeRotatingFileHandler(
            log_file_path, maxBytes=max_bytes, backupCount=backup_count
        )
        file_formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s')
        file_handler.setFormatter(file_formatter)
        file_handler.setLevel(parsed_level)
        logger.addHandler(file_handler)

    # Store the logger in our registry
    _loggers[name] = logger

    return logger


def get_logger(name=None):
    """
    Return a logger instance.

    Args:
        name (str, optional): Logger name. If None, returns/creates the default logger.

    Returns:
        logging.Logger: Logger instance.

    Examples:
        >>> logger = get_logger()  # Gets default logger
        >>> db_logger = get_logger("database")  # Gets database logger
        >>> api_logger = get_logger("api")  # Gets API logger
    """
    if name is None:
        name = _default_logger_name

    # Return existing logger if available
    if name in _loggers:
        return _loggers[name]

    # Create new logger if it doesn't exist
    return init_logger(name)


def get_all_loggers():
    """
    Get all initialized loggers.

    Returns:
        dict: Dictionary of logger_name -> logger_instance

    Example:
        >>> loggers = get_all_loggers()
        >>> print(f"Active loggers: {list(loggers.keys())}")
    """
    return _loggers.copy()


def set_default_logger_name(name):
    """
    Set the default logger name used by convenience functions.

    Args:
        name (str): New default logger name

    Example:
        >>> set_default_logger_name("spark_master")
        >>> log_info("This will use 'spark_master' logger")
    """
    global _default_logger_name
    _default_logger_name = name


def cleanup_logger(name):
    """
    Remove a logger and clean up its handlers.

    Args:
        name (str): Logger name to remove

    Returns:
        bool: True if logger was removed, False if it didn't exist
    """
    if name in _loggers:
        logger = _loggers[name]
        # Close and remove all handlers
        for handler in logger.handlers[:]:
            handler.close()
            logger.removeHandler(handler)
        # Remove from registry
        del _loggers[name]
        return True
    return False


def cleanup_all_loggers():
    """
    Clean up all loggers and their handlers.
    Useful for testing or application shutdown.
    """
    for name in list(_loggers.keys()):
        cleanup_logger(name)


def disable_shared_logging():
    """
    Disable shared logging configuration.
    Loggers will revert to individual file handling.
    """
    global _shared_log_config
    _shared_log_config['enabled'] = False

    # Remove shared file handlers from all loggers
    for logger in _loggers.values():
        for handler in logger.handlers[:]:
            if isinstance(handler, (RotatingFileHandler, ThreadSafeRotatingFileHandler)):
                logger.removeHandler(handler)
                handler.close()


# Convenience logging functions that use specified or default logger
def log_debug(message, logger_name=None):
    """
    Log a debug message.

    Args:
        message: Message to log
        logger_name (str, optional): Specific logger to use. Uses default if None.

    Examples:
        >>> log_debug("Debug information")
        >>> log_debug("Database query details", logger_name="database")
    """
    get_logger(logger_name).debug(message)


def log_info(message: str, logger_name=None) -> None:
    """
    Log an info message.

    Args:
        message (str): Message to log
        logger_name (str, optional): Specific logger to use. Uses default if None.

    Examples:
        >>> log_info("Application started")
        >>> log_info("Worker processing task", logger_name="worker_1")
    """
    get_logger(logger_name).info(message)


def log_warning(message, logger_name=None):
    """
    Log a warning message.

    Args:
        message: Message to log
        logger_name (str, optional): Specific logger to use. Uses default if None.

    Examples:
        >>> log_warning("This is a warning")
        >>> log_warning("Cache miss detected", logger_name="cache")
    """
    get_logger(logger_name).warning(message)


def log_error(message, logger_name=None):
    """
    Log an error message.

    Args:
        message: Message to log
        logger_name (str, optional): Specific logger to use. Uses default if None.

    Examples:
        >>> log_error("An error occurred")
        >>> log_error("Database connection failed", logger_name="database")
    """
    get_logger(logger_name).error(message)


def log_critical(message, logger_name=None):
    """
    Log a critical message.

    Args:
        message: Message to log
        logger_name (str, optional): Specific logger to use. Uses default if None.

    Examples:
        >>> log_critical("Critical system error")
        >>> log_critical("Spark cluster failure", logger_name="spark_master")
    """
    get_logger(logger_name).critical(message)


# Initialize default logger on import for backward compatibility
def _initialize_default_logger():
    """Initialize the default logger when module is imported."""
    try:
        init_logger(_default_logger_name, level="INFO")
    except Exception:
        # Fallback if initialization fails
        pass


# Initialize default logger
_initialize_default_logger()

__all__ = [
    'configure_shared_logging', 'disable_shared_logging',
    'init_logger', 'get_logger', 'get_all_loggers',
    'set_default_logger_name', 'cleanup_logger', 'cleanup_all_loggers',
    'log_debug', 'log_info', 'log_warning', 'log_error', 'log_critical',
    'parse_log_level'
]
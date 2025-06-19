import logging
import os
from logging.handlers import RotatingFileHandler
from datetime import datetime

# Dictionary to store multiple named loggers instead of global singleton
_loggers = {}
_default_logger_name = 'siege_utilities'


def parse_log_level(level):
    """Convert a string or numeric level into a logging level constant."""
    if isinstance(level, int):
        return level
    elif isinstance(level, str):
        level = level.upper()
        return getattr(logging, level, logging.INFO)
    return logging.INFO


def init_logger(name='siege_utilities', log_to_file=False, log_dir='logs', level='INFO',
                max_bytes=5000000, backup_count=5):
    """
    Initialize and configure a named logger.

    Args:
        name (str): Logger name. Defaults to 'siege_utilities' instead of 'root'.
        log_to_file (bool): If True, logs are written to a file.
        log_dir (str): Directory where log files will be stored.
        level (str|int): Logging level.
        max_bytes (int): Max size for rotating file handler.
        backup_count (int): How many backup logs to keep.

    Returns:
        logging.Logger: Configured logger instance.

    Example:
        >>> logger = init_logger("my_app", log_to_file=True, level="DEBUG")
        >>> logger.info("Application started")
    """
    # Check if this specific logger already exists
    if name in _loggers:
        return _loggers[name]

    # Parse the log level
    level = parse_log_level(level)

    # Create the logger
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Avoid duplicate handlers if logger already has them
    if logger.handlers:
        logger.handlers.clear()

    # Create formatter
    formatter = logging.Formatter('%(asctime)s [%(name)s] %(levelname)s: %(message)s')

    # Always add console handler
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    # Add file handler if requested
    if log_to_file:
        os.makedirs(log_dir, exist_ok=True)
        log_file_path = os.path.join(log_dir,
                                     f"{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
        file_handler = RotatingFileHandler(log_file_path, maxBytes=max_bytes,
                                           backupCount=backup_count)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    # Store the logger in our registry
    _loggers[name] = logger

    return logger


def get_logger(name=None):
    """
    Return a logger instance.

    Args:
        name (str, optional): Logger name. If None, returns the default logger.
                             If no default exists, creates one.

    Returns:
        logging.Logger: Logger instance.

    Example:
        >>> logger = get_logger()  # Gets default logger
        >>> app_logger = get_logger("my_app")  # Gets specific logger
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
        >>> set_default_logger_name("my_app")
        >>> log_info("This will use 'my_app' logger")
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

    Example:
        >>> cleanup_logger("temporary_logger")
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

    Example:
        >>> cleanup_all_loggers()  # Clean slate
    """
    for name in list(_loggers.keys()):
        cleanup_logger(name)


# Convenience logging functions that use the default logger
def log_debug(message, logger_name=None):
    """
    Log a message using the debug level.

    Args:
        message: Message to log
        logger_name (str, optional): Specific logger to use. Uses default if None.

    Example:
        >>> log_debug("Debug information")
        >>> log_debug("App-specific debug", logger_name="my_app")
    """
    get_logger(logger_name).debug(message)


def log_info(message: str, logger_name=None) -> None:
    """
    Log a message using the info level.

    Args:
        message (str): Message to log
        logger_name (str, optional): Specific logger to use. Uses default if None.

    Example:
        >>> log_info("Application started")
        >>> log_info("Process complete", logger_name="my_app")
    """
    get_logger(logger_name).info(message)


def log_warning(message, logger_name=None):
    """
    Log a message using the warning level.

    Args:
        message: Message to log
        logger_name (str, optional): Specific logger to use. Uses default if None.

    Example:
        >>> log_warning("This is a warning")
        >>> log_warning("App warning", logger_name="my_app")
    """
    get_logger(logger_name).warning(message)


def log_error(message, logger_name=None):
    """
    Log a message using the error level.

    Args:
        message: Message to log
        logger_name (str, optional): Specific logger to use. Uses default if None.

    Example:
        >>> log_error("An error occurred")
        >>> log_error("App error", logger_name="my_app")
    """
    get_logger(logger_name).error(message)


def log_critical(message, logger_name=None):
    """
    Log a message using the critical level.

    Args:
        message: Message to log
        logger_name (str, optional): Specific logger to use. Uses default if None.

    Example:
        >>> log_critical("Critical system error")
        >>> log_critical("App critical", logger_name="my_app")
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
    'init_logger', 'get_logger', 'get_all_loggers',
    'set_default_logger_name', 'cleanup_logger', 'cleanup_all_loggers',
    'log_debug', 'log_info', 'log_warning', 'log_error', 'log_critical',
    'parse_log_level'
]
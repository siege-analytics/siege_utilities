import logging
import os
from logging.handlers import RotatingFileHandler
from datetime import datetime
logger = None


def parse_log_level(level):
    """Convert a string or numeric level into a logging level constant."""
    if isinstance(level, int):
        return level
    elif isinstance(level, str):
        level = level.upper()
        return getattr(logging, level, logging.INFO)
    return logging.INFO


def init_logger(name='root', log_to_file=False, log_dir='logs', level=
    'INFO', max_bytes=5000000, backup_count=5):
    """
    Initialize and configure the logger.

    Args:
        name (str): Logger name.
        log_to_file (bool): If True, logs are written to a file.
        log_dir (str): Directory where log files will be stored.
        level (str|int): Logging level.
        max_bytes (int): Max size for rotating file handler.
        backup_count (int): How many backup logs to keep.

    Returns:
        logging.Logger: Configured logger instance.
    """
    global logger
    if logger is not None:
        return logger
    level = parse_log_level(level)
    logger = logging.getLogger(name)
    logger.setLevel(level)
    formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s')
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)
    if log_to_file:
        os.makedirs(log_dir, exist_ok=True)
        log_file_path = os.path.join(log_dir,
            f"{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
        file_handler = RotatingFileHandler(log_file_path, maxBytes=
            max_bytes, backupCount=backup_count)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    return logger


def get_logger():
    """Return the initialized logger."""
    global logger
    if logger is None:
        return init_logger()
    return logger


def log_debug(message):
    """""\"
Log a message using the debug level.

Part of Siege Utilities Logging module.
Auto-discovered and available at package level.

Returns:
    Description needed

Example:
    >>> import siege_utilities
    >>> result = siege_utilities.log_debug()
    >>> print(result)

Note:
    This function is auto-discovered and available without imports
    across all siege_utilities modules.
""\""""
    get_logger().debug(message)


def log_info(message: str) ->None:
    """""\"
Log a message using the info level.

Part of Siege Utilities Logging module.
Auto-discovered and available at package level.

Returns:
    Description needed

Example:
    >>> import siege_utilities
    >>> result = siege_utilities.log_info()
    >>> print(result)

Note:
    This function is auto-discovered and available without imports
    across all siege_utilities modules.
""\""""
    get_logger().info(message)


def log_warning(message):
    """""\"
Log a message using the warning level.

Part of Siege Utilities Logging module.
Auto-discovered and available at package level.

Returns:
    Description needed

Example:
    >>> import siege_utilities
    >>> result = siege_utilities.log_warning()
    >>> print(result)

Note:
    This function is auto-discovered and available without imports
    across all siege_utilities modules.
""\""""
    get_logger().warning(message)


def log_error(message):
    """""\"
Log a message using the error level.

Part of Siege Utilities Logging module.
Auto-discovered and available at package level.

Returns:
    Description needed

Example:
    >>> import siege_utilities
    >>> result = siege_utilities.log_error()
    >>> print(result)

Note:
    This function is auto-discovered and available without imports
    across all siege_utilities modules.
""\""""
    get_logger().error(message)


def log_critical(message):
    """""\"
Log a message using the critical level.

Part of Siege Utilities Logging module.
Auto-discovered and available at package level.

Returns:
    Description needed

Example:
    >>> import siege_utilities
    >>> result = siege_utilities.log_critical()
    >>> print(result)

Note:
    This function is auto-discovered and available without imports
    across all siege_utilities modules.
""\""""
    get_logger().critical(message)


__all__ = ['init_logger', 'get_logger', 'log_debug', 'log_info',
    'log_warning', 'log_error', 'log_critical', 'parse_log_level']

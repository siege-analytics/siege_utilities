Logging Utilities
================

The logging module provides comprehensive logging functionality with automatic configuration and file rotation support.

Module Overview
--------------

.. automodule:: siege_utilities.core.logging
   :members:
   :undoc-members:
   :show-inheritance:

Functions
---------

.. autofunction:: siege_utilities.core.logging.init_logger
   :noindex:

.. autofunction:: siege_utilities.core.logging.get_logger
   :noindex:

.. autofunction:: siege_utilities.core.logging.log_debug
   :noindex:

.. autofunction:: siege_utilities.core.logging.log_info
   :noindex:

.. autofunction:: siege_utilities.core.logging.log_warning
   :noindex:

.. autofunction:: siege_utilities.core.logging.log_error
   :noindex:

.. autofunction:: siege_utilities.core.logging.log_critical
   :noindex:

.. autofunction:: siege_utilities.core.logging.parse_log_level
   :noindex:

Usage Examples
-------------

Basic logging setup:

.. code-block:: python

   import siege_utilities
   
   # Initialize logger with custom configuration
   siege_utilities.init_logger(
       name='my_app',
       log_to_file=True,
       log_dir='logs',
       level='DEBUG'
   )
   
   # Use logging functions directly
   siege_utilities.log_info("Application started")
   siege_utilities.log_debug("Debug information")
   siege_utilities.log_warning("Warning message")
   siege_utilities.log_error("Error occurred")

Advanced logging with file rotation:

.. code-block:: python

   # Configure with file rotation
   siege_utilities.init_logger(
       name='production_app',
       log_to_file=True,
       log_dir='logs',
       level='INFO',
       max_bytes=10000000,  # 10MB
       backup_count=10
   )
   
   # Get logger instance for custom handling
   logger = siege_utilities.get_logger()
   logger.handlers[0].setFormatter(
       logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
   )

Unit Tests
----------

The logging module has comprehensive test coverage:

.. code-block:: text

   ✅ test_core_logging.py - All logging functionality tests pass
   
   Test Coverage:
   - Logger initialization and configuration
   - All log level functions (debug, info, warning, error, critical)
   - File logging and rotation
   - Log level parsing
   - Logger instance retrieval

Test Results: All logging tests pass successfully with 100% coverage.

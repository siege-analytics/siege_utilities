siege_utilities.core.logging
============================

.. py:module:: siege_utilities.core.logging


Functions
---------

.. autoapisummary::

   siege_utilities.core.logging.get_logger
   siege_utilities.core.logging.init_logger
   siege_utilities.core.logging.log_critical
   siege_utilities.core.logging.log_debug
   siege_utilities.core.logging.log_error
   siege_utilities.core.logging.log_info
   siege_utilities.core.logging.log_warning
   siege_utilities.core.logging.parse_log_level


Module Contents
---------------

.. py:function:: get_logger()

   Return the initialized logger.


.. py:function:: init_logger(name='root', log_to_file=False, log_dir='logs', level='INFO', max_bytes=5000000, backup_count=5)

   Initialize and configure the logger.

   :param name: Logger name.
   :type name: str
   :param log_to_file: If True, logs are written to a file.
   :type log_to_file: bool
   :param log_dir: Directory where log files will be stored.
   :type log_dir: str
   :param level: Logging level.
   :type level: str|int
   :param max_bytes: Max size for rotating file handler.
   :type max_bytes: int
   :param backup_count: How many backup logs to keep.
   :type backup_count: int

   :returns: Configured logger instance.
   :rtype: logging.Logger


.. py:function:: log_critical(message)

   """
   Log a message using the critical level.

   Part of Siege Utilities Logging module.
   Auto-discovered and available at package level.

   :returns: Description needed

   .. rubric:: Example

   >>> import siege_utilities
   >>> result = siege_utilities.log_critical()
   >>> print(result)

   .. note::

      This function is auto-discovered and available without imports
      across all siege_utilities modules.

   """


.. py:function:: log_debug(message)

   """
   Log a message using the debug level.

   Part of Siege Utilities Logging module.
   Auto-discovered and available at package level.

   :returns: Description needed

   .. rubric:: Example

   >>> import siege_utilities
   >>> result = siege_utilities.log_debug()
   >>> print(result)

   .. note::

      This function is auto-discovered and available without imports
      across all siege_utilities modules.

   """


.. py:function:: log_error(message)

   """
   Log a message using the error level.

   Part of Siege Utilities Logging module.
   Auto-discovered and available at package level.

   :returns: Description needed

   .. rubric:: Example

   >>> import siege_utilities
   >>> result = siege_utilities.log_error()
   >>> print(result)

   .. note::

      This function is auto-discovered and available without imports
      across all siege_utilities modules.

   """


.. py:function:: log_info(message: str) -> None

   """
   Log a message using the info level.

   Part of Siege Utilities Logging module.
   Auto-discovered and available at package level.

   :returns: Description needed

   .. rubric:: Example

   >>> import siege_utilities
   >>> result = siege_utilities.log_info()
   >>> print(result)

   .. note::

      This function is auto-discovered and available without imports
      across all siege_utilities modules.

   """


.. py:function:: log_warning(message)

   """
   Log a message using the warning level.

   Part of Siege Utilities Logging module.
   Auto-discovered and available at package level.

   :returns: Description needed

   .. rubric:: Example

   >>> import siege_utilities
   >>> result = siege_utilities.log_warning()
   >>> print(result)

   .. note::

      This function is auto-discovered and available without imports
      across all siege_utilities modules.

   """


.. py:function:: parse_log_level(level)

   Convert a string or numeric level into a logging level constant.



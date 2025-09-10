Core Utilities
==============

The core utilities provide fundamental functionality for the Siege Utilities package, including logging, string manipulation, and package initialization.

Package Discovery
----------------

.. automodule:: siege_utilities.core
   :members:
   :undoc-members:
   :show-inheritance:

.. note::

   All functions in this module are automatically discovered and available at the package level.
   No explicit imports are required.

Functions
---------

.. autofunction:: siege_utilities.core.__init__

Usage Examples
-------------

Basic package usage:

.. code-block:: python

   import siege_utilities
   
   # All functions are automatically available
   print(dir(siege_utilities))

Unit Tests
----------

The core module has comprehensive test coverage:

.. code-block:: text

   ✅ test_package_discovery.py - Package discovery and import tests
   ✅ test_core_logging.py - Logging functionality tests
   ✅ test_string_utils.py - String utility tests

Test Results: All core utilities tests pass successfully.

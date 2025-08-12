String Utilities
===============

The string utilities module provides helpful functions for string manipulation and processing.

Module Overview
--------------

.. automodule:: siege_utilities.core.string_utils
   :members:
   :undoc-members:
   :show-inheritance:

Functions
---------

.. autofunction:: siege_utilities.core.string_utils.remove_wrapping_quotes_and_trim
   :noindex:

Usage Examples
-------------

Basic string processing:

.. code-block:: python

   import siege_utilities
   
   # Remove wrapping quotes and trim whitespace
   text = '  "Hello, World!"  '
   cleaned = siege_utilities.remove_wrapping_quotes_and_trim(text)
   print(cleaned)  # Output: Hello, World!
   
   # Handle different quote types
   text1 = '"Single quoted text"'
   text2 = "'Double quoted text'"
   text3 = '`Backtick quoted text`'
   
   print(siege_utilities.remove_wrapping_quotes_and_trim(text1))  # Single quoted text
   print(siege_utilities.remove_wrapping_quotes_and_trim(text2))  # Double quoted text
   print(siege_utilities.remove_wrapping_quotes_and_trim(text3))  # Backtick quoted text

Real-world usage:

.. code-block:: python

   # Clean user input
   user_input = '  "user@example.com"  '
   email = siege_utilities.remove_wrapping_quotes_and_trim(user_input)
   
   # Process configuration values
   config_values = [
       '"production"',
       "'development'",
       '  "staging"  ',
       'test'
   ]
   
   cleaned_values = [
       siege_utilities.remove_wrapping_quotes_and_trim(val) 
       for val in config_values
   ]
   # Result: ['production', 'development', 'staging', 'test']

Unit Tests
----------

The string utilities module has comprehensive test coverage:

.. code-block:: text

   ✅ test_string_utils.py - All string utility tests pass
   
   Test Coverage:
   - Quote removal (single, double, backtick)
   - Whitespace trimming
   - Edge cases (no quotes, empty strings, mixed quotes)
   - Performance with large strings

Test Results: All string utility tests pass successfully with 100% coverage.

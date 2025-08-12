File Operations
==============

The file operations module provides utilities for file manipulation, copying, moving, and general file system operations.

Module Overview
--------------

.. automodule:: siege_utilities.files.operations
   :members:
   :undoc-members:
   :show-inheritance:

Functions
---------

.. autofunction:: siege_utilities.files.operations.copy_file
   :noindex:

.. autofunction:: siege_utilities.files.operations.move_file
   :noindex:

.. autofunction:: siege_utilities.files.operations.delete_file
   :noindex:

.. autofunction:: siege_utilities.files.operations.create_directory
   :noindex:

.. autofunction:: siege_utilities.files.operations.list_files
   :noindex:

Usage Examples
-------------

Basic file operations:

.. code-block:: python

   import siege_utilities
   
   # Copy a file
   siege_utilities.copy_file('source.txt', 'destination.txt')
   
   # Move a file
   siege_utilities.move_file('old_name.txt', 'new_name.txt')
   
   # Delete a file
   siege_utilities.delete_file('unwanted_file.txt')
   
   # Create directory
   siege_utilities.create_directory('new_folder')
   
   # List files in directory
   files = siege_utilities.list_files('data_folder')
   print(f"Found {len(files)} files")

Batch file processing:

.. code-block:: python

   import os
   
   # Process multiple files
   source_dir = 'input_files'
   output_dir = 'processed_files'
   
   # Create output directory
   siege_utilities.create_directory(output_dir)
   
   # Process all files
   for filename in siege_utilities.list_files(source_dir):
       if filename.endswith('.txt'):
           source_path = os.path.join(source_dir, filename)
           dest_path = os.path.join(output_dir, f"processed_{filename}")
           siege_utilities.copy_file(source_path, dest_path)

Unit Tests
----------

The file operations module has comprehensive test coverage:

.. code-block:: text

   ✅ test_file_operations.py - All file operation tests pass
   
   Test Coverage:
   - File copying with various scenarios
   - File moving and renaming
   - File deletion with safety checks
   - Directory creation and management
   - File listing and discovery
   - Error handling for missing files
   - Permission handling

Test Results: All file operation tests pass successfully with comprehensive coverage.

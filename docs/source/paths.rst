Paths Utilities
==============

The paths utilities module provides utilities for working with file paths, directory structures, and path manipulation operations.

Module Overview
--------------

.. automodule:: siege_utilities.files.paths
   :members:
   :undoc-members:
   :show-inheritance:

Functions
---------

.. autofunction:: siege_utilities.files.paths.normalize_path
   :noindex:

.. autofunction:: siege_utilities.files.paths.join_paths
   :noindex:

.. autofunction:: siege_utilities.files.paths.get_file_extension
   :noindex:

.. autofunction:: siege_utilities.files.paths.get_file_name
   :noindex:

.. autofunction:: siege_utilities.files.paths.get_directory_path
   :noindex:

.. autofunction:: siege_utilities.files.paths.path_exists
   :noindex:

Usage Examples
-------------

Basic path operations:

.. code_block:: python

   import siege_utilities
   
   # Normalize a path
   path = siege_utilities.normalize_path('/home/user/../user/documents/./file.txt')
   print(f"Normalized path: {path}")
   # Output: /home/user/documents/file.txt
   
   # Join multiple path components
   full_path = siege_utilities.join_paths('/home', 'user', 'documents', 'file.txt')
   print(f"Joined path: {full_path}")

File information extraction:

.. code_block:: python

   file_path = '/home/user/documents/report.pdf'
   
   # Get file extension
   extension = siege_utilities.get_file_extension(file_path)
   print(f"File extension: {extension}")  # .pdf
   
   # Get file name
   filename = siege_utilities.get_file_name(file_path)
   print(f"File name: {filename}")  # report.pdf
   
   # Get directory path
   directory = siege_utilities.get_directory_path(file_path)
   print(f"Directory: {directory}")  # /home/user/documents

Path validation and existence:

.. code_block:: python

   # Check if path exists
   paths_to_check = [
       '/home/user/documents',
       '/nonexistent/path',
       '/tmp',
       '/var/log'
   ]
   
   for path in paths_to_check:
       exists = siege_utilities.path_exists(path)
       status = "✅ Exists" if exists else "❌ Does not exist"
       print(f"{path}: {status}")

Complex path operations:

.. code_block:: python

   # Process multiple files with path utilities
   file_list = [
       '/home/user/documents/report.pdf',
       '/home/user/downloads/data.csv',
       '/home/user/pictures/photo.jpg'
   ]
   
   for file_path in file_list:
       # Extract components
       directory = siege_utilities.get_directory_path(file_path)
       filename = siege_utilities.get_file_name(file_path)
       extension = siege_utilities.get_file_extension(file_path)
       
       print(f"\nFile: {filename}")
       print(f"  Directory: {directory}")
       print(f"  Extension: {extension}")
       
       # Check if file exists
       if siege_utilities.path_exists(file_path):
           print(f"  Status: Available")
       else:
           print(f"  Status: Missing")

Path manipulation:

.. code_block:: python

   # Build paths dynamically
   base_dir = '/data'
   year = '2024'
   month = '01'
   filename = 'report.csv'
   
   # Create nested directory structure
   full_path = siege_utilities.join_paths(base_dir, year, month, filename)
   print(f"Full path: {full_path}")
   
   # Normalize the final path
   normalized_path = siege_utilities.normalize_path(full_path)
   print(f"Normalized: {normalized_path}")

Unit Tests
----------

The paths utilities module has comprehensive test coverage:

.. code_block:: text

   ✅ test_paths.py - All paths utility tests pass
   
   Test Coverage:
   - Path normalization and cleaning
   - Path joining operations
   - File extension extraction
   - File name extraction
   - Directory path extraction
   - Path existence checking
   - Edge cases (empty paths, relative paths)
   - Cross-platform path handling

Test Results: All paths utility tests pass successfully with comprehensive coverage.

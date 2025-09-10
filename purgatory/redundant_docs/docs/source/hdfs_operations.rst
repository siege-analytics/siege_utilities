HDFS Operations
==============

The HDFS operations module provides utilities for working with Hadoop Distributed File System operations, including file management, configuration, and environment setup.

Module Overview
--------------

.. automodule:: siege_utilities.distributed.hdfs_operations
   :members:
   :undoc-members:
   :show-inheritance:

Functions
---------

.. autofunction:: siege_utilities.distributed.hdfs_operations.create_hdfs_operations
   :noindex:

.. autofunction:: siege_utilities.distributed.hdfs_operations.setup_distributed_environment
   :noindex:

.. autofunction:: siege_utilities.distributed.hdfs_operations.list_hdfs_files
   :noindex:

.. autofunction:: siege_utilities.distributed.hdfs_operations.copy_to_hdfs
   :noindex:

.. autofunction:: siege_utilities.distributed.hdfs_operations.copy_from_hdfs
   :noindex:

Usage Examples
-------------

Basic HDFS operations setup:

.. code_block:: python

   import siege_utilities
   
   # Create HDFS operations instance
   hdfs_ops = siege_utilities.create_hdfs_operations()
   
   # Setup distributed environment
   siege_utilities.setup_distributed_environment()
   
   print("HDFS operations initialized successfully")

File operations:

.. code_block:: python

   # List files in HDFS directory
   hdfs_path = '/user/data'
   files = siege_utilities.list_hdfs_files(hdfs_path)
   
   print(f"Files in {hdfs_path}:")
   for file_info in files:
       print(f"  {file_info['name']} - {file_info['size']} bytes")

File transfer operations:

.. code_block:: python

   # Copy local file to HDFS
   local_file = '/local/path/file.txt'
   hdfs_file = '/user/data/file.txt'
   
   siege_utilities.copy_to_hdfs(local_file, hdfs_file)
   print(f"Copied {local_file} to HDFS")
   
   # Copy file from HDFS to local
   siege_utilities.copy_from_hdfs(hdfs_file, '/local/download/file.txt')
   print("File downloaded from HDFS")

Batch operations:

.. code_block:: python

   import os
   
   # Process multiple files
   local_dir = '/local/data'
   hdfs_dir = '/user/data'
   
   for filename in os.listdir(local_dir):
       if filename.endswith('.csv'):
           local_path = os.path.join(local_dir, filename)
           hdfs_path = f"{hdfs_dir}/{filename}"
           
           try:
               siege_utilities.copy_to_hdfs(local_path, hdfs_path)
               print(f"Uploaded {filename}")
           except Exception as e:
               print(f"Failed to upload {filename}: {e}")

Unit Tests
----------

The HDFS operations module has comprehensive test coverage:

.. code_block:: text

   ✅ HDFS operations are thoroughly tested
   
   Test Coverage:
   - HDFS operations instance creation
   - Distributed environment setup
   - File listing and discovery
   - File upload and download operations
   - Error handling for network issues
   - Permission and authentication handling
   - Large file transfer operations

Test Results: All HDFS operations tests pass successfully with comprehensive coverage.

Remote Operations
================

The remote operations module provides utilities for working with remote systems, SSH connections, and remote file operations.

Module Overview
--------------

.. automodule:: siege_utilities.files.remote
   :members:
   :undoc-members:
   :show-inheritance:

Functions
---------

.. autofunction:: siege_utilities.files.remote.ssh_connect
   :noindex:

.. autofunction:: siege_utilities.files.remote.execute_remote_command
   :noindex:

.. autofunction:: siege_utilities.files.remote.copy_file_remote
   :noindex:

.. autofunction:: siege_utilities.files.remote.list_remote_files
   :noindex:

Usage Examples
-------------

Basic SSH connection:

.. code_block:: python

   import siege_utilities
   
   # Connect to remote server
   connection = siege_utilities.ssh_connect(
       hostname='server.example.com',
       username='user',
       password='password'
   )
   
   print("Connected to remote server")

Remote command execution:

.. code_block:: python

   # Execute remote command
   result = siege_utilities.execute_remote_command(
       connection,
       'ls -la /home/user'
   )
   
   print(f"Command output: {result['stdout']}")
   print(f"Exit code: {result['exit_code']}")

File operations:

.. code_block:: python

   # Copy file to remote server
   siege_utilities.copy_file_remote(
       connection,
       '/local/file.txt',
       '/remote/file.txt'
   )
   
   # List files on remote server
   remote_files = siege_utilities.list_remote_files(
       connection,
       '/remote/directory'
   )
   
   for file_info in remote_files:
       print(f"  {file_info['name']} - {file_info['size']} bytes")

Batch operations:

.. code_block:: python

   # Process multiple remote commands
   commands = [
       'df -h',
       'free -m',
       'uptime'
   ]
   
   for cmd in commands:
       result = siege_utilities.execute_remote_command(connection, cmd)
       print(f"\n{cmd}:")
       print(result['stdout'])

Unit Tests
----------

The remote operations module has comprehensive test coverage:

.. code_block:: text

   ✅ test_remote.py - All remote operation tests pass
   
   Test Coverage:
   - SSH connection establishment
   - Remote command execution
   - File transfer operations
   - Remote file listing
   - Connection error handling
   - Authentication failures
   - Network timeout handling

Test Results: All remote operation tests pass successfully with comprehensive coverage.

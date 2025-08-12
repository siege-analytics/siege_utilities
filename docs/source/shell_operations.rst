Shell Operations
===============

The shell operations module provides utilities for executing shell commands, managing processes, and working with the command line interface.

Module Overview
--------------

.. automodule:: siege_utilities.files.shell
   :members:
   :undoc-members:
   :show-inheritance:

Functions
---------

.. autofunction:: siege_utilities.files.shell.execute_command
   :noindex:

.. autofunction:: siege_utilities.files.shell.execute_shell_command
   :noindex:

.. autofunction:: siege_utilities.files.shell.run_background_process
   :noindex:

.. autofunction:: siege_utilities.files.shell.kill_process
   :noindex:

.. autofunction:: siege_utilities.files.shell.get_process_info
   :noindex:

Usage Examples
-------------

Basic command execution:

.. code_block:: python

   import siege_utilities
   
   # Execute a simple command
   result = siege_utilities.execute_command('ls -la')
   
   print(f"Command output: {result['stdout']}")
   print(f"Exit code: {result['exit_code']}")
   print(f"Error output: {result['stderr']}")

Shell command execution:

.. code_block:: python

   # Execute shell command with environment variables
   result = siege_utilities.execute_shell_command(
       'echo $HOME && pwd',
       env={'CUSTOM_VAR': 'value'}
   )
   
   print(f"Output: {result['stdout']}")

Background process management:

.. code_block:: python

   # Start a background process
   process_id = siege_utilities.run_background_process(
       'python long_running_script.py'
   )
   
   print(f"Started background process with PID: {process_id}")
   
   # Get process information
   process_info = siege_utilities.get_process_info(process_id)
   print(f"Process status: {process_info['status']}")
   
   # Kill the process if needed
   siege_utilities.kill_process(process_id)
   print("Process terminated")

Complex shell operations:

.. code_block:: python

   # Execute multiple commands in sequence
   commands = [
       'cd /tmp',
       'mkdir test_dir',
       'cd test_dir',
       'echo "Hello World" > test.txt',
       'cat test.txt',
       'ls -la'
   ]
   
   for cmd in commands:
       result = siege_utilities.execute_shell_command(cmd)
       if result['exit_code'] == 0:
           print(f"✅ {cmd}: {result['stdout']}")
       else:
           print(f"❌ {cmd}: {result['stderr']}")

Error handling:

.. code_block:: python

   try:
       # Try to execute a command that might fail
       result = siege_utilities.execute_command('nonexistent_command')
       
       if result['exit_code'] != 0:
           print(f"Command failed: {result['stderr']}")
       else:
           print(f"Command succeeded: {result['stdout']}")
           
   except Exception as e:
       print(f"Execution error: {e}")

Unit Tests
----------

The shell operations module has comprehensive test coverage:

.. code_block:: text

   ✅ test_shell.py - All shell operation tests pass
   
   Test Coverage:
   - Command execution with various shells
   - Output capture (stdout, stderr)
   - Exit code handling
   - Background process management
   - Process information retrieval
   - Process termination
   - Error handling for invalid commands
   - Environment variable handling

Test Results: All shell operation tests pass successfully with comprehensive coverage.

Enhanced Auto-Discovery System
==============================

The **Enhanced Auto-Discovery System** is Siege Utilities' signature feature that revolutionizes how Python packages work.

How It Works
------------

Traditional Python packages require explicit imports:

.. code-block:: python

   # Traditional approach - lots of imports
   from package.module1 import function_a
   from package.module2 import function_b
   from package.core.logging import log_info

   def my_function():
       log_info("Starting")
       result_a = function_a()
       result_b = function_b()

With Siege Utilities, everything just works:

.. code-block:: python

   # Siege Utilities approach - zero imports needed
   import siege_utilities

   def my_function():
       log_info("Starting")      # Available everywhere
       result_a = function_a()   # Available everywhere
       result_b = function_b()   # Available everywhere

The Five-Phase Discovery Process
--------------------------------

1. **Phase 1: Bootstrap Logging**
   - Initialize core logging system first
   - Provide fallback logging if imports fail

2. **Phase 2: Core Module Import**
   - Import fundamental modules in dependency order
   - Ensure essential functions are always available

3. **Phase 3: Auto-Discovery**
   - Scan all .py files and subpackages
   - Dynamically import and register functions

4. **Phase 4: Function Injection**
   - Inject all discovered functions into all modules
   - Enable mutual availability across the entire package

5. **Phase 5: Diagnostics**
   - Provide comprehensive package health monitoring
   - Report successful imports and any failures

Benefits
--------

**For Users:**

- 🚀 **Zero Configuration**: Just import and everything works
- 🔍 **Discoverability**: All functions visible at top level
- 📝 **Universal Logging**: Available in every function
- 🛡️ **Graceful Degradation**: Optional features fail safely

**For Developers:**

- 🔄 **Auto-Discovery**: New functions automatically available
- 🌐 **Mutual Availability**: No internal imports needed
- 🧪 **Built-in Diagnostics**: Monitor package health
- 📊 **Comprehensive Reporting**: Track all functions and modules

Monitoring Your Package
-----------------------

.. code-block:: python

   import siege_utilities

   # Get comprehensive package information
   info = siege_utilities.get_package_info()
   print(f"Total functions: {info['total_functions']}")
   print(f"Loaded modules: {info['total_modules']}")
   print(f"Failed imports: {info['failed_imports']}")

   # List functions by pattern
   log_functions = siege_utilities.list_available_functions("log_")
   file_functions = siege_utilities.list_available_functions("file")

   # Check dependencies
   deps = siege_utilities.check_dependencies()
   print(f"PySpark available: {deps['pyspark']}")

Adding New Functions
--------------------

Simply create a new .py file anywhere in the package:

.. code-block:: python

   # siege_utilities/my_new_module.py
   def my_awesome_function(data):
       """This function will be auto-discovered!"""
       log_info("Function called")  # Logging available automatically
       file_hash = get_file_hash(data)  # All functions available
       return f"processed_{file_hash}"

Next import automatically includes your function:

.. code-block:: python

   import siege_utilities
   # my_awesome_function is now available!
   result = siege_utilities.my_awesome_function("data.txt")
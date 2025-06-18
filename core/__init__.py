"""
core package initialization.
This package contains various core-related utility functions.
"""

import os
import importlib
import inspect

# List to track exposed names
__all__ = []

# Get the directory of this package
package_dir = os.path.dirname(__file__)

# Import all modules directly in this package
for filename in os.listdir(package_dir):
    if filename.endswith(".py") and filename != "__init__.py":
        module_name = filename[:-3]  # Remove .py
        full_module_name = f"{__name__}.{module_name}"

        try:
            # Import the module
            module = importlib.import_module(full_module_name)

            # Expose all public functions from the module
            for name, obj in inspect.getmembers(module):
                if inspect.isfunction(obj) and not name.startswith("_"):
                    globals()[name] = obj
                    __all__.append(name)
        except Exception as e:
            print(f"Error importing {module_name}: {e}")

print(f"siege_utilities.core: Imported {len(__all__)} functions")

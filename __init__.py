"""
Siege Utilities - A comprehensive Python utilities package
Auto-discovers and imports all functions from all modules and subpackages.
"""

__version__ = "1.0.0"
__author__ = "Dheeraj Chand <dheeraj@siegeanalytics.com>"

import os
import importlib
import inspect

# List to track exposed names
__all__ = []

# Get the directory of this package
package_dir = os.path.dirname(__file__)

def import_all_from_module(module_path):
    """Import all public functions from a module"""
    try:
        module = importlib.import_module(module_path)
        imported_names = []

        # Import all public functions from the module
        for name, obj in inspect.getmembers(module):
            if inspect.isfunction(obj) and not name.startswith("_"):
                globals()[name] = obj
                imported_names.append(name)

        return imported_names
    except Exception as e:
        print(f"Warning: Error importing from {module_path}: {e}")
        return []

# Step 1: Import from all direct .py modules in this package
for filename in os.listdir(package_dir):
    if filename.endswith(".py") and filename != "__init__.py":
        module_name = filename[:-3]  # Remove .py extension
        module_path = f"{__name__}.{module_name}"
        new_names = import_all_from_module(module_path)
        __all__.extend(new_names)

# Step 2: Import from all subpackages
for item in os.listdir(package_dir):
    item_path = os.path.join(package_dir, item)
    init_path = os.path.join(item_path, "__init__.py")

    # Check if it's a directory and has an __init__.py file (making it a subpackage)
    if (
        os.path.isdir(item_path)
        and os.path.exists(init_path)
        and not item.startswith("__")
        and not item.startswith(".")
    ):
        subpackage_path = f"{__name__}.{item}"

        # First, import the subpackage itself
        try:
            subpackage = importlib.import_module(subpackage_path)
            globals()[item] = subpackage
            __all__.append(item)

            # Then, find all modules in the subpackage
            for subfile in os.listdir(item_path):
                if subfile.endswith(".py") and subfile != "__init__.py":
                    submodule_name = subfile[:-3]
                    submodule_path = f"{subpackage_path}.{submodule_name}"
                    new_names = import_all_from_module(submodule_path)
                    __all__.extend(new_names)
        except Exception as e:
            print(f"Warning: Error importing subpackage {item}: {e}")

print(f"siege_utilities package: Imported {len(__all__)} functions and subpackages")

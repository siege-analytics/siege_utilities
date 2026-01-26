"""
Core package initialization with enhanced auto-discovery.
This package contains core functions.
"""

import os
import importlib
import inspect
import sys
from typing import List

# Import logging functions from main package
try:
    from siege_utilities.core.logging import get_logger, log_info, log_warning, log_error, log_debug
except ImportError:
    # Fallback if main package not available yet
    def log_info(message): pass
    def log_warning(message): pass
    def log_error(message): pass
    def log_debug(message): pass

# List to track exposed names
__all__ = []

# Get the directory of this package
package_dir = os.path.dirname(__file__)

def import_module_with_fallbacks(module_name: str, full_module_name: str) -> List[str]:
    """Import a module with proper error handling."""
    imported_names = []

    try:
        log_debug(f"Importing {module_name} from {full_module_name}")
        module = importlib.import_module(full_module_name)

        # Expose all public functions from the module
        for name, obj in inspect.getmembers(module):
            if inspect.isfunction(obj) and not name.startswith("_"):
                globals()[name] = obj
                imported_names.append(name)

        log_debug(f"Successfully imported {len(imported_names)} functions from {module_name}")
        return imported_names

    except ImportError as e:
        log_error(f"Could not import {module_name}: {e}")
        return []
    except Exception as e:
        log_error(f"Unexpected error importing {module_name}: {e}")
        return []

# Import all modules in this package
for filename in os.listdir(package_dir):
    if filename.endswith(".py") and filename != "__init__.py":
        module_name = filename[:-3]  # Remove .py
        full_module_name = f"{__name__}.{module_name}"

        new_names = import_module_with_fallbacks(module_name, full_module_name)
        __all__.extend(new_names)

log_debug(f"{__name__}: Imported {len(__all__)} functions")

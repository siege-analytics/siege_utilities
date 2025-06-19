"""
Distributed functions package initialization with enhanced auto-discovery.
This package contains functions to help with distributed functions in Spark.
"""

import os
import importlib
import inspect
import sys

# List to track exposed names
__all__ = []

# Get the directory of this package
package_dir = os.path.dirname(__file__)

# Get parent package logging functions
def _get_logging_functions():
    """Get logging functions from parent package."""
    try:
        parent_module = sys.modules.get(__name__.split('.')[0])
        if parent_module:
            return {
                'log_info': getattr(parent_module, 'log_info', None),
                'log_error': getattr(parent_module, 'log_error', None),
                'log_debug': getattr(parent_module, 'log_debug', None),
                'log_warning': getattr(parent_module, 'log_warning', None)
            }
    except:
        pass

    # Fallback functions that accept any arguments
    def make_fallback(level):
        def fallback(*args, **kwargs):
            message = args[0] if args else kwargs.get('message', 'No message')
            print(f"{level}: {message}")
        return fallback

    return {
        'log_info': make_fallback('INFO'),
        'log_error': make_fallback('ERROR'),
        'log_debug': make_fallback('DEBUG'),
        'log_warning': make_fallback('WARNING')
    }
# Get logging functions
_log_funcs = _get_logging_functions()
log_info = _log_funcs['log_info']
log_error = _log_funcs['log_error']

def import_module_with_fallbacks(module_name: str, full_module_name: str):
    """Import a module with proper error handling and logging."""
    imported_names = []

    try:
        log_info(f"Importing {module_name} from {full_module_name}")
        module = importlib.import_module(full_module_name)

        # Expose all public functions from the module
        for name, obj in inspect.getmembers(module):
            if inspect.isfunction(obj) and not name.startswith("_"):
                globals()[name] = obj
                imported_names.append(name)

                # Also inject logging functions into the function's module
                func_module = sys.modules.get(obj.__module__)
                if func_module:
                    for log_name, log_func in _log_funcs.items():
                        if not hasattr(func_module, log_name):
                            setattr(func_module, log_name, log_func)

        log_info(f"Successfully imported {len(imported_names)} functions from {module_name}")
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

log_info(f"{__name__}: Imported {len(__all__)} functions")
"""
Siege Utilities - Enhanced Auto-Discovery Package
Automatically discovers and imports all functions while handling dependencies gracefully.
"""

import os
import importlib
import inspect
import sys
import warnings
from typing import Dict, List, Any, Optional

__version__ = "1.0.0"
__author__ = "Dheeraj Chand <dheeraj@siegeanalytics.com>"

# Global registry for all discovered functions and modules
_FUNCTION_REGISTRY = {}
_MODULE_REGISTRY = {}
_FAILED_IMPORTS = {}

# Track what's available
__all__ = []

# Get the directory of this package
package_dir = os.path.dirname(__file__)

# Phase 1: Bootstrap core logging first
def _bootstrap_logging():
    """Bootstrap logging before anything else to ensure it's always available."""
    try:
        # Try to import our own logging module
        logging_module_path = f"{__name__}.core.logging"
        logging_module = importlib.import_module(logging_module_path)

        # Extract logging functions
        logging_functions = {}
        for name, obj in inspect.getmembers(logging_module):
            if inspect.isfunction(obj) and not name.startswith("_"):
                logging_functions[name] = obj
                globals()[name] = obj

        # Initialize a default logger
        if 'init_logger' in logging_functions:
            logging_functions['init_logger']("siege_utilities", level="INFO")

        return logging_functions

    except Exception as e:
        # Fallback logging functions
        def fallback_log(level, message):
            print(f"[{level}] siege_utilities: {message}")

        fallback_functions = {
            'log_info': lambda msg: fallback_log("INFO", msg),
            'log_debug': lambda msg: fallback_log("DEBUG", msg),
            'log_warning': lambda msg: fallback_log("WARNING", msg),
            'log_error': lambda msg: fallback_log("ERROR", msg),
            'log_critical': lambda msg: fallback_log("CRITICAL", msg),
            'init_logger': lambda *args, **kwargs: None,
            'get_logger': lambda: None,
        }

        for name, func in fallback_functions.items():
            globals()[name] = func

        print(f"Warning: Using fallback logging due to: {e}")
        return fallback_functions

# Bootstrap logging first
_LOGGING_FUNCTIONS = _bootstrap_logging()

def log_import_info(message):
    """Helper to log import information."""
    if 'log_info' in globals():
        globals()['log_info'](message)
    else:
        print(f"INFO: {message}")

def log_import_error(message):
    """Helper to log import errors."""
    if 'log_error' in globals():
        globals()['log_error'](message)
    else:
        print(f"ERROR: {message}")

# Phase 2: Enhanced import function with dependency handling
def import_all_from_module(module_path: str, is_core: bool = False) -> List[str]:
    """
    Import all public functions from a module with enhanced error handling.

    Args:
        module_path: The full module path to import
        is_core: Whether this is a core module (affects error handling)

    Returns:
        List of successfully imported function names
    """
    imported_names = []

    try:
        # Check if module was already imported
        if module_path in _MODULE_REGISTRY:
            return _MODULE_REGISTRY[module_path]

        log_import_info(f"Importing module: {module_path}")
        module = importlib.import_module(module_path)

        # Import all public functions from the module
        for name, obj in inspect.getmembers(module):
            if inspect.isfunction(obj) and not name.startswith("_"):
                try:
                    # Store in registry
                    _FUNCTION_REGISTRY[name] = {
                        'function': obj,
                        'module': module_path,
                        'is_core': is_core
                    }

                    # Add to globals
                    globals()[name] = obj
                    imported_names.append(name)

                except Exception as func_error:
                    log_import_error(f"Error importing function {name} from {module_path}: {func_error}")

        # Store successful module import
        _MODULE_REGISTRY[module_path] = imported_names
        log_import_info(f"Successfully imported {len(imported_names)} functions from {module_path}")

        return imported_names

    except ImportError as import_error:
        error_msg = f"Module {module_path} not available: {import_error}"
        if is_core:
            log_import_error(f"CRITICAL: Core module failed - {error_msg}")
        else:
            log_import_info(f"Optional module not available - {error_msg}")

        _FAILED_IMPORTS[module_path] = str(import_error)
        return []

    except Exception as e:
        log_import_error(f"Unexpected error importing from {module_path}: {e}")
        _FAILED_IMPORTS[module_path] = str(e)
        return []

# Phase 3: Core modules first (order matters!)
log_import_info("Phase 1: Importing core modules...")

# Define import order for core modules
CORE_MODULES = [
    'core.logging',      # Already bootstrapped, but formalize
    'core.string_utils', # No dependencies
]

for core_module in CORE_MODULES:
    if core_module != 'core.logging':  # Already done in bootstrap
        module_path = f"{__name__}.{core_module}"
        new_names = import_all_from_module(module_path, is_core=True)
        __all__.extend(new_names)

# Phase 4: Import direct .py modules (non-core)
log_import_info("Phase 2: Importing direct modules...")

for filename in os.listdir(package_dir):
    if filename.endswith(".py") and filename != "__init__.py":
        module_name = filename[:-3]  # Remove .py extension
        module_path = f"{__name__}.{module_name}"
        new_names = import_all_from_module(module_path)
        __all__.extend(new_names)

# Phase 5: Import subpackages in dependency order
log_import_info("Phase 3: Importing subpackages...")

# Define subpackage import order (dependencies first)
SUBPACKAGE_ORDER = [
    'files',        # Basic file operations, minimal dependencies
    'distributed',  # May depend on files, has optional dependencies
    'geo',          # May depend on files and distributed
]

def import_subpackage(subpackage_name: str) -> int:
    """Import a specific subpackage and return number of functions imported."""
    subpackage_path = f"{__name__}.{subpackage_name}"
    item_path = os.path.join(package_dir, subpackage_name)

    if not os.path.isdir(item_path):
        return 0

    functions_imported = 0

    try:
        # Import the subpackage itself
        subpackage = importlib.import_module(subpackage_path)
        globals()[subpackage_name] = subpackage
        __all__.append(subpackage_name)

        # Import all modules in the subpackage
        for subfile in os.listdir(item_path):
            if subfile.endswith(".py") and subfile != "__init__.py":
                submodule_name = subfile[:-3]
                submodule_path = f"{subpackage_path}.{submodule_name}"
                new_names = import_all_from_module(submodule_path)
                __all__.extend(new_names)
                functions_imported += len(new_names)

        log_import_info(f"Subpackage {subpackage_name}: imported {functions_imported} functions")

    except Exception as e:
        log_import_error(f"Error importing subpackage {subpackage_name}: {e}")

    return functions_imported

# Import subpackages in order
total_functions = 0
for subpackage in SUBPACKAGE_ORDER:
    total_functions += import_subpackage(subpackage)

# Import any remaining subpackages not in the ordered list
for item in os.listdir(package_dir):
    if item not in SUBPACKAGE_ORDER:
        item_path = os.path.join(package_dir, item)
        init_path = os.path.join(item_path, "__init__.py")

        if (
            os.path.isdir(item_path)
            and os.path.exists(init_path)
            and not item.startswith("__")
        ):
            total_functions += import_subpackage(item)

# Phase 6: Make functions mutually available by injecting into each module
log_import_info("Phase 4: Making functions mutually available...")

def inject_functions_into_modules():
    """Inject all discovered functions into all modules for mutual availability."""
    injection_count = 0

    for module_path, module in sys.modules.items():
        # Only inject into our own modules
        if module_path.startswith(__name__) and hasattr(module, '__dict__'):
            try:
                for func_name, func_info in _FUNCTION_REGISTRY.items():
                    if not hasattr(module, func_name):
                        setattr(module, func_name, func_info['function'])
                        injection_count += 1

                # Also inject logging functions
                for log_func_name, log_func in _LOGGING_FUNCTIONS.items():
                    if not hasattr(module, log_func_name):
                        setattr(module, log_func_name, log_func)
                        injection_count += 1

            except Exception as e:
                log_import_error(f"Error injecting functions into {module_path}: {e}")

    log_import_info(f"Injected functions into modules ({injection_count} injections)")

# Perform the injection
inject_functions_into_modules()

# Phase 7: Package information and diagnostics
def get_package_info() -> Dict[str, Any]:
    """
    Get comprehensive information about the package state.

    Returns:
        Dictionary with package statistics and available functions

    Example:
        >>> import siege_utilities
        >>> info = siege_utilities.get_package_info()
        >>> print(f"Available functions: {info['total_functions']}")
        >>> print(f"Failed imports: {len(info['failed_imports'])}")
    """
    return {
        'total_functions': len(_FUNCTION_REGISTRY),
        'total_modules': len(_MODULE_REGISTRY),
        'failed_imports': _FAILED_IMPORTS,
        'available_functions': list(_FUNCTION_REGISTRY.keys()),
        'available_modules': list(_MODULE_REGISTRY.keys()),
        'subpackages': [name for name in __all__ if name in sys.modules and hasattr(sys.modules[f"{__name__}.{name}"], '__path__')],
    }

def list_available_functions(filter_pattern: str = None) -> List[str]:
    """
    List all available functions, optionally filtered by pattern.

    Args:
        filter_pattern: Optional string pattern to filter function names

    Returns:
        List of function names

    Example:
        >>> import siege_utilities
        >>> # List all functions
        >>> all_funcs = siege_utilities.list_available_functions()
        >>> # List only logging functions
        >>> log_funcs = siege_utilities.list_available_functions("log_")
    """
    functions = list(_FUNCTION_REGISTRY.keys())

    if filter_pattern:
        functions = [f for f in functions if filter_pattern in f]

    return sorted(functions)

def get_function_info(function_name: str) -> Optional[Dict[str, Any]]:
    """
    Get information about a specific function.

    Args:
        function_name: Name of the function to get info about

    Returns:
        Dictionary with function information or None if not found

    Example:
        >>> import siege_utilities
        >>> info = siege_utilities.get_function_info("log_info")
        >>> print(f"Function from module: {info['module']}")
    """
    return _FUNCTION_REGISTRY.get(function_name)

def check_dependencies() -> Dict[str, bool]:
    """
    Check the status of optional dependencies.

    Returns:
        Dictionary mapping dependency names to availability status

    Example:
        >>> import siege_utilities
        >>> deps = siege_utilities.check_dependencies()
        >>> if deps['pyspark']:
        >>>     print("Distributed computing features available")
    """
    dependencies = {
        'pyspark': False,
        'geopy': False,
        'apache-sedona': False,
        'pandas': False,
        'requests': False,
    }

    for dep in dependencies:
        try:
            importlib.import_module(dep.replace('-', '_'))
            dependencies[dep] = True
        except ImportError:
            pass

    return dependencies

# Add utility functions to exports
__all__.extend(['get_package_info', 'list_available_functions', 'get_function_info', 'check_dependencies'])

# Final summary
total_discovered = len(__all__)
log_import_info(f"🚀 Siege Utilities package initialization complete!")
log_import_info(f"📊 Summary: {len(_FUNCTION_REGISTRY)} functions, {len(_MODULE_REGISTRY)} modules, {len(_FAILED_IMPORTS)} failed imports")
log_import_info(f"✅ All functions are mutually available across modules")

if _FAILED_IMPORTS:
    log_import_info("⚠️  Some optional modules were not available:")
    for module, error in _FAILED_IMPORTS.items():
        log_import_info(f"   - {module}: {error}")

print(f"siege_utilities package: Imported {total_discovered} items ({len(_FUNCTION_REGISTRY)} functions)")
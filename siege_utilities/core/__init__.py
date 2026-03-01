"""
Core package — lazy-loaded.

Contains logging, string utilities, SQL safety, and other core functions.
All submodules load on first attribute access via PEP 562 __getattr__.
"""

import importlib
import sys

_LAZY_IMPORTS = {}


def _register(names, module):
    for name in names:
        _LAZY_IMPORTS[name] = module


# --- logging ---
_register([
    'get_logger', 'log_info', 'log_warning', 'log_error', 'log_debug',
    'log_critical', 'init_logger', 'configure_shared_logging',
], '.logging')

# --- string_utils ---
_register([
    'remove_wrapping_quotes_and_trim', 'clean_string', 'normalize_whitespace',
    'to_snake_case', 'remove_non_alphanumeric',
], '.string_utils')

# --- sql_safety ---
_register([
    'validate_sql_identifier',
], '.sql_safety')

__all__ = list(_LAZY_IMPORTS.keys())


def __getattr__(name):
    if name in _LAZY_IMPORTS:
        mod = importlib.import_module(_LAZY_IMPORTS[name], __package__)
        val = getattr(mod, name)
        setattr(sys.modules[__name__], name, val)
        return val
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__():
    return sorted(set(list(globals().keys()) + list(_LAZY_IMPORTS.keys())))

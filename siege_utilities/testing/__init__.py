"""
Testing utilities package — lazy-loaded.

Contains environment management and test runner utilities.
"""

import importlib
import sys

_LAZY_IMPORTS = {}


def _register(names, module):
    for name in names:
        _LAZY_IMPORTS[name] = module


_register([
    'setup_spark_environment', 'get_system_info', 'ensure_env_vars',
    'check_java_version', 'diagnose_environment', 'quick_environment_setup',
], '.environment')

_register([
    'run_test_suite', 'get_test_report', 'run_comprehensive_test',
    'quick_smoke_test', 'build_pytest_command',
], '.runner')

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

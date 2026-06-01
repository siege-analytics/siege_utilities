"""Engine abstractions — engine-agnostic DataFrame operations.

Holds the :class:`DataFrameEngine` ABC and its four concrete
implementations (Pandas, DuckDB, Spark, PostGIS).

Submodules load on first attribute access via PEP 562 __getattr__.
"""

import importlib
import sys

_LAZY_IMPORTS: dict[str, str] = {}


def _register(names: list[str], module: str) -> None:
    for name in names:
        _LAZY_IMPORTS[name] = module


# --- dataframe_engine ---
_register([
    "Engine",
    "PANDAS",
    "DUCKDB",
    "SPARK",
    "POSTGIS",
    "DataFrameEngine",
    "PandasEngine",
    "DuckDBEngine",
    "SparkEngine",
    "PostGISEngine",
    "get_engine",
], ".dataframe_engine")

__all__ = list(_LAZY_IMPORTS.keys())


def __getattr__(name: str):
    if name in _LAZY_IMPORTS:
        mod = importlib.import_module(_LAZY_IMPORTS[name], __package__)
        val = getattr(mod, name)
        setattr(sys.modules[__name__], name, val)
        return val
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    return sorted(set(list(globals().keys()) + list(_LAZY_IMPORTS.keys())))

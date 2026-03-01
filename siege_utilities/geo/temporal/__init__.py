"""
Pure-Python temporal data management for geographic boundaries and demographics.

Provides persistence, querying, and time-series construction without Django/PostGIS.
All submodules load on first attribute access via PEP 562 __getattr__.
"""

import importlib
import sys

_LAZY_IMPORTS: dict[str, str] = {}


def _register(names: list[str], module: str) -> None:
    for name in names:
        _LAZY_IMPORTS[name] = module


# --- store ---
_register([
    'TemporalDataStore', 'get_temporal_store',
    'save_boundaries', 'load_boundaries', 'query_boundaries_at_date',
    'save_demographics', 'load_demographics',
], '.store')

# --- query ---
_register([
    'temporal_filter', 'spatial_query', 'point_in_boundary',
], '.query')

# --- services ---
_register([
    'TemporalTimeseriesBuilder', 'TemporalDemographicService',
    'TimeseriesBuildResult',
], '.services')

__all__ = list(_LAZY_IMPORTS.keys())


def __getattr__(name: str):
    if name in _LAZY_IMPORTS:
        mod = importlib.import_module(_LAZY_IMPORTS[name], __package__)
        val = getattr(mod, name)
        setattr(sys.modules[__name__], name, val)
        return val
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__():
    return sorted(set(list(globals().keys()) + list(_LAZY_IMPORTS.keys())))

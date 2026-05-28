"""Deprecation shim — re-exports from :mod:`siege_utilities.engines.dataframe_engine`.

Moved during ELE-2437 (engine abstraction grouped under ``engines/``).
Will be removed in v4.0.0.
"""
import warnings as _warnings

_warnings.warn(
    "siege_utilities.data.dataframe_engine has moved to "
    "siege_utilities.engines.dataframe_engine. Update your imports; "
    "this shim will be removed in v4.0.0.",
    DeprecationWarning,
    stacklevel=2,
)

from siege_utilities.engines.dataframe_engine import *  # noqa: F401, F403, E402

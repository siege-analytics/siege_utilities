"""Deprecation shim — re-exports from :mod:`siege_utilities.engines.dataframe_engine`.

The engine abstraction moved to a top-level ``engines/`` package during
ELE-2437. This shim preserves the old import path for one deprecation
window; remove in the next minor release.
"""
import warnings as _warnings

_warnings.warn(
    "siege_utilities.data.dataframe_engine has moved to "
    "siege_utilities.engines.dataframe_engine. Update your imports; "
    "the old path will be removed in a future release.",
    DeprecationWarning,
    stacklevel=2,
)

from ..engines.dataframe_engine import *  # noqa: F401, F403, E402

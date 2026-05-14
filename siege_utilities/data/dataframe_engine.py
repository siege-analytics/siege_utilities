"""Deprecation shim -- re-exports from :mod:`siege_utilities.engines.dataframe_engine`.

The engine abstraction lives at the top-level ``engines/`` package.
This shim preserves the old import path; the old path will be removed
in v3.17.0.
"""
import warnings as _warnings

_warnings.warn(
    "siege_utilities.data.dataframe_engine has moved to "
    "siege_utilities.engines.dataframe_engine; the old path will be "
    "removed in v3.17.0. Update your imports.",
    DeprecationWarning,
    stacklevel=2,
)

from ..engines.dataframe_engine import *  # noqa: F401, F403, E402

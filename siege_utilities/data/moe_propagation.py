"""Deprecation shim — re-exports from :mod:`siege_utilities.data.statistics.moe_propagation`.

Moved during ELE-2437. Remove in the next minor release.
"""
import warnings as _warnings

_warnings.warn(
    "siege_utilities.data.moe_propagation has moved to "
    "siege_utilities.data.statistics.moe_propagation. Update your imports.",
    DeprecationWarning,
    stacklevel=2,
)

from .statistics.moe_propagation import *  # noqa: F401, F403, E402

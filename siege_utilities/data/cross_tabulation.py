"""Deprecation shim — re-exports from :mod:`siege_utilities.data.statistics.cross_tabulation`.

Moved during ELE-2437 (statistics primitives grouped under ``data/statistics/``).
Remove in the next minor release.
"""
import warnings as _warnings

_warnings.warn(
    "siege_utilities.data.cross_tabulation has moved to "
    "siege_utilities.data.statistics.cross_tabulation. Update your imports.",
    DeprecationWarning,
    stacklevel=2,
)

from .statistics.cross_tabulation import *  # noqa: F401, F403, E402

"""Deprecation shim — re-exports from :mod:`siege_utilities.data.statistics.cross_tabulation`.

Moved during ELE-2437 (statistics primitives grouped under ``data/statistics/``).
Will be removed in v4.0.0.
"""
import warnings as _warnings

_warnings.warn(
    "siege_utilities.data.cross_tabulation has moved to "
    "siege_utilities.data.statistics.cross_tabulation. Update your imports; "
    "this shim will be removed in v4.0.0.",
    DeprecationWarning,
    stacklevel=2,
)

from .statistics.cross_tabulation import *  # noqa: F401, F403, E402

# Re-export everything from the canonical module location
from .statistics.cross_tabulation import __all__ as _upstream_all  # noqa: F401, E402
__all__ = _upstream_all if _upstream_all else []  # noqa: E402

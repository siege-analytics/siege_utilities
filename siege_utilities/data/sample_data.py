"""Deprecation shim — re-exports from :mod:`siege_utilities.reference.sample_data`.

Moved during ELE-2437. Will be removed in v4.0.0.
"""
import warnings as _warnings

_warnings.warn(
    "siege_utilities.data.sample_data has moved to "
    "siege_utilities.reference.sample_data. Update your imports; "
    "this shim will be removed in v4.0.0.",
    DeprecationWarning,
    stacklevel=2,
)

from ..reference.sample_data import *  # noqa: F401, F403, E402

# Re-export everything from the canonical module location
from ..reference.sample_data import __all__ as _upstream_all  # noqa: F401, E402
__all__ = _upstream_all if _upstream_all else []  # noqa: E402

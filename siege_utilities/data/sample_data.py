"""Deprecation shim — re-exports from :mod:`siege_utilities.reference.sample_data`.

Moved during ELE-2437. Remove in the next minor release.
"""
import warnings as _warnings

_warnings.warn(
    "siege_utilities.data.sample_data has moved to "
    "siege_utilities.reference.sample_data. Update your imports.",
    DeprecationWarning,
    stacklevel=2,
)

from ..reference.sample_data import *  # noqa: F401, F403, E402

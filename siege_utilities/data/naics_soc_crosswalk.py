"""Deprecation shim — re-exports from :mod:`siege_utilities.reference.naics_soc_crosswalk`.

Moved during ELE-2437 (reference data grouped under ``reference/``).
Will be removed in v4.0.0.
"""
import warnings as _warnings

_warnings.warn(
    "siege_utilities.data.naics_soc_crosswalk has moved to "
    "siege_utilities.reference.naics_soc_crosswalk. Update your imports; "
    "this shim will be removed in v4.0.0.",
    DeprecationWarning,
    stacklevel=2,
)

from ..reference.naics_soc_crosswalk import *  # noqa: F401, F403, E402

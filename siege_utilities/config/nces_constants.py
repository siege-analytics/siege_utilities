"""Deprecation shim — NCES constants moved to :mod:`siege_utilities.geo.nces_constants`.

Moved during SU#577. Will be removed in v4.0.0.
"""
import warnings as _warnings

_warnings.warn(
    "siege_utilities.config.nces_constants has moved to "
    "siege_utilities.geo.nces_constants. Update your imports. "
    "This shim will be removed in v4.0.0.",
    DeprecationWarning,
    stacklevel=2,
)

from siege_utilities.geo.nces_constants import *  # noqa: F401, F403, E402

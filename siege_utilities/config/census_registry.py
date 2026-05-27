"""Deprecation shim — census registry moved to :mod:`siege_utilities.geo.census_registry`.

Moved during SU#577. Will be removed in v4.0.0.
"""
import warnings as _warnings

_warnings.warn(
    "siege_utilities.config.census_registry has moved to "
    "siege_utilities.geo.census_registry. Update your imports. "
    "This shim will be removed in v4.0.0.",
    DeprecationWarning,
    stacklevel=2,
)

from siege_utilities.geo.census_registry import *  # noqa: F401, F403, E402
from siege_utilities.geo.census_registry import _ALIAS_TO_CANONICAL  # noqa: F401, E402
from siege_utilities.geo.census_registry import _CURRENT_YEAR  # noqa: F401, E402

"""Deprecation shim — re-exports from :mod:`siege_utilities.geo.providers.nces_download`.

Moved during ELE-2438. Remove in the next minor release.
"""
import warnings as _warnings

_warnings.warn(
    "siege_utilities.geo.nces_download has moved to "
    "siege_utilities.geo.providers.nces_download. Update your imports.",
    DeprecationWarning,
    stacklevel=2,
)

from .providers.nces_download import *  # noqa: F401, F403, E402

"""Deprecation shim — re-exports from :mod:`siege_utilities.geo.providers.boundary_providers`.

Moved during ELE-2438 (spatial providers consolidated under
``geo/providers/``). Remove in the next minor release.
"""
import warnings as _warnings

_warnings.warn(
    "siege_utilities.geo.boundary_providers has moved to "
    "siege_utilities.geo.providers.boundary_providers. Update your imports.",
    DeprecationWarning,
    stacklevel=2,
)

from .providers.boundary_providers import *  # noqa: F401, F403, E402

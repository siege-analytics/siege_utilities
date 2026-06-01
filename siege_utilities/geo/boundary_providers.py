"""Deprecation shim — re-exports from :mod:`siege_utilities.geo.providers.boundary_providers`.

Moved during ELE-2438 (spatial providers consolidated under
``geo/providers/``). Will be removed in v4.0.0.
"""

# __all__ is inherited from the wildcard re-export below.

import warnings as _warnings

_warnings.warn(
    "siege_utilities.geo.boundary_providers has moved to "
    "siege_utilities.geo.providers.boundary_providers. Update your imports; "
    "this shim will be removed in v4.0.0.",
    DeprecationWarning,
    stacklevel=2,
)

from .providers.boundary_providers import *  # noqa: F401, F403, E402

__all__ = [
    "BoundaryFetchError",
    "BoundaryProvider",
    "CensusTIGERProvider",
    "GADMProvider",
    "RDHProvider",
    "resolve_boundary_provider",
]

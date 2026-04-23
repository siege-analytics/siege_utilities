"""Deprecation shim — re-exports from :mod:`siege_utilities.geo.providers.redistricting_data_hub`.

RDH is an external spatial data source; moved to ``geo/providers/`` under
ELE-2438 (D3) so all spatial sources live in one place. Remove in the
next minor release.
"""
import warnings as _warnings

_warnings.warn(
    "siege_utilities.data.redistricting_data_hub has moved to "
    "siege_utilities.geo.providers.redistricting_data_hub. Update your imports.",
    DeprecationWarning,
    stacklevel=2,
)

from ..geo.providers.redistricting_data_hub import *  # noqa: F401, F403, E402

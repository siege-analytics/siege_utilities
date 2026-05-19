"""Deprecation shim — re-exports from :mod:`siege_utilities.geo.providers.census_geocoder`.

Moved during ELE-2438. Remove in the next minor release.
"""
import warnings as _warnings

_warnings.warn(
    "siege_utilities.geo.census_geocoder has moved to "
    "siege_utilities.geo.providers.census_geocoder. Update your imports.",
    DeprecationWarning,
    stacklevel=2,
)

from .providers.census_geocoder import *  # noqa: F401, F403, E402
from .providers.census_geocoder import (  # noqa: F401, E402
    CensusGeocodeError,
    CensusGeocodeResult,
    CensusVintage,
    _get_geocoder,
    _parse_single_result,
    _safe_float,
    geocode_batch,
    geocode_batch_chunked,
    geocode_single,
    select_vintage_for_cycle,
)

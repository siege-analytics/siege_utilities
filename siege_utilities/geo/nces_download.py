"""Deprecation shim — re-exports from :mod:`siege_utilities.geo.providers.nces_download`.

Moved during ELE-2438. Will be removed in v4.0.0.
"""

import warnings as _warnings

_warnings.warn(
    "siege_utilities.geo.nces_download has moved to "
    "siege_utilities.geo.providers.nces_download. Update your imports; "
    "this shim will be removed in v4.0.0.",
    DeprecationWarning,
    stacklevel=2,
)

from .providers.nces_download import (  # noqa: E402
    DISTRICT_DATA_COLUMNS,
    LOCALE_BOUNDARY_COLUMNS,
    NCESDownloadError,
    NCESDownloader,
    SCHOOL_LOCATION_COLUMNS,
)

__all__ = [
    "LOCALE_BOUNDARY_COLUMNS",
    "SCHOOL_LOCATION_COLUMNS",
    "DISTRICT_DATA_COLUMNS",
    "NCESDownloadError",
    "NCESDownloader",
]

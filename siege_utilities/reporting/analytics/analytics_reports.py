"""Deprecation shim — re-exports from :mod:`siege_utilities.reporting.analytics_reports`.

Moved up one level during ELE-2439 so the ``reporting/analytics/`` subdirectory
can be removed once ``PollingAnalyzer`` is deleted in v4.0.0.
See ``docs/adr/0006-polling-analyzer-location.md``.
"""
import warnings as _warnings

_warnings.warn(
    "siege_utilities.reporting.analytics.analytics_reports has moved to "
    "siege_utilities.reporting.analytics_reports. Update your imports; "
    "this shim will be removed in v4.0.0.",
    DeprecationWarning,
    stacklevel=2,
)

from ..analytics_reports import *  # noqa: F401, F403, E402

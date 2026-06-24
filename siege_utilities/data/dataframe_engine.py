"""Deprecation shim — re-exports from :mod:`siege_utilities.engines.dataframe_engine`.

The multi-engine DataFrame abstraction moved to ``siege_utilities.engines``
(engines are an execution concern, not a data-domain one). Update your imports;
this shim will be removed in v4.0.0.
"""
import warnings as _warnings

_warnings.warn(
    "siege_utilities.data.dataframe_engine has moved to "
    "siege_utilities.engines.dataframe_engine. Update your imports; "
    "this shim will be removed in v4.0.0.",
    DeprecationWarning,
    stacklevel=2,
)

from ..engines.dataframe_engine import *  # noqa: F401, F403, E402

# Re-export everything from the canonical module location
from ..engines.dataframe_engine import __all__ as _upstream_all  # noqa: F401, E402
__all__ = _upstream_all if _upstream_all else []  # noqa: E402

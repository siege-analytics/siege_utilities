"""Unified exception hierarchy and error-handling strategy for siege_utilities.

All domain exceptions should inherit from :class:`SiegeError` so callers
can catch the entire family with a single ``except SiegeError:``.

The :data:`OnErrorStrategy` type and :func:`handle_error` utility let
functions expose a consistent ``on_error`` parameter that controls
whether failures raise, warn, or silently skip.
"""

from __future__ import annotations

import logging
import warnings
from typing import Literal, Optional, TypeVar

log = logging.getLogger(__name__)

#: Strategy for handling non-fatal errors.
#:
#: - ``"raise"`` — raise the exception (default, fail-fast).
#: - ``"warn"``  — emit a :class:`UserWarning` and return a fallback value.
#: - ``"skip"``  — log at DEBUG level and return a fallback value silently.
OnErrorStrategy = Literal["raise", "warn", "skip"]

T = TypeVar("T")


# ---------------------------------------------------------------------------
# Base exception
# ---------------------------------------------------------------------------

class SiegeError(Exception):
    """Root exception for all siege_utilities errors."""


# ---------------------------------------------------------------------------
# Domain exceptions
# ---------------------------------------------------------------------------

class SiegeDataError(SiegeError):
    """Error in data loading, parsing, or transformation."""


class SiegeGeoError(SiegeError):
    """Error in geographic operations (boundaries, spatial joins, etc.)."""


class SiegeAPIError(SiegeError):
    """Error communicating with an external API."""


class SiegeConfigError(SiegeError):
    """Error in configuration or registry lookup."""


class GitError(SiegeError):
    """Error executing a git command or git workflow operation."""


# ---------------------------------------------------------------------------
# Error-handling utility
# ---------------------------------------------------------------------------

def handle_error(
    exc: Exception,
    *,
    on_error: OnErrorStrategy = "raise",
    fallback: T = None,  # type: ignore[assignment]
    context: Optional[str] = None,
) -> T:
    """Apply the chosen error strategy to *exc*.

    Parameters
    ----------
    exc : Exception
        The caught exception.
    on_error : OnErrorStrategy
        ``"raise"`` re-raises, ``"warn"`` emits a warning, ``"skip"`` logs DEBUG.
    fallback : T
        Value to return when *on_error* is ``"warn"`` or ``"skip"``.
    context : str, optional
        Human-readable description of what was being attempted (included in
        warning / log message).

    Returns
    -------
    T
        *fallback* when the error is not re-raised.

    Raises
    ------
    Exception
        Re-raises *exc* when ``on_error="raise"``.
    """
    msg = f"{context}: {exc}" if context else str(exc)

    if on_error == "raise":
        raise exc
    elif on_error == "warn":
        warnings.warn(msg, UserWarning, stacklevel=3)
        log.warning(msg)
    else:  # skip
        log.debug(msg)

    return fallback

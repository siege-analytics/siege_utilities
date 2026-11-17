"""Retry policy shared by the CRM HTTP clients."""

import math
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Mapping

from siege_utilities.connectors._protocol import ConnectorRateLimitError


def validate_wait_settings(retry_backoff: float, max_retry_wait: float) -> None:
    """Require finite, nonnegative wait settings before sending a request."""
    for name, value in (("retry_backoff", retry_backoff), ("max_retry_wait", max_retry_wait)):
        if not math.isfinite(value) or value < 0:
            raise ValueError(f"{name} must be finite and nonnegative.")


def backoff_wait(backoff: float, attempt: int, max_retry_wait: float = 900.0) -> float:
    """Bound exponential fallback waits, including floating point overflow."""
    try:
        delay = backoff ** attempt
    except OverflowError:
        return max_retry_wait
    return min(delay, max_retry_wait)


def retry_attempts(method: str, configured: int) -> int:
    """Only retry methods whose repeated execution is safe.

    These connectors do not implement an API-supported idempotency key for
    POST. A timeout or server error after a write can mean it committed.
    """
    return max(1, configured) if method.upper() in {"GET", "PUT", "DELETE"} else 1


def rate_limit_error(
    headers: Mapping[str, str], message: str, fallback: float,
    *, max_retry_wait: float = 900.0,
) -> ConnectorRateLimitError:
    """Wait on a 429 before retrying or returning control to the caller.

    Retry-After accepts delay seconds or an HTTP date. Missing or malformed
    values use the configured backoff and leave retry_after unset. Hints over
    the cap, including non-finite values, raise without sleeping or retrying.
    """
    value = headers.get("Retry-After")
    delay = None
    if value is not None:
        try:
            delay = float(value)
        except OverflowError:
            delay = math.inf
        except (TypeError, ValueError):
            try:
                when = parsedate_to_datetime(value)
                if when.tzinfo is None:
                    when = when.replace(tzinfo=timezone.utc)
                delay = (when - datetime.now(timezone.utc)).total_seconds()
            except (TypeError, ValueError, OverflowError):
                pass
        if delay is not None:
            delay = max(0.0, delay) if math.isfinite(delay) else delay
    wait = delay if delay is not None else max(0.0, fallback)
    error = ConnectorRateLimitError(message, retry_after=delay)
    if not math.isfinite(wait) or wait > max_retry_wait:
        raise error
    time.sleep(wait)
    return error

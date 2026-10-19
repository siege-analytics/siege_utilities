"""Retry policy shared by the CRM HTTP clients."""

import math
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Mapping

from siege_utilities.connectors._protocol import ConnectorRateLimitError


def retry_attempts(method: str, configured: int) -> int:
    """Only retry methods whose repeated execution is safe.

    These connectors do not implement an API-supported idempotency key for
    POST. A timeout or server error after a write can mean it committed.
    """
    return max(1, configured) if method.upper() in {"GET", "PUT", "DELETE"} else 1


def rate_limit_error(
    headers: Mapping[str, str], message: str, fallback: float,
) -> ConnectorRateLimitError:
    """Wait on a 429 before retrying or returning control to the caller.

    Retry-After accepts delay seconds or an HTTP date. Missing or malformed
    values use the configured backoff and leave retry_after unset.
    """
    value = headers.get("Retry-After")
    delay = None
    if value is not None:
        try:
            delay = float(value)
        except (TypeError, ValueError):
            try:
                when = parsedate_to_datetime(value)
                if when.tzinfo is None:
                    when = when.replace(tzinfo=timezone.utc)
                delay = (when - datetime.now(timezone.utc)).total_seconds()
            except (TypeError, ValueError, OverflowError):
                pass
        if delay is not None:
            delay = max(0.0, delay) if math.isfinite(delay) else None
    time.sleep(delay if delay is not None else max(0.0, fallback))
    return ConnectorRateLimitError(message, retry_after=delay)

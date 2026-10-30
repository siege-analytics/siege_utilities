"""Shared OAuth replay and diagnostic handling for CRM transports."""

import logging
import time
from collections.abc import Callable

from siege_utilities.core._http import redact_secrets
from siege_utilities.connectors._protocol import ConnectorAuthError, ConnectorError
from siege_utilities.connectors._retry import backoff_wait, rate_limit_error, retry_attempts


class RedactingLogger(logging.LoggerAdapter):
    """Remove secrets before creating a record, including its message args.

    When bound to a connector (``extra={"secret_values": conn._secret_values}``)
    every record is additionally redacted against that connector's configured
    secret values, so a connector's own log line cannot echo a configured
    credential even if a new call site forgets to redact its arguments. The
    module-level logger (``extra={}``) keeps only the key/syntax redaction.
    Value redaction honours the shared length floor, so short configured values
    are still suppressed at the call site via ``_redact_field``.
    """

    def log(self, level, msg, *args, **kwargs):
        if self.isEnabledFor(level):
            text = str(msg) % args if args else str(msg)
            self.logger.log(
                level, redact_secrets(text, values=self._configured_values()), **kwargs,
            )

    def _configured_values(self):
        provider = (self.extra or {}).get("secret_values")
        if provider is None:
            return ()
        from siege_utilities.connectors._protocol import _SECRET_COLLECTION_FAILED

        values = provider()  # _secret_values is itself fail-closed and never raises
        if values is _SECRET_COLLECTION_FAILED or not isinstance(values, (list, tuple)):
            return ()
        return values


class RefreshOn401:
    """Allow one token renewal per logical request, across transport retries."""

    def __init__(self, refresh: Callable[[], None] | None, unauthorized: Callable | None = None):
        self._refresh = refresh
        self._refreshed = False
        self._unauthorized = unauthorized

    def send(self, send: Callable):
        response = send()
        if self.retry(response):
            response = send()
        return response

    def retry(self, response) -> bool:
        rejected = self._unauthorized(response) if self._unauthorized else response.status_code == 401
        if rejected and self._refresh and not self._refreshed:
            self._refreshed = True
            self._refresh()
            return True
        return False


def request_raw(
    connector, method: str, send: Callable, refresh: Callable | None,
    *, unauthorized: Callable | None = None,
):
    """Apply the JSON transport's retry and refresh rules to multipart/CSV I/O."""
    import requests

    auth = RefreshOn401(refresh, unauthorized)
    attempts = retry_attempts(method, getattr(connector, "_retry_attempts", 3))
    max_retry_wait = getattr(connector, "_max_retry_wait", 900.0)
    last_failure = "HTTP error"
    for attempt in range(1, attempts + 1):
        try:
            response = auth.send(send)
        except requests.RequestException as exc:
            last_failure = type(exc).__name__
        else:
            if response.status_code in (401, 403):
                raise ConnectorAuthError(f"CRM authentication failed ({response.status_code})")
            if response.status_code == 429:
                error = rate_limit_error(
                    response.headers, "CRM rate limit hit during bulk transfer.",
                    backoff_wait(connector._retry_backoff, attempt, max_retry_wait),
                    max_retry_wait=max_retry_wait,
                )
                if attempt < attempts:
                    continue
                raise error
            if not 500 <= response.status_code < 600:
                return response
            last_failure = f"HTTP {response.status_code}"
        if attempt < attempts:
            time.sleep(backoff_wait(connector._retry_backoff, attempt, max_retry_wait))
    raise ConnectorError(f"CRM bulk transfer failed after {attempts} attempts: {last_failure}")

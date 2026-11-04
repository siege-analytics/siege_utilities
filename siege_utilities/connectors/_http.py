"""Shared OAuth replay and diagnostic handling for CRM transports."""

import logging
import time
from collections.abc import Callable

from siege_utilities.core._http import contains_secret_value, redact_secrets
from siege_utilities.connectors._protocol import (
    _REDACTION_UNAVAILABLE,
    ConnectorAuthError,
    ConnectorError,
)
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
        if not self.isEnabledFor(level):
            return
        # Sanitize the FINAL rendered record, not the arguments (#1846 R-1846-5).
        # Contextual channels bypass message redaction: drop the traceback
        # channels entirely (a connector log site carries detail in the message,
        # which is sanitized), and redact `extra` field values while keeping the
        # keys so downstream formatters still render them.
        kwargs.pop("exc_info", None)
        kwargs.pop("stack_info", None)
        extra = kwargs.pop("extra", None)
        values, usable = self._configured_values()
        template = str(msg)
        if not usable:
            # Fail closed: collection could not be trusted, so no argument can be
            # proven secret-free. Emit only the trusted template with a marker.
            message = redact_secrets(template) + " [log args suppressed: secret collection unavailable]"
        else:
            rendered = template % args if args else template
            redacted = redact_secrets(rendered, values=values)
            if contains_secret_value(redacted, values):
                # A configured value below the length floor is still present and
                # cannot be removed, so emit only the trusted template.
                message = redact_secrets(template) + " [log args suppressed: short credential]"
            else:
                message = redacted
        if extra:
            rendered_extra = {}
            for key, value in extra.items():
                if not usable:
                    rendered_extra[key] = _REDACTION_UNAVAILABLE
                    continue
                redacted = redact_secrets(str(value), values=values)
                rendered_extra[key] = (
                    _REDACTION_UNAVAILABLE if contains_secret_value(redacted, values) else redacted
                )
            kwargs["extra"] = rendered_extra
        self.logger.log(level, message, **kwargs)

    def _configured_values(self):
        """Return ``(values, usable)``. ``usable`` is False only when a bound
        connector's collection failed or returned a non-sequence; the module
        logger (no provider) is usable with key/syntax-only redaction."""
        provider = (self.extra or {}).get("secret_values")
        if provider is None:
            return (), True
        from siege_utilities.connectors._protocol import _SECRET_COLLECTION_FAILED

        # _secret_values is itself fail-closed, but the thunk late-binds a
        # replaceable policy, so a raising provider must also fail closed here
        # rather than crash the log call or fall through to no redaction.
        try:
            values = provider()
        except Exception:
            return (), False
        if values is _SECRET_COLLECTION_FAILED or not isinstance(values, (list, tuple)):
            return (), False
        return values, True


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

"""Map Parsons-raised exceptions onto the siege ``ConnectorError`` hierarchy.

Every siege wrapper of a Parsons connector routes its API calls through
:func:`map_parsons_exception` (or the :func:`translate_errors` decorator) so
callers see a single error contract regardless of which Parsons connector
raised. This satisfies ``SU-1`` (errors are not data) and ``SU-2`` (does it
do what it says): the wrapper class advertises ``ConnectorError``, and every
raised exception belongs to that hierarchy or its subclasses.

Design (from P0-4, docs/PARSONS_AUTH_MATRIX.md, and P0-3 spike ANALYSIS.md):

- ``ImportError`` from a Parsons module → :class:`ConnectorError` naming the
  missing extra so the caller knows which ``siege_utilities[parsons-*]``
  extra to install.
- ``requests.exceptions.HTTPError`` (or a subclass) with 401/403 status →
  :class:`ConnectorAuthError`.
- ``requests.exceptions.HTTPError`` with 404 status → :class:`ConnectorNotFoundError`.
- ``requests.exceptions.HTTPError`` with 429 status → :class:`ConnectorRateLimitError`
  (with ``retry_after`` from the ``Retry-After`` header when present).
- Any other Parsons or transport exception → :class:`ConnectorError` with
  ``raise ... from`` chaining so ``exc.__cause__`` preserves the original.
"""

from __future__ import annotations

import functools
from typing import Any, Callable, TypeVar

from ...connectors._protocol import (
    ConnectorAuthError,
    ConnectorError,
    ConnectorNotFoundError,
    ConnectorRateLimitError,
)

__all__ = [
    "map_parsons_exception",
    "translate_errors",
]


F = TypeVar("F", bound=Callable[..., Any])


def _status_code(exc: BaseException) -> int | None:
    """Best-effort extraction of an HTTP status code from any exception shape.

    Parsons raises ``requests.exceptions.HTTPError`` through most connectors,
    which carries a ``.response`` with ``.status_code``. Some connectors wrap
    the requests exception in their own subclass; the attribute chain is the
    same. Return None if no status is available.
    """
    response = getattr(exc, "response", None)
    if response is None:
        return None
    return getattr(response, "status_code", None)


def _retry_after(exc: BaseException) -> float | None:
    """Extract Retry-After header seconds if present.

    RFC 7231 allows either an integer seconds value or an HTTP-date. We only
    parse the integer form here — the HTTP-date form is rare in practice for
    the Parsons connector surface (VAN, ActionKit, Mobilize, ActBlue).
    """
    response = getattr(exc, "response", None)
    if response is None:
        return None
    headers = getattr(response, "headers", None)
    if headers is None:
        return None
    raw = headers.get("Retry-After")
    if raw is None:
        return None
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


def map_parsons_exception(exc: BaseException, *, connector: str | None = None) -> ConnectorError:
    """Translate a Parsons or transport exception to a ``ConnectorError``.

    Never returns ``None``. Never swallows the original. The returned
    exception is meant for ``raise ... from exc`` — the caller is expected
    to preserve chaining.

    Message shape: names only the connector name, HTTP status (if any),
    and the underlying exception's CLASS NAME — never the exception's
    string form. Transport and credential backends may include secrets,
    resolved values, URLs, or connection strings in their message text;
    interpolating that into our public error would leak them into logs,
    PR bodies, and reraise chains. Callers who need the original text
    can inspect ``exc.__cause__`` (which we preserve).

    Args:
        exc: The exception raised by Parsons or its underlying transport.
        connector: Optional connector name for message context
            (e.g., ``"van"``, ``"action_kit"``).

    Returns:
        A ``ConnectorError`` (or subclass) with a sanitized message and
        the original preserved via chaining at the raise site.
    """
    prefix = f"[{connector}] " if connector else ""
    cls = type(exc).__name__

    if isinstance(exc, ImportError):
        # ImportError message is safe to include (module name only, no
        # credentials); it's actionable for the "which extra to install"
        # signal.
        return ConnectorError(
            f"{prefix}Parsons module import failed ({cls}). "
            f"Install the correct siege_utilities[parsons-*] extra "
            f"(see docs/PARSONS_DEP_MATRIX.md)."
        )

    status = _status_code(exc)
    if status in (401, 403):
        return ConnectorAuthError(
            f"{prefix}Authentication failed (HTTP {status}; cause: {cls})"
        )
    if status == 404:
        return ConnectorNotFoundError(
            f"{prefix}Resource not found (HTTP 404; cause: {cls})"
        )
    if status == 429:
        return ConnectorRateLimitError(
            f"{prefix}Rate limit exceeded (HTTP 429; cause: {cls})",
            retry_after=_retry_after(exc),
        )

    return ConnectorError(f"{prefix}{cls}")


def translate_errors(connector: str) -> Callable[[F], F]:
    """Decorator wrapping a wrapper-method body so raises → ``ConnectorError``.

    Preserves ``ConnectorError`` subclasses if raised directly by the wrapper
    (e.g., the wrapper raises ``ConnectorAuthError`` after inspecting a
    credential dict) so we don't double-wrap.

    Synchronous-only. Applying this decorator to a coroutine function is
    rejected at decoration time with :class:`TypeError` — the synchronous
    wrapper cannot observe or translate exceptions raised inside an
    ``await``. Native ``async`` support can be added later without
    breaking sync callers.
    """
    import inspect

    def decorator(fn: F) -> F:
        if inspect.iscoroutinefunction(fn):
            raise TypeError(
                f"translate_errors({connector!r}) does not support coroutine "
                f"functions; wrap the sync body only, or add native async "
                f"translation before decorating {fn.__qualname__!r}."
            )

        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return fn(*args, **kwargs)
            except ConnectorError:
                # already in our hierarchy — don't double-wrap
                raise
            except Exception as exc:  # noqa: BLE001
                raise map_parsons_exception(exc, connector=connector) from exc

        return wrapper  # type: ignore[return-value]

    return decorator

"""
Connector protocol and shared types for CRM integrations.

Defines the contract that all CRM connectors satisfy, plus supporting
types for bulk operations and error handling. Follows the Gazetteer
Protocol pattern (``geo.gazetteers.base``): narrow, runtime-checkable,
intentionally minimal.

Connectors are primitives — pull/push records. Transformation lives
in ``identifiers/``, ``geo/``, ``reporting/``. No sync scheduling,
no CDC, no conflict resolution beyond dedup.
"""

from __future__ import annotations

import json
import math
import threading
from dataclasses import dataclass, field
from datetime import date, datetime
from collections.abc import Callable
from typing import Any, Protocol, runtime_checkable

import numpy as np
import pandas as pd

from siege_utilities.core._http import _MIN_SECRET_VALUE_LEN, redact_secrets

# Distinct fail-closed signal: secret collection could not be trusted, so the
# caller must not emit any upstream text it cannot prove secret-free.
_SECRET_COLLECTION_FAILED = object()
# Constant substituted when redaction is unavailable. Carries no upstream detail.
_REDACTION_UNAVAILABLE = "[secret-redaction unavailable]"
# Fixed log message when a record cannot be safely rendered (short credential or
# failed collection with a non-literal template).
_LOG_SUPPRESSED = "[log message suppressed]"
# Per-thread re-entrancy guard: while the boundary is sanitizing one exception,
# a nested failure in a wrapped public callable (e.g. a hostile secret getter)
# re-raises raw so fail-closed collection handles it rather than recursing.
_boundary_state = threading.local()

__all__ = [
    "ConnectorProtocol",
    "UpsertResult",
    "UpsertError",
    "ConnectorError",
    "ConnectorAuthError",
    "ConnectorRateLimitError",
    "ConnectorNotFoundError",
]


def sanitize_record(row: dict[str, Any]) -> dict[str, Any]:
    """Return JSON-safe upsert fields without mutating the input row.

    Omit top-level missing fields (None, NaN, NaT, pd.NA). Recurse through
    dicts and lists, keeping explicit nested None as JSON null. Missing
    pandas/numpy sentinels in nested dict values raise ConnectorError with
    the key path. Missing list items become null, preserving their positions.
    Tuples become JSON lists.
    Dates use ISO 8601 and numpy scalars become native Python scalars.
    Scalar leaves that strict JSON cannot encode (such as Decimal or infinity)
    keep their string representation; containers are never stringified.

    Raises:
        ConnectorError: a nested dict contains a missing pandas/numpy sentinel,
            or an unsupported container, invalid JSON object key, circular
            reference, or excessive nesting cannot be represented as JSON.
    """
    try:
        return _sanitize_value(row, path="$", ancestors=set(), top_level=True)
    except RecursionError as exc:
        raise ConnectorError("Record nesting exceeds the JSON recursion limit") from exc


def _sanitize_value(value: Any, *, path: str, ancestors: set[int], top_level: bool) -> Any:
    if isinstance(value, (dict, list, tuple)):
        container_id = id(value)
        if container_id in ancestors:
            raise ConnectorError(f"Circular container reference at {path}")
        ancestors.add(container_id)
        try:
            if isinstance(value, dict):
                sanitized = {}
                for key, child in value.items():
                    try:
                        json.dumps({key: None}, allow_nan=False)
                    except (TypeError, ValueError) as exc:
                        raise ConnectorError(
                            f"Invalid JSON object key at {path}: {key!r}"
                        ) from exc
                    child_path = f"{path}[{key!r}]"
                    # pd.isna on containers returns arrays, not a scalar flag.
                    if pd.api.types.is_scalar(child) and pd.isna(child):
                        if top_level:
                            continue
                        if child is not None:
                            raise ConnectorError(
                                f"Missing pandas/numpy sentinel at {child_path}"
                            )
                    sanitized[key] = _sanitize_value(
                        child, path=child_path, ancestors=ancestors, top_level=False,
                    )
                return sanitized
            return [
                _sanitize_value(
                    child, path=f"{path}[{index}]", ancestors=ancestors, top_level=False,
                )
                for index, child in enumerate(value)
            ]
        finally:
            ancestors.remove(container_id)

    if not pd.api.types.is_scalar(value):
        raise ConnectorError(
            f"Unsupported value or container type {type(value).__name__} at {path}"
        )
    if pd.isna(value):
        return None
    if isinstance(value, (datetime, date)):
        value = value.isoformat()
    elif isinstance(value, np.bool_):
        value = bool(value)
    elif isinstance(value, np.integer):
        value = int(value)
    elif isinstance(value, np.floating):
        value = float(value)
    try:
        json.dumps(value, allow_nan=False)
    except (TypeError, ValueError):
        value = str(value)
    return value


# ---------------------------------------------------------------------------
# Error hierarchy
# ---------------------------------------------------------------------------


class _SecretRedactionMixin:
    """Connector-boundary redaction of the instance's own configured secret
    values.

    Diagnostic text only -- exception messages/reprs, log records, and
    UpsertResult/UpsertError reprs. NEVER applied to outgoing request payloads,
    URLs, or headers (those must stay byte-identical; see #1846 B2 item 4).
    """

    _SECRET_ATTRS = (
        "_client_secret", "_access_token", "_refresh_token", "_password", "_api_key",
        "_security_token",
    )

    @property
    def _log(self):
        """Instance logger that redacts this connector's configured values.

        Every record emitted through this adapter is redacted against the
        instance's own secret values, so a log site that interpolates a value
        equal to a configured long credential cannot leak it even without an
        explicit ``_redact_field`` call. Short configured values still need
        site-level suppression via ``_redact_field`` (the shared length floor
        keeps the adapter from blanking common short strings). Cached per
        instance; the bound thunk re-reads ``self._secret_values`` at log time
        so both later credential changes and a replaced collection policy are
        observed rather than frozen at cache time.
        """
        adapter = self.__dict__.get("_redacting_log")
        if adapter is None:
            import logging

            from siege_utilities.connectors._http import RedactingLogger

            adapter = RedactingLogger(
                logging.getLogger(type(self).__module__),
                {"secret_values": lambda: self._secret_values()},
            )
            self.__dict__["_redacting_log"] = adapter
        return adapter

    def _secret_values(self) -> "list[str] | object":
        """Configured secret values to redact, or the fail-closed signal.

        Returns a list of the instance's own secret strings, or
        ``_SECRET_COLLECTION_FAILED`` when collection could not complete. A
        caller-supplied header mapping is untrusted: its ``.get`` may be a
        hostile override that raises anything (its own exception text can
        carry a secret). Any such failure yields the fail-closed signal rather
        than a partial list, so ``_redact`` cannot emit text it did not fully
        scan. The broad handler is reviewed in
        scripts/exception_contracts_allowlist.json (#1846 B2 D5).
        """
        try:
            values: list[str] = []
            for attr in self._SECRET_ATTRS:
                value = getattr(self, attr, None)
                if isinstance(value, str) and value:
                    values.append(value)
            session = getattr(self, "_session", None)
            headers = getattr(session, "headers", None)
            if headers is not None:
                for header in ("Authorization", "X-Api-Key"):
                    raw = headers.get(header)
                    if isinstance(raw, str) and raw:
                        values.append(raw[7:] if raw[:7].lower() == "bearer " else raw)
            return values
        except Exception:
            # Build the signal AFTER the except so no raise chains the caught
            # exception (whose text may hold a secret) into __context__.
            return _SECRET_COLLECTION_FAILED

    def _redact(self, text: object) -> str:
        """Key-based plus configured-value redaction for diagnostic text.

        Fails closed: when secret collection could not be trusted, return a
        constant carrying no upstream detail rather than text scanned only by
        the key-based pass (which cannot remove an un-enumerated secret value).
        """
        values = self._secret_values()
        if values is _SECRET_COLLECTION_FAILED:
            return _REDACTION_UNAVAILABLE
        return redact_secrets(str(text), values=values)

    def _safe_upstream_detail(self, text: object, *, limit: int = 200) -> str | None:
        """Value+syntax-redacted upstream text, or ``None`` when untrustworthy.

        Returns ``None`` (caller must fall back to trusted constants only) when
        secret collection failed, or when any configured secret is shorter than
        the value redactor's minimum length -- such a secret is not removed by
        value replacement (short strings are skipped so common words cannot
        blank diagnostics), so echoing upstream text could expose it. Value
        redaction runs on the full text before truncation, so a long secret is
        removed in full rather than merely having its tail cut (#1846 B2 D3/D4).
        """
        values = self._secret_values()
        if values is _SECRET_COLLECTION_FAILED:
            return None
        if any(len(value) < _MIN_SECRET_VALUE_LEN for value in values):
            return None
        return redact_secrets(str(text), values=values)[:limit]

    def _redact_field(self, value: object) -> object:
        """Value-aware redaction for one diagnostic field (D3 all-paths).

        ``None`` stays ``None``. Otherwise return the configured-value-redacted
        text, or the trusted ``[REDACTED]`` constant when a configured credential
        is too short to remove by value (D3 suppression) or collection failed.
        This is the render-safe transform for UpsertError fields and the
        rendered repr copy of returned ids; it never mutates the stored value.
        """
        if value is None:
            return None
        detail = self._safe_upstream_detail(str(value))
        return "[REDACTED]" if detail is None else detail

    # -- Public-edge redaction boundary (#1846 R-1846-5/6) -------------------
    # One runtime boundary enforced here, not site by site: every public
    # connector callable (methods, __init__, coroutines, generators and
    # property/classmethod/staticmethod descriptors) is wrapped so any exception
    # leaving it is re-raised as the same class with a sanitized message, and the
    # RedactingLogger sanitizes the final rendered record. Per-site
    # ``_redact_field`` calls above stay as defense in depth. The transport path
    # (URLs, headers, payloads) is never touched, so request bytes are identical.
    # Out of scope: methods added after class creation, inherited non-mixin
    # methods, and arbitrary in-process side channels (warnings, other loggers).

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        for name, attr in list(vars(cls).items()):
            wrapped = _SecretRedactionMixin._wrap_attr(name, attr)
            if wrapped is not None:
                setattr(cls, name, wrapped)

    @staticmethod
    def _wants_wrap(name, func):
        import inspect

        if not inspect.isfunction(func):
            return False
        if getattr(func, "_secret_boundary", False):
            return False
        return name == "__init__" or not name.startswith("_")

    @staticmethod
    def _wrap_attr(name, attr):
        """Return a boundary-wrapped replacement for a public attr, or None."""
        import inspect

        if isinstance(attr, (staticmethod, classmethod)):
            inner = attr.__func__
            if not _SecretRedactionMixin._wants_wrap(name, inner):
                return None
            # #1846 R-1846-7 F3: a class/static method has no instance, so the
            # instance-shaped boundary would bind ``cls``/the first arg as
            # ``self`` and raise a secondary TypeError/AttributeError. Wrap with a
            # contextless boundary: classmethod forwards ``cls``, staticmethod
            # takes no receiver, and any failure becomes the trusted constant.
            wrapped = _SecretRedactionMixin._wrap_contextless(
                inner, receiver=isinstance(attr, classmethod)
            )
            return type(attr)(wrapped)
        if isinstance(attr, property):
            parts = (attr.fget, attr.fset, attr.fdel)
            new = tuple(
                _SecretRedactionMixin._wrap_callable(part)
                if (part is not None and not getattr(part, "_secret_boundary", False))
                else part
                for part in parts
            )
            if new == parts:
                return None
            return property(new[0], new[1], new[2], attr.__doc__)
        if inspect.isfunction(attr) and _SecretRedactionMixin._wants_wrap(name, attr):
            return _SecretRedactionMixin._wrap_callable(attr)
        return None

    @staticmethod
    def _wrap_callable(func):
        """Wrap a sync/async/generator callable so exceptions are sanitized."""
        import functools
        import inspect

        if inspect.iscoroutinefunction(func):
            @functools.wraps(func)
            async def boundary(self, *args, **kwargs):
                try:
                    return await func(self, *args, **kwargs)
                except Exception as exc:
                    sanitized = _SecretRedactionMixin._sanitize_or_reraise(self, exc, func)
                    raise sanitized from None
        elif inspect.isasyncgenfunction(func):
            @functools.wraps(func)
            async def boundary(self, *args, **kwargs):
                # #1846 R-1846-7 F4: drive the inner async generator and forward
                # the full protocol -- asend (values), athrow (exceptions) and
                # aclose (GeneratorExit -> inner finally) -- instead of a plain
                # ``async for ... yield`` adapter that drops send/throw/close.
                # Exceptions escaping the inner generator are sanitized.
                agen = func(self, *args, **kwargs)
                try:
                    item = await agen.__anext__()
                except StopAsyncIteration:
                    return
                except Exception as exc:
                    raise _SecretRedactionMixin._sanitize_or_reraise(self, exc, func) from None
                while True:
                    try:
                        sent = yield item
                    except GeneratorExit:
                        await agen.aclose()
                        raise
                    except BaseException as thrown:
                        try:
                            item = await agen.athrow(thrown)
                        except StopAsyncIteration:
                            return
                        except Exception as exc:
                            raise _SecretRedactionMixin._sanitize_or_reraise(self, exc, func) from None
                    else:
                        try:
                            item = await agen.asend(sent)
                        except StopAsyncIteration:
                            return
                        except Exception as exc:
                            raise _SecretRedactionMixin._sanitize_or_reraise(self, exc, func) from None
        elif inspect.isgeneratorfunction(func):
            @functools.wraps(func)
            def boundary(self, *args, **kwargs):
                try:
                    yield from func(self, *args, **kwargs)
                except Exception as exc:
                    sanitized = _SecretRedactionMixin._sanitize_or_reraise(self, exc, func)
                    raise sanitized from None
        else:
            @functools.wraps(func)
            def boundary(self, *args, **kwargs):
                try:
                    return func(self, *args, **kwargs)
                except Exception as exc:
                    sanitized = _SecretRedactionMixin._sanitize_or_reraise(self, exc, func)
                # Raise OUTSIDE the except block so the sanitized exception
                # carries no implicit __context__ (and ``from None`` clears
                # __cause__). Async/generator variants raise inside the handler;
                # their suppressed outer __context__ is a documented limit.
                raise sanitized from None

        boundary._secret_boundary = True
        return boundary

    @staticmethod
    def _wrap_contextless(func, *, receiver):
        """Wrap a classmethod/staticmethod (#1846 R-1846-7 F3).

        There is no instance, so there is no configured credential to redact
        against: any failure becomes the trusted constant for the SAME class via
        ``_sanitize_contextless``. ``receiver`` is True for classmethods (the
        bound ``cls`` is forwarded) and False for staticmethods (no receiver);
        the enclosing descriptor rebinds the returned plain function.
        """
        import functools

        if receiver:
            @functools.wraps(func)
            def boundary(cls, *args, **kwargs):
                try:
                    return func(cls, *args, **kwargs)
                except Exception as exc:
                    raise _SecretRedactionMixin._sanitize_contextless(exc) from None
        else:
            @functools.wraps(func)
            def boundary(*args, **kwargs):
                try:
                    return func(*args, **kwargs)
                except Exception as exc:
                    raise _SecretRedactionMixin._sanitize_contextless(exc) from None

        boundary._secret_boundary = True
        return boundary

    @staticmethod
    def _sanitize_or_reraise(self, exc, func):
        """Sanitize *exc*, or re-raise raw if already sanitizing on this thread.

        Re-entrancy (a hostile secret getter calling a wrapped public method
        during sanitization) re-raises raw so fail-closed collection handles it
        rather than recursing. ``__init__`` is sanitized like any other boundary
        callable: a post-registration fault redacts the stored credential, and a
        pre-registration validation error ("...are required") carries no stored
        or interpolated secret, so value-redaction leaves its trusted literal
        intact. (Limit: a constructor that inlined a caller-passed secret into a
        pre-registration message could not value-redact it; current connectors
        never do, and the short-credential constant covers any that later did.)
        """
        if getattr(_boundary_state, "active", False):
            raise exc
        return self._sanitize_exception(exc)

    def _sanitize_exception(self, exc):
        """Return a sanitized exception; never raise, never leave raw text.

        Read every exception metadatum ONCE inside a single fail-closed guard
        (#1846 R-1846-7 F2): a faulting getter or ``__str__`` cannot be re-read,
        and any failure goes straight to the ``ConnectorError`` constant fallback
        carrying ``.original_type``. The SAME class is rebuilt from only the
        sanitized message; only the validated numeric scalars captured in that one
        read are set on it -- original attributes are NEVER copied back, so a rich
        exception whose ``__str__`` renders ``status_code``/``retry_after`` cannot
        restore raw text. The raw exception reference is dropped before returning
        so a frame-locals capture cannot retain it.
        """
        original_type = type(exc).__name__
        _boundary_state.active = True
        try:
            status = self._validated_status(exc)
            retry_after = self._validated_retry_after(exc)
            message = self._boundary_message(exc, status)
            read_ok = True
        except Exception:
            read_ok = False
        finally:
            _boundary_state.active = False
        if not read_ok:
            # Fail closed: a metadata getter or __str__ raised. Nothing is
            # re-read; emit the bare class-name constant.
            rebuilt = self._constant_error(original_type)
            del exc
            return rebuilt
        try:
            rebuilt = exc.__class__(message)
            rebuilt.args = (message,)
            self._apply_validated_scalars(rebuilt, status, retry_after)
        except Exception:
            # Reconstruction or a scalar set failed: fall back to the always
            # constructible constant and set the same validated scalars on it.
            rebuilt = self._constant_error(original_type)
            self._apply_validated_scalars(rebuilt, status, retry_after)
        del exc
        return rebuilt

    @staticmethod
    def _sanitize_contextless(exc):
        """Sanitize an exception from a class/static method (no instance creds).

        With no instance there is no configured value to redact against, so the
        message is always the trusted constant (class name plus a validated
        numeric HTTP status). The SAME class is rebuilt so callers still catch
        their own type; a class that cannot be rebuilt from one message falls back
        to ``ConnectorError`` carrying ``.original_type``. Metadata is read once
        under the same fail-closed guard as the instance path.
        """
        original_type = type(exc).__name__
        _boundary_state.active = True
        try:
            status = _SecretRedactionMixin._validated_status(exc)
            retry_after = _SecretRedactionMixin._validated_retry_after(exc)
            label = f"{original_type} (HTTP {status})" if status is not None else original_type
            read_ok = True
        except Exception:
            read_ok = False
        finally:
            _boundary_state.active = False
        if not read_ok:
            return _SecretRedactionMixin._constant_error(original_type)
        try:
            rebuilt = exc.__class__(label)
            rebuilt.args = (label,)
            _SecretRedactionMixin._apply_validated_scalars(rebuilt, status, retry_after)
        except Exception:
            rebuilt = _SecretRedactionMixin._constant_error(original_type)
            _SecretRedactionMixin._apply_validated_scalars(rebuilt, status, retry_after)
        return rebuilt

    @staticmethod
    def _constant_error(original_type):
        """A ``ConnectorError`` whose text is the trusted class-name constant."""
        rebuilt = ConnectorError(original_type)
        rebuilt.original_type = original_type
        return rebuilt

    @staticmethod
    def _apply_validated_scalars(rebuilt, status, retry_after):
        """Set ONLY the validated numeric scalars captured in the single read.

        Never copies original attributes back: ``status``/``retry_after`` here are
        already proven safe (a plain ``int`` in range / an exact ``int``/``float``
        that is either non-finite or non-negative), so setting them cannot restore
        raw credential text.
        """
        if status is not None:
            rebuilt.status_code = status
            rebuilt.status = status
        if retry_after is not None:
            rebuilt.retry_after = retry_after

    @staticmethod
    def _validated_status(exc):
        """A plausible HTTP status int from *exc*, else None.

        Only a *plain* ``int`` (``type(x) is int``, so ``bool`` and hostile int
        subclasses whose ``__format__``/``__str__`` could render a credential are
        rejected) in the 100-599 range. Never parsed from text.
        """
        for attr in ("status_code", "status"):
            value = getattr(exc, attr, None)
            if type(value) is int and 100 <= value <= 599:
                return value
        return None

    @staticmethod
    def _validated_retry_after(exc):
        """A safe retry-after scalar from *exc*, else None.

        Requires an exact ``int``/``float`` (``type(x) in (int, float)``, so
        ``bool``, int/float subclasses with a hostile ``__str__``/``__format__``,
        strings and arbitrary objects are all dropped). A plain number cannot
        carry credential text; the exact-type check is the leak guard.

        Finiteness is handled asymmetrically: a NON-finite value (``inf``/``nan``)
        passes through because the B1 over-cap contract surfaces it as the "over
        cap, do not sleep" sentinel (test_connector_over_cap_raises_without_sleep).
        A FINITE value must be non-negative; a negative finite ``retry_after`` is
        dropped. ``nan >= 0`` is False, so the non-finite carve-out is checked
        first to preserve the sentinel.
        """
        value = getattr(exc, "retry_after", None)
        if type(value) in (int, float) and (not math.isfinite(value) or value >= 0):
            return value
        return None

    def _boundary_message(self, exc, status):
        """Sanitized message: a trusted constant, or the value-redacted message.

        Strict short policy (#1846 R-1846-6/7): when any configured credential is
        under the length floor or collection failed, emit ONLY a trusted constant
        -- the class name plus the pre-validated numeric HTTP ``status`` captured
        by the single metadata read -- because reversible encodings
        (percent/base64/HTML/hex/newline) make residual scanning unsafe.
        Otherwise value-redact the rendered message against configured values.
        ``status`` is read once by the caller and never re-read here.
        """
        values = self._secret_values()
        failed = values is _SECRET_COLLECTION_FAILED
        short = (not failed) and any(len(value) < _MIN_SECRET_VALUE_LEN for value in values)
        if failed or short:
            label = type(exc).__name__
            return f"{label} (HTTP {status})" if status is not None else label
        return redact_secrets(str(exc), values=values)


class ConnectorError(Exception):
    """Base for all connector errors."""

    def __init__(self, message: str) -> None:
        super().__init__(redact_secrets(str(message)))


class ConnectorAuthError(ConnectorError):
    """Authentication or authorization failure."""


class ConnectorRateLimitError(ConnectorError):
    """API rate limit exceeded."""

    def __init__(self, message: str, retry_after: float | None = None) -> None:
        super().__init__(message)
        self.retry_after = retry_after


class ConnectorNotFoundError(ConnectorError):
    """Requested object type or record not found."""


# ---------------------------------------------------------------------------
# Bulk operation result types
# ---------------------------------------------------------------------------


@dataclass(repr=False)
class UpsertError:
    """One failed record in a bulk upsert."""

    record_index: int
    message: str
    field: str | None = None
    code: str | None = None

    def __post_init__(self) -> None:
        for name in ("message", "field", "code"):
            value = getattr(self, name)
            if value is not None:
                setattr(self, name, redact_secrets(str(value)))

    def __repr__(self) -> str:
        values = ", ".join(
            f"{name}={redact_secrets(str(value))!r}" if value is not None else f"{name}=None"
            for name, value in (("message", self.message), ("field", self.field), ("code", self.code))
        )
        return f"UpsertError(record_index={self.record_index}, {values})"


@dataclass(repr=False)
class UpsertResult:
    """Outcome of a bulk upsert operation.

    Never silent — ``failure_count == 0`` is the only success signal.
    Callers must check ``errors`` when ``failure_count > 0`` (SU-1).
    """

    success_count: int
    failure_count: int
    created_ids: list[str] = field(default_factory=list)
    updated_ids: list[str] = field(default_factory=list)
    errors: list[UpsertError] = field(default_factory=list)
    # Connector-supplied value-aware redactor (#1846 D1 render-only). Applied
    # ONLY inside __repr__ over a copy; the stored id lists stay byte-identical.
    # Excluded from equality and from the rendered repr itself.
    redact: "Callable[[object], object] | None" = field(
        default=None, repr=False, compare=False,
    )

    def __repr__(self) -> str:
        render = self.redact if self.redact is not None else (lambda value: redact_secrets(str(value)))
        created = [render(value) for value in self.created_ids]
        updated = [render(value) for value in self.updated_ids]
        return (
            f"UpsertResult(success_count={self.success_count}, failure_count={self.failure_count}, "
            f"created_ids={created!r}, updated_ids={updated!r}, errors={self.errors!r})"
        )

    @property
    def total(self) -> int:
        return self.success_count + self.failure_count

    @property
    def ok(self) -> bool:
        return self.failure_count == 0


# ---------------------------------------------------------------------------
# Protocol
# ---------------------------------------------------------------------------


@runtime_checkable
class ConnectorProtocol(Protocol):
    """CRM connector contract.

    The protocol is intentionally narrow — eight methods. Backends layer
    OAuth token refresh, rate-limit backoff, pagination, and other plumbing
    internally; callers just see this surface.

    Each connector may expose vendor-specific methods beyond the protocol
    (e.g., ``SalesforceConnector.soql()``). The protocol captures the
    shared shape that reporting, dedup, and enrichment pipelines depend on.
    """

    @property
    def provider_name(self) -> str:
        """Human-readable backend identifier (``"salesforce"``, etc.)."""
        ...

    def authenticate(self) -> None:
        """Establish an authenticated session.

        Raises:
            ConnectorAuthError: credentials invalid or auth flow failed.
        """
        ...

    def is_connected(self) -> bool:
        """Whether the connector has an active, authenticated session."""
        ...

    def list_object_types(self) -> list[str]:
        """Available object types (``["Contact", "Account", ...]``)."""
        ...

    def get_objects(
        self,
        object_type: str,
        *,
        fields: list[str] | None = None,
        filters: dict[str, Any] | None = None,
        limit: int | None = None,
    ) -> pd.DataFrame:
        """Fetch records of *object_type* as a DataFrame.

        Args:
            object_type: CRM object name (``"Contact"``, ``"Opportunity"``).
            fields: Columns to return. ``None`` for a sensible default set.
            filters: Key-value filter criteria (interpretation is
                connector-specific).
            limit: Maximum records to return. ``None`` for all.

        Raises:
            ConnectorNotFoundError: *object_type* does not exist.
            ConnectorAuthError: session expired or insufficient permissions.
            ConnectorRateLimitError: API rate limit hit.
        """
        ...

    def create_record(
        self, object_type: str, data: dict[str, Any]
    ) -> str:
        """Create a single record; return its ID.

        Raises:
            ConnectorError: validation or API failure (never silent).
        """
        ...

    def update_record(
        self, object_type: str, record_id: str, data: dict[str, Any]
    ) -> bool:
        """Update a single record; return ``True`` on success.

        Raises on failure — never returns ``False`` silently (SU-1).
        """
        ...

    def upsert_records(
        self,
        object_type: str,
        records: pd.DataFrame,
        match_field: str,
    ) -> UpsertResult:
        """Bulk create-or-update from a DataFrame.

        Args:
            object_type: Target CRM object.
            records: DataFrame whose columns map to CRM fields.
            match_field: Column used to match existing records
                (e.g., ``"email"`` for contacts).

        Returns:
            :class:`UpsertResult` with per-record outcome.

        Raises:
            ConnectorAuthError: session expired.
            ConnectorRateLimitError: API rate limit hit.
        """
        ...

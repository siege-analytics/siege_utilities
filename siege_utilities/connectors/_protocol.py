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
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Protocol, runtime_checkable

import numpy as np
import pandas as pd

from siege_utilities.core._http import redact_secrets

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
    )

    def _secret_values(self) -> list[str]:
        values: list[str] = []
        for attr in self._SECRET_ATTRS:
            value = getattr(self, attr, None)
            if isinstance(value, str) and value:
                values.append(value)
        session = getattr(self, "_session", None)
        headers = getattr(session, "headers", None)
        if headers is not None:
            for header in ("Authorization", "X-Api-Key"):
                try:
                    raw = headers.get(header)
                except (AttributeError, TypeError):
                    # headers is not a real mapping (no/incompatible .get);
                    # diagnostics must stay robust, so skip rather than raise.
                    raw = None
                if isinstance(raw, str) and raw:
                    values.append(raw[7:] if raw[:7].lower() == "bearer " else raw)
        return values

    def _redact(self, text: object) -> str:
        """Key-based plus configured-value redaction for diagnostic text."""
        return redact_secrets(str(text), values=self._secret_values())


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

    def __repr__(self) -> str:
        created = [redact_secrets(str(value)) for value in self.created_ids]
        updated = [redact_secrets(str(value)) for value in self.updated_ids]
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

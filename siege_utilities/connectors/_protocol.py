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

    Recurse through dicts and lists, omitting missing dict children (None,
    NaN, NaT, pd.NA) at every level, including top-level fields. Missing list
    items become null, preserving their positions. Tuples become JSON lists.
    Dates use ISO 8601 and numpy scalars become native Python scalars.
    Scalar leaves that strict JSON cannot encode (such as Decimal or infinity)
    keep their string representation; containers are never stringified.

    Raises:
        ConnectorError: an unsupported container, invalid JSON object key,
            circular reference, or excessive nesting cannot be represented as JSON.
    """
    try:
        return _sanitize_value(row, path="$", ancestors=set())
    except RecursionError as exc:
        raise ConnectorError("Record nesting exceeds the JSON recursion limit") from exc


def _sanitize_value(value: Any, *, path: str, ancestors: set[int]) -> Any:
    if isinstance(value, (dict, list, tuple)):
        container_id = id(value)
        if container_id in ancestors:
            raise ConnectorError(f"Circular container reference at {path}")
        ancestors.add(container_id)
        try:
            if isinstance(value, dict):
                sanitized = {}
                for key, child in value.items():
                    # pd.isna on containers returns arrays, not a scalar flag.
                    if pd.api.types.is_scalar(child) and pd.isna(child):
                        continue
                    try:
                        json.dumps({key: None}, allow_nan=False)
                    except (TypeError, ValueError) as exc:
                        raise ConnectorError(
                            f"Invalid JSON object key at {path}: {key!r}"
                        ) from exc
                    sanitized[key] = _sanitize_value(
                        child, path=f"{path}[{key!r}]", ancestors=ancestors,
                    )
                return sanitized
            return [
                _sanitize_value(child, path=f"{path}[{index}]", ancestors=ancestors)
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


class ConnectorError(Exception):
    """Base for all connector errors."""


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


@dataclass
class UpsertError:
    """One failed record in a bulk upsert."""

    record_index: int
    message: str
    field: str | None = None
    code: str | None = None


@dataclass
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

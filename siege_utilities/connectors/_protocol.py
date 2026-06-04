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

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

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

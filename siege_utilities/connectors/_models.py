"""
Canonical CRM data models.

Vendor-neutral Pydantic models for the four universal CRM entities
(Contact, Account, Opportunity, Activity) plus a shared address type.
These models sit between raw connector output and downstream analytics —
connectors produce vendor-specific dicts, callers normalize into these
shapes for cross-CRM dedup and reporting.

Each model carries ``source_system`` / ``source_id`` to trace records
back to their origin. ``metadata`` provides an escape hatch for
vendor-specific fields that don't map to the canonical shape.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Self

import pandas as pd
from pydantic import BaseModel, ConfigDict, Field

__all__ = [
    "CRMAddress",
    "CRMContact",
    "CRMAccount",
    "CRMOpportunity",
    "CRMActivity",
]


class CRMAddress(BaseModel):
    """Mailing or billing address, shared across CRM entities."""

    model_config = ConfigDict(extra="forbid")

    street: str | None = None
    city: str | None = None
    state: str | None = None
    postal_code: str | None = None
    country: str | None = None


class CRMContact(BaseModel):
    """A person record from any CRM system."""

    model_config = ConfigDict(extra="forbid")

    id: str
    first_name: str | None = None
    last_name: str | None = None
    email: str | None = None
    phone: str | None = None
    title: str | None = None
    account_id: str | None = None
    address: CRMAddress | None = None
    source_system: str = Field(description="CRM vendor identifier (salesforce, hubspot, …)")
    source_id: str = Field(description="Record ID in the source CRM")
    metadata: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def to_dataframe(cls, records: list[Self]) -> pd.DataFrame:
        """Flatten a list of contacts into a DataFrame.

        Address fields are prefixed with ``address_``.
        """
        rows: list[dict[str, Any]] = []
        for r in records:
            d = r.model_dump(exclude={"address", "metadata"})
            if r.address:
                for k, v in r.address.model_dump().items():
                    d[f"address_{k}"] = v
            d.update(r.metadata)
            rows.append(d)
        return pd.DataFrame(rows)


class CRMAccount(BaseModel):
    """A company / organization record from any CRM system."""

    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    industry: str | None = None
    website: str | None = None
    revenue: Decimal | None = None
    employee_count: int | None = None
    address: CRMAddress | None = None
    source_system: str = Field(description="CRM vendor identifier")
    source_id: str = Field(description="Record ID in the source CRM")
    metadata: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def to_dataframe(cls, records: list[Self]) -> pd.DataFrame:
        """Flatten a list of accounts into a DataFrame."""
        rows: list[dict[str, Any]] = []
        for r in records:
            d = r.model_dump(exclude={"address", "metadata"})
            if r.revenue is not None:
                d["revenue"] = float(r.revenue)
            if r.address:
                for k, v in r.address.model_dump().items():
                    d[f"address_{k}"] = v
            d.update(r.metadata)
            rows.append(d)
        return pd.DataFrame(rows)


class CRMOpportunity(BaseModel):
    """A deal / opportunity record from any CRM system."""

    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    account_id: str | None = None
    stage: str | None = None
    amount: Decimal | None = None
    close_date: date | None = None
    probability: float | None = None
    owner_id: str | None = None
    source_system: str = Field(description="CRM vendor identifier")
    source_id: str = Field(description="Record ID in the source CRM")
    metadata: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def to_dataframe(cls, records: list[Self]) -> pd.DataFrame:
        """Flatten a list of opportunities into a DataFrame."""
        rows: list[dict[str, Any]] = []
        for r in records:
            d = r.model_dump(exclude={"metadata"})
            if d.get("amount") is not None:
                d["amount"] = float(d["amount"])
            if d.get("close_date") is not None:
                d["close_date"] = str(d["close_date"])
            d.update(r.metadata)
            rows.append(d)
        return pd.DataFrame(rows)


class CRMActivity(BaseModel):
    """An activity / task / event record from any CRM system."""

    model_config = ConfigDict(extra="forbid")

    id: str
    type: str
    subject: str | None = None
    description: str | None = None
    contact_id: str | None = None
    account_id: str | None = None
    timestamp: datetime | None = None
    due_date: date | None = None
    status: str | None = None
    source_system: str = Field(description="CRM vendor identifier")
    source_id: str = Field(description="Record ID in the source CRM")
    metadata: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def to_dataframe(cls, records: list[Self]) -> pd.DataFrame:
        """Flatten a list of activities into a DataFrame."""
        rows: list[dict[str, Any]] = []
        for r in records:
            d = r.model_dump(exclude={"metadata"})
            if d.get("timestamp") is not None:
                d["timestamp"] = str(d["timestamp"])
            if d.get("due_date") is not None:
                d["due_date"] = str(d["due_date"])
            d.update(r.metadata)
            rows.append(d)
        return pd.DataFrame(rows)

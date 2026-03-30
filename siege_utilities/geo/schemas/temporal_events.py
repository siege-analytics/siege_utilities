"""
Pydantic schemas for temporal event models (Phase B).

Mirrors Django models in geo/django/models/temporal_events.py.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field

from .base import TemporalGeographicFeatureSchema


SPECIAL_CAUSE_CHOICES = frozenset({
    "death", "resignation", "expulsion", "recall", "vacancy",
})

RACE_EVENT_TYPE_CHOICES = frozenset({
    "FILING_OPEN", "FILING_CLOSE", "PRIMARY", "PRIMARY_RUNOFF",
    "GENERAL", "GENERAL_RUNOFF", "RECOUNT", "CERTIFICATION",
    "INAUGURATION", "COURT_RULING",
})

EVENT_CATEGORY_CHOICES = frozenset({
    "NATURAL_DISASTER", "COURT_RULING", "REDISTRICTING", "LEGISLATION",
    "EXECUTIVE_ORDER", "PROTEST", "INFRASTRUCTURE", "PUBLIC_HEALTH", "OTHER",
})

RESULT_SOURCE_CHOICES = frozenset({"ap", "state_sos", "county", "manual"})


class RaceSchema(BaseModel):
    """Schema for Race."""

    seat_id: int | str
    congress_number: int = Field(ge=1, le=200)
    is_special: bool = False
    cause_of_special: str = Field(default="", max_length=20)

    model_config = {"from_attributes": True}


class SpatioTemporalEventSchema(TemporalGeographicFeatureSchema):
    """Schema for SpatioTemporalEvent."""

    event_start: datetime
    event_end: Optional[datetime] = None
    event_category: str = Field(max_length=30)
    description: str = ""

    model_config = {"from_attributes": True}


class RaceEventSchema(BaseModel):
    """Schema for RaceEvent."""

    race_id: int | str
    event_type: str = Field(max_length=20)
    event_date: date
    event_start: Optional[datetime] = None
    event_end: Optional[datetime] = None
    external_event_id: Optional[int | str] = None
    notes: str = ""

    model_config = {"from_attributes": True}


class ReturnSnapshotSchema(BaseModel):
    """Schema for ReturnSnapshot."""

    race_id: int | str
    timestamp: datetime
    source: str = Field(max_length=20)

    precincts_reporting: Optional[int] = None
    total_precincts: Optional[int] = None
    pct_reporting: Optional[float] = Field(default=None, ge=0.0, le=100.0)

    total_ballots_counted: Optional[int] = None
    ballots_outstanding: Optional[int] = None

    results: dict = Field(default_factory=dict)
    is_final: bool = False

    model_config = {"from_attributes": True}

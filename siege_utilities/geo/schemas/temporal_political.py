"""
Pydantic schemas for temporal political models (Phase A).

Mirrors Django models in geo/django/models/temporal_political.py.
"""

from __future__ import annotations

from datetime import date
from typing import Optional

from pydantic import BaseModel, Field


OFFICE_TYPE_CHOICES = frozenset({
    "PRESIDENT", "US_SENATE", "US_HOUSE", "GOVERNOR", "STATE_SENATE", "STATE_HOUSE",
})

PRIMARY_TYPE_CHOICES = frozenset({
    "open", "closed", "semi_closed", "semi_open", "top_two", "top_four", "blanket",
})


class CongressionalTermSchema(BaseModel):
    """Schema for CongressionalTerm."""

    congress_number: int = Field(ge=1, le=200)
    start_date: date
    end_date: date
    election_year: int
    is_presidential: bool = False
    senate_classes_up: list[int] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class SeatSchema(BaseModel):
    """Schema for Seat."""

    office: str = Field(max_length=20)
    state_fips: Optional[str] = Field(default=None, max_length=2)
    district_label: str = Field(default="", max_length=20)
    senate_class: Optional[int] = Field(default=None, ge=1, le=3)
    is_active: bool = True

    model_config = {"from_attributes": True}


class StateElectionCalendarSchema(BaseModel):
    """Schema for StateElectionCalendar."""

    state_fips: str = Field(max_length=2)
    congress_number: int = Field(ge=1, le=200)

    primary_date: Optional[date] = None
    primary_type: str = Field(default="", max_length=20)
    primary_runoff_date: Optional[date] = None

    general_date: Optional[date] = None
    general_runoff_date: Optional[date] = None

    registration_deadline: Optional[date] = None
    early_voting_start: Optional[date] = None
    early_voting_end: Optional[date] = None
    mail_ballot_request_deadline: Optional[date] = None
    mail_ballot_return_deadline: Optional[date] = None

    certification_deadline: Optional[date] = None

    model_config = {"from_attributes": True}

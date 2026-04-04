"""
Pydantic schemas for redistricting models.

Mirrors the Django models in geo/django/models/redistricting.py but without
Django dependency.  Geometry handled via GeoDataFrame/WKT in converters.
"""

from __future__ import annotations

from datetime import date
from typing import Optional

from pydantic import BaseModel, Field, model_validator

from .base import CensusTIGERSchema


CHAMBER_CHOICES = frozenset({"congress", "state_senate", "state_house"})
PLAN_TYPE_CHOICES = frozenset({
    "enacted", "proposed", "alternative", "court_ordered", "commission",
})
PLAN_SOURCE_CHOICES = frozenset({
    "rdh", "census", "court", "legislature", "commission",
})
DATASET_CHOICES = frozenset({"acs5", "acs1", "dec", "dec_pl"})
OFFICE_CHOICES = frozenset({
    "president", "senate", "house", "governor",
    "state_senate", "state_house", "attorney_general", "secretary_of_state",
})


class RedistrictingPlanSchema(BaseModel):
    """Schema for a redistricting plan with temporal resolution.

    Supports court-ordered mid-cycle redistricting: multiple plans can exist
    for the same state/chamber/cycle with different effective date ranges.
    Use for_date(state_fips, chamber, date) on the Django model to find
    which plan was active on a given date.
    """

    state_fips: str = Field(max_length=2)
    chamber: str = Field(max_length=20)
    cycle_year: int = Field(ge=1960, le=2040)
    plan_name: str = Field(max_length=255)
    plan_type: str = Field(default="enacted", max_length=20)
    source: str = Field(default="rdh", max_length=20)
    source_url: str = ""
    num_districts: int
    enacted_date: Optional[date] = None
    effective_from: Optional[date] = None
    effective_to: Optional[date] = None
    superseded_by_id: Optional[int] = None
    court_case: str = ""
    data_source: str = Field(default="rdh", max_length=100)

    model_config = {"from_attributes": True}

    @model_validator(mode="after")
    def validate_effective_range(self):
        """Effective range must be valid if both dates are set."""
        if self.effective_from and self.effective_to:
            if self.effective_to < self.effective_from:
                raise ValueError(
                    f"effective_to ({self.effective_to}) cannot be before "
                    f"effective_from ({self.effective_from})"
                )
        return self


class PlanDistrictSchema(CensusTIGERSchema):
    """Schema for a single district within a redistricting plan."""

    plan_id: int | str | None = None
    district_number: str = Field(max_length=10)

    # Compactness scores
    polsby_popper: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    reock: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    convex_hull_ratio: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    schwartzberg: Optional[float] = Field(default=None, ge=0.0, le=1.0)

    # Denormalized population
    total_population: Optional[int] = None
    vap: Optional[int] = None
    cvap: Optional[int] = None
    deviation_pct: Optional[float] = None


class DistrictDemographicsSchema(BaseModel):
    """Schema for demographic profile of a plan district."""

    district_id: int | str
    dataset: str = Field(max_length=10)
    year: int = Field(ge=1990, le=2050)

    # Race/ethnicity
    pop_white: Optional[int] = None
    pop_black: Optional[int] = None
    pop_hispanic: Optional[int] = None
    pop_asian: Optional[int] = None
    pop_native: Optional[int] = None
    pop_other: Optional[int] = None
    pop_two_or_more: Optional[int] = None

    # Economic
    median_household_income: Optional[int] = None
    poverty_rate: Optional[float] = Field(default=None, ge=0.0, le=100.0)

    # Full variable set
    values: dict[str, float | int | str] = Field(default_factory=dict)
    moe_values: dict[str, float | int | str] = Field(default_factory=dict)

    model_config = {"from_attributes": True}

    @model_validator(mode="after")
    def auto_populate_race_from_values(self):
        """Auto-populate race fields from Census variable codes if present."""
        _map = {
            "B02001_002E": "pop_white",
            "B02001_003E": "pop_black",
            "B03003_003E": "pop_hispanic",
            "B02001_005E": "pop_asian",
            "B02001_004E": "pop_native",
            "B02001_007E": "pop_other",
            "B02001_008E": "pop_two_or_more",
            "B19013_001E": "median_household_income",
        }
        if self.values:
            for code, attr in _map.items():
                if code in self.values and getattr(self, attr) is None:
                    try:
                        setattr(self, attr, int(self.values[code]))
                    except (ValueError, TypeError):
                        pass
        return self


class PrecinctElectionResultSchema(BaseModel):
    """Schema for precinct-level election results."""

    state_fips: str = Field(max_length=2)
    precinct_id: str = Field(max_length=60)
    precinct_name: str = Field(default="", max_length=255)
    election_year: int = Field(ge=1900, le=2050)
    office: str = Field(max_length=30)
    party: str = Field(max_length=50)
    candidate_name: str = Field(default="", max_length=255)
    votes: int
    total_votes: Optional[int] = None
    vote_share: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    data_source: str = Field(default="rdh", max_length=100)

    model_config = {"from_attributes": True}

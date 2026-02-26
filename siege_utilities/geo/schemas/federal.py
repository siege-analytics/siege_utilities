"""Pydantic schemas for federal boundary models."""

from typing import Optional

from pydantic import Field

from .base import TemporalBoundarySchema


class NLRBRegionSchema(TemporalBoundarySchema):
    region_number: int
    region_office: str = Field(default="", max_length=100)
    states_covered: list[str] = Field(default_factory=list)


class FederalJudicialDistrictSchema(TemporalBoundarySchema):
    district_code: str = Field(max_length=10)
    district_name: str = Field(max_length=100)
    circuit_number: Optional[int] = None
    state_fips: str = Field(default="", max_length=2)

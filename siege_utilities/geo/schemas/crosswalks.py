"""Pydantic schema for the TemporalCrosswalk model."""

from typing import Optional
from decimal import Decimal

from pydantic import BaseModel, Field


class TemporalCrosswalkSchema(BaseModel):
    source_boundary_id: str = Field(max_length=60)
    source_vintage_year: int = Field(ge=1790, le=2100)
    source_type: str = Field(default="", max_length=50)
    target_boundary_id: str = Field(max_length=60)
    target_vintage_year: int = Field(ge=1790, le=2100)
    target_type: str = Field(default="", max_length=50)
    relationship: str = Field(max_length=20)
    weight: Decimal = Field(ge=0, le=1, decimal_places=8)
    weight_type: str = Field(default="population", max_length=20)
    state_fips: str = Field(default="", max_length=2)
    source_population: Optional[int] = None
    target_population: Optional[int] = None
    allocated_population: Optional[int] = None
    area_sq_meters: Optional[int] = None
    data_source: str = Field(default="", max_length=100)

    model_config = {"from_attributes": True}

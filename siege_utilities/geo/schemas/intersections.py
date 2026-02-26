"""Pydantic schemas for intersection models."""

from typing import Optional
from decimal import Decimal

from pydantic import BaseModel, Field


class BoundaryIntersectionSchema(BaseModel):
    source_type: str = Field(max_length=50)
    source_boundary_id: str = Field(max_length=60)
    target_type: str = Field(max_length=50)
    target_boundary_id: str = Field(max_length=60)
    vintage_year: int = Field(ge=1790, le=2100)
    intersection_area: Optional[int] = None
    pct_of_source: Optional[Decimal] = None
    pct_of_target: Optional[Decimal] = None
    is_dominant: bool = False

    model_config = {"from_attributes": True}


class CountyCDIntersectionSchema(BaseModel):
    county_id: int
    congressional_district_id: int
    vintage_year: int
    intersection_area: Optional[int] = None
    pct_of_county: Optional[Decimal] = None
    pct_of_cd: Optional[Decimal] = None
    is_dominant: bool = False

    model_config = {"from_attributes": True}


class VTDCDIntersectionSchema(BaseModel):
    vtd_id: int
    congressional_district_id: int
    vintage_year: int
    intersection_area: Optional[int] = None
    pct_of_vtd: Optional[Decimal] = None
    pct_of_cd: Optional[Decimal] = None
    is_dominant: bool = False

    model_config = {"from_attributes": True}


class TractCDIntersectionSchema(BaseModel):
    tract_id: int
    congressional_district_id: int
    vintage_year: int
    intersection_area: Optional[int] = None
    pct_of_tract: Optional[Decimal] = None
    pct_of_cd: Optional[Decimal] = None
    is_dominant: bool = False

    model_config = {"from_attributes": True}

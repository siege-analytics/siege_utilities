"""
Base Pydantic schemas mirroring the abstract model hierarchy.

Geometry is NOT included — it's handled via GeoDataFrame/WKT in converters.
"""

from datetime import date
from typing import Optional

from pydantic import BaseModel, Field, model_validator


class TemporalGeographicFeatureSchema(BaseModel):
    """Schema for TemporalGeographicFeature fields."""

    feature_id: str = Field(default="", max_length=60)
    name: str = Field(max_length=255)
    vintage_year: int = Field(ge=1790, le=2100)
    valid_from: Optional[date] = None
    valid_to: Optional[date] = None
    source: str = Field(default="", max_length=50)

    model_config = {"from_attributes": True}


class TemporalBoundarySchema(TemporalGeographicFeatureSchema):
    """Schema for TemporalBoundary fields (no geometry)."""

    boundary_id: str = Field(default="", max_length=60)
    area_land: Optional[int] = None
    area_water: Optional[int] = None
    # internal_point stored as WKT string when needed
    internal_point_wkt: Optional[str] = None

    @model_validator(mode="after")
    def sync_ids(self):
        if self.feature_id and not self.boundary_id:
            self.boundary_id = self.feature_id
        return self


class CensusTIGERSchema(TemporalBoundarySchema):
    """Schema for CensusTIGERBoundary fields."""

    geoid: str = Field(max_length=20)
    state_fips: str = Field(default="", max_length=2)
    lsad: str = Field(default="", max_length=2)
    mtfcc: str = Field(default="", max_length=5)
    funcstat: str = Field(default="", max_length=1)

    @model_validator(mode="after")
    def sync_from_geoid(self):
        if self.geoid:
            if not self.feature_id:
                self.feature_id = self.geoid
            if not self.boundary_id:
                self.boundary_id = self.geoid
        return self

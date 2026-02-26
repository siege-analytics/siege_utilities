"""Pydantic schemas for NCES education models."""

from typing import Optional

from pydantic import Field

from .base import CensusTIGERSchema, TemporalBoundarySchema, TemporalGeographicFeatureSchema


class SchoolDistrictBaseSchema(CensusTIGERSchema):
    lea_id: str = Field(max_length=7)
    district_type: str = Field(default="", max_length=2)
    locale_code: str = Field(default="", max_length=2)
    locale_category: str = Field(default="", max_length=20)
    locale_subcategory: str = Field(default="", max_length=20)


class SchoolDistrictElementarySchema(SchoolDistrictBaseSchema):
    pass


class SchoolDistrictSecondarySchema(SchoolDistrictBaseSchema):
    pass


class SchoolDistrictUnifiedSchema(SchoolDistrictBaseSchema):
    pass


class NCESLocaleBoundarySchema(TemporalBoundarySchema):
    """Schema for NCESLocaleBoundary."""

    locale_code: int = Field(ge=11, le=43)
    locale_category: str = Field(max_length=20)
    locale_subcategory: str = Field(default="", max_length=30)
    nces_year: int = Field(ge=2000, le=2100)


class SchoolLocationSchema(TemporalGeographicFeatureSchema):
    """Schema for SchoolLocation (point feature, no geometry in schema)."""

    ncessch: str = Field(max_length=12)
    school_name: str = Field(max_length=255)
    lea_id: str = Field(max_length=7)
    locale_code: Optional[int] = Field(default=None, ge=11, le=43)
    locale_category: str = Field(default="", max_length=20)
    locale_subcategory: str = Field(default="", max_length=30)

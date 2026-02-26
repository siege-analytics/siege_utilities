"""Pydantic schemas for NCES school district models."""

from pydantic import Field

from .base import CensusTIGERSchema


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

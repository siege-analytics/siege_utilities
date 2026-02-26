"""Pydantic schemas for GADM models."""

from typing import Optional

from pydantic import Field

from .base import TemporalBoundarySchema


class GADMBoundarySchema(TemporalBoundarySchema):
    gid: str = Field(max_length=50)


class GADMCountrySchema(GADMBoundarySchema):
    iso3: str = Field(max_length=3)


class GADMAdmin1Schema(GADMBoundarySchema):
    gid_0_string: str = Field(default="", max_length=50)
    type_1: str = Field(default="", max_length=50)
    engtype_1: str = Field(default="", max_length=50)


class GADMAdmin2Schema(GADMBoundarySchema):
    gid_1_string: str = Field(default="", max_length=50)
    type_2: str = Field(default="", max_length=50)
    engtype_2: str = Field(default="", max_length=50)


class GADMAdmin3Schema(GADMBoundarySchema):
    gid_2_string: str = Field(default="", max_length=50)
    type_3: str = Field(default="", max_length=50)
    engtype_3: str = Field(default="", max_length=50)


class GADMAdmin4Schema(GADMBoundarySchema):
    gid_3_string: str = Field(default="", max_length=50)
    type_4: str = Field(default="", max_length=50)
    engtype_4: str = Field(default="", max_length=50)


class GADMAdmin5Schema(GADMBoundarySchema):
    gid_4_string: str = Field(default="", max_length=50)
    type_5: str = Field(default="", max_length=50)
    engtype_5: str = Field(default="", max_length=50)

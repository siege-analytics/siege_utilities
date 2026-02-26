"""Pydantic schemas for political Census models."""

from typing import Optional

from pydantic import Field

from .base import CensusTIGERSchema


class StateLegislativeUpperSchema(CensusTIGERSchema):
    district_number: str = Field(max_length=3)


class StateLegislativeLowerSchema(CensusTIGERSchema):
    district_number: str = Field(max_length=3)


class VTDSchema(CensusTIGERSchema):
    county_fips: str = Field(max_length=3)
    vtd_code: str = Field(max_length=6)
    precinct_name: str = Field(default="", max_length=255)
    precinct_code: str = Field(default="", max_length=20)
    registered_voters: Optional[int] = None
    data_source: str = Field(default="", max_length=100)


class PrecinctSchema(CensusTIGERSchema):
    county_fips: str = Field(max_length=3)
    precinct_code: str = Field(max_length=20)
    precinct_name: str = Field(default="", max_length=255)
    precinct_source: str = Field(default="", max_length=100)

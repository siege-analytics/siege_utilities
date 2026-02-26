"""Pydantic schemas for the 8 concrete Census TIGER boundary models."""

from typing import Optional

from pydantic import Field

from .base import CensusTIGERSchema


class StateSchema(CensusTIGERSchema):
    abbreviation: str = Field(max_length=2)
    region: str = Field(default="", max_length=20)
    division: str = Field(default="", max_length=30)


class CountySchema(CensusTIGERSchema):
    county_fips: str = Field(max_length=3)
    county_name: str = Field(default="", max_length=100)


class TractSchema(CensusTIGERSchema):
    county_fips: str = Field(max_length=3)
    tract_code: str = Field(max_length=6)


class BlockGroupSchema(CensusTIGERSchema):
    county_fips: str = Field(max_length=3)
    tract_code: str = Field(max_length=6)
    block_group: str = Field(max_length=1)


class BlockSchema(CensusTIGERSchema):
    county_fips: str = Field(max_length=3)
    tract_code: str = Field(max_length=6)
    block_code: str = Field(max_length=4)


class PlaceSchema(CensusTIGERSchema):
    place_fips: str = Field(max_length=5)
    place_type: str = Field(default="", max_length=2)


class ZCTASchema(CensusTIGERSchema):
    zcta5: str = Field(max_length=5)


class CongressionalDistrictSchema(CensusTIGERSchema):
    district_number: str = Field(max_length=2)
    congress_number: Optional[int] = None
    session: str = Field(default="", max_length=4)

"""
Tests for the Pydantic schema layer (siege_utilities.geo.schemas).

Tests schema validation, field constraints, inheritance, and round-trip
conversion via converters.
"""

from decimal import Decimal

import pytest
from pydantic import ValidationError


class TestBaseSchemas:
    def test_temporal_geographic_feature_schema(self):
        from siege_utilities.geo.schemas.base import TemporalGeographicFeatureSchema

        schema = TemporalGeographicFeatureSchema(
            feature_id="TEST-001",
            name="Test Feature",
            vintage_year=2020,
        )
        assert schema.feature_id == "TEST-001"
        assert schema.vintage_year == 2020
        assert schema.valid_from is None
        assert schema.source == ""

    def test_temporal_boundary_schema(self):
        from siege_utilities.geo.schemas.base import TemporalBoundarySchema

        schema = TemporalBoundarySchema(
            feature_id="TEST-001",
            name="Test Boundary",
            vintage_year=2020,
            area_land=1234567,
            area_water=98765,
        )
        assert schema.area_land == 1234567
        assert schema.boundary_id == "TEST-001"  # auto-synced

    def test_census_tiger_schema(self):
        from siege_utilities.geo.schemas.base import CensusTIGERSchema

        schema = CensusTIGERSchema(
            geoid="06",
            name="California",
            vintage_year=2020,
            state_fips="06",
        )
        assert schema.geoid == "06"
        assert schema.feature_id == "06"  # synced from geoid
        assert schema.source == ""

    def test_vintage_year_validation(self):
        from siege_utilities.geo.schemas.base import TemporalGeographicFeatureSchema

        with pytest.raises(ValidationError):
            TemporalGeographicFeatureSchema(
                feature_id="X", name="X", vintage_year=1700
            )

        with pytest.raises(ValidationError):
            TemporalGeographicFeatureSchema(
                feature_id="X", name="X", vintage_year=2200
            )


class TestBoundarySchemas:
    def test_state_schema(self):
        from siege_utilities.geo.schemas import StateSchema

        schema = StateSchema(
            geoid="06",
            name="California",
            vintage_year=2020,
            state_fips="06",
            abbreviation="CA",
            region="West",
            division="Pacific",
        )
        assert schema.abbreviation == "CA"
        assert schema.region == "West"

    def test_county_schema(self):
        from siege_utilities.geo.schemas import CountySchema

        schema = CountySchema(
            geoid="06037",
            name="Los Angeles",
            vintage_year=2020,
            state_fips="06",
            county_fips="037",
            county_name="Los Angeles",
        )
        assert schema.county_fips == "037"

    def test_tract_schema(self):
        from siege_utilities.geo.schemas import TractSchema

        schema = TractSchema(
            geoid="06037101100",
            name="Tract 1011.00",
            vintage_year=2020,
            state_fips="06",
            county_fips="037",
            tract_code="101100",
        )
        assert schema.tract_code == "101100"

    def test_cd_schema(self):
        from siege_utilities.geo.schemas import CongressionalDistrictSchema

        schema = CongressionalDistrictSchema(
            geoid="0614",
            name="CA-14",
            vintage_year=2020,
            state_fips="06",
            district_number="14",
            congress_number=118,
        )
        assert schema.congress_number == 118


class TestPoliticalSchemas:
    def test_vtd_schema(self):
        from siege_utilities.geo.schemas import VTDSchema

        schema = VTDSchema(
            geoid="06037001",
            name="VTD 001",
            vintage_year=2020,
            state_fips="06",
            county_fips="037",
            vtd_code="001",
            registered_voters=5432,
            data_source="CA SOS 2024",
        )
        assert schema.registered_voters == 5432
        assert schema.data_source == "CA SOS 2024"


class TestGADMSchemas:
    def test_gadm_country_schema(self):
        from siege_utilities.geo.schemas import GADMCountrySchema

        schema = GADMCountrySchema(
            feature_id="USA",
            name="United States",
            vintage_year=2024,
            gid="USA",
            iso3="USA",
        )
        assert schema.iso3 == "USA"

    def test_gadm_admin1_schema(self):
        from siege_utilities.geo.schemas import GADMAdmin1Schema

        schema = GADMAdmin1Schema(
            feature_id="USA.5_1",
            name="California",
            vintage_year=2024,
            gid="USA.5_1",
            gid_0_string="USA",
            type_1="State",
            engtype_1="State",
        )
        assert schema.gid_0_string == "USA"


class TestEducationSchemas:
    def test_school_district_unified_schema(self):
        from siege_utilities.geo.schemas import SchoolDistrictUnifiedSchema

        schema = SchoolDistrictUnifiedSchema(
            geoid="0600001",
            name="Los Angeles USD",
            vintage_year=2020,
            state_fips="06",
            lea_id="0600001",
            district_type="00",
            locale_code="11",
            locale_category="City",
            locale_subcategory="Large",
        )
        assert schema.locale_code == "11"
        assert schema.locale_category == "City"


class TestFederalSchemas:
    def test_nlrb_region_schema(self):
        from siege_utilities.geo.schemas import NLRBRegionSchema

        schema = NLRBRegionSchema(
            feature_id="NLRB-01",
            name="Region 1",
            vintage_year=2024,
            region_number=1,
            region_office="Boston",
            states_covered=["09", "23", "25", "33", "44", "50"],
        )
        assert schema.region_number == 1
        assert len(schema.states_covered) == 6

    def test_fjd_schema(self):
        from siege_utilities.geo.schemas import FederalJudicialDistrictSchema

        schema = FederalJudicialDistrictSchema(
            feature_id="CACD",
            name="Central District of California",
            vintage_year=2024,
            district_code="CACD",
            district_name="Central District of California",
            circuit_number=9,
            state_fips="06",
        )
        assert schema.circuit_number == 9


class TestCrosswalkSchema:
    def test_temporal_crosswalk_schema(self):
        from siege_utilities.geo.schemas import TemporalCrosswalkSchema

        schema = TemporalCrosswalkSchema(
            source_boundary_id="06037100100",
            source_vintage_year=2010,
            source_type="tract",
            target_boundary_id="06037100101",
            target_vintage_year=2020,
            target_type="tract",
            relationship="SPLIT",
            weight=Decimal("0.60000000"),
        )
        assert schema.relationship == "SPLIT"
        assert schema.weight == Decimal("0.60000000")


class TestIntersectionSchemas:
    def test_generic_intersection(self):
        from siege_utilities.geo.schemas import BoundaryIntersectionSchema

        schema = BoundaryIntersectionSchema(
            source_type="county",
            source_boundary_id="06037",
            target_type="cd",
            target_boundary_id="0614",
            vintage_year=2020,
            pct_of_source=Decimal("0.450000"),
            pct_of_target=Decimal("0.720000"),
            is_dominant=True,
        )
        assert schema.is_dominant is True


class TestSchemaConverters:
    def test_gdf_to_schemas(self):
        import geopandas as gpd
        from shapely.geometry import box

        from siege_utilities.geo.schemas import StateSchema
        from siege_utilities.geo.schemas.converters import gdf_to_schemas

        gdf = gpd.GeoDataFrame(
            {
                "geoid": ["06", "48"],
                "name": ["California", "Texas"],
                "vintage_year": [2020, 2020],
                "state_fips": ["06", "48"],
                "abbreviation": ["CA", "TX"],
                "feature_id": ["06", "48"],
                "geometry": [box(-124, 32, -114, 42), box(-106, 25, -93, 36)],
            },
            crs="EPSG:4326",
        )

        schemas = gdf_to_schemas(gdf, StateSchema)
        assert len(schemas) == 2
        assert schemas[0].abbreviation == "CA"
        assert schemas[1].name == "Texas"

    def test_gdf_to_schemas_with_column_map(self):
        import geopandas as gpd
        from shapely.geometry import box

        from siege_utilities.geo.schemas import StateSchema
        from siege_utilities.geo.schemas.converters import gdf_to_schemas

        gdf = gpd.GeoDataFrame(
            {
                "GEOID": ["06"],
                "NAME": ["California"],
                "vintage_year": [2020],
                "STATEFP": ["06"],
                "STUSPS": ["CA"],
                "feature_id": ["06"],
                "geometry": [box(-124, 32, -114, 42)],
            },
            crs="EPSG:4326",
        )

        schemas = gdf_to_schemas(
            gdf,
            StateSchema,
            column_map={
                "GEOID": "geoid",
                "NAME": "name",
                "STATEFP": "state_fips",
                "STUSPS": "abbreviation",
            },
        )
        assert len(schemas) == 1
        assert schemas[0].geoid == "06"

    def test_schema_round_trip(self):
        from siege_utilities.geo.schemas import CountySchema

        data = {
            "geoid": "06037",
            "name": "Los Angeles",
            "vintage_year": 2020,
            "state_fips": "06",
            "county_fips": "037",
            "county_name": "Los Angeles",
            "feature_id": "06037",
        }
        schema = CountySchema(**data)
        dumped = schema.model_dump()
        schema2 = CountySchema(**dumped)
        assert schema.geoid == schema2.geoid
        assert schema.county_fips == schema2.county_fips

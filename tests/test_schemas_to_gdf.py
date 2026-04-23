"""Tests for schemas_to_gdf converter."""

import pytest

import geopandas as gpd
from shapely.geometry import box

from siege_utilities.geo.schemas import StateSchema, CountySchema, schemas_to_gdf
from siege_utilities.geo.schemas.converters import gdf_to_schemas


class TestSchemasToGdf:
    def test_basic_conversion(self):
        schemas = [
            StateSchema(
                geoid="06", name="California", vintage_year=2020,
                state_fips="06", abbreviation="CA",
            ),
            StateSchema(
                geoid="48", name="Texas", vintage_year=2020,
                state_fips="48", abbreviation="TX",
            ),
        ]
        gdf = schemas_to_gdf(schemas)
        assert isinstance(gdf, gpd.GeoDataFrame)
        assert len(gdf) == 2
        assert "geoid" in gdf.columns
        assert gdf.iloc[0]["abbreviation"] == "CA"

    def test_with_geometry_wkts(self):
        schemas = [
            CountySchema(
                geoid="06037", name="Los Angeles", vintage_year=2020,
                state_fips="06", county_fips="037", county_name="Los Angeles",
            ),
        ]
        wkts = [box(-118.7, 33.7, -117.6, 34.8).wkt]
        gdf = schemas_to_gdf(schemas, geometry_wkts=wkts, srid=4326)
        assert gdf.crs is not None
        assert gdf.crs.to_epsg() == 4326
        assert gdf.geometry.iloc[0] is not None

    def test_empty_input(self):
        gdf = schemas_to_gdf([])
        assert isinstance(gdf, gpd.GeoDataFrame)
        assert len(gdf) == 0

    def test_round_trip_gdf_schema_gdf(self):
        """GDF -> schemas -> GDF preserves data."""
        original = gpd.GeoDataFrame(
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
        # GDF -> schemas
        schemas = gdf_to_schemas(original, StateSchema)
        assert len(schemas) == 2

        # schemas -> GDF (without geometry since gdf_to_schemas drops it)
        result = schemas_to_gdf(schemas)
        assert len(result) == 2
        assert result.iloc[0]["abbreviation"] == "CA"
        assert result.iloc[1]["name"] == "Texas"

    def test_none_geometry_in_list(self):
        schemas = [
            StateSchema(
                geoid="06", name="California", vintage_year=2020,
                state_fips="06", abbreviation="CA",
            ),
        ]
        gdf = schemas_to_gdf(schemas, geometry_wkts=[None])
        assert len(gdf) == 1

    def test_mismatched_geometry_wkts_length_raises(self):
        schemas = [
            StateSchema(
                geoid="06", name="California", vintage_year=2020,
                state_fips="06", abbreviation="CA",
            ),
        ]
        with pytest.raises(ValueError, match="geometry_wkts length"):
            schemas_to_gdf(schemas, geometry_wkts=[box(0, 0, 1, 1).wkt, box(2, 2, 3, 3).wkt])

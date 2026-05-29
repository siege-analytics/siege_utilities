"""Tests for geocode_results_to_dataframe() helper.

Verifies the conversion from list[CensusGeocodeResult] to pandas DataFrame
with correct columns, types, and edge-case handling.
"""

import pytest
import pandas as pd

from siege_utilities.geo.providers.census_geocoder import (
    CensusGeocodeResult,
    geocode_results_to_dataframe,
)

EXPECTED_COLUMNS = [
    "input_id",
    "input_address",
    "matched",
    "match_type",
    "matched_address",
    "latitude",
    "longitude",
    "state_geoid",
    "county_geoid",
    "tract_geoid",
    "block_geoid",
    "block_group_geoid",
    "state_fips",
    "county_fips",
    "tract",
    "block",
    "side",
    "tiger_line_id",
]


class TestGeocodeResultsToDataframe:
    """Tests for geocode_results_to_dataframe()."""

    def test_empty_list_returns_empty_dataframe_with_columns(self):
        df = geocode_results_to_dataframe([])
        assert isinstance(df, pd.DataFrame)
        assert list(df.columns) == EXPECTED_COLUMNS
        assert len(df) == 0

    def test_single_matched_result(self):
        result = CensusGeocodeResult(
            matched=True,
            input_id="1",
            input_address="123 Main St, Austin, TX 78741",
            matched_address="123 MAIN ST, AUSTIN, TX, 78741",
            lat=30.25,
            lon=-97.75,
            state_fips="48",
            county_fips="453",
            tract="001234",
            block="1001",
            match_type="Exact",
            side="L",
            tiger_line_id="12345",
        )
        df = geocode_results_to_dataframe([result])
        assert len(df) == 1
        row = df.iloc[0]
        assert row["matched"] == True
        assert row["latitude"] == 30.25
        assert row["longitude"] == -97.75
        assert row["tract_geoid"] == "48453001234"
        assert row["block_geoid"] == "484530012341001"
        assert row["county_geoid"] == "48453"
        assert row["state_geoid"] == "48"
        assert row["block_group_geoid"] == "484530012341"
        assert row["input_id"] == "1"

    def test_single_unmatched_result(self):
        result = CensusGeocodeResult(
            input_id="5",
            input_address="742 Evergreen Terr, Springfield, XX 00000",
        )
        df = geocode_results_to_dataframe([result])
        assert len(df) == 1
        row = df.iloc[0]
        assert row["matched"] == False
        assert pd.isna(row["latitude"])
        assert pd.isna(row["longitude"])
        assert row["tract_geoid"] == ""
        assert row["block_geoid"] == ""

    def test_mixed_matched_and_unmatched(self):
        matched = CensusGeocodeResult(
            matched=True,
            input_id="1",
            input_address="123 Main St",
            lat=30.0,
            lon=-97.0,
            state_fips="48",
            county_fips="453",
            tract="001234",
            block="1001",
        )
        unmatched = CensusGeocodeResult(
            input_id="2",
            input_address="Bad Address",
        )
        df = geocode_results_to_dataframe([matched, unmatched])
        assert len(df) == 2
        assert df.iloc[0]["matched"] == True
        assert df.iloc[1]["matched"] == False
        assert df.iloc[0]["tract_geoid"] == "48453001234"
        assert df.iloc[1]["tract_geoid"] == ""

    def test_column_order_matches_expected(self):
        df = geocode_results_to_dataframe([CensusGeocodeResult()])
        assert list(df.columns) == EXPECTED_COLUMNS

    def test_raises_type_error_for_non_list(self):
        with pytest.raises(TypeError, match="results must be a list"):
            geocode_results_to_dataframe("not a list")

    def test_lat_lon_renamed_to_latitude_longitude(self):
        result = CensusGeocodeResult(matched=True, lat=40.0, lon=-74.0)
        df = geocode_results_to_dataframe([result])
        assert "latitude" in df.columns
        assert "longitude" in df.columns
        assert "lat" not in df.columns
        assert "lon" not in df.columns

    def test_importable_from_geo_init(self):
        """Verify the function is exported via geo/__init__.py."""
        from siege_utilities.geo import geocode_results_to_dataframe as fn
        assert callable(fn)

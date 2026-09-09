"""Pandas geocode validation helpers."""

import pandas as pd

from siege_utilities.geo.geocoding import _get_crs_bounds
from siege_utilities.geo.geocoding import mark_valid_geocode_data_pandas
from siege_utilities.geo.geocoding import validate_geocode_data_pandas


def test_validate_geocode_data_pandas_coerces_numeric_strings():
    df = pd.DataFrame(
        {
            "id": ["valid-string", "bad-lat", "missing-lat", "out-of-bounds"],
            "lat": ["40.0", "bad", None, "999"],
            "lon": ["-89.0", "-88.0", "0", "1"],
        }
    )

    result = validate_geocode_data_pandas(df, "lat", "lon")

    assert result["id"].tolist() == ["valid-string"]
    assert result.loc[0, "lat"] == "40.0"


def test_mark_valid_geocode_data_pandas_coerces_numeric_strings():
    df = pd.DataFrame(
        {
            "id": ["valid-string", "bad-lat", "missing-lat", "out-of-bounds"],
            "lat": ["40.0", "bad", None, "999"],
            "lon": ["-89.0", "-88.0", "0", "1"],
        }
    )

    result = mark_valid_geocode_data_pandas(df, "lat", "lon")

    assert result["is_valid"].tolist() == [True, False, False, False]


def test_get_crs_bounds_falls_back_for_invalid_crs():
    assert _get_crs_bounds("not-a-real-crs") == (-90.0, 90.0, -180.0, 180.0)

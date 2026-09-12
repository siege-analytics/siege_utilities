"""Pandas geocode validation contract tests."""

import pandas as pd

from siege_utilities.geo.geocoding import (
    mark_valid_geocode_data_pandas,
    validate_geocode_data_pandas,
)


def test_validate_geocode_data_pandas_accepts_numeric_strings_without_mutating():
    df = pd.DataFrame(
        {
            "lat": ["40", "bad", None, "91", "45.5"],
            "lon": ["-89", "-80", "-80", "0", "181"],
            "name": ["valid", "bad-lat", "missing-lat", "bad-range-lat", "bad-range-lon"],
        }
    )
    before = df.copy(deep=True)

    result = validate_geocode_data_pandas(df, "lat", "lon")

    assert result["name"].tolist() == ["valid"]
    assert result.loc[0, "lat"] == "40"
    pd.testing.assert_frame_equal(df, before)


def test_mark_valid_geocode_data_pandas_uses_boolean_mask_and_copy():
    df = pd.DataFrame(
        {
            "lat": ["40", "bad", None, "91", "45.5"],
            "lon": ["-89", "-80", "-80", "0", "181"],
        }
    )

    result = mark_valid_geocode_data_pandas(df, "lat", "lon", output_col="valid")

    assert result["valid"].tolist() == [True, False, False, False, False]
    assert "valid" not in df.columns
    assert result.loc[0, "lat"] == "40"

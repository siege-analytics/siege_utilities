"""Regression coverage for GEOID alphabets, padding, and float columns (#1486)."""

import pandas as pd
import pytest

from siege_utilities.geo.geoid_utils import (
    GEOIDValidator,
    can_normalize_geoid,
    normalize_geoid,
    normalize_geoid_column,
    prepare_geoid_for_join,
    validate_geoid,
)


DISTRICT_GEOIDS = [
    ("06ZZZ", "sldu"),
    ("06ZZZ", "sldl"),
    *[(f"0200{letter}", "sldu") for letter in "ABCDEFGHIJKLMNOPQRST"],
    ("06ZZ", "cd"),
]


@pytest.mark.parametrize("geoid,level", DISTRICT_GEOIDS)
def test_district_validation_accepts_census_alphabet(geoid, level):
    assert validate_geoid(geoid, level) is True
    assert validate_geoid(geoid[1:], level, strict=False) is True
    assert can_normalize_geoid(geoid, level) is True
    assert normalize_geoid(geoid[1:], level) == geoid


@pytest.mark.parametrize("geoid,level", DISTRICT_GEOIDS)
def test_django_validator_accepts_census_district_alphabet(geoid, level):
    assert GEOIDValidator(level)(geoid) is None


@pytest.mark.parametrize(
    "geoid,level",
    [
        ("CA037", "county"),
        ("-6037", "county"),
        ("A6", "state"),
        ("0603710110A", "tract"),
        ("06037101100A", "block_group"),
        ("06037101100100A", "block"),
        ("060000A", "place"),
        ("9021A", "zcta"),
        ("CAZZZ", "sldu"),
        ("06zzZ", "sldl"),
        ("06-ZZ", "sldu"),
        ("CAZZ", "cd"),
        ("06zz", "cd"),
    ],
)
def test_normalization_rejects_wrong_alphabet(geoid, level):
    with pytest.raises(ValueError):
        normalize_geoid(geoid, level)


@pytest.mark.parametrize(
    "value,level,expected",
    [(6037.0, "county", "06037"), (10010201001.0, "block_group", "010010201001")],
)
def test_integral_float_restores_one_leading_zero(value, level, expected):
    assert normalize_geoid(value, level) == expected
    assert can_normalize_geoid(value, level) is True


@pytest.mark.parametrize("value", ["1001020100", 1001020100, 1001020100.0])
def test_ten_digit_tract_cannot_become_a_block_group(value):
    with pytest.raises(ValueError):
        normalize_geoid(value, "block_group")
    assert can_normalize_geoid(value, "block_group") is False


@pytest.mark.parametrize("helper", [normalize_geoid_column, prepare_geoid_for_join])
@pytest.mark.parametrize(
    "values,level,expected",
    [
        ([6037, None, 6073], "county", ["06037", "06073"]),
        ([10010201001, None, 10010201002], "block_group", ["010010201001", "010010201002"]),
    ],
)
def test_float_column_with_missing_value_normalizes(helper, values, level, expected):
    frame = pd.DataFrame({"geoid": values}, dtype="float64")
    original = frame.copy(deep=True)
    result = helper(frame, "geoid", level)
    assert result["geoid"].iloc[[0, 2]].tolist() == expected
    assert pd.isna(result["geoid"].iloc[1])
    pd.testing.assert_frame_equal(frame, original)


@pytest.mark.parametrize(
    "value,level",
    [
        ("06ZZZ", "sldu"),
        ("0200T", "sldu"),
        ("06ZZ", "cd"),
        ("CA037", "county"),
        ("-6037", "county"),
        ("", "county"),
        (None, "county"),
    ],
)
def test_can_normalize_matches_normalization(value, level):
    try:
        normalize_geoid(value, level)
    except ValueError:
        normalizable = False
    else:
        normalizable = True
    assert can_normalize_geoid(value, level) is normalizable

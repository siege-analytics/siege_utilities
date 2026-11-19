"""Regression coverage for GEOID alphabets, padding, and float columns (#1486)."""

import pandas as pd
import pytest

from siege_utilities.geo.geoid_utils import (
    GEOIDValidator,
    can_normalize_geoid,
    geoid_to_slug,
    normalize_geoid,
    normalize_geoid_column,
    prepare_geoid_for_join,
    slug_to_geoid,
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
        ("06.ZZ", "sldu"),
        ("CAZZ", "cd"),
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


@pytest.mark.parametrize("geoid,level", [
    *DISTRICT_GEOIDS,
    ("061A", "cd"),
    ("06A1B", "sldl"),
    ("4801", "cd"),
    ("48001", "sldu"),
    ("48150", "sldl"),
])
def test_district_slug_round_trip_preserves_geoid(geoid, level):
    slug = geoid_to_slug(geoid, level)
    round_tripped = slug_to_geoid(slug)

    assert round_tripped == geoid
    assert validate_geoid(round_tripped, level) is True


@pytest.mark.parametrize("slug,expected", [
    ("ca-sldu-zzz", "06ZZZ"),
    ("CA-SLDL-ZzZ", "06ZZZ"),
    ("ak-sldu-00a", "0200A"),
    ("ca-cd-zz", "06ZZ"),
])
def test_district_slug_tail_canonicalizes_to_uppercase(slug, expected):
    assert slug_to_geoid(slug) == expected


# Real 2024 Census Vermont lower-chamber GEOIDs contain a hyphen (TIGERweb
# Legislative layer 6): Franklin-3, Windsor-Windham and Bennington-1.
VERMONT_SLDL_GEOIDS = ["50F-3", "50Y-W", "50B-1"]


@pytest.mark.parametrize("geoid", VERMONT_SLDL_GEOIDS)
def test_hyphenated_sld_geoid_normalizes_and_validates(geoid):
    assert normalize_geoid(geoid, "sldl") == geoid
    assert validate_geoid(geoid, "sldl") is True
    assert can_normalize_geoid(geoid, "sldl") is True


@pytest.mark.parametrize("helper", [normalize_geoid_column, prepare_geoid_for_join])
@pytest.mark.parametrize("geoid", VERMONT_SLDL_GEOIDS)
def test_hyphenated_sld_geoid_survives_column_helpers(helper, geoid):
    frame = pd.DataFrame(
        {"geoid": [geoid, None], "value": [100, 200]}, index=["keep-a", "keep-b"]
    )
    original = frame.copy(deep=True)
    result = helper(frame, "geoid", "sldl")
    assert result["geoid"].iloc[0] == geoid
    assert pd.isna(result["geoid"].iloc[1])
    assert result.index.equals(frame.index)
    pd.testing.assert_frame_equal(frame, original)


@pytest.mark.parametrize("geoid", VERMONT_SLDL_GEOIDS)
def test_hyphenated_sld_geoid_slug_round_trip(geoid):
    slug = geoid_to_slug(geoid, "sldl")
    assert slug == "vt-sldl-" + geoid[2:]
    assert slug_to_geoid(slug) == geoid


@pytest.mark.parametrize("slug,expected", [
    ("VT-SLDL-f-3", "50F-3"),
    ("vt-sldl-y-w", "50Y-W"),
])
def test_hyphenated_sld_slug_tail_canonicalizes_to_uppercase(slug, expected):
    assert slug_to_geoid(slug) == expected


@pytest.mark.parametrize("geoid", VERMONT_SLDL_GEOIDS)
def test_django_validator_accepts_hyphenated_sld_geoid(geoid):
    pytest.importorskip("django")
    assert GEOIDValidator("sldl")(geoid) is None


@pytest.mark.parametrize(
    "geoid,level",
    [
        ("06-1", "cd"),
        ("0-ZZ", "cd"),
        ("50F.3", "sldl"),
        ("50F/3", "sldl"),
        ("50F_3", "sldu"),
        ("50F 3", "sldu"),
    ],
)
def test_district_alphabet_rejects_other_punctuation_and_cd_hyphens(geoid, level):
    with pytest.raises(ValueError):
        normalize_geoid(geoid, level)
    assert validate_geoid(geoid, level) is False


# Lowercase district letters are canonicalized to uppercase by normalization
# (4.0.0 returned them unchanged); strict validation still requires the
# canonical uppercase form.
@pytest.mark.parametrize(
    "value,level,expected",
    [
        ("0200a", "sldu", "0200A"),
        ("06zzZ", "sldl", "06ZZZ"),
        ("50f-3", "sldl", "50F-3"),
        ("6zz", "cd", "06ZZ"),
    ],
)
def test_lowercase_district_input_canonicalizes_to_uppercase(value, level, expected):
    assert normalize_geoid(value, level) == expected
    assert can_normalize_geoid(value, level) is True
    assert validate_geoid(value, level, strict=False) is True
    assert validate_geoid(value, level) is False
    assert validate_geoid(expected, level) is True


@pytest.mark.parametrize("helper", [normalize_geoid_column, prepare_geoid_for_join])
def test_lowercase_district_column_canonicalizes_to_uppercase(helper):
    frame = pd.DataFrame({"geoid": ["0200a", None, "50f-3"]})
    original = frame.copy(deep=True)
    result = helper(frame, "geoid", "sldl")
    assert result["geoid"].iloc[[0, 2]].tolist() == ["0200A", "50F-3"]
    assert pd.isna(result["geoid"].iloc[1])
    pd.testing.assert_frame_equal(frame, original)


@pytest.mark.parametrize("value,level", [("06éZ", "cd"), ("06ßZ", "cd")])
def test_non_ascii_district_letters_are_not_case_mapped(value, level):
    with pytest.raises(ValueError):
        normalize_geoid(value, level)

"""Connecticut's 2022 recode must not pass through as unchanged geography."""

import pandas as pd
import pytest

from siege_utilities.geo.place_history import DictCrosswalkProvider, place_history
from siege_utilities.geo.timeseries.longitudinal_data import (
    _normalize_boundaries_multi_year,
)


CT_CROSSWALK_ERROR = r"Connecticut.*2020->2022 crosswalk"


def test_place_history_ct_tract_crossing_raises():
    with pytest.raises(ValueError, match=CT_CROSSWALK_ERROR):
        place_history("09001010100", 2020, 2023, provider=DictCrosswalkProvider())


@pytest.mark.parametrize("county", [
    "09001", "09003", "09005", "09007", "09009", "09011", "09013", "09015",
    "09110", "09120", "09130", "09140", "09150", "09160", "09170", "09180",
    "09190",
])
@pytest.mark.parametrize("years", [(2021, 2022), (2022, 2021)])
def test_place_history_ct_county_crossing_raises(county, years):
    with pytest.raises(ValueError, match=CT_CROSSWALK_ERROR):
        place_history(county, *years, provider=DictCrosswalkProvider())


@pytest.mark.parametrize("geoid", [
    "09001010100", "090010101001", "090010101001001",
    "09190010100", "091900101001", "091900101001001",
])
@pytest.mark.parametrize("years", [(2010, 2023), (2023, 2010)])
def test_place_history_ct_descendant_crossing_raises(geoid, years):
    with pytest.raises(ValueError, match=CT_CROSSWALK_ERROR):
        place_history(geoid, *years, provider=DictCrosswalkProvider())


@pytest.mark.parametrize("geoid,from_year,to_year", [
    ("17031010100", 2020, 2023),
    ("09", 2020, 2023),  # State GEOIDs do not encode a county.
    ("0900100", 2020, 2023),  # Place GEOIDs are not county descendants.
    ("0900100100", 2020, 2023),  # County subdivisions are outside this guard.
    ("09002010100", 2020, 2023),  # Not an old or new CT county code.
    ("09111010100", 2020, 2023),
    ("09001010100", 2020, 2021),
    ("09001010100", 2021, 2020),
    ("09001010100", 2021, 2021),
    ("09190010100", 2022, 2022),
    ("09190010100", 2022, 2023),
])
def test_place_history_outside_ct_crossing_is_unchanged(geoid, from_year, to_year):
    result = place_history(geoid, from_year, to_year, provider=DictCrosswalkProvider())

    assert not result.errors
    assert result.lineage.is_unchanged
    assert result.lineage.terminal_geoids == [geoid]


def _frame(geoids):
    return pd.DataFrame({"GEOID": geoids, "B01001_001E": [100] * len(geoids)})


@pytest.mark.parametrize("target_year", [2020, 2021, 2022, 2023])
@pytest.mark.parametrize("state_fips", ["09", None])
@pytest.mark.parametrize("geography,suffix", [
    ("county", ""), ("tract", "010100"),
    ("block_group", "0101001"), ("block", "0101001001"),
])
def test_normalization_ct_crossing_raises(target_year, state_fips, geography, suffix):
    # Including non-CT rows covers a nationwide request without a state filter.
    yearly_data = {
        2021: _frame(["17031" + suffix, "09001" + suffix]),
        2022: _frame(["17031" + suffix, "09190" + suffix]),
    }

    with pytest.raises(ValueError, match=CT_CROSSWALK_ERROR):
        _normalize_boundaries_multi_year(
            yearly_data, target_year, geography, state_fips,
        )


@pytest.mark.parametrize("year,geoid,target_year", [
    (2021, "09001010100", 2022),
    (2022, "09190010100", 2021),
])
def test_normalization_ct_source_to_target_crossing_raises(year, geoid, target_year):
    with pytest.raises(ValueError, match=CT_CROSSWALK_ERROR):
        _normalize_boundaries_multi_year(
            {year: _frame([geoid])}, target_year, "tract", "09",
        )


@pytest.mark.parametrize("yearly_geoids,target_year,geography,state_fips", [
    ({2021: ["17031010100"], 2022: ["17031010100"]}, 2020, "tract", "17"),
    ({2021: ["09"], 2022: ["09"]}, 2020, "state", "09"),
    ({2021: ["0900100"], 2022: ["0900100"]}, 2020, "place", "09"),
    ({2020: ["09001010100"], 2021: ["09001010100"]}, 2020, "tract", "09"),
    ({2021: ["09001010100"]}, 2021, "tract", "09"),
    ({2022: ["09190010100"]}, 2022, "tract", "09"),
    ({2022: ["09190010100"], 2023: ["09190010100"]}, 2022, "tract", "09"),
    ({2021: [], 2022: []}, 2020, "tract", "09"),
    ({}, 2020, "tract", "09"),
])
def test_normalization_outside_ct_crossing_is_unchanged(
    yearly_geoids, target_year, geography, state_fips,
):
    yearly_data = {year: _frame(geoids) for year, geoids in yearly_geoids.items()}

    result = _normalize_boundaries_multi_year(
        yearly_data, target_year, geography, state_fips,
    )

    assert result.keys() == yearly_data.keys()
    for year, frame in yearly_data.items():
        pd.testing.assert_frame_equal(result[year], frame)

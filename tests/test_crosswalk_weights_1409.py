"""Pandas-only regressions for crosswalk weights and normalization (#1409)."""

from unittest.mock import patch

import pandas as pd
import pytest

from siege_utilities.geo.crosswalk.crosswalk_processor import (
    CrosswalkProcessor,
    normalize_to_year,
)
from siege_utilities.geo.crosswalk.relationship_types import WeightMethod


def processor(crosswalk):
    return CrosswalkProcessor(pd.DataFrame(crosswalk), 2010, 2020, "tract")


@pytest.mark.parametrize("aggregation_func, partial_value", [("sum", 5.0), ("weighted_mean", 2.5)])
def test_extensive_sum_preserves_missing_and_sums_available_values(aggregation_func, partial_value):
    proc = processor({
        "source_geoid": ["S1", "S2", "S3", "S4", "S5"],
        "target_geoid": ["missing", "missing", "partial", "partial", "zero"],
        "area_weight": [1.0] * 5,
    })
    data = pd.DataFrame({
        "GEOID": ["S1", "S2", "S3", "S4", "S5"],
        "count": [float("nan"), float("nan"), 5.0, float("nan"), 0.0],
        "other_count": [2.0, 3.0, float("nan"), float("nan"), 0.0],
    })

    result = proc.transform(data, aggregation_func=aggregation_func).set_index("GEOID")

    assert pd.isna(result.loc["missing", "count"])
    assert result.loc["partial", "count"] == partial_value
    assert result.loc["zero", "count"] == 0.0
    assert result.loc["missing", "other_count"] == (5.0 if aggregation_func == "sum" else 2.5)
    assert pd.isna(result.loc["partial", "other_count"])


@pytest.mark.parametrize("method", [WeightMethod.POPULATION, WeightMethod.HOUSING])
def test_requested_weight_column_is_required(method):
    proc = processor({
        "source_geoid": ["S1", "S1"],
        "target_geoid": ["T1", "T2"],
        "area_weight": [0.5, 0.5],
    })
    data = pd.DataFrame({"GEOID": ["S1"], "count": [100.0]})

    with pytest.raises(ValueError, match=f"{method.value}_weight"):
        proc.transform(data, weight_method=method)


@pytest.mark.parametrize("method, expected", [
    (WeightMethod.POPULATION, {"T1": 20.0, "T2": 120.0, "unmatched": 7.0}),
    (WeightMethod.HOUSING, {"T1": 75.0, "T2": 65.0, "unmatched": 7.0}),
])
def test_requested_weights_drive_split_and_merge_without_column_collisions(method, expected):
    proc = processor({
        "source_geoid": ["S1", "S1", "S2"],
        "target_geoid": ["T1", "T2", "T2"],
        "area_weight": [0.5, 0.5, 1.0],
        "population_weight": [0.2, 0.8, 1.0],
        "housing_weight": [0.75, 0.25, 1.0],
    })
    weight_column = f"{method.value}_weight"
    data = pd.DataFrame({
        "GEOID": ["S1", "S2", "unmatched"],
        "count": [100.0, 40.0, 7.0],
        # An ordinary value column must not collide with crosswalk metadata.
        weight_column: [10.0, 4.0, 0.7],
    })

    result = proc.transform(data, weight_method=method).set_index("GEOID")
    area_result = proc.transform(data, weight_method=WeightMethod.AREA).set_index("GEOID")

    assert result["count"].to_dict() == pytest.approx(expected)
    assert result[weight_column].to_dict() == pytest.approx({k: v / 10 for k, v in expected.items()})
    assert result["count"].sum() == pytest.approx(data["count"].sum())
    assert result.loc["T1", "count"] != area_result.loc["T1", "count"]
    assert result.loc["T2", "count"] != area_result.loc["T2", "count"]
    assert set(result.columns) == {"count", weight_column}


@pytest.mark.parametrize("method", [WeightMethod.POPULATION, WeightMethod.HOUSING])
def test_requested_weights_preserve_zero_and_missing_allocations(method):
    proc = processor({
        "source_geoid": ["S1", "S1"],
        "target_geoid": ["T1", "T2"],
        "area_weight": [0.5, 0.5],
        f"{method.value}_weight": [0.0, float("nan")],
    })
    data = pd.DataFrame({"GEOID": ["S1"], "count": [100.0]})

    result = proc.transform(data, weight_method=method).set_index("GEOID")

    assert result.loc["T1", "count"] == 0.0
    assert pd.isna(result.loc["T2", "count"])


@pytest.mark.parametrize("source_values", [[90.0], [30.0, 60.0]])
def test_equal_conserves_totals_on_pure_split_and_pure_merge(source_values):
    split = processor({
        "source_geoid": ["S1", "S1", "S1"],
        "target_geoid": ["T1", "T2", "T3"],
        "area_weight": [0.2, 0.3, 0.5],
    })
    data = pd.DataFrame({"GEOID": ["S1"] * len(source_values), "count": source_values})

    result = split.transform(data, weight_method=WeightMethod.EQUAL).set_index("GEOID")

    assert result["count"].to_dict() == pytest.approx({"T1": 30.0, "T2": 30.0, "T3": 30.0})
    assert result["count"].sum() == pytest.approx(90.0)

    merge = processor({
        "source_geoid": ["S1", "S2", "S3"],
        "target_geoid": ["T1", "T1", "T1"],
        "area_weight": [1.0, 1.0, 1.0],
    })
    data = pd.DataFrame({"GEOID": ["S1", "S2", "S3"], "count": [10.0, 20.0, 60.0]})
    total = merge.transform(data, weight_method=WeightMethod.EQUAL).set_index("GEOID")
    mean = merge.transform(
        data, weight_method=WeightMethod.EQUAL, aggregation_func="weighted_mean",
    ).set_index("GEOID")

    assert total["count"].to_dict() == {"T1": 90.0}
    assert mean["count"].to_dict() == {"T1": 30.0}


@pytest.mark.parametrize("method, expected_counts", [
    (None, {"T1": 25.0, "T2": 115.0}),
    (WeightMethod.EQUAL, {"T1": 50.0, "T2": 90.0}),
    (WeightMethod.POPULATION, {"T1": 20.0, "T2": 120.0}),
    (WeightMethod.HOUSING, {"T1": 75.0, "T2": 65.0}),
])
def test_normalize_to_year_averages_rates_and_allocates_counts(method, expected_counts):
    crosswalk = pd.DataFrame({
        "source_geoid": ["S1", "S1", "S2"],
        "target_geoid": ["T1", "T2", "T2"],
        "area_weight": [0.25, 0.75, 1.0],
        "population_weight": [0.2, 0.8, 1.0],
        "housing_weight": [0.75, 0.25, 1.0],
        "overlap_area": [1.0, 3.0, 9.0],
    })
    data = pd.DataFrame({"GEOID": ["S1", "S2"], "count": [100.0, 40.0], "rate": [0.2, 0.8]})
    kwargs = {} if method is None else {"weight_method": method}

    with patch(
        "siege_utilities.geo.crosswalk.crosswalk_processor.get_crosswalk",
        return_value=crosswalk,
    ) as get_crosswalk:
        result = normalize_to_year(
            data, data_year=2010, target_year=2020,
            intensive_variables=["rate"], **kwargs,
        ).set_index("GEOID")

    assert result["rate"].to_dict() == pytest.approx({"T1": 0.2, "T2": 0.65})
    assert result["count"].to_dict() == pytest.approx(expected_counts)
    assert result["count"].sum() == pytest.approx(140.0)
    get_crosswalk.assert_called_once_with(
        source_year=2010, target_year=2020, geography_level="tract", state_fips=None,
    )

"""Carried coverage with weighted_mean, and chained normalize_to_year calls.

weighted_mean divides by the weight of the rows whose value is present.
Carried coverage says how complete a value is; it is not a weight, so it must
not shrink that denominator.

A 2000 to 2020 chain takes two steps, for example transform with your own
2000 to 2010 crosswalk table and then normalize_to_year from 2010 to 2020, the
only transition the Census crosswalk client serves. The second call receives
the <col>_coverage columns of the first and needs carried_coverage to accept
them. The chained tests below run two normalize_to_year calls through a
patched crosswalk lookup, which exercises the same second step.
"""
from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest

from siege_utilities.geo.crosswalk import crosswalk_processor
from siege_utilities.geo.crosswalk.crosswalk_processor import (
    CrosswalkProcessor,
    normalize_to_year,
)

ONE_TO_ONE = {"source_geoid": ["X"], "target_geoid": ["P"], "area_weight": [1.0]}
MERGE = {"source_geoid": ["X", "Y"], "target_geoid": ["P", "P"], "area_weight": [1.0, 1.0]}


def _proc(rows):
    return CrosswalkProcessor(pd.DataFrame(rows), 2010, 2020, "tract")


def _weighted_mean(rows, data):
    out = _proc(rows).transform(
        data, aggregation_func="weighted_mean", carried_coverage=["pop_coverage"],
    )
    return out.set_index("GEOID")


# --- weighted_mean with carried coverage --------------------------------------

def test_weighted_mean_one_to_one_step_keeps_the_value_and_its_coverage():
    data = pd.DataFrame({"GEOID": ["X"], "pop": [10.0], "pop_coverage": [0.5]})
    out = _weighted_mean(ONE_TO_ONE, data)
    assert out.loc["P", "pop"] == pytest.approx(10.0)
    assert out.loc["P", "pop_coverage"] == pytest.approx(0.5)


def test_weighted_mean_of_two_values_does_not_depend_on_their_coverage():
    data = pd.DataFrame({"GEOID": ["X", "Y"], "pop": [10.0, 20.0],
                         "pop_coverage": [0.5, 1.0]})
    out = _weighted_mean(MERGE, data)
    plain = _proc(MERGE).transform(
        data[["GEOID", "pop"]], aggregation_func="weighted_mean",
    ).set_index("GEOID")
    assert plain.loc["P", "pop"] == pytest.approx(15.0)
    assert out.loc["P", "pop"] == pytest.approx(15.0)
    assert out.loc["P", "pop_coverage"] == pytest.approx(0.75)


def test_weighted_mean_chain_keeps_the_step_one_mean():
    # Step 1: A (weight 0.25) has a value, B (weight 0.75) does not.
    step1_rows = {"source_geoid": ["A", "B"], "target_geoid": ["X", "X"],
                  "area_weight": [0.25, 0.75]}
    data = pd.DataFrame({"GEOID": ["A", "B"], "pop": [8.0, np.nan]})
    step1 = _proc(step1_rows).transform(data, aggregation_func="weighted_mean")
    assert step1.set_index("GEOID").loc["X", "pop"] == pytest.approx(8.0)
    assert step1.set_index("GEOID").loc["X", "pop_coverage"] == pytest.approx(0.25)

    out = _weighted_mean(ONE_TO_ONE, step1)
    assert out.loc["P", "pop"] == pytest.approx(8.0)
    assert out.loc["P", "pop_coverage"] == pytest.approx(0.25)


def test_weighted_mean_skips_a_missing_value_whatever_its_carried_coverage():
    data = pd.DataFrame({"GEOID": ["X", "Y"], "pop": [10.0, np.nan],
                         "pop_coverage": [1.0, 0.5]})
    out = _weighted_mean(MERGE, data)
    assert out.loc["P", "pop"] == pytest.approx(10.0)


def test_weighted_mean_without_carried_coverage_is_unchanged():
    rows = {"source_geoid": ["A", "B", "C"], "target_geoid": ["X", "X", "X"],
            "area_weight": [0.5, 0.25, 0.25]}
    data = pd.DataFrame({"GEOID": ["A", "B", "C"], "pop": [4.0, 8.0, np.nan]})
    out = _proc(rows).transform(data, aggregation_func="weighted_mean").set_index("GEOID")
    assert out.loc["X", "pop"] == pytest.approx((4.0 * 0.5 + 8.0 * 0.25) / 0.75)
    assert out.loc["X", "pop_coverage"] == pytest.approx(0.75)


# --- chained normalize_to_year -------------------------------------------------

STEP1 = {"source_geoid": ["A", "B", "C"], "target_geoid": ["X", "Y", "Y"],
         "area_weight": [1.0, 1.0, 1.0]}
STEP2 = {"source_geoid": ["X", "Y", "Y"], "target_geoid": ["P", "Q1", "Q2"],
         "area_weight": [1.0, 0.5, 0.5]}


def _get_crosswalk(source_year, target_year, geography_level="tract", state_fips=None):
    if (source_year, target_year) == (2000, 2010):
        return pd.DataFrame(STEP1)
    if (source_year, target_year) == (2010, 2020):
        return pd.DataFrame(STEP2)
    raise ValueError(f"no crosswalk {source_year}->{target_year}")


def _chain(data):
    with patch.object(crosswalk_processor, "get_crosswalk", side_effect=_get_crosswalk):
        step1 = normalize_to_year(data, data_year=2000, target_year=2010)
        step2 = normalize_to_year(
            step1, data_year=2010, target_year=2020, carried_coverage=["pop_coverage"],
        )
    return step2.set_index("GEOID")


def test_chained_normalize_to_year_accepts_carried_coverage():
    data = pd.DataFrame({"GEOID": ["A", "B", "C"], "pop": [10.0, 5.0, 7.0]})
    out = _chain(data)
    assert sorted(out.columns) == ["pop", "pop_coverage"]
    assert out["pop"].to_dict() == pytest.approx({"P": 10.0, "Q1": 6.0, "Q2": 6.0})
    assert (out["pop_coverage"] == 1.0).all()


def test_chained_normalize_to_year_carries_coverage_and_a_missing_value():
    data = pd.DataFrame({"GEOID": ["A", "B", "C"], "pop": [10.0, 5.0, np.nan]})
    out = _chain(data)
    assert out.loc["P", "pop"] == pytest.approx(10.0)
    assert out.loc["P", "pop_coverage"] == pytest.approx(1.0)
    assert out.loc[["Q1", "Q2"], "pop"].isna().all()
    assert out.loc["Q1", "pop_coverage"] == pytest.approx(0.5)
    assert out.loc["Q2", "pop_coverage"] == pytest.approx(0.5)

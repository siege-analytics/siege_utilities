"""Equivalence tests for the single grouping pass in TemporalTimeseriesBuilder (#1891).

``build`` used to filter the whole snapshot frame once per boundary for every
variable. It now groups the frame once and reuses the rows. These tests run a
verbatim copy of the previous loop as an oracle and require the new builder to
produce the same results field for field, including order, skipped counts and
the point at which a missing column raises.
"""

from __future__ import annotations

import pandas as pd
import pytest

from siege_utilities.geo.schemas.demographics import DemographicTimeSeriesSchema
from siege_utilities.geo.temporal.services import (
    TemporalTimeseriesBuilder,
    TimeseriesBuildResult,
)

VAR_A = "B01001_001E"
VAR_B = "B19013_001E"
YEARS = [2016, 2017, 2018, 2019]


def _legacy_build(builder, variables, years, geography_type, snapshots_df):
    """The previous per-boundary loop, copied verbatim from develop 6c049c2c."""
    years_sorted = sorted(years)
    results = []
    for variable in variables:
        result = TimeseriesBuildResult(
            variable_code=variable,
            geography_type=geography_type,
        )
        series_list = []

        boundary_ids = snapshots_df["boundary_id"].unique()
        for bid in boundary_ids:
            bid_rows = snapshots_df[snapshots_df["boundary_id"] == bid]

            values_by_year = {}
            moe_by_year = {}

            for _, row in bid_rows.iterrows():
                raw_yr = row["year"]
                if raw_yr is None or (isinstance(raw_yr, float) and raw_yr != raw_yr):
                    continue
                yr = int(raw_yr)
                if yr not in years_sorted:
                    continue
                vals = row.get("values", {})
                if isinstance(vals, dict) and variable in vals:
                    val = vals[variable]
                    if val is not None:
                        values_by_year[yr] = val
                        moe_vals = row.get("moe_values", {})
                        if isinstance(moe_vals, dict) and variable in moe_vals:
                            moe_by_year[yr] = moe_vals[variable]

            if len(values_by_year) < 2:
                result.records_skipped += 1
                continue

            s_years = sorted(values_by_year.keys())
            s_values = [values_by_year[y] for y in s_years]
            s_moe = [moe_by_year.get(y) for y in s_years]

            mean_val = sum(s_values) / len(s_values)
            std_dev = builder._std_dev(s_values, mean_val)
            elapsed_years = s_years[-1] - s_years[0]
            cagr = builder._cagr(s_values[0], s_values[-1], elapsed_years)
            trend = builder._trend_direction(s_values)

            ts = DemographicTimeSeriesSchema(
                boundary_type=geography_type,
                boundary_id=str(bid),
                variable_code=variable,
                dataset=builder.dataset,
                start_year=s_years[0],
                end_year=s_years[-1],
                years=s_years,
                values=s_values,
                moe_values=s_moe,
                mean_value=mean_val,
                std_dev=std_dev,
                cagr=cagr,
                trend_direction=trend,
            )
            series_list.append(ts)
            result.records_created += 1

        result.series = series_list
        results.append(result)
    return results


def _snapshot(results):
    """Every observable field of a build, in order."""
    return [
        (
            r.variable_code,
            r.geography_type,
            r.records_created,
            r.records_skipped,
            list(r.errors),
            [s.model_dump() for s in r.series],
        )
        for r in results
    ]


def _row(bid, year, a=None, b=None, moe_a=None):
    values = {}
    if a is not None:
        values[VAR_A] = a
    if b is not None:
        values[VAR_B] = b
    moe = {} if moe_a is None else {VAR_A: moe_a}
    return {"boundary_id": bid, "year": year, "values": values, "moe_values": moe}


def _assert_equivalent(df, variables=(VAR_A, VAR_B), years=YEARS):
    builder = TemporalTimeseriesBuilder(dataset="acs5")
    expected = _legacy_build(builder, list(variables), years, "tract", df)
    actual = builder.build(
        variables=list(variables), years=years,
        geography_type="tract", snapshots_df=df,
    )
    assert _snapshot(actual) == _snapshot(expected)
    return actual


FRAMES = {
    "empty_with_columns": pd.DataFrame(
        columns=["boundary_id", "year", "values", "moe_values"]
    ),
    "single_boundary": pd.DataFrame(
        [_row("T1", y, a=100 + y, b=5 + y, moe_a=y % 7) for y in YEARS]
    ),
    "missing_requested_year": pd.DataFrame(
        [_row("T1", 2016, a=10), _row("T1", 2019, a=30),
         _row("T2", 2017, a=5)]
    ),
    "duplicate_years_last_row_wins": pd.DataFrame(
        [_row("T1", 2016, a=10, moe_a=1), _row("T1", 2017, a=20, moe_a=2),
         _row("T1", 2017, a=99, moe_a=9), _row("T1", 2018, a=30)]
    ),
    "unrequested_year_ignored": pd.DataFrame(
        [_row("T1", 2010, a=1), _row("T1", 2016, a=10), _row("T1", 2018, a=30)]
    ),
    "nan_year_skipped": pd.DataFrame(
        [_row("T1", 2016.0, a=10), _row("T1", float("nan"), a=50),
         _row("T1", 2018.0, a=30)]
    ),
    "nan_and_none_boundary_ids_counted_skipped": pd.DataFrame(
        [_row("T1", 2016, a=10), _row(float("nan"), 2016, a=1),
         _row("T1", 2017, a=20), _row(None, 2017, a=2),
         _row(float("nan"), 2018, a=3)]
    ),
    "mixed_int_and_str_ids_interleaved": pd.DataFrame(
        [_row(1, 2016, a=10), _row("1", 2016, a=11), _row("B", 2016, a=7),
         _row(1, 2017, a=12), _row("1", 2017, a=13), _row("B", 2018, b=4),
         _row(2, 2018, a=3), _row(1, 2018, a=14, b=6), _row("1", 2019, a=15)]
    ),
    "value_none_and_variable_absent": pd.DataFrame(
        [_row("T1", 2016, a=10), {"boundary_id": "T1", "year": 2017,
                                  "values": {VAR_A: None}, "moe_values": {}},
         _row("T1", 2018, b=3), _row("T1", 2019, a=40, moe_a=4)]
    ),
    "non_dict_values_cells": pd.DataFrame(
        [{"boundary_id": "T1", "year": 2016, "values": None, "moe_values": None},
         _row("T1", 2017, a=20, moe_a=2), _row("T1", 2018, a=30),
         {"boundary_id": "T1", "year": 2019, "values": "n/a", "moe_values": 0}]
    ),
}


def _with_ids(ids, dtype=None):
    """Two years per id, ids in interleaved frame order, optional column dtype."""
    rows = []
    for year in (2016, 2017):
        for i, bid in enumerate(ids):
            rows.append(_row(bid, year, a=10 * (i + 1) + year % 10))
    df = pd.DataFrame(rows)
    if dtype is not None:
        df["boundary_id"] = df["boundary_id"].astype(dtype)
    return df


# Typed id columns, where ``unique()`` and the factorized groups can yield
# different scalar types (numpy vs pandas) for the same id.
FRAMES.update({
    "int64_ids": _with_ids([30, 10, 20]),
    "float_ids_with_nan": _with_ids([3.0, float("nan"), 1.5]),
    "datetime_ids": _with_ids(
        [pd.Timestamp("2020-03-01"), pd.Timestamp("2019-01-01")]
    ),
    "categorical_ids_with_nan": _with_ids(["Z", None, "A"], dtype="category"),
})


@pytest.mark.parametrize("name", sorted(FRAMES))
def test_grouped_build_matches_previous_algorithm(name):
    _assert_equivalent(FRAMES[name])


def test_boundary_order_is_first_appearance_not_sorted():
    df = pd.DataFrame(
        [_row("Z9", 2016, a=1), _row("A1", 2016, a=2), _row("M5", 2016, a=3),
         _row("A1", 2017, a=4), _row("Z9", 2017, a=5), _row("M5", 2017, a=6)]
    )
    actual = _assert_equivalent(df, variables=(VAR_A,))
    assert [s.boundary_id for s in actual[0].series] == ["Z9", "A1", "M5"]


def test_missing_boundary_ids_each_count_as_one_skipped_boundary():
    df = FRAMES["nan_and_none_boundary_ids_counted_skipped"]
    actual = _assert_equivalent(df, variables=(VAR_A,))
    expected_skipped = len(df["boundary_id"].unique()) - 1  # all but T1
    assert actual[0].records_created == 1
    assert actual[0].records_skipped == expected_skipped


def test_duplicate_year_keeps_last_row_in_frame_order():
    actual = _assert_equivalent(
        FRAMES["duplicate_years_last_row_wins"], variables=(VAR_A,)
    )
    series = actual[0].series[0]
    assert series.years == [2016, 2017, 2018]
    assert series.values == [10, 99, 30]
    assert series.moe_values == [1, 9, None]


def test_frame_is_grouped_once_for_all_variables(monkeypatch):
    calls = []
    original = TemporalTimeseriesBuilder._positions_by_boundary

    def counting(df, boundary_ids):
        calls.append(len(df))
        return original(df, boundary_ids)

    monkeypatch.setattr(
        TemporalTimeseriesBuilder, "_positions_by_boundary", staticmethod(counting)
    )
    df = FRAMES["mixed_int_and_str_ids_interleaved"]
    _assert_equivalent(df, variables=(VAR_A, VAR_B, "B99999_001E"))
    assert calls == [len(df)]


def test_no_variables_does_not_group_or_read_columns(monkeypatch):
    def fail(df, boundary_ids):
        raise AssertionError("grouping must not run without variables")

    monkeypatch.setattr(
        TemporalTimeseriesBuilder, "_positions_by_boundary", staticmethod(fail)
    )
    df = pd.DataFrame({"unrelated": [1, 2]})
    builder = TemporalTimeseriesBuilder(dataset="acs5")
    assert builder.build(
        variables=[], years=YEARS, geography_type="tract", snapshots_df=df
    ) == []


def test_missing_boundary_id_column_raises_keyerror_like_before():
    df = pd.DataFrame([{"year": 2016, "values": {VAR_A: 1}}])
    builder = TemporalTimeseriesBuilder(dataset="acs5")
    with pytest.raises(KeyError, match="boundary_id"):
        _legacy_build(builder, [VAR_A], YEARS, "tract", df)
    with pytest.raises(KeyError, match="boundary_id"):
        builder.build(
            variables=[VAR_A], years=YEARS, geography_type="tract",
            snapshots_df=df,
        )


def test_missing_year_column_raises_keyerror_like_before():
    df = pd.DataFrame([{"boundary_id": "T1", "values": {VAR_A: 1}}])
    builder = TemporalTimeseriesBuilder(dataset="acs5")
    with pytest.raises(KeyError, match="year"):
        _legacy_build(builder, [VAR_A], YEARS, "tract", df)
    with pytest.raises(KeyError, match="year"):
        builder.build(
            variables=[VAR_A], years=YEARS, geography_type="tract",
            snapshots_df=df,
        )


def test_missing_year_column_with_only_missing_ids_does_not_raise():
    """No boundary has rows, so the year column is never read, as before."""
    df = pd.DataFrame([{"boundary_id": None, "values": {VAR_A: 1}}])
    actual = _assert_equivalent(df, variables=(VAR_A,))
    assert actual[0].records_skipped == 1
    assert actual[0].records_created == 0

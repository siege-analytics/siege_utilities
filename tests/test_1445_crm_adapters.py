"""Pipeline completeness and UTC time-series regressions (#1445)."""

import pandas as pd
import pytest

from siege_utilities.connectors._adapters import pipeline_adapter, timeseries_adapter


@pytest.fixture
def deals():
    return pd.DataFrame({"stage": ["Won", "Lost", None], "amount": [100, 50, 999]})


def test_pipeline_retains_stageless_amount(deals):
    result = pipeline_adapter(deals)
    assert result["count"].sum() == 3
    assert result.total_value.sum() == 1149
    assert result.set_index("stage").loc["(none)"].to_dict() == {
        "count": 1, "total_value": 999, "avg_value": 999,
    }


def test_pipeline_preserves_unlisted_stage_label(deals):
    result = pipeline_adapter(deals, stage_order=["Prospect", "Won"])
    assert "Lost" in result.stage.tolist()
    assert result.stage.notna().all()
    assert result.total_value.sum() == 1149


def test_pipeline_emits_missing_ordered_stages_as_zero(deals):
    result = pipeline_adapter(deals, stage_order=["Prospect", "Won"])
    assert result.stage.tolist() == ["Prospect", "Won", "Lost", "(none)"]
    assert result.iloc[0].to_dict() == {
        "stage": "Prospect", "count": 0, "total_value": 0, "avg_value": 0,
    }


def test_pipeline_empty_data_still_emits_ordered_stages():
    result = pipeline_adapter(pd.DataFrame(), stage_order=["Prospect", "Won"])
    assert result.to_dict("records") == [
        {"stage": stage, "count": 0, "total_value": 0, "avg_value": 0}
        for stage in ["Prospect", "Won"]
    ]


def test_pipeline_categorical_nulls_and_duplicate_order_do_not_mutate_input():
    frame = pd.DataFrame({"phase": pd.Categorical(["Won", None, "Lost"]), "value": [0, 999, 50]})
    original = frame.copy(deep=True)
    result = pipeline_adapter(frame, stage_column="phase", value_column="value",
                              stage_order=["Prospect", "Won", "Won"])
    assert result.stage.tolist() == ["Prospect", "Won", "(none)", "Lost"]
    assert result.total_value.sum() == 1049
    pd.testing.assert_frame_equal(frame, original)


def test_timeseries_mixed_dst_offsets_use_utc_days():
    frame = pd.DataFrame({
        "timestamp": ["2026-03-08T00:30:00-05:00", "2026-03-08T23:30:00-04:00", "invalid"],
        "amount": [10, 20, 999],
    })
    original = frame.copy(deep=True)
    result = timeseries_adapter(frame)
    assert result.date.tolist() == [pd.Timestamp("2026-03-08", tz="UTC"), pd.Timestamp("2026-03-09", tz="UTC")]
    assert result.value.tolist() == [1, 1]
    totals = timeseries_adapter(frame, value_column="amount", agg="sum")
    assert totals.value.tolist() == [10, 20]
    pd.testing.assert_frame_equal(frame, original)

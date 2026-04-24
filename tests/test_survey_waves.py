"""Tests for siege_utilities.survey Wave/WaveSet + wave_charts (ELE-2440)."""

from __future__ import annotations

from datetime import date

import pandas as pd
import pytest

from siege_utilities.reporting.pages.page_models import TableType
from siege_utilities.survey import (
    Wave,
    WaveSet,
    WavesError,
    build_chain,
    compare_waves,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _wave_df(d_count: int, r_count: int) -> pd.DataFrame:
    return pd.DataFrame({"party": ["D"] * d_count + ["R"] * r_count})


@pytest.fixture
def three_wave_set() -> WaveSet:
    return WaveSet(
        name="2024 tracker",
        waves=[
            Wave(id="W1", date=date(2024, 3, 1), df=_wave_df(60, 40)),
            Wave(id="W2", date=date(2024, 6, 1), df=_wave_df(55, 45)),
            Wave(id="W3", date=date(2024, 9, 1), df=_wave_df(50, 50)),
        ],
    )


# ---------------------------------------------------------------------------
# Wave / WaveSet dataclasses
# ---------------------------------------------------------------------------


class TestWaveDataclass:
    def test_minimal_wave(self):
        w = Wave(id="W1", date=date(2024, 3, 1))
        assert w.id == "W1"
        assert w.df is None
        assert w.stack is None
        assert w.weight_scheme is None

    def test_wave_with_df(self):
        df = _wave_df(10, 10)
        w = Wave(id="W1", date=date(2024, 3, 1), df=df)
        assert w.df is df


class TestWaveSet:
    def test_add_wave(self):
        ws = WaveSet(name="x")
        w = Wave(id="W1", date=date(2024, 1, 1))
        ws.add_wave(w)
        assert ws.waves == [w]

    def test_ordered_sorts_by_date(self):
        out_of_order = WaveSet(
            name="mix",
            waves=[
                Wave(id="late", date=date(2024, 9, 1)),
                Wave(id="early", date=date(2024, 3, 1)),
                Wave(id="mid", date=date(2024, 6, 1)),
            ],
        )
        assert [w.id for w in out_of_order.ordered] == ["early", "mid", "late"]


# ---------------------------------------------------------------------------
# compare_chain / compare_waves
# ---------------------------------------------------------------------------


class TestCompareChain:
    def test_returns_longitudinal_chain(self, three_wave_set):
        chain = three_wave_set.compare_chain(row_var="party")
        assert chain.table_type is TableType.LONGITUDINAL

    def test_columns_are_wave_ids(self, three_wave_set):
        chain = three_wave_set.compare_chain(row_var="party")
        # Views keyed by wave id, plus the delta column
        assert "W1" in chain.views
        assert "W2" in chain.views
        assert "W3" in chain.views

    def test_delta_column_present_with_multiple_waves(self, three_wave_set):
        chain = three_wave_set.compare_chain(row_var="party")
        assert chain.delta_column is not None
        assert chain.delta_column in chain.views

    def test_delta_matches_last_minus_first(self, three_wave_set):
        chain = three_wave_set.compare_chain(row_var="party")
        # W1: D=60 R=40; W3: D=50 R=50 → ΔD = -10, ΔR = +10
        delta_views = {v.metric: v.count for v in chain.views[chain.delta_column]}
        assert delta_views["D"] == pytest.approx(-10.0)
        assert delta_views["R"] == pytest.approx(10.0)

    def test_single_wave_has_no_delta(self):
        single = WaveSet(
            name="one",
            waves=[Wave(id="W1", date=date(2024, 3, 1), df=_wave_df(10, 10))],
        )
        chain = single.compare_chain(row_var="party")
        assert chain.delta_column is None

    def test_dataframe_columns_ordered_by_date(self, three_wave_set):
        # Deliberately shuffle insertion order to prove `ordered` is what drives it.
        ws = WaveSet(
            name="shuffled",
            waves=[three_wave_set.waves[2], three_wave_set.waves[0], three_wave_set.waves[1]],
        )
        chain = ws.compare_chain(row_var="party")
        non_delta_cols = [c for c in chain.to_dataframe().columns if c != chain.delta_column]
        assert non_delta_cols == ["W1", "W2", "W3"]

    def test_empty_waveset_raises(self):
        with pytest.raises(WavesError, match="no waves"):
            compare_waves(WaveSet(name="empty"), row_var="party")

    def test_wave_missing_df_raises(self):
        ws = WaveSet(
            name="partial",
            waves=[
                Wave(id="W1", date=date(2024, 3, 1), df=_wave_df(10, 10)),
                Wave(id="W2", date=date(2024, 6, 1)),  # no df
            ],
        )
        with pytest.raises(WavesError, match="missing df"):
            ws.compare_chain(row_var="party")


# ---------------------------------------------------------------------------
# wave_charts — smoke tests
# ---------------------------------------------------------------------------


class TestWaveChartsSmoke:
    def test_trend_chart_returns_figure(self, three_wave_set):
        matplotlib = pytest.importorskip("matplotlib")
        matplotlib.use("Agg")
        from siege_utilities.reporting.wave_charts import trend_chart

        chain = three_wave_set.compare_chain(row_var="party")
        fig = trend_chart(chain)
        assert fig is not None
        assert len(fig.axes) == 1

    def test_heatmap_returns_figure(self, three_wave_set):
        matplotlib = pytest.importorskip("matplotlib")
        matplotlib.use("Agg")
        from siege_utilities.reporting.wave_charts import heatmap

        chain = three_wave_set.compare_chain(row_var="party")
        fig = heatmap(chain)
        assert fig is not None

    def test_rejects_non_longitudinal_chain(self):
        pytest.importorskip("matplotlib")
        from siege_utilities.reporting.wave_charts import WaveChartError, trend_chart

        df = _wave_df(10, 10).assign(county="Travis")
        chain = build_chain(
            df, row_var="party", break_vars=["county"],
            table_type=TableType.SINGLE_RESPONSE,
        )
        with pytest.raises(WaveChartError, match="LONGITUDINAL"):
            trend_chart(chain)

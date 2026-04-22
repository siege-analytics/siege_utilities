"""Tests for siege_utilities.reporting.analytics.polling_analyzer (SAL-63)."""
from __future__ import annotations

import pytest

# PollingAnalyzer pulls in ChartGenerator which imports reportlab; skip the
# whole module in envs (e.g. geo-without-GDAL CI) that don't install it.
pytest.importorskip("reportlab")

import matplotlib  # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

from siege_utilities.reporting.analytics.polling_analyzer import (  # noqa: E402
    PollingAnalysisError,
    PollingAnalyzer,
    _choose_heatmap_fmt,
)


@pytest.fixture
def sample_long_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "region": ["N", "N", "S", "S", "E", "W"],
            "segment": ["A", "B", "A", "B", "A", "B"],
            "value": [10, 20, 30, 40, 15, 25],
        }
    )


class TestChooseHeatmapFmt:
    def test_integer_data_returns_d(self):
        df = pd.DataFrame({"a": [1, 2], "b": [3, 4]})
        assert _choose_heatmap_fmt(df) == "d"

    def test_float_data_returns_2f(self):
        df = pd.DataFrame({"a": [1.5, 2.5], "b": [3.25, 4.75]})
        assert _choose_heatmap_fmt(df) == ".2f"


class TestPerformanceRankings:
    def test_returns_expected_shape(self, sample_long_df):
        analyzer = PollingAnalyzer()
        out = analyzer.create_performance_rankings(
            sample_long_df, dimensions=["region", "segment"]
        )
        assert set(out) == {"region", "segment"}
        for _, entries in out.items():
            assert isinstance(entries, list)
            for entry in entries:
                assert len(entry) == 3
                _, summed, pct = entry
                assert isinstance(summed, float)
                assert isinstance(pct, float)
                assert 0.0 <= pct <= 100.0

    def test_top_n_limits_results(self, sample_long_df):
        analyzer = PollingAnalyzer()
        out = analyzer.create_performance_rankings(
            sample_long_df, dimensions=["region"], top_n=2
        )
        assert len(out["region"]) == 2

    def test_missing_column_raises(self, sample_long_df):
        analyzer = PollingAnalyzer()
        with pytest.raises(PollingAnalysisError):
            analyzer.create_performance_rankings(
                sample_long_df, dimensions=["does_not_exist"]
            )


class TestPollingSummary:
    def test_summary_mentions_totals(self, sample_long_df):
        analyzer = PollingAnalyzer()
        out = analyzer.create_polling_summary({"region": sample_long_df})
        assert "value" in out
        assert "140" in out

    def test_raises_when_metric_missing_everywhere(self):
        analyzer = PollingAnalyzer()
        with pytest.raises(PollingAnalysisError):
            analyzer.create_polling_summary({"x": pd.DataFrame({"a": [1]})})

    def test_picks_first_non_metric_column_when_name_unspecified(self):
        """Caller does not have to tell us which column is the label."""
        analyzer = PollingAnalyzer()
        df = pd.DataFrame({"extra_meta": [0, 0, 0], "region": ["N", "S", "E"], "value": [10, 30, 5]})
        out = analyzer.create_polling_summary({"t": df})
        # 'extra_meta' is first non-metric col; its value for the max-value row is 0
        assert "0 leads t" in out or "leads t with 30" in out

    def test_name_column_kwarg_overrides_heuristic(self):
        """Explicit name_column= wins over positional guessing."""
        analyzer = PollingAnalyzer()
        df = pd.DataFrame({"extra_meta": [0, 0, 0], "region": ["N", "S", "E"], "value": [10, 30, 5]})
        out = analyzer.create_polling_summary({"t": df}, name_column="region")
        assert "S leads t" in out

    def test_raises_when_no_non_metric_column(self):
        analyzer = PollingAnalyzer()
        df = pd.DataFrame({"value": [1, 2, 3]})
        with pytest.raises(PollingAnalysisError, match="no non-metric column"):
            analyzer.create_polling_summary({"t": df})


class TestHeatmap:
    def test_integer_data_uses_d_format(self, sample_long_df):
        """Assert both the helper returns 'd' and the heatmap renders."""
        analyzer = PollingAnalyzer()
        ct = analyzer.create_cross_tabulation_matrix(
            sample_long_df, dimensions=["region", "segment"]
        )
        key = next(iter(ct))
        assert _choose_heatmap_fmt(ct[key]) == "d"
        fig = analyzer.create_heatmap_visualization(ct[key])
        assert isinstance(fig, plt.Figure)
        plt.close(fig)

    def test_float_data_picks_2f_and_does_not_raise(self):
        analyzer = PollingAnalyzer()
        float_ct = pd.DataFrame({"a": [1.5, 2.5], "b": [3.25, 4.75]}, index=["x", "y"])
        assert _choose_heatmap_fmt(float_ct) == ".2f"
        fig = analyzer.create_heatmap_visualization(float_ct)
        assert isinstance(fig, plt.Figure)
        plt.close(fig)

    def test_metric_is_keyword_only(self, sample_long_df):
        analyzer = PollingAnalyzer()
        ct = analyzer.create_cross_tabulation_matrix(
            sample_long_df, dimensions=["region", "segment"]
        )
        key = next(iter(ct))
        with pytest.raises(TypeError):
            analyzer.create_heatmap_visualization(ct[key], "my title", "metric_name")


class TestChangeDetection:
    def test_default_column_names(self):
        analyzer = PollingAnalyzer()
        current = pd.DataFrame({"geography": ["A", "B"], "value": [100, 200]})
        historical = pd.DataFrame({"geography": ["A", "B"], "value": [80, 220]})
        out = analyzer.create_change_detection_data(current, historical)
        assert set(["geography", "change_pct", "change_direction"]).issubset(out.columns)

    def test_zero_baseline_is_growth_from_zero_not_stable(self):
        """A brand-new geography (historical=0, current>0) must not collapse
        to 'stable' just because the percent is undefined."""
        analyzer = PollingAnalyzer()
        current = pd.DataFrame({"geography": ["NEW"], "value": [500]})
        historical = pd.DataFrame({"geography": ["NEW"], "value": [0]})
        out = analyzer.create_change_detection_data(current, historical)
        direction = out.loc[out["geography"] == "NEW", "change_direction"].iloc[0]
        assert direction == "growth_from_zero"

    def test_zero_baseline_zero_current_is_stable(self):
        analyzer = PollingAnalyzer()
        current = pd.DataFrame({"geography": ["DORMANT"], "value": [0]})
        historical = pd.DataFrame({"geography": ["DORMANT"], "value": [0]})
        out = analyzer.create_change_detection_data(current, historical)
        direction = out.loc[out["geography"] == "DORMANT", "change_direction"].iloc[0]
        assert direction == "stable"


class TestCrossTabulation:
    def test_missing_dimension_raises(self, sample_long_df):
        analyzer = PollingAnalyzer()
        with pytest.raises(PollingAnalysisError):
            analyzer.create_cross_tabulation_matrix(
                sample_long_df, dimensions=["region", "does_not_exist"]
            )


class TestLongitudinalAnalysis:
    def _time_series_df(self):
        return pd.DataFrame(
            {
                "date": pd.date_range("2026-01-01", periods=12, freq="D"),
                "region": ["N", "S"] * 6,
                "value": list(range(1, 13)),
            }
        )

    def test_returns_dict_keyed_by_period(self):
        analyzer = PollingAnalyzer()
        out = analyzer.create_longitudinal_analysis(
            self._time_series_df(), time_column="date", dimensions=["region"],
            periods=("daily", "weekly"),
        )
        assert set(out) == {"daily", "weekly"}
        assert set(out["daily"]) == {"region"}
        assert not out["daily"]["region"].empty

    def test_metric_is_keyword_only(self):
        analyzer = PollingAnalyzer()
        df = self._time_series_df()
        with pytest.raises(TypeError):
            analyzer.create_longitudinal_analysis(df, "date", ["region"], "value")

    def test_unknown_period_raises(self):
        analyzer = PollingAnalyzer()
        with pytest.raises(PollingAnalysisError, match="unknown period"):
            analyzer.create_longitudinal_analysis(
                self._time_series_df(), time_column="date",
                dimensions=["region"], periods=("yearly",),
            )

    def test_missing_time_column_raises(self):
        analyzer = PollingAnalyzer()
        df = self._time_series_df().drop(columns=["date"])
        with pytest.raises(PollingAnalysisError):
            analyzer.create_longitudinal_analysis(
                df, time_column="date", dimensions=["region"],
            )


class TestTrendAnalysisChart:
    def _longitudinal_data(self):
        return {
            "daily": pd.DataFrame(
                {
                    "period": pd.date_range("2026-01-01", periods=5, freq="D"),
                    "value": [10, 15, 20, 25, 30],
                }
            ),
            "weekly": pd.DataFrame(
                {
                    "period": pd.date_range("2026-01-01", periods=2, freq="W"),
                    "value": [100, 150],
                }
            ),
        }

    def test_returns_figure(self):
        analyzer = PollingAnalyzer()
        fig = analyzer.create_trend_analysis_chart(
            self._longitudinal_data(), dimension="region"
        )
        assert isinstance(fig, plt.Figure)
        plt.close(fig)

    def test_metric_is_keyword_only(self):
        analyzer = PollingAnalyzer()
        with pytest.raises(TypeError):
            analyzer.create_trend_analysis_chart(
                self._longitudinal_data(), "region", "value",
            )

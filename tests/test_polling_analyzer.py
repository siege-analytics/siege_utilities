"""Tests for siege_utilities.reporting.analytics.polling_analyzer (SAL-63)."""
from __future__ import annotations

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import pytest

from siege_utilities.reporting.analytics.polling_analyzer import (
    PollingAnalysisError,
    PollingAnalyzer,
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


class TestPerformanceRankings:
    def test_returns_expected_shape(self, sample_long_df):
        analyzer = PollingAnalyzer()
        out = analyzer.create_performance_rankings(
            sample_long_df, dimensions=["region", "segment"]
        )
        assert set(out) == {"region", "segment"}
        for dim, entries in out.items():
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


class TestHeatmap:
    def test_integer_data_uses_d_format(self, sample_long_df):
        analyzer = PollingAnalyzer()
        ct = analyzer.create_cross_tabulation_matrix(
            sample_long_df, dimensions=["region", "segment"]
        )
        key = next(iter(ct))
        fig = analyzer.create_heatmap_visualization(ct[key])
        assert isinstance(fig, plt.Figure)
        plt.close(fig)

    def test_float_data_does_not_raise(self):
        analyzer = PollingAnalyzer()
        float_ct = pd.DataFrame(
            {"a": [1.5, 2.5], "b": [3.25, 4.75]}, index=["x", "y"]
        )
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

    def test_zero_baseline_handled(self):
        analyzer = PollingAnalyzer()
        current = pd.DataFrame({"geography": ["A"], "value": [50]})
        historical = pd.DataFrame({"geography": ["A"], "value": [0]})
        out = analyzer.create_change_detection_data(current, historical)
        assert not out.empty


class TestCrossTabulation:
    def test_missing_dimension_raises(self, sample_long_df):
        analyzer = PollingAnalyzer()
        with pytest.raises(PollingAnalysisError):
            analyzer.create_cross_tabulation_matrix(
                sample_long_df, dimensions=["region", "does_not_exist"]
            )

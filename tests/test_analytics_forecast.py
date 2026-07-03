"""Tests for siege_utilities.analytics.forecast."""

import pytest

from siege_utilities.analytics.forecast import (
    ForecastAnalyzer,
    ForecastReport,
    _compute_accuracy,
    _grade_mape,
)


class TestGradeMape:
    def test_excellent(self):
        assert _grade_mape(5.0) == "Excellent"

    def test_good(self):
        assert _grade_mape(12.0) == "Good"

    def test_fair(self):
        assert _grade_mape(20.0) == "Fair"

    def test_poor(self):
        assert _grade_mape(30.0) == "Poor"

    def test_boundary_excellent(self):
        assert _grade_mape(9.99) == "Excellent"

    def test_boundary_good(self):
        assert _grade_mape(10.0) == "Good"


class TestComputeAccuracy:
    def test_mismatched_lengths_raises(self):
        with pytest.raises(ValueError, match="same length"):
            _compute_accuracy([100], [90, 80])

    def test_empty_raises(self):
        with pytest.raises(ValueError, match="At least one"):
            _compute_accuracy([], [])

    def test_all_zeros_raises(self):
        with pytest.raises(ValueError, match="All observations have actual=0"):
            _compute_accuracy([0, 0], [10, 20])

    def test_perfect_forecast(self):
        result = _compute_accuracy([100, 200, 300], [100, 200, 300])
        assert result.mape == 0.0
        assert result.bias == 0.0
        assert result.bias_direction == "neutral"
        assert result.grade == "Excellent"
        assert result.n_excluded == 0

    def test_over_forecasting(self):
        result = _compute_accuracy([100, 100], [120, 130])
        assert result.bias > 0
        assert result.bias_direction == "over-forecasting"

    def test_under_forecasting(self):
        result = _compute_accuracy([100, 100], [80, 70])
        assert result.bias < 0
        assert result.bias_direction == "under-forecasting"

    def test_zero_actual_excluded(self):
        result = _compute_accuracy([100, 0, 200], [90, 50, 180])
        assert result.n_excluded == 1
        assert result.n_observations == 3


class TestForecastAnalyzer:
    def test_mismatched_lengths_raises(self):
        with pytest.raises(ValueError, match="same length"):
            ForecastAnalyzer(actuals=[100], forecasts=[90, 80])

    def test_empty_raises(self):
        with pytest.raises(ValueError, match="At least one"):
            ForecastAnalyzer(actuals=[], forecasts=[])

    def test_categories_length_mismatch_raises(self):
        with pytest.raises(ValueError, match="categories must have same"):
            ForecastAnalyzer(
                actuals=[100, 200],
                forecasts=[90, 180],
                categories=["A"],
            )

    def test_periods_length_mismatch_raises(self):
        with pytest.raises(ValueError, match="periods must have same"):
            ForecastAnalyzer(
                actuals=[100, 200],
                forecasts=[90, 180],
                periods=["Q1"],
            )

    def test_happy_path(self):
        analyzer = ForecastAnalyzer(
            actuals=[100, 200, 150],
            forecasts=[110, 190, 160],
        )
        report = analyzer.analyze()
        assert isinstance(report, ForecastReport)
        assert report.overall.mape > 0
        assert report.overall.n_observations == 3
        assert report.by_category == []
        assert report.trend == []

    def test_category_breakdown(self):
        analyzer = ForecastAnalyzer(
            actuals=[100, 200, 150, 300],
            forecasts=[110, 190, 160, 280],
            categories=["East", "East", "West", "West"],
        )
        report = analyzer.analyze()
        assert len(report.by_category) == 2
        cats = {cb.category for cb in report.by_category}
        assert cats == {"East", "West"}

    def test_trend_improving(self):
        analyzer = ForecastAnalyzer(
            actuals=[100, 100, 100, 100],
            forecasts=[130, 125, 110, 102],
            periods=["Q1", "Q2", "Q3", "Q4"],
        )
        report = analyzer.analyze()
        assert len(report.trend) == 4
        assert report.trend_direction == "improving"

    def test_trend_degrading(self):
        analyzer = ForecastAnalyzer(
            actuals=[100, 100, 100, 100],
            forecasts=[102, 110, 125, 130],
            periods=["Q1", "Q2", "Q3", "Q4"],
        )
        report = analyzer.analyze()
        assert report.trend_direction == "degrading"

    def test_trend_stable(self):
        analyzer = ForecastAnalyzer(
            actuals=[100, 100],
            forecasts=[110, 110],
            periods=["Q1", "Q2"],
        )
        report = analyzer.analyze()
        assert report.trend_direction == "stable"

    def test_single_period_no_trend(self):
        analyzer = ForecastAnalyzer(
            actuals=[100],
            forecasts=[110],
            periods=["Q1"],
        )
        report = analyzer.analyze()
        assert report.trend_direction is None

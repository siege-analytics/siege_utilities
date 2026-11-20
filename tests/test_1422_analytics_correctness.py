"""Offline regressions for the seven statistical defects in issue #1422."""

from datetime import datetime, timedelta
from decimal import Decimal
from fractions import Fraction
import logging
import math
import socket

import numpy as np
import pytest

from siege_utilities.analytics.comparison import ComparativeAnalyzer, DimensionScore
from siege_utilities.analytics.forecast import ForecastAnalyzer
from siege_utilities.analytics.pipeline import PipelineAnalyzer, PipelineItem
from siege_utilities.analytics.pricing import analyze_price_sensitivity
from siege_utilities.analytics.risk import (
    RiskAnalyzer, RiskSignal, RiskTier, RiskTierConfig, SignalType,
)
from siege_utilities.analytics.scoring import Dimension, HealthScorer


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def blocked(*args, **kwargs):
        pytest.fail("Analytics regressions must not access the network")

    monkeypatch.setattr(socket.socket, "connect", blocked)
    monkeypatch.setattr(socket.socket, "connect_ex", blocked)
    monkeypatch.setattr(socket, "create_connection", blocked)
    monkeypatch.setattr(socket, "getaddrinfo", blocked)


@pytest.mark.parametrize("earlier_count,expected", [(1, 5.0), (0, None)])
def test_stage_ratios_describe_independent_counts(earlier_count, expected):
    now = datetime(2026, 1, 31)
    items = [
        PipelineItem(f"early-{i}", "early", 1, now)
        for i in range(earlier_count)
    ] + [PipelineItem(f"late-{i}", "late", 1, now) for i in range(5)]
    report = PipelineAnalyzer(["early", "late"]).analyze(items, as_of=now)

    ratio = report.stage_ratios[0]
    assert ratio.ratio == expected
    assert (ratio.from_count, ratio.to_count) == (earlier_count, 5)
    assert (ratio.from_stage, ratio.to_stage) == ("early", "late")
    assert not hasattr(report, "conversions")


@pytest.mark.parametrize("count", [1, 2])
@pytest.mark.parametrize("bound", [10.0, 30.0])
def test_aging_alerts_work_for_small_samples(count, bound):
    now = datetime(2026, 1, 31)
    items = [PipelineItem("overdue", "review", 1, now - timedelta(days=bound + 1))]
    if count == 2:
        items.append(PipelineItem("at-bound", "review", 1, now - timedelta(days=bound)))
    analyzer = PipelineAnalyzer(["review"], aging_threshold=bound)
    report = analyzer.analyze(items, as_of=now)

    assert report.velocity[0].aging_items == ["overdue"]


def test_default_aging_threshold_is_an_exclusive_30_day_limit():
    """The default flags items older than 30 days; exactly 30.0 is not flagged (pipeline uses ``d > limit``)."""
    now = datetime(2026, 1, 31)
    items = [
        PipelineItem("under", "review", 1, now - timedelta(days=29.9)),
        PipelineItem("at-limit", "review", 1, now - timedelta(days=30.0)),
        PipelineItem("over", "review", 1, now - timedelta(days=30.1)),
    ]
    report = PipelineAnalyzer(["review"]).analyze(items, as_of=now)

    assert report.velocity[0].aging_items == ["over"]


@pytest.mark.parametrize("missing", [float("nan"), None, float("inf")])
@pytest.mark.parametrize("missing_side", ["actual", "forecast"])
def test_missing_forecast_data_is_insufficient(missing, missing_side):
    actuals = [100.0, missing if missing_side == "actual" else 100.0]
    forecasts = [110.0, missing if missing_side == "forecast" else 100.0]
    report = ForecastAnalyzer(
        actuals, forecasts, categories=["valid", "missing"], periods=["Q1", "Q2"],
    ).analyze()

    assert report.overall.grade == "Insufficient data"
    assert report.overall.bias_direction == "insufficient-data"
    assert report.overall.mape is None
    assert report.overall.bias is None
    assert report.overall.n_observations == 2
    assert report.overall.n_excluded == 1
    missing_category = next(c for c in report.by_category if c.category == "missing")
    assert missing_category.accuracy.grade == "Insufficient data"
    assert [point.period for point in report.trend] == ["Q1"]
    assert report.trend_direction is None


@pytest.mark.parametrize("middle,direction", [([60, 0], "improving"), ([0, 60], "degrading")])
def test_trend_sorts_periods_and_fits_middle_observations(middle, direction):
    # Equal endpoints would look stable; the middle periods determine the fit.
    errors = [10, *middle, 10]

    def analyze(order):
        return ForecastAnalyzer(
            actuals=[100.0] * 4,
            forecasts=[100.0 + errors[i] for i in order],
            periods=[f"2026-Q{i + 1}" for i in order],
        ).analyze()

    ordered = analyze([0, 1, 2, 3])
    shuffled = analyze([2, 0, 3, 1])
    assert ordered.trend_direction == shuffled.trend_direction == direction
    assert ordered.trend == shuffled.trend
    assert [point.period for point in shuffled.trend] == [
        "2026-Q1", "2026-Q2", "2026-Q3", "2026-Q4",
    ]


def _exact_fitted_change(mapes):
    """OLS fitted change in exact rational arithmetic, for comparison."""
    xs = [Fraction(i) for i in range(len(mapes))]
    ys = [Fraction(mape) for mape in mapes]
    mean_x = sum(xs) / len(xs)
    mean_y = sum(ys) / len(ys)
    slope = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys)) / sum(
        (x - mean_x) ** 2 for x in xs
    )
    return slope * (len(mapes) - 1)


@pytest.mark.parametrize("forecasts,direction", [
    ([0.8, 1.1], "degrading"),
    ([1.1, 0.8], "improving"),
    ([0.5, 0.8, 1.1], "degrading"),
    ([1.1, 0.8, 0.5], "improving"),
    # MAPEs [0, 0, 1.5e308, 1.5e308]: the exact fitted change, 1.8e308, is
    # itself above the largest float.
    ([1e-306, 1e-306, 1.5, 1.5], "degrading"),
    ([1.5, 1.5, 1e-306, 1e-306], "improving"),
])
def test_trend_direction_survives_extreme_finite_mapes(forecasts, direction):
    # Tiny actuals give finite period MAPEs near the largest float, so naive
    # sums inside the OLS fit overflow even though every input is finite.
    actuals = [1e-306] * len(forecasts)
    report = ForecastAnalyzer(
        actuals, forecasts, periods=[f"2026-{i + 1:02}" for i in range(len(forecasts))],
    ).analyze()

    mapes = [point.mape for point in report.trend]
    assert len(mapes) == len(forecasts)
    assert all(math.isfinite(mape) for mape in mapes)
    exact = _exact_fitted_change(mapes)
    assert (exact > 1) if direction == "degrading" else (exact < -1)
    assert report.trend_direction == direction


@pytest.mark.parametrize("large", [float(2**60), float(2**500), float(2**1000)])
@pytest.mark.parametrize("middle,direction", [
    ([110.0, 100.0], "improving"),
    ([100.0, 110.0], "degrading"),
])
def test_small_middle_periods_survive_a_large_mean(large, middle, direction):
    # MAPEs [M, 10, 0, M] (or [M, 0, 10, M]): the fitted change is exactly
    # -3 (or +3) points, but a float fit centred on a mean near M/2 rounds
    # 10 - mean and 0 - mean to the same value and loses the middle periods.
    report = ForecastAnalyzer(
        actuals=[100.0] * 4,
        forecasts=[large, *middle, large],
        periods=["Q1", "Q2", "Q3", "Q4"],
    ).analyze()

    mapes = [point.mape for point in report.trend]
    assert len(mapes) == 4 and all(math.isfinite(mape) for mape in mapes)
    assert mapes[1:3] == ([10.0, 0.0] if direction == "improving" else [0.0, 10.0])
    assert _exact_fitted_change(mapes) == (-3 if direction == "improving" else 3)
    assert report.trend_direction == direction


@pytest.mark.parametrize("dtype", [
    np.float16, np.float32, np.float64, np.longdouble, float, Decimal, Fraction,
], ids=[
    "float16", "float32", "float64", "longdouble", "python-float", "decimal",
    "fraction",
])
@pytest.mark.parametrize("last,direction", [(111, "stable"), (112, "degrading")])
def test_trend_accepts_numpy_float_mapes(dtype, last, direction):
    # NumPy keeps the input dtype through the MAPE arithmetic, so the trend
    # fit sees float16/float32/longdouble scalars, which Fraction() rejects.
    # float64, Python float, Decimal and Fraction inputs are controls.
    report = ForecastAnalyzer(
        actuals=[dtype(100), dtype(100)],
        forecasts=[dtype(110), dtype(last)],
        periods=["Q1", "Q2"],
    ).analyze()

    assert [float(point.mape) for point in report.trend] == [10.0, last - 100.0]
    assert report.trend_direction == direction


@pytest.mark.parametrize("mapes,direction", [
    ([0.01, 1.01], "stable"),
    ([0.1, 1.1], "stable"),
    ([0.3, 1.3], "stable"),
    ([1.01, 0.01], "stable"),
    ([1.1, 0.1], "stable"),
    ([1.3, 0.3], "stable"),
    ([0.1, 1.11], "degrading"),
    ([1.11, 0.1], "improving"),
])
def test_trend_band_uses_the_reported_two_decimal_mapes(mapes, direction):
    # The reported MAPEs differ by exactly 1.00, which is stable. Their
    # binary floats differ by slightly more than 1 (Fraction(1.1) -
    # Fraction(0.1) exceeds 1 by about 8e-17), so the band must be applied
    # to the reported decimals, not the binary values.
    report = ForecastAnalyzer(
        actuals=[100.0, 100.0],
        forecasts=[100.0 + mape for mape in mapes],
        periods=["2026-01", "2026-02"],
    ).analyze()

    assert [point.mape for point in report.trend] == mapes
    assert report.trend_direction == direction


@pytest.mark.parametrize("errors,direction", [
    ([10.0, 11.0], "stable"),
    ([10.0, 11.01], "degrading"),
    ([11.0, 10.0], "stable"),
    ([11.01, 10.0], "improving"),
])
def test_trend_threshold_is_exactly_one_point(errors, direction):
    # A fitted change of exactly 1.0 point is stable; 1.01 is not.
    report = ForecastAnalyzer(
        actuals=[100.0, 100.0],
        forecasts=[100.0 + error for error in errors],
        periods=["2026-01", "2026-02"],
    ).analyze()

    assert [point.mape for point in report.trend] == errors
    assert report.trend_direction == direction


def test_trend_skips_a_period_whose_mape_overflows(caplog):
    # 1e10 / 1e-306 overflows to inf, so 2026-02 has no finite MAPE; the fit
    # uses the two finite periods (10% then 20%).
    logger_name = "siege_utilities.analytics.forecast"
    with caplog.at_level(logging.WARNING, logger=logger_name):
        report = ForecastAnalyzer(
            actuals=[100.0, 1e-306, 100.0],
            forecasts=[110.0, 1e10, 120.0],
            periods=["2026-01", "2026-02", "2026-03"],
        ).analyze()

    assert [point.period for point in report.trend] == ["2026-01", "2026-03"]
    assert report.trend_direction == "degrading"
    assert "Period '2026-02' skipped: MAPE or bias is not finite" in [
        record.getMessage() for record in caplog.records
        if record.name == logger_name and record.levelno == logging.WARNING
    ]


@pytest.mark.parametrize("kind", ["health", "risk"])
def test_tiers_use_the_reported_rounded_composite(kind):
    if kind == "health":
        result = HealthScorer([Dimension("signal", 100)]).score(
            "entity", {"signal": 69.999},
        )
        expected_tier = "Green"
    else:
        result = RiskAnalyzer(
            [RiskSignal("signal", SignalType.THRESHOLD, 100)],
            tier_config=RiskTierConfig(high_min=70),
            interventions={RiskTier.HIGH: "Review"},
        ).assess("entity", {"signal": 69.999})
        expected_tier = RiskTier.HIGH

    assert result.composite_score == 70.0
    assert result.tier == expected_tier
    if kind == "risk":
        assert result.intervention == "Review"


@pytest.mark.parametrize("weights,error", [
    ({"quality": -1, "speed": 2}, "non-negative"),
    ({"quality": 0, "speed": 0}, "positive"),
    ({"quality": float("nan"), "speed": 1}, "finite"),
    ({"quality": float("inf"), "speed": 1}, "finite"),
    ({"quality": 3, "speed": 1}, None),
    ({"quality": 75, "speed": 25}, None),
])
def test_comparison_weights_are_validated_and_normalized(weights, error):
    if error:
        with pytest.raises(ValueError, match=error):
            ComparativeAnalyzer(["quality", "speed"], weights=weights)
        return

    result = ComparativeAnalyzer(["quality", "speed"], weights=weights).compare({
        "quality-first": {
            "quality": DimensionScore(5, "Quality benchmark"),
            "speed": DimensionScore(1, "Speed benchmark"),
        },
        "speed-first": {
            "quality": DimensionScore(1, "Quality benchmark"),
            "speed": DimensionScore(5, "Speed benchmark"),
        },
    })
    assert result.weighted_totals == {"quality-first": 4.0, "speed-first": 2.0}


@pytest.mark.parametrize("bad_response", [(30, 20, 50, 70), (10, 60, 50, 70), (10, 20, 80, 70)])
def test_pricing_rejects_inconsistent_response_order(bad_response):
    # Keep a valid respondent first so the error must identify the later row.
    columns = list(zip((10, 20, 50, 70), bad_response))
    with pytest.raises(ValueError, match=r"response.*1.*too_cheap <= cheap <= expensive <= too_expensive"):
        analyze_price_sensitivity(*columns, min_sample=1)

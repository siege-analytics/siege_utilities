"""Offline regressions for the seven statistical defects in issue #1422."""

from datetime import datetime, timedelta
import socket

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

"""
Forecast accuracy measurement.

MAPE calculation with per-category breakdown, bias detection, and
accuracy trend analysis.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ForecastAccuracy:
    """Result of a forecast accuracy calculation."""

    mape: float
    bias: float
    bias_direction: str
    grade: str
    n_observations: int
    n_excluded: int


@dataclass(frozen=True)
class CategoryBreakdown:
    """Per-category forecast accuracy."""

    category: str
    accuracy: ForecastAccuracy


@dataclass(frozen=True)
class TrendPoint:
    """Accuracy at a single time period."""

    period: str
    mape: float
    bias: float


@dataclass(frozen=True)
class ForecastReport:
    """Complete forecast accuracy report."""

    overall: ForecastAccuracy
    by_category: list[CategoryBreakdown]
    trend: list[TrendPoint]
    trend_direction: str | None


def _grade_mape(mape: float) -> str:
    if mape < 10:
        return "Excellent"
    if mape < 15:
        return "Good"
    if mape < 25:
        return "Fair"
    return "Poor"


def _compute_accuracy(
    actuals: list[float],
    forecasts: list[float],
) -> ForecastAccuracy:
    """Compute MAPE and bias from parallel lists.

    Observations where actual == 0 are excluded from MAPE
    (division by zero) but counted in n_excluded.
    """
    if len(actuals) != len(forecasts):
        raise ValueError(
            f"actuals and forecasts must have same length, "
            f"got {len(actuals)} and {len(forecasts)}"
        )
    if not actuals:
        raise ValueError("At least one observation is required")

    errors = []
    biases = []
    excluded = 0

    for actual, forecast in zip(actuals, forecasts):
        if actual == 0:
            excluded += 1
            continue
        pct_error = abs(actual - forecast) / abs(actual)
        errors.append(pct_error)
        biases.append((forecast - actual) / abs(actual))

    if not errors:
        raise ValueError(
            "All observations have actual=0; MAPE is undefined"
        )

    mape = sum(errors) / len(errors) * 100
    bias = sum(biases) / len(biases) * 100

    if bias > 1.0:
        bias_direction = "over-forecasting"
    elif bias < -1.0:
        bias_direction = "under-forecasting"
    else:
        bias_direction = "neutral"

    return ForecastAccuracy(
        mape=round(mape, 2),
        bias=round(bias, 2),
        bias_direction=bias_direction,
        grade=_grade_mape(mape),
        n_observations=len(actuals),
        n_excluded=excluded,
    )


class ForecastAnalyzer:
    """Forecast accuracy engine.

    Parameters
    ----------
    actuals : list[float]
        Actual observed values.
    forecasts : list[float]
        Forecasted values (same length as actuals).
    categories : list[str] | None
        Optional category labels for per-category breakdown.
    periods : list[str] | None
        Optional time period labels for trend analysis.

    Raises
    ------
    ValueError
        If inputs have mismatched lengths or are empty.
    """

    def __init__(
        self,
        actuals: list[float],
        forecasts: list[float],
        categories: list[str] | None = None,
        periods: list[str] | None = None,
    ) -> None:
        if len(actuals) != len(forecasts):
            raise ValueError(
                f"actuals and forecasts must have same length, "
                f"got {len(actuals)} and {len(forecasts)}"
            )
        if not actuals:
            raise ValueError("At least one observation is required")
        if categories is not None and len(categories) != len(actuals):
            raise ValueError(
                f"categories must have same length as actuals, "
                f"got {len(categories)} and {len(actuals)}"
            )
        if periods is not None and len(periods) != len(actuals):
            raise ValueError(
                f"periods must have same length as actuals, "
                f"got {len(periods)} and {len(actuals)}"
            )

        self._actuals = list(actuals)
        self._forecasts = list(forecasts)
        self._categories = list(categories) if categories else None
        self._periods = list(periods) if periods else None

        logger.info(
            "ForecastAnalyzer initialized with %d observations",
            len(self._actuals),
        )

    def analyze(self) -> ForecastReport:
        """Run full forecast accuracy analysis.

        Returns
        -------
        ForecastReport
        """
        overall = _compute_accuracy(self._actuals, self._forecasts)

        by_category = self._category_breakdown()
        trend, trend_direction = self._trend_analysis()

        report = ForecastReport(
            overall=overall,
            by_category=by_category,
            trend=trend,
            trend_direction=trend_direction,
        )

        logger.info(
            "Forecast analysis: MAPE=%.1f%% (%s), bias=%.1f%% (%s)",
            overall.mape,
            overall.grade,
            overall.bias,
            overall.bias_direction,
        )

        return report

    def _category_breakdown(self) -> list[CategoryBreakdown]:
        if self._categories is None:
            return []

        groups: dict[str, tuple[list[float], list[float]]] = {}
        for actual, forecast, cat in zip(
            self._actuals, self._forecasts, self._categories
        ):
            if cat not in groups:
                groups[cat] = ([], [])
            groups[cat][0].append(actual)
            groups[cat][1].append(forecast)

        results = []
        for cat in sorted(groups.keys()):
            cat_actuals, cat_forecasts = groups[cat]
            try:
                accuracy = _compute_accuracy(cat_actuals, cat_forecasts)
                results.append(CategoryBreakdown(category=cat, accuracy=accuracy))
            except ValueError:
                logger.warning(
                    "Category %r skipped: all actuals are zero", cat
                )

        return results

    def _trend_analysis(self) -> tuple[list[TrendPoint], str | None]:
        if self._periods is None:
            return [], None

        groups: dict[str, tuple[list[float], list[float]]] = {}
        period_order: list[str] = []
        for actual, forecast, period in zip(
            self._actuals, self._forecasts, self._periods
        ):
            if period not in groups:
                groups[period] = ([], [])
                period_order.append(period)
            groups[period][0].append(actual)
            groups[period][1].append(forecast)

        points = []
        for period in period_order:
            p_actuals, p_forecasts = groups[period]
            try:
                acc = _compute_accuracy(p_actuals, p_forecasts)
                points.append(TrendPoint(
                    period=period,
                    mape=acc.mape,
                    bias=acc.bias,
                ))
            except ValueError:
                logger.warning(
                    "Period %r skipped: all actuals are zero", period
                )

        if len(points) < 2:
            return points, None

        first_mape = points[0].mape
        last_mape = points[-1].mape
        if last_mape < first_mape - 1.0:
            direction = "improving"
        elif last_mape > first_mape + 1.0:
            direction = "degrading"
        else:
            direction = "stable"

        return points, direction

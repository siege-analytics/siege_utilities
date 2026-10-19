"""
Forecast accuracy measurement.

MAPE calculation with per-category breakdown, bias detection, and
accuracy trend analysis.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ForecastAccuracy:
    """Accuracy, or None metrics and an insufficient-data label for missing data.

    n_observations counts all input pairs. n_excluded counts pairs with a
    zero actual or a missing/non-finite value.
    """

    mape: float | None
    bias: float | None
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


def _grade_mape(mape: float | None) -> str:
    if mape is None or not math.isfinite(mape):
        return "Insufficient data"
    if mape < 10:
        return "Excellent"
    if mape < 15:
        return "Good"
    if mape < 25:
        return "Fair"
    return "Poor"


def _compute_accuracy(
    actuals: list[float | None],
    forecasts: list[float | None],
) -> ForecastAccuracy:
    """Compute MAPE and bias from parallel lists.

    Observations where actual == 0 are excluded from MAPE
    (division by zero) but counted in n_excluded. If either series contains
    None or a non-finite value, the entire group's result is insufficient
    data: MAPE and bias are None, grade is "Insufficient data", and
    bias_direction is "insufficient-data". Partial data is not graded.
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
    incomplete = False

    for actual, forecast in zip(actuals, forecasts):
        if (
            actual is None or forecast is None
            or not math.isfinite(actual) or not math.isfinite(forecast)
        ):
            incomplete = True
            excluded += 1
            continue
        if actual == 0:
            excluded += 1
            continue
        pct_error = abs(actual - forecast) / abs(actual)
        errors.append(pct_error)
        biases.append((forecast - actual) / abs(actual))

    if incomplete:
        return ForecastAccuracy(
            mape=None,
            bias=None,
            bias_direction="insufficient-data",
            grade="Insufficient data",
            n_observations=len(actuals),
            n_excluded=excluded,
        )

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
    actuals : list[float | None]
        Actual observed values. Missing or non-finite values produce an
        insufficient-data result for the overall series and affected groups.
    forecasts : list[float | None]
        Forecasted values (same length as actuals), with the same missing-data
        policy as actuals.
    categories : list[str] | None
        Optional category labels for per-category breakdown.
    periods : list[str] | None
        Optional sortable time period labels (e.g. ISO dates or YYYY-Qn).
        Labels are sorted lexicographically and valid periods are treated as
        equally spaced. Direction uses an OLS fit of all period MAPEs:
        a fitted change below -1 percentage point is improving, above +1
        is degrading, otherwise stable. Zero-only and insufficient-data
        periods are omitted; fewer than two valid periods gives no direction.

    Raises
    ------
    ValueError
        If inputs have mismatched lengths or are empty.
    """

    def __init__(
        self,
        actuals: list[float | None],
        forecasts: list[float | None],
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
            "Forecast analysis: MAPE=%s (%s), bias=%s (%s)",
            overall.mape,
            overall.grade,
            overall.bias,
            overall.bias_direction,
        )

        return report

    def _category_breakdown(self) -> list[CategoryBreakdown]:
        if self._categories is None:
            return []

        groups: dict[str, tuple[list[float | None], list[float | None]]] = {}
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

        groups: dict[str, tuple[list[float | None], list[float | None]]] = {}
        for actual, forecast, period in zip(
            self._actuals, self._forecasts, self._periods
        ):
            if period not in groups:
                groups[period] = ([], [])
            groups[period][0].append(actual)
            groups[period][1].append(forecast)

        points = []
        for period in sorted(groups):
            p_actuals, p_forecasts = groups[period]
            try:
                acc = _compute_accuracy(p_actuals, p_forecasts)
                if acc.mape is None or acc.bias is None:
                    logger.warning("Period %r skipped: insufficient data", period)
                    continue
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

        # OLS slope across every valid period, using equally spaced indices.
        mean_x = (len(points) - 1) / 2
        mean_y = sum(point.mape for point in points) / len(points)
        slope = sum(
            (i - mean_x) * (point.mape - mean_y)
            for i, point in enumerate(points)
        ) / sum((i - mean_x) ** 2 for i in range(len(points)))
        fitted_change = slope * (len(points) - 1)
        if fitted_change < -1.0:
            direction = "improving"
        elif fitted_change > 1.0:
            direction = "degrading"
        else:
            direction = "stable"

        return points, direction

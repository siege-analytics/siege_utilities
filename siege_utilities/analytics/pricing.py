"""
Van Westendorp Price Sensitivity Meter.

Four-question survey analysis for optimal price range determination
via cumulative frequency intersections.
"""

from __future__ import annotations

import logging
import warnings
from dataclasses import dataclass
from typing import Sequence

import numpy as np

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PricePoint:
    """An intersection point on the price sensitivity curve."""

    label: str
    price: float
    description: str


@dataclass(frozen=True)
class PricingCorridor:
    """Van Westendorp pricing corridor result.

    Attributes
    ----------
    pmc : PricePoint
        Point of Marginal Cheapness (too cheap ∩ not cheap).
    pme : PricePoint
        Point of Marginal Expensiveness (too expensive ∩ not expensive).
    opp : PricePoint
        Optimal Price Point (too cheap ∩ too expensive).
    idp : PricePoint
        Indifference Price Point (cheap ∩ expensive).
    price_grid : list[float]
        Sorted price points used for cumulative distributions.
    sample_size : int
        Number of survey responses.
    """

    pmc: PricePoint | None
    pme: PricePoint | None
    opp: PricePoint | None
    idp: PricePoint | None
    price_grid: list[float]
    sample_size: int

    @property
    def acceptable_range(self) -> tuple[float, float] | None:
        """Return (PMC, PME) range or None if either endpoint is missing."""
        if self.pmc is not None and self.pme is not None:
            return (self.pmc.price, self.pme.price)
        return None


def _validate_responses(
    too_cheap: Sequence[float],
    cheap: Sequence[float],
    expensive: Sequence[float],
    too_expensive: Sequence[float],
    min_sample: int,
) -> int:
    """Validate survey responses and return sample size."""
    lengths = {
        len(too_cheap), len(cheap), len(expensive), len(too_expensive),
    }
    if len(lengths) > 1:
        raise ValueError(
            f"All four questions must have the same number of responses. "
            f"Got lengths: too_cheap={len(too_cheap)}, cheap={len(cheap)}, "
            f"expensive={len(expensive)}, too_expensive={len(too_expensive)}"
        )

    n = len(too_cheap)
    if n == 0:
        raise ValueError("Survey responses must not be empty")

    all_vals = list(too_cheap) + list(cheap) + list(expensive) + list(too_expensive)
    if any(not np.isfinite(v) for v in all_vals):
        raise ValueError("All prices must be finite (no NaN or Inf)")
    if any(v < 0 for v in all_vals):
        raise ValueError("All prices must be non-negative")

    if n < min_sample:
        warnings.warn(
            f"Only {n} responses (minimum recommended: {min_sample}). "
            f"Intersection points may be unreliable.",
            UserWarning,
            stacklevel=3,
        )

    return n


def _build_cumulative(
    responses: Sequence[float],
    price_grid: np.ndarray,
    ascending: bool,
) -> np.ndarray:
    """Build cumulative frequency distribution over a price grid.

    Parameters
    ----------
    responses : sequence of float
        Raw survey prices for one question.
    price_grid : ndarray
        Sorted price points to evaluate.
    ascending : bool
        If True, cumulative proportion <= price (e.g. "too cheap").
        If False, cumulative proportion >= price (e.g. "too expensive").

    Returns
    -------
    ndarray
        Cumulative proportions at each grid point.
    """
    arr = np.array(responses, dtype=float)
    n = len(arr)
    result = np.empty(len(price_grid), dtype=float)
    for i, p in enumerate(price_grid):
        if ascending:
            result[i] = np.sum(arr <= p) / n
        else:
            result[i] = np.sum(arr >= p) / n
    return result


def _check_monotonicity(
    curve: np.ndarray,
    label: str,
    ascending: bool,
) -> None:
    """Raise ValueError if cumulative distribution is non-monotonic."""
    diffs = np.diff(curve)
    if ascending:
        if np.any(diffs < -1e-10):
            raise ValueError(
                f"Non-monotonic cumulative distribution for '{label}'. "
                f"This indicates data quality issues in the survey responses."
            )
    else:
        if np.any(diffs > 1e-10):
            raise ValueError(
                f"Non-monotonic cumulative distribution for '{label}'. "
                f"This indicates data quality issues in the survey responses."
            )


def _find_intersection(
    grid: np.ndarray,
    curve_a: np.ndarray,
    curve_b: np.ndarray,
) -> float | None:
    """Find the price where two curves intersect via linear interpolation."""
    diff = curve_a - curve_b
    sign_changes = np.where(np.diff(np.sign(diff)))[0]

    if len(sign_changes) == 0:
        return None

    idx = sign_changes[0]
    x0, x1 = grid[idx], grid[idx + 1]
    d0, d1 = diff[idx], diff[idx + 1]

    if abs(d1 - d0) < 1e-15:
        return float((x0 + x1) / 2)

    t = -d0 / (d1 - d0)
    return float(x0 + t * (x1 - x0))


def analyze_price_sensitivity(
    too_cheap: Sequence[float],
    cheap: Sequence[float],
    expensive: Sequence[float],
    too_expensive: Sequence[float],
    *,
    min_sample: int = 10,
    grid_points: int = 200,
) -> PricingCorridor:
    """Run Van Westendorp Price Sensitivity Meter analysis.

    Parameters
    ----------
    too_cheap : sequence of float
        Prices below which the product is perceived as too cheap.
    cheap : sequence of float
        Prices at which the product is perceived as cheap/bargain.
    expensive : sequence of float
        Prices at which the product is perceived as expensive.
    too_expensive : sequence of float
        Prices above which the product is perceived as too expensive.
    min_sample : int
        Minimum recommended sample size (warn if fewer).
    grid_points : int
        Number of points in the price grid for interpolation.

    Returns
    -------
    PricingCorridor
        Intersection points and corridor data.

    Raises
    ------
    ValueError
        If responses are empty, unequal length, contain negatives,
        or have non-monotonic distributions.
    """
    if min_sample < 1:
        raise ValueError(
            f"min_sample must be at least 1, got {min_sample}"
        )
    if grid_points < 2:
        raise ValueError(
            f"grid_points must be at least 2, got {grid_points}"
        )

    n = _validate_responses(
        too_cheap, cheap, expensive, too_expensive, min_sample,
    )

    all_prices = np.concatenate([
        too_cheap, cheap, expensive, too_expensive,
    ])
    grid = np.linspace(
        float(np.min(all_prices)),
        float(np.max(all_prices)),
        grid_points,
    )

    cum_too_cheap = _build_cumulative(too_cheap, grid, ascending=True)
    cum_cheap = _build_cumulative(cheap, grid, ascending=True)
    cum_expensive = _build_cumulative(expensive, grid, ascending=False)
    cum_too_expensive = _build_cumulative(too_expensive, grid, ascending=False)

    _check_monotonicity(cum_too_cheap, "too_cheap", ascending=True)
    _check_monotonicity(cum_cheap, "cheap", ascending=True)
    _check_monotonicity(cum_expensive, "expensive", ascending=False)
    _check_monotonicity(cum_too_expensive, "too_expensive", ascending=False)

    not_cheap = 1.0 - cum_cheap
    not_expensive = 1.0 - cum_expensive

    pmc_price = _find_intersection(grid, cum_too_cheap, not_cheap)
    pme_price = _find_intersection(grid, cum_too_expensive, not_expensive)
    opp_price = _find_intersection(grid, cum_too_cheap, cum_too_expensive)
    idp_price = _find_intersection(grid, cum_cheap, cum_expensive)

    missing = []
    if pmc_price is None:
        missing.append("PMC")
    if pme_price is None:
        missing.append("PME")
    if opp_price is None:
        missing.append("OPP")
    if idp_price is None:
        missing.append("IDP")

    if missing:
        warnings.warn(
            f"Could not find intersection(s): {', '.join(missing)}. "
            f"Price range may extend beyond survey data bounds "
            f"[{float(grid[0]):.2f}, {float(grid[-1]):.2f}].",
            UserWarning,
            stacklevel=2,
        )

    def _point(label: str, price: float | None, desc: str) -> PricePoint | None:
        if price is None:
            return None
        return PricePoint(label=label, price=round(price, 2), description=desc)

    corridor = PricingCorridor(
        pmc=_point("PMC", pmc_price, "Point of Marginal Cheapness"),
        pme=_point("PME", pme_price, "Point of Marginal Expensiveness"),
        opp=_point("OPP", opp_price, "Optimal Price Point"),
        idp=_point("IDP", idp_price, "Indifference Price Point"),
        price_grid=grid.tolist(),
        sample_size=n,
    )

    logger.info(
        "Van Westendorp analysis: n=%d, PMC=%s, OPP=%s, IDP=%s, PME=%s",
        n,
        f"${pmc_price:.2f}" if pmc_price is not None else "N/A",
        f"${opp_price:.2f}" if opp_price is not None else "N/A",
        f"${idp_price:.2f}" if idp_price is not None else "N/A",
        f"${pme_price:.2f}" if pme_price is not None else "N/A",
    )

    return corridor

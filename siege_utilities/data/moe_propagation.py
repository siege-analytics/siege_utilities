"""ACS Margin of Error propagation through derived estimates.

Implements the Census Bureau's recommended methods for propagating
margins of error through arithmetic operations on ACS estimates:

- **Sum/difference**: root-sum-of-squares of component MOEs
- **Proportion**: delta method with bounded output
- **Ratio**: delta method for ratios of non-nested estimates
- **CV threshold**: flag unreliable estimates by coefficient of variation

Reference:
    U.S. Census Bureau, "Understanding and Using ACS Data",
    Appendix A — Calculating Margins of Error.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional, Sequence


Z_90 = 1.645  # z-score for 90% confidence (ACS default)


@dataclass
class Estimate:
    """An ACS estimate with its margin of error at 90% confidence."""

    value: float
    moe: float

    @property
    def se(self) -> float:
        """Standard error (MOE / 1.645)."""
        return self.moe / Z_90

    @property
    def cv(self) -> float:
        """Coefficient of variation (SE / |estimate|), as a proportion."""
        if self.value == 0:
            return float("inf")
        return abs(self.se / self.value)

    @property
    def cv_pct(self) -> float:
        """Coefficient of variation as a percentage."""
        return self.cv * 100

    def is_reliable(self, cv_threshold: float = 0.40) -> bool:
        """Return ``True`` if CV is below *cv_threshold* (default 40%)."""
        return self.cv < cv_threshold

    def confidence_interval(self, confidence: float = 0.90) -> tuple[float, float]:
        """Return (lower, upper) bounds at the given confidence level.

        Parameters
        ----------
        confidence : float
            Confidence level.  Only 0.90 (default, uses stored MOE directly)
            and 0.95 are supported.
        """
        if confidence == 0.90:
            half = self.moe
        elif confidence == 0.95:
            half = self.se * 1.96
        else:
            raise ValueError(f"Unsupported confidence level: {confidence}")
        return (self.value - half, self.value + half)


# ---------------------------------------------------------------------------
# Propagation functions
# ---------------------------------------------------------------------------

def moe_sum(estimates: Sequence[Estimate]) -> Estimate:
    """Propagate MOE through a sum of independent ACS estimates.

    MOE_sum = sqrt(sum(MOE_i^2))

    Parameters
    ----------
    estimates : sequence of Estimate
        The addends.

    Returns
    -------
    Estimate
        Combined estimate with propagated MOE.
    """
    total = sum(e.value for e in estimates)
    moe = math.sqrt(sum(e.moe ** 2 for e in estimates))
    return Estimate(value=total, moe=moe)


def moe_difference(a: Estimate, b: Estimate) -> Estimate:
    """Propagate MOE through the difference *a - b*.

    Uses the same root-sum-of-squares formula as :func:`moe_sum`.
    """
    return Estimate(
        value=a.value - b.value,
        moe=math.sqrt(a.moe ** 2 + b.moe ** 2),
    )


def moe_proportion(
    numerator: Estimate,
    denominator: Estimate,
) -> Estimate:
    """Propagate MOE for a proportion (numerator / denominator).

    Uses the Census Bureau's recommended formula for proportions where the
    numerator is a subset of the denominator:

        SE_p = sqrt(SE_num^2 - p^2 * SE_den^2) / denominator

    If the radicand is negative (which can happen with small samples), falls
    back to the conservative approximation:

        SE_p = sqrt(SE_num^2 + p^2 * SE_den^2) / denominator

    Parameters
    ----------
    numerator : Estimate
        Must be a subset of *denominator*.
    denominator : Estimate
        The total.

    Returns
    -------
    Estimate
        Proportion with propagated MOE, bounded to [0, 1].
    """
    if denominator.value == 0:
        return Estimate(value=0.0, moe=0.0)

    p = numerator.value / denominator.value

    se_num = numerator.se
    se_den = denominator.se

    radicand = se_num ** 2 - p ** 2 * se_den ** 2
    if radicand >= 0:
        se_p = math.sqrt(radicand) / denominator.value
    else:
        # Conservative fallback
        se_p = math.sqrt(se_num ** 2 + p ** 2 * se_den ** 2) / denominator.value

    moe_p = se_p * Z_90
    # Bound proportion to [0, 1]
    p_bounded = max(0.0, min(1.0, p))
    return Estimate(value=p_bounded, moe=moe_p)


def moe_ratio(
    numerator: Estimate,
    denominator: Estimate,
) -> Estimate:
    """Propagate MOE for a ratio of non-nested estimates.

    Uses the delta method:

        SE_r = sqrt(SE_num^2 + r^2 * SE_den^2) / denominator

    Parameters
    ----------
    numerator, denominator : Estimate
        Independent (non-nested) estimates.

    Returns
    -------
    Estimate
    """
    if denominator.value == 0:
        return Estimate(value=0.0, moe=0.0)

    r = numerator.value / denominator.value
    se_num = numerator.se
    se_den = denominator.se

    se_r = math.sqrt(se_num ** 2 + r ** 2 * se_den ** 2) / abs(denominator.value)
    return Estimate(value=r, moe=se_r * Z_90)


def moe_product(a: Estimate, b: Estimate) -> Estimate:
    """Propagate MOE through a product *a * b* (independent estimates).

    Uses the delta-method approximation:

        SE_ab = sqrt(a^2 * SE_b^2 + b^2 * SE_a^2)
    """
    se = math.sqrt(a.value ** 2 * b.se ** 2 + b.value ** 2 * a.se ** 2)
    return Estimate(value=a.value * b.value, moe=se * Z_90)


# ---------------------------------------------------------------------------
# Convenience helpers
# ---------------------------------------------------------------------------

def flag_unreliable(
    estimates: Sequence[Estimate],
    cv_threshold: float = 0.40,
) -> list[tuple[int, Estimate]]:
    """Return indices and Estimates that exceed *cv_threshold*.

    Parameters
    ----------
    estimates : sequence of Estimate
    cv_threshold : float
        Maximum acceptable CV (default 0.40 = 40%).

    Returns
    -------
    list of (index, Estimate)
    """
    return [(i, e) for i, e in enumerate(estimates) if not e.is_reliable(cv_threshold)]

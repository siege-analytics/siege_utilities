"""Tests for ACS Margin of Error propagation module."""

import math

import pytest

from siege_utilities.data.moe_propagation import (
    Estimate,
    flag_unreliable,
    moe_difference,
    moe_product,
    moe_proportion,
    moe_ratio,
    moe_sum,
)


# ---------------------------------------------------------------------------
# Estimate dataclass
# ---------------------------------------------------------------------------

class TestEstimate:

    def test_se(self):
        e = Estimate(value=1000, moe=164.5)
        assert abs(e.se - 100.0) < 0.1

    def test_cv(self):
        e = Estimate(value=1000, moe=164.5)
        assert abs(e.cv - 0.1) < 0.01

    def test_cv_pct(self):
        e = Estimate(value=1000, moe=164.5)
        assert abs(e.cv_pct - 10.0) < 0.5

    def test_cv_zero_value(self):
        e = Estimate(value=0, moe=10)
        assert e.cv == float("inf")

    def test_reliable(self):
        e = Estimate(value=1000, moe=100)
        assert e.is_reliable()

    def test_unreliable(self):
        e = Estimate(value=100, moe=500)
        assert not e.is_reliable()

    def test_confidence_interval_90(self):
        e = Estimate(value=1000, moe=100)
        lo, hi = e.confidence_interval(0.90)
        assert lo == 900
        assert hi == 1100

    def test_confidence_interval_95(self):
        e = Estimate(value=1000, moe=164.5)
        lo, hi = e.confidence_interval(0.95)
        # SE = 100, 95% CI = 1000 ± 196
        assert abs(lo - 804) < 1
        assert abs(hi - 1196) < 1

    def test_confidence_interval_bad_level(self):
        e = Estimate(value=1000, moe=100)
        with pytest.raises(ValueError, match="Unsupported"):
            e.confidence_interval(0.99)


# ---------------------------------------------------------------------------
# moe_sum
# ---------------------------------------------------------------------------

class TestMoeSum:

    def test_two_estimates(self):
        a = Estimate(value=100, moe=10)
        b = Estimate(value=200, moe=20)
        result = moe_sum([a, b])
        assert result.value == 300
        assert abs(result.moe - math.sqrt(10**2 + 20**2)) < 0.001

    def test_three_estimates(self):
        ests = [Estimate(value=100, moe=10) for _ in range(3)]
        result = moe_sum(ests)
        assert result.value == 300
        assert abs(result.moe - math.sqrt(3) * 10) < 0.001

    def test_single_estimate(self):
        e = Estimate(value=50, moe=5)
        result = moe_sum([e])
        assert result.value == 50
        assert result.moe == 5


# ---------------------------------------------------------------------------
# moe_difference
# ---------------------------------------------------------------------------

class TestMoeDifference:

    def test_basic(self):
        a = Estimate(value=300, moe=30)
        b = Estimate(value=100, moe=10)
        result = moe_difference(a, b)
        assert result.value == 200
        assert abs(result.moe - math.sqrt(30**2 + 10**2)) < 0.001


# ---------------------------------------------------------------------------
# moe_proportion
# ---------------------------------------------------------------------------

class TestMoeProportion:

    def test_half(self):
        num = Estimate(value=50, moe=10)
        den = Estimate(value=100, moe=15)
        result = moe_proportion(num, den)
        assert abs(result.value - 0.5) < 0.001
        assert result.moe > 0

    def test_bounded_to_01(self):
        # Numerator > denominator (unusual but possible)
        num = Estimate(value=110, moe=10)
        den = Estimate(value=100, moe=5)
        result = moe_proportion(num, den)
        assert result.value <= 1.0

    def test_zero_denominator(self):
        num = Estimate(value=50, moe=10)
        den = Estimate(value=0, moe=0)
        result = moe_proportion(num, den)
        assert result.value == 0.0
        assert result.moe == 0.0


# ---------------------------------------------------------------------------
# moe_ratio
# ---------------------------------------------------------------------------

class TestMoeRatio:

    def test_basic(self):
        a = Estimate(value=200, moe=20)
        b = Estimate(value=100, moe=10)
        result = moe_ratio(a, b)
        assert abs(result.value - 2.0) < 0.001
        assert result.moe > 0

    def test_zero_denominator(self):
        a = Estimate(value=200, moe=20)
        b = Estimate(value=0, moe=10)
        result = moe_ratio(a, b)
        assert result.value == 0.0


# ---------------------------------------------------------------------------
# moe_product
# ---------------------------------------------------------------------------

class TestMoeProduct:

    def test_basic(self):
        a = Estimate(value=10, moe=1)
        b = Estimate(value=20, moe=2)
        result = moe_product(a, b)
        assert result.value == 200
        assert result.moe > 0


# ---------------------------------------------------------------------------
# flag_unreliable
# ---------------------------------------------------------------------------

class TestFlagUnreliable:

    def test_none_flagged(self):
        ests = [Estimate(value=1000, moe=50) for _ in range(3)]
        flagged = flag_unreliable(ests)
        assert len(flagged) == 0

    def test_some_flagged(self):
        ests = [
            Estimate(value=1000, moe=50),   # CV ≈ 3% — reliable
            Estimate(value=10, moe=100),     # CV huge — unreliable
        ]
        flagged = flag_unreliable(ests)
        assert len(flagged) == 1
        assert flagged[0][0] == 1

    def test_custom_threshold(self):
        e = Estimate(value=100, moe=50)  # CV ≈ 30%
        flagged = flag_unreliable([e], cv_threshold=0.20)
        assert len(flagged) == 1
        flagged = flag_unreliable([e], cv_threshold=0.50)
        assert len(flagged) == 0

"""Tests for siege_utilities.data.statistics.cross_tabulation module."""

from __future__ import annotations

import pandas as pd
import pytest

from siege_utilities.data.statistics.cross_tabulation import (
    ChiSquareResult,
    CrossTabSpec,
    chi_square_test,
    contingency_table,
    moe_cross_tab,
    rate_table,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_df():
    """Simple dataset for cross-tabulation."""
    return pd.DataFrame({
        "race": ["White", "White", "Black", "Black", "Hispanic", "Hispanic"],
        "county": ["A", "B", "A", "B", "A", "B"],
        "population": [1000, 800, 500, 600, 300, 400],
    })


@pytest.fixture
def moe_df():
    """MOE data matching sample_df."""
    return pd.DataFrame({
        "race": ["White", "White", "Black", "Black", "Hispanic", "Hispanic"],
        "county": ["A", "B", "A", "B", "A", "B"],
        "population_moe": [50, 40, 30, 35, 20, 25],
    })


# ---------------------------------------------------------------------------
# contingency_table
# ---------------------------------------------------------------------------

class TestContingencyTable:

    def test_basic_counts(self):
        df = pd.DataFrame({
            "gender": ["M", "M", "F", "F", "M"],
            "color": ["red", "blue", "red", "blue", "red"],
        })
        ct = contingency_table(df, "gender", "color", margins=False)
        assert ct.loc["M", "red"] == 2
        assert ct.loc["M", "blue"] == 1
        assert ct.loc["F", "red"] == 1
        assert ct.loc["F", "blue"] == 1

    def test_sum_values(self, sample_df):
        ct = contingency_table(
            sample_df, "race", "county", value_var="population", margins=True,
        )
        assert ct.loc["White", "A"] == 1000
        assert ct.loc["Total", "Total"] == 3600

    def test_margins_totals(self, sample_df):
        ct = contingency_table(
            sample_df, "race", "county", value_var="population", margins=True,
        )
        assert ct.loc["Total", "A"] == 1800
        assert ct.loc["Total", "B"] == 1800

    def test_no_margins(self, sample_df):
        ct = contingency_table(
            sample_df, "race", "county", value_var="population", margins=False,
        )
        assert "Total" not in ct.index
        assert "Total" not in ct.columns

    def test_weighted(self):
        df = pd.DataFrame({
            "row": ["A", "B"],
            "col": ["X", "X"],
            "val": [10, 20],
            "wt": [2.0, 0.5],
        })
        ct = contingency_table(
            df, "row", "col", value_var="val", weight_var="wt", margins=False,
        )
        assert ct.loc["A", "X"] == 20.0  # 10 * 2
        assert ct.loc["B", "X"] == 10.0  # 20 * 0.5

    def test_mean_aggfunc(self, sample_df):
        ct = contingency_table(
            sample_df, "race", "county", value_var="population",
            aggfunc="mean", margins=False,
        )
        assert ct.loc["White", "A"] == 1000
        assert ct.loc["White", "B"] == 800


# ---------------------------------------------------------------------------
# rate_table
# ---------------------------------------------------------------------------

class TestRateTable:

    @pytest.fixture
    def ct(self, sample_df):
        return contingency_table(
            sample_df, "race", "county", value_var="population", margins=True,
        )

    def test_normalize_all(self, ct):
        rates = rate_table(ct, normalize="all")
        assert abs(rates.values.sum() - 1.0) < 1e-9
        assert "Total" not in rates.index

    def test_normalize_index(self, ct):
        rates = rate_table(ct, normalize="index")
        # Each row should sum to 1
        for row_label in rates.index:
            assert abs(rates.loc[row_label].sum() - 1.0) < 1e-9

    def test_normalize_columns(self, ct):
        rates = rate_table(ct, normalize="columns")
        # Each column should sum to 1
        for col_label in rates.columns:
            assert abs(rates[col_label].sum() - 1.0) < 1e-9

    def test_invalid_normalize(self, ct):
        with pytest.raises(ValueError, match="normalize"):
            rate_table(ct, normalize="invalid")


# ---------------------------------------------------------------------------
# chi_square_test
# ---------------------------------------------------------------------------

class TestChiSquareTest:

    def test_known_result(self):
        """Known 2x2 contingency table with exact expected values."""
        ct = pd.DataFrame(
            {"male": [10, 20], "female": [30, 40]},
            index=["yes", "no"],
        )
        result = chi_square_test(ct)
        assert isinstance(result, ChiSquareResult)
        assert result.dof == 1
        assert result.statistic > 0
        assert 0 <= result.p_value <= 1

    def test_strips_margins(self, sample_df):
        ct = contingency_table(
            sample_df, "race", "county", value_var="population", margins=True,
        )
        result = chi_square_test(ct)
        # Should not error even with Total row/col
        assert result.dof == (3 - 1) * (2 - 1)  # 3 races × 2 counties

    def test_expected_freq_shape(self, sample_df):
        ct = contingency_table(
            sample_df, "race", "county", value_var="population", margins=False,
        )
        result = chi_square_test(ct)
        assert result.expected_freq.shape == ct.shape

    def test_independent_data_high_p(self):
        """Perfectly uniform distribution should have high p-value."""
        ct = pd.DataFrame(
            {"X": [100, 100], "Y": [100, 100]},
            index=["A", "B"],
        )
        result = chi_square_test(ct)
        assert result.p_value > 0.99


# ---------------------------------------------------------------------------
# moe_cross_tab
# ---------------------------------------------------------------------------

class TestMoeCrossTab:

    def test_basic_propagation(self, sample_df, moe_df):
        result = moe_cross_tab(
            estimates_df=sample_df,
            moes_df=moe_df,
            row_var="race",
            col_var="county",
            value_var="population",
            moe_var="population_moe",
        )
        assert isinstance(result, pd.DataFrame)
        assert result.shape == (3, 2)  # 3 races × 2 counties
        # All MOEs should be positive
        assert (result.values >= 0).all()

    def test_single_observation_moe_passthrough(self):
        """When each cell has exactly one observation, MOE should pass through."""
        est = pd.DataFrame({
            "r": ["A", "B"],
            "c": ["X", "X"],
            "val": [100, 200],
        })
        moe = pd.DataFrame({
            "r": ["A", "B"],
            "c": ["X", "X"],
            "m": [10.0, 20.0],
        })
        result = moe_cross_tab(est, moe, "r", "c", "val", "m")
        # Single obs: MOE = original MOE
        assert abs(result.loc["A", "X"] - 10.0) < 1e-6
        assert abs(result.loc["B", "X"] - 20.0) < 1e-6


# ---------------------------------------------------------------------------
# CrossTabSpec dataclass
# ---------------------------------------------------------------------------

class TestCrossTabSpec:

    def test_defaults(self):
        spec = CrossTabSpec(row_var="race", col_var="county")
        assert spec.value_var is None
        assert spec.aggfunc == "sum"

    def test_custom(self):
        spec = CrossTabSpec(
            row_var="r", col_var="c", value_var="v",
            weight_var="w", aggfunc="mean", geography="geo",
        )
        assert spec.geography == "geo"


# ---------------------------------------------------------------------------
# Module exports
# ---------------------------------------------------------------------------

class TestExports:

    def test_all(self):
        from siege_utilities.data.statistics.cross_tabulation import __all__
        expected = {
            "ChiSquareResult", "CrossTabSpec",
            "chi_square_test", "contingency_table", "moe_cross_tab", "rate_table",
        }
        assert expected == set(__all__)

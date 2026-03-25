"""Tests for LongitudinalAligner, inflation_factor, and CPI-U table."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from siege_utilities.geo.timeseries.longitudinal_data import (
    AlignmentResult,
    CPI_U_ANNUAL,
    LongitudinalAligner,
    inflation_factor,
)


# ---------------------------------------------------------------------------
# CPI-U table and inflation_factor
# ---------------------------------------------------------------------------

class TestCPIUTable:

    def test_table_has_expected_years(self):
        for yr in (2000, 2010, 2015, 2020, 2023):
            assert yr in CPI_U_ANNUAL

    def test_values_are_positive(self):
        for yr, val in CPI_U_ANNUAL.items():
            assert val > 0, f"CPI-U for {yr} should be positive"

    def test_monotonically_increasing_trend(self):
        years = sorted(CPI_U_ANNUAL.keys())
        # Allow small year-to-year dips (2009 deflation) but overall upward
        assert CPI_U_ANNUAL[years[-1]] > CPI_U_ANNUAL[years[0]]


class TestInflationFactor:

    def test_same_year_returns_one(self):
        assert inflation_factor(2020, 2020) == 1.0

    def test_forward_adjustment(self):
        factor = inflation_factor(2010, 2020)
        assert factor > 1.0  # prices rose 2010→2020

    def test_backward_adjustment(self):
        factor = inflation_factor(2020, 2010)
        assert factor < 1.0

    def test_known_ratio(self):
        # CPI 2020=258.8, CPI 2010=218.1 → factor ≈ 1.1865
        factor = inflation_factor(2010, 2020)
        assert abs(factor - 258.8 / 218.1) < 0.001

    def test_missing_year_raises(self):
        with pytest.raises(KeyError):
            inflation_factor(1990, 2020)


# ---------------------------------------------------------------------------
# LongitudinalAligner.__init__
# ---------------------------------------------------------------------------

class TestAlignerInit:

    def test_default(self):
        a = LongitudinalAligner()
        assert a.target_vintage == 2020
        assert a.geography == "tract"
        assert a.state_fips is None

    def test_custom(self):
        a = LongitudinalAligner(target_vintage=2010, geography="county", state_fips="06")
        assert a.target_vintage == 2010
        assert a.geography == "county"
        assert a.state_fips == "06"

    def test_invalid_vintage(self):
        with pytest.raises(ValueError, match="2000, 2010, or 2020"):
            LongitudinalAligner(target_vintage=2030)


# ---------------------------------------------------------------------------
# _transition_chain
# ---------------------------------------------------------------------------

class TestTransitionChain:

    def test_identity(self):
        assert LongitudinalAligner._transition_chain(2020, 2020) == []

    def test_single_step_forward(self):
        assert LongitudinalAligner._transition_chain(2010, 2020) == [(2010, 2020)]

    def test_single_step_backward(self):
        assert LongitudinalAligner._transition_chain(2020, 2010) == [(2020, 2010)]

    def test_chained_2000_to_2020(self):
        chain = LongitudinalAligner._transition_chain(2000, 2020)
        assert chain == [(2000, 2010), (2010, 2020)]

    def test_chained_2020_to_2000(self):
        chain = LongitudinalAligner._transition_chain(2020, 2000)
        assert chain == [(2020, 2010), (2010, 2000)]

    def test_unsupported_raises(self):
        with pytest.raises(ValueError, match="No supported crosswalk"):
            LongitudinalAligner._transition_chain(1990, 2020)


# ---------------------------------------------------------------------------
# align()
# ---------------------------------------------------------------------------

class TestAlign:

    @pytest.fixture
    def sample_df(self):
        return pd.DataFrame({
            "GEOID": ["06001400100", "06001400200"],
            "TOTPOP": [5000, 3000],
            "MEDINC": [65000, 45000],
        })

    def test_identity_alignment(self, sample_df):
        aligner = LongitudinalAligner(target_vintage=2020)
        result = aligner.align(sample_df, source_vintage=2020)
        assert isinstance(result, AlignmentResult)
        assert result.method == "identity"
        assert result.rows_before == 2
        assert result.rows_after == 2
        assert result.data.equals(sample_df)

    def test_crosswalk_alignment(self, sample_df):
        aligner = LongitudinalAligner(target_vintage=2020, geography="tract")
        mock_result = sample_df.copy()
        mock_result["GEOID"] = ["06001400101", "06001400201"]

        with patch(
            "siege_utilities.geo.timeseries.longitudinal_data."
            "LongitudinalAligner._apply_crosswalk_step",
            return_value=mock_result,
        ):
            result = aligner.align(sample_df, source_vintage=2010)

        assert result.method == "crosswalk"
        assert result.source_vintage == 2010
        assert result.target_vintage == 2020
        assert len(result.data) == 2

    def test_fallback_to_areal(self, sample_df):
        aligner = LongitudinalAligner(target_vintage=2020, geography="tract")
        mock_result = sample_df.copy()

        with patch(
            "siege_utilities.geo.timeseries.longitudinal_data."
            "LongitudinalAligner._apply_crosswalk_step",
            side_effect=RuntimeError("no crosswalk file"),
        ), patch(
            "siege_utilities.geo.timeseries.longitudinal_data."
            "LongitudinalAligner._apply_areal_interpolation",
            return_value=mock_result,
        ):
            result = aligner.align(sample_df, source_vintage=2010)

        assert result.method == "areal"
        assert len(result.warnings) == 1
        assert "areal interpolation" in result.warnings[0]

    def test_both_methods_fail(self, sample_df):
        aligner = LongitudinalAligner(target_vintage=2020, geography="tract")

        with patch(
            "siege_utilities.geo.timeseries.longitudinal_data."
            "LongitudinalAligner._apply_crosswalk_step",
            side_effect=RuntimeError("no crosswalk"),
        ), patch(
            "siege_utilities.geo.timeseries.longitudinal_data."
            "LongitudinalAligner._apply_areal_interpolation",
            side_effect=RuntimeError("no boundaries"),
        ):
            result = aligner.align(sample_df, source_vintage=2010)

        assert result.method == "failed"
        assert len(result.warnings) >= 1

    def test_chained_crosswalk(self, sample_df):
        """2000→2020 should invoke two crosswalk steps."""
        aligner = LongitudinalAligner(target_vintage=2020, geography="tract")

        call_count = 0
        def mock_step(df, src, tgt, geo, sfips, geoid_col):
            nonlocal call_count
            call_count += 1
            return df.copy()

        with patch(
            "siege_utilities.geo.timeseries.longitudinal_data."
            "LongitudinalAligner._apply_crosswalk_step",
            side_effect=mock_step,
        ):
            result = aligner.align(sample_df, source_vintage=2000)

        assert call_count == 2
        assert result.method == "crosswalk"

    def test_override_geography_and_state(self, sample_df):
        aligner = LongitudinalAligner(target_vintage=2020, geography="tract")

        with patch(
            "siege_utilities.geo.timeseries.longitudinal_data."
            "LongitudinalAligner._apply_crosswalk_step",
            return_value=sample_df.copy(),
        ) as mock_step:
            aligner.align(
                sample_df, source_vintage=2010,
                geography="county", state_fips="36",
            )

        _, kwargs = mock_step.call_args
        # positional args: df, src, tgt, geo, sfips, geoid_col
        args = mock_step.call_args[0]
        assert args[3] == "county"
        assert args[4] == "36"


# ---------------------------------------------------------------------------
# adjust_inflation()
# ---------------------------------------------------------------------------

class TestAdjustInflation:

    def test_adjusts_columns(self):
        df = pd.DataFrame({"GEOID": ["A"], "MEDINC": [50000.0], "NAME": ["Test"]})
        result = LongitudinalAligner.adjust_inflation(
            df, dollar_columns=["MEDINC"], from_year=2010, to_year=2020,
        )
        expected = 50000.0 * (258.8 / 218.1)
        assert abs(result["MEDINC"].iloc[0] - expected) < 0.01

    def test_does_not_modify_original(self):
        df = pd.DataFrame({"MEDINC": [50000.0]})
        result = LongitudinalAligner.adjust_inflation(
            df, dollar_columns=["MEDINC"], from_year=2010, to_year=2020,
        )
        assert df["MEDINC"].iloc[0] == 50000.0
        assert result["MEDINC"].iloc[0] != 50000.0

    def test_missing_column_ignored(self):
        df = pd.DataFrame({"GEOID": ["A"], "TOTPOP": [1000]})
        result = LongitudinalAligner.adjust_inflation(
            df, dollar_columns=["MEDINC"], from_year=2010, to_year=2020,
        )
        assert "MEDINC" not in result.columns

    def test_same_year_no_change(self):
        df = pd.DataFrame({"MEDINC": [50000.0]})
        result = LongitudinalAligner.adjust_inflation(
            df, dollar_columns=["MEDINC"], from_year=2020, to_year=2020,
        )
        assert result["MEDINC"].iloc[0] == 50000.0


# ---------------------------------------------------------------------------
# AlignmentResult dataclass
# ---------------------------------------------------------------------------

class TestAlignmentResult:

    def test_defaults(self):
        r = AlignmentResult(
            data=pd.DataFrame(),
            source_vintage=2010,
            target_vintage=2020,
        )
        assert r.method == "crosswalk"
        assert r.rows_before == 0
        assert r.warnings == []

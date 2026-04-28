"""Tests for siege_utilities.survey.significance (SAL-65)."""
import pytest
from siege_utilities.survey.models import Chain, View
from siege_utilities.survey.significance import (
    SignificanceError,
    column_proportion_test,
    chi_square_flag,
)
from siege_utilities.reporting.pages.page_models import TableType

try:
    import scipy  # noqa: F401
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False

requires_scipy = pytest.mark.skipif(not SCIPY_AVAILABLE, reason="scipy not installed")


def _make_chain_two_cols():
    """Chain with two clearly different column proportions for sig testing."""
    views = {
        "county=Travis": [
            View(metric="D", base=1000, count=700.0, pct=0.70),
            View(metric="R", base=1000, count=300.0, pct=0.30),
        ],
        "county=Harris": [
            View(metric="D", base=1000, count=400.0, pct=0.40),
            View(metric="R", base=1000, count=600.0, pct=0.60),
        ],
    }
    return Chain(row_var="party", break_vars=["county"],
                 views=views, table_type=TableType.CROSS_TAB)


class TestColumnProportionTest:
    @requires_scipy
    def test_returns_chain(self):
        chain = _make_chain_two_cols()
        result = column_proportion_test(chain)
        assert result is chain

    @requires_scipy
    def test_mutates_in_place(self):
        chain = _make_chain_two_cols()
        column_proportion_test(chain)
        # At least one view should have a sig flag for such extreme difference
        all_flags = [
            v.sig_flag
            for views in chain.views.values()
            for v in views
            if v.sig_flag
        ]
        assert len(all_flags) > 0

    def test_single_column_no_change(self):
        views = {"A": [View(metric="x", base=100, count=50.0, pct=0.5)]}
        chain = Chain(row_var="q", break_vars=["g"], views=views,
                      table_type=TableType.CROSS_TAB)
        result = column_proportion_test(chain)
        assert result is chain

    def test_scipy_fallback_flags_extreme_difference(self, monkeypatch):
        """When scipy is absent, the z=1.96 fallback still flags clear
        differences — the fallback is *correct* for alpha=0.05, just limited.
        """
        monkeypatch.setattr(
            "siege_utilities.survey.significance._SCIPY_AVAILABLE", False
        )
        chain = _make_chain_two_cols()
        column_proportion_test(chain, alpha=0.05)
        all_flags = [
            v.sig_flag for vs in chain.views.values() for v in vs if v.sig_flag
        ]
        assert len(all_flags) > 0

    def test_scipy_fallback_rejects_unknown_alpha(self, monkeypatch):
        """alpha=0.02 has no exact fallback z-crit; must raise rather than
        silently use 1.96."""
        monkeypatch.setattr(
            "siege_utilities.survey.significance._SCIPY_AVAILABLE", False
        )
        chain = _make_chain_two_cols()
        with pytest.raises(SignificanceError, match="requires scipy"):
            column_proportion_test(chain, alpha=0.02)


class TestChiSquareFlag:
    @requires_scipy
    def test_returns_chain(self):
        chain = _make_chain_two_cols()
        result = chi_square_flag(chain)
        assert result is chain

    @requires_scipy
    def test_sets_chi_square_significant(self):
        chain = _make_chain_two_cols()
        chi_square_flag(chain)
        assert hasattr(chain, "chi_square_significant")

    @requires_scipy
    def test_significant_for_strong_association(self):
        chain = _make_chain_two_cols()
        chi_square_flag(chain, alpha=0.05)
        assert bool(chain.chi_square_significant) is True

    def test_empty_chain_no_crash(self):
        chain = Chain(row_var="q", break_vars=[], views={},
                      table_type=TableType.CROSS_TAB)
        chi_square_flag(chain)
        assert bool(chain.chi_square_significant) is False

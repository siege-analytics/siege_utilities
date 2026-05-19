"""Tests for siege_utilities.survey.models (SAL-65)."""
import pytest
import pandas as pd
from siege_utilities.survey.models import View, Chain, Cluster, Stack, WeightScheme
from siege_utilities.reporting.pages.page_models import TableType


class TestView:
    def test_construction(self):
        v = View(metric="yes", base=100, count=60.0, pct=0.6)
        assert v.metric == "yes"
        assert v.pct == pytest.approx(0.6)

    def test_default_sig_flag_none(self):
        v = View(metric="no", base=100, count=40.0)
        assert v.sig_flag is None


class TestChain:
    def _simple_chain(self):
        views = {
            "county=Travis": [
                View(metric="Democrat", base=200, count=120.0, pct=0.6),
                View(metric="Republican", base=200, count=80.0, pct=0.4),
            ]
        }
        return Chain(
            row_var="party",
            break_vars=["county"],
            views=views,
            table_type=TableType.SINGLE_RESPONSE,
        )

    def test_to_dataframe_shape(self):
        chain = self._simple_chain()
        df = chain.to_dataframe()
        assert isinstance(df, pd.DataFrame)
        assert df.shape == (2, 1)

    def test_to_dataframe_values_are_pct_times_100(self):
        chain = self._simple_chain()
        df = chain.to_dataframe()
        col = df.iloc[:, 0]
        assert col["Democrat"] == pytest.approx(60.0)
        assert col["Republican"] == pytest.approx(40.0)

    def test_empty_chain_returns_empty_df(self):
        chain = Chain(row_var="x", break_vars=[], views={},
                      table_type=TableType.CROSS_TAB)
        assert chain.to_dataframe().empty

    def test_geo_column_default_none(self):
        chain = self._simple_chain()
        assert chain.geo_column is None

    def test_base_note_default_empty(self):
        chain = self._simple_chain()
        assert chain.base_note == ""


class TestCluster:
    def test_add_chain(self):
        cluster = Cluster(name="Demographics")
        chain = Chain(row_var="age", break_vars=["county"], views={},
                      table_type=TableType.CROSS_TAB)
        result = cluster.add_chain(chain)
        assert result is cluster
        assert len(cluster.chains) == 1

    def test_empty_cluster(self):
        cluster = Cluster(name="Empty")
        assert cluster.chains == []


class TestWeightScheme:
    def test_valid_targets_validate_ok(self):
        ws = WeightScheme(targets={
            "age_group": {"18-34": 0.25, "35-54": 0.40, "55+": 0.35},
        })
        ws.validate()  # should not raise

    def test_invalid_targets_raise(self):
        ws = WeightScheme(targets={
            "gender": {"M": 0.60, "F": 0.60},  # sums to 1.2
        })
        with pytest.raises(ValueError, match="sum to"):
            ws.validate()


class TestStack:
    def test_all_chains(self):
        c1 = Chain(row_var="q1", break_vars=[], views={}, table_type=TableType.SINGLE_RESPONSE)
        c2 = Chain(row_var="q2", break_vars=[], views={}, table_type=TableType.RANKING)
        cluster = Cluster(name="S1", chains=[c1, c2])
        stack = Stack(name="My Report", clusters=[cluster])
        assert len(stack.all_chains) == 2

    def test_add_cluster(self):
        stack = Stack(name="R")
        cluster = Cluster(name="C")
        result = stack.add_cluster(cluster)
        assert len(stack.clusters) == 1
        assert result is stack  # fluent return contract (symmetric with Cluster.add_chain)

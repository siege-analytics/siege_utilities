"""Tests for siege_utilities.survey.crosstab.build_chain (SAL-65)."""
import pytest
import pandas as pd
from siege_utilities.survey.crosstab import build_chain
from siege_utilities.reporting.pages.page_models import TableType


@pytest.fixture
def respondent_df():
    return pd.DataFrame({
        "party":   ["D", "D", "R", "R", "D", "I", "R", "I"],
        "county":  ["Travis", "Travis", "Travis", "Harris", "Harris", "Harris", "Travis", "Harris"],
        "value":   [1, 1, 1, 1, 1, 1, 1, 1],
        "year":    [2020, 2022, 2020, 2022, 2020, 2022, 2022, 2020],
        "support": [8, 7, 3, 4, 9, 6, 2, 5],
    })


class TestBuildChainSingleResponse:
    def test_returns_chain(self, respondent_df):
        from siege_utilities.survey.models import Chain
        chain = build_chain(respondent_df, "party", ["county"],
                            table_type=TableType.SINGLE_RESPONSE)
        assert isinstance(chain, Chain)

    def test_table_type_set(self, respondent_df):
        chain = build_chain(respondent_df, "party", ["county"],
                            table_type=TableType.SINGLE_RESPONSE)
        assert chain.table_type == TableType.SINGLE_RESPONSE

    def test_views_keyed_by_break(self, respondent_df):
        chain = build_chain(respondent_df, "party", ["county"],
                            table_type=TableType.SINGLE_RESPONSE)
        assert any("county=" in k for k in chain.views)

    def test_pcts_sum_to_one(self, respondent_df):
        chain = build_chain(respondent_df, "party", ["county"],
                            table_type=TableType.SINGLE_RESPONSE)
        for views in chain.views.values():
            total_pct = sum(v.pct for v in views if v.pct is not None)
            assert total_pct == pytest.approx(1.0, abs=0.01)


class TestBuildChainMultipleResponse:
    def test_base_note_contains_multiple_responses(self, respondent_df):
        chain = build_chain(respondent_df, "party", ["county"],
                            table_type=TableType.MULTIPLE_RESPONSE)
        assert "multiple responses" in chain.base_note.lower()

    def test_base_note_contains_respondent_count(self, respondent_df):
        chain = build_chain(respondent_df, "party", ["county"],
                            table_type=TableType.MULTIPLE_RESPONSE)
        assert "n=" in chain.base_note

    def test_table_type_set(self, respondent_df):
        chain = build_chain(respondent_df, "party", ["county"],
                            table_type=TableType.MULTIPLE_RESPONSE)
        assert chain.table_type == TableType.MULTIPLE_RESPONSE


class TestBuildChainLongitudinal:
    def test_delta_column_present(self, respondent_df):
        chain = build_chain(respondent_df, "party", ["year"],
                            table_type=TableType.LONGITUDINAL)
        assert chain.delta_column is not None

    def test_delta_column_in_views(self, respondent_df):
        chain = build_chain(respondent_df, "party", ["year"],
                            table_type=TableType.LONGITUDINAL)
        assert chain.delta_column in chain.views

    def test_two_time_periods_in_views(self, respondent_df):
        chain = build_chain(respondent_df, "party", ["year"],
                            table_type=TableType.LONGITUDINAL)
        period_keys = [k for k in chain.views if k != chain.delta_column]
        assert len(period_keys) == 2


class TestBuildChainRanking:
    def test_views_not_empty(self, respondent_df):
        chain = build_chain(respondent_df, "party", ["county"],
                            table_type=TableType.RANKING)
        assert chain.views

    def test_top_n_limits_rows(self, respondent_df):
        chain = build_chain(respondent_df, "party", ["county"],
                            table_type=TableType.RANKING, top_n=2)
        for views in chain.views.values():
            assert len(views) <= 2


class TestBuildChainMeanScale:
    def test_returns_chain(self, respondent_df):
        chain = build_chain(respondent_df, "party", ["county"],
                            metric="support",
                            table_type=TableType.MEAN_SCALE)
        assert chain.table_type == TableType.MEAN_SCALE


class TestBuildChainGeoColumn:
    def test_geo_column_attached(self, respondent_df):
        chain = build_chain(respondent_df, "party", ["county"],
                            table_type=TableType.CROSS_TAB,
                            geo_column="county")
        assert chain.geo_column == "county"

    def test_no_geo_column_by_default(self, respondent_df):
        chain = build_chain(respondent_df, "party", ["county"],
                            table_type=TableType.CROSS_TAB)
        assert chain.geo_column is None

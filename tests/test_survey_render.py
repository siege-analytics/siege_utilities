"""Tests for siege_utilities.survey.render (SAL-65)."""
import pandas as pd
from siege_utilities.survey.models import Chain, View
from siege_utilities.survey.render import chain_to_argument
from siege_utilities.reporting.pages.page_models import Argument, TableType


def _chain(table_type, geo_column=None):
    views = {
        "county=Travis": [
            View(metric="D", base=200, count=120.0, pct=0.6),
            View(metric="R", base=200, count=80.0, pct=0.4),
        ]
    }
    return Chain(
        row_var="party", break_vars=["county"],
        views=views, table_type=table_type, geo_column=geo_column,
    )


class TestChainToArgument:
    def test_returns_argument(self):
        chain = _chain(TableType.SINGLE_RESPONSE)
        arg = chain_to_argument(chain, headline="Party ID", narrative="Text")
        assert isinstance(arg, Argument)

    def test_headline_and_narrative_set(self):
        chain = _chain(TableType.CROSS_TAB)
        arg = chain_to_argument(chain, headline="H", narrative="N")
        assert arg.headline == "H"
        assert arg.narrative == "N"

    def test_table_is_dataframe(self):
        chain = _chain(TableType.SINGLE_RESPONSE)
        arg = chain_to_argument(chain, headline="H", narrative="N")
        assert isinstance(arg.table, pd.DataFrame)

    def test_table_type_preserved(self):
        for tt in TableType:
            chain = _chain(tt)
            arg = chain_to_argument(chain, headline="H", narrative="N")
            assert arg.table_type == tt

    def test_map_figure_none_without_geo_column(self):
        chain = _chain(TableType.SINGLE_RESPONSE, geo_column=None)
        arg = chain_to_argument(chain, headline="H", narrative="N")
        assert arg.map_figure is None

    def test_layout_side_by_side_without_map(self):
        chain = _chain(TableType.SINGLE_RESPONSE, geo_column=None)
        arg = chain_to_argument(chain, headline="H", narrative="N")
        assert arg.layout == "side_by_side"

    def test_tags_include_table_type_value(self):
        chain = _chain(TableType.MULTIPLE_RESPONSE)
        arg = chain_to_argument(chain, headline="H", narrative="N")
        assert "multiple_response" in arg.tags

    def test_base_note_from_multiple_response_chain(self):
        from siege_utilities.survey.crosstab import build_chain
        df = pd.DataFrame({
            "party": ["D", "R", "D", "I"],
            "county": ["T", "T", "H", "H"],
            "value": [1, 1, 1, 1],
        })
        chain = build_chain(df, "party", ["county"],
                            table_type=TableType.MULTIPLE_RESPONSE)
        arg = chain_to_argument(chain, headline="H", narrative="N")
        assert "multiple responses" in (arg.base_note or "").lower()


class TestChainToArgumentWithGeo:
    def test_layout_influenced_by_map_figure(self):
        """If chain.geo_column is set and map_figure is generated, layout = full_width."""
        # We can't guarantee the map builder succeeds without geo deps, but we can
        # force-test the Argument auto-layout logic by injecting a map_figure.
        from siege_utilities.reporting.pages.page_models import Argument, TableType
        arg = Argument(
            headline="H", narrative="N", table=pd.DataFrame(),
            table_type=TableType.CROSS_TAB,
            map_figure=object(),  # any truthy value
        )
        assert arg.layout == "full_width"

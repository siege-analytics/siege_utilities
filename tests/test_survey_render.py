"""Tests for siege_utilities.survey.render (SAL-65)."""
import pandas as pd
import pytest

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

    def test_render_path_invokes_map_builder_and_sets_map_figure(self, monkeypatch):
        """The render path must actually call _build_map and put the result on
        the Argument — not just rely on layout logic. Monkeypatches _build_map
        to return a sentinel, then asserts the sentinel reaches Argument.map_figure.
        """
        from siege_utilities.survey import render as render_mod
        from siege_utilities.survey.models import Chain, View
        from siege_utilities.reporting.pages.page_models import TableType

        sentinel_fig = object()

        def fake_build_map(chain):
            assert chain.geo_column == chain.row_var, (
                "render path must only invoke _build_map when "
                "row_var and geo_column match (data integrity contract)"
            )
            return sentinel_fig

        monkeypatch.setattr(render_mod, "_build_map", fake_build_map)

        views = {
            "year=2024": [
                View(metric="TX", base=1000, count=500.0, pct=0.5),
                View(metric="CA", base=1000, count=500.0, pct=0.5),
            ]
        }
        chain = Chain(
            row_var="state",
            break_vars=["year"],
            views=views,
            table_type=TableType.CROSS_TAB,
            geo_column="state",  # matches row_var
        )
        arg = render_mod.chain_to_argument(chain, headline="H", narrative="N")
        assert arg.map_figure is sentinel_fig
        assert arg.layout == "full_width"

    def test_build_map_raises_on_geo_row_mismatch(self):
        """RenderError when geo_column is set but row_var is something else —
        would silently mislabel row categories (e.g. "Democrat") as geo features.
        """
        from siege_utilities.survey import render as render_mod
        from siege_utilities.survey.models import Chain, View
        from siege_utilities.reporting.pages.page_models import TableType

        views = {
            "state=TX": [
                View(metric="Democrat", base=1000, count=400.0, pct=0.4),
                View(metric="Republican", base=1000, count=600.0, pct=0.6),
            ]
        }
        chain = Chain(
            row_var="party",       # NOT geographic
            break_vars=["state"],
            views=views,
            table_type=TableType.CROSS_TAB,
            geo_column="state",    # mismatch
        )
        with pytest.raises(render_mod.RenderError, match="mislabeled as geo features"):
            render_mod._build_map(chain)

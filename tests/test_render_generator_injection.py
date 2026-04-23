"""Tests for ELE-2441: D8 (Chain.to_argument removed) + D9 (generator kwargs honored)."""
from __future__ import annotations

from unittest.mock import MagicMock

import pandas as pd
import pytest

from siege_utilities.survey.models import Chain, View
from siege_utilities.reporting.pages.page_models import TableType
from siege_utilities.survey.render import chain_to_argument


def _make_chain(geo_column=None):
    """Minimal Chain with two break-values and one view each."""
    return Chain(
        row_var="party",
        break_vars=["region"],
        views={
            "North": [View(metric="count", base=100.0, count=50.0, pct=0.5)],
            "South": [View(metric="count", base=100.0, count=50.0, pct=0.5)],
        },
        table_type=TableType.CROSS_TAB,
        base_note="n=100",
        geo_column=geo_column,
    )


class TestChainHasNoToArgumentMethod:
    """D8: the convenience method is removed; function is sole entry point."""

    def test_method_removed(self):
        chain = _make_chain()
        assert not hasattr(chain, "to_argument")


class TestChartGeneratorInjection:
    """D9: chart_generator kwarg is honored."""

    def test_default_matplotlib_path_runs(self):
        """chart_generator=None uses the default matplotlib path."""
        chain = _make_chain()
        arg = chain_to_argument(chain, headline="H", narrative="N")
        # Doesn't care what the chart is — just that no exception and argument built
        assert arg.headline == "H"
        assert arg.narrative == "N"

    def test_custom_chart_generator_is_called(self):
        """chart_generator=callable is invoked with (df, chart_type, headline)."""
        chain = _make_chain()
        sentinel = MagicMock(name="figure-sentinel")
        fake_generator = MagicMock(return_value=sentinel)

        arg = chain_to_argument(
            chain,
            headline="H",
            narrative="N",
            chart_generator=fake_generator,
        )

        fake_generator.assert_called_once()
        call_args = fake_generator.call_args
        assert isinstance(call_args.args[0], pd.DataFrame)  # df
        assert call_args.args[1] in {
            "horizontal_bar", "grouped_bar", "line", "bar_with_error",
            "heatmap", "small_multiples",
        }
        assert call_args.args[2] == "H"
        assert arg.chart is sentinel

    def test_custom_chart_generator_returning_none_is_respected(self):
        """Callable may legitimately return None (e.g. headless environment)."""
        chain = _make_chain()
        fake_generator = MagicMock(return_value=None)

        arg = chain_to_argument(
            chain,
            headline="H",
            narrative="N",
            chart_generator=fake_generator,
        )
        assert arg.chart is None


class TestMapGeneratorInjection:
    """D9: map_generator kwarg is honored."""

    def test_map_generator_not_called_without_geo_column(self):
        chain = _make_chain(geo_column=None)
        fake_mapper = MagicMock()
        fake_mapper.create_choropleth_map = MagicMock(return_value="SHOULD_NOT_SEE_ME")

        arg = chain_to_argument(
            chain,
            headline="H",
            narrative="N",
            map_generator=fake_mapper,
        )
        fake_mapper.create_choropleth_map.assert_not_called()
        assert arg.map_figure is None

    def test_custom_map_generator_is_called_when_geo_configured(self):
        # row_var must equal geo_column for map to build
        chain = Chain(
            row_var="state",
            break_vars=["metric"],
            views={
                "CA": [View(metric="count", base=1.0, count=1.0, pct=1.0)],
                "TX": [View(metric="count", base=1.0, count=1.0, pct=1.0)],
            },
            table_type=TableType.CROSS_TAB,
            geo_column="state",
        )
        map_sentinel = MagicMock(name="map-figure-sentinel")
        fake_mapper = MagicMock()
        fake_mapper.create_choropleth_map = MagicMock(return_value=map_sentinel)

        arg = chain_to_argument(
            chain,
            headline="H",
            narrative="N",
            map_generator=fake_mapper,
        )

        fake_mapper.create_choropleth_map.assert_called_once()
        kwargs = fake_mapper.create_choropleth_map.call_args.kwargs
        assert kwargs["geo_column"] == "state"
        assert kwargs["value_column"] == "value"
        assert arg.map_figure is map_sentinel

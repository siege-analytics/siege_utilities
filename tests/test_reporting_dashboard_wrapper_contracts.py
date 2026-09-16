"""Canonical root-import contracts for reporting dashboard wrappers."""

from siege_utilities import create_dashboard
from siege_utilities import create_dataframe_summary_charts

from tests.reporting_chart_support import FakeChartGenerator
from tests.reporting_chart_support import install_fake_chart_generator


def test_create_dashboard_delegates_layout_dimensions_and_kwargs(monkeypatch):
    install_fake_chart_generator(monkeypatch)
    charts = [{"kind": "bar"}, {"kind": "line"}]

    assert create_dashboard(
        charts,
        "1x2",
        10.5,
        6.25,
        background="white",
    ) == {"kind": "dashboard"}

    assert FakeChartGenerator.instances[0].calls == [
        (
            "dashboard",
            (charts, "1x2", 10.5, 6.25),
            {"background": "white"},
        )
    ]


def test_create_dataframe_summary_charts_delegates_parameters(monkeypatch):
    install_fake_chart_generator(monkeypatch)
    frame = object()

    assert create_dataframe_summary_charts(
        frame,
        "Summary",
        9.0,
        5.5,
        palette="brand",
    ) == {"kind": "summary"}

    assert FakeChartGenerator.instances[0].calls == [
        (
            "summary",
            (frame, "Summary", 9.0, 5.5),
            {"palette": "brand"},
        )
    ]

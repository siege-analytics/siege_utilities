"""Canonical root-import contracts for reporting dashboard wrappers."""

from siege_utilities import create_dashboard
from siege_utilities import create_dataframe_summary_charts


class FakeChartGenerator:
    instances = []

    def __init__(self):
        self.calls = []
        FakeChartGenerator.instances.append(self)

    def create_dashboard(self, *args, **kwargs):
        self.calls.append(("dashboard", args, kwargs))
        return {"kind": "dashboard"}

    def create_dataframe_summary_charts(self, *args, **kwargs):
        self.calls.append(("summary", args, kwargs))
        return {"kind": "summary"}


def install_fake_chart_generator(monkeypatch):
    from siege_utilities.reporting import chart_generator

    FakeChartGenerator.instances = []
    monkeypatch.setattr(
        chart_generator,
        "ChartGenerator",
        FakeChartGenerator,
    )


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

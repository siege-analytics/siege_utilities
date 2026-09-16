"""Canonical root-import contracts for reporting chart wrapper helpers."""

from siege_utilities import create_bar_chart
from siege_utilities import create_line_chart
from siege_utilities import create_pie_chart
from siege_utilities import generate_chart_from_dataframe


class FakeChartGenerator:
    instances = []

    def __init__(self):
        self.calls = []
        FakeChartGenerator.instances.append(self)

    def create_bar_chart(self, *args, **kwargs):
        self.calls.append(("bar", args, kwargs))
        return {"kind": "bar"}

    def create_line_chart(self, *args, **kwargs):
        self.calls.append(("line", args, kwargs))
        return {"kind": "line"}

    def create_pie_chart(self, *args, **kwargs):
        self.calls.append(("pie", args, kwargs))
        return {"kind": "pie"}

    def generate_chart_from_dataframe(self, *args, **kwargs):
        self.calls.append(("dataframe", args, kwargs))
        return {"kind": "dataframe"}


def install_fake_chart_generator(monkeypatch):
    from siege_utilities.reporting import chart_generator

    FakeChartGenerator.instances = []
    monkeypatch.setattr(
        chart_generator,
        "ChartGenerator",
        FakeChartGenerator,
    )


def test_basic_chart_wrappers_delegate_dimensions_and_kwargs(monkeypatch):
    install_fake_chart_generator(monkeypatch)
    data = {"rows": [1, 2]}

    assert create_bar_chart(
        data,
        "city",
        "sales",
        "Sales",
        640,
        480,
        color="blue",
    ) == {"kind": "bar"}
    assert create_line_chart(
        data,
        "date",
        "revenue",
        "Revenue",
        800,
        300,
        smooth=True,
    ) == {"kind": "line"}
    assert create_pie_chart(
        data,
        "segment",
        "amount",
        "Mix",
        500,
        500,
        hole=0.4,
    ) == {"kind": "pie"}

    assert [instance.calls for instance in FakeChartGenerator.instances] == [
        [
            (
                "bar",
                (data, "city", "sales", "Sales", 640, 480),
                {"color": "blue"},
            )
        ],
        [
            (
                "line",
                (data, "date", "revenue", "Revenue", 800, 300),
                {"smooth": True},
            )
        ],
        [
            (
                "pie",
                (data, "segment", "amount", "Mix", 500, 500),
                {"hole": 0.4},
            )
        ],
    ]


def test_generate_chart_from_dataframe_delegates_chart_parameters(monkeypatch):
    install_fake_chart_generator(monkeypatch)
    frame = object()

    assert generate_chart_from_dataframe(
        frame,
        "line",
        "date",
        ["sales", "cost"],
        "Trend",
        7.5,
        4.25,
        palette="brand",
    ) == {"kind": "dataframe"}

    assert FakeChartGenerator.instances[0].calls == [
        (
            "dataframe",
            (frame, "line", "date", ["sales", "cost"], "Trend", 7.5, 4.25),
            {"palette": "brand"},
        )
    ]

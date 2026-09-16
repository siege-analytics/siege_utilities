"""Shared test support for reporting chart wrapper contracts."""


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

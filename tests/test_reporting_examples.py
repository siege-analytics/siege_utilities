"""Run every bundled reporting demo with real renderers and offline sample data."""

import runpy
from pathlib import Path

import pytest


@pytest.mark.parametrize(
    "example, artifacts",
    [
        ("bivariate_choropleth_example", ["bivariate_output/temp_bivariate_choropleth.html"]),
        (
            "ga_geographic_analysis",
            ["ga_state_choropleth.png", "ga_city_heatmap.html", "ga_bivariate.png"],
        ),
        ("google_analytics_report_example", ["ga_performance_report.pdf"]),
    ],
)
def test_reporting_example_runs_end_to_end(monkeypatch, example, artifacts):
    for dependency in ("matplotlib", "seaborn", "folium", "reportlab", "geopandas"):
        pytest.importorskip(dependency)
    import matplotlib

    matplotlib.use("Agg")
    monkeypatch.setenv("MPLBACKEND", "Agg")
    runpy.run_module(f"siege_utilities.reporting.examples.{example}", run_name="__main__")
    for artifact in artifacts:
        assert Path(artifact).stat().st_size > 0

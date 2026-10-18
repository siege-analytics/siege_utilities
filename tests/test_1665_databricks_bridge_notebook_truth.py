"""Guard the schematic bridge's units and driver-memory contract (#1665).

Inspect the notebook itself: executing its helper cells does not exercise
the Spark/GeoPandas bridge, which lives in Markdown.
"""

from pathlib import Path

import nbformat
import pytest


NOTEBOOK = (
    Path(__file__).resolve().parents[1]
    / "notebooks/engines/03_databricks_geo.ipynb"
)


@pytest.fixture(scope="module")
def notebook():
    return nbformat.read(NOTEBOOK, as_version=4)


@pytest.fixture(scope="module")
def bridge(notebook):
    sections = [
        cell.source
        for cell in notebook.cells
        if cell.cell_type == "markdown"
        and cell.source.startswith("## 4. Spark ↔ GeoPandas bridge")
    ]
    assert len(sections) == 1, "Expected one Markdown bridge section"
    return " ".join(sections[0].split())


def test_notebook_is_valid(notebook):
    nbformat.validate(notebook)


def test_bridge_is_labeled_schematic_not_executed(bridge, notebook):
    assert "schematic" in bridge.lower(), (
        "The degree-buffer example must be labeled schematic"
    )
    assert "not executed" in bridge.lower()
    assert not any(
        "spark_to_geopandas(" in cell.source
        for cell in notebook.cells
        if cell.cell_type == "code"
    ), "A runnable bridge needs local metric-radius and CRS behavior tests"


def test_degree_buffer_disclaims_metric_distance(bridge):
    assert "gdf.geometry.buffer(0.01)" in bridge
    assert "EPSG:4326" in bridge
    assert "0.01 angular degrees" in bridge
    assert "not a fixed metric distance" in bridge
    assert (
        "# Schematic only: angular degrees, not meters. "
        "gdf = gdf.assign(geometry=gdf.geometry.buffer(0.01))"
    ) in bridge, "Keep the unit warning beside the schematic buffer call"


def test_real_use_recipe_projects_then_buffers_in_meters(bridge):
    assert "projected metric CRS" in bridge
    assert "UTM" in bridge
    assert "equidistant" in bridge
    assert "radius_m = 1000" in bridge
    assert "meters" in bridge
    project = bridge.index("projected = gdf.to_crs(metric_crs)")
    buffer = bridge.index("projected.geometry.buffer(radius_m)")
    restore = bridge.index("buffered.to_crs('EPSG:4326')")
    assert project < buffer < restore, (
        "The recipe must transform to metric coordinates before buffering"
    )


def test_driver_collection_requires_a_caller_bound(bridge):
    assert "collects all supplied rows to the driver" in bridge
    assert "no internal row limit" in bridge
    assert "before calling `spark_to_geopandas`" in bridge
    assert "driver memory" in bridge
    assert "max_driver_rows = 1000" in bridge
    assert "spark_to_geopandas( spark_df.limit(max_driver_rows)," in bridge

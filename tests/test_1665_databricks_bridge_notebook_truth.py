"""Guard the schematic bridge's units and driver-memory contract (#1665).

Inspect the notebook itself: executing its helper cells does not exercise
the Spark/GeoPandas bridge, which lives in Markdown.
"""

import inspect
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
        "The bridge example must be labeled schematic"
    )
    assert "not executed" in bridge.lower()
    assert not any(
        "spark_to_geopandas(" in cell.source
        for cell in notebook.cells
        if cell.cell_type == "code"
    ), "A runnable bridge needs local metric-radius and CRS behavior tests"


def test_degree_buffer_disclaims_metric_distance(bridge):
    assert "EPSG:4326" in bridge
    assert "`buffer(0.01)` uses 0.01 angular degrees" in bridge
    assert "not a fixed metric distance" in bridge
    assert "metric_crs = 'EPSG:32618'" in bridge
    assert "radius_m = 1000 # meters" in bridge
    assert "projected.geometry.buffer(radius_m)" in bridge


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


def _bridge_source():
    nb = nbformat.read(NOTEBOOK, as_version=4)
    return next(c.source for c in nb.cells if c.source.startswith("## 4. Spark"))

def test_schematic_code_buffers_in_meters_and_does_not_overwrite_with_a_sample():
    code = _bridge_source().split("```python", 1)[1].split("```", 1)[0]
    assert "buffer(0.01)" not in code, "code block still buffers in degrees"
    assert code.index("to_crs(metric_crs)") < code.index("buffer(radius_m)") < code.index("to_crs('EPSG:4326')")
    assert not ("limit(max_driver_rows)" in code and "mode('overwrite')" in code), \
        "a capped sample must not overwrite a persistent table"

@pytest.mark.parametrize("name", ["pandas_to_spark", "spark_to_pandas", "geopandas_to_spark", "spark_to_geopandas"])
def test_listed_bridge_signatures_match_module(name):
    from siege_utilities.databricks import dataframe_bridge
    line = next(l for l in _bridge_source().splitlines() if l.startswith(f"- `{name}("))
    for param in inspect.signature(getattr(dataframe_bridge, name)).parameters:
        assert param in line, f"{name} listing omits {param!r}"

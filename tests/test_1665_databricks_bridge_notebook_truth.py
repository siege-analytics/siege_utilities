"""Guard the schematic bridge's units and driver-memory contract (#1665).

Inspect the notebook itself: executing its helper cells does not exercise
the Spark/GeoPandas bridge, which lives in Markdown.
"""

import inspect
import re
from pathlib import Path

import nbformat
import pytest


NOTEBOOK = (
    Path(__file__).resolve().parents[1]
    / "notebooks/engines/03_databricks_geo.ipynb"
)

# One pattern for the guard and for its own test, so the test exercises the
# predicate the guard uses. Accepts either quote style and inner whitespace.
_OVERWRITE_MODE = re.compile(r"""\.mode\(\s*["']overwrite["']\s*\)""")


@pytest.fixture(scope="module")
def notebook() -> nbformat.NotebookNode:
    return nbformat.read(NOTEBOOK, as_version=4)


@pytest.fixture(scope="module")
def bridge(notebook: nbformat.NotebookNode) -> str:
    sections = [
        cell.source
        for cell in notebook.cells
        if cell.cell_type == "markdown"
        and cell.source.startswith("## 4. Spark ↔ GeoPandas bridge")
    ]
    assert len(sections) == 1, "Expected one Markdown bridge section"
    return " ".join(sections[0].split())


def test_notebook_is_valid(notebook: nbformat.NotebookNode) -> None:
    nbformat.validate(notebook)


def test_bridge_is_labeled_schematic_not_executed(
    bridge: str, notebook: nbformat.NotebookNode
) -> None:
    assert "schematic" in bridge.lower(), (
        "The bridge example must be labeled schematic"
    )
    assert "not executed" in bridge.lower()
    assert not any(
        "spark_to_geopandas(" in cell.source
        for cell in notebook.cells
        if cell.cell_type == "code"
    ), "A runnable bridge needs local metric-radius and CRS behavior tests"


def test_degree_buffer_disclaims_metric_distance(bridge: str) -> None:
    assert "EPSG:4326" in bridge
    assert "`buffer(0.01)` uses 0.01 angular degrees" in bridge
    assert "not a fixed metric distance" in bridge
    assert "metric_crs = 'EPSG:32618'" in bridge
    assert "radius_m = 1000 # meters" in bridge
    assert "projected.geometry.buffer(radius_m)" in bridge


def test_real_use_recipe_projects_then_buffers_in_meters(bridge: str) -> None:
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


def test_driver_collection_requires_a_caller_bound(bridge: str) -> None:
    assert "collects all supplied rows to the driver" in bridge
    assert "no internal row limit" in bridge
    assert "before calling `spark_to_geopandas`" in bridge
    assert "driver memory" in bridge
    assert "max_driver_rows = 1000" in bridge
    assert "spark_to_geopandas( spark_df.limit(max_driver_rows)," in bridge


def _bridge_source() -> str:
    nb = nbformat.read(NOTEBOOK, as_version=4)
    return next(c.source for c in nb.cells if c.source.startswith("## 4. Spark"))


def _capped_sample_overwrites(code: str) -> bool:
    """True when a capped sample is written with ``mode("overwrite")``."""
    return "limit(max_driver_rows)" in code and bool(_OVERWRITE_MODE.search(code))


def test_schematic_code_buffers_in_meters_and_does_not_overwrite_with_a_sample() -> None:
    code = _bridge_source().split("```python", 1)[1].split("```", 1)[0]
    assert "buffer(0.01)" not in code, "code block still buffers in degrees"
    assert code.index("to_crs(metric_crs)") < code.index("buffer(radius_m)") < code.index("to_crs('EPSG:4326')")
    assert not _capped_sample_overwrites(code), \
        "a capped sample must not overwrite a persistent table"


@pytest.mark.parametrize("write", ['.mode("overwrite")', ".mode('overwrite')", ".mode( 'overwrite' )"])
def test_capped_sample_overwrite_is_detected_in_either_quote_style(write: str) -> None:
    code = f"spark_df.limit(max_driver_rows).write{write}.saveAsTable('t')"
    assert _capped_sample_overwrites(code)


def test_uncapped_or_append_writes_are_not_flagged_as_sample_overwrites() -> None:
    assert not _capped_sample_overwrites("spark_df.write.mode('overwrite').saveAsTable('t')")
    assert not _capped_sample_overwrites("spark_df.limit(max_driver_rows).write.mode('append').saveAsTable('t')")


def _documented_params(line: str) -> set[str]:
    """Parameter identifiers the notebook lists for a bridge function.

    The listing is ``- `name(a, b='x', c=None)` ``; return ``{'a', 'b', 'c'}``
    by taking the token before any ``=`` or ``:`` in each comma-separated
    argument. Matching whole identifiers (not substrings) keeps a shared prefix
    such as ``crs`` versus ``crs_column`` from masking a dropped parameter.
    """
    inside = line.split("(", 1)[1].rsplit(")", 1)[0]
    names = set()
    for segment in inside.split(","):
        token = segment.strip().split("=")[0].split(":")[0].strip()
        if token:
            names.add(token)
    return names


def _signature_mismatch(name: str, documented: set[str]) -> tuple[list[str], list[str]]:
    """Return (missing, stale): implemented-but-unlisted and listed-but-removed names."""
    from siege_utilities.databricks import dataframe_bridge
    implemented = set(inspect.signature(getattr(dataframe_bridge, name)).parameters)
    return sorted(implemented - documented), sorted(documented - implemented)


@pytest.mark.parametrize("name", ["pandas_to_spark", "spark_to_pandas", "geopandas_to_spark", "spark_to_geopandas"])
def test_listed_bridge_signatures_match_module(name: str) -> None:
    line = next(l for l in _bridge_source().splitlines() if l.startswith(f"- `{name}("))
    missing, stale = _signature_mismatch(name, _documented_params(line))
    assert not missing and not stale, (
        f"{name} listing mismatch: missing {missing}, stale {stale}"
    )


def test_signature_check_flags_a_stale_documented_param() -> None:
    # A listed argument that the function no longer has must fail the check;
    # the earlier loop only walked implemented names and let it pass.
    line = next(l for l in _bridge_source().splitlines() if l.startswith("- `pandas_to_spark("))
    stale_line = line.replace("(", "(removed_param=None, ", 1)
    missing, stale = _signature_mismatch("pandas_to_spark", _documented_params(stale_line))
    assert stale == ["removed_param"] and not missing, (missing, stale)


def test_signature_check_flags_a_dropped_documented_param() -> None:
    # A shared prefix must not mask a missing parameter: dropping `crs=None`
    # while keeping `crs_column='geometry_crs'` has to be caught. The earlier
    # `param in line` substring check passed that mutation falsely.
    from siege_utilities.databricks import dataframe_bridge
    line = next(l for l in _bridge_source().splitlines() if l.startswith("- `spark_to_geopandas("))
    real = set(inspect.signature(dataframe_bridge.spark_to_geopandas).parameters)
    assert {"crs", "crs_column"} <= real, "fixture assumes both parameters exist"
    mutated = line.replace("crs=None, ", "")
    assert "crs=None" not in mutated and "crs_column=" in mutated, mutated
    # The discredited substring check still accepts the mutation (the false green).
    assert all(param in mutated for param in real)
    # The exact-identifier check flags the dropped parameter.
    documented = _documented_params(mutated)
    assert "crs_column" in documented and "crs" not in documented, documented
    assert [param for param in real if param not in documented] == ["crs"]

"""Keep the offline gazetteer demo and its geo notebook group truthful."""

import ast
from pathlib import Path

import nbformat
import pytest
from shapely.geometry import Point

from siege_utilities.geo.gazetteers.base import GazetteerNotFoundError
from tests import test_notebooks as notebook_runner


NOTEBOOK_PATH = (
    Path(__file__).resolve().parents[1]
    / "notebooks/spatial/07_natural_language_to_geometry.ipynb"
)


@pytest.fixture
def notebook():
    """Read and validate the shipped notebook, including stable cell metadata."""
    nb = nbformat.read(NOTEBOOK_PATH, as_version=4)
    nbformat.validate(nb)
    return nb


@pytest.fixture
def gazetteer(notebook):
    """Execute the real gazetteer definition and fixtures from the notebook."""
    cells = [
        cell for cell in notebook.cells
        if cell.cell_type == "code"
        and any(
            isinstance(node, ast.ClassDef) and node.name == "_DemoGazetteer"
            for node in ast.parse(cell.source).body
        )
    ]
    assert len(cells) == 1, "Expected one demo gazetteer definition"
    namespace = {}
    exec(compile(cells[0].source, str(NOTEBOOK_PATH), "exec"), namespace)
    return namespace["_DemoGazetteer"]()


def test_demo_names_resolve_to_distinct_geometries(gazetteer):
    lake = gazetteer.lookup("Lake Geneva")
    city = gazetteer.lookup("Lausanne")

    assert not lake.geometry.equals(city.geometry)
    for name, result in (("Lake Geneva", lake), ("Lausanne", city)):
        assert result.name == name
        assert result.geometry.is_valid and not result.geometry.is_empty
        assert result.centroid.equals(result.geometry.centroid)


def test_unknown_demo_name_is_rejected(gazetteer):
    with pytest.raises(GazetteerNotFoundError, match="Atlantis"):
        gazetteer.lookup("Atlantis")


@pytest.mark.parametrize("town, lon, lat", [
    ("Thonon-les-Bains", 6.479, 46.371),
    ("Evian-les-Bains", 6.590, 46.401),
])
def test_south_shore_towns_are_not_north_of_lake_geneva(gazetteer, town, lon, lat):
    lake = gazetteer.lookup("Lake Geneva")
    assert lake.geometry.contains(Point(6.55, 46.45)), "fixture must cover the Grand Lac"
    assert lat < lake.centroid.y, f"{town} is on the south shore"


def test_directional_demo_uses_the_lake_reference(notebook):
    namespace = {}
    for cell in notebook.cells:
        if cell.cell_type == "code":
            exec(compile(cell.source, str(NOTEBOOK_PATH), "exec"), namespace)
            if "predicate" in namespace:
                break

    lake = namespace["gz"].lookup("Lake Geneva")
    city = namespace["gz"].lookup("Lausanne")
    for mode in ("bounded", "halfplane", "predicate"):
        reference = namespace[mode].reference
        assert reference.name == "Lake Geneva"
        assert reference.geometry.equals(lake.geometry)

    # A point between the fixture centroids exposes a silent city fallback.
    assert lake.centroid.y != city.centroid.y
    between = Point(lake.centroid.x, (lake.centroid.y + city.centroid.y) / 2)
    predicate = namespace["predicate"].geometry
    assert predicate(between) == (between.y > lake.centroid.y)
    assert predicate(namespace["north_point"])
    assert not predicate(namespace["south_point"])


# Execute the existing geo notebook group so this regression also covers it in
# CI. These notebooks run unmocked -- 01_boundaries fetches real TIGER boundaries
# over the network -- so the group is marked `integration` and runs only in the
# network-enabled lane. The ordinary offline lane (`-m "not integration"`) must
# not run it, or 01_boundaries raises BoundaryFetchError. Offline, network-mocked
# coverage of the same geo group is provided separately by #1783; do not rely on
# this collector for the offline lane.
@pytest.mark.integration
@pytest.mark.requires_gdal
@pytest.mark.parametrize(
    "nb_rel", notebook_runner.NOTEBOOK_GROUPS["geo"],
    ids=lambda path: Path(path).stem,
)
def test_geo_notebook_group(nb_rel):
    notebook_runner._run_notebook(notebook_runner.NOTEBOOKS_DIR / nb_rel)

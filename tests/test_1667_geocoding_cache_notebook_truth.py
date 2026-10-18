"""Keep the geocoding narrative honest and execute the geo group offline (#1667)."""

import inspect
import re
import sys
from pathlib import Path

import nbformat
import pytest
from nbclient import NotebookClient

from tests.test_notebooks import NOTEBOOK_GROUPS


NOTEBOOKS_DIR = Path(__file__).resolve().parents[1] / "notebooks"
GEOCODING_NOTEBOOK = "spatial/02_geocoding.ipynb"


def test_geocoding_markdown_describes_an_in_memory_scan() -> None:
    notebook = nbformat.read(NOTEBOOKS_DIR / GEOCODING_NOTEBOOK, as_version=4)
    nbformat.validate(notebook)
    cells = {cell.id: cell for cell in notebook.cells}
    for cell in notebook.cells:
        if cell.cell_type == "markdown":
            assert not re.search(r"\bcach(?:e|ed|es|ing)\b|\bsecond run\b", cell.source, re.I), (
                f"{cell.id}: the timed cell scans collected results; "
                "remove claims about caching or a second geocoder run"
            )
    for cell_id in ("title", "s5"):
        assert "in-memory scan" in cells[cell_id].source.lower(), (
            f"{cell_id}: describe the timed operation as an in-memory scan"
        )
    assert cells["c5"].cell_type == "code"
    assert "[r.input_id for r in results if r.matched]" in cells["c5"].source


def _install_offline_services() -> tuple[list[str], object]:
    """Run inside each disposable kernel; keep the library's local work real."""
    import os
    import socket
    from unittest.mock import Mock

    import requests

    network_attempts = []

    def reject_network(*args, **kwargs):
        network_attempts.append("outbound network call")
        raise AssertionError("Geo notebooks must run offline in this test")

    requests.sessions.Session.request = reject_network
    socket.create_connection = reject_network
    socket.socket.connect = reject_network
    socket.socket.connect_ex = reject_network
    os.environ.pop("CENSUS_API_KEY", None)

    # These imports and patches stay in the child kernel, away from other tests.
    import geopandas as gpd
    from shapely.geometry import box

    from siege_utilities.geo.providers import census_geocoder
    from siege_utilities.geo.providers.boundary_providers import CensusTIGERProvider

    def get_boundary(self, level, identifier=None, **kwargs):
        assert kwargs == {"year": 2024}
        assert identifier == (None if level == "state" else "48")
        # Small synthetic shapes satisfy the provider's GeoDataFrame contract.
        rows = {
            "state": [("48", "", "Texas")],
            "county": [
                ("48453", "453", "Travis"),
                ("48201", "201", "Harris"),
                ("48113", "113", "Dallas"),
            ],
            "tract": [("48453000100", "453", "Tract 1")],
        }[level]
        return gpd.GeoDataFrame(
            {
                "geoid": [row[0] for row in rows],
                "countyfp": [row[1] for row in rows],
                "name": [row[2] for row in rows],
                "statefp": ["48"] * len(rows),
            },
            geometry=[box(-98 + i, 30, -97.5 + i, 30.5) for i in range(len(rows))],
            crs="EPSG:4326",
        )

    CensusTIGERProvider.get_boundary = get_boundary
    geocoder = Mock(spec=["addressbatch"])
    geocoder.addressbatch.return_value = [
        {
            "id": str(i),
            "match": True,
            "statefp": "48",
            "countyfp": county,
            "tract": "000100",
            "block": "1000",
            "lat": lat,
            "lon": lon,
        }
        for i, county, lat, lon in [
            (1, "453", 30.26, -97.75),
            (2, "113", 32.78, -96.77),
            (3, "201", 29.76, -95.37),
        ]
    ] + [{"id": "4", "match": False}, {"id": "5", "match": False}]
    census_geocoder._get_geocoder = Mock(return_value=geocoder)
    return network_attempts, geocoder


@pytest.mark.parametrize("nb_rel", NOTEBOOK_GROUPS["geo"])
def test_geo_notebook_group_runs_offline(nb_rel: str, tmp_path: Path) -> None:
    """The normal CI test job discovers this file, including all six geo notebooks."""
    notebook = nbformat.read(NOTEBOOKS_DIR / nb_rel, as_version=4)
    nbformat.validate(notebook)
    bootstrap = (
        f"import sys\nsys.path.insert(0, {str(NOTEBOOKS_DIR.parent)!r})\n"
        + inspect.getsource(_install_offline_services)
        + "\n_offline_attempts, _offline_geocoder = _install_offline_services()\n"
    )
    notebook.cells.insert(0, nbformat.v4.new_code_cell(bootstrap))
    checks = "assert not _offline_attempts, _offline_attempts\n"
    if nb_rel == GEOCODING_NOTEBOOK:
        checks += (
            "_offline_geocoder.addressbatch.assert_called_once()\n"
            "assert len(results) == 5\n"
            "assert matched_ids == ['1', '2', '3']\n"
            "assert unmatched['id'].tolist() == ['4', '5']\n"
        )
    notebook.cells.append(nbformat.v4.new_code_cell(checks))

    client = NotebookClient(
        notebook,
        timeout=120,
        kernel_name="python3",
        resources={"metadata": {"path": str(tmp_path)}},
    )
    # Use pytest's interpreter even if a developer has a different default kernel.
    client.create_kernel_manager()
    client.km.kernel_spec.argv = [
        sys.executable, "-m", "ipykernel_launcher", "-f", "{connection_file}",
    ]
    client.execute()
    nbformat.validate(notebook)

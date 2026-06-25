"""Error-path coverage (SU-4b) for siege_utilities.examples.enhanced_features_demo.

The demo module imports geopandas and the geo/reporting stack at import time,
so the suite is skipped where geopandas is unavailable. Where present, it
forces the two ``except (...) -> raise RuntimeError`` wrappers and the
top-level ``main()`` failure handler.
"""

import pytest

pytest.importorskip("geopandas")

import siege_utilities.examples.enhanced_features_demo as demo


def test_demo_spatial_data_sources_wraps_failure_as_runtime_error(monkeypatch):
    def boom(*a, **k):
        raise ValueError("census api unreachable")

    monkeypatch.setattr(demo, "get_census_boundaries", boom)

    with pytest.raises(RuntimeError) as exc_info:
        demo.demo_spatial_data_sources()
    assert "Census boundary download failed" in str(exc_info.value)


def test_demo_spatial_transformations_wraps_corrupt_input_as_runtime_error(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(demo, "get_download_directory", lambda: tmp_path)
    # A file that exists but is not a valid GeoPackage -> gpd.read_file raises.
    (tmp_path / "census_counties_2020.gpkg").write_bytes(b"not a real gpkg")

    with pytest.raises(RuntimeError) as exc_info:
        demo.demo_spatial_transformations()
    assert "Spatial transformation failed" in str(exc_info.value)


def test_main_returns_1_when_a_demo_raises(monkeypatch):
    def boom():
        raise RuntimeError("demo blew up")

    monkeypatch.setattr(demo, "demo_user_configuration", boom)

    assert demo.main() == 1

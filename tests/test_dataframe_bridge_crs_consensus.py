"""spark_to_geopandas must not silently unify mixed CRS.

Consensus finding C6 (#1354): when crs_column held more than one distinct
CRS, spark_to_geopandas took the first non-null value and dropped the
column, placing every other row under the wrong spatial reference with no
signal. The fix rejects a mixed crs_column. These tests pin the rejection
and the single-CRS restore/override paths.
"""
import pandas as pd
import pytest

pytest.importorskip("geopandas", reason="install geopandas+shapely to exercise the bridge")
pytest.importorskip("shapely", reason="install geopandas+shapely to exercise the bridge")

from siege_utilities.databricks import dataframe_bridge as bridge


def _patch_spark_to_pandas(monkeypatch, pdf):
    monkeypatch.setattr(bridge, "spark_to_pandas", lambda *a, **k: pdf.copy())


def test_mixed_crs_column_is_rejected(monkeypatch):
    pdf = pd.DataFrame(
        {
            "geometry": ["POINT (0 0)", "POINT (1 1)"],
            "geometry_crs": ["EPSG:4326", "EPSG:3857"],
        }
    )
    _patch_spark_to_pandas(monkeypatch, pdf)
    with pytest.raises(ValueError, match="multiple distinct CRS"):
        bridge.spark_to_geopandas(object(), geometry_column="geometry")


def test_single_crs_column_is_restored(monkeypatch):
    pdf = pd.DataFrame(
        {
            "geometry": ["POINT (0 0)", "POINT (1 1)"],
            "geometry_crs": ["EPSG:4326", "EPSG:4326"],
        }
    )
    _patch_spark_to_pandas(monkeypatch, pdf)
    gdf = bridge.spark_to_geopandas(object(), geometry_column="geometry")
    assert gdf.crs is not None and gdf.crs.to_epsg() == 4326
    assert "geometry_crs" not in gdf.columns


def test_explicit_crs_overrides_single_value(monkeypatch):
    pdf = pd.DataFrame(
        {
            "geometry": ["POINT (0 0)"],
            "geometry_crs": ["EPSG:4326"],
        }
    )
    _patch_spark_to_pandas(monkeypatch, pdf)
    gdf = bridge.spark_to_geopandas(object(), geometry_column="geometry", crs="EPSG:3857")
    assert gdf.crs.to_epsg() == 3857

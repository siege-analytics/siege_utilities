"""Tests for spatial runtime planning and Databricks loader fallback behavior."""

from siege_utilities.geo.databricks_fallback import select_spatial_loader
from siege_utilities.geo.spatial_runtime import (
    _parse_databricks_runtime_version,
    resolve_spatial_runtime_plan,
)


def test_parse_databricks_runtime_version():
    assert _parse_databricks_runtime_version("17.1.x-scala2.12") == (17, 1)
    assert _parse_databricks_runtime_version("16.4") == (16, 4)
    assert _parse_databricks_runtime_version(None) is None
    assert _parse_databricks_runtime_version("invalid") is None


def test_resolve_spatial_runtime_plan_prefers_native():
    plan = resolve_spatial_runtime_plan(
        databricks_runtime_version="17.1.x-scala2.12",
        sedona_available=True,
    )
    assert plan.runtime == "databricks_native"
    assert plan.loader_order == ["databricks_native", "sedona", "python"]
    assert plan.native_spatial_available is True
    assert plan.sedona_available is True


def test_resolve_spatial_runtime_plan_falls_back_to_sedona():
    plan = resolve_spatial_runtime_plan(
        databricks_runtime_version="15.4.x-scala2.12",
        sedona_available=True,
    )
    assert plan.runtime == "sedona"
    assert plan.loader_order == ["sedona", "python"]
    assert plan.native_spatial_available is False
    assert plan.sedona_available is True


def test_resolve_spatial_runtime_plan_falls_back_to_python():
    plan = resolve_spatial_runtime_plan(
        databricks_runtime_version="15.4.x-scala2.12",
        sedona_available=False,
    )
    assert plan.runtime == "python"
    assert plan.loader_order == ["python"]
    assert plan.native_spatial_available is False
    assert plan.sedona_available is False


def test_select_spatial_loader_prefers_native_when_available():
    plan = select_spatial_loader(
        ogr2ogr_available=True,
        sedona_available=True,
        native_spatial_available=True,
    )
    assert plan.primary_loader == "databricks_native"
    assert plan.loader_order == ["databricks_native", "ogr2ogr", "sedona", "python"]


def test_select_spatial_loader_prefers_ogr2ogr_without_native():
    plan = select_spatial_loader(
        ogr2ogr_available=True,
        sedona_available=True,
    )
    assert plan.primary_loader == "ogr2ogr"
    assert plan.loader_order == ["ogr2ogr", "sedona", "python"]


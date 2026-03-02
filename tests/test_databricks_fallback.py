"""Tests for Databricks spatial fallback planning helpers."""

import pytest

pytestmark = pytest.mark.databricks

from siege_utilities.geo.databricks_fallback import (
    build_census_ingest_targets,
    build_census_table_name,
    select_spatial_loader,
)


def test_select_spatial_loader_prefers_ogr2ogr() -> None:
    plan = select_spatial_loader(ogr2ogr_available=True, sedona_available=True)
    assert plan.primary_loader == "ogr2ogr"
    assert plan.loader_order == ["ogr2ogr", "sedona", "python"]


def test_select_spatial_loader_falls_back_to_sedona() -> None:
    plan = select_spatial_loader(ogr2ogr_available=False, sedona_available=True)
    assert plan.primary_loader == "sedona"
    assert plan.loader_order == ["sedona", "python"]


def test_select_spatial_loader_falls_back_to_python() -> None:
    plan = select_spatial_loader(ogr2ogr_available=False, sedona_available=False)
    assert plan.primary_loader == "python"
    assert plan.loader_order == ["python"]


def test_build_census_table_name_normalizes_alias() -> None:
    assert build_census_table_name(2024, "bg") == "census_2024_block_group"


def test_build_census_ingest_targets_dedupes_by_canonical_level() -> None:
    targets = build_census_ingest_targets(2024, ["bg", "block_group", "tract"])
    assert targets == ["census_2024_block_group", "census_2024_tract"]

"""Regression tests for CRS validation and reprojection in #1413."""

import pandas as pd
import pytest

from siege_utilities.databricks import dataframe_bridge as bridge

pytest.importorskip("geopandas")
shapely = pytest.importorskip("shapely")
pyproj = pytest.importorskip("pyproj")

pytestmark = pytest.mark.databricks


class SparkFrame:
    """Supply collected rows without requiring a Spark runtime."""

    def __init__(self, pdf):
        self.pdf = pdf

    def toPandas(self):
        return self.pdf.copy()


@pytest.mark.parametrize("missing_crs", [None, float("nan"), pd.NA])
@pytest.mark.parametrize("target_crs", [None, "EPSG:3857"])
def test_mixed_null_and_known_crs_raises(missing_crs, target_crs):
    frame = SparkFrame(pd.DataFrame({
        "geometry": ["POINT (1 1)", "POINT (2 2)"],
        "geometry_crs": ["EPSG:4326", missing_crs],
    }))

    with pytest.raises(ValueError, match="null.*non-null CRS"):
        bridge.spark_to_geopandas(frame, crs=target_crs)


@pytest.mark.parametrize("geometry_format", ["wkt", "wkb_hex"])
@pytest.mark.parametrize("custom_columns", [False, True])
def test_conflicting_crs_reprojects_coordinates(
    geometry_format, custom_columns,
):
    geometry_column = "shape" if custom_columns else "geometry"
    crs_column = "source_crs" if custom_columns else "geometry_crs"
    point = shapely.Point(1, 1)
    frame = SparkFrame(pd.DataFrame({
        "id": [7, 8],
        geometry_column: [getattr(point, geometry_format), None],
        crs_column: ["EPSG:4326", "EPSG:4326"],
    }, index=[3, 5]))

    result = bridge.spark_to_geopandas(
        frame, geometry_column=geometry_column,
        geometry_format=geometry_format,
        crs="EPSG:3857", crs_column=crs_column,
    )

    assert result.crs.to_epsg() == 3857
    assert result.geometry.iloc[0].x == pytest.approx(111319.49079327357)
    assert result.geometry.iloc[0].y == pytest.approx(111325.1428663851)
    assert result.geometry.iloc[1] is None
    assert result.geometry.name == geometry_column
    assert result.index.tolist() == [3, 5]
    assert result["id"].tolist() == [7, 8]
    assert crs_column not in result.columns


@pytest.mark.parametrize("target_crs", [None, "EPSG:4326", "epsg:4326"])
def test_matching_crs_preserves_coordinates(target_crs):
    frame = SparkFrame(pd.DataFrame({
        "geometry": ["POINT (1 1)"],
        "geometry_crs": ["EPSG:4326"],
    }))

    result = bridge.spark_to_geopandas(frame, crs=target_crs)

    assert result.crs.to_epsg() == 4326
    assert result.geometry.iloc[0].equals(shapely.Point(1, 1))
    assert "geometry_crs" not in result.columns


@pytest.mark.parametrize("include_crs_column", [False, True])
@pytest.mark.parametrize("target_crs", [None, "EPSG:4326"])
def test_unknown_source_crs_requires_caller_declaration(
    include_crs_column, target_crs,
):
    pdf = pd.DataFrame({"geometry": ["POINT (1 1)", "POINT (2 2)"]})
    if include_crs_column:
        pdf["geometry_crs"] = [None, pd.NA]

    result = bridge.spark_to_geopandas(SparkFrame(pdf), crs=target_crs)

    if target_crs is None:
        assert result.crs is None
    else:
        assert result.crs.to_epsg() == 4326
    assert result.geometry.iloc[0].equals(shapely.Point(1, 1))
    assert result.geometry.iloc[1].equals(shapely.Point(2, 2))
    assert "geometry_crs" not in result.columns


def test_target_crs_does_not_resolve_multiple_stored_crs():
    frame = SparkFrame(pd.DataFrame({
        "geometry": ["POINT (1 1)", "POINT (2 2)"],
        "geometry_crs": ["EPSG:4326", "EPSG:3857"],
    }))

    with pytest.raises(ValueError, match="multiple distinct CRS"):
        bridge.spark_to_geopandas(frame, crs="EPSG:3857")


def test_target_crs_cannot_hide_invalid_stored_crs():
    frame = SparkFrame(pd.DataFrame({
        "geometry": ["POINT (1 1)"],
        "geometry_crs": ["invalid-source-crs"],
    }))

    with pytest.raises(pyproj.exceptions.CRSError):
        bridge.spark_to_geopandas(frame, crs="EPSG:3857")


@pytest.mark.parametrize("target_crs", [None, "EPSG:3857"])
def test_empty_frame_has_no_crs_conflict(target_crs):
    frame = SparkFrame(pd.DataFrame(columns=["geometry", "geometry_crs"]))

    result = bridge.spark_to_geopandas(frame, crs=target_crs)

    assert result.empty
    assert "geometry_crs" not in result.columns
    if target_crs is None:
        assert result.crs is None
    else:
        assert result.crs.to_epsg() == 3857

"""multi_assign and the spatial_join CRS check across boundary layers (#1852, #1898, #1619)."""
import warnings

import pytest

gpd = pytest.importorskip("geopandas")

import pandas as pd  # noqa: E402 - after the optional-dependency skip
from shapely.geometry import Point, box  # noqa: E402

from siege_utilities.engines.dataframe_engine import (  # noqa: E402
    DuckDBEngine,
    PandasEngine,
    PostGISEngine,
    SparkEngine,
)

ENGINES = ["pandas", "duckdb", pytest.param("postgis", marks=pytest.mark.postgis)]
MISMATCH_WARNING = "CRS mismatch between the CRS of left geometries and the CRS of right geometries"


def _engine(name):
    if name == "pandas":
        return PandasEngine()
    if name == "duckdb":
        pytest.importorskip("duckdb")
        return DuckDBEngine()
    pytest.importorskip("sqlalchemy")
    # These joins run on the driver, so no database connection is opened.
    return PostGISEngine("postgresql://localhost/unused")


def _lonlat_layer():
    return gpd.GeoDataFrame({"d": ["x"]}, geometry=[box(-100, 25, -95, 35)], crs="EPSG:4326")


@pytest.mark.parametrize("engine_name", ENGINES)
def test_plain_layer_counts_as_unknown_crs_for_known_points(engine_name):
    # Points in a non-default CRS and a layer of WKT in the same coordinates
    # with no CRS metadata. The layer's CRS is unknown, so the check must not
    # compare the points against the default CRS that conversion would stamp.
    engine = _engine(engine_name)
    points = gpd.GeoDataFrame(
        {"id": [1, 2]}, geometry=[Point(-10850000, 3550000), Point(0, 0)], crs="EPSG:3857"
    )
    layer = pd.DataFrame({"d": ["x"], "geometry": [box(-11000000, 3400000, -10700000, 3700000).wkt]})
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        result = engine.multi_assign(points, {"district": layer})
    result = result.sort_values("id").reset_index(drop=True)
    assert result["district_d"].tolist()[0] == "x"
    assert result["district_d"].isna().tolist() == [False, True]
    # The assigned frame keeps the points' geometry and CRS.
    assert result.crs == points.crs
    assert all(a.equals(b) for a, b in zip(result.geometry, points.geometry))
    # The only CRS warning is geopandas' known/unknown CRS notice from sjoin.
    # Warnings about anything other than CRS are outside this test.
    messages = [str(w.message) for w in caught if "CRS" in str(w.message)]
    assert messages and all(m.startswith(MISMATCH_WARNING) for m in messages), messages


def _reject_set_crs_none(original):
    # geopandas < 1.0 raises "Must pass either crs or epsg." from set_crs
    # when crs and epsg are both None; geopandas 1.x accepts it.
    def set_crs(self, crs=None, epsg=None, inplace=False, allow_override=False):
        if crs is None and epsg is None:
            raise ValueError("Must pass either crs or epsg.")
        return original(self, crs=crs, epsg=epsg, inplace=inplace, allow_override=allow_override)

    return set_crs


@pytest.mark.parametrize("engine_name", ENGINES)
def test_plain_layer_crs_is_removed_without_set_crs_none(engine_name, monkeypatch):
    # The pyproject floor is geopandas 0.13.2, where set_crs(None) raises.
    # Simulate that and check that multi_assign still joins non-default-CRS
    # points with a plain layer. Had the layer kept the default CRS that
    # conversion gives it, the spatial_join check would raise a mismatch, so
    # the join result shows the CRS was removed without set_crs(None).
    monkeypatch.setattr(gpd.GeoDataFrame, "set_crs", _reject_set_crs_none(gpd.GeoDataFrame.set_crs))
    monkeypatch.setattr(gpd.GeoSeries, "set_crs", _reject_set_crs_none(gpd.GeoSeries.set_crs))
    engine = _engine(engine_name)
    points = gpd.GeoDataFrame(
        {"id": [1, 2]}, geometry=[Point(-10850000, 3550000), Point(0, 0)], crs="EPSG:3857"
    )
    layer = pd.DataFrame({"d": ["x"], "geometry": [box(-11000000, 3400000, -10700000, 3700000).wkt]})
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        result = engine.multi_assign(points, {"district": layer})
    result = result.sort_values("id").reset_index(drop=True)
    assert result["district_d"].isna().tolist() == [False, True]
    assert result.crs == points.crs


@pytest.mark.parametrize("engine_name", ["pandas", "duckdb"])
def test_removing_a_layer_crs_leaves_the_callers_geometry_column_alone(engine_name):
    # A plain DataFrame holding a typed geometry column has no frame-level CRS,
    # so multi_assign treats the layer as unknown and removes the converted
    # CRS (the current contract; a follow-up may enforce the column's CRS).
    # Whatever conversion returns, the removal must leave the caller's column
    # CRS as it was.
    engine = _engine(engine_name)
    points = gpd.GeoDataFrame(
        {"id": [1]}, geometry=[Point(-10850000, 3550000)], crs="EPSG:3857"
    )
    layer = pd.DataFrame(_lonlat_layer())
    assert layer["geometry"].values.crs == "EPSG:4326"
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        engine.multi_assign(points, {"district": layer})
    assert layer["geometry"].values.crs == "EPSG:4326"


@pytest.mark.parametrize("engine_name", ENGINES)
def test_plain_layer_with_default_crs_points_joins_without_a_warning(engine_name):
    # The common case: points in the default CRS and a plain lon/lat layer.
    # The layer keeps the default CRS that conversion gives it, as a direct
    # spatial_join would, so there is neither a false mismatch nor a warning.
    engine = _engine(engine_name)
    points = gpd.GeoDataFrame(
        {"id": [1, 2]}, geometry=[Point(-97.7, 30.3), Point(0, 0)], crs="EPSG:4326"
    )
    layer = pd.DataFrame({"d": ["x"], "geometry": [box(-100, 25, -95, 35).wkt]})
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        result = engine.multi_assign(points, {"district": layer})
    result = result.sort_values("id").reset_index(drop=True)
    assert result["district_d"].isna().tolist() == [False, True]
    assert result.crs == points.crs
    assert not [w for w in caught if str(w.message).startswith(MISMATCH_WARNING)]


@pytest.mark.parametrize("engine_name", ENGINES)
def test_known_mismatching_layer_still_raises(engine_name):
    engine = _engine(engine_name)
    points = gpd.GeoDataFrame({"id": [1]}, geometry=[Point(-97.7, 30.3)], crs="EPSG:4326").to_crs(3857)
    with pytest.raises(ValueError) as exc_info:
        engine.multi_assign(points, {"district": _lonlat_layer()})
    assert str(exc_info.value) == (
        "CRS mismatch in spatial_join: left has EPSG:3857, "
        "right has EPSG:4326. Reproject one input to match the other."
    )


@pytest.mark.postgis
def test_postgis_multi_assign_checks_a_later_layer():
    # #1898: PostGIS multi_assign checked only the first boundary layer.
    engine = _engine("postgis")
    points = gpd.GeoDataFrame({"id": [1]}, geometry=[Point(-97.7, 30.3)], crs="EPSG:4326").to_crs(3857)
    layers = {
        "district": _lonlat_layer().to_crs(3857),
        "county": _lonlat_layer().rename(columns={"d": "c"}),
    }
    with pytest.raises(ValueError) as exc_info:
        engine.multi_assign(points, layers)
    assert str(exc_info.value) == (
        "CRS mismatch in spatial_join: left has EPSG:3857, "
        "right has EPSG:4326. Reproject one input to match the other."
    )


@pytest.mark.parametrize("engine_name", ENGINES)
def test_multi_assign_rejects_a_repeated_layer_name(engine_name):
    engine = _engine(engine_name)
    points = gpd.GeoDataFrame({"id": [1]}, geometry=[Point(-97.7, 30.3)], crs="EPSG:4326")
    enriched = engine.multi_assign(points, {"district": _lonlat_layer()})
    with pytest.raises(ValueError) as exc_info:
        engine.multi_assign(enriched, {"district": _lonlat_layer()})
    assert str(exc_info.value) == (
        "multi_assign: layer columns collide with point columns: ['district_d']"
    )


@pytest.mark.requires_spark
def test_spark_multi_assign_rejects_a_repeated_layer_name(real_spark_session):
    engine = SparkEngine(real_spark_session)
    points = real_spark_session.createDataFrame(
        [(1, "POINT (0.5 0.5)", "x")], ["id", "geometry", "district_d"]
    )
    layer = real_spark_session.createDataFrame(
        [("x", "POLYGON ((0 0, 1 0, 1 1, 0 1, 0 0))")], ["d", "geometry"]
    )
    with pytest.raises(ValueError) as exc_info:
        engine.multi_assign(points, {"district": layer})
    assert str(exc_info.value) == (
        "multi_assign: layer columns collide with point columns: ['district_d']"
    )

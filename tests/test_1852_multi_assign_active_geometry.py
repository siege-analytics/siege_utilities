"""multi_assign keeps a boundary layer's active geometry column when it is not named "geometry" (#1852)."""
import pytest

gpd = pytest.importorskip("geopandas")
pytest.importorskip("duckdb")

from shapely.geometry import Point, box  # noqa: E402

from siege_utilities.engines.dataframe_engine import DuckDBEngine, PandasEngine  # noqa: E402


@pytest.fixture(params=["pandas", "duckdb"])
def engine(request):
    if request.param == "pandas":
        yield PandasEngine()
        return
    duck = DuckDBEngine()
    yield duck
    duck._connection.close()


def test_multi_assign_layer_with_active_geometry_named_geom(engine):
    points = gpd.GeoDataFrame({"pid": [1, 2]}, geometry=[Point(0.5, 0.5), Point(5, 5)], crs=4326)
    layer = gpd.GeoDataFrame({"name": ["a"]}, geometry=[box(0, 0, 1, 1)], crs=4326).rename_geometry("geom")
    out = engine.multi_assign(points, {"county": layer})
    assert out.sort_values("pid")["county_name"].tolist()[0] == "a"
    assert out.sort_values("pid")["county_name"].isna().tolist() == [False, True]


def test_multi_assign_layer_with_extra_column_named_geometry(engine):
    # Active geometry "geom"; a non-active geometry column named "geometry" is
    # an attribute and is prefixed like any other.
    points = gpd.GeoDataFrame({"pid": [1]}, geometry=[Point(0.5, 0.5)], crs=4326)
    layer = gpd.GeoDataFrame({"name": ["a"]}, geometry=[box(0, 0, 1, 1)], crs=4326).rename_geometry("geom")
    layer["geometry"] = gpd.GeoSeries([Point(9, 9)], crs=4326)
    out = engine.multi_assign(points, {"county": layer})
    assert out["county_name"].tolist() == ["a"]
    assert "county_geometry" in out.columns

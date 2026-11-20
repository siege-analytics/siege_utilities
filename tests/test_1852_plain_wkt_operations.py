"""Plain WKT is read at EPSG:4326 and reprojected to a requested ``crs`` (#1852).

Base ``dissolve``, ``apportion`` and ``nearest`` accept plain DataFrames with
WKT text. Their coordinates are lon/lat at the default CRS, so a projected
``crs`` must reproject them, not relabel lon/lat numbers as projected metres.
"""

from collections.abc import Iterator
from typing import Any

import pandas as pd
import pytest

gpd = pytest.importorskip("geopandas")
from shapely.geometry import Point, box  # noqa: E402 - after the geopandas skip

from siege_utilities.engines.dataframe_engine import DuckDBEngine, PandasEngine, PostGISEngine  # noqa: E402

PROJECTED = "EPSG:5070"


@pytest.fixture(params=["pandas", "duckdb", "postgis"])
def engine(request: pytest.FixtureRequest) -> Iterator[Any]:
    if request.param == "duckdb":
        pytest.importorskip("duckdb")
        result = DuckDBEngine()
        yield result
        result._connection.close()
    elif request.param == "postgis":
        pytest.importorskip("sqlalchemy")
        # These inherited operations run in GeoPandas; no database is contacted.
        yield PostGISEngine("postgresql://unused")
    else:
        yield PandasEngine()


def _wkt_frame(column: str, values: list[Any], geometries: list[Any]) -> pd.DataFrame:
    return pd.DataFrame({column: values, "geometry": [g.wkt for g in geometries]})


def _projected(geometries: list[Any]) -> Any:
    return gpd.GeoSeries(geometries, crs=4326).to_crs(PROJECTED)


def test_dissolve_reprojects_plain_wkt(engine: Any) -> None:
    shapes = [box(-98, 30, -97, 31), box(-97, 30, -96, 31)]
    out = engine.dissolve(_wkt_frame("group", ["a", "a"], shapes), "group", crs=PROJECTED)

    assert out.crs.to_epsg() == 5070
    expected = _projected(shapes).union_all()
    # Projected metres, not lon/lat numbers relabelled as metres.
    assert abs(out.geometry.iloc[0].bounds[0]) > 1000
    assert out.geometry.iloc[0].symmetric_difference(expected).area < 1e-6 * expected.area


def test_apportion_reprojects_plain_wkt(engine: Any) -> None:
    # Splitting by latitude: planar degrees give a share of exactly 0.5, the
    # reprojected areas do not, so relabelling lon/lat would be visible.
    source = [box(-100, 30, -90, 40)]
    targets = [box(-100, 30, -90, 35), box(-100, 35, -90, 40)]
    result = engine.apportion(
        _wkt_frame("pop", [1000.0], source), _wkt_frame("tid", [1, 2], targets), "pop", crs=PROJECTED,
    )

    expected = PandasEngine().apportion(
        gpd.GeoDataFrame({"pop": [1000.0]}, geometry=_projected(source)),
        gpd.GeoDataFrame({"tid": [1, 2]}, geometry=_projected(targets)),
        "pop",
    )
    shares = result.set_index("tid")["apportioned_pop"]
    assert shares.loc[1] == pytest.approx(expected.set_index("tid")["apportioned_pop"].loc[1], rel=1e-9)
    assert abs(shares.loc[1] - 500.0) > 1.0


def test_nearest_reprojects_plain_wkt(engine: Any) -> None:
    points = [Point(-97.74, 30.27)]
    targets = [Point(-97.73, 30.27)]
    result = engine.nearest(
        _wkt_frame("pid", [1], points), _wkt_frame("tid", [9], targets), crs=PROJECTED,
    )

    expected = _projected(points).distance(_projected(targets)).iloc[0]
    # About a kilometre in projected metres, not 0.01 lon/lat "metres".
    assert result["distance"].iloc[0] == pytest.approx(expected, rel=1e-9)
    assert result["distance"].iloc[0] > 500

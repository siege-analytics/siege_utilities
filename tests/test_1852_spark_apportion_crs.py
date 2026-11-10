"""On SparkEngine, apportion's ``crs`` declares the stored CRS (#1852).

Spark stores no source CRS, so ``crs`` names the CRS the stored coordinates are
already in, as SparkEngine.to_geodataframe documents; it does not reproject.
Given the coordinates' actual projected CRS, Spark apportion must match the
pandas engine on the same data.
"""

from types import SimpleNamespace

import pandas as pd
import pytest

gpd = pytest.importorskip("geopandas")
from shapely.geometry import box  # noqa: E402 - after the geopandas skip

from siege_utilities.engines.dataframe_engine import PandasEngine, SparkEngine  # noqa: E402

PROJECTED = "EPSG:5070"
SOURCE = [box(0, 0, 1000, 1000)]
TARGETS = [box(0, 0, 300, 1000), box(300, 0, 1000, 1000)]


def _stored(column: str, values: list, geometries: list) -> SimpleNamespace:
    """A Spark-shaped frame: WKT text that converts to pandas on demand."""
    frame = pd.DataFrame({column: values, "geometry": [g.wkt for g in geometries]})
    return SimpleNamespace(toPandas=lambda: frame.copy())


def _spark_engine() -> SparkEngine:
    # Bypass __init__: no JVM is needed, because apportion converts to
    # GeoPandas through toPandas and runs the shared GeoPandas implementation.
    engine = SparkEngine.__new__(SparkEngine)
    engine._spark = None
    engine._enable_sedona = False
    engine._sedona_registered = False
    return engine


def test_spark_apportion_with_declared_projected_crs_matches_pandas() -> None:
    spark_result = _spark_engine().apportion(
        _stored("pop", [1000.0], SOURCE),
        _stored("tid", [1, 2], TARGETS),
        "pop",
        crs=PROJECTED,
    )
    pandas_result = PandasEngine().apportion(
        gpd.GeoDataFrame({"pop": [1000.0]}, geometry=SOURCE, crs=PROJECTED),
        gpd.GeoDataFrame({"tid": [1, 2]}, geometry=TARGETS, crs=PROJECTED),
        "pop",
    )

    spark_shares = spark_result.set_index("tid")["apportioned_pop"].sort_index()
    pandas_shares = pandas_result.set_index("tid")["apportioned_pop"].sort_index()
    pd.testing.assert_series_equal(spark_shares, pandas_shares, check_exact=False, rtol=1e-12)
    # The stored metres were used as-is: a 300/700 split of 1000.
    assert spark_shares.tolist() == pytest.approx([300.0, 700.0], rel=1e-12)

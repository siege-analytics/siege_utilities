"""End-to-end geopandas <-> Spark bridge round-trip on a real SparkSession.

Regression guard for #1336: geopandas_to_spark preserves the CRS in a
``geometry_crs`` column, and spark_to_geopandas must restore it so the
round-trip keeps its spatial reference instead of silently returning
``crs=None``. Also covers the explicit-``crs`` override path.

These converters live under the ``databricks`` package but carry no
Databricks-runtime dependency -- they serialize geometry as WKT/WKB and run
against any local SparkSession plus geopandas/shapely.

Uses the session-scoped ``real_spark_session`` fixture (skips cleanly when
pyspark is absent); skips when geopandas/shapely are absent.
"""

import pytest

from siege_utilities import geopandas_to_spark
from siege_utilities import spark_to_geopandas


@pytest.mark.e2e
class TestGeopandasBridgeE2E:
    def _geoframe(self):
        gpd = pytest.importorskip("geopandas")
        shapely_geometry = pytest.importorskip("shapely.geometry")
        Point = shapely_geometry.Point
        return gpd.GeoDataFrame(
            {"id": [1, 2], "geometry": [Point(0, 0), Point(1, 1)]},
            crs="EPSG:4326",
        )

    def test_round_trip_preserves_crs(self, real_spark_session):
        gdf = self._geoframe()

        sdf = geopandas_to_spark(gdf, real_spark_session)
        assert "geometry_crs" in sdf.columns

        back = spark_to_geopandas(sdf)

        # the CRS survives the round-trip (the #1336 defect returned None).
        assert back.crs is not None
        assert back.crs.to_epsg() == 4326
        # the preserved-CRS column is metadata and must not leak into output.
        assert "geometry_crs" not in back.columns
        # geometry itself round-trips unchanged.
        coords = sorted((p.x, p.y) for p in back.geometry)
        assert coords == [(0.0, 0.0), (1.0, 1.0)]

    def test_explicit_crs_overrides_preserved_column(self, real_spark_session):
        gdf = self._geoframe()  # crs EPSG:4326 preserved in the column

        sdf = geopandas_to_spark(gdf, real_spark_session)
        back = spark_to_geopandas(sdf, crs="EPSG:3857")

        # the explicit argument wins over the preserved column value.
        assert back.crs.to_epsg() == 3857
        assert "geometry_crs" not in back.columns

    def test_round_trip_preserves_non_epsg_crs(self, real_spark_session):
        # A non-EPSG authority CRS (World Mollweide) has no EPSG code, so a
        # to_epsg()-based check would miss a regression here. Compare the CRS
        # objects directly to guard the non-EPSG restoration path too.
        gpd = pytest.importorskip("geopandas")
        shapely_geometry = pytest.importorskip("shapely.geometry")
        Point = shapely_geometry.Point
        gdf = gpd.GeoDataFrame(
            {"id": [1], "geometry": [Point(0, 0)]},
            crs="ESRI:54009",
        )

        sdf = geopandas_to_spark(gdf, real_spark_session)
        back = spark_to_geopandas(sdf)

        assert back.crs is not None
        assert back.crs == gdf.crs
        assert "geometry_crs" not in back.columns

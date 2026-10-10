"""End-to-end guard for serializing a null-CRS GeoDataFrame to Spark.

Regression guard for #1338: geopandas_to_spark previously assigned the CRS
metadata column as an all-None pandas column when the GeoDataFrame had no CRS,
and Spark's type inference then raised CANNOT_DETERMINE_TYPE, so a legitimately
CRS-less GeoDataFrame could not be serialized at all. The fix appends the
metadata column as an explicitly string-typed literal.

Uses the session-scoped ``real_spark_session`` fixture (skips cleanly when
pyspark is absent); skips when geopandas/shapely are absent.
"""

import pytest

from siege_utilities import geopandas_to_spark
from siege_utilities import spark_to_geopandas


@pytest.mark.e2e
class TestGeopandasNullCrsE2E:
    def _null_crs_frame(self):
        gpd = pytest.importorskip("geopandas")
        shapely_geometry = pytest.importorskip("shapely.geometry")
        Point = shapely_geometry.Point
        return gpd.GeoDataFrame(
            {"id": [1, 2], "geometry": [Point(0, 0), Point(1, 1)]},
            crs=None,
        )

    def test_serializes_null_crs_as_typed_string_column(
        self, real_spark_session
    ):
        gdf = self._null_crs_frame()

        # pre-fix this raised PySparkValueError CANNOT_DETERMINE_TYPE.
        sdf = geopandas_to_spark(gdf, real_spark_session)

        assert sdf.count() == 2
        assert "geometry_crs" in sdf.columns
        # the metadata column is explicitly string-typed, not an untyped
        # all-null column Spark cannot infer.
        assert dict(sdf.dtypes)["geometry_crs"] == "string"
        rows = sdf.select("geometry_crs").collect()
        assert {r["geometry_crs"] for r in rows} == {None}

    def test_null_crs_round_trips_to_none(self, real_spark_session):
        gdf = self._null_crs_frame()

        sdf = geopandas_to_spark(gdf, real_spark_session)
        back = spark_to_geopandas(sdf)

        # a CRS-less frame round-trips back to crs=None (no fabricated CRS).
        assert back.crs is None
        coords = sorted((p.x, p.y) for p in back.geometry)
        assert coords == [(0.0, 0.0), (1.0, 1.0)]

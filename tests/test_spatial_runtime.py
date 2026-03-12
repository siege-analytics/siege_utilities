"""Tests for spatial runtime planning and Databricks loader fallback behavior."""

from unittest import mock

import pytest

from siege_utilities.geo.databricks_fallback import select_spatial_loader
from siege_utilities.geo.spatial_runtime import (
    GeometryPayload,
    _parse_databricks_runtime_version,
    resolve_spatial_runtime_plan,
)

# Shapely may or may not be installed; conditionally import for skip markers.
try:
    from shapely.geometry import Point, Polygon

    _HAS_SHAPELY = True
except ImportError:
    _HAS_SHAPELY = False

needs_shapely = pytest.mark.skipif(not _HAS_SHAPELY, reason="shapely not installed")


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


# -----------------------------------------------------------------------
# GeometryPayload tests
# -----------------------------------------------------------------------


class TestGeometryPayloadCreation:
    """Test basic GeometryPayload construction."""

    def test_default_values(self):
        p = GeometryPayload()
        assert p.geometry_wkt is None
        assert p.geometry_wkb is None
        assert p.geometry_geojson is None
        assert p.crs == "EPSG:4326"
        assert p.geometry_type is None

    def test_explicit_values(self):
        p = GeometryPayload(
            geometry_wkt="POINT (1 2)",
            crs="EPSG:3857",
            geometry_type="Point",
        )
        assert p.geometry_wkt == "POINT (1 2)"
        assert p.crs == "EPSG:3857"
        assert p.geometry_type == "Point"


# -----------------------------------------------------------------------
# Encode / decode round-trip tests (require shapely)
# -----------------------------------------------------------------------


class TestEncodeDecodeRoundTrip:
    """Round-trip encoding and decoding through GeometryPayload."""

    @needs_shapely
    def test_point_roundtrip(self):
        from siege_utilities.geo.spatial_runtime import decode_geometry, encode_geometry

        pt = Point(1.5, 2.5)
        payload = encode_geometry(pt)
        assert payload.geometry_type == "Point"
        assert payload.geometry_wkt is not None
        assert payload.geometry_wkb is not None
        assert payload.geometry_geojson is not None
        assert payload.crs == "EPSG:4326"

        restored = decode_geometry(payload)
        assert restored.equals(pt)

    @needs_shapely
    def test_polygon_roundtrip(self):
        from siege_utilities.geo.spatial_runtime import decode_geometry, encode_geometry

        poly = Polygon([(0, 0), (1, 0), (1, 1), (0, 1)])
        payload = encode_geometry(poly, crs="EPSG:3857")
        assert payload.geometry_type == "Polygon"
        assert payload.crs == "EPSG:3857"

        restored = decode_geometry(payload)
        assert restored.equals(poly)

    @needs_shapely
    def test_decode_prefers_wkt(self):
        """decode_geometry should use WKT when available."""
        from siege_utilities.geo.spatial_runtime import decode_geometry, encode_geometry

        pt = Point(3, 4)
        payload = encode_geometry(pt)
        # Clear wkb and geojson to prove WKT path is taken
        payload_wkt_only = GeometryPayload(geometry_wkt=payload.geometry_wkt)
        restored = decode_geometry(payload_wkt_only)
        assert restored.equals(pt)

    @needs_shapely
    def test_decode_falls_back_to_wkb(self):
        from siege_utilities.geo.spatial_runtime import decode_geometry, encode_geometry

        pt = Point(5, 6)
        payload = encode_geometry(pt)
        payload_wkb_only = GeometryPayload(geometry_wkb=payload.geometry_wkb)
        restored = decode_geometry(payload_wkb_only)
        assert restored.equals(pt)

    @needs_shapely
    def test_decode_falls_back_to_geojson(self):
        from siege_utilities.geo.spatial_runtime import decode_geometry, encode_geometry

        pt = Point(7, 8)
        payload = encode_geometry(pt)
        payload_geojson_only = GeometryPayload(geometry_geojson=payload.geometry_geojson)
        restored = decode_geometry(payload_geojson_only)
        assert restored.equals(pt)

    @needs_shapely
    def test_decode_empty_payload_raises(self):
        from siege_utilities.geo.spatial_runtime import decode_geometry

        with pytest.raises(ValueError, match="no geometry data"):
            decode_geometry(GeometryPayload())

    @needs_shapely
    def test_encode_non_geometry_raises(self):
        from siege_utilities.geo.spatial_runtime import encode_geometry

        with pytest.raises(TypeError, match="Expected a shapely BaseGeometry"):
            encode_geometry("not a geometry")

    @needs_shapely
    def test_custom_crs_preserved(self):
        from siege_utilities.geo.spatial_runtime import encode_geometry

        payload = encode_geometry(Point(0, 0), crs="EPSG:32618")
        assert payload.crs == "EPSG:32618"


# -----------------------------------------------------------------------
# Spark row round-trip tests
# -----------------------------------------------------------------------


class TestSparkRowRoundTrip:
    """payload_to_spark_row / spark_row_to_payload round-trip."""

    @needs_shapely
    def test_point_spark_roundtrip(self):
        from siege_utilities.geo.spatial_runtime import (
            decode_geometry,
            encode_geometry,
            payload_to_spark_row,
            spark_row_to_payload,
        )

        pt = Point(10, 20)
        payload = encode_geometry(pt)
        row = payload_to_spark_row(payload)

        # All row values must be str or None (Spark-safe)
        for key, val in row.items():
            assert val is None or isinstance(val, str), f"{key} is {type(val)}"

        restored_payload = spark_row_to_payload(row)
        restored_geom = decode_geometry(restored_payload)
        assert restored_geom.equals(pt)

    @needs_shapely
    def test_polygon_spark_roundtrip(self):
        from siege_utilities.geo.spatial_runtime import (
            decode_geometry,
            encode_geometry,
            payload_to_spark_row,
            spark_row_to_payload,
        )

        poly = Polygon([(0, 0), (4, 0), (4, 4), (0, 4)])
        payload = encode_geometry(poly, crs="EPSG:2263")
        row = payload_to_spark_row(payload)
        restored_payload = spark_row_to_payload(row)
        assert restored_payload.crs == "EPSG:2263"
        restored_geom = decode_geometry(restored_payload)
        assert restored_geom.equals(poly)

    def test_spark_row_with_none_fields(self):
        """Handles payload with all-None geometry fields gracefully."""
        from siege_utilities.geo.spatial_runtime import (
            payload_to_spark_row,
            spark_row_to_payload,
        )

        payload = GeometryPayload()
        row = payload_to_spark_row(payload)
        assert row["geometry_wkt"] is None
        assert row["geometry_wkb_b64"] is None
        assert row["geometry_geojson"] is None

        restored = spark_row_to_payload(row)
        assert restored.geometry_wkt is None
        assert restored.geometry_wkb is None
        assert restored.geometry_geojson is None


# -----------------------------------------------------------------------
# Missing-shapely guard tests
# -----------------------------------------------------------------------


class TestMissingShapelyGuard:
    """Verify that codec functions raise ImportError when shapely is absent."""

    def test_encode_geometry_without_shapely(self):
        with mock.patch.dict("sys.modules", {"shapely": None, "shapely.geometry": None, "shapely.geometry.base": None, "shapely.wkt": None, "shapely.wkb": None}):
            # Force _SHAPELY_AVAILABLE to False
            import siege_utilities.geo.spatial_runtime as sr

            original = sr._SHAPELY_AVAILABLE
            sr._SHAPELY_AVAILABLE = False
            try:
                with pytest.raises(ImportError, match="requires shapely"):
                    sr.encode_geometry(object())
            finally:
                sr._SHAPELY_AVAILABLE = original

    def test_decode_geometry_without_shapely(self):
        import siege_utilities.geo.spatial_runtime as sr

        original = sr._SHAPELY_AVAILABLE
        sr._SHAPELY_AVAILABLE = False
        try:
            with pytest.raises(ImportError, match="requires shapely"):
                sr.decode_geometry(GeometryPayload(geometry_wkt="POINT (0 0)"))
        finally:
            sr._SHAPELY_AVAILABLE = original


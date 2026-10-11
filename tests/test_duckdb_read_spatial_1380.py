"""Issue #1380: DuckDBEngine.read_spatial robustness across duckdb 1.4.x/1.5.x.

Locks the output schema and attribute addressing so the driver-injected
OGC_FID column (emitted by duckdb spatial 1.5.x, not 1.4.x) cannot silently
change the column set, and so the cross-model review findings stay fixed:
- a feature property named ``geom`` stays addressable while the real geometry
  becomes ``geom_1`` (geometry identified by type, not name);
- a property literally named ``column_0`` is not shadowed by a fallback name;
- a property literally named ``c0`` does not collide with a positional alias;
- a column of geometry ARRAYS is not ST_AsWKB'd (scalar-only detection).
"""

import json
import tempfile

import pytest


def _geojson(props: dict, coords=(1, 2)) -> str:
    f = tempfile.NamedTemporaryFile(suffix=".geojson", delete=False, mode="w")
    f.write(
        json.dumps(
            {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "properties": props,
                        "geometry": {"type": "Point", "coordinates": list(coords)},
                    }
                ],
            }
        )
    )
    f.close()
    return f.name


def _engine():
    pytest.importorskip("geopandas")
    pytest.importorskip("duckdb")
    from siege_utilities.engines.dataframe_engine import DuckDBEngine

    return DuckDBEngine()


def test_simple_point_schema_has_no_injected_column():
    from shapely.geometry import Point

    gdf = _engine().read_spatial(_geojson({"id": 1}), crs="EPSG:4326")
    # Version-consistent schema: exactly the attribute + geometry, no OGC_FID.
    assert list(gdf.columns) == ["id", "geom"], list(gdf.columns)
    assert gdf.geometry.iloc[0].equals(Point(1, 2))


def test_geom_property_clash_keeps_int_and_real_geometry():
    from shapely.geometry import Point

    gdf = _engine().read_spatial(_geojson({"geom": 123}), crs="EPSG:4326")
    assert list(gdf.columns) == ["geom", "geom_1"], list(gdf.columns)
    assert int(gdf["geom"].iloc[0]) == 123
    assert gdf.geometry.iloc[0].equals(Point(1, 2))


def test_property_named_column_0_is_not_shadowed():
    gdf = _engine().read_spatial(_geojson({"column_0": 44}), crs="EPSG:4326")
    assert "column_0" in gdf.columns
    assert int(gdf["column_0"].iloc[0]) == 44, list(gdf.columns)


def test_property_named_c0_does_not_collide_with_alias():
    gdf = _engine().read_spatial(_geojson({"c0": 999, "foo": 7}), crs="EPSG:4326")
    assert int(gdf["c0"].iloc[0]) == 999, list(gdf.columns)
    assert int(gdf["foo"].iloc[0]) == 7, list(gdf.columns)


def test_geometry_array_column_is_not_aswkb_materialized():
    # A column of geometry ARRAYS must not be ST_AsWKB'd (that raises a
    # BinderException); scalar-only detection leaves it untouched.
    eng = _engine()
    eng._ensure_spatial()
    rel = eng._connection.sql("SELECT [ST_Point(1,2), ST_Point(3,4)] AS pts, 5 AS n")
    out = eng._materialize_geometry_wkb(rel)
    assert list(out.columns) == ["pts", "n"], list(out.columns)
    assert len(out) == 1


def test_geometry_column_positions_type_matrix():
    # Deterministic coverage of the scalar-vs-collection discriminator across
    # every geometry type spelling, without needing a live engine. Scalar
    # geometry (bare or CRS/PROJJSON-qualified) is detected; every bracketed
    # collection spelling is excluded (ST_AsWKB cannot apply to an array).
    from siege_utilities.engines.dataframe_engine import DuckDBEngine

    class _Rel:
        def __init__(self, types):
            self.types = types

    types = [
        "GEOMETRY",                         # 0 scalar bare
        "GEOMETRY('EPSG:4326')",            # 1 scalar CRS
        "GEOMETRY('PROJCS[\"X\",...]')",   # 2 scalar PROJJSON (brackets inside parens)
        "VARCHAR",                          # 3 not geometry
        "GEOMETRY[]",                       # 4 collection bare
        "GEOMETRY[3]",                      # 5 collection fixed
        "GEOMETRY('EPSG:4326')[]",          # 6 collection CRS-qualified
        "GEOMETRY('EPSG:4326')[][]",        # 7 collection nested
        "BIGINT",                           # 8 not geometry
    ]
    positions = DuckDBEngine._geometry_column_positions(_Rel(types))
    assert positions == [0, 1, 2], positions


def test_crs_qualified_geometry_array_is_not_aswkb_materialized():
    # ``list(geom)`` over a scanned file yields a CRS-qualified collection type
    # ``GEOMETRY('EPSG:4326')[]``; it must not be detected as a scalar geometry
    # (would raise BinderException on duckdb 1.5.x).
    eng = _engine()
    eng._ensure_spatial()
    path = _geojson({"id": 1})
    rel = eng._connection.sql(
        "SELECT list(geom) AS pts, count(*) AS n FROM ST_Read(?)", params=[path]
    )
    out = eng._materialize_geometry_wkb(rel)
    assert list(out.columns) == ["pts", "n"], list(out.columns)
    assert int(out["n"].iloc[0]) == 1

"""DuckDB binds SQL parameters and carries source CRS through WKB and file reads."""

import pandas as pd
import pytest

duckdb = pytest.importorskip("duckdb")
gpd = pytest.importorskip("geopandas")
from shapely.geometry import Point

from siege_utilities.engines.dataframe_engine import DuckDBEngine


@pytest.fixture
def engine():
    result = DuckDBEngine()
    yield result
    result._connection.close()


@pytest.fixture
def typed_engine(engine):
    if tuple(map(int, duckdb.__version__.split(".")[:2])) < (1, 5):
        pytest.skip("CRS-qualified geometry types require DuckDB 1.5")
    engine._ensure_spatial()
    return engine


@pytest.mark.parametrize("keyword", ["parameters", "params"])
@pytest.mark.parametrize("sql, values", [("SELECT ? AS answer", [42]), ("SELECT $value AS answer", {"value": 42})])
def test_query_binds_parameters(engine, keyword, sql, values):
    assert engine.query(sql, **{keyword: values})["answer"].tolist() == [42]


def test_unknown_query_keyword_is_rejected_before_execution(engine):
    with pytest.raises(TypeError, match="unexpected.*paramters"):
        engine.query("CREATE TABLE should_not_exist(i INT)", paramters=[1])
    assert engine.query("SHOW TABLES").empty


def test_parameterized_multi_statement_is_rejected_before_execution(engine):
    with pytest.raises(ValueError, match="single statement"):
        engine.query("CREATE TABLE should_not_exist(i INT); SELECT ?", parameters=[1])
    assert engine.query("SHOW TABLES").empty


def test_query_rejects_two_parameter_arguments(engine):
    with pytest.raises(TypeError, match="parameters.*params"):
        engine.query("SELECT ?", parameters=[1], params=[2])


def test_parameterized_spatial_query_loads_extension(engine):
    result = engine.query("SELECT ST_Point(?, ?) AS geometry", parameters=[500, 1000])
    assert engine.to_geodataframe(result).geometry.iloc[0].equals(Point(500, 1000))


def test_parameterized_dml_executes_once(engine):
    engine.query("CREATE TABLE items (i INT)")
    assert engine.query("INSERT INTO items VALUES (?)", parameters=[1])["Count"].tolist() == [1]
    result = engine.query(
        "INSERT INTO items VALUES (?) RETURNING ST_Point(i, i) AS geometry", parameters=[2],
    )
    assert engine.to_geodataframe(result).geometry.iloc[0].equals(Point(2, 2))
    assert engine.query("SELECT i FROM items ORDER BY i")["i"].tolist() == [1, 2]


def test_query_parameters_with_registered_frame(engine):
    result = engine.query(
        "SELECT id FROM source WHERE id > ?", table="source", df=pd.DataFrame({"id": [1, 2]}),
        parameters=[1],
    )
    assert result["id"].tolist() == [2]


@pytest.mark.parametrize("shape", ["value", "null", "empty"])
@pytest.mark.parametrize("materialization", ["query", "relation"])
def test_typed_wkb_preserves_crs(typed_engine, shape, materialization):
    expression = "NULL" if shape == "null" else "ST_Point(500, 1000)"
    sql = f"SELECT {expression}::GEOMETRY('EPSG:3857') AS geometry"
    if shape == "empty":
        sql += " WHERE FALSE"
    if materialization == "query":
        frame = typed_engine.query(sql).copy()
    else:
        frame = typed_engine._connection.sql(sql)
    result = typed_engine.to_geodataframe(frame)
    assert result.crs.to_epsg() == 3857
    if shape == "value":
        assert result.geometry.iloc[0].equals(Point(500, 1000))
    elif shape == "null":
        assert result.geometry.isna().all()
    else:
        assert result.empty


def test_crs_tracks_deduplicated_geometry_columns(typed_engine):
    frame = typed_engine.query(
        "SELECT ST_Point(1, 2)::GEOMETRY('EPSG:3857') AS geometry, "
        "ST_Point(3, 4)::GEOMETRY('EPSG:5070') AS geometry"
    )
    assert typed_engine.to_geodataframe(frame, "geometry").crs.to_epsg() == 3857
    second = typed_engine.to_geodataframe(frame, "geometry_1")
    assert second.crs.to_epsg() == 5070
    assert second.geometry.iloc[0].equals(Point(3, 4))


def test_typed_dml_returning_preserves_crs_without_replaying_write(typed_engine):
    typed_engine.query("CREATE TABLE items(i INT)")
    result = typed_engine.query(
        "INSERT INTO items VALUES (?) RETURNING ST_Point(i, i)::GEOMETRY('EPSG:3857') AS geometry",
        parameters=[500],
    )
    converted = typed_engine.to_geodataframe(result)
    assert converted.crs.to_epsg() == 3857
    assert converted.geometry.iloc[0].equals(Point(500, 500))
    assert typed_engine.query("SELECT i FROM items")["i"].tolist() == [500]


@pytest.mark.parametrize("expression", ["ST_Point(500, 1000)", "NULL::GEOMETRY"])
def test_unknown_geometry_crs_stays_unknown(engine, expression):
    result = engine.to_geodataframe(engine.query(f"SELECT {expression} AS geometry"))
    assert result.crs is None


def test_plain_wkb_stays_unknown(engine):
    result = engine.to_geodataframe(pd.DataFrame({"geometry": [Point(500, 1000).wkb]}))
    assert result.crs is None


def test_target_crs_reprojects_typed_wkb(typed_engine):
    frame = typed_engine.query("SELECT ST_Point(500, 1000)::GEOMETRY('EPSG:3857') AS geometry")
    result = typed_engine.to_geodataframe(frame, crs=4326)
    expected = gpd.GeoSeries([Point(500, 1000)], crs=3857).to_crs(4326).iloc[0]
    assert result.crs.to_epsg() == 4326
    assert result.geometry.iloc[0].equals_exact(expected, 1e-10)


@pytest.mark.parametrize("empty", [False, True])
def test_geodataframe_wkb_round_trip_carries_crs(engine, empty):
    source = gpd.GeoDataFrame(geometry=[] if empty else [Point(500, 1000)], crs=3857)
    result = engine.to_geodataframe(engine.from_geodataframe(source))
    assert result.crs == source.crs
    assert result.geometry.to_wkt().tolist() == source.geometry.to_wkt().tolist()


@pytest.fixture
def stateplane_file(tmp_path):
    source = gpd.GeoDataFrame({"id": [1]}, geometry=[Point(3000000, 10000000)], crs=2277)
    path = tmp_path / "tx_stateplane.shp"
    source.to_file(path)
    return path, source


def test_read_spatial_preserves_source_crs_and_coordinates(engine, stateplane_file):
    path, source = stateplane_file
    result = engine.read_spatial(str(path))
    assert result.crs == source.crs
    assert result.geometry.iloc[0].equals(source.geometry.iloc[0])


def test_read_spatial_reprojects_only_when_requested(engine, stateplane_file):
    path, source = stateplane_file
    result = engine.read_spatial(str(path), crs=4326)
    assert result.crs.to_epsg() == 4326
    assert result.geometry.iloc[0].equals_exact(source.to_crs(4326).geometry.iloc[0], 1e-8)


def test_read_spatial_unknown_crs_is_not_defaulted(engine, stateplane_file):
    path, _ = stateplane_file
    path.with_suffix(".prj").unlink()
    result = engine.read_spatial(str(path))
    assert result.crs is None
    assert result.geometry.iloc[0].equals(Point(3000000, 10000000))
    with pytest.raises(ValueError, match="naive geometries"):
        engine.read_spatial(str(path), crs=4326)


@pytest.mark.parametrize("epsg", [4326, 3857])
def test_known_crs_survives_engine_attribute_join(typed_engine, epsg):
    # A known per-column CRS lives in DataFrame.attrs; an ordinary attribute
    # join must not drop it (fix-by-removal regression). The bare GEOMETRY /
    # unknown-source case stays None and is covered separately.
    spatial = typed_engine.query(
        f"SELECT 1 AS pid, ST_Point(-97, 30)::GEOMETRY('EPSG:{epsg}') AS geometry"
    )
    joined = typed_engine.join(
        spatial, pd.DataFrame({"pid": [1], "label": ["x"]}), on="pid"
    )
    result = typed_engine.to_geodataframe(joined)
    assert result.crs is not None
    assert result.crs.to_epsg() == epsg
    assert list(result.columns) == ["pid", "geometry", "label"]
    assert result.geometry.iloc[0].equals(Point(-97, 30))


def test_unknown_crs_stays_none_through_engine_attribute_join(typed_engine):
    spatial = typed_engine.query("SELECT 1 AS pid, ST_Point(-97, 30) AS geometry")
    joined = typed_engine.join(
        spatial, pd.DataFrame({"pid": [1], "label": ["x"]}), on="pid"
    )
    result = typed_engine.to_geodataframe(joined)
    assert result.crs is None


# -- #1852 R1 re-review: geometry join-key CRS provenance -------------------
# Adopted from snug-coral's test_rereview_delta.py (#1852 scoped re-review),
# adapted to the repo's typed_engine fixture (which skips on DuckDB < 1.5). The
# key test must be red at 46f4b882 and green on develop and at the new head.


@pytest.mark.parametrize("right_epsg", [None, 3857])
def test_left_geometry_join_key_is_not_relabelled_from_right(typed_engine, right_epsg):
    left = typed_engine.query(
        "SELECT 1 AS pid, ST_Point(-97, 30)::GEOMETRY('EPSG:4326') AS geometry"
    )
    cast = f"::GEOMETRY('EPSG:{right_epsg}')" if right_epsg else ""
    right = typed_engine.query(
        f"SELECT ST_Point(500, 1000){cast} AS geometry, 'x' AS note_text"
    )
    out = typed_engine.to_geodataframe(
        typed_engine.join(left, right, on="geometry", how="left")
    )
    assert out.geometry.iloc[0].wkt == "POINT (-97 30)"
    assert out["note_text"].isna().all(), "Fixture must retain only the unmatched left key"
    assert out.crs is not None, "Known left key CRS overwritten with unknown right metadata"
    assert out.crs.to_epsg() == 4326, f"Left key relabelled {out.crs}"


@pytest.mark.parametrize("direction", ["left", "right"])
@pytest.mark.parametrize("epsg", [4326, 3857])
def test_known_crs_attribute_join_both_directions(typed_engine, epsg, direction):
    spatial = typed_engine.query(
        f"SELECT 1 AS pid, ST_Point(-97, 30)::GEOMETRY('EPSG:{epsg}') AS geometry"
    )
    attrs = pd.DataFrame({"pid": [1], "label": ["x"]})
    left, right = (spatial, attrs) if direction == "left" else (attrs, spatial)
    out = typed_engine.to_geodataframe(typed_engine.join(left, right, on="pid"))
    assert out.crs.to_epsg() == epsg
    assert out.geometry.iloc[0].wkt == "POINT (-97 30)"


def test_suffixes_keep_both_geometry_crses(typed_engine):
    left = typed_engine.query(
        "SELECT 1 AS pid, ST_Point(-97, 30)::GEOMETRY('EPSG:4326') AS geometry"
    )
    right = typed_engine.query(
        "SELECT 1 AS pid, ST_Point(500, 1000)::GEOMETRY('EPSG:3857') AS geometry"
    )
    out = typed_engine.join(left, right, on=["pid"])
    assert out.columns.tolist() == ["pid", "geometry_x", "geometry_y"]
    a = typed_engine.to_geodataframe(out, "geometry_x")
    b = typed_engine.to_geodataframe(out, "geometry_y")
    assert a.crs.to_epsg() == 4326 and a.geometry.iloc[0].wkt == "POINT (-97 30)"
    assert b.crs.to_epsg() == 3857 and b.geometry.iloc[0].wkt == "POINT (500 1000)"

"""B1-B4 regression fixtures from the independent review of PR #1818."""

import pytest

gpd = pytest.importorskip("geopandas")
from pyproj import CRS
from shapely.geometry import Point

from siege_utilities.geo.spatial_transformations import (
    DuckDBConnector,
    PostGISConnector,
    SpatialQueryError,
)


@pytest.fixture
def duck_connector():
    duckdb = pytest.importorskip("duckdb")
    connector = DuckDBConnector.__new__(DuckDBConnector)
    connector.connection = duckdb.connect(":memory:")
    yield connector
    connector.close()


def test_b2_legacy_caller_metadata_is_preserved(duck_connector):
    duck_connector.connection.execute(
        "CREATE TABLE places (name VARCHAR, geometry_wkt VARCHAR, _siege_crs VARCHAR)"
    )
    duck_connector.connection.execute(
        "INSERT INTO places VALUES ('a', 'POINT (0 0)', 'EPSG:4326'), "
        "('b', 'POINT (1 1)', 'EPSG:4326')"
    )
    result = duck_connector.download_spatial_data("places")
    assert result.columns.tolist() == ["name", "_siege_crs", "geometry"]
    assert result._siege_crs.tolist() == ["EPSG:4326", "EPSG:4326"]
    assert result.name.tolist() == ["a", "b"]


def test_b2_input_caller_metadata_roundtrips(duck_connector):
    frame = gpd.GeoDataFrame(
        {"name": ["a", "b"], "_siege_crs": ["caller value", "another value"]},
        geometry=[Point(0, 0), Point(1, 1)], crs="EPSG:4326",
    )
    duck_connector.upload_spatial_data(frame, "places")
    result = duck_connector.download_spatial_data("places")
    from geopandas.testing import assert_geodataframe_equal

    assert_geodataframe_equal(result, frame)


def test_b4_returning_decode_failure_rolls_back(duck_connector):
    duck_connector.connection.execute(
        "CREATE TABLE places (id INTEGER, geometry_wkt VARCHAR, _siege_crs VARCHAR)"
    )
    with pytest.raises(SpatialQueryError):
        duck_connector.execute_spatial_query(
            "INSERT INTO places VALUES (1, 'not a geometry', 'EPSG:4326') RETURNING *"
        )
    assert duck_connector.connection.execute("SELECT * FROM places").fetchall() == []


@pytest.mark.parametrize("authority", [("ESRI", 102003), None, ("bad_authority", 102003)])
def test_b1_authority_lookup_never_replays_returning(authority):
    from unittest.mock import MagicMock
    from shapely import set_srid, to_wkb

    connector = PostGISConnector.__new__(PostGISConnector)
    connector.connection = MagicMock()
    query_cursor, crs_cursor = MagicMock(), MagicMock()
    connector.connection.cursor.side_effect = [query_cursor, crs_cursor]
    crs_cursor.__enter__.return_value = crs_cursor
    crs_cursor.fetchone.return_value = authority
    srid = 4326 if authority is None else 102003
    query_cursor.statusmessage = "INSERT 0 1"
    query_cursor.description = [("geometry",)]
    query_cursor.fetchall.return_value = [(to_wkb(set_srid(Point(1, 2), srid), include_srid=True),)]
    query = "INSERT INTO places DEFAULT VALUES RETURNING geometry"
    if authority and authority[0] == "bad_authority":
        with pytest.raises(SpatialQueryError):
            connector.execute_spatial_query(query)
        connector.connection.rollback.assert_called_once()
        connector.connection.commit.assert_not_called()
    else:
        expected = "EPSG:4326" if authority is None else "ESRI:102003"
        result = connector.execute_spatial_query(query, crs=expected)
        assert result.crs == CRS(expected)
        connector.connection.commit.assert_called_once()
    query_cursor.execute.assert_called_once_with(query)
    crs_cursor.execute.assert_called_once_with(
        "SELECT auth_name, auth_srid FROM spatial_ref_sys WHERE srid = %s", (srid,),
    )


@pytest.mark.parametrize("reader", ["download", "query"])
def test_b2_empty_table_crs_survives_reconnect(tmp_path, reader):
    duckdb = pytest.importorskip("duckdb")
    connector = DuckDBConnector.__new__(DuckDBConnector)
    path = str(tmp_path / "empty.duckdb")
    frame = gpd.GeoDataFrame({"id": [1]}, geometry=[Point(1, 2)], crs="EPSG:3857")
    connector.connection = duckdb.connect(path)
    try:
        connector.upload_spatial_data(frame.iloc[:0], "places")
        connector.close()
        connector.connection = duckdb.connect(path)
        result = (connector.download_spatial_data("places") if reader == "download"
                  else connector.execute_spatial_query("SELECT geometry_wkt FROM places"))
        assert result.empty
        assert result.crs == frame.crs
        with pytest.raises(RuntimeError, match="different source CRS"):
            connector.upload_spatial_data(frame.to_crs(4326), "places", if_exists="append")
        assert connector.connection.execute("SELECT count(*) FROM places").fetchone() == (0,)
    finally:
        connector.close()


@pytest.mark.parametrize("query", [
    'WITH p AS (SELECT * FROM "places") SELECT geometry_wkt, _siege_crs FROM p',
    'INSERT INTO /* target */ "places" SELECT * FROM "places" RETURNING *',
    'UPDATE "places" SET id=2 RETURNING *',
    'DELETE FROM "places" RETURNING *',
    'PREPARE "q x" AS INSERT INTO "places" SELECT * FROM "places" RETURNING *; EXECUTE "q x"',
])
def test_b2_queries_retain_table_crs_and_caller_column(duck_connector, query):
    frame = gpd.GeoDataFrame(
        {"id": [1], "_siege_crs": ["caller value"]}, geometry=[Point(1, 2)], crs="EPSG:3857",
    )
    duck_connector.connection.execute("CREATE SCHEMA retained")
    duck_connector.connection.execute("SET schema='retained'")
    duck_connector.upload_spatial_data(frame, "places")
    result = duck_connector.execute_spatial_query(query)
    assert result.crs == frame.crs
    assert result._siege_crs.tolist() == ["caller value"]
    assert result.geometry.iloc[0].equals_exact(frame.geometry.iloc[0], 0)


def test_b2_legacy_comment_and_columns_survive_append(duck_connector):
    duck_connector.connection.execute(
        "CREATE TABLE places (id BIGINT, _siege_crs VARCHAR, geometry_wkt VARCHAR)"
    )
    duck_connector.connection.execute("COMMENT ON TABLE places IS 'caller comment'")
    frame = gpd.GeoDataFrame(
        {"id": [1], "_siege_crs": ["caller value"]}, geometry=[Point(1, 2)], crs="EPSG:3857",
    )
    duck_connector.upload_spatial_data(frame, "places", if_exists="append")
    result = duck_connector.download_spatial_data("places")
    assert result._siege_crs.tolist() == ["caller value"]
    assert result.crs == frame.crs
    comment = duck_connector.connection.execute("SELECT comment FROM duckdb_tables()").fetchone()[0]
    assert comment.startswith("caller comment\n")


@pytest.mark.parametrize("query", [
    "UPDATE places SET geometry_wkt='not a geometry' RETURNING *",
    "DELETE FROM places RETURNING id, 'not a geometry' AS geometry_wkt",
    "INSERT INTO places VALUES (2,'POINT (2 2)'); "
    "INSERT INTO places VALUES (3,'not a geometry') RETURNING *",
])
def test_b4_failed_mutation_restores_all_rows(duck_connector, query):
    duck_connector.connection.execute("CREATE TABLE places (id INTEGER, geometry_wkt VARCHAR)")
    duck_connector.connection.execute("INSERT INTO places VALUES (1,'POINT (1 1)')")
    with pytest.raises(SpatialQueryError):
        duck_connector.execute_spatial_query(query)
    assert duck_connector.connection.execute("SELECT * FROM places").fetchall() == [(1, "POINT (1 1)")]


def test_b4_crs_validation_failure_rolls_back(duck_connector):
    frame = gpd.GeoDataFrame({"id": [1]}, geometry=[Point(1, 2)], crs="EPSG:3857")
    duck_connector.upload_spatial_data(frame, "places")
    with pytest.raises(SpatialQueryError):
        duck_connector.execute_spatial_query(
            "INSERT INTO places SELECT * FROM places RETURNING *", crs="invalid:crs",
        )
    assert duck_connector.connection.execute("SELECT count(*) FROM places").fetchone() == (1,)


def test_b4_caller_transaction_is_preserved_when_owned_write_is_refused(duck_connector):
    connection = duck_connector.connection
    connection.execute("CREATE TABLE places (id INTEGER)")
    connection.execute("BEGIN")
    connection.execute("INSERT INTO places VALUES (99)")
    assert duck_connector.execute_spatial_query("SELECT * FROM places").id.tolist() == [99]
    with pytest.raises(SpatialQueryError, match="active transaction"):
        duck_connector.execute_spatial_query("INSERT INTO places VALUES (1) RETURNING *")
    assert connection.execute("SELECT * FROM places").fetchall() == [(99,)]
    connection.execute("ROLLBACK")
    assert connection.execute("SELECT * FROM places").fetchall() == []


def test_b2_unreserved_keyword_table_name(duck_connector):
    frame = gpd.GeoDataFrame({"id": [1]}, geometry=[Point(1, 2)], crs="EPSG:3857")
    duck_connector.upload_spatial_data(frame, "data")
    duck_connector.upload_spatial_data(frame, "data", if_exists="append")
    result = duck_connector.execute_spatial_query("UPDATE data SET id=2 RETURNING *")
    assert result.crs == frame.crs
    assert result.id.tolist() == [2, 2]


def test_b4_unexpected_decoder_failure_rolls_back(duck_connector, monkeypatch):
    import siege_utilities.geo.spatial_transformations as module

    duck_connector.connection.execute("CREATE TABLE places (id INTEGER)")

    def fail_decode(*args, **kwargs):
        raise RuntimeError("decoder failed")

    monkeypatch.setattr(module, "_duckdb_result_frame", fail_decode)
    with pytest.raises(SpatialQueryError, match="decoder failed"):
        duck_connector.execute_spatial_query("INSERT INTO places VALUES (1) RETURNING *")
    assert duck_connector.connection.execute("SELECT * FROM places").fetchall() == []

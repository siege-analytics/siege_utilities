"""Regression tests for #1414 using mocked PostGIS and local DuckDB only."""

from contextlib import contextmanager
from copy import deepcopy
import sys
from unittest.mock import MagicMock

import pytest

gpd = pytest.importorskip("geopandas")
from shapely.geometry import Point

from siege_utilities.geo.spatial_transformations import (
    DuckDBConnector,
    PostGISConnector,
    SpatialQueryError,
)


@pytest.fixture
def projected_gdf():
    return gpd.GeoDataFrame(
        {"id": [2], "name": ["new"]},
        geometry=[Point(1000000, 2000000)],
        crs="EPSG:3857",
    )


@pytest.fixture
def duck_connector():
    duckdb = pytest.importorskip("duckdb")
    connector = DuckDBConnector.__new__(DuckDBConnector)
    connector.connection = duckdb.connect(":memory:")
    yield connector
    connector.close()


@pytest.mark.parametrize("mode", ["default", "replace"])
def test_postgis_existing_table_survives_failed_upload(monkeypatch, projected_gdf, mode):
    """Default refuses an existing table; failed replacement restores its state."""
    pytest.importorskip("sqlalchemy")
    monkeypatch.setitem(sys.modules, "geoalchemy2", MagicMock())
    original = {"rows": [1], "indexes": ["id_idx"], "grants": ["reader"], "constraints": ["id_pk"]}
    table = deepcopy(original)
    engine = MagicMock()
    connection = object()

    @contextmanager
    def transaction():
        snapshot = deepcopy(table)
        try:
            yield connection
        except Exception:
            table.clear()
            table.update(snapshot)
            raise

    engine.begin.side_effect = transaction
    monkeypatch.setattr("sqlalchemy.create_engine", lambda _: engine)

    def write(frame, *, con, if_exists, **kwargs):
        if if_exists == "fail":
            raise ValueError("table already exists")
        table.clear()  # DROP has succeeded before CREATE fails.
        if mode == "replace":
            raise ValueError("create failed")
        table["rows"] = frame.id.tolist()

    monkeypatch.setattr(gpd.GeoDataFrame, "to_postgis", write)
    connector = PostGISConnector.__new__(PostGISConnector)
    connector.connection_string = "postgresql://localhost/test"
    options = {} if mode == "default" else {"if_exists": mode}
    with pytest.raises(SpatialQueryError, match="already exists|create failed"):
        connector.upload_spatial_data(projected_gdf, "places", **options)
    assert table == original
    engine.dispose.assert_called_once()


@pytest.mark.parametrize("mode", ["append", "replace", "default"])
def test_duckdb_existing_table_survives_upload(duck_connector, projected_gdf, mode):
    """Exercise real transactional DDL and append without a server or extension."""
    connection = duck_connector.connection
    connection.execute("CREATE TABLE places (id BIGINT, name VARCHAR, geometry_wkt VARCHAR)")
    connection.execute("INSERT INTO places VALUES (1, 'old', 'POINT (0 0)')")
    if mode == "append":
        # Use the uploader's schema so CRS metadata added by the fix is present.
        duck_connector.upload_spatial_data(projected_gdf, "places", if_exists="replace")
        duck_connector.upload_spatial_data(projected_gdf, "places", if_exists="append")
        assert connection.execute("SELECT id FROM places ORDER BY id").fetchall() == [(2,), (2,)]
    else:
        if mode == "replace":
            # Inject only the CREATE failure; use real DuckDB DROP/ROLLBACK.
            duckdb = pytest.importorskip("duckdb")
            proxy = MagicMock(wraps=connection)

            def execute(query, *args, **kwargs):
                if query.startswith("CREATE TABLE places AS"):
                    raise duckdb.InvalidInputException("create failed")
                return connection.execute(query, *args, **kwargs)

            proxy.execute.side_effect = execute
            duck_connector.connection = proxy
        options = {} if mode == "default" else {"if_exists": mode}
        with pytest.raises(RuntimeError):
            duck_connector.upload_spatial_data(projected_gdf, "places", **options)
        assert connection.execute("SELECT id, name FROM places").fetchall() == [(1, "old")]


@pytest.mark.parametrize("backend", ["postgis", "duckdb"])
@pytest.mark.parametrize("statement", ["cte", "returning"])
def test_row_returning_queries_return_rows(backend, statement):
    queries = {
        "cte": "WITH x AS (SELECT 7 AS id) SELECT * FROM x",
        "returning": "INSERT INTO places VALUES (7) RETURNING id",
    }
    query = queries[statement]
    if backend == "postgis":
        connector = PostGISConnector.__new__(PostGISConnector)
        connector._opened_connection = True
        connector.connection = MagicMock()
        connector.connection.autocommit = False
        connector.connection.get_transaction_status.return_value = 0  # IDLE
        cursor = connector.connection.cursor.return_value
        cursor.description = [("id", None, None, None, None, None, None)]
        cursor.fetchall.return_value = [(7,)]
        cursor.rowcount = 1
        cursor.statusmessage = "SELECT 1" if statement == "cte" else "INSERT 0 1"
        result = connector.execute_spatial_query(query)
        assert result["id"].tolist() == [7]
        cursor.execute.assert_called_once_with(query)
        cursor.close.assert_called_once()
        connector.connection.commit.assert_called_once()
    else:
        duckdb = pytest.importorskip("duckdb")
        connector = DuckDBConnector.__new__(DuckDBConnector)
        connector.connection = duckdb.connect(":memory:")
        try:
            connector.connection.execute("CREATE TABLE places (id INTEGER)")
            result = connector.execute_spatial_query(query)
            assert result["id"].tolist() == [7]
            expected = 1 if statement == "returning" else 0
            assert connector.connection.execute("SELECT count(*) FROM places").fetchone()[0] == expected
        finally:
            connector.close()


@pytest.mark.parametrize("reader", ["download", "query"])
def test_duckdb_table_and_query_crs_after_reconnect(tmp_path, projected_gdf, reader):
    duckdb = pytest.importorskip("duckdb")
    database = str(tmp_path / "places.duckdb")
    connector = DuckDBConnector.__new__(DuckDBConnector)
    connector.connection = duckdb.connect(database)
    connector.upload_spatial_data(projected_gdf, "places")
    connector.close()
    connector.connection = duckdb.connect(database)
    try:
        if reader == "download":
            result = connector.download_spatial_data("places")
        else:
            result = connector.execute_spatial_query("SELECT * FROM places")
        assert result.crs.to_epsg() == (3857 if reader == "download" else 4326)
        assert result.geometry.iloc[0].equals_exact(projected_gdf.geometry.iloc[0], 0)
        assert result.columns.tolist() == projected_gdf.columns.tolist()
    finally:
        connector.close()


@pytest.mark.parametrize("encoding", ["bytes", "hex", "memoryview"])
def test_postgis_returning_decodes_ewkb_once(encoding):
    from shapely import set_srid, to_wkb

    point = Point(1000000, 2000000)
    encoded = to_wkb(set_srid(point, 3857), include_srid=True)
    if encoding == "hex":
        encoded = encoded.hex()
    elif encoding == "memoryview":
        encoded = memoryview(encoded)
    connector = PostGISConnector.__new__(PostGISConnector)
    connector._opened_connection = True
    connector.connection = MagicMock()
    connector.connection.autocommit = False
    connector.connection.get_transaction_status.return_value = 0  # IDLE
    cursor = connector.connection.cursor.return_value
    cursor.description = [("id",), ("geom",)]
    cursor.statusmessage = "INSERT 0 2"
    cursor.__enter__.return_value.fetchone.return_value = ("EPSG", 3857)
    cursor.fetchall.return_value = [(1, encoded), (2, None)]
    query = "INSERT INTO places SELECT * FROM incoming RETURNING id, geom"
    result = connector.execute_spatial_query(query, geom_col="geom", crs="EPSG:3857")
    assert result.geometry.name == "geom"
    assert result.crs.to_epsg() == 3857
    assert result.geometry.iloc[0].equals_exact(point, 0)
    assert result.geometry.iloc[1] is None
    cursor.execute.assert_called_once_with(query)
    connector.connection.commit.assert_called_once()


def test_postgis_bad_geometry_rolls_back_returning():
    connector = PostGISConnector.__new__(PostGISConnector)
    connector._opened_connection = True
    connector.connection = MagicMock()
    connector.connection.autocommit = False
    connector.connection.get_transaction_status.return_value = 0  # IDLE
    cursor = connector.connection.cursor.return_value
    cursor.description = [("geometry",)]
    cursor.statusmessage = "INSERT 0 1"
    cursor.fetchall.return_value = [(b"invalid wkb",)]
    with pytest.raises(SpatialQueryError):
        connector.execute_spatial_query("INSERT INTO places DEFAULT VALUES RETURNING geometry")
    connector.connection.rollback.assert_called_once()
    connector.connection.commit.assert_not_called()
    cursor.close.assert_called_once()


@pytest.mark.parametrize("backend", ["postgis", "duckdb"])
def test_non_returning_dml_keeps_rowcount(backend):
    query = "INSERT INTO places VALUES (1), (2)"
    if backend == "postgis":
        connector = PostGISConnector.__new__(PostGISConnector)
        connector._opened_connection = True
        connector.connection = MagicMock()
        connector.connection.autocommit = False
        connector.connection.get_transaction_status.return_value = 0  # IDLE
        cursor = connector.connection.cursor.return_value
        cursor.description = None
        cursor.statusmessage = "INSERT 0 2"
        cursor.rowcount = 2
        assert connector.execute_spatial_query(query) == 2
        cursor.fetchall.assert_not_called()
    else:
        duckdb = pytest.importorskip("duckdb")
        connector = DuckDBConnector.__new__(DuckDBConnector)
        connector.connection = duckdb.connect(":memory:")
        try:
            assert connector.execute_spatial_query("CREATE TABLE places (id INTEGER)") == -1
            assert connector.execute_spatial_query(query) == 2
            result = connector.execute_spatial_query("/* comment */ SELECT count(*) AS Count FROM places")
            assert result["Count"].tolist() == [2]
        finally:
            connector.close()


def test_duckdb_append_creates_missing_table_and_matches_column_names(duck_connector, projected_gdf):
    duck_connector.upload_spatial_data(projected_gdf, "places", if_exists="append")
    incoming = projected_gdf[["name", "geometry", "id"]].copy()
    incoming["id"] = [3]
    incoming["name"] = ["appended"]
    duck_connector.upload_spatial_data(incoming, "places", if_exists="append")
    result = duck_connector.download_spatial_data("places")
    assert result.id.tolist() == [2, 3]
    assert result.name.tolist() == ["new", "appended"]
    assert result.crs == projected_gdf.crs


@pytest.mark.parametrize("failure", ["crs", "schema", "mode"])
def test_duckdb_failed_append_or_invalid_mode_preserves_table(duck_connector, projected_gdf, failure):
    duck_connector.upload_spatial_data(projected_gdf, "places")
    incoming = projected_gdf.copy()
    mode = "append"
    if failure == "crs":
        incoming = incoming.to_crs(4326)
    elif failure == "schema":
        incoming["extra_column"] = [1]
    else:
        mode = "typo"
    with pytest.raises(RuntimeError):
        duck_connector.upload_spatial_data(incoming, "places", if_exists=mode)
    result = duck_connector.download_spatial_data("places")
    assert result.id.tolist() == [2]
    assert result.crs == projected_gdf.crs
    assert duck_connector.connection.execute(
        "SELECT count(*) FROM duckdb_views() WHERE view_name = 'siege_upload_df'"
    ).fetchone() == (0,)


def test_duckdb_legacy_append_preserves_unknown_crs(duck_connector, projected_gdf):
    duck_connector.connection.execute(
        "CREATE TABLE places AS SELECT 1 AS id, 'old' AS name, 'POINT (0 0)' AS geometry_wkt"
    )
    assert duck_connector.download_spatial_data("places").crs is None
    with pytest.raises(SpatialQueryError, match="Source CRS is unknown"):
        duck_connector.download_spatial_data("places", crs="EPSG:4326")
    duck_connector.upload_spatial_data(projected_gdf, "places", if_exists="append")
    with pytest.raises(SpatialQueryError, match="known and unknown CRSs"):
        duck_connector.download_spatial_data("places")
    result = duck_connector.download_spatial_data("places", source_crs="EPSG:3857")
    assert result.id.tolist() == [1, 2]
    assert result.crs == projected_gdf.crs


def test_duckdb_reprojects_from_stored_crs(duck_connector, projected_gdf):
    duck_connector.upload_spatial_data(projected_gdf, "places")
    result = duck_connector.download_spatial_data("places", crs="EPSG:4326")
    expected = projected_gdf.to_crs(4326)
    assert result.crs == expected.crs
    assert result.geometry.iloc[0].equals_exact(expected.geometry.iloc[0], 1e-10)
    with pytest.raises(SpatialQueryError, match="conflicting source CRSs"):
        duck_connector.download_spatial_data("places", source_crs="EPSG:4326")


def test_duckdb_preserves_custom_crs_null_geometry_and_precision(duck_connector):
    frame = gpd.GeoDataFrame(
        {"id": [1, 2]}, geometry=[Point(1.12345678912345, 2.98765432198765), None],
        crs="+proj=aeqd +lat_0=12.345 +lon_0=67.89 +datum=WGS84 +units=m +no_defs",
    )
    assert frame.crs.to_epsg() is None
    duck_connector.upload_spatial_data(frame, "places")
    result = duck_connector.download_spatial_data("places")
    assert result.crs == frame.crs
    assert result.geometry.iloc[0].equals_exact(frame.geometry.iloc[0], 0)
    assert result.geometry.iloc[1] is None


def test_duckdb_empty_and_projected_results_accept_source_crs(duck_connector, projected_gdf):
    # Empty object columns have no inferable SQL type; use the string dtype.
    duck_connector.upload_spatial_data(projected_gdf.astype({"name": "string"}).iloc[:0], "places")
    empty = duck_connector.download_spatial_data("places", source_crs="EPSG:3857")
    assert empty.empty
    assert empty.crs == projected_gdf.crs
    duck_connector.upload_spatial_data(projected_gdf, "places", if_exists="append")
    result = duck_connector.download_spatial_data("places", source_crs="EPSG:3857")
    assert result.crs == projected_gdf.crs


def test_duckdb_returning_retains_geometry_with_develop_crs(duck_connector, projected_gdf):
    duck_connector.upload_spatial_data(projected_gdf, "places")
    result = duck_connector.execute_spatial_query("INSERT INTO places SELECT * FROM places RETURNING *")
    assert result.crs.to_epsg() == 4326
    assert result.geometry.iloc[0].equals_exact(projected_gdf.geometry.iloc[0], 0)
    assert duck_connector.connection.execute("SELECT count(*) FROM places").fetchone() == (2,)

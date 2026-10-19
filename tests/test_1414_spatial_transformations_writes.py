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
        connector.connection = MagicMock()
        cursor = connector.connection.cursor.return_value
        cursor.description = [("id", None, None, None, None, None, None)]
        cursor.fetchall.return_value = [(7,)]
        cursor.rowcount = 1
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
def test_duckdb_preserves_source_crs_after_reconnect(tmp_path, projected_gdf, reader):
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
        assert result.crs == projected_gdf.crs
        assert result.geometry.iloc[0].equals_exact(projected_gdf.geometry.iloc[0], 0)
        assert result.columns.tolist() == projected_gdf.columns.tolist()
    finally:
        connector.close()

"""Download transactions and DuckDB column names for PR #1818.

``download_spatial_data`` reads through ``geopandas.read_postgis``, which
opens a transaction on a non-autocommit connection and never ends it. The
connector must end that transaction itself, so the next
``execute_spatial_query`` on a connection the connector opened still commits.
A download inside a caller's own transaction must leave it open.

A DuckDB upload of a frame whose active geometry has another name must refuse
an attribute column named ``geometry``, which the download would overwrite.
"""

import pytest
from shapely.geometry import Point


@pytest.mark.postgis
@pytest.mark.parametrize("statement, check, expected", [
    ("COMMENT ON TABLE {t} IS 'kept'", "SELECT obj_description('{t}'::regclass)", "kept"),
    ("REFRESH MATERIALIZED VIEW {s}.mv", "SELECT n FROM {s}.mv", 2),
])
def test_write_after_download_commits_on_connector_owned_connection(
    postgis_pair, statement, check, expected,
):
    connector, observer, table = postgis_pair
    schema = table.rsplit(".", 1)[0]
    with observer.cursor() as cursor:
        cursor.execute(f"INSERT INTO {table} VALUES (1, ST_SetSRID(ST_Point(1,1),4326))")
        cursor.execute(f"CREATE MATERIALIZED VIEW {schema}.mv AS SELECT count(*) AS n FROM {table}")
        cursor.execute(f"INSERT INTO {table} VALUES (2, ST_SetSRID(ST_Point(5,5),4326))")

    frame = connector.download_spatial_data(table.replace('"', ""), geom_col="geometry")
    assert len(frame) == 2
    assert connector.connection.get_transaction_status() == 0  # idle: the read ended its transaction

    assert connector.execute_spatial_query(statement.format(t=table, s=schema)) == -1
    connector.close()  # anything the connector did not commit is discarded here
    with observer.cursor() as cursor:
        cursor.execute(check.format(t=table, s=schema))
        assert cursor.fetchone()[0] == expected


@pytest.mark.postgis
def test_download_inside_caller_transaction_leaves_it_open(postgis_pair):
    from psycopg2.extensions import TRANSACTION_STATUS_INTRANS

    connector, observer, table = postgis_pair
    with connector.connection.cursor() as cursor:
        cursor.execute(f"INSERT INTO {table} VALUES (7, ST_SetSRID(ST_Point(0,0),4326))")
    assert connector.connection.get_transaction_status() == TRANSACTION_STATUS_INTRANS

    frame = connector.download_spatial_data(table.replace('"', ""), geom_col="geometry")
    assert list(frame["id"]) == [7]
    assert connector.connection.get_transaction_status() == TRANSACTION_STATUS_INTRANS

    connector.connection.rollback()
    with observer.cursor() as cursor:
        cursor.execute(f"SELECT count(*) FROM {table}")
        assert cursor.fetchone()[0] == 0


def test_duckdb_upload_refuses_attribute_column_named_geometry(duck_connector):
    gpd = pytest.importorskip("geopandas")

    gdf = gpd.GeoDataFrame(
        {"geometry": ["text value"], "geom": [Point(1, 2)]}, geometry="geom", crs="EPSG:4326",
    )
    with pytest.raises(RuntimeError, match="named 'geometry'"):
        duck_connector.upload_spatial_data(gdf, "places")
    tables = duck_connector.connection.execute(
        "SELECT count(*) FROM information_schema.tables WHERE table_name = 'places'"
    ).fetchone()[0]
    assert tables == 0

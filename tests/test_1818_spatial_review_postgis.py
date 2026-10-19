"""Live PostGIS authority and transaction regressions for PR #1818."""

import os
from uuid import uuid4

import pytest
from pyproj import CRS
from shapely.geometry import Point

from siege_utilities.geo.spatial_transformations import PostGISConnector, SpatialQueryError

pytestmark = pytest.mark.postgis


@pytest.fixture
def postgis_pair():
    """Use only the disposable database named by the test run."""
    psycopg2 = pytest.importorskip("psycopg2")
    dsn = os.environ.get("SIEGE_TEST_POSTGIS_DSN") or os.environ.get("SIEGE_UTILITIES_TEST_PG_DSN")
    if not dsn:
        pytest.skip("Set SIEGE_TEST_POSTGIS_DSN to a disposable PostGIS database")
    observer = psycopg2.connect(dsn)
    observer.autocommit = True
    connector = PostGISConnector(dsn)
    schema = "review_1818_" + uuid4().hex
    with observer.cursor() as cursor:
        cursor.execute(f'CREATE SCHEMA "{schema}"')
        cursor.execute(f'CREATE TABLE "{schema}".places (id INTEGER, geometry geometry)')
    try:
        yield connector, observer, f'"{schema}".places'
    finally:
        connector.close()
        with observer.cursor() as cursor:
            cursor.execute(f'DROP SCHEMA "{schema}" CASCADE')
        observer.close()



def test_b1_postgis_resolves_esri_authority(postgis_pair):
    connector, observer, _ = postgis_pair
    with observer.cursor() as cursor:
        cursor.execute(
            "INSERT INTO spatial_ref_sys (srid, auth_name, auth_srid, srtext) "
            "VALUES (102003, 'ESRI', 102003, %s) ON CONFLICT (srid) DO NOTHING",
            [CRS("ESRI:102003").to_wkt()],
        )
    result = connector.execute_spatial_query(
        "SELECT ST_SetSRID(ST_Point(1000000,2000000),102003) AS geometry",
        crs="ESRI:102003",
    )
    assert result.crs == CRS("ESRI:102003")
    assert result.geometry.iloc[0].equals_exact(Point(1000000, 2000000), 0)



def test_b1_postgis_wraps_crs_errors(postgis_pair):
    connector, _, _ = postgis_pair
    with pytest.raises(SpatialQueryError) as raised:
        connector.execute_spatial_query(
            "SELECT ST_SetSRID(ST_Point(0,0),4326) AS geometry", crs="invalid:crs",
        )
    from pyproj.exceptions import CRSError

    assert isinstance(raised.value.__cause__, CRSError)
    assert connector.connection.get_transaction_status() == 0



def test_b3_select_does_not_commit_caller_pending_write(postgis_pair, record_property):
    connector, observer, table = postgis_pair
    with connector.connection.cursor() as cursor:
        cursor.execute(f"INSERT INTO {table} VALUES (99, ST_SetSRID(ST_Point(0,0),4326))")
    before = connector.connection.get_transaction_status()
    result = connector.execute_spatial_query(f"SELECT * FROM {table}")
    after = connector.connection.get_transaction_status()
    with observer.cursor() as cursor:
        cursor.execute(f"SELECT count(*) FROM {table}")
        visible_before_rollback = cursor.fetchone()[0]
    connector.connection.rollback()
    with observer.cursor() as cursor:
        cursor.execute(f"SELECT count(*) FROM {table}")
        visible_after_rollback = cursor.fetchone()[0]
    assert result.id.tolist() == [99]
    record_property("observer_before_caller_rollback", visible_before_rollback)
    record_property("observer_after_caller_rollback", visible_after_rollback)
    assert (visible_before_rollback, visible_after_rollback) == (0, 0)
    assert before == after



def test_b3_returning_commits_only_after_crs_validation(postgis_pair):
    connector, observer, table = postgis_pair
    with pytest.raises(SpatialQueryError):
        connector.execute_spatial_query(
            f"INSERT INTO {table} VALUES (1, ST_SetSRID(ST_Point(1,2),4326)) RETURNING *",
            crs="invalid:crs",
        )
    with observer.cursor() as cursor:
        cursor.execute(f"SELECT count(*) FROM {table}")
        assert cursor.fetchone() == (0,)
    result = connector.execute_spatial_query(
        f"INSERT INTO {table} VALUES (2, ST_SetSRID(ST_Point(1,2),4326)) RETURNING *",
        crs="EPSG:4326",
    )
    assert result.id.tolist() == [2]
    with observer.cursor() as cursor:
        cursor.execute(f"SELECT id FROM {table}")
        assert cursor.fetchall() == [(2,)]


@pytest.mark.parametrize("operation", ["INSERT", "DELETE", "UPDATE", "MERGE"])
def test_r2_1_mutating_cte_rows_match_durable_state_after_close(postgis_pair, operation):
    connector, observer, table = postgis_pair
    with observer.cursor() as cursor:
        cursor.execute(f"INSERT INTO {table} VALUES (7, ST_SetSRID(ST_Point(1,2),4326))")
    bodies = {
        "INSERT": f"INSERT INTO {table} VALUES (8, ST_SetSRID(ST_Point(3,4),4326)) RETURNING *",
        "DELETE": f"DELETE FROM {table} WHERE id=7 RETURNING *",
        "UPDATE": f"UPDATE {table} SET id=8 WHERE id=7 RETURNING *",
        "MERGE": f"MERGE INTO {table} p USING (VALUES (7)) src(id) ON p.id=src.id "
                 "WHEN MATCHED THEN UPDATE SET id=8 RETURNING p.*",
    }
    expected = [] if operation == "DELETE" else [(7,), (8,)] if operation == "INSERT" else [(8,)]
    with connector:
        result = connector.execute_spatial_query(f"WITH written AS ({bodies[operation]}) SELECT * FROM written")
        assert result.id.tolist() == [7 if operation == "DELETE" else 8]
        assert result.crs.to_epsg() == 4326
        with observer.cursor() as cursor:
            cursor.execute(f"SELECT id FROM {table} ORDER BY id")
            after_success = cursor.fetchall()
    with observer.cursor() as cursor:
        cursor.execute(f"SELECT id FROM {table} ORDER BY id")
        after_close = cursor.fetchall()
    assert after_success == after_close == expected


@pytest.fixture
def volatile_insert(postgis_pair):
    connector, observer, table = postgis_pair
    function = table.rsplit(".", 1)[0] + ".record_point"
    with observer.cursor() as cursor:
        cursor.execute(
            f"CREATE FUNCTION {function}() RETURNS geometry LANGUAGE plpgsql VOLATILE AS $$ "
            f"BEGIN INSERT INTO {table} VALUES (8, ST_SetSRID(ST_Point(3,4),4326)); "
            "RETURN ST_SetSRID(ST_Point(3,4),4326); END $$"
        )
    return connector, observer, table, f"SELECT 8 AS id, {function}() AS geometry"


def test_r2_1_owned_volatile_select_is_durable_after_close(volatile_insert, record_property):
    connector, observer, table, query = volatile_insert
    with connector:
        result = connector.execute_spatial_query(query)
        assert result.id.tolist() == [8]
        assert result.crs.to_epsg() == 4326
        status_after_success = connector.connection.get_transaction_status()
        with observer.cursor() as cursor:
            cursor.execute(f"SELECT id FROM {table}")
            after_success = cursor.fetchall()
    with observer.cursor() as cursor:
        cursor.execute(f"SELECT id FROM {table}")
        after_close = cursor.fetchall()
    record_property("observer_after_success", after_success)
    record_property("observer_after_close", after_close)
    assert after_success == after_close == [(8,)]
    assert status_after_success == 0


def test_r2_1_owned_volatile_select_rolls_back_on_decode_error(volatile_insert):
    connector, observer, table, query = volatile_insert
    with pytest.raises(SpatialQueryError):
        connector.execute_spatial_query(query, crs="invalid:crs")
    assert connector.connection.get_transaction_status() == 0
    connector.close()
    with observer.cursor() as cursor:
        cursor.execute(f"SELECT id FROM {table}")
        assert cursor.fetchall() == []


def test_beta_caller_for_update_commits_under_write_token_classifier(postgis_pair):
    from unittest.mock import MagicMock
    from psycopg2.extensions import TRANSACTION_STATUS_IDLE

    connector, observer, table = postgis_pair
    connection = connector.connection
    connector.connection = MagicMock(wraps=connection)
    with observer.cursor() as cursor:
        cursor.execute(f"INSERT INTO {table} VALUES (7, ST_SetSRID(ST_Point(1,2),4326))")
    with connection.cursor() as cursor:
        cursor.execute("BEGIN")
    result = connector.execute_spatial_query(f"SELECT * FROM {table} WHERE id=7 FOR UPDATE")
    assert result.id.tolist() == [7]
    assert connection.get_transaction_status() == TRANSACTION_STATUS_IDLE
    connector.connection.commit.assert_called_once()
    connector.connection.rollback.assert_not_called()
    with observer.cursor() as cursor:
        cursor.execute(f"SELECT id FROM {table} WHERE id=7 FOR UPDATE NOWAIT")
        assert cursor.fetchall() == [(7,)]


@pytest.mark.parametrize("cte", [False, True])
def test_r2_1_caller_write_commits_like_develop(postgis_pair, cte, record_property):
    connector, observer, table = postgis_pair
    with connector.connection.cursor() as cursor:
        cursor.execute(f"INSERT INTO {table} VALUES (99, ST_SetSRID(ST_Point(0,0),4326))")
    query = f"INSERT INTO {table} VALUES (8, ST_SetSRID(ST_Point(3,4),4326)) RETURNING *"
    if cte:
        query = f"WITH written AS ({query}) SELECT * FROM written"
    connector.execute_spatial_query(query)
    status_after_success = connector.connection.get_transaction_status()
    with observer.cursor() as cursor:
        cursor.execute(f"SELECT id FROM {table} ORDER BY id")
        after_success = cursor.fetchall()
    connector.connection.rollback()
    with observer.cursor() as cursor:
        cursor.execute(f"SELECT id FROM {table} ORDER BY id")
        after_rollback = cursor.fetchall()
    record_property("observer_after_success", after_success)
    record_property("observer_after_caller_rollback", after_rollback)
    record_property("transaction_status_after_success", status_after_success)
    assert status_after_success == 0
    assert after_success == after_rollback == [(8,), (99,)]


@pytest.mark.parametrize("query", [
    "SELECT 'INSERT INTO places' AS note",
    'SELECT 1 AS "UPDATE" /* DELETE FROM places */',
    "WITH src AS (SELECT $tag$MERGE INTO places$tag$ AS note) SELECT * FROM src",
    'SELECT 1 AS "merge" -- INSERT INTO places\n',
    "SELECT (1) /* outer /* INSERT */ UPDATE */ AS value",
])
def test_r2_1_read_tokens_do_not_commit_pending_id_99(postgis_pair, query):
    connector, observer, table = postgis_pair
    with connector.connection.cursor() as cursor:
        cursor.execute(f"INSERT INTO {table} VALUES (99, ST_SetSRID(ST_Point(0,0),4326))")
    connector.execute_spatial_query(query)
    with observer.cursor() as cursor:
        cursor.execute(f"SELECT id FROM {table}")
        assert cursor.fetchall() == []
    connector.connection.rollback()
    with observer.cursor() as cursor:
        cursor.execute(f"SELECT id FROM {table}")
        assert cursor.fetchall() == []


def test_r2_1_failed_write_preserves_caller_pending_rows(postgis_pair):
    connector, observer, table = postgis_pair
    with connector.connection.cursor() as cursor:
        cursor.execute(f"INSERT INTO {table} VALUES (99, ST_SetSRID(ST_Point(0,0),4326))")
    with pytest.raises(SpatialQueryError):
        connector.execute_spatial_query(
            f"WITH written AS (INSERT INTO {table} VALUES (8, ST_SetSRID(ST_Point(1,2),4326)) "
            "RETURNING *) SELECT * FROM written", crs="invalid:crs",
        )
    with connector.connection.cursor() as cursor:
        cursor.execute(f"SELECT id FROM {table}")
        assert cursor.fetchall() == [(99,)]
    connector.connection.commit()
    with observer.cursor() as cursor:
        cursor.execute(f"SELECT id FROM {table}")
        assert cursor.fetchall() == [(99,)]


@pytest.mark.parametrize("keyword", [
    "INSERT", "UPDATE", "DELETE", "MERGE", "CREATE", "DROP", "ALTER",
    "TRUNCATE", "COPY", "CALL", "DO", "GRANT", "REVOKE",
])
@pytest.mark.parametrize("template", ["SELECT {word}", "SELECT ({word})", "SELECT (({word}))"])
def test_r2_1_every_write_keyword_marks_caller_cte_non_read_only(keyword, template):
    """Exercise commit classification independently of PostgreSQL grammar."""
    from unittest.mock import MagicMock

    connector = PostGISConnector.__new__(PostGISConnector)
    connector._opened_connection = True
    connector.connection = MagicMock()
    connector.connection.get_transaction_status.return_value = 2
    cursor = connector.connection.cursor.return_value
    cursor.statusmessage = "SELECT 1"
    cursor.description = [("id",)]
    cursor.fetchall.return_value = [(7,)]
    query = f"WITH src AS ({template.format(word=keyword.lower())}) SELECT * FROM src"
    result = connector.execute_spatial_query(query)
    assert result.id.tolist() == [7]
    connector.connection.commit.assert_called_once()


@pytest.mark.parametrize("query", [
    "SELECT delete_flag, updated_at, merge_id FROM selection",
    'SELECT "INSERT", "UPDATE", "DELETE" FROM "select"',
    "SELECT 'INSERT UPDATE DELETE MERGE CREATE DROP ALTER TRUNCATE COPY CALL DO GRANT REVOKE'",
    "SELECT $$INSERT UPDATE DELETE MERGE CREATE DROP ALTER TRUNCATE COPY CALL DO GRANT REVOKE$$",
    "SELECT $tag$INSERT DROP UPDATE$tag$ /* CREATE /* DELETE */ ALTER */ -- CALL DO\n",
    "SELECT E'escaped\\\' UPDATE', 'doubled'' DELETE', update$flag, deleteé",
])
def test_r2_1_literals_comments_and_identifier_substrings_do_not_commit(query):
    from unittest.mock import MagicMock

    connector = PostGISConnector.__new__(PostGISConnector)
    connector._opened_connection = True
    connector.connection = MagicMock()
    connector.connection.get_transaction_status.return_value = 2
    cursor = connector.connection.cursor.return_value
    cursor.statusmessage = "SELECT 1"
    cursor.description = [("id",)]
    cursor.fetchall.return_value = [(7,)]
    assert connector.execute_spatial_query(query).id.tolist() == [7]
    connector.connection.commit.assert_not_called()
    connector.connection.rollback.assert_not_called()


@pytest.mark.parametrize("query", ["SELECT 7 AS id", "SHOW server_version", "EXPLAIN SELECT 7"])
def test_r2_1_owned_success_commits_without_classification(query, monkeypatch):
    from unittest.mock import MagicMock
    import siege_utilities.geo.spatial_transformations as module

    connector = PostGISConnector.__new__(PostGISConnector)
    connector._opened_connection = True
    connector.connection = MagicMock()
    connector.connection.get_transaction_status.return_value = 0
    cursor = connector.connection.cursor.return_value
    cursor.statusmessage = query.split()[0] + " 1"
    cursor.description = [("id",)]
    cursor.fetchall.return_value = [(7,)]
    classifier = MagicMock(side_effect=AssertionError("Owned statements must not be classified"))
    monkeypatch.setattr(module, "_postgis_has_dml", classifier)
    assert connector.execute_spatial_query(query).id.tolist() == [7]
    connector.connection.commit.assert_called_once()
    connector.connection.rollback.assert_not_called()
    classifier.assert_not_called()


def test_r2_1_constructor_records_connection_ownership(monkeypatch):
    from unittest.mock import MagicMock
    import psycopg2
    import siege_utilities.geo.spatial_transformations as module

    connection = MagicMock()
    connect = MagicMock(return_value=connection)
    monkeypatch.setattr(module, "get_user_config", lambda: None)
    monkeypatch.setattr(psycopg2, "connect", connect)
    connector = PostGISConnector("dbname=test")
    assert connector.connection is connection
    assert connector._opened_connection is True
    connect.assert_called_once_with("dbname=test")


@pytest.mark.parametrize("crs", [None, "EPSG:4326"])
def test_beta_postgis_native_srid_or_requested_crs(postgis_pair, crs):
    connector, _, _ = postgis_pair
    result = connector.execute_spatial_query(
        "SELECT ST_SetSRID(ST_Point(1000000,2000000),3857) AS geometry", crs=crs,
    )
    assert result.crs.to_epsg() == (4326 if crs else 3857)
    if crs is None:
        assert result.geometry.iloc[0].equals_exact(Point(1000000, 2000000), 0)


def test_beta_postgis_table_read_preserves_stored_crs(postgis_pair):
    connector, observer, table = postgis_pair
    with observer.cursor() as cursor:
        cursor.execute(f"INSERT INTO {table} VALUES (7, ST_SetSRID(ST_Point(1000000,2000000),3857))")
    result = connector.download_spatial_data(table.replace('"', ''), geom_col="geometry")
    assert result.crs.to_epsg() == 3857
    assert result.geometry.iloc[0].equals_exact(Point(1000000, 2000000), 0)


def test_beta_postgis_unknown_srid_uses_develop_fallback(postgis_pair, caplog):
    connector, _, _ = postgis_pair
    with caplog.at_level("WARNING"):
        result = connector.execute_spatial_query("SELECT ST_Point(1,2) AS geometry")
    assert result.crs.to_epsg() == 4326
    assert "PostGIS geometries lack SRID metadata" in caplog.text


def test_beta_unquoted_write_token_alias_uses_classifier(postgis_pair):
    connector, observer, table = postgis_pair
    with connector.connection.cursor() as cursor:
        cursor.execute(f"INSERT INTO {table} VALUES (99, ST_SetSRID(ST_Point(0,0),4326))")
    assert connector.execute_spatial_query("SELECT 1 AS merge")["merge"].tolist() == [1]
    with observer.cursor() as cursor:
        cursor.execute(f"SELECT id FROM {table}")
        assert cursor.fetchall() == [(99,)]

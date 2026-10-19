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
    connector = PostGISConnector.__new__(PostGISConnector)
    connector.connection = psycopg2.connect(dsn)
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



def test_b3_select_does_not_commit_caller_pending_write(postgis_pair):
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


@pytest.mark.parametrize("cte", [False, True])
def test_r2_1_caller_write_transaction_remains_caller_managed(postgis_pair, cte):
    connector, observer, table = postgis_pair
    with connector.connection.cursor() as cursor:
        cursor.execute(f"INSERT INTO {table} VALUES (99, ST_SetSRID(ST_Point(0,0),4326))")
    query = f"INSERT INTO {table} VALUES (8, ST_SetSRID(ST_Point(3,4),4326)) RETURNING *"
    if cte:
        query = f"WITH written AS ({query}) SELECT * FROM written"
    assert connector.execute_spatial_query(query).id.tolist() == [8]
    with observer.cursor() as cursor:
        cursor.execute(f"SELECT id FROM {table}")
        assert cursor.fetchall() == []
    connector.connection.rollback()
    with observer.cursor() as cursor:
        cursor.execute(f"SELECT id FROM {table}")
        assert cursor.fetchall() == []


@pytest.mark.parametrize("query", [
    "SELECT 'INSERT INTO places' AS note",
    'SELECT 1 AS "UPDATE" /* DELETE FROM places */',
    "WITH src AS (SELECT $tag$MERGE INTO places$tag$ AS note) SELECT * FROM src",
    "SELECT 1 AS merge -- INSERT INTO places\n",
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
def test_r2_1_every_write_keyword_marks_outer_select_non_read_only(keyword, template):
    """Exercise commit classification independently of PostgreSQL grammar."""
    from unittest.mock import MagicMock

    connector = PostGISConnector.__new__(PostGISConnector)
    connector.connection = MagicMock()
    connector.connection.get_transaction_status.return_value = 0
    cursor = connector.connection.cursor.return_value
    cursor.statusmessage = "SELECT 1"
    cursor.description = [("id",)]
    cursor.fetchall.return_value = [(7,)]
    result = connector.execute_spatial_query(template.format(word=keyword.lower()))
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
    connector.connection = MagicMock()
    connector.connection.get_transaction_status.return_value = 0
    cursor = connector.connection.cursor.return_value
    cursor.statusmessage = "SELECT 1"
    cursor.description = [("id",)]
    cursor.fetchall.return_value = [(7,)]
    assert connector.execute_spatial_query(query).id.tolist() == [7]
    connector.connection.commit.assert_not_called()

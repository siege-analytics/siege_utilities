"""Develop/head characterization of caller-owned PostGIS transactions."""

from unittest.mock import MagicMock

import pytest

from tests.test_1818_spatial_review_postgis import postgis_pair, volatile_insert  # noqa: F401

pytestmark = pytest.mark.postgis


def test_characterization_close_discards_callers_uncommitted_work(postgis_pair):
    connector, observer, table = postgis_pair
    with connector.connection.cursor() as cursor:
        cursor.execute(f"INSERT INTO {table} VALUES (99, ST_SetSRID(ST_Point(0,0),4326))")
    with observer.cursor() as cursor:
        cursor.execute(f"SELECT id FROM {table}")
        assert cursor.fetchall() == []
    connector.close()
    with observer.cursor() as cursor:
        cursor.execute(f"SELECT id FROM {table}")
        assert cursor.fetchall() == []


def test_characterization_caller_volatile_select_waits_for_caller_commit(volatile_insert):
    from psycopg2.extensions import TRANSACTION_STATUS_INTRANS

    connector, observer, table, query = volatile_insert
    connection = connector.connection
    with connection.cursor() as cursor:
        cursor.execute("BEGIN")
    connector.connection = MagicMock(wraps=connection)
    result = connector.execute_spatial_query(query)
    assert result.id.tolist() == [8]
    assert connection.get_transaction_status() == TRANSACTION_STATUS_INTRANS
    connector.connection.commit.assert_not_called()
    connector.connection.rollback.assert_not_called()
    with observer.cursor() as cursor:
        cursor.execute(f"SELECT id FROM {table}")
        assert cursor.fetchall() == []
    connection.commit()
    with observer.cursor() as cursor:
        cursor.execute(f"SELECT id FROM {table}")
        assert cursor.fetchall() == [(8,)]
    connector.close()
    with observer.cursor() as cursor:
        cursor.execute(f"SELECT id FROM {table}")
        assert cursor.fetchall() == [(8,)]

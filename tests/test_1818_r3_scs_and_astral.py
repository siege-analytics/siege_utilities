"""R-1818-3: standard_conforming_strings-aware lexing (F1) and astral dollar
tags (F2).

The lexer-mode cases are pure Python and run anywhere. The real-PostgreSQL cases
exercise the live-setting read and skip without SIEGE_TEST_POSTGIS_DSN (CI's
test-postgis lane and the reviewer run them).
"""
import os
from uuid import uuid4

import pytest

from siege_utilities.geo import spatial_transformations as module
from siege_utilities.geo.spatial_transformations import (
    _sql_statement_list,
    _transaction_control_kind,
)


# -- F1: the two lexer modes diverge only on a backslash, and only the
# backslash (standard_conforming_strings off) mode matches a server with the
# setting off, so it exposes a COMMIT the standard lexer hides inside a string.
def test_backslash_mode_exposes_a_commit_the_standard_lexer_hides():
    # With standard strings, `'a\''; COMMIT; '` is one string (the doubled quote
    # keeps the literal open to the final quote); with backslash escapes the \'
    # closes the first literal, so COMMIT is a real statement.
    query = "SELECT 'a\\''; COMMIT; '"
    standard = _sql_statement_list(query, backslash_escapes=False)
    backslash = _sql_statement_list(query, backslash_escapes=True)
    assert all(_transaction_control_kind(s) is None for s in standard)
    assert any(_transaction_control_kind(s) == "COMMIT" for s in backslash)


def test_escaped_literal_without_hidden_control_is_a_single_statement_both_modes():
    query = "SELECT 'a\\'b' AS label"
    for backslash_escapes in (False, True):
        statements = _sql_statement_list(query, backslash_escapes=backslash_escapes)
        # No top-level semicolon outside a string, so one statement either way.
        assert len(statements) == 1
        assert _transaction_control_kind(statements[0]) is None


def test_e_string_honours_backslash_in_both_modes():
    # An E'' string always honours backslash, so the embedded quote never ends it
    # and the COMMIT stays inside the literal under either setting.
    query = "SELECT E'a\\'; COMMIT; ' AS label"
    for backslash_escapes in (False, True):
        statements = _sql_statement_list(query, backslash_escapes=backslash_escapes)
        assert len(statements) == 1
        assert _transaction_control_kind(statements[0]) is None


@pytest.mark.parametrize("tag", ["review", "\U0001F600", "\U00010000"], ids=["ascii", "emoji", "linearB"])
def test_astral_dollar_tag_body_is_one_statement(tag):
    # A dollar-quoted body with an astral tag swallows the embedded "; COMMIT; ",
    # so the whole input is one statement with no transaction control.
    query = f"SELECT 1 AS a, ${tag}$; COMMIT; ${tag}$ AS label"
    statements = _sql_statement_list(query)
    assert len(statements) == 1
    assert _transaction_control_kind(statements[0]) is None


# -- Real PostgreSQL: the live standard_conforming_strings read + fail-closed.
@pytest.fixture
def pg_pair():
    dsn = os.environ.get("SIEGE_TEST_POSTGIS_DSN")
    if not dsn:
        pytest.skip("SIEGE_TEST_POSTGIS_DSN not set; real-PostgreSQL SCS cases need a live cluster")
    import psycopg2

    observer = psycopg2.connect(dsn)
    observer.autocommit = True
    client = module.PostGISConnector(dsn)
    table = "review_scs_" + uuid4().hex
    with observer.cursor() as cursor:
        cursor.execute(f"CREATE TABLE {table}(id INT, geometry geometry)")
    try:
        yield client, observer, table
    finally:
        client.close()
        with observer.cursor() as cursor:
            cursor.execute(f"DROP TABLE {table}")
        observer.close()


@pytest.mark.parametrize("scs", ["on", "off"])
@pytest.mark.parametrize("autocommit", [False, True])
@pytest.mark.parametrize("caller", [False, True])
def test_real_pg_backslash_commit_is_rejected_on_both_settings(pg_pair, scs, autocommit, caller):
    client, observer, table = pg_pair
    conn = client.connection
    conn.autocommit = autocommit
    with conn.cursor() as cursor:
        cursor.execute(f"SET standard_conforming_strings = {scs}")
    if caller and not autocommit:
        with conn.cursor() as cursor:
            cursor.execute("BEGIN")
            cursor.execute(f"INSERT INTO {table} VALUES(99, ST_SetSRID(ST_Point(1,2),4326))")
    payload = (
        f"INSERT INTO {table} VALUES(8, ST_SetSRID(ST_Point(1,2),4326)); "
        "SELECT 'a\\''; COMMIT; ' AS geometry"
    )
    with pytest.raises(module.SpatialQueryError):
        client.execute_spatial_query(payload, crs="EPSG:4326")
    with observer.cursor() as cursor:
        cursor.execute(f"SELECT id FROM {table}")
        assert cursor.fetchall() == []
    if caller and not autocommit:
        conn.rollback()


@pytest.mark.parametrize("scs", ["on", "off"])
def test_real_pg_valid_escaped_literal_is_accepted(pg_pair, scs):
    client, observer, table = pg_pair
    with client.connection.cursor() as cursor:
        cursor.execute(f"SET standard_conforming_strings = {scs}")
    literal = "a\\'b" if scs == "off" else "a''b"
    result = client.execute_spatial_query(
        f"SELECT '{literal}' AS label, ST_SetSRID(ST_Point(1,2),4326) AS geometry"
    )
    assert len(result) == 1

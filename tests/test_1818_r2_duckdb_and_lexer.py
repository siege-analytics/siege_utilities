"""R-1818-2: DuckDB upload/query transaction join + SQL-guard lexer fixes.

Covers F1 (upload joins a caller DuckDB transaction with no BEGIN/COMMIT/ROLLBACK
of its own), F2 (``--`` comments end at CR and CRLF; a comment-terminated control
batch is rejected before execution) and F3 (Unicode dollar-quote tags). DuckDB
and pure-lexer only; no external services.
"""
import duckdb
import geopandas as gpd
import pytest
from shapely.geometry import Point

from siege_utilities.geo import spatial_transformations as module
from siege_utilities.geo.spatial_transformations import (
    _sql_statement_list,
    _transaction_control_kind,
)


def _connector():
    client = module.DuckDBConnector.__new__(module.DuckDBConnector)
    client.connection = duckdb.connect(":memory:")
    return client


def _frame():
    return gpd.GeoDataFrame({"id": [1]}, geometry=[Point(1, 2)], crs="EPSG:4326")


@pytest.mark.parametrize("mode", ["fail", "append", "replace"])
@pytest.mark.parametrize("finalizer", ["COMMIT", "ROLLBACK"])
def test_upload_joins_caller_transaction(mode, finalizer):
    # F1: upload must join the caller's transaction. On COMMIT the caller row and
    # the target rows are both present; on ROLLBACK neither survives. At head the
    # unconditional BEGIN raised "transaction within a transaction" and lost the
    # caller's row.
    client = _connector()
    conn = client.connection
    try:
        conn.execute("CREATE TABLE pending(id INT)")
        conn.execute("BEGIN")
        conn.execute("INSERT INTO pending VALUES(99)")
        client.upload_spatial_data(_frame(), "places", if_exists=mode)
        conn.execute(finalizer)
        pending = conn.execute("SELECT id FROM pending").fetchall()
        places_exists = conn.execute(
            "SELECT COUNT(*) FROM information_schema.tables WHERE table_name='places'"
        ).fetchone()[0]
        if finalizer == "COMMIT":
            assert pending == [(99,)]
            assert conn.execute("SELECT id FROM places").fetchall() == [(1,)]
        else:
            assert pending == []
            assert places_exists == 0
    finally:
        client.close()


@pytest.mark.parametrize("mode", ["fail", "append", "replace"])
def test_upload_without_caller_is_durable(mode):
    # Autocommit: the connector owns BEGIN/COMMIT and the write is durable.
    client = _connector()
    try:
        client.upload_spatial_data(_frame(), "places", if_exists=mode)
        assert client.connection.execute("SELECT id FROM places").fetchall() == [(1,)]
    finally:
        client.close()


@pytest.mark.parametrize("newline", ["\n", "\r\n", "\r"], ids=["LF", "CRLF", "CR"])
def test_comment_terminated_control_batch_rejected(newline):
    # F2: a COMMIT hidden behind a `--` comment that ends at the given newline is
    # rejected before anything executes, so the INSERT never commits.
    client = _connector()
    try:
        client.connection.execute("CREATE TABLE places(id INT, geometry_wkt VARCHAR)")
        query = (
            f"INSERT INTO places VALUES(8,'POINT (1 2)'); -- review{newline}"
            f"COMMIT;{newline}SELECT 'not geometry' AS geometry_wkt"
        )
        with pytest.raises(module.SpatialQueryError):
            client.execute_spatial_query(query)
        assert client.connection.execute("SELECT id FROM places").fetchall() == []
    finally:
        client.close()


def test_cr_comment_ends_and_exposes_following_statements():
    # F2 lexer: a `--` comment ends at CR, so COMMIT and SELECT are their own
    # statements rather than being swallowed as comment text.
    statements = _sql_statement_list("INSERT INTO t VALUES(8); -- x\rCOMMIT;\rSELECT 1")
    assert len(statements) == 3
    assert _transaction_control_kind(statements[1]) == "COMMIT"


@pytest.mark.parametrize("tag", ["review", "é", "分析"])
def test_unicode_dollar_tag_body_is_a_single_statement(tag):
    # F3 lexer: a Unicode-tagged dollar body swallows the embedded "; COMMIT; ",
    # so the whole input is one statement with no transaction control and is not
    # wrongly rejected as a mixed-control batch.
    query = f"SELECT 1 AS a, ${tag}$; COMMIT; ${tag}$ AS label"
    statements = _sql_statement_list(query)
    assert len(statements) == 1
    assert _transaction_control_kind(statements[0]) is None

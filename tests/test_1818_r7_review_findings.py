"""Regressions for the PR #1818 review findings fixed in round 7.

Each test failed at 3263e7f2 and passes after the fix:

* astral characters inside an unquoted word (lexer word range);
* PostgreSQL ``BEGIN ATOMIC`` function bodies kept as one statement;
* SELECT classified by its first word, not a string prefix;
* statements that cannot run inside a transaction block under autocommit;
* an equivalent CRS spelled differently on DuckDB append and download;
* the DuckDB floor required by ``COMMENT ON TABLE``.

The live-PostGIS cases use the shared ``postgis_pair`` fixture and skip without
``SIEGE_TEST_POSTGIS_DSN``.
"""

import json
import re
import tomllib
from pathlib import Path

import pytest

from siege_utilities.geo import spatial_transformations as module
from siege_utilities.geo.spatial_transformations import (
    _postgis_has_dml,
    _sql_statement_list,
    _sql_tokens,
    _transaction_control_kind,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
ASTRAL = "\U0001d400"  # MATHEMATICAL BOLD CAPITAL A, outside the BMP


# --- Astral characters inside an unquoted word -------------------------------


@pytest.mark.parametrize("backslash_escapes", [False, True])
def test_astral_character_stays_inside_one_word(backslash_escapes):
    word = f"drop{ASTRAL}col"
    assert list(_sql_tokens(word, backslash_escapes)) == [("word", word)]


@pytest.mark.parametrize("backslash_escapes", [False, True])
def test_astral_word_prefix_is_not_a_write_keyword(backslash_escapes):
    query = f"WITH x AS (SELECT 1 AS update{ASTRAL}col) SELECT * FROM x"
    assert _postgis_has_dml(query, backslash_escapes) is False


def test_astral_word_prefix_is_not_transaction_control():
    (statement,) = _sql_statement_list(f"commit{ASTRAL}x")
    assert _transaction_control_kind(statement) is None


@pytest.mark.postgis
def test_astral_identifier_read_does_not_commit_caller_transaction(postgis_pair):
    connector, observer, table = postgis_pair
    with connector.connection.cursor() as cursor:
        cursor.execute(f"INSERT INTO {table} VALUES (99, ST_SetSRID(ST_Point(0,0),4326))")
    result = connector.execute_spatial_query(
        f"WITH x AS (SELECT 1 AS update{ASTRAL}col) SELECT * FROM x"
    )
    assert result[f"update{ASTRAL}col"].tolist() == [1]
    with observer.cursor() as cursor:
        cursor.execute(f"SELECT id FROM {table}")
        assert cursor.fetchall() == [], "a read-only CTE committed the caller's pending insert"
    connector.connection.rollback()


# --- PostgreSQL BEGIN ATOMIC bodies --------------------------------------------

ATOMIC_BODY = (
    "CREATE FUNCTION {name}(x int) RETURNS int LANGUAGE sql BEGIN ATOMIC "
    "SELECT 1; SELECT CASE WHEN x > 0 THEN x ELSE 0 END; END"
)


def test_atomic_body_is_one_statement_on_postgres():
    statements = _sql_statement_list(ATOMIC_BODY.format(name="f"), postgres_atomic=True)
    assert len(statements) == 1
    assert _transaction_control_kind(statements[0]) is None


def test_atomic_body_then_another_statement_splits_after_end():
    query = ATOMIC_BODY.format(name="f") + "; SELECT 2"
    statements = _sql_statement_list(query, postgres_atomic=True)
    assert len(statements) == 2
    assert [value for _, value in statements[1]] == ["SELECT", "2"]


@pytest.mark.parametrize("query", [
    "BEGIN; INSERT INTO t VALUES (1); COMMIT",
    "BEGIN ATOMIC; SELECT 1",
])
def test_transaction_begin_is_not_an_atomic_body(query):
    # BEGIN as a statement's first word is transaction control, never a body.
    statements = _sql_statement_list(query, postgres_atomic=True)
    assert len(statements) > 1
    assert _transaction_control_kind(statements[0]) == "BEGIN"


@pytest.mark.parametrize("head", [
    "CREATE OR REPLACE FUNCTION f(x int) RETURNS int LANGUAGE sql",
    "CREATE PROCEDURE p(x int) LANGUAGE sql",
])
def test_atomic_body_opens_for_replace_and_procedure(head):
    query = head + " BEGIN ATOMIC SELECT 1; SELECT CASE WHEN x > 0 THEN x ELSE 0 END; END"
    assert len(_sql_statement_list(query, postgres_atomic=True)) == 1


@pytest.mark.parametrize("query", [
    # A column named begin with the bare alias atomic is ordinary SQL.
    "SELECT begin atomic FROM t; COMMIT; SELECT 1",
    # Inside parentheses (a parameter named begin of a type named atomic).
    "CREATE FUNCTION f(begin atomic) RETURNS int LANGUAGE sql AS 'select 1'; COMMIT; SELECT 1",
])
def test_begin_atomic_outside_a_routine_body_does_not_hide_commit(query):
    statements = _sql_statement_list(query, postgres_atomic=True)
    assert len(statements) == 3
    assert _transaction_control_kind(statements[1]) == "COMMIT"


@pytest.mark.postgis
def test_bare_begin_atomic_alias_cannot_smuggle_commit(postgis_pair):
    connector, observer, table = postgis_pair
    with connector.connection.cursor() as cursor:
        cursor.execute(f"INSERT INTO {table} VALUES (99, ST_SetSRID(ST_Point(0,0),4326))")
    query = "SELECT begin atomic FROM (SELECT 1 AS begin) s; COMMIT; SELECT 1 AS x"
    with pytest.raises(module.SpatialQueryError, match="multi-statement batch"):
        connector.execute_spatial_query(query)
    with observer.cursor() as cursor:
        cursor.execute(f"SELECT id FROM {table}")
        assert cursor.fetchall() == [], "the smuggled COMMIT committed the caller's insert"
    connector.connection.rollback()


def test_atomic_tracking_is_postgres_only():
    # DuckDB has no BEGIN ATOMIC bodies; its split is unchanged.
    assert len(_sql_statement_list(ATOMIC_BODY.format(name="f"))) == 3


@pytest.mark.postgis
def test_atomic_function_body_executes(postgis_pair):
    connector, observer, table = postgis_pair
    name = table.rsplit(".", 1)[0] + ".atomic_pick"
    connector.execute_spatial_query(ATOMIC_BODY.format(name=name))
    with observer.cursor() as cursor:
        cursor.execute(f"SELECT {name}(5), {name}(-5)")
        assert cursor.fetchone() == (5, 0)


# --- SELECT classified by its first word ---------------------------------------


@pytest.mark.postgis
@pytest.mark.parametrize("prefix", ["-- lock rows\n", "/* lock */ ", "("], ids=["line-comment", "block-comment", "paren"])
def test_select_for_update_never_commits_caller_transaction(postgis_pair, prefix):
    connector, observer, table = postgis_pair
    with connector.connection.cursor() as cursor:
        cursor.execute(f"INSERT INTO {table} VALUES (99, ST_SetSRID(ST_Point(0,0),4326))")
    query = f"{prefix}SELECT id FROM {table} FOR UPDATE" + (")" if prefix == "(" else "")
    result = connector.execute_spatial_query(query)
    assert result.id.tolist() == [99]
    with observer.cursor() as cursor:
        cursor.execute(f"SELECT id FROM {table}")
        assert cursor.fetchall() == [], "SELECT ... FOR UPDATE committed the caller's transaction"
    connector.connection.rollback()


@pytest.mark.postgis
def test_commented_write_still_commits_caller_transaction(postgis_pair):
    # Develop parity: a non-SELECT statement with write tokens commits.
    connector, observer, table = postgis_pair
    with connector.connection.cursor() as cursor:
        cursor.execute("SELECT 1")
    connector.execute_spatial_query(
        f"/* load */ INSERT INTO {table} VALUES (5, ST_SetSRID(ST_Point(0,0),4326))"
    )
    with observer.cursor() as cursor:
        cursor.execute(f"SELECT id FROM {table}")
        assert cursor.fetchall() == [(5,)]


# --- No-transaction-block statements under autocommit --------------------------


@pytest.mark.parametrize("query, expected", [
    ("VACUUM t", True),
    ("vacuum (analyze) t", True),
    ("ALTER SYSTEM SET work_mem = '8MB'", True),
    ("CREATE DATABASE d", True),
    ("DROP DATABASE IF EXISTS d", True),
    ("CREATE TABLESPACE s LOCATION '/x'", True),
    ("DROP TABLESPACE s", True),
    ("CREATE INDEX CONCURRENTLY i ON t (id)", True),
    ("CREATE UNIQUE INDEX CONCURRENTLY i ON t (id)", True),
    ("DROP INDEX CONCURRENTLY i", True),
    ("REINDEX INDEX CONCURRENTLY i", True),
    ("REINDEX DATABASE d", True),
    ("REINDEX SYSTEM d", True),
    ("/* maintenance */ VACUUM t", True),
    ("CREATE INDEX i ON t (id)", False),
    ("REINDEX TABLE t", False),
    ("ALTER TABLE t ADD COLUMN c int", False),
    ("INSERT INTO t VALUES (1)", False),
    ("SELECT 'VACUUM'", False),
    ("VACUUM t; VACUUM u", False),
])
def test_requires_no_transaction_block(query, expected):
    assert module._requires_no_transaction_block(_sql_statement_list(query)) is expected


@pytest.mark.postgis
@pytest.mark.parametrize("statement", ["VACUUM {table}", "CREATE INDEX CONCURRENTLY places_id_idx ON {table} (id)"])
def test_no_transaction_block_statement_runs_under_autocommit(postgis_pair, statement):
    connector, observer, table = postgis_pair
    connector.connection.autocommit = True
    assert connector.execute_spatial_query(statement.format(table=table)) == -1
    if "INDEX" in statement:
        schema = table.rsplit(".", 1)[0].strip('"')
        with observer.cursor() as cursor:
            cursor.execute(
                "SELECT indexname FROM pg_indexes WHERE schemaname = %s", (schema,)
            )
            assert cursor.fetchall() == [("places_id_idx",)]


@pytest.mark.postgis
def test_autocommit_failed_write_still_rolls_back(postgis_pair):
    # Ordinary writes keep the connector-owned BEGIN/ROLLBACK under autocommit.
    connector, observer, table = postgis_pair
    connector.connection.autocommit = True
    with pytest.raises(module.SpatialQueryError):
        connector.execute_spatial_query(
            f"INSERT INTO {table} VALUES (1, ST_SetSRID(ST_Point(0,0),4326)) "
            "RETURNING 'not WKB'::text AS geometry"
        )
    with observer.cursor() as cursor:
        cursor.execute(f"SELECT id FROM {table}")
        assert cursor.fetchall() == []


# --- Equivalent CRS spelled differently (DuckDB) -------------------------------


def _frame(crs):
    gpd = pytest.importorskip("geopandas")
    point = pytest.importorskip("shapely.geometry").Point
    return gpd.GeoDataFrame({"id": [1]}, geometry=[point(1, 2)], crs=crs)


def _equivalent_spelling():
    """EPSG:4326 under another name: equal per pyproj, different canonical WKT.

    PROJ's equivalence test ignores object names, while pyproj hashes the
    canonical WKT, so a set of the two CRS objects has two members.
    """
    from pyproj import CRS

    canonical = CRS("EPSG:4326")
    variant = canonical.to_wkt().replace('GEOGCRS["WGS 84"', 'GEOGCRS["WGS 84 (stored)"', 1)
    assert CRS(variant) == canonical
    assert CRS(variant).to_wkt() != canonical.to_wkt()
    assert len({CRS(variant), canonical}) == 2
    return variant


def test_result_frame_accepts_equivalent_crs_spellings():
    pd = pytest.importorskip("pandas")
    from pyproj import CRS

    frame = pd.DataFrame({"id": [1], "geometry_wkt": ["POINT (1 2)"]})
    stored = [CRS("EPSG:4326").to_wkt(), _equivalent_spelling()]
    result = module._duckdb_result_frame(frame, stored_crs=stored)
    assert result.crs == CRS("EPSG:4326")


def test_append_with_equivalent_crs_spelling_keeps_table_readable(duck_connector):
    from pyproj import CRS

    duck_connector.upload_spatial_data(_frame("EPSG:4326"), "places")
    # Re-spell the stored CRS the way another tool or PROJ build might name it.
    variant = _equivalent_spelling()
    comment = "\nsiege_utilities.crs.v1=" + json.dumps([variant])
    duck_connector.connection.execute(
        "COMMENT ON TABLE places IS '" + comment.replace("'", "''") + "'"
    )
    duck_connector.upload_spatial_data(_frame("EPSG:4326"), "places", if_exists="append")
    _, stored = module._duckdb_table_metadata(duck_connector.connection, "places")
    assert stored == [variant], "append kept a second spelling of the same CRS"
    result = duck_connector.download_spatial_data("places")
    assert result.crs == CRS("EPSG:4326")
    assert result.id.tolist() == [1, 1]


def test_download_tolerates_existing_equivalent_spellings(duck_connector):
    # Tables written before the append fix may already hold both spellings.
    from pyproj import CRS

    duck_connector.upload_spatial_data(_frame("EPSG:4326"), "places")
    both = [CRS("EPSG:4326").to_wkt(), _equivalent_spelling()]
    comment = "\nsiege_utilities.crs.v1=" + json.dumps(both)
    duck_connector.connection.execute(
        "COMMENT ON TABLE places IS '" + comment.replace("'", "''") + "'"
    )
    assert duck_connector.download_spatial_data("places").crs == CRS("EPSG:4326")


def test_append_with_different_crs_is_still_rejected(duck_connector):
    duck_connector.upload_spatial_data(_frame("EPSG:4326"), "places")
    with pytest.raises(RuntimeError, match="different source CRS"):
        duck_connector.upload_spatial_data(_frame("EPSG:3857"), "places", if_exists="append")


# --- DuckDB standalone transaction control (thread 4312759702) ----------------


def _duck_rows(connector):
    return connector.connection.execute("SELECT id FROM pending ORDER BY id").fetchall()


@pytest.mark.parametrize("finalizer, expected", [("COMMIT", [(1,)]), ("ROLLBACK", [])])
def test_duckdb_standalone_control_statements_run_unwrapped(duck_connector, finalizer, expected):
    # A standalone BEGIN/COMMIT/ROLLBACK runs as written: no connector-owned
    # BEGIN around it (which DuckDB would reject as a nested transaction) and no
    # connector COMMIT after it, so the caller's transaction spans the calls.
    duck_connector.connection.execute("CREATE TABLE pending(id INT)")
    assert duck_connector.execute_spatial_query("BEGIN") == -1
    duck_connector.execute_spatial_query("INSERT INTO pending VALUES (1)")
    assert duck_connector.execute_spatial_query(finalizer) == -1
    assert _duck_rows(duck_connector) == expected


def test_duckdb_standalone_begin_leaves_transaction_open(duck_connector):
    duck_connector.connection.execute("CREATE TABLE pending(id INT)")
    duck_connector.execute_spatial_query("BEGIN")
    duck_connector.execute_spatial_query("INSERT INTO pending VALUES (1)")
    assert duck_connector._caller_owns_transaction()
    duck_connector.connection.execute("ROLLBACK")
    assert _duck_rows(duck_connector) == []


@pytest.mark.parametrize("query", [
    "BEGIN; INSERT INTO pending VALUES (1); COMMIT",
    "INSERT INTO pending VALUES (1); COMMIT",
    "BEGIN; INSERT INTO pending VALUES (1)",
])
def test_duckdb_mixed_control_batch_is_rejected_with_no_side_effects(duck_connector, query):
    duck_connector.connection.execute("CREATE TABLE pending(id INT)")
    with pytest.raises(module.SpatialQueryError, match="multi-statement batch"):
        duck_connector.execute_spatial_query(query)
    assert _duck_rows(duck_connector) == []
    assert not duck_connector._caller_owns_transaction()


# --- DuckDB floor for COMMENT ON TABLE ----------------------------------------


@pytest.mark.parametrize("extra", ["performance", "all"])
def test_duckdb_extra_floor_supports_comment_on_table(extra):
    # COMMENT ON TABLE and duckdb_tables().comment arrived in DuckDB 0.10.0.
    project = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text())
    pins = [p for p in project["project"]["optional-dependencies"][extra] if p.startswith("duckdb")]
    assert len(pins) == 1
    floor = re.search(r">=\s*([0-9.]+)", pins[0]).group(1)
    assert tuple(int(part) for part in floor.split(".")) >= (0, 10, 0), pins[0]

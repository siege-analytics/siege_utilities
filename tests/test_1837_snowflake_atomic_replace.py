"""Regression tests for #1837: a failed overwrite must not drop the table.

``SnowflakeConnector.upload_dataframe(..., overwrite=True)`` used to run
``DROP TABLE`` and then a separate ``CREATE TABLE`` under autocommit, and the
``auto_create_table=False`` path truncated the table before copying, so a
failed create or load left the caller's table absent or empty. Overwrite now
loads a uniquely named staging table first:

* ``auto_create_table=True``: the staging table is swapped in, or renamed into
  place when there is no target;
* ``auto_create_table=False``: the target's rows are replaced from the staging
  table with one ``INSERT OVERWRITE``, keeping the target table object.

These tests use an in-memory fake of Snowflake's autocommit SQL. They do not
talk to Snowflake. The fake models table objects (identity, rows, columns,
grants, kind), ``DROP``/``CREATE``/``LIKE``, ``SWAP WITH``, ``RENAME TO``,
``INSERT OVERWRITE``, the INFORMATION_SCHEMA existence probe and
``write_pandas``. Each statement can fail before it takes effect, or after it
took effect while the client still sees an error. Its rules follow the
Snowflake documentation, not observation: a new table is permanent and gets
the schema's future grants, except that a ``LIKE ... COPY GRANTS`` table gets
the source's grants instead; a ``LIKE`` table copies columns; a swap exchanges
which object each name refers to; ``INSERT OVERWRITE`` replaces the rows of the
same object and is rolled back on failure.
"""

import logging
import re

import pandas as pd
import pytest

pytest.importorskip("snowflake.connector")

from snowflake.connector.errors import (  # noqa: E402
    InterfaceError,
    OperationalError,
    ProgrammingError,
)

from siege_utilities.analytics import snowflake_connector as sc  # noqa: E402

_NAME = r'"([A-Za-z0-9_]+)"'


class Table:
    """One table object; identity is the Python object."""

    def __init__(self, rows=(), columns=("amount",), grants=(), kind="PERMANENT"):
        self.rows = [dict(row) for row in rows]
        self.columns = list(columns)
        self.grants = set(grants)
        self.kind = kind


class FakeSnowflake:
    """Autocommit fake: every statement takes effect immediately or not at all."""

    def __init__(self, tables=None):
        self.tables = dict(tables or {})
        self.statements = []
        self.dropped = []
        self.fail_on = []      # (pattern, exception): raise before the statement
        self.raise_after = []  # (pattern, exception): apply, then raise
        self.fail_write = None
        self.future_grants = set()  # schema-level future grants on tables
        self.write_calls = []       # (table, auto_create_table, overwrite, grants at load)
        self._result = None

    def _inject(self, rules, sql):
        for pattern, exc in rules:
            if re.search(pattern, sql):
                raise exc

    # --- cursor API ------------------------------------------------------
    def execute(self, sql, params=None):
        self.statements.append(sql)
        self._inject(self.fail_on, sql)
        self._apply(sql, params)
        self._inject(self.raise_after, sql)
        return self

    def _apply(self, sql, params):
        if sql.startswith(("USE DATABASE", "USE SCHEMA")):
            return
        if "INFORMATION_SCHEMA.TABLES" in sql:
            self._result = (int(params[0] in self.tables),)
            return
        match = re.fullmatch(rf"DROP TABLE IF EXISTS {_NAME}", sql)
        if match:
            table = self.tables.pop(match[1], None)
            if table is not None:
                self.dropped.append((match[1], table))
            return
        match = re.fullmatch(rf"CREATE TABLE( IF NOT EXISTS)? {_NAME} \((.*)\)", sql)
        if match:
            if match[2] in self.tables:
                if match[1]:
                    return
                raise ProgrammingError(f"Object '{match[2]}' already exists.")
            self.tables[match[2]] = Table(columns=re.findall(r'"([^"]+)" ', match[3]),
                                          grants=self.future_grants)
            return
        match = re.fullmatch(rf"CREATE TABLE {_NAME} LIKE {_NAME}( COPY GRANTS)?", sql)
        if match:
            if match[1] in self.tables:
                raise ProgrammingError(f"Object '{match[1]}' already exists.")
            if match[2] not in self.tables:
                raise ProgrammingError(f"Table '{match[2]}' does not exist.")
            source = self.tables[match[2]]
            # COPY GRANTS: the source's grants and no future grants; without
            # it, the schema's future grants.
            grants = source.grants if match[3] else self.future_grants
            self.tables[match[1]] = Table(columns=source.columns, grants=grants)
            return
        match = re.fullmatch(rf"ALTER TABLE {_NAME} SWAP WITH {_NAME}", sql)
        if match:
            a, b = match[1], match[2]
            if a not in self.tables or b not in self.tables:
                raise ProgrammingError("SWAP needs both tables")
            if "TEMPORARY" in (self.tables[a].kind, self.tables[b].kind):
                raise ProgrammingError("cannot swap a temporary table")
            self.tables[a], self.tables[b] = self.tables[b], self.tables[a]
            return
        match = re.fullmatch(rf"ALTER TABLE {_NAME} RENAME TO {_NAME}", sql)
        if match:
            if match[2] in self.tables:
                raise ProgrammingError(f"Object '{match[2]}' already exists.")
            self.tables[match[2]] = self.tables.pop(match[1])
            return
        match = re.fullmatch(rf"INSERT OVERWRITE INTO {_NAME} \((.*) FROM {_NAME}", sql, re.S)
        if match:
            target, source = self.tables.get(match[1]), self.tables.get(match[3])
            columns = self._parse_insert_columns(match[2])
            if target is None or source is None:
                raise ProgrammingError("INSERT OVERWRITE needs both tables")
            if columns is None or not set(columns) <= set(target.columns):
                raise ProgrammingError("invalid column list")
            target.rows = [{c: row.get(c) for c in columns} for row in source.rows]
            return
        raise AssertionError(f"fake does not understand SQL: {sql}")

    @staticmethod
    def _parse_insert_columns(middle):
        """Split '<list>) SELECT <list>' with identical lists into column names.

        Each list must be comma-separated double-quoted identifiers with any
        embedded double quote doubled, as Snowflake requires. Returns None for
        anything else, including an unescaped quote or an unquoted name.
        """
        separator = ") SELECT "
        half = (len(middle) - len(separator)) // 2
        left, sep, right = middle[:half], middle[half:half + len(separator)], middle[half + len(separator):]
        token = r'"((?:[^"]|"")+)"'
        if sep != separator or left != right or not re.fullmatch(rf"{token}(?:, {token})*", left, re.S):
            return None
        return [name.replace('""', '"') for name in re.findall(token, left, re.S)]

    def fetchone(self):
        return self._result

    def fetchall(self):
        return []

    def commit(self):
        pass

    # --- write_pandas ----------------------------------------------------
    def write_pandas(self, conn, df, table_name, *, auto_create_table, overwrite, **kwargs):
        assert auto_create_table is False
        table = self.tables.get(table_name)
        if table is None:
            raise ProgrammingError(f"Table '{table_name}' does not exist.")
        self.write_calls.append((table_name, auto_create_table, overwrite, set(table.grants)))
        if not set(df.columns) <= set(table.columns):
            raise ProgrammingError("invalid identifier")
        if overwrite:
            table.rows = []  # SDK: TRUNCATE before COPY
        if self.fail_write is not None:
            raise self.fail_write
        table.rows.extend(df.to_dict("records"))
        return True, 1, len(df), None


OLD = [{"amount": 1}, {"amount": 2}]
NEW = pd.DataFrame({"amount": [10, 20, 30]})
NEW_ROWS = NEW.to_dict("records")
BOTH_PATHS = pytest.mark.parametrize("auto_create", [True, False], ids=["swap", "insert_overwrite"])


@pytest.fixture
def original():
    return Table(OLD, grants={("SELECT", "ANALYST")}, kind="TRANSIENT")


@pytest.fixture
def fake(original):
    return FakeSnowflake({"events": original})


@pytest.fixture
def connector(monkeypatch, fake):
    monkeypatch.setattr(sc, "write_pandas", fake.write_pandas)
    conn = sc.SnowflakeConnector(account="acct", user="user")
    conn.connection = object()
    conn.cursor = fake
    return conn


def _staging_tables(fake):
    return [name for name in fake.tables if "_SU_STAGE_" in name]


def _fixed_uuid(monkeypatch, hex_value):
    class FixedUuid:
        hex = hex_value

    monkeypatch.setattr(sc.uuid, "uuid4", lambda: FixedUuid())


# --- failure atomicity: the reviewer's fixture and its siblings ------------


@BOTH_PATHS
def test_failed_create_does_not_leave_table_absent(connector, fake, original, auto_create):
    fake.fail_on.append((r"^CREATE TABLE", ProgrammingError("injected CREATE failure")))

    with pytest.raises(RuntimeError, match="injected CREATE failure"):
        connector.upload_dataframe(NEW, "events", auto_create_table=auto_create, overwrite=True)

    assert fake.tables == {"events": original}
    assert original.rows == OLD
    assert fake.dropped == []


@BOTH_PATHS
def test_failed_load_keeps_original_rows(connector, fake, original, auto_create):
    fake.fail_write = ProgrammingError("injected COPY failure")

    with pytest.raises(RuntimeError, match="injected COPY failure"):
        connector.upload_dataframe(NEW, "events", auto_create_table=auto_create, overwrite=True)

    assert fake.tables == {"events": original}
    assert original.rows == OLD


@BOTH_PATHS
def test_keyboard_interrupt_during_load_keeps_original_and_cleans_up(
    connector, fake, original, auto_create
):
    """Kills a mutant that narrows ``except BaseException`` to ``Exception``."""
    fake.fail_write = KeyboardInterrupt()

    with pytest.raises(KeyboardInterrupt):
        connector.upload_dataframe(NEW, "events", auto_create_table=auto_create, overwrite=True)

    assert fake.tables == {"events": original}
    assert original.rows == OLD


def test_failed_swap_keeps_original_and_drops_staging(connector, fake, original):
    fake.fail_on.append((r"SWAP WITH", ProgrammingError("injected SWAP failure")))

    with pytest.raises(RuntimeError, match="injected SWAP failure"):
        connector.upload_dataframe(NEW, "events", overwrite=True)

    assert fake.tables == {"events": original}
    assert original.rows == OLD


def test_failed_insert_overwrite_keeps_original_rows(connector, fake, original):
    fake.fail_on.append((r"^INSERT OVERWRITE", ProgrammingError("injected INSERT failure")))

    with pytest.raises(RuntimeError, match="injected INSERT failure"):
        connector.upload_dataframe(NEW, "events", auto_create_table=False, overwrite=True)

    assert fake.tables == {"events": original}
    assert original.rows == OLD


def test_write_pandas_reporting_failure_keeps_original(connector, fake, original, monkeypatch):
    monkeypatch.setattr(sc, "write_pandas", lambda *a, **k: (False, 1, 0, None))

    with pytest.raises(RuntimeError, match="write_pandas reported failure"):
        connector.upload_dataframe(NEW, "events", overwrite=True)

    assert fake.tables == {"events": original}
    assert original.rows == OLD


def test_original_is_never_dropped_before_new_data_is_in_place(connector, fake):
    connector.upload_dataframe(NEW, "events", overwrite=True)

    assert 'DROP TABLE IF EXISTS "events"' not in fake.statements
    swap = next(i for i, s in enumerate(fake.statements) if "SWAP WITH" in s)
    assert swap == max(
        i for i, s in enumerate(fake.statements) if '"events"' in s and "INFORMATION" not in s
    )


# --- auto_create_table=False keeps the table object (S2-1) ----------------


def test_overwrite_without_auto_create_keeps_object_grants_and_kind(connector, fake, original):
    connector.upload_dataframe(NEW, "events", auto_create_table=False, overwrite=True)

    after = fake.tables["events"]
    assert after is original
    assert after.grants == {("SELECT", "ANALYST")}
    assert after.kind == "TRANSIENT"
    assert after.rows == NEW_ROWS
    assert _staging_tables(fake) == []
    assert not any(s.startswith(("ALTER", 'DROP TABLE IF EXISTS "events"')) for s in fake.statements)


def test_overwrite_without_auto_create_uses_one_insert_overwrite(connector, fake):
    connector.upload_dataframe(NEW, "events", auto_create_table=False, overwrite=True)

    staging = re.fullmatch(
        r'CREATE TABLE "(events_SU_STAGE_[0-9A-F]{12})" LIKE "events" COPY GRANTS',
        fake.statements[0],
    )[1]
    assert fake.statements[1:] == [
        f'INSERT OVERWRITE INTO "events" ("amount") SELECT "amount" FROM "{staging}"',
        f'DROP TABLE IF EXISTS "{staging}"',
    ]


def test_staging_table_does_not_expose_rows_to_schema_future_grants(connector, fake, original):
    # The schema grants future SELECT to READER, but READER cannot read
    # "events" (its access was revoked). The staging table must not let
    # READER read the new rows, even while they are staged.
    fake.future_grants = {("SELECT", "READER")}

    connector.upload_dataframe(NEW, "events", auto_create_table=False, overwrite=True)

    [(staging, _, _, staging_grants)] = fake.write_calls
    assert "_SU_STAGE_" in staging
    assert staging_grants == {("SELECT", "ANALYST")}
    assert original.grants == {("SELECT", "ANALYST")}
    assert fake.tables["events"] is original and original.rows == NEW_ROWS


def test_swap_target_gets_future_grants_like_a_recreated_table(connector, fake, original):
    # Unchanged from 6.0.0: the new target object of a swap is a new table,
    # as the table re-created after DROP was, so it gets the schema's future
    # grants and not the previous object's explicit grants.
    fake.future_grants = {("SELECT", "READER")}

    connector.upload_dataframe(NEW, "events", auto_create_table=True, overwrite=True)

    assert fake.tables["events"] is not original
    assert fake.tables["events"].grants == {("SELECT", "READER")}


@BOTH_PATHS
def test_staging_load_uses_the_overwrite_copy_options(connector, fake, auto_create):
    # The overwrite path passed overwrite=True to write_pandas before #1837,
    # which makes the SDK read binary columns with BINARY_AS_TEXT=FALSE and
    # infer column types. The staging load keeps those options; on the empty
    # staging table overwrite only truncates. The fake cannot decode Parquet,
    # so this checks the arguments, not the binary decoding itself.
    connector.upload_dataframe(NEW, "events", auto_create_table=auto_create, overwrite=True)

    [(table, auto_create_table, overwrite, _)] = fake.write_calls
    assert re.fullmatch(r"events_SU_STAGE_[0-9A-F]{12}", table)
    assert auto_create_table is False
    assert overwrite is True


def test_overwrite_without_auto_create_column_mismatch_keeps_original(connector, fake, original):
    with pytest.raises(RuntimeError, match="invalid identifier"):
        connector.upload_dataframe(
            pd.DataFrame({"amount": [1], "extra": [2]}), "events",
            auto_create_table=False, overwrite=True,
        )

    assert fake.tables == {"events": original}
    assert original.rows == OLD


def test_overwrite_without_auto_create_missing_table_fails_cleanly(connector, fake):
    del fake.tables["events"]

    with pytest.raises(RuntimeError, match="does not exist"):
        connector.upload_dataframe(NEW, "events", auto_create_table=False, overwrite=True)

    assert fake.tables == {}
    assert fake.dropped == []


# --- auto_create_table=True: swap or rename --------------------------------


def test_overwrite_replaces_existing_rows_and_cleans_up(connector, fake, original):
    connector.upload_dataframe(NEW, "events", overwrite=True)

    after = fake.tables["events"]
    assert after.rows == NEW_ROWS
    # As with 6.0.0's drop-and-recreate, the target is a new table object.
    assert after is not original and after.grants == set()
    assert [table for _, table in fake.dropped] == [original]
    assert _staging_tables(fake) == []


def test_overwrite_of_missing_table_renames_staging_into_place(connector, fake):
    del fake.tables["events"]

    connector.upload_dataframe(NEW, "events", overwrite=True)

    assert list(fake.tables) == ["events"] and fake.tables["events"].rows == NEW_ROWS
    assert any(re.fullmatch(r'ALTER TABLE "events_SU_STAGE_[0-9A-F]{12}" RENAME TO "events"', s)
               for s in fake.statements)


def test_temporary_target_fails_with_original_intact(connector, fake, original):
    original.kind = "TEMPORARY"

    with pytest.raises(RuntimeError, match="temporary"):
        connector.upload_dataframe(NEW, "events", overwrite=True)

    assert fake.tables == {"events": original}
    assert original.rows == OLD


def test_append_path_is_unchanged(connector, fake, original):
    connector.upload_dataframe(NEW, "events")

    assert fake.tables["events"] is original
    assert original.rows == OLD + NEW_ROWS
    assert not any("SWAP" in s or "DROP" in s or "OVERWRITE" in s for s in fake.statements)
    assert [call[:3] for call in fake.write_calls] == [("events", False, False)]


# --- cleanup errors never change the outcome (S3-3) ------------------------


@BOTH_PATHS
def test_cleanup_interface_error_after_success_is_logged_not_raised(
    connector, fake, caplog, auto_create
):
    fake.fail_on.append((r'^DROP TABLE IF EXISTS "events_SU_STAGE_',
                         InterfaceError("Cursor is closed in execute.")))

    with caplog.at_level(logging.ERROR, logger=sc.log.name):
        connector.upload_dataframe(NEW, "events", auto_create_table=auto_create, overwrite=True)

    assert fake.tables["events"].rows == NEW_ROWS
    leftover = _staging_tables(fake)
    assert len(leftover) == 1 and leftover[0] in caplog.text


def test_cleanup_interface_error_after_failed_load_keeps_primary_error(connector, fake, original,
                                                                     caplog):
    fake.fail_write = ProgrammingError("primary COPY failure")
    fake.fail_on.append((r'^DROP TABLE IF EXISTS "events_SU_STAGE_',
                         InterfaceError("Cursor is closed in execute.")))

    with caplog.at_level(logging.ERROR, logger=sc.log.name):
        with pytest.raises(RuntimeError, match="primary COPY failure") as excinfo:
            connector.upload_dataframe(NEW, "events", overwrite=True)

    assert type(excinfo.value.__cause__) is ProgrammingError
    assert fake.tables["events"] is original and original.rows == OLD
    assert _staging_tables(fake)[0] in caplog.text


def test_cleanup_database_error_after_success_is_logged(connector, fake, caplog):
    fake.fail_on.append((r'^DROP TABLE IF EXISTS "events_SU_STAGE_', OperationalError("gone")))

    with caplog.at_level(logging.ERROR, logger=sc.log.name):
        connector.upload_dataframe(NEW, "events", overwrite=True)

    leftover = _staging_tables(fake)
    assert len(leftover) == 1 and fake.tables[leftover[0]].rows == OLD
    assert leftover[0] in caplog.text


# --- documented edge: final statement applied, client sees an error -------


def test_swap_applied_but_client_sees_error_is_documented_behaviour(connector, fake, original):
    fake.raise_after.append((r"SWAP WITH", OperationalError("timeout waiting for the response")))

    with pytest.raises(RuntimeError, match="timeout"):
        connector.upload_dataframe(NEW, "events", overwrite=True)

    # As the docstring says: the target already holds the new rows, and the
    # previous rows were dropped with the staging name.
    assert fake.tables["events"].rows == NEW_ROWS
    assert [table for _, table in fake.dropped] == [original]


# --- staging name: collision, validation, length ---------------------------


@BOTH_PATHS
def test_staging_name_collision_fails_without_touching_the_other_table(
    connector, fake, original, monkeypatch, auto_create
):
    """Kills a mutant that creates the staging table with IF NOT EXISTS."""
    _fixed_uuid(monkeypatch, "abcdef012345" + "0" * 20)
    bystander = Table([{"amount": 99}])
    fake.tables["events_SU_STAGE_ABCDEF012345"] = bystander

    with pytest.raises(RuntimeError, match="already exists"):
        connector.upload_dataframe(NEW, "events", auto_create_table=auto_create, overwrite=True)

    assert fake.tables["events_SU_STAGE_ABCDEF012345"] is bystander
    assert bystander.rows == [{"amount": 99}]
    assert fake.tables["events"] is original and original.rows == OLD
    assert fake.dropped == []


@BOTH_PATHS
def test_invalid_staging_name_fails_before_any_sql(connector, fake, monkeypatch, auto_create):
    """Kills a mutant that drops the staging-name validation."""
    _fixed_uuid(monkeypatch, "ab;--cd01234" + "0" * 20)

    with pytest.raises(RuntimeError, match="staging table name"):
        connector.upload_dataframe(NEW, "events", auto_create_table=auto_create, overwrite=True)

    assert fake.statements == []


@pytest.mark.parametrize("length", [233, 234, 255])
def test_table_name_length_limit(connector, fake, length):
    name = "T" * length
    fake.tables = {name: Table(OLD)}

    if length <= 233:
        connector.upload_dataframe(NEW, name, overwrite=True)
        assert fake.tables[name].rows == NEW_ROWS
    else:
        with pytest.raises(RuntimeError, match="too long"):
            connector.upload_dataframe(NEW, name, overwrite=True)
        assert fake.tables[name].rows == OLD
        assert fake.statements == []


def test_invalid_table_name_fails_before_any_sql(connector, fake):
    with pytest.raises(ValueError):
        connector.upload_dataframe(NEW, "events; DROP TABLE users", overwrite=True)

    assert fake.statements == []


@BOTH_PATHS
def test_all_new_sql_quotes_identifiers(connector, fake, auto_create):
    connector.upload_dataframe(NEW, "events", auto_create_table=auto_create, overwrite=True)

    ddl = [s for s in fake.statements if s.startswith(("CREATE", "ALTER", "DROP", "INSERT"))]
    assert ddl
    for statement in ddl:
        for name in re.findall(r"\b((?:events|amount)\w*)", statement):
            assert f'"{name}"' in statement, statement


def test_create_helper_refuses_destructive_overwrite(connector):
    with pytest.raises(ValueError, match="overwrite"):
        connector._create_table_from_dataframe(NEW, "events", overwrite=True)


# --- column names are quoted like the SDK, not restricted (review S3-1) ----


@pytest.mark.parametrize(
    "column",
    ["First Name", 'say "hi"', "é", 'x") SELECT 1; DROP TABLE "events'],
    ids=["space", "double_quote", "unicode", "injection_attempt"],
)
def test_overwrite_without_auto_create_accepts_any_column_name(connector, fake, column):
    # The fake's write_pandas accepts any label, as snowflake-connector-python
    # 3.1.0 and later do; earlier versions do not escape an embedded double
    # quote in the COPY column list, so 'say "hi"' models 3.1.0 or later.
    original =Table([{column: 1}, {column: 2}], columns=[column], grants={("SELECT", "ANALYST")})
    fake.tables = {"events": original}

    connector.upload_dataframe(
        pd.DataFrame({column: [10, 20, 30]}), "events", auto_create_table=False, overwrite=True
    )

    assert fake.tables["events"] is original
    assert original.rows == [{column: 10}, {column: 20}, {column: 30}]
    quoted = '"' + column.replace('"', '""') + '"'
    insert = next(s for s in fake.statements if s.startswith("INSERT OVERWRITE"))
    assert insert.startswith(f'INSERT OVERWRITE INTO "events" ({quoted}) SELECT {quoted} FROM "')
    assert not any(s.startswith("DROP") and '"events"' in s for s in fake.statements)
    assert _staging_tables(fake) == []


@pytest.mark.parametrize(
    "column", ["amount\n", "", "a\x00b", "a\x7fb"],
    ids=["trailing_newline", "empty", "nul", "delete"],
)
def test_overwrite_without_auto_create_rejects_unusable_column_before_data_sql(
    connector, fake, original, column
):
    with pytest.raises(RuntimeError, match="column name"):
        connector.upload_dataframe(
            pd.DataFrame({column: [1]}), "events", auto_create_table=False, overwrite=True
        )

    assert fake.statements == []
    assert fake.tables == {"events": original} and original.rows == OLD


# --- final or staging statement applied while the client sees an error ----


def test_insert_overwrite_applied_but_client_sees_error_keeps_object(connector, fake, original):
    fake.raise_after.append((r"^INSERT OVERWRITE", OperationalError("timeout waiting for the response")))

    with pytest.raises(RuntimeError, match="timeout"):
        connector.upload_dataframe(NEW, "events", auto_create_table=False, overwrite=True)

    # As documented: the target already holds the new rows; it is still the
    # same object, and the staging table (a copy of the new rows) is dropped.
    assert fake.tables["events"] is original
    assert original.rows == NEW_ROWS
    assert [table.rows for _, table in fake.dropped] == [NEW_ROWS]
    assert _staging_tables(fake) == []


@BOTH_PATHS
def test_staging_create_applied_but_client_sees_error_is_logged_by_name(
    connector, fake, original, caplog, auto_create
):
    fake.raise_after.append((r'^CREATE TABLE "events_SU_STAGE_',
                             OperationalError("timeout waiting for the response")))

    with caplog.at_level(logging.INFO, logger=sc.log.name):
        with pytest.raises(RuntimeError, match="timeout"):
            connector.upload_dataframe(NEW, "events", auto_create_table=auto_create, overwrite=True)

    leftover = _staging_tables(fake)
    assert len(leftover) == 1
    assert fake.tables["events"] is original and original.rows == OLD
    # Not dropped (this call cannot prove it created the table), but named.
    named = [r.getMessage() for r in caplog.records
             if r.levelno >= logging.WARNING and leftover[0] in r.getMessage()]
    assert named, caplog.text


@BOTH_PATHS
def test_staging_table_name_is_logged_before_it_is_created(connector, fake, caplog, auto_create):
    with caplog.at_level(logging.INFO, logger=sc.log.name):
        connector.upload_dataframe(NEW, "events", auto_create_table=auto_create, overwrite=True)

    create = next(s for s in fake.statements if s.startswith('CREATE TABLE "events_SU_STAGE_'))
    staging = re.match(r'CREATE TABLE "([^"]+)"', create)[1]
    assert staging in caplog.text

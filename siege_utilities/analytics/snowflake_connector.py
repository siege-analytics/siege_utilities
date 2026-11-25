"""
Snowflake data warehouse connector for Siege Utilities.

Provides seamless integration with Snowflake for data warehousing and analytics.
"""

import logging
from typing import Optional, Dict, List, Any, Union
from pathlib import Path
import json
import os
import uuid

try:
    import snowflake.connector
    # Only write_pandas is part of pandas_tools. The connector has no
    # read_pandas; importing it raised ImportError and disabled the whole
    # connector on an installed SDK (C13 #1357). Reads use the cursor's
    # fetch_pandas_all / description, see download_dataframe.
    from snowflake.connector.pandas_tools import write_pandas
    from snowflake.connector.errors import (
        DatabaseError as _SnowflakeDatabaseError,
        Error as _SnowflakeError,
        ProgrammingError as _SnowflakeProgrammingError,
        OperationalError as _SnowflakeOperationalError,
    )
    SNOWFLAKE_AVAILABLE = True
    _SF_CONN_ERRORS = (_SnowflakeDatabaseError, _SnowflakeOperationalError)
    _SF_QUERY_ERRORS = (_SnowflakeProgrammingError, _SnowflakeDatabaseError)
    # Base of every SDK error, including InterfaceError ("Cursor is closed").
    _SF_ANY_ERRORS = (_SnowflakeError,)
except ImportError:
    SNOWFLAKE_AVAILABLE = False
    _SF_CONN_ERRORS = (OSError,)
    _SF_QUERY_ERRORS = (ValueError,)
    _SF_ANY_ERRORS = (OSError, ValueError)

# Overwrite stages rows in "<table>_SU_STAGE_<12 hex>" (#1837).
_STAGING_MARKER = "_SU_STAGE_"
_STAGING_NAME_EXTRA = len(_STAGING_MARKER) + 12
# https://docs.snowflake.com/en/sql-reference/identifiers-syntax
_MAX_IDENTIFIER_LENGTH = 255


def _quote_column_identifier(name: Any) -> str:
    """Quote a DataFrame column label as one Snowflake identifier.

    Matches the SDK's ``write_pandas`` quoting: wrap in double quotes and
    double any embedded double quote, so names such as ``First Name`` or
    ``say "hi"`` are kept exactly and cannot end the identifier early.
    ``write_pandas`` escapes embedded double quotes from
    snowflake-connector-python 3.1.0, so only from that version can a label
    containing one be loaded.

    Raises:
        ValueError: The name is empty, longer than 255 characters, or
            contains a control character (including a trailing newline).
    """
    text = str(name)
    if (not text or len(text) > _MAX_IDENTIFIER_LENGTH
            or any(ord(char) < 32 or 127 <= ord(char) <= 159 for char in text)):
        raise ValueError(
            f"Invalid SQL column name {text!r}: empty, longer than "
            f"{_MAX_IDENTIFIER_LENGTH} characters, or contains a control character"
        )
    return '"' + text.replace('"', '""') + '"'

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False

log = logging.getLogger(__name__)


class SnowflakeConnector:
    """Snowflake data warehouse connector with advanced features."""

    def __init__(self,
                 account: Optional[str] = None,
                 user: Optional[str] = None,
                 password: Optional[str] = None,
                 warehouse: Optional[str] = None,
                 database: Optional[str] = None,
                 schema: Optional[str] = None,
                 role: Optional[str] = None,
                 config_file: Optional[Union[str, Path]] = None):
        """
        Initialize Snowflake connector.

        Args:
            account: Snowflake account identifier
            user: Snowflake username
            password: Snowflake password (optional if using config file)
            warehouse: Default warehouse to use
            database: Default database to use
            schema: Default schema to use
            role: Default role to use
            config_file: Path to configuration file
        """
        if not SNOWFLAKE_AVAILABLE:
            raise ImportError("Snowflake connector not available. Install with: pip install snowflake-connector-python")

        self.account = account
        self.user = user
        self.password = password
        self.warehouse = warehouse
        self.database = database
        self.schema = schema
        self.role = role
        self.config_file = config_file

        # Load configuration if provided. account/user may arrive either as
        # explicit arguments or from the config file (C14 #1357): they are
        # optional here precisely so get_snowflake_connector(config_file=...)
        # works. Require them to be resolved from one source or the other.
        if config_file:
            self._load_config(config_file)

        if not self.account or not self.user:
            missing = [n for n in ("account", "user") if not getattr(self, n)]
            raise ValueError(
                f"Snowflake connector requires {missing}; pass as arguments or "
                f"provide them in config_file."
            )

        # Initialize connection
        self.connection = None
        self.cursor = None

        log.info(f"Initialized Snowflake connector for account: {self.account}")

    def _load_config(self, config_file: Union[str, Path]) -> None:
        """Load configuration from file."""
        config_path = Path(config_file)
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")

        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)

            _ALLOWED_CONFIG_KEYS = frozenset({
                "account", "user", "password", "warehouse",
                "database", "schema", "role",
            })
            for key, value in config.items():
                if key in _ALLOWED_CONFIG_KEYS and value is not None:
                    setattr(self, key, value)

        except Exception as e:
            log.error(f"Failed to load configuration: {e}")
            raise

    def connect(self) -> None:
        """Establish connection to Snowflake.

        Raises:
            ConnectionError: If the connection attempt fails.
        """
        connection_params = {
            'account': self.account,
            'user': self.user,
            'warehouse': self.warehouse,
            'database': self.database,
            'schema': self.schema,
            'role': self.role
        }

        if self.password:
            connection_params['password'] = self.password

        connection_params = {k: v for k, v in connection_params.items() if v is not None}

        try:
            self.connection = snowflake.connector.connect(**connection_params)
            self.cursor = self.connection.cursor()
            log.info("Successfully connected to Snowflake")
        except (*_SF_CONN_ERRORS, TypeError) as e:
            raise ConnectionError(f"Failed to connect to Snowflake: {e}") from e

    def disconnect(self) -> None:
        """Close Snowflake connection."""
        try:
            if self.cursor:
                self.cursor.close()
            if self.connection:
                self.connection.close()
            log.info("Disconnected from Snowflake")
        except (*_SF_CONN_ERRORS, AttributeError) as e:
            log.error(f"Error disconnecting from Snowflake: {e}")

    def execute_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> List[tuple]:
        """
        Execute a SQL query.

        Args:
            query: SQL query string
            params: Query parameters (optional)

        Returns:
            Query results as list of tuples

        Raises:
            ConnectionError: If not connected and connection fails.
            RuntimeError: If query execution fails.
        """
        if not self.connection:
            self.connect()

        try:
            if params:
                self.cursor.execute(query, params)
            else:
                self.cursor.execute(query)

            results = self.cursor.fetchall()
            log.info(f"Query executed successfully. Rows returned: {len(results)}")
            return results

        except (*_SF_QUERY_ERRORS, ValueError) as e:
            raise RuntimeError(f"Query execution failed: {e}") from e

    def execute_ddl(self, ddl_statement: str) -> None:
        """
        Execute DDL statements (CREATE, ALTER, DROP, etc.).

        Args:
            ddl_statement: DDL SQL statement

        Raises:
            ConnectionError: If not connected and connection fails.
            RuntimeError: If DDL execution fails.
        """
        if not self.connection:
            self.connect()

        try:
            self.cursor.execute(ddl_statement)
            self.connection.commit()
            log.info("DDL statement executed successfully")
        except (*_SF_QUERY_ERRORS,) as e:
            raise RuntimeError(f"DDL execution failed: {e}") from e

    def upload_dataframe(self,
                        df: 'pd.DataFrame',
                        table_name: str,
                        database: Optional[str] = None,
                        schema: Optional[str] = None,
                        auto_create_table: bool = True,
                        overwrite: bool = False) -> None:
        """
        Upload pandas DataFrame to Snowflake table.

        Args:
            df: Pandas DataFrame to upload
            table_name: Target table name
            database: Target database (uses default if not specified)
            schema: Target schema (uses default if not specified)
            auto_create_table: Whether to automatically create table if it doesn't exist
            overwrite: Replace the table's rows with ``df``. The existing
                table is never dropped or truncated before the new rows are
                loaded (#1837). The rows are first loaded into a new staging
                table named ``<table>_SU_STAGE_<12 hex>``, so ``table_name``
                may be at most 233 characters (Snowflake identifiers are
                limited to 255). Then:

                * ``auto_create_table=False``: the staging table is a
                  session-temporary table created by the connector's
                  ``write_pandas`` load (``table_type="temporary"``) with the
                  column types Snowflake infers from the uploaded data, and
                  the target's rows are replaced in one ``INSERT OVERWRITE
                  INTO <table> (<columns>) SELECT <columns> FROM <staging>``
                  statement, which converts the values to the target's
                  column types. A temporary table "is not visible to other
                  users or sessions" and is purged when the session ends
                  (https://docs.snowflake.com/en/user-guide/tables-temp-transient),
                  so other roles cannot read the staged rows, and Snowflake
                  removes the staging table at session end if cleanup fails.
                  This was not tested against a live Snowflake account. The
                  target table object is kept, with its grants, owner, kind,
                  streams and Time Travel history (inferred from the object
                  being kept). Row access and masking policies on the target
                  are not examined and do not apply to the session-temporary
                  staging table, but no other role can read that table; they
                  apply again once the rows are in the target (#2034). Under
                  autocommit a single statement is its
                  own transaction and is rolled back if it fails
                  (https://docs.snowflake.com/en/sql-reference/transactions);
                  the connector assumes autocommit and does not check it
                  (#2034). ``OVERWRITE`` removes the existing rows before
                  inserting and does not change the table's access
                  privileges; it needs INSERT and DELETE on the target
                  (https://docs.snowflake.com/en/sql-reference/sql/insert),
                  and since it is the only statement that names the target,
                  ownership of the target is not needed. Snowflake documents
                  that creating a temporary table does not require CREATE
                  TABLE on the schema; with SDK 3.0.0 to 3.7.0 the load also
                  renames the temporary table, and renaming a table requires
                  CREATE TABLE on the schema, with no temporary-table
                  exemption stated
                  (https://docs.snowflake.com/en/sql-reference/sql/alter-table;
                  no worse than 6.0.0 on those versions). If a table already has
                  the staging name, the call raises before loading anything.
                  Column labels are quoted as the SDK quotes them, so names
                  such as ``First Name`` work; labels containing a double
                  quote need snowflake-connector-python 3.1.0 or later. An
                  empty label or one with a control character raises before
                  any staging or data SQL.
                  The target must exist; a missing target raises.
                * ``auto_create_table=True``: the staging table is created
                  from ``df``'s columns, then exchanged with an existing
                  target in one ``ALTER TABLE ... SWAP WITH`` statement, or
                  renamed into place when there is no target. Swapping needs
                  OWNERSHIP of the target (as 6.0.0's ``DROP TABLE`` did) and
                  is not allowed with a temporary table, so a temporary
                  target makes the call fail with the original intact
                  (https://docs.snowflake.com/en/sql-reference/sql/alter-table).
                  The staging table on this path is permanent (#2034).
                  The target becomes the new, permanent staging table object:
                  as with 6.0.0's drop-and-recreate, explicit grants, streams
                  and Time Travel history of the previous object do not carry
                  over (https://docs.snowflake.com/en/sql-reference/sql/create-table).

                If any step fails, the target is left as it was and the
                staging table, if this call created it, is dropped. After a
                successful upload the staging table (after a swap it holds
                the previous rows) is dropped; if that cleanup fails, the
                upload still succeeds and the leftover table name is logged
                as an error. The staging name is logged before it is created.
                With ``auto_create_table=True``, a staging ``CREATE`` that the
                server applied while the client saw an error is not dropped,
                because the call cannot prove it created that table, but its
                name is logged as a warning. A process killed mid-upload can
                also leave one behind; find them with
                ``SHOW TABLES LIKE '%_SU_STAGE_%'``. A temporary staging table
                (``auto_create_table=False``) is purged when the session ends.

        Raises:
            ImportError: If pandas is not available.
            ConnectionError: If not connected and connection fails.
            RuntimeError: If the upload fails, wrapping the SDK's
                ``DatabaseError`` family (including ``ProgrammingError`` and
                ``OperationalError``) and ``ValueError``. With
                ``overwrite=True`` the target is unchanged when this is
                raised, except in one case: if the final ``SWAP``,
                ``RENAME`` or ``INSERT OVERWRITE`` was applied by the server
                but the client still saw an error (for example a timeout on
                the response), the target already holds the new rows; after
                a swap, the previous rows are then dropped with the staging
                table.
            snowflake.connector.errors.Error: Other SDK errors, such as
                ``InterfaceError`` for a closed cursor, propagate unwrapped.
        """
        if not PANDAS_AVAILABLE:
            raise ImportError("Pandas not available for DataFrame operations. Install with: pip install pandas")

        if not self.connection:
            self.connect()

        from siege_utilities.core.sql_safety import validate_sql_identifier as validate_identifier
        validate_identifier(table_name, label="table name")
        try:
            if database:
                validate_identifier(database, label="database name")
                self.cursor.execute(f'USE DATABASE "{database}"')
            if schema:
                validate_identifier(schema, label="schema name")
                self.cursor.execute(f'USE SCHEMA "{schema}"')

            if overwrite:
                # Never drop or truncate the caller's table before the new
                # rows are loaded (#1837): load a staging table first.
                if auto_create_table:
                    nrows = self._swap_in_dataframe(df, table_name)
                else:
                    nrows = self._overwrite_rows_from_dataframe(df, table_name)
                log.info(f"Successfully uploaded {nrows} rows to table {table_name}")
                return

            if auto_create_table:
                self._create_table_from_dataframe(df, table_name)

            # write_pandas quotes identifiers by default (case-sensitive, exact
            # DataFrame column case). _create_table_from_dataframe quotes to
            # match, so the created columns line up with what write_pandas
            # targets -- and an existing case-sensitive table (auto_create off)
            # is still addressed correctly.
            success, nchunks, nrows, _ = write_pandas(
                self.connection,
                df,
                table_name,
                auto_create_table=False,
                overwrite=False,
            )

            if not success:
                raise RuntimeError(f"write_pandas reported failure for table {table_name}")

            log.info(f"Successfully uploaded {nrows} rows to table {table_name}")

        except (*_SF_QUERY_ERRORS, ValueError) as e:
            raise RuntimeError(f"DataFrame upload failed: {e}") from e

    def download_dataframe(self,
                          query: str,
                          params: Optional[Dict[str, Any]] = None) -> 'pd.DataFrame':
        """
        Download data from Snowflake as pandas DataFrame.

        Args:
            query: SQL query to execute
            params: Query parameters (optional)

        Returns:
            Pandas DataFrame with query results

        Raises:
            ImportError: If pandas is not available.
            ConnectionError: If not connected and connection fails.
            RuntimeError: If the query fails.
        """
        if not PANDAS_AVAILABLE:
            raise ImportError("Pandas not available for DataFrame operations. Install with: pip install pandas")

        if not self.connection:
            self.connect()

        try:
            if params:
                self.cursor.execute(query, params)
            else:
                self.cursor.execute(query)
            # fetch_pandas_all is the connector's cursor->DataFrame path. It
            # requires the pyarrow extra (snowflake-connector-python[pandas]);
            # without it the call raises, caught below and surfaced as a clear
            # RuntimeError rather than a partial frame.
            df = self.cursor.fetch_pandas_all()
            log.info(f"Successfully downloaded {len(df)} rows as DataFrame")
            return df

        except (*_SF_QUERY_ERRORS, ValueError) as e:
            raise RuntimeError(f"DataFrame download failed: {e}") from e

    def _create_table_from_dataframe(self, df: 'pd.DataFrame', table_name: str,
                                     overwrite: bool = False, *, if_not_exists: bool = True) -> None:
        """Create Snowflake table based on DataFrame structure.

        Never drops an existing table. Replacement goes through
        :meth:`_swap_in_dataframe` or :meth:`_overwrite_rows_from_dataframe`,
        which keep the original until the new rows are in place (#1837).

        Raises:
            ValueError: ``overwrite`` is True, or a table or column name is
                not a safe SQL identifier.
        """
        from siege_utilities.core.sql_safety import validate_sql_identifier as validate_identifier
        if overwrite:
            raise ValueError(
                "_create_table_from_dataframe no longer drops tables; use "
                "upload_dataframe(overwrite=True) to replace a table atomically"
            )
        validate_identifier(table_name, label="table name")
        # Quote identifiers so CREATE matches write_pandas (which quotes by
        # default, preserving the DataFrame's exact column case). Unquoted
        # identifiers are uppercased by Snowflake and would not match the
        # quoted columns write_pandas writes, breaking read-back.
        columns = []
        for col_name, dtype in df.dtypes.items():
            validate_identifier(str(col_name), label="column name", allow_dotted=False)
            snowflake_type = self._map_pandas_to_snowflake_type(dtype)
            columns.append(f'"{col_name}" {snowflake_type}')

        create = 'CREATE TABLE IF NOT EXISTS' if if_not_exists else 'CREATE TABLE'
        create_statement = f'{create} "{table_name}" ({", ".join(columns)})'
        self.cursor.execute(create_statement)
        log.info(f"Created table {table_name} with {len(columns)} columns")

    def _table_exists(self, table_name: str) -> bool:
        """Return whether ``table_name`` (exact, quoted spelling) exists in the
        current database and schema. ``table_name`` must already be validated.

        The probe binds the name with a ``%s`` placeholder, so it relies on the
        connector's default ``pyformat`` parameter style, as ``get_table_info``
        does. A process that sets ``snowflake.connector.paramstyle`` to
        ``qmark`` or ``numeric`` makes this statement fail, before any DDL runs.
        """
        self.cursor.execute(
            """
            SELECT COUNT(*)
            FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_NAME = %s
              AND TABLE_SCHEMA = CURRENT_SCHEMA()
              AND TABLE_CATALOG = CURRENT_DATABASE()
            """,
            (table_name,),
        )
        return self.cursor.fetchone()[0] > 0

    def _drop_staging_table(self, staging_name: str, contents: str) -> None:
        """Drop a staging table this call created; log instead of raising.

        Catches the SDK's ``Error`` base, so ``InterfaceError`` (for example
        "Cursor is closed in execute.") is covered as well as the
        ``DatabaseError`` family. After a successful upload a cleanup failure
        therefore never turns success into an error, and on a failure path it
        never replaces the primary error. The leftover table name is logged.
        """
        try:
            self.cursor.execute(f'DROP TABLE IF EXISTS "{staging_name}"')
        except _SF_ANY_ERRORS as e:
            log.error(
                f"Could not drop staging table {staging_name} holding {contents}; "
                f"drop it manually: {e}"
            )

    def _new_staging_name(self, table_name: str) -> str:
        """Return a unique, validated staging table name for ``table_name``.

        Raises:
            ValueError: The name would exceed Snowflake's 255-character
                identifier limit (``table_name`` longer than 233 characters),
                or is not a safe identifier. Raised before any staging or data
                SQL runs (``USE DATABASE``/``USE SCHEMA`` may already have run).
        """
        from siege_utilities.core.sql_safety import validate_sql_identifier as validate_identifier
        staging_name = f'{table_name}{_STAGING_MARKER}{uuid.uuid4().hex[:12].upper()}'
        if len(staging_name) > _MAX_IDENTIFIER_LENGTH:
            raise ValueError(
                f"Table name is too long to overwrite: the staging table name would "
                f"exceed Snowflake's {_MAX_IDENTIFIER_LENGTH}-character identifier limit; "
                f"table names of up to {_MAX_IDENTIFIER_LENGTH - _STAGING_NAME_EXTRA} "
                f"characters are supported"
            )
        validate_identifier(staging_name, label="staging table name")
        return staging_name

    def _load_staging_table(self, df: 'pd.DataFrame', staging_name: str, table_name: str,
                            table_type: str = "") -> int:
        """Load ``df`` into the staging table and return the row count.

        Passes ``overwrite=True``, as the overwrite path did for the target
        before #1837, so ``write_pandas`` infers the column types from the
        uploaded data and builds the same ``COPY`` (from SDK 3.0.3 binary
        columns are read with ``BINARY_AS_TEXT=FALSE`` and the ``COPY``
        casts to the inferred types). The target is never named in
        this call. What ``write_pandas(staging, auto_create_table=False,
        overwrite=True, table_type=...)`` does depends on the SDK version
        (read from its source, not run against Snowflake):

        * 3.7.1 and later (5.2.0 checked): ``CREATE <table_type> TABLE IF NOT
          EXISTS <staging> (<inferred columns>)``, which creates the table if
          it does not exist and is a no-op on an existing one, then
          ``TRUNCATE TABLE IF EXISTS <staging>``, then ``COPY INTO
          <staging>``.
        * 3.0.0 to 3.7.0: ``CREATE <table_type> TABLE IF NOT EXISTS
          <random> (<inferred columns>)``, ``COPY INTO <random>``, ``DROP
          TABLE IF EXISTS <staging>``, ``ALTER TABLE <random> RENAME TO
          <staging>``; the staging table is then the SDK's table, with
          inferred column types. ``table_type`` is accepted from 3.0.0.

        ``table_type="temporary"`` (``auto_create_table=False`` path) makes
        the table the load creates temporary in both ranges; ``""`` (swap
        path) keeps it permanent.

        Raises:
            RuntimeError: ``write_pandas`` reports failure.
        """
        success, _, nrows, _ = write_pandas(
            self.connection,
            df,
            staging_name,
            auto_create_table=False,
            overwrite=True,
            table_type=table_type,
        )
        if not success:
            raise RuntimeError(f"write_pandas reported failure for table {table_name}")
        return nrows

    def _swap_in_dataframe(self, df: 'pd.DataFrame', table_name: str) -> int:
        """Overwrite with ``auto_create_table=True``: load, then swap or rename.

        Create a new staging table from ``df``'s columns (plain ``CREATE
        TABLE``, so a name collision fails instead of reusing another table),
        load it, then exchange it with an existing target in one ``ALTER
        TABLE ... SWAP WITH`` statement, or rename it into place when there is
        no target. Swap and rename need OWNERSHIP of the tables; swapping with
        a temporary table is not allowed
        (https://docs.snowflake.com/en/sql-reference/sql/alter-table). On any
        failure the staging table is dropped only if this call created it, and
        the error is re-raised. After a successful swap the staging name holds
        the previous rows and is dropped.

        Returns:
            Number of rows loaded.

        Raises:
            ValueError: From :meth:`_new_staging_name` or a column name.
            RuntimeError: ``write_pandas`` reports failure.
            snowflake.connector.errors.Error: A statement fails.
                ``upload_dataframe`` wraps the ``DatabaseError`` family and
                ``ValueError`` in ``RuntimeError``; other SDK errors propagate.
        """
        staging_name = self._new_staging_name(table_name)
        target_exists = self._table_exists(table_name)
        created = False
        try:
            log.info(f"Creating staging table {staging_name} to overwrite {table_name}")
            self._create_table_from_dataframe(df, staging_name, if_not_exists=False)
            created = True
            nrows = self._load_staging_table(df, staging_name, table_name)
            if target_exists:
                self.cursor.execute(f'ALTER TABLE "{staging_name}" SWAP WITH "{table_name}"')
            else:
                self.cursor.execute(f'ALTER TABLE "{staging_name}" RENAME TO "{table_name}"')
        except BaseException as error:
            self._clean_up_failed_staging(staging_name, table_name, created, error)
            raise
        if target_exists:
            self._drop_staging_table(staging_name, f"the previous rows of {table_name}")
        return nrows

    def _clean_up_failed_staging(self, staging_name: str, table_name: str,
                                 created: bool, error: BaseException) -> None:
        """On a failed overwrite, drop the staging table if this call created it.

        If the staging ``CREATE`` itself raised, the server may still have
        applied it (for example when only the response timed out). The table
        is then not dropped, because this call cannot prove it created it, but
        its name is logged so it can be found and dropped. A ``ValueError``
        means validation failed before any ``CREATE`` was sent.
        """
        if created:
            self._drop_staging_table(staging_name, f"unpublished rows for {table_name}")
        elif not isinstance(error, ValueError):
            log.warning(
                f"Creating staging table {staging_name} for {table_name} failed ({error}); "
                f"if the server applied the CREATE anyway, {staging_name} was left behind "
                f"and holds no published data; drop it manually"
            )

    def _overwrite_rows_from_dataframe(self, df: 'pd.DataFrame', table_name: str) -> int:
        """Overwrite with ``auto_create_table=False``: keep the table object.

        Load ``df`` into a new session-temporary staging table that the load
        itself creates (``write_pandas(..., table_type="temporary")``, see
        :meth:`_load_staging_table`), with the column types Snowflake infers
        from the uploaded data. Then replace the target's rows in one
        ``INSERT OVERWRITE INTO <table> (<columns>) SELECT <columns> FROM
        <staging>`` statement, which converts the values to the target's
        column types, and drop the staging table. The connector issues no
        ``CREATE`` of its own here: Snowflake documents ``TEMPORARY`` for the
        column-definition form the SDK sends, not for ``CREATE TABLE ...
        LIKE``. A temporary table "is not visible to other users or
        sessions", is purged when the session ends and does not require
        CREATE TABLE on the schema
        (https://docs.snowflake.com/en/user-guide/tables-temp-transient), so
        schema future grants, the target's grants and its row access policy
        do not open the staged rows to other roles, and a staging table left
        by a failed cleanup disappears at session end. Not tested against a
        live Snowflake account; in particular, that the ``INSERT OVERWRITE``
        conversion from the inferred staging types gives the same values as
        a ``COPY`` straight into the target was not verified for
        ``TIMESTAMP_TZ``/``TIMESTAMP_LTZ`` targets (session time zone),
        ``VARIANT``/``OBJECT``/``ARRAY`` targets, or strings longer than a
        ``VARCHAR(n)`` target column.

        Because the load creates the staging table only if no table of that
        name exists (and SDKs before 3.7.1 drop that name first), the call
        first checks ``INFORMATION_SCHEMA.TABLES`` and raises if a table the
        role can see already has the name, so the load does not truncate,
        drop or read a table that existed before the call (tables the role
        cannot see are not listed there; the name's 12 random hex digits make
        a clash unlikely). Whatever the load leaves under the staging name is
        then this call's and is dropped on success and on failure. The target
        object keeps its grants, owner, kind,
        streams and Time Travel history: ``OVERWRITE`` removes the existing
        rows before inserting and "doesn't change the access control
        privileges granted on the table"; it needs INSERT and DELETE on the
        target (https://docs.snowflake.com/en/sql-reference/sql/insert). Run
        under autocommit, the statement is its own transaction and is rolled
        back if it fails, so the target holds either all old or all new rows
        (https://docs.snowflake.com/en/sql-reference/transactions). The
        connector assumes autocommit and does not check it (#2034). Row
        access and masking policies on the target are not examined and do
        not apply to the session-temporary staging table, but no other role
        can read that table; they apply again once the rows are in the target
        (#2034).

        Returns:
            Number of rows loaded.

        Column labels are quoted the way the SDK's ``write_pandas`` quotes them
        (see :func:`_quote_column_identifier`), so any label the target table
        can hold, such as ``First Name``, is accepted; labels containing a
        double quote need snowflake-connector-python 3.1.0 or later.

        Raises:
            ValueError: From :meth:`_new_staging_name`, or a column label that
                is empty, too long or contains a control character; raised
                before any staging or data SQL runs.
            RuntimeError: ``write_pandas`` reports failure, or a table already
                has the staging name (raised before anything is loaded).
            snowflake.connector.errors.Error: A statement fails, including the
                ``INSERT OVERWRITE`` when the target does not exist or lacks
                one of ``df``'s columns (the staging table is then dropped).
                ``upload_dataframe`` wraps the ``DatabaseError`` family and
                ``ValueError`` in ``RuntimeError``; other SDK errors propagate.
        """
        column_list = ", ".join(_quote_column_identifier(col) for col in df.columns)
        staging_name = self._new_staging_name(table_name)
        if self._table_exists(staging_name):
            raise RuntimeError(
                f"Staging table name {staging_name} is already in use; "
                f"{table_name} was not changed"
            )
        try:
            log.info(f"Creating staging table {staging_name} to overwrite {table_name}")
            nrows = self._load_staging_table(df, staging_name, table_name, table_type="temporary")
            self.cursor.execute(
                f'INSERT OVERWRITE INTO "{table_name}" ({column_list}) '
                f'SELECT {column_list} FROM "{staging_name}"'
            )
        except BaseException as error:
            # The name was free before the load, so whatever is there now was
            # created by this call's load.
            self._clean_up_failed_staging(staging_name, table_name, True, error)
            raise
        self._drop_staging_table(staging_name, f"a copy of the new rows of {table_name}")
        return nrows

    def _map_pandas_to_snowflake_type(self, pandas_dtype) -> str:
        """Map a pandas dtype to the Snowflake column type used by auto-create.

        Uses ``pandas.api.types`` predicates rather than matching the dtype's
        name, so pandas nullable dtypes map like their NumPy counterparts:

        * booleans (``bool``, ``boolean``) -> ``BOOLEAN``;
        * integers, signed or unsigned, including nullable ``Int64`` ->
          ``NUMBER(38,0)``;
        * floats, including nullable ``Float64`` -> ``FLOAT``;
        * timezone-aware datetimes (pandas ``DatetimeTZDtype``) ->
          ``TIMESTAMP_TZ``, naive NumPy ``datetime64`` -> ``TIMESTAMP_NTZ``.
          These are the tested datetime families. Arrow-backed timestamp
          dtypes (for example from ``convert_dtypes(dtype_backend="pyarrow")``)
          are not recognised and fall back to ``VARCHAR(16777216)``, as in
          v4.0.0; no native Arrow loading or round-trip is claimed;
        * categoricals -> the type of their categories (integer categories ->
          ``NUMBER(38,0)``, string categories -> ``VARCHAR``).

        Timedeltas map to ``VARCHAR(16777216)``, as in v4.0.0, because Snowflake
        has no ``INTERVAL`` column type. This method only chooses the column
        type; it does not serialize values. Callers who need durations in a
        usable form should serialize them before upload (for example
        ``.dt.total_seconds()``) or pre-create the table and pass
        ``auto_create_table=False``. Everything else (strings, objects,
        intervals, periods) maps to ``VARCHAR(16777216)``.
        """
        if isinstance(pandas_dtype, pd.CategoricalDtype):
            return self._map_pandas_to_snowflake_type(pandas_dtype.categories.dtype)
        if pd.api.types.is_bool_dtype(pandas_dtype):
            return 'BOOLEAN'
        if pd.api.types.is_integer_dtype(pandas_dtype):
            return 'NUMBER(38,0)'
        if pd.api.types.is_float_dtype(pandas_dtype):
            return 'FLOAT'
        if isinstance(pandas_dtype, pd.DatetimeTZDtype):
            return 'TIMESTAMP_TZ'
        if pd.api.types.is_datetime64_dtype(pandas_dtype):
            return 'TIMESTAMP_NTZ'
        if pd.api.types.is_timedelta64_dtype(pandas_dtype):
            return 'VARCHAR(16777216)'
        return 'VARCHAR(16777216)'

    def get_table_info(self, table_name: str, database: Optional[str] = None, schema: Optional[str] = None) -> Dict[str, Any]:
        """
        Get information about a Snowflake table.

        Args:
            table_name: Name of the table
            database: Database name (uses default if not specified)
            schema: Schema name (uses default if not specified)

        Returns:
            Dictionary with table information

        Raises:
            ConnectionError: If not connected and connection fails.
            RuntimeError: If the query fails.
        """
        if not self.connection:
            self.connect()

        from siege_utilities.core.sql_safety import validate_sql_identifier as validate_identifier
        validate_identifier(table_name, label="table name")
        try:
            if database:
                validate_identifier(database, label="database name")
                self.cursor.execute(f'USE DATABASE "{database}"')
            if schema:
                validate_identifier(schema, label="schema name")
                self.cursor.execute(f'USE SCHEMA "{schema}"')

            # Quote the identifier so a table CREATEd with quotes (case-sensitive,
            # the write_pandas / _create_table_from_dataframe convention) is
            # addressable here. Unquoted DESCRIBE/SELECT would uppercase the name
            # and miss a mixed-case table.
            self.cursor.execute(f'DESCRIBE TABLE "{table_name}"')
            columns = self.cursor.fetchall()

            self.cursor.execute(f'SELECT COUNT(*) FROM "{table_name}"')
            row_count = self.cursor.fetchone()[0]

            self.cursor.execute(
                """
                SELECT BYTES, ROWS
                FROM INFORMATION_SCHEMA.TABLES
                WHERE TABLE_NAME = %s
                  AND TABLE_SCHEMA = CURRENT_SCHEMA()
                  AND TABLE_CATALOG = CURRENT_DATABASE()
                """,
                (table_name,),
            )
            size_info = self.cursor.fetchone()

            table_info = {
                'name': table_name,
                'columns': [{'name': col[0], 'type': col[1], 'nullable': col[2]} for col in columns],
                'row_count': row_count,
                'bytes': size_info[0] if size_info else None,
                'rows': size_info[1] if size_info else None
            }

            return table_info

        except (*_SF_QUERY_ERRORS, ValueError, IndexError) as e:
            raise RuntimeError(f"Failed to get table info for {table_name}: {e}") from e

    def list_tables(self, database: Optional[str] = None, schema: Optional[str] = None) -> List[str]:
        """
        List all tables in a database/schema.

        Args:
            database: Database name (uses default if not specified)
            schema: Schema name (uses default if not specified)

        Returns:
            List of table names

        Raises:
            ConnectionError: If not connected and connection fails.
            RuntimeError: If the query fails.
        """
        if not self.connection:
            self.connect()

        from siege_utilities.core.sql_safety import validate_sql_identifier as validate_identifier
        try:
            if database:
                validate_identifier(database, label="database name")
                self.cursor.execute(f'USE DATABASE "{database}"')
            if schema:
                validate_identifier(schema, label="schema name")
                self.cursor.execute(f'USE SCHEMA "{schema}"')

            self.cursor.execute("SHOW TABLES")
            tables = [row[1] for row in self.cursor.fetchall()]

            return tables

        except (*_SF_QUERY_ERRORS, ValueError, IndexError) as e:
            raise RuntimeError(f"Failed to list tables: {e}") from e

    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()


# Convenience functions
def get_snowflake_connector(config_file: Optional[Union[str, Path]] = None) -> SnowflakeConnector:
    """Get Snowflake connector instance from configuration."""
    if config_file:
        return SnowflakeConnector(config_file=config_file)
    else:
        account = os.getenv('SNOWFLAKE_ACCOUNT')
        user = os.getenv('SNOWFLAKE_USER')
        password = os.getenv('SNOWFLAKE_PASSWORD')

        if not all([account, user, password]):
            raise ValueError("Snowflake configuration not found. Set environment variables or provide config file.")

        return SnowflakeConnector(account=account, user=user, password=password)


def upload_to_snowflake(df: 'pd.DataFrame',
                        table_name: str,
                        config_file: Optional[Union[str, Path]] = None,
                        **kwargs) -> None:
    """Convenience function to upload DataFrame to Snowflake.

    Args:
        df: Pandas DataFrame to upload.
        table_name: Target table name.
        config_file: Path to configuration file (optional).
        **kwargs: Forwarded to SnowflakeConnector.upload_dataframe().
            See that method for accepted parameters.
    """
    with get_snowflake_connector(config_file) as snow:
        snow.upload_dataframe(df, table_name, **kwargs)


def download_from_snowflake(query: str,
                           config_file: Optional[Union[str, Path]] = None,
                           **kwargs) -> 'pd.DataFrame':
    """Convenience function to download DataFrame from Snowflake.

    Args:
        query: SQL query to execute.
        config_file: Path to configuration file (optional).
        **kwargs: Forwarded to SnowflakeConnector.download_dataframe().
            See that method for accepted parameters.
    """
    with get_snowflake_connector(config_file) as snow:
        return snow.download_dataframe(query, **kwargs)


def execute_snowflake_query(query: str,
                           config_file: Optional[Union[str, Path]] = None,
                           **kwargs) -> List[tuple]:
    """Convenience function to execute Snowflake query.

    Args:
        query: SQL query string.
        config_file: Path to configuration file (optional).
        **kwargs: Forwarded to SnowflakeConnector.execute_query().
            See that method for accepted parameters.
    """
    with get_snowflake_connector(config_file) as snow:
        return snow.execute_query(query, **kwargs)


# Global instance for easy access
snowflake_connector = None

__all__ = [
    'SnowflakeConnector',
    'get_snowflake_connector',
    'upload_to_snowflake',
    'download_from_snowflake',
    'execute_snowflake_query',
    'snowflake_connector',
    'SNOWFLAKE_AVAILABLE'
]

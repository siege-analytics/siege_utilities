"""
Snowflake data warehouse connector for Siege Utilities.

Provides seamless integration with Snowflake for data warehousing and analytics.
"""

import logging
from typing import Optional, Dict, List, Any, Union
from pathlib import Path
import json
import os
import re

try:
    import snowflake.connector
    # Only write_pandas is part of pandas_tools. The connector has no
    # read_pandas; importing it raised ImportError and disabled the whole
    # connector on an installed SDK (C13 #1357). Reads use the cursor's
    # fetch_pandas_all / description, see download_dataframe.
    from snowflake.connector.pandas_tools import write_pandas
    from snowflake.connector.errors import (
        DatabaseError as _SnowflakeDatabaseError,
        ProgrammingError as _SnowflakeProgrammingError,
        OperationalError as _SnowflakeOperationalError,
    )
    SNOWFLAKE_AVAILABLE = True
    _SF_CONN_ERRORS = (_SnowflakeDatabaseError, _SnowflakeOperationalError)
    _SF_QUERY_ERRORS = (_SnowflakeProgrammingError, _SnowflakeDatabaseError)
except ImportError:
    SNOWFLAKE_AVAILABLE = False
    _SF_CONN_ERRORS = (OSError,)
    _SF_QUERY_ERRORS = (ValueError,)

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False

log = logging.getLogger(__name__)


_UNQUOTED_IDENTIFIER = re.compile(r"[A-Za-z_][A-Za-z0-9_$]*")
# Reserved and limited keywords also need quoting in table/column contexts.
# https://docs.snowflake.com/en/sql-reference/reserved-keywords
_RESERVED_IDENTIFIERS = frozenset("""
    ACCOUNT ALL ALTER AND ANY AS BETWEEN BY CASE CAST CHECK COLUMN CONNECT
    CONNECTION CONSTRAINT CREATE CROSS CURRENT CURRENT_DATE CURRENT_TIME
    CURRENT_TIMESTAMP CURRENT_USER DATABASE DELETE DISTINCT DROP ELSE EXISTS
    FALSE FOLLOWING FOR FROM FULL GRANT GROUP GSCLUSTER HAVING ILIKE IN INCREMENT
    INNER INSERT INTERSECT INTO IS ISSUE JOIN LATERAL LEFT LIKE LOCALTIME
    LOCALTIMESTAMP MINUS NATURAL NOT NULL OF ON OR ORDER ORGANIZATION QUALIFY
    REGEXP REVOKE RIGHT RLIKE ROW ROWS SAMPLE SCHEMA SELECT SET SOME START TABLE
    TABLESAMPLE THEN TO TRIGGER TRUE TRY_CAST UNION UNIQUE UPDATE USING VALUES
    VIEW WHEN WHENEVER WHERE WINDOW WITH
""".split())


def _format_identifier(name: str, *, label: str = "identifier", for_sql: bool = True) -> str:
    """Resolve one name, returning SQL or its stored spelling for SDK/metadata.

    Plain lower/upper case names fold to uppercase; mixed case, punctuation,
    reserved words and already quoted names retain case. Dots inside a name
    are literal, so callers compose qualified references from separate names.
    Quote escaping keeps special names inside a single SQL identifier. Reject
    empty names, controls and statement/comment delimiters before execution.
    """
    if not isinstance(name, str) or not name:
        raise ValueError(f"SQL {label} must be a non-empty string")
    quoted = re.fullmatch(r'"(?:[^"]|"")+"', name) is not None
    if quoted:
        name = name[1:-1].replace('""', '"')
    if (not name or len(name) > 255 or any(ord(char) < 32 or 127 <= ord(char) <= 159 for char in name)
            or any(token in name for token in (";", "--", "/*", "*/"))):
        raise ValueError(f"Invalid SQL {label}: empty, too long, or contains SQL delimiters/control characters")
    if (not quoted and _UNQUOTED_IDENTIFIER.fullmatch(name)
            and (name == name.lower() or name == name.upper())
            and name.upper() not in _RESERVED_IDENTIFIERS):
        return name.upper()
    if for_sql:
        return '"' + name.replace('"', '""') + '"'
    return name


class SnowflakeConnector:
    """Snowflake connector with case-insensitive plain identifier resolution.

    Generated SQL folds plain lower/upper case identifiers to uppercase.
    Mixed case and special names stay quoted. To address a lowercase object
    created with quotes in v4.0.0, include the delimiters, e.g. '"events"'.
    This also applies to DataFrame columns; uploads do not rename the input.
    Raw SQL passed to execute_query/execute_ddl/download_dataframe is unchanged.
    """

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
        }
        for key in ('warehouse', 'database', 'schema', 'role'):
            value = getattr(self, key)
            if value is not None:
                connection_params[key] = _format_identifier(value, label=key)

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
            overwrite: Whether to overwrite existing table

        Raises:
            ImportError: If pandas is not available.
            ConnectionError: If not connected and connection fails.
            RuntimeError: If the upload fails.
        """
        if not PANDAS_AVAILABLE:
            raise ImportError("Pandas not available for DataFrame operations. Install with: pip install pandas")

        if not self.connection:
            self.connect()

        table_sql = _format_identifier(table_name, label="table name")
        column_sql = [_format_identifier(str(col), label="column name") for col in df.columns]
        column_names = [_format_identifier(str(col), label="column name", for_sql=False) for col in df.columns]
        if len(set(column_names)) != len(column_names):
            raise ValueError("DataFrame columns resolve to duplicate Snowflake identifiers")
        upload_df = df.copy(deep=False)
        upload_df.columns = column_names
        try:
            if database:
                self.cursor.execute(f'USE DATABASE {_format_identifier(database, label="database name")}')
            if schema:
                self.cursor.execute(f'USE SCHEMA {_format_identifier(schema, label="schema name")}')

            if auto_create_table:
                self._create_table_from_dataframe(df, table_name, overwrite)

            # The SDK has one quoting switch for the whole upload. Normalize
            # plain names first so even a mixed-name upload targets the same
            # objects as our DDL. All-plain uploads use unquoted identifiers.
            # The SDK escapes column quotes itself, but not table-name quotes.
            quote_identifiers = any(name.startswith('"') for name in [table_sql, *column_sql])
            upload_table = table_sql[1:-1] if table_sql.startswith('"') else table_sql
            success, nchunks, nrows, _ = write_pandas(
                self.connection,
                upload_df,
                upload_table,
                auto_create_table=False,
                overwrite=overwrite,
                quote_identifiers=quote_identifiers,
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

    def _create_table_from_dataframe(self, df: 'pd.DataFrame', table_name: str, overwrite: bool) -> None:
        """Create Snowflake table based on DataFrame structure."""
        table_sql = _format_identifier(table_name, label="table name")
        columns = []
        for col_name, dtype in df.dtypes.items():
            column_sql = _format_identifier(str(col_name), label="column name")
            snowflake_type = self._map_pandas_to_snowflake_type(dtype)
            columns.append(f'{column_sql} {snowflake_type}')

        if overwrite:
            self.cursor.execute(f'DROP TABLE IF EXISTS {table_sql}')

        create_statement = f'CREATE TABLE IF NOT EXISTS {table_sql} ({", ".join(columns)})'
        self.cursor.execute(create_statement)
        log.info(f"Created table {table_name} with {len(columns)} columns")

    def _map_pandas_to_snowflake_type(self, pandas_dtype) -> str:
        """Map pandas data types to Snowflake data types."""
        dtype_str = str(pandas_dtype)

        if 'int' in dtype_str:
            return 'NUMBER(38,0)'
        elif 'float' in dtype_str:
            return 'FLOAT'
        elif 'bool' in dtype_str:
            return 'BOOLEAN'
        elif 'datetime' in dtype_str:
            return 'TIMESTAMP_NTZ'
        elif 'object' in dtype_str:
            return 'VARCHAR(16777216)'
        else:
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

        table_sql = _format_identifier(table_name, label="table name")
        database = database if database is not None else self.database
        schema = schema if schema is not None else self.schema
        try:
            if database:
                database_sql = _format_identifier(database, label="database name")
                self.cursor.execute(f'USE DATABASE {database_sql}')
            if schema:
                schema_sql = _format_identifier(schema, label="schema name")
                self.cursor.execute(f'USE SCHEMA {schema_sql}')
                table_sql = f'{schema_sql}.{table_sql}'
                if database:
                    table_sql = f'{database_sql}.{table_sql}'

            self.cursor.execute(f'DESCRIBE TABLE {table_sql}')
            columns = self.cursor.fetchall()

            self.cursor.execute(f'SELECT COUNT(*) FROM {table_sql}')
            row_count = self.cursor.fetchone()[0]

            self.cursor.execute(
                """
                SELECT BYTES, ROWS
                FROM INFORMATION_SCHEMA.TABLES
                WHERE TABLE_NAME = %s
                  AND TABLE_SCHEMA = CURRENT_SCHEMA()
                  AND TABLE_CATALOG = CURRENT_DATABASE()
                """,
                (_format_identifier(table_name, label="table name", for_sql=False),),
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

        try:
            if database:
                self.cursor.execute(f'USE DATABASE {_format_identifier(database, label="database name")}')
            if schema:
                self.cursor.execute(f'USE SCHEMA {_format_identifier(schema, label="schema name")}')

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

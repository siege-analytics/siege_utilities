"""
Snowflake data warehouse connector for Siege Utilities.

Provides seamless integration with Snowflake for data warehousing and analytics.
"""

import logging
from typing import Optional, Dict, List, Any, Union
from pathlib import Path
import json
import os

try:
    import snowflake.connector
    from snowflake.connector.pandas_tools import write_pandas, read_pandas
    SNOWFLAKE_AVAILABLE = True
except ImportError:
    SNOWFLAKE_AVAILABLE = False

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False

log = logging.getLogger(__name__)


class SnowflakeConnector:
    """Snowflake data warehouse connector with advanced features."""
    
    def __init__(self, 
                 account: str,
                 user: str,
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
        
        # Load configuration if provided
        if config_file:
            self._load_config(config_file)
        
        # Initialize connection
        self.connection = None
        self.cursor = None
        
        log.info(f"Initialized Snowflake connector for account: {account}")
    
    def _load_config(self, config_file: Union[str, Path]) -> None:
        """Load configuration from file."""
        config_path = Path(config_file)
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
            
            # Update instance variables with config values
            for key, value in config.items():
                if hasattr(self, key) and value is not None:
                    setattr(self, key, value)
                    
        except Exception as e:
            log.error(f"Failed to load configuration: {e}")
            raise
    
    def connect(self) -> bool:
        """Establish connection to Snowflake."""
        try:
            connection_params = {
                'account': self.account,
                'user': self.user,
                'warehouse': self.warehouse,
                'database': self.database,
                'schema': self.schema,
                'role': self.role
            }
            
            # Add password if provided
            if self.password:
                connection_params['password'] = self.password
            
            # Remove None values
            connection_params = {k: v for k, v in connection_params.items() if v is not None}
            
            self.connection = snowflake.connector.connect(**connection_params)
            self.cursor = self.connection.cursor()
            
            log.info("Successfully connected to Snowflake")
            return True
            
        except Exception as e:
            log.error(f"Failed to connect to Snowflake: {e}")
            return False
    
    def disconnect(self) -> None:
        """Close Snowflake connection."""
        try:
            if self.cursor:
                self.cursor.close()
            if self.connection:
                self.connection.close()
            log.info("Disconnected from Snowflake")
        except Exception as e:
            log.error(f"Error disconnecting from Snowflake: {e}")
    
    def execute_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> Optional[List[tuple]]:
        """
        Execute a SQL query.
        
        Args:
            query: SQL query string
            params: Query parameters (optional)
            
        Returns:
            Query results as list of tuples
        """
        if not self.connection:
            if not self.connect():
                return None
        
        try:
            if params:
                self.cursor.execute(query, params)
            else:
                self.cursor.execute(query)
            
            results = self.cursor.fetchall()
            log.info(f"Query executed successfully. Rows returned: {len(results)}")
            return results
            
        except Exception as e:
            log.error(f"Query execution failed: {e}")
            return None
    
    def execute_ddl(self, ddl_statement: str) -> bool:
        """
        Execute DDL statements (CREATE, ALTER, DROP, etc.).
        
        Args:
            ddl_statement: DDL SQL statement
            
        Returns:
            True if successful, False otherwise
        """
        if not self.connection:
            if not self.connect():
                return False
        
        try:
            self.cursor.execute(ddl_statement)
            self.connection.commit()
            log.info("DDL statement executed successfully")
            return True
            
        except Exception as e:
            log.error(f"DDL execution failed: {e}")
            return False
    
    def upload_dataframe(self, 
                        df: 'pd.DataFrame',
                        table_name: str,
                        database: Optional[str] = None,
                        schema: Optional[str] = None,
                        auto_create_table: bool = True,
                        overwrite: bool = False) -> bool:
        """
        Upload pandas DataFrame to Snowflake table.
        
        Args:
            df: Pandas DataFrame to upload
            table_name: Target table name
            database: Target database (uses default if not specified)
            schema: Target schema (uses default if not specified)
            auto_create_table: Whether to automatically create table if it doesn't exist
            overwrite: Whether to overwrite existing table
            
        Returns:
            True if successful, False otherwise
        """
        if not PANDAS_AVAILABLE:
            log.error("Pandas not available for DataFrame operations")
            return False
        
        if not self.connection:
            if not self.connect():
                return False
        
        try:
            # Set database and schema context
            if database:
                self.cursor.execute(f"USE DATABASE {database}")
            if schema:
                self.cursor.execute(f"USE SCHEMA {schema}")
            
            # Create table if needed
            if auto_create_table:
                self._create_table_from_dataframe(df, table_name, overwrite)
            
            # Upload data
            success, nchunks, nrows, _ = write_pandas(
                self.connection,
                df,
                table_name,
                auto_create_table=False,
                overwrite=overwrite
            )
            
            if success:
                log.info(f"Successfully uploaded {nrows} rows to table {table_name}")
                return True
            else:
                log.error(f"Failed to upload data to table {table_name}")
                return False
                
        except Exception as e:
            log.error(f"DataFrame upload failed: {e}")
            return False
    
    def download_dataframe(self, 
                          query: str,
                          params: Optional[Dict[str, Any]] = None) -> Optional['pd.DataFrame']:
        """
        Download data from Snowflake as pandas DataFrame.
        
        Args:
            query: SQL query to execute
            params: Query parameters (optional)
            
        Returns:
            Pandas DataFrame with query results
        """
        if not PANDAS_AVAILABLE:
            log.error("Pandas not available for DataFrame operations")
            return None
        
        if not self.connection:
            if not self.connect():
                return None
        
        try:
            df = read_pandas(self.connection, query, params)
            log.info(f"Successfully downloaded {len(df)} rows as DataFrame")
            return df
            
        except Exception as e:
            log.error(f"DataFrame download failed: {e}")
            return None
    
    def _create_table_from_dataframe(self, df: 'pd.DataFrame', table_name: str, overwrite: bool) -> None:
        """Create Snowflake table based on DataFrame structure."""
        if overwrite:
            self.cursor.execute(f"DROP TABLE IF EXISTS {table_name}")
        
        # Generate CREATE TABLE statement
        columns = []
        for col_name, dtype in df.dtypes.items():
            # Map pandas dtypes to Snowflake types
            snowflake_type = self._map_pandas_to_snowflake_type(dtype)
            columns.append(f"{col_name} {snowflake_type}")
        
        create_statement = f"CREATE TABLE IF NOT EXISTS {table_name} ({', '.join(columns)})"
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
    
    def get_table_info(self, table_name: str, database: Optional[str] = None, schema: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Get information about a Snowflake table.
        
        Args:
            table_name: Name of the table
            database: Database name (uses default if not specified)
            schema: Schema name (uses default if not specified)
            
        Returns:
            Dictionary with table information
        """
        if not self.connection:
            if not self.connect():
                return None
        
        try:
            # Set context
            if database:
                self.cursor.execute(f"USE DATABASE {database}")
            if schema:
                self.cursor.execute(f"USE SCHEMA {schema}")
            
            # Get table description
            self.cursor.execute(f"DESCRIBE TABLE {table_name}")
            columns = self.cursor.fetchall()
            
            # Get row count
            self.cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            row_count = self.cursor.fetchone()[0]
            
            # Get table size
            self.cursor.execute(f"SELECT BYTES, ROWS FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = '{table_name}'")
            size_info = self.cursor.fetchone()
            
            table_info = {
                'name': table_name,
                'columns': [{'name': col[0], 'type': col[1], 'nullable': col[2]} for col in columns],
                'row_count': row_count,
                'bytes': size_info[0] if size_info else None,
                'rows': size_info[1] if size_info else None
            }
            
            return table_info
            
        except Exception as e:
            log.error(f"Failed to get table info: {e}")
            return None
    
    def list_tables(self, database: Optional[str] = None, schema: Optional[str] = None) -> Optional[List[str]]:
        """
        List all tables in a database/schema.
        
        Args:
            database: Database name (uses default if not specified)
            schema: Schema name (uses default if not specified)
            
        Returns:
            List of table names
        """
        if not self.connection:
            if not self.connect():
                return None
        
        try:
            # Set context
            if database:
                self.cursor.execute(f"USE DATABASE {database}")
            if schema:
                self.cursor.execute(f"USE SCHEMA {schema}")
            
            # List tables
            self.cursor.execute("SHOW TABLES")
            tables = [row[1] for row in self.cursor.fetchall()]
            
            return tables
            
        except Exception as e:
            log.error(f"Failed to list tables: {e}")
            return None
    
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
        # Try to load from environment variables
        account = os.getenv('SNOWFLAKE_ACCOUNT')
        user = os.getenv('SNOWFLAKE_USER')
        password = os.getenv('SNOWFLAKE_PASSWORD')
        
        if not all([account, user, password]):
            raise ValueError("Snowflake configuration not found. Set environment variables or provide config file.")
        
        return SnowflakeConnector(account=account, user=user, password=password)


def upload_to_snowflake(df: 'pd.DataFrame', 
                        table_name: str,
                        config_file: Optional[Union[str, Path]] = None,
                        **kwargs) -> bool:
    """Convenience function to upload DataFrame to Snowflake."""
    with get_snowflake_connector(config_file) as snow:
        return snow.upload_dataframe(df, table_name, **kwargs)


def download_from_snowflake(query: str,
                           config_file: Optional[Union[str, Path]] = None,
                           **kwargs) -> Optional['pd.DataFrame']:
    """Convenience function to download DataFrame from Snowflake."""
    with get_snowflake_connector(config_file) as snow:
        return snow.download_dataframe(query, **kwargs)


def execute_snowflake_query(query: str,
                           config_file: Optional[Union[str, Path]] = None,
                           **kwargs) -> Optional[List[tuple]]:
    """Convenience function to execute Snowflake query."""
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

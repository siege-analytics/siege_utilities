"""
Simple database configuration management for siege_utilities.
Handles database connection settings for Spark and other uses.
"""

import json
import os
import pathlib
import logging
import re
from typing import Dict, Any, Optional
from urllib.parse import quote_plus

__all__ = [
    'create_database_config',
    'save_database_config',
    'load_database_config',
    'get_spark_database_options',
    'test_database_connection',
    'list_database_configs',
    'create_spark_session_with_databases',
]

logger = logging.getLogger(__name__)

# Import logging functions from core logging module
try:
    from siege_utilities.core.logging import log_info, log_warning, log_error, log_debug
except ImportError:
    # Fallback if core logging not available yet
    def log_info(message): logger.info(message)
    def log_warning(message): logger.warning(message)
    def log_error(message): logger.error(message)
    def log_debug(message): logger.debug(message)


_ENV_VAR_RE = re.compile(r'^\$\{?([A-Za-z_][A-Za-z0-9_]*)\}?$')


def _resolve_env_var(value: str) -> str:
    """Resolve ``$VAR`` or ``${VAR}`` references from the environment."""
    m = _ENV_VAR_RE.match(value)
    if m:
        env_name = m.group(1)
        resolved = os.environ.get(env_name)
        if resolved is None:
            raise EnvironmentError(
                f"Environment variable {env_name!r} is not set"
            )
        return resolved
    return value


def _is_env_ref(value: str) -> bool:
    """Return True if *value* is an env-var reference like ``$VAR`` or ``${VAR}``."""
    return bool(_ENV_VAR_RE.match(value))


def create_database_config(name: str, connection_type: str, host: str, port: int,
                           database: str, username: str, password: str, **kwargs) -> Dict[str, Any]:
    """
    Create a database connection configuration.

    Args:
        name: Friendly name for the connection
        connection_type: Database type (postgres, mysql, oracle, etc.)
        host: Database host
        port: Database port
        database: Database name
        username: Username
        password: Password
        **kwargs: Additional connection parameters

    Returns:
        Database configuration dictionary

    Example:
        >>> import siege_utilities  # doctest: +SKIP
        >>> db_config = siege_utilities.create_database_config(  # doctest: +SKIP
        ...     "analytics_db",
        ...     "postgres",
        ...     "localhost",
        ...     5432,
        ...     "analytics",
        ...     "user",
        ...     "password"
        ... )
    """

    safe_host = quote_plus(str(host))
    safe_db = quote_plus(str(database))

    jdbc_urls = {
        'postgres': f"jdbc:postgresql://{safe_host}:{port}/{safe_db}",
        'mysql': f"jdbc:mysql://{safe_host}:{port}/{safe_db}",
        'oracle': f"jdbc:oracle:thin:@{safe_host}:{port}:{safe_db}",
        'sqlserver': f"jdbc:sqlserver://{safe_host}:{port};databaseName={safe_db}"
    }

    jdbc_drivers = {
        'postgres': 'org.postgresql.Driver',
        'mysql': 'com.mysql.cj.jdbc.Driver',
        'oracle': 'oracle.jdbc.driver.OracleDriver',
        'sqlserver': 'com.microsoft.sqlserver.jdbc.SQLServerDriver'
    }

    config = {
        'name': name,
        'connection_type': connection_type,
        'host': host,
        'port': port,
        'database': database,
        'username': username,
        'password': password,  # Note: In production, this should be encrypted
        'jdbc_url': jdbc_urls.get(connection_type.lower(), f"jdbc:{connection_type}://{host}:{port}/{database}"),
        'jdbc_driver': jdbc_drivers.get(connection_type.lower(), f"com.{connection_type}.jdbc.Driver"),
        'connection_params': {
            'ssl_mode': kwargs.get('ssl_mode'),
            'timeout': kwargs.get('timeout', 30),
            'pool_size': kwargs.get('pool_size', 5)
        },
        'spark_options': {
            'fetchsize': kwargs.get('fetchsize', '1000'),
            'batchsize': kwargs.get('batchsize', '10000')
        }
    }

    # Add any additional custom parameters
    for key, value in kwargs.items():
        if key not in ['ssl_mode', 'timeout', 'pool_size', 'fetchsize', 'batchsize']:
            config['connection_params'][key] = value

    log_info(f"Created database config: {name} ({connection_type})")
    return config


def save_database_config(config: Dict[str, Any], config_directory: str = "config") -> str:
    """
    Save database configuration to JSON file.

    Args:
        config: Database configuration dictionary
        config_directory: Directory to save config files

    Returns:
        Path to saved config file

    Example:
        >>> db_config = create_database_config("my_db", "postgres", "localhost", 5432, "testdb", "user", "pass")  # doctest: +SKIP
        >>> file_path = siege_utilities.save_database_config(db_config)  # doctest: +SKIP
    """

    config_dir = pathlib.Path(config_directory)
    config_dir.mkdir(parents=True, exist_ok=True)

    db_name = config['name']
    if not db_name or '/' in db_name or '\\' in db_name or '..' in db_name:
        raise ValueError(f"Invalid database name for filename: {db_name!r}")
    config_file = config_dir / f"database_{db_name}.json"

    safe_config = dict(config)
    password = safe_config.get('password', '')
    if password and not _is_env_ref(str(password)):
        env_name = f"DB_{db_name.upper()}_PASSWORD"
        log_warning(
            f"Plaintext password replaced with env var reference ${{{env_name}}}. "
            f"Set this variable in your environment before loading the config."
        )
        safe_config['password'] = f"${{{env_name}}}"

    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump(safe_config, f, indent=2)

    log_info(f"Saved database config to: {config_file}")
    return str(config_file)


def load_database_config(db_name: str, config_directory: str = "config") -> Dict[str, Any]:
    """
    Load database configuration from JSON file.

    Args:
        db_name: Database configuration name to load
        config_directory: Directory containing config files

    Returns:
        Database configuration dictionary.

    Raises:
        FileNotFoundError: If the database config file does not exist.
        json.JSONDecodeError: If the file contains invalid JSON.
        OSError: If the file cannot be read.

    Example:
        >>> db_config = siege_utilities.load_database_config("analytics_db")  # doctest: +SKIP
        >>> print(f"Database: {db_config['database']}")  # doctest: +SKIP
    """

    config_file = pathlib.Path(config_directory) / f"database_{db_name}.json"

    if not config_file.exists():
        raise FileNotFoundError(f"Database config not found: {config_file}")

    with open(config_file, 'r', encoding='utf-8') as f:
        config = json.load(f)

    for key in ('username', 'password'):
        val = config.get(key, '')
        if isinstance(val, str) and _is_env_ref(val):
            config[key] = _resolve_env_var(val)

    log_info(f"Loaded database config: {db_name}")
    return config


def get_spark_database_options(db_name: str, config_directory: str = "config") -> Dict[str, str]:
    """
    Get Spark-compatible options for database connection.

    Args:
        db_name: Database configuration name
        config_directory: Directory containing config files

    Returns:
        Dictionary of Spark options.

    Raises:
        FileNotFoundError: If the database config does not exist.
        KeyError: If the config is missing required keys.

    Example:
        >>> spark_options = siege_utilities.get_spark_database_options("analytics_db")  # doctest: +SKIP
        >>> df = spark.read.format("jdbc").options(**spark_options).option("dbtable", "users").load()  # doctest: +SKIP
    """

    config = load_database_config(db_name, config_directory)

    required_keys = ('jdbc_url', 'jdbc_driver', 'username', 'password')
    missing = [k for k in required_keys if k not in config]
    if missing:
        raise KeyError(
            f"Database config {db_name!r} missing required keys: {missing}"
        )

    spark_options = {
        'url': config['jdbc_url'],
        'driver': config['jdbc_driver'],
        'user': config['username'],
        'password': config['password']
    }

    spark_options.update(config.get('spark_options', {}))

    log_info(f"Retrieved Spark options for database: {db_name}")
    return spark_options


def test_database_connection(db_name: str, config_directory: str = "config") -> bool:
    """
    Test database connection (basic connectivity check).

    Args:
        db_name: Database configuration name
        config_directory: Directory containing config files

    Returns:
        True if connection successful, False otherwise

    Example:
        >>> if siege_utilities.test_database_connection("analytics_db"):  # doctest: +SKIP
        ...     print("Database connection successful!")
    """

    config = load_database_config(db_name, config_directory)

    try:
        # Try basic connection test with SQLAlchemy if available
        try:
            from sqlalchemy import create_engine, text

            connection_type = config['connection_type'].lower()
            host = config['host']
            port = config['port']
            database = config['database']
            username = quote_plus(str(config['username']))
            password = quote_plus(str(config['password']))

            from urllib.parse import quote_plus

            if connection_type == 'postgres':
                conn_string = f"postgresql://{quote_plus(username)}:{quote_plus(password)}@{host}:{port}/{database}"
            elif connection_type == 'mysql':
                conn_string = f"mysql+pymysql://{quote_plus(username)}:{quote_plus(password)}@{host}:{port}/{database}"
            else:
                log_warning(f"Connection test not implemented for {connection_type}")
                return False

            engine = create_engine(conn_string)
            with engine.connect() as conn:
                # Simple test query
                result = conn.execute(text("SELECT 1"))
                result.fetchone()

            log_info(f"Database connection test successful: {db_name}")
            return True

        except ImportError:
            log_warning("SQLAlchemy not available for connection testing")
            log_info("Install with: pip install sqlalchemy")
            return False

    except (OSError, KeyError, TypeError) as e:
        log_error(f"Database connection test failed for {db_name}: {e}")
        return False


def list_database_configs(config_directory: str = "config") -> list:
    """
    List all available database configurations.

    Args:
        config_directory: Directory containing config files

    Returns:
        List of dictionaries with database info

    Example:
        >>> databases = siege_utilities.list_database_configs()  # doctest: +SKIP
        >>> for db in databases:  # doctest: +SKIP
        ...     print(f"{db['name']}: {db['connection_type']}")
    """

    config_dir = pathlib.Path(config_directory)

    if not config_dir.exists():
        log_warning("Config directory does not exist")
        return []

    databases = []

    for config_file in config_dir.glob("database_*.json"):
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)

            databases.append({
                'name': config['name'],
                'connection_type': config['connection_type'],
                'host': config['host'],
                'database': config['database'],
                'config_file': str(config_file)
            })

        except (OSError, json.JSONDecodeError, KeyError) as e:
            log_error(f"Error reading database config {config_file}: {e}")

    log_info(f"Found {len(databases)} database configurations")
    return databases


def create_spark_session_with_databases(app_name: str = "SiegeAnalytics",
                                        database_names: list = None,
                                        config_directory: str = "config"):
    """
    Create Spark session configured for database access.

    Args:
        app_name: Spark application name
        database_names: List of database config names to prepare drivers for
        config_directory: Directory containing config files

    Returns:
        Configured Spark session or None if PySpark not available

    Raises:
        ValueError: If a database config declares a ``connection_type`` for which
            no JDBC driver is registered. Supported types: ``postgres``, ``mysql``,
            ``oracle``. The error names the offending type so callers can either
            add a supported config or extend the dispatch.

    Example:
        >>> spark = siege_utilities.create_spark_session_with_databases(  # doctest: +SKIP
        ...     "Analytics App",
        ...     ["analytics_db", "staging_db"]
        ... )
    """

    try:
        from pyspark.sql import SparkSession
    except ImportError as e:
        raise ImportError(
            "PySpark is required for create_spark_session_with_databases. "
            "Install with: pip install pyspark"
        ) from e

    builder = SparkSession.builder.appName(app_name)

    packages = []
    supported_connection_types = ('postgres', 'mysql', 'oracle')

    if database_names:
        for db_name in database_names:
            config = load_database_config(db_name, config_directory)
            if 'connection_type' not in config:
                raise ValueError(
                    f"Database config {db_name!r} missing 'connection_type' key"
                )
            connection_type = config['connection_type'].lower()

            if connection_type == 'postgres':
                packages.append("org.postgresql:postgresql:42.3.1")
            elif connection_type == 'mysql':
                packages.append("mysql:mysql-connector-java:8.0.28")
            elif connection_type == 'oracle':
                packages.append("com.oracle.database.jdbc:ojdbc8:21.1.0.0")
            else:
                raise ValueError(
                    f"Unsupported connection_type {connection_type!r} for "
                    f"database {db_name!r}. Supported types: "
                    f"{', '.join(supported_connection_types)}. "
                    f"Previously this case silently loaded the PostgreSQL "
                    f"JDBC driver, which produced misleading connection "
                    f"errors at runtime."
                )

    # Add common packages if none specified
    if not packages:
        packages = ["org.postgresql:postgresql:42.3.1"]  # Default to PostgreSQL

    if packages:
        builder = builder.config("spark.jars.packages", ",".join(packages))

    # Add some basic optimizations
    builder = builder.config("spark.sql.adaptive.enabled", "true")
    builder = builder.config("spark.sql.adaptive.coalescePartitions.enabled", "true")

    spark = builder.getOrCreate()
    log_info(f"Created Spark session: {app_name}")

    return spark
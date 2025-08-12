"""
Simple database configuration management for siege_utilities.
Handles database connection settings for Spark and other uses.
"""

import json
import pathlib
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


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
        >>> import siege_utilities
        >>> db_config = siege_utilities.create_database_config(
        ...     "analytics_db",
        ...     "postgres",
        ...     "localhost",
        ...     5432,
        ...     "analytics",
        ...     "user",
        ...     "password"
        ... )
    """

    # Generate JDBC URL based on connection type
    jdbc_urls = {
        'postgres': f"jdbc:postgresql://{host}:{port}/{database}",
        'mysql': f"jdbc:mysql://{host}:{port}/{database}",
        'oracle': f"jdbc:oracle:thin:@{host}:{port}:{database}",
        'sqlserver': f"jdbc:sqlserver://{host}:{port};databaseName={database}"
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

    print(f"Created database config: {name} ({connection_type})")
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
        >>> db_config = create_database_config("my_db", "postgres", "localhost", 5432, "testdb", "user", "pass")
        >>> file_path = siege_utilities.save_database_config(db_config)
    """

    config_dir = pathlib.Path(config_directory)
    config_dir.mkdir(parents=True, exist_ok=True)

    db_name = config['name']
    config_file = config_dir / f"database_{db_name}.json"

    # Warning about password storage
    print(f"Saving database config with password in plain text to {config_file}")
    print("In production, consider using environment variables or encryption")

    with open(config_file, 'w') as f:
        json.dump(config, f, indent=2)

    print(f"Saved database config to: {config_file}")
    return str(config_file)


def load_database_config(db_name: str, config_directory: str = "config") -> Optional[Dict[str, Any]]:
    """
    Load database configuration from JSON file.

    Args:
        db_name: Database configuration name to load
        config_directory: Directory containing config files

    Returns:
        Database configuration dictionary or None if not found

    Example:
        >>> db_config = siege_utilities.load_database_config("analytics_db")
        >>> if db_config:
        ...     print(f"Database: {db_config['database']}")
    """

    config_file = pathlib.Path(config_directory) / f"database_{db_name}.json"

    if not config_file.exists():
        print(f"Database config not found: {config_file}")
        return None

    try:
        with open(config_file, 'r') as f:
            config = json.load(f)

        print(f"Loaded database config: {db_name}")
        return config

    except Exception as e:
        print(f"Error loading database config {config_file}: {e}")
        return None


def get_spark_database_options(db_name: str, config_directory: str = "config") -> Optional[Dict[str, str]]:
    """
    Get Spark-compatible options for database connection.

    Args:
        db_name: Database configuration name
        config_directory: Directory containing config files

    Returns:
        Dictionary of Spark options or None if config not found

    Example:
        >>> spark_options = siege_utilities.get_spark_database_options("analytics_db")
        >>> if spark_options:
        ...     df = spark.read.format("jdbc").options(**spark_options).option("dbtable", "users").load()
    """

    config = load_database_config(db_name, config_directory)

    if config is None:
        return None

    spark_options = {
        'url': config['jdbc_url'],
        'driver': config['jdbc_driver'],
        'user': config['username'],
        'password': config['password']
    }

    # Add Spark-specific options
    spark_options.update(config.get('spark_options', {}))

    print(f"Retrieved Spark options for database: {db_name}")
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
        >>> if siege_utilities.test_database_connection("analytics_db"):
        ...     print("Database connection successful!")
    """

    config = load_database_config(db_name, config_directory)

    if config is None:
        return False

    try:
        # Try basic connection test with SQLAlchemy if available
        try:
            from sqlalchemy import create_engine

            connection_type = config['connection_type'].lower()
            host = config['host']
            port = config['port']
            database = config['database']
            username = config['username']
            password = config['password']

            if connection_type == 'postgres':
                conn_string = f"postgresql://{username}:{password}@{host}:{port}/{database}"
            elif connection_type == 'mysql':
                conn_string = f"mysql+pymysql://{username}:{password}@{host}:{port}/{database}"
            else:
                print(f"Connection test not implemented for {connection_type}")
                return False

            engine = create_engine(conn_string)
            with engine.connect() as conn:
                # Simple test query
                result = conn.execute("SELECT 1")
                result.fetchone()

            print(f"Database connection test successful: {db_name}")
            return True

        except ImportError:
            print("SQLAlchemy not available for connection testing")
            print("Install with: pip install sqlalchemy")
            return False

    except Exception as e:
        print(f"Database connection test failed for {db_name}: {e}")
        return False


def list_database_configs(config_directory: str = "config") -> list:
    """
    List all available database configurations.

    Args:
        config_directory: Directory containing config files

    Returns:
        List of dictionaries with database info

    Example:
        >>> databases = siege_utilities.list_database_configs()
        >>> for db in databases:
        ...     print(f"{db['name']}: {db['connection_type']}")
    """

    config_dir = pathlib.Path(config_directory)

    if not config_dir.exists():
        print("Config directory does not exist")
        return []

    databases = []

    for config_file in config_dir.glob("database_*.json"):
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)

            databases.append({
                'name': config['name'],
                'connection_type': config['connection_type'],
                'host': config['host'],
                'database': config['database'],
                'config_file': str(config_file)
            })

        except Exception as e:
            print(f"Error reading database config {config_file}: {e}")

    print(f"Found {len(databases)} database configurations")
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

    Example:
        >>> spark = siege_utilities.create_spark_session_with_databases(
        ...     "Analytics App",
        ...     ["analytics_db", "staging_db"]
        ... )
    """

    try:
        from pyspark.sql import SparkSession
    except ImportError:
        print("PySpark not available. Install with: pip install pyspark")
        return None

    # Build Spark session
    builder = SparkSession.builder.appName(app_name)

    # Add database drivers based on configured databases
    packages = []

    if database_names:
        for db_name in database_names:
            config = load_database_config(db_name, config_directory)
            if config:
                connection_type = config['connection_type'].lower()

                if connection_type == 'postgres':
                    packages.append("org.postgresql:postgresql:42.3.1")
                elif connection_type == 'mysql':
                    packages.append("mysql:mysql-connector-java:8.0.28")
                elif connection_type == 'oracle':
                    packages.append("com.oracle.database.jdbc:ojdbc8:21.1.0.0")

    # Add common packages if none specified
    if not packages:
        packages = ["org.postgresql:postgresql:42.3.1"]  # Default to PostgreSQL

    if packages:
        builder = builder.config("spark.jars.packages", ",".join(packages))

    # Add some basic optimizations
    builder = builder.config("spark.sql.adaptive.enabled", "true")
    builder = builder.config("spark.sql.adaptive.coalescePartitions.enabled", "true")

    spark = builder.getOrCreate()
    print(f"Created Spark session: {app_name}")

    return spark
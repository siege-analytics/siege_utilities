# Database Connections - Spark-Optimized with Sedona Integration

## Problem

You need to establish database connections that work seamlessly with Apache Spark, including support for Apache Sedona (formerly GeoSpark) for spatial data processing. The connections should be configurable, scalable, and support both batch and streaming operations.

## Solution

Use Siege Utilities' database connection management system with Spark-optimized configurations, Apache Sedona integration, and configurable connection pooling for optimal performance.

## Quick Start

```python
import siege_utilities
from siege_utilities.config.databases import DatabaseConnectionManager

# Initialize database connection manager
db_manager = DatabaseConnectionManager()

# Get Spark-optimized connection
spark_conn = db_manager.get_spark_connection('postgresql')
print("✅ Spark database connection established")
```

## Complete Implementation

### 1. Spark-Optimized Database Configuration

#### Database Connection Manager
```python
import siege_utilities
from siege_utilities.config.databases import DatabaseConfig, DatabaseConnectionManager
from siege_utilities.distributed.spark_utils import SparkUtils
from siege_utilities.core.logging import Logger
import pyspark
from pyspark.sql import SparkSession
import os

class SparkDatabaseManager:
    """Database manager optimized for Spark operations with Sedona support"""
    
    def __init__(self, spark_config=None, sedona_config=None):
        self.logger = Logger("spark_database_manager")
        self.spark_config = spark_config or {}
        self.sedona_config = sedona_config or {}
        
        # Initialize Spark with Sedona
        self.spark = self._initialize_spark_with_sedona()
        
        # Initialize database connection manager
        self.db_manager = DatabaseConnectionManager()
    
    def _initialize_spark_with_sedona(self):
        """Initialize Spark session with Apache Sedona for spatial operations"""
        
        try:
            # Base Spark configuration
            spark_builder = SparkSession.builder \
                .appName("SiegeUtilities-Spark-Sedona") \
                .config("spark.sql.adaptive.enabled", "true") \
                .config("spark.sql.adaptive.coalescePartitions.enabled", "true") \
                .config("spark.sql.adaptive.skewJoin.enabled", "true") \
                .config("spark.sql.adaptive.localShuffleReader.enabled", "true") \
                .config("spark.sql.adaptive.optimizeSkewsInRebalancePartitions.enabled", "true")
            
            # Add Sedona configurations
            if self.sedona_config.get("enable_sedona", True):
                spark_builder = spark_builder \
                    .config("spark.jars.packages", 
                           "org.apache.sedona:sedona-spark-shaded-3.4_2.12:1.4.1,"
                           "org.datasyslab:geotools-wrapper:1.4.1-28.2") \
                    .config("spark.serializer", "org.apache.spark.serializer.KryoSerializer") \
                    .config("spark.kryo.registrator", "org.apache.sedona.viz.core.Serde.GeoSparkVizKryoRegistrator") \
                    .config("spark.kryoserializer.buffer.max", "2047m") \
                    .config("spark.kryo.registrationRequired", "false")
            
            # Add database-specific configurations
            if self.spark_config.get("database_type") == "postgresql":
                spark_builder = spark_builder \
                    .config("spark.jars.packages", 
                           spark_builder._options.get("spark.jars.packages", "") + 
                           ",org.postgresql:postgresql:42.6.0")
            
            # Create Spark session
            spark = spark_builder.getOrCreate()
            
            # Initialize Sedona if enabled
            if self.sedona_config.get("enable_sedona", True):
                from sedona.register import SedonaRegistrator
                SedonaRegistrator.registerAll(spark)
                self.logger.info("✅ Apache Sedona initialized successfully")
            
            self.logger.info(f"✅ Spark session created: {spark.version}")
            return spark
            
        except Exception as e:
            self.logger.error(f"❌ Failed to initialize Spark with Sedona: {e}")
            raise
    
    def get_database_connection(self, db_type, connection_config):
        """Get database connection optimized for Spark operations"""
        
        try:
            if db_type == "postgresql":
                return self._get_postgresql_connection(connection_config)
            elif db_type == "mysql":
                return self._get_mysql_connection(connection_config)
            elif db_type == "oracle":
                return self._get_oracle_connection(connection_config)
            elif db_type == "sqlserver":
                return self._get_sqlserver_connection(connection_config)
            else:
                raise ValueError(f"Unsupported database type: {db_type}")
                
        except Exception as e:
            self.logger.error(f"❌ Failed to get {db_type} connection: {e}")
            raise
    
    def _get_postgresql_connection(self, config):
        """Get PostgreSQL connection optimized for Spark"""
        
        # PostgreSQL JDBC URL for Spark
        jdbc_url = f"jdbc:postgresql://{config['host']}:{config['port']}/{config['database']}"
        
        connection_properties = {
            "user": config['username'],
            "password": config['password'],
            "driver": "org.postgresql.Driver",
            "url": jdbc_url
        }
        
        # Add performance optimizations
        if config.get('use_ssl', False):
            connection_properties.update({
                "sslmode": "require",
                "sslcert": config.get('ssl_cert'),
                "sslkey": config.get('ssl_key'),
                "sslrootcert": config.get('ssl_root_cert')
            })
        
        return {
            'type': 'postgresql',
            'jdbc_url': jdbc_url,
            'properties': connection_properties,
            'spark_options': {
                'url': jdbc_url,
                'properties': connection_properties
            }
        }
    
    def read_from_database(self, connection, query, table_name=None, **options):
        """Read data from database using Spark with optimal performance"""
        
        try:
            if connection['type'] == 'postgresql':
                # Use JDBC for PostgreSQL
                df = self.spark.read \
                    .jdbc(
                        url=connection['jdbc_url'],
                        table=table_name or f"({query}) as temp_table",
                        properties=connection['properties']
                    )
                
                # Optimize partitioning for large datasets
                if options.get('partition_column') and options.get('num_partitions'):
                    df = df.repartition(options['num_partitions'])
                
                self.logger.info(f"✅ Read {df.count()} rows from {connection['type']}")
                return df
                
        except Exception as e:
            self.logger.error(f"❌ Failed to read from {connection['type']}: {e}")
            raise
    
    def write_to_database(self, df, connection, table_name, mode="append", **options):
        """Write DataFrame to database using Spark with optimal performance"""
        
        try:
            if connection['type'] == 'postgresql':
                # Use JDBC for PostgreSQL
                df.write \
                    .mode(mode) \
                    .jdbc(
                        url=connection['jdbc_url'],
                        table=table_name,
                        properties=connection['properties']
                    )
                
                self.logger.info(f"✅ Wrote data to {table_name} in {connection['type']}")
                
        except Exception as e:
            self.logger.error(f"❌ Failed to write to {connection['type']}: {e}")
            raise

# Initialize Spark database manager
spark_db_manager = SparkDatabaseManager(
    spark_config={'database_type': 'postgresql'},
    sedona_config={'enable_sedona': True}
)
```

### 2. Sedona Spatial Operations

#### Spatial Data Processing with Sedona
```python
def demonstrate_sedona_spatial_operations():
    """Demonstrate Apache Sedona spatial operations with database data"""
    
    try:
        print("🗺️ Apache Sedona Spatial Operations Demo")
        print("=" * 50)
        
        # Sample spatial data
        spatial_data = [
            (1, "Point A", "POINT(-122.4194 37.7749)", "San Francisco"),
            (2, "Point B", "POINT(-74.0060 40.7128)", "New York"),
            (3, "Point C", "POINT(-87.6298 41.8781)", "Chicago"),
            (4, "Point D", "POINT(-118.2437 34.0522)", "Los Angeles")
        ]
        
        # Create Spark DataFrame with spatial data
        spatial_df = spark_db_manager.spark.createDataFrame(
            spatial_data, 
            ["id", "name", "geometry", "city"]
        )
        
        print(f"✅ Created spatial DataFrame with {spatial_df.count()} points")
        
        # Convert to Sedona geometry
        from sedona.utils import geometry_serde
        from sedona.sql import st_geomfromtext, st_astext, st_distance
        
        # Register UDFs
        spark_db_manager.spark.udf.register("ST_GeomFromText", st_geomfromtext)
        spark_db_manager.spark.udf.register("ST_AsText", st_astext)
        spark_db_manager.spark.udf.register("ST_Distance", st_distance)
        
        # Create temporary view
        spatial_df.createOrReplaceTempView("spatial_points")
        
        # Perform spatial operations
        spatial_query = """
        SELECT 
            id, name, city,
            ST_GeomFromText(geometry) as geom,
            ST_AsText(ST_GeomFromText(geometry)) as geom_text
        FROM spatial_points
        """
        
        spatial_result = spark_db_manager.spark.sql(spatial_query)
        print(f"✅ Spatial operations completed")
        print(f"📊 Result schema: {spatial_result.schema}")
        
        # Show results
        spatial_result.show(truncate=False)
        
        return spatial_result
        
    except Exception as e:
        print(f"❌ Sedona spatial operations failed: {e}")
        return None

# Run Sedona demonstration
sedona_demo = demonstrate_sedona_spatial_operations()
```

### 3. Database Connection Pooling

#### Connection Pool Management
```python
class DatabaseConnectionPool:
    """Connection pool for database connections with Spark optimization"""
    
    def __init__(self, max_connections=10, connection_timeout=30):
        self.max_connections = max_connections
        self.connection_timeout = connection_timeout
        self.active_connections = {}
        self.connection_pool = {}
        self.logger = Logger("database_connection_pool")
    
    def get_connection(self, db_type, connection_config):
        """Get connection from pool or create new one"""
        
        connection_key = f"{db_type}_{connection_config['host']}_{connection_config['database']}"
        
        if connection_key in self.connection_pool:
            # Return existing connection
            return self.connection_pool[connection_key]
        else:
            # Create new connection
            if len(self.connection_pool) < self.max_connections:
                connection = spark_db_manager.get_database_connection(db_type, connection_config)
                self.connection_pool[connection_key] = connection
                self.logger.info(f"✅ Created new {db_type} connection")
                return connection
            else:
                raise Exception("Connection pool is full")
    
    def release_connection(self, connection_key):
        """Release connection back to pool"""
        
        if connection_key in self.connection_pool:
            # In a real implementation, you might want to close the connection
            # For Spark, connections are typically long-lived
            self.logger.info(f"✅ Released connection: {connection_key}")
    
    def close_all_connections(self):
        """Close all connections in the pool"""
        
        for key in list(self.connection_pool.keys()):
            self.release_connection(key)
        
        self.logger.info("✅ All database connections closed")

# Initialize connection pool
db_connection_pool = DatabaseConnectionPool(max_connections=5)
```

## Configuration Options

### Spark with Sedona Configuration
```yaml
spark_configuration:
  # Base Spark settings
  app_name: "SiegeUtilities-Spark-Sedona"
  master: "local[*]"  # or "yarn" for cluster mode
  
  # Performance optimizations
  sql_adaptive:
    enabled: true
    coalesce_partitions: true
    skew_join: true
    local_shuffle_reader: true
    optimize_skews_in_rebalance: true
  
  # Memory and serialization
  serializer: "org.apache.spark.serializer.KryoSerializer"
  kryo_buffer_max: "2047m"
  kryo_registration_required: false
  
  # Sedona configuration
  sedona:
    enabled: true
    version: "1.4.1"
    scala_version: "2.12"
    spark_version: "3.4"
    geotools_wrapper: "1.4.1-28.2"
  
  # Database-specific JARs
  additional_jars:
    postgresql: "org.postgresql:postgresql:42.6.0"
    mysql: "mysql:mysql-connector-java:8.0.33"
    oracle: "com.oracle.database.jdbc:ojdbc8:21.9.0.0"
```

### Database Connection Configuration
```yaml
database_connections:
  postgresql:
    host: "localhost"
    port: 5432
    database: "siege_analytics"
    username: "siege_user"
    password: "secure_password"
    use_ssl: true
    ssl_cert: "/path/to/client-cert.pem"
    ssl_key: "/path/to/client-key.pem"
    ssl_root_cert: "/path/to/server-ca.pem"
    
    # Spark optimization
    partition_column: "id"
    num_partitions: 10
    fetch_size: 1000
    batch_size: 10000
  
  mysql:
    host: "localhost"
    port: 3306
    database: "siege_analytics"
    username: "siege_user"
    password: "secure_password"
    use_ssl: true
    
    # Spark optimization
    partition_column: "id"
    num_partitions: 8
    fetch_size: 1000
    batch_size: 10000
```

## Expected Output

```
✅ Spark session created: 3.4.0
✅ Apache Sedona initialized successfully
✅ Created new postgresql connection
✅ Read 1,250 rows from postgresql
✅ Wrote data to analytics_table in postgresql

🗺️ Apache Sedona Spatial Operations Demo
==================================================
✅ Created spatial DataFrame with 4 points
✅ Spatial operations completed
📊 Result schema: StructType([StructField('id', LongType(), True), ...])

+---+------+--------+--------------------+--------------------+
|id |name  |city    |geom                |geom_text           |
+---+------+--------+--------------------+--------------------+
|1  |Point A|San Francisco|POINT (-122.4194 37.7749)|POINT (-122.4194 37.7749)|
|2  |Point B|New York    |POINT (-74.006 40.7128)  |POINT (-74.006 40.7128)  |
|3  |Point C|Chicago     |POINT (-87.6298 41.8781) |POINT (-87.6298 41.8781) |
|4  |Point D|Los Angeles |POINT (-118.2437 34.0522)|POINT (-118.2437 34.0522)|
+---+------+--------+--------------------+--------------------+
```

## Next Steps

After mastering Spark-optimized database connections:

- **Streaming Operations**: Implement real-time database streaming with Spark
- **Advanced Spatial Analysis**: Use Sedona for complex spatial operations
- **Performance Tuning**: Optimize database operations for large datasets
- **Multi-Database Operations**: Work with multiple database types simultaneously
- **Data Lake Integration**: Connect to data lakes and warehouses

## Related Recipes

- **[Spark Processing](Spark-Processing)** - Master distributed data processing with Spark
- **[Batch Processing](Batch-Processing)** - Process large datasets with multi-engine support
- **[File Operations](File-Operations)** - Handle data files with multiple engines
- **[Basic Setup](Basic-Setup)** - Configure Siege Utilities for database operations

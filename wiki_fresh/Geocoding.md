# Geocoding Recipe

## Overview
This recipe demonstrates how to perform efficient address geocoding, reverse geocoding, spatial data processing, and geographic analysis using `siege_utilities`, supporting both Apache Spark and Pandas engines for seamless scalability from small datasets to massive distributed spatial operations.

## Prerequisites
- Python 3.7+
- `siege_utilities` library installed
- Apache Spark (optional, for distributed processing)
- Basic understanding of geospatial concepts

## Installation
```bash
pip install siege_utilities
pip install pyspark pandas numpy geopandas pyproj geopy  # Core dependencies
```

## Multi-Engine Geocoding Architecture

### 1. Engine-Agnostic Geocoding Manager

```python
from siege_utilities.geo.geocoding import GeocodingService
from siege_utilities.geo.spatial_data import SpatialDataProcessor
from siege_utilities.geo.spatial_transformations import CoordinateTransformer
from siege_utilities.distributed.spark_utils import SparkUtils
from siege_utilities.core.logging import Logger

class MultiEngineGeocodingManager:
    """Geocoding manager that works with both Spark and Pandas engines"""
    
    def __init__(self, default_engine="auto", spark_config=None, geocoding_config=None):
        self.default_engine = default_engine
        self.geocoding_config = geocoding_config or {}
        self.logger = Logger("multi_engine_geocoding_manager")
        
        # Initialize Spark if needed
        if default_engine in ["spark", "auto"]:
            self.spark_utils = SparkUtils(spark_config)
            self.spark_available = True
        else:
            self.spark_utils = None
            self.spark_available = False
        
        # Initialize geocoding components
        self._setup_geocoding_components()
    
    def _setup_geocoding_components(self):
        """Setup geocoding components based on configuration"""
        
        # Create geocoding service
        self.geocoding_service = GeocodingService(
            provider=self.geocoding_config.get("provider", "nominatim"),
            api_key=self.geocoding_config.get("api_key"),
            rate_limit=self.geocoding_config.get("rate_limit", 1)
        )
        
        # Create spatial data processor
        self.spatial_processor = SpatialDataProcessor(
            coordinate_system=self.geocoding_config.get("coordinate_system", "EPSG:4326")
        )
        
        # Create coordinate transformer
        self.coordinate_transformer = CoordinateTransformer(
            source_crs=self.geocoding_config.get("source_crs", "EPSG:4326"),
            target_crs=self.geocoding_config.get("target_crs", "EPSG:3857")
        )
    
    def get_optimal_engine(self, data_size_mb=None, operation_complexity="medium"):
        """Automatically select the best engine for geocoding operations"""
        
        if data_size_mb is None:
            return "auto"
        
        # Engine selection logic based on data size and operation complexity
        if data_size_mb < 10 and operation_complexity == "simple":
            return "pandas"
        elif data_size_mb < 100 and operation_complexity == "medium":
            return "pandas"
        elif data_size_mb >= 100 or operation_complexity == "complex":
            return "spark" if self.spark_available else "pandas"
        else:
            return "auto"
    
    def geocode_addresses(self, address_data, geocoding_config, engine=None, **kwargs):
        """Geocode addresses using specified or auto-detected engine"""
        
        # Estimate data size for engine selection
        data_size_mb = self._estimate_data_size(address_data)
        
        # Select optimal engine
        if engine is None:
            engine = self.get_optimal_engine(data_size_mb, geocoding_config.get("complexity", "medium"))
        
        self.logger.info(f"Geocoding addresses with {engine} engine (data size: {data_size_mb:.2f}MB)")
        
        # Start performance monitoring
        start_time = time.time()
        
        try:
            if engine == "spark" and self.spark_available:
                result = self._geocode_with_spark(address_data, geocoding_config, **kwargs)
            else:
                result = self._geocode_with_pandas(address_data, geocoding_config, **kwargs)
            
            # Log successful completion
            execution_time = time.time() - start_time
            self.logger.info(f"Successfully geocoded addresses with {engine} engine in {execution_time:.2f}s")
            
            return result
            
        except Exception as e:
            # Log error with context
            execution_time = time.time() - start_time
            self.logger.error(f"Error geocoding addresses with {engine} engine after {execution_time:.2f}s: {str(e)}")
            raise
    
    def reverse_geocode(self, coordinate_data, reverse_config, engine=None, **kwargs):
        """Reverse geocode coordinates using specified or auto-detected engine"""
        
        # Estimate data size for engine selection
        data_size_mb = self._estimate_data_size(coordinate_data)
        
        # Select optimal engine
        if engine is None:
            engine = self.get_optimal_engine(data_size_mb, reverse_config.get("complexity", "medium"))
        
        self.logger.info(f"Reverse geocoding coordinates with {engine} engine (data size: {data_size_mb:.2f}MB)")
        
        # Start performance monitoring
        start_time = time.time()
        
        try:
            if engine == "spark" and self.spark_available:
                result = self._reverse_geocode_with_spark(coordinate_data, reverse_config, **kwargs)
            else:
                result = self._reverse_geocode_with_pandas(coordinate_data, reverse_config, **kwargs)
            
            # Log successful completion
            execution_time = time.time() - start_time
            self.logger.info(f"Successfully reverse geocoded coordinates with {engine} engine in {execution_time:.2f}s")
            
            return result
            
        except Exception as e:
            # Log error with context
            execution_time = time.time() - start_time
            self.logger.error(f"Error reverse geocoding coordinates with {engine} engine after {execution_time:.2f}s: {str(e)}")
            raise
    
    def _geocode_with_spark(self, address_data, geocoding_config, **kwargs):
        """Geocode addresses using Spark for large datasets"""
        
        from pyspark.sql.functions import udf, col
        from pyspark.sql.types import StructType, StructField, StringType, DoubleType
        
        # Define schema for geocoding results
        geocoding_schema = StructType([
            StructField("latitude", DoubleType(), True),
            StructField("longitude", DoubleType(), True),
            StructField("confidence", DoubleType(), True),
            StructField("address_components", StringType(), True)
        ])
        
        # Create UDF for geocoding
        @udf(returnType=geocoding_schema)
        def geocode_address(address):
            if not address:
                return None
            
            try:
                # Use geocoding service
                result = self.geocoding_service.geocode(address)
                
                if result:
                    return (
                        result.get("latitude"),
                        result.get("longitude"),
                        result.get("confidence", 0.0),
                        str(result.get("address_components", {}))
                    )
                else:
                    return None
                    
            except Exception as e:
                self.logger.warning(f"Geocoding failed for address '{address}': {str(e)}")
                return None
        
        # Apply geocoding to address data
        if isinstance(address_data, str):
            # Load data from file
            if address_data.endswith('.csv'):
                df = self.spark_utils.read_csv(address_data)
            elif address_data.endswith('.parquet'):
                df = self.spark_utils.read_parquet(address_data)
            else:
                df = self.spark_utils.read_file(address_data)
        else:
            df = address_data
        
        # Get address column name
        address_column = geocoding_config.get("address_column", "address")
        
        # Apply geocoding
        geocoded_df = df.withColumn(
            "geocoding_result",
            geocode_address(col(address_column))
        )
        
        # Extract geocoding results
        result_df = geocoded_df.select(
            "*",
            col("geocoding_result.latitude").alias("latitude"),
            col("geocoding_result.longitude").alias("longitude"),
            col("geocoding_result.confidence").alias("confidence"),
            col("geocoding_result.address_components").alias("address_components")
        ).drop("geocoding_result")
        
        return result_df
    
    def _geocode_with_pandas(self, address_data, geocoding_config, **kwargs):
        """Geocode addresses using Pandas for smaller datasets"""
        
        import pandas as pd
        
        # Load data if needed
        if isinstance(address_data, str):
            if address_data.endswith('.csv'):
                df = pd.read_csv(address_data)
            elif address_data.endswith('.parquet'):
                df = pd.read_parquet(address_data)
            else:
                df = pd.read_file(address_data)
        else:
            df = address_data.copy()
        
        # Get address column name
        address_column = geocoding_config.get("address_column", "address")
        
        # Initialize result columns
        df['latitude'] = None
        df['longitude'] = None
        df['confidence'] = None
        df['address_components'] = None
        
        # Geocode addresses
        for index, row in df.iterrows():
            address = row[address_column]
            
            if pd.notna(address):
                try:
                    # Use geocoding service
                    result = self.geocoding_service.geocode(address)
                    
                    if result:
                        df.at[index, 'latitude'] = result.get("latitude")
                        df.at[index, 'longitude'] = result.get("longitude")
                        df.at[index, 'confidence'] = result.get("confidence", 0.0)
                        df.at[index, 'address_components'] = str(result.get("address_components", {}))
                    
                except Exception as e:
                    self.logger.warning(f"Geocoding failed for address '{address}' at index {index}: {str(e)}")
        
        return df
    
    def _reverse_geocode_with_spark(self, coordinate_data, reverse_config, **kwargs):
        """Reverse geocode coordinates using Spark for large datasets"""
        
        from pyspark.sql.functions import udf, col
        from pyspark.sql.types import StructType, StructField, StringType, DoubleType
        
        # Define schema for reverse geocoding results
        reverse_schema = StructType([
            StructField("address", StringType(), True),
            StructField("city", StringType(), True),
            StructField("state", StringType(), True),
            StructField("country", StringType(), True),
            StructField("confidence", DoubleType(), True)
        ])
        
        # Create UDF for reverse geocoding
        @udf(returnType=reverse_schema)
        def reverse_geocode_coordinates(lat, lon):
            if lat is None or lon is None:
                return None
            
            try:
                # Use geocoding service for reverse geocoding
                result = self.geocoding_service.reverse_geocode(lat, lon)
                
                if result:
                    return (
                        result.get("address"),
                        result.get("city"),
                        result.get("state"),
                        result.get("country"),
                        result.get("confidence", 0.0)
                    )
                else:
                    return None
                    
            except Exception as e:
                self.logger.warning(f"Reverse geocoding failed for coordinates ({lat}, {lon}): {str(e)}")
                return None
        
        # Load data if needed
        if isinstance(coordinate_data, str):
            if coordinate_data.endswith('.csv'):
                df = self.spark_utils.read_csv(coordinate_data)
            elif coordinate_data.endswith('.parquet'):
                df = self.spark_utils.read_parquet(coordinate_data)
            else:
                df = self.spark_utils.read_file(coordinate_data)
        else:
            df = coordinate_data
        
        # Get coordinate column names
        lat_column = reverse_config.get("latitude_column", "latitude")
        lon_column = reverse_config.get("longitude_column", "longitude")
        
        # Apply reverse geocoding
        reverse_geocoded_df = df.withColumn(
            "reverse_geocoding_result",
            reverse_geocode_coordinates(col(lat_column), col(lon_column))
        )
        
        # Extract reverse geocoding results
        result_df = reverse_geocoded_df.select(
            "*",
            col("reverse_geocoding_result.address").alias("address"),
            col("reverse_geocoding_result.city").alias("city"),
            col("reverse_geocoding_result.state").alias("state"),
            col("reverse_geocoding_result.country").alias("country"),
            col("reverse_geocoding_result.confidence").alias("confidence")
        ).drop("reverse_geocoding_result")
        
        return result_df
    
    def _reverse_geocode_with_pandas(self, coordinate_data, reverse_config, **kwargs):
        """Reverse geocode coordinates using Pandas for smaller datasets"""
        
        import pandas as pd
        
        # Load data if needed
        if isinstance(coordinate_data, str):
            if coordinate_data.endswith('.csv'):
                df = pd.read_csv(coordinate_data)
            elif coordinate_data.endswith('.parquet'):
                df = pd.read_parquet(coordinate_data)
            else:
                df = pd.read_file(coordinate_data)
        else:
            df = coordinate_data.copy()
        
        # Get coordinate column names
        lat_column = reverse_config.get("latitude_column", "latitude")
        lon_column = reverse_config.get("longitude_column", "longitude")
        
        # Initialize result columns
        df['address'] = None
        df['city'] = None
        df['state'] = None
        df['country'] = None
        df['confidence'] = None
        
        # Reverse geocode coordinates
        for index, row in df.iterrows():
            lat = row[lat_column]
            lon = row[lon_column]
            
            if pd.notna(lat) and pd.notna(lon):
                try:
                    # Use geocoding service for reverse geocoding
                    result = self.geocoding_service.reverse_geocoding(lat, lon)
                    
                    if result:
                        df.at[index, 'address'] = result.get("address")
                        df.at[index, 'city'] = result.get("city")
                        df.at[index, 'state'] = result.get("state")
                        df.at[index, 'country'] = result.get("country")
                        df.at[index, 'confidence'] = result.get("confidence", 0.0)
                    
                except Exception as e:
                    self.logger.warning(f"Reverse geocoding failed for coordinates ({lat}, {lon}) at index {index}: {str(e)}")
        
        return df
    
    def _estimate_data_size(self, data):
        """Estimate data size in MB"""
        
        if hasattr(data, 'toPandas'):  # Spark DataFrame
            # Sample data to estimate size
            sample = data.limit(1000).toPandas()
            sample_size_mb = sample.memory_usage(deep=True).sum() / (1024 * 1024)
            # Estimate total size based on sample
            total_rows = data.count()
            estimated_size_mb = (sample_size_mb / 1000) * total_rows
            return estimated_size_mb
        else:  # Pandas DataFrame
            return data.memory_usage(deep=True).sum() / (1024 * 1024)
```

### 2. Multi-Engine Spatial Data Processing

```python
class MultiEngineSpatialProcessor:
    """Process spatial data using any engine"""
    
    def __init__(self, geocoding_manager):
        self.geocoding_manager = geocoding_manager
        self.logger = Logger("spatial_processor")
    
    def process_spatial_data(self, spatial_data, processing_config, engine=None, **kwargs):
        """Process spatial data using specified or auto-detected engine"""
        
        # Estimate data size for engine selection
        data_size_mb = self.geocoding_manager._estimate_data_size(spatial_data)
        
        # Select optimal engine
        if engine is None:
            engine = self.geocoding_manager.get_optimal_engine(data_size_mb, processing_config.get("complexity", "medium"))
        
        self.logger.info(f"Processing spatial data with {engine} engine (data size: {data_size_mb:.2f}MB)")
        
        if engine == "spark" and self.geocoding_manager.spark_available:
            return self._process_spatial_with_spark(spatial_data, processing_config, **kwargs)
        else:
            return self._process_spatial_with_pandas(spatial_data, processing_config, **kwargs)
    
    def _process_spatial_with_spark(self, spatial_data, processing_config, **kwargs):
        """Process spatial data using Spark for large datasets"""
        
        from pyspark.sql.functions import udf, col, expr
        from pyspark.sql.types import DoubleType, StringType
        
        # Load data if needed
        if isinstance(spatial_data, str):
            if spatial_data.endswith('.geojson'):
                df = self.geocoding_manager.spark_utils.read_geojson(spatial_data)
            elif spatial_data.endswith('.parquet'):
                df = self.geocoding_manager.spark_utils.read_parquet(spatial_data)
            else:
                df = self.geocoding_manager.spark_utils.read_file(spatial_data)
        else:
            df = spatial_data
        
        # Apply spatial processing operations
        operation_type = processing_config.get("type")
        
        if operation_type == "coordinate_transformation":
            df = self._transform_coordinates_spark(df, processing_config)
        elif operation_type == "spatial_join":
            df = self._spatial_join_spark(df, processing_config)
        elif operation_type == "distance_calculation":
            df = self._calculate_distances_spark(df, processing_config)
        elif operation_type == "buffer_creation":
            df = self._create_buffers_spark(df, processing_config)
        
        return df
    
    def _process_spatial_with_pandas(self, spatial_data, processing_config, **kwargs):
        """Process spatial data using Pandas for smaller datasets"""
        
        import geopandas as gpd
        
        # Load data if needed
        if isinstance(spatial_data, str):
            if spatial_data.endswith('.geojson'):
                df = gpd.read_file(spatial_data)
            elif spatial_data.endswith('.parquet'):
                df = gpd.read_parquet(spatial_data)
            else:
                df = gpd.read_file(spatial_data)
        else:
            df = spatial_data.copy()
        
        # Apply spatial processing operations
        operation_type = processing_config.get("type")
        
        if operation_type == "coordinate_transformation":
            df = self._transform_coordinates_pandas(df, processing_config)
        elif operation_type == "spatial_join":
            df = self._spatial_join_pandas(df, processing_config)
        elif operation_type == "distance_calculation":
            df = self._calculate_distances_pandas(df, processing_config)
        elif operation_type == "buffer_creation":
            df = self._create_buffers_pandas(df, processing_config)
        
        return df
    
    def _transform_coordinates_spark(self, df, config):
        """Transform coordinates using Spark"""
        
        source_crs = config.get("source_crs", "EPSG:4326")
        target_crs = config.get("target_crs", "EPSG:3857")
        
        # Create UDF for coordinate transformation
        @udf(returnType=StringType())
        def transform_coordinates(lat, lon):
            try:
                transformer = self.geocoding_manager.coordinate_transformer
                transformed_lat, transformed_lon = transformer.transform_coordinates(lat, lon, source_crs, target_crs)
                return f"{transformed_lat},{transformed_lon}"
            except Exception as e:
                return None
        
        # Apply transformation
        lat_column = config.get("latitude_column", "latitude")
        lon_column = config.get("longitude_column", "longitude")
        
        df = df.withColumn(
            "transformed_coordinates",
            transform_coordinates(col(lat_column), col(lon_column))
        )
        
        return df
    
    def _transform_coordinates_pandas(self, df, config):
        """Transform coordinates using Pandas/GeoPandas"""
        
        source_crs = config.get("source_crs", "EPSG:4326")
        target_crs = config.get("target_crs", "EPSG:3857")
        
        # Transform coordinates
        df = df.to_crs(target_crs)
        
        return df
    
    def _spatial_join_spark(self, df, config):
        """Perform spatial join using Spark"""
        
        # This would require GeoSpark or similar spatial extensions
        # For now, we'll implement a basic join based on bounding boxes
        
        join_column = config.get("join_column", "geometry")
        join_type = config.get("join_type", "inner")
        
        # Create bounding box columns for spatial join
        df = df.withColumn("bbox_min_x", expr("ST_XMin(ST_GeomFromText(geometry))"))
        df = df.withColumn("bbox_max_x", expr("ST_XMax(ST_GeomFromText(geometry))"))
        df = df.withColumn("bbox_min_y", expr("ST_YMin(ST_GeomFromText(geometry))"))
        df = df.withColumn("bbox_max_y", expr("ST_YMax(ST_GeomFromText(geometry))"))
        
        return df
    
    def _spatial_join_pandas(self, df, config):
        """Perform spatial join using Pandas/GeoPandas"""
        
        join_column = config.get("join_column", "geometry")
        join_type = config.get("join_type", "inner")
        
        # Perform spatial join
        if "other_data" in config:
            other_df = config["other_data"]
            df = gpd.sjoin(df, other_df, how=join_type, predicate="intersects")
        
        return df
    
    def _calculate_distances_spark(self, df, config):
        """Calculate distances using Spark"""
        
        # Create UDF for distance calculation
        @udf(returnType=DoubleType())
        def calculate_distance(lat1, lon1, lat2, lon2):
            try:
                from geopy.distance import geodesic
                point1 = (lat1, lon1)
                point2 = (lat2, lon2)
                return geodesic(point1, point2).kilometers
            except Exception as e:
                return None
        
        # Apply distance calculation
        lat1_column = config.get("lat1_column", "lat1")
        lon1_column = config.get("lon1_column", "lon1")
        lat2_column = config.get("lat2_column", "lat2")
        lon2_column = config.get("lon2_column", "lon2")
        
        df = df.withColumn(
            "distance_km",
            calculate_distance(col(lat1_column), col(lon1_column), col(lat2_column), col(lon2_column))
        )
        
        return df
    
    def _calculate_distances_pandas(self, df, config):
        """Calculate distances using Pandas"""
        
        from geopy.distance import geodesic
        
        # Get column names
        lat1_column = config.get("lat1_column", "lat1")
        lon1_column = config.get("lon1_column", "lon1")
        lat2_column = config.get("lat2_column", "lat2")
        lon2_column = config.get("lon2_column", "lon2")
        
        # Calculate distances
        distances = []
        for index, row in df.iterrows():
            try:
                point1 = (row[lat1_column], row[lon1_column])
                point2 = (row[lat2_column], row[lon2_column])
                distance = geodesic(point1, point2).kilometers
                distances.append(distance)
            except Exception as e:
                distances.append(None)
        
        df['distance_km'] = distances
        
        return df
    
    def _create_buffers_spark(self, df, config):
        """Create buffers using Spark"""
        
        buffer_distance = config.get("buffer_distance", 1000)  # meters
        
        # Create UDF for buffer creation
        @udf(returnType=StringType())
        def create_buffer(lat, lon, distance):
            try:
                # This would require proper spatial operations in Spark
                # For now, we'll return a simple buffer representation
                return f"BUFFER({lat},{lon},{distance})"
            except Exception as e:
                return None
        
        # Apply buffer creation
        lat_column = config.get("latitude_column", "latitude")
        lon_column = config.get("longitude_column", "longitude")
        
        df = df.withColumn(
            "buffer_geometry",
            create_buffer(col(lat_column), col(lon_column), buffer_distance)
        )
        
        return df
    
    def _create_buffers_pandas(self, df, config):
        """Create buffers using Pandas/GeoPandas"""
        
        buffer_distance = config.get("buffer_distance", 1000)  # meters
        
        # Create buffers
        df['buffer_geometry'] = df.geometry.buffer(buffer_distance / 100000)  # Convert to degrees
        
        return df
```

### 3. Multi-Engine Batch Geocoding

```python
class MultiEngineBatchGeocoder:
    """Process multiple geocoding tasks with optimal engine selection"""
    
    def __init__(self, geocoding_manager):
        self.geocoding_manager = geocoding_manager
        self.logger = Logger("batch_geocoder")
    
    def batch_geocode(self, geocoding_tasks, output_dir="output", engine="auto"):
        """Process multiple geocoding tasks using optimal engines for each"""
        
        results = {}
        
        for task_name, task_config in geocoding_tasks.items():
            try:
                # Process individual task with optimal engine selection
                result = self._process_single_task(task_name, task_config, output_dir, engine)
                results[task_name] = result
                
            except Exception as e:
                self.logger.error(f"Error processing {task_name}: {str(e)}")
                results[task_name] = {"error": str(e), "status": "failed"}
        
        return results
    
    def _process_single_task(self, task_name, task_config, output_dir, engine):
        """Process a single geocoding task with optimal engine selection"""
        
        # Get task data
        data_source = task_config.get("data_source")
        geocoding_config = task_config.get("geocoding_config", {})
        spatial_config = task_config.get("spatial_config", {})
        
        # Load data
        if isinstance(data_source, str):
            data = self._load_data(data_source, engine)
        else:
            data = data_source
        
        # Perform geocoding
        if geocoding_config:
            geocoded_data = self.geocoding_manager.geocode_addresses(
                data, geocoding_config, engine=engine
            )
        else:
            geocoded_data = data
        
        # Perform spatial processing
        if spatial_config:
            processed_data = self.geocoding_manager.spatial_processor.process_spatial_data(
                geocoded_data, spatial_config, engine=engine
            )
        else:
            processed_data = geocoded_data
        
        # Generate output filename
        base_name = f"{task_name}_geocoded"
        output_path = f"{output_dir}/{base_name}.parquet"
        
        # Save processed data
        self._save_data(processed_data, output_path, engine)
        
        return {
            "task_name": task_name,
            "output_file": output_path,
            "engine_used": engine,
            "record_count": self._get_record_count(processed_data, engine),
            "status": "success"
        }
    
    def _load_data(self, data_source, engine):
        """Load data using specified engine"""
        
        if engine == "spark" and self.geocoding_manager.spark_available:
            if data_source.endswith('.geojson'):
                return self.geocoding_manager.spark_utils.read_geojson(data_source)
            elif data_source.endswith('.parquet'):
                return self.geocoding_manager.spark_utils.read_parquet(data_source)
            else:
                return self.geocoding_manager.spark_utils.read_file(data_source)
        else:
            if data_source.endswith('.geojson'):
                import geopandas as gpd
                return gpd.read_file(data_source)
            elif data_source.endswith('.parquet'):
                import pandas as pd
                return pd.read_parquet(data_source)
            else:
                import pandas as pd
                return pd.read_file(data_source)
    
    def _save_data(self, data, output_path, engine):
        """Save data using specified engine"""
        
        if engine == "spark":
            data.write.parquet(output_path)
        else:
            data.to_parquet(output_path, index=False)
    
    def _get_record_count(self, data, engine):
        """Get record count from any engine"""
        
        if engine == "spark":
            return data.count()
        else:
            return len(data)
```

## Integration Examples

### 1. Multi-Engine Geocoding Pipeline

```python
def create_multi_engine_geocoding_pipeline():
    """Create a complete multi-engine geocoding pipeline"""
    
    # Initialize geocoding manager
    geocoding_config = {
        "provider": "nominatim",
        "rate_limit": 1,
        "coordinate_system": "EPSG:4326",
        "source_crs": "EPSG:4326",
        "target_crs": "EPSG:3857"
    }
    
    geocoding_manager = MultiEngineGeocodingManager(default_engine="auto", geocoding_config=geocoding_config)
    
    # Create specialized processors
    spatial_processor = MultiEngineSpatialProcessor(geocoding_manager)
    batch_geocoder = MultiEngineBatchGeocoder(geocoding_manager)
    
    # Define geocoding tasks
    geocoding_tasks = {
        "customer_addresses": {
            "data_source": "data/customers/customer_addresses.csv",
            "geocoding_config": {
                "address_column": "full_address",
                "complexity": "medium"
            },
            "spatial_config": {
                "type": "coordinate_transformation",
                "source_crs": "EPSG:4326",
                "target_crs": "EPSG:3857"
            }
        },
        "store_locations": {
            "data_source": "data/stores/store_locations.csv",
            "geocoding_config": {
                "address_column": "store_address",
                "complexity": "simple"
            },
            "spatial_config": {
                "type": "buffer_creation",
                "buffer_distance": 5000  # 5km buffer
            }
        },
        "delivery_zones": {
            "data_source": "data/delivery/delivery_zones.geojson",
            "geocoding_config": {},  # No geocoding needed for GeoJSON
            "spatial_config": {
                "type": "spatial_join",
                "join_column": "geometry",
                "join_type": "inner"
            }
        }
    }
    
    # Process geocoding tasks with optimal engine selection
    batch_results = batch_geocoder.batch_geocode(geocoding_tasks, "output/geocoded")
    
    # Perform additional spatial analysis
    spatial_analysis_results = {}
    
    for task_name, result in batch_results.items():
        if result.get("status") == "success":
            # Load processed data for additional analysis
            processed_data = batch_geocoder._load_data(result["output_file"], "auto")
            
            # Perform distance calculations between stores and customers
            if task_name == "customer_addresses":
                distance_config = {
                    "type": "distance_calculation",
                    "lat1_column": "latitude",
                    "lon1_column": "longitude",
                    "lat2_column": "store_lat",
                    "lon2_column": "store_lon"
                }
                
                spatial_analysis_results[task_name] = spatial_processor.process_spatial_data(
                    processed_data, distance_config
                )
    
    return batch_results, spatial_analysis_results

# Run the pipeline
geocoding_pipeline_results = create_multi_engine_geocoding_pipeline()
```

### 2. Real-time Geocoding Dashboard

```python
def create_geocoding_dashboard():
    """Create a dashboard to monitor geocoding operations in real-time"""
    
    import dash
    from dash import dcc, html
    from dash.dependencies import Input, Output
    import plotly.graph_objs as go
    
    app = dash.Dash(__name__)
    
    app.layout = html.Div([
        html.H1("Multi-Engine Geocoding Dashboard"),
        
        html.Div([
            html.Div([
                html.Label("Geocoding Provider:"),
                dcc.Dropdown(
                    id="provider-filter",
                    options=[
                        {"label": "All Providers", "value": "all"},
                        {"label": "Nominatim", "value": "nominatim"},
                        {"label": "Google", "value": "google"},
                        {"label": "Bing", "value": "bing"}
                    ],
                    value="all",
                    style={"width": "150px"}
                )
            ], style={"width": "200px", "margin": "20px"}),
            
            html.Div([
                html.Label("Engine:"),
                dcc.Dropdown(
                    id="engine-filter",
                    options=[
                        {"label": "All Engines", "value": "all"},
                        {"label": "Pandas", "value": "pandas"},
                        {"label": "Spark", "value": "spark"},
                        {"label": "Auto", "value": "auto"}
                    ],
                    value="all",
                    style={"width": "150px"}
                )
            ], style={"width": "200px", "margin": "20px"}),
            
            html.Div([
                html.Label("Update Frequency (seconds):"),
                dcc.Slider(
                    id="update-frequency",
                    min=5,
                    max=60,
                    step=5,
                    value=30,
                    marks={i: str(i) for i in [5, 15, 30, 45, 60]},
                    tooltip={"placement": "bottom", "always_visible": True}
                )
            ], style={"width": "300px", "margin": "20px"})
        ], style={"display": "flex", "justifyContent": "center", "marginBottom": "20px"}),
        
        html.Div([
            dcc.Graph(id="geocoding-success-chart"),
            dcc.Graph(id="engine-performance-chart"),
            dcc.Graph(id="geocoding-accuracy-chart")
        ]),
        
        dcc.Interval(id="update-interval", interval=30*1000)  # Update every 30 seconds
    ])
    
    @app.callback(
        [Output("geocoding-success-chart", "figure"),
         Output("engine-performance-chart", "figure"),
         Output("geocoding-accuracy-chart", "figure")],
        [Input("update-interval", "n_intervals"),
         Input("provider-filter", "value"),
         Input("engine-filter", "value"),
         Input("update-frequency", "value")]
    )
    def update_charts(n, provider, engine, frequency):
        # Get geocoding data (this would come from your actual geocoding system)
        # For demonstration, we'll create sample data
        
        # Geocoding success chart
        time_points = list(range(24))  # Last 24 hours
        success_rates = [np.random.uniform(85, 98) for _ in time_points]
        
        success_fig = go.Figure(data=[
            go.Scatter(x=time_points, y=success_rates, mode="lines+markers", name="Success Rate")
        ])
        success_fig.update_layout(title="Geocoding Success Rate Over Time", xaxis_title="Hours Ago", yaxis_title="Success Rate (%)")
        
        # Engine performance chart
        engines = ["pandas", "spark", "auto"]
        avg_geocoding_times = [0.5, 2.1, 1.2]  # seconds per address
        
        perf_fig = go.Figure(data=[
            go.Bar(x=engines, y=avg_geocoding_times, name="Average Geocoding Time")
        ])
        perf_fig.update_layout(title="Engine Performance Comparison", yaxis_title="Time per Address (seconds)")
        
        # Geocoding accuracy chart
        accuracy_metrics = ["High", "Medium", "Low"]
        accuracy_counts = [1200, 800, 200]
        
        accuracy_fig = go.Figure(data=[
            go.Pie(labels=accuracy_metrics, values=accuracy_counts, name="Geocoding Accuracy")
        ])
        accuracy_fig.update_layout(title="Geocoding Accuracy Distribution")
        
        return success_fig, perf_fig, accuracy_fig
    
    return app

# Start the dashboard
geocoding_dashboard = create_geocoding_dashboard()
geocoding_dashboard.run_server(debug=True, port=8055)
```

## Best Practices

### 1. Engine Selection
- Use **Pandas** for datasets < 10MB and simple geocoding
- Use **Spark** for datasets > 100MB and complex spatial operations
- Use **Auto-detection** for unknown data sizes and dynamic workloads
- Consider **geocoding complexity** when selecting engine

### 2. Performance Optimization
- **Cache geocoding results** to avoid repeated API calls
- **Use appropriate coordinate systems** for your use case
- **Implement rate limiting** for external geocoding services
- **Monitor API usage** and costs

### 3. Data Quality
- **Validate addresses** before geocoding
- **Handle geocoding failures** gracefully
- **Use confidence scores** to filter low-quality results
- **Implement address standardization** for better results

### 4. Error Handling
- **Implement fallback mechanisms** when geocoding services fail
- **Provide meaningful error messages** for debugging
- **Log geocoding failures** for analysis
- **Retry failed geocoding** with different providers when possible

## Troubleshooting

### Common Issues

1. **Engine Compatibility Issues**
   ```python
   # Check engine availability
   if geocoding_manager.spark_available:
       print("Spark is available for distributed geocoding")
   else:
       print("Using Pandas only")
   ```

2. **API Rate Limiting**
   ```python
   # Adjust rate limiting based on provider
   if provider == "nominatim":
       rate_limit = 1  # 1 request per second
   elif provider == "google":
       rate_limit = 10  # 10 requests per second
   ```

3. **Coordinate System Issues**
   ```python
   # Check coordinate system compatibility
   source_crs = "EPSG:4326"  # WGS84
   target_crs = "EPSG:3857"  # Web Mercator
   
   # Transform coordinates if needed
   transformed_data = coordinate_transformer.transform_coordinates(data, source_crs, target_crs)
   ```

## Conclusion

The multi-engine geocoding capabilities in `siege_utilities` provide:

- **Seamless scalability** from small address lists to massive datasets
- **Automatic engine selection** based on data characteristics
- **Unified geocoding interfaces** that work with both Spark and Pandas
- **Comprehensive spatial processing** across all engines
- **Performance optimization** through intelligent engine selection

By following this recipe, you can build robust, scalable geocoding pipelines that automatically adapt to your data sizes and processing requirements while providing high-quality geographic data for your applications.

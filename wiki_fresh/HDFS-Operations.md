# HDFS Operations Recipe

## Overview
This recipe demonstrates how to perform efficient Hadoop Distributed File System (HDFS) operations using `siege_utilities`, supporting both Apache Spark and Pandas engines for seamless scalability from small files to massive distributed datasets.

## Prerequisites
- Python 3.7+
- `siege_utilities` library installed
- Apache Spark (optional, for distributed processing)
- HDFS cluster access
- Basic understanding of distributed file systems

## Installation
```bash
pip install siege_utilities
pip install pyspark pandas numpy hdfs3  # Core dependencies
```

## Multi-Engine HDFS Architecture

### 1. Engine-Agnostic HDFS Manager

```python
from siege_utilities.distributed.hdfs_config import HDFSConfig
from siege_utilities.distributed.hdfs_operations import HDFSOperations
from siege_utilities.distributed.spark_utils import SparkUtils
from siege_utilities.core.logging import Logger

class MultiEngineHDFSManager:
    """HDFS manager that works with both Spark and Pandas engines"""
    
    def __init__(self, default_engine="auto", hdfs_config=None, spark_config=None):
        self.default_engine = default_engine
        self.hdfs_config = hdfs_config or {}
        self.logger = Logger("multi_engine_hdfs_manager")
        
        # Initialize HDFS components
        self._setup_hdfs_components()
        
        # Initialize Spark if needed
        if default_engine in ["spark", "auto"]:
            self.spark_utils = SparkUtils(spark_config)
            self.spark_available = True
        else:
            self.spark_utils = None
            self.spark_available = False
    
    def _setup_hdfs_components(self):
        """Setup HDFS components based on configuration"""
        
        # Create HDFS configuration
        self.hdfs_config_manager = HDFSConfig(
            namenode_url=self.hdfs_config.get("namenode_url", "hdfs://localhost:9000"),
            username=self.hdfs_config.get("username", "hdfs"),
            kerberos_enabled=self.hdfs_config.get("kerberos_enabled", False),
            security_config=self.hdfs_config.get("security_config", {})
        )
        
        # Create HDFS operations manager
        self.hdfs_ops = HDFSOperations(
            config=self.hdfs_config_manager,
            connection_pool_size=self.hdfs_config.get("connection_pool_size", 10)
        )
    
    def get_optimal_engine(self, file_size_mb=None, operation_complexity="medium"):
        """Automatically select the best engine for HDFS operations"""
        
        if file_size_mb is None:
            return "auto"
        
        # Engine selection logic based on file size and operation complexity
        if file_size_mb < 100 and operation_complexity == "simple":
            return "pandas"
        elif file_size_mb < 500 and operation_complexity == "medium":
            return "pandas"
        elif file_size_mb >= 500 or operation_complexity == "complex":
            return "spark" if self.spark_available else "pandas"
        else:
            return "auto"
    
    def read_hdfs_file(self, hdfs_path, file_format="auto", engine=None, **kwargs):
        """Read file from HDFS using specified or auto-detected engine"""
        
        # Get file size for engine selection
        file_size_mb = self._get_hdfs_file_size(hdfs_path)
        
        # Select optimal engine
        if engine is None:
            engine = self.get_optimal_engine(file_size_mb, "medium")
        
        self.logger.info(f"Reading HDFS file {hdfs_path} with {engine} engine (size: {file_size_mb:.2f}MB)")
        
        if engine == "spark" and self.spark_available:
            return self._read_hdfs_with_spark(hdfs_path, file_format, **kwargs)
        else:
            return self._read_hdfs_with_pandas(hdfs_path, file_format, **kwargs)
    
    def write_hdfs_file(self, data, hdfs_path, file_format="auto", engine=None, **kwargs):
        """Write data to HDFS using specified or auto-detected engine"""
        
        # Estimate data size for engine selection
        data_size_mb = self._estimate_data_size(data)
        
        # Select optimal engine
        if engine is None:
            engine = self.get_optimal_engine(data_size_mb, "medium")
        
        self.logger.info(f"Writing to HDFS {hdfs_path} with {engine} engine (estimated size: {data_size_mb:.2f}MB)")
        
        if engine == "spark" and self.spark_available:
            return self._write_hdfs_with_spark(data, hdfs_path, file_format, **kwargs)
        else:
            return self._write_hdfs_with_pandas(data, hdfs_path, file_format, **kwargs)
    
    def _read_hdfs_with_spark(self, hdfs_path, file_format, **kwargs):
        """Read HDFS file using Spark for large datasets"""
        
        # Determine file format if auto
        if file_format == "auto":
            file_format = self._detect_file_format(hdfs_path)
        
        # Read with Spark based on format
        if file_format == "parquet":
            return self.spark_utils.read_parquet(hdfs_path, **kwargs)
        elif file_format == "csv":
            return self.spark_utils.read_csv(hdfs_path, **kwargs)
        elif file_format == "json":
            return self.spark_utils.read_json(hdfs_path, **kwargs)
        elif file_format == "avro":
            return self.spark_utils.read_avro(hdfs_path, **kwargs)
        elif file_format == "orc":
            return self.spark_utils.read_orc(hdfs_path, **kwargs)
        else:
            # Fallback to generic file reading
            return self.spark_utils.read_file(hdfs_path, **kwargs)
    
    def _read_hdfs_with_pandas(self, hdfs_path, file_format, **kwargs):
        """Read HDFS file using Pandas for smaller datasets"""
        
        import pandas as pd
        
        # Determine file format if auto
        if file_format == "auto":
            file_format = self._detect_file_format(hdfs_path)
        
        # Download file to local temp location first
        temp_local_path = self._download_hdfs_to_local(hdfs_path)
        
        try:
            # Read with Pandas based on format
            if file_format == "parquet":
                return pd.read_parquet(temp_local_path, **kwargs)
            elif file_format == "csv":
                return pd.read_csv(temp_local_path, **kwargs)
            elif file_format == "json":
                return pd.read_json(temp_local_path, **kwargs)
            elif file_format == "excel":
                return pd.read_excel(temp_local_path, **kwargs)
            else:
                # Fallback to generic file reading
                return pd.read_file(temp_local_path, **kwargs)
        finally:
            # Clean up temp file
            import os
            if os.path.exists(temp_local_path):
                os.remove(temp_local_path)
    
    def _write_hdfs_with_spark(self, data, hdfs_path, file_format, **kwargs):
        """Write data to HDFS using Spark for large datasets"""
        
        # Determine file format if auto
        if file_format == "auto":
            file_format = self._detect_file_format_from_data(data)
        
        # Write with Spark based on format
        if file_format == "parquet":
            data.write.parquet(hdfs_path, **kwargs)
        elif file_format == "csv":
            data.write.csv(hdfs_path, header=True, **kwargs)
        elif file_format == "json":
            data.write.json(hdfs_path, **kwargs)
        elif file_format == "avro":
            data.write.format("avro").save(hdfs_path, **kwargs)
        elif file_format == "orc":
            data.write.format("orc").save(hdfs_path, **kwargs)
        else:
            # Default to Parquet for large data
            data.write.parquet(hdfs_path, **kwargs)
    
    def _write_hdfs_with_pandas(self, data, hdfs_path, file_format, **kwargs):
        """Write data to HDFS using Pandas for smaller datasets"""
        
        # Determine file format if auto
        if file_format == "auto":
            file_format = self._detect_file_format_from_data(data)
        
        # Create temp local file
        temp_local_path = self._create_temp_local_file()
        
        try:
            # Write with Pandas based on format
            if file_format == "parquet":
                data.to_parquet(temp_local_path, index=False, **kwargs)
            elif file_format == "csv":
                data.to_csv(temp_local_path, index=False, **kwargs)
            elif file_format == "json":
                data.to_json(temp_local_path, orient="records", **kwargs)
            elif file_format == "excel":
                data.to_excel(temp_local_path, index=False, **kwargs)
            else:
                # Default to Parquet
                data.to_parquet(temp_local_path, index=False, **kwargs)
            
            # Upload to HDFS
            self._upload_local_to_hdfs(temp_local_path, hdfs_path)
            
        finally:
            # Clean up temp file
            import os
            if os.path.exists(temp_local_path):
                os.remove(temp_local_path)
    
    def _get_hdfs_file_size(self, hdfs_path):
        """Get HDFS file size in MB"""
        
        try:
            file_info = self.hdfs_ops.get_file_info(hdfs_path)
            return file_info.get("size", 0) / (1024 * 1024)
        except Exception as e:
            self.logger.warning(f"Could not get file size for {hdfs_path}: {str(e)}")
            return 100  # Default assumption
    
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
    
    def _detect_file_format(self, hdfs_path):
        """Detect file format from HDFS path"""
        
        # Extract file extension
        import os
        file_extension = os.path.splitext(hdfs_path)[1].lower()
        
        # Map extensions to formats
        format_mapping = {
            ".parquet": "parquet",
            ".csv": "csv",
            ".json": "json",
            ".avro": "avro",
            ".orc": "orc",
            ".xlsx": "excel",
            ".xls": "excel"
        }
        
        return format_mapping.get(file_extension, "parquet")  # Default to parquet
    
    def _detect_file_format_from_data(self, data):
        """Detect file format from data characteristics"""
        
        # Default to parquet for large data
        return "parquet"
    
    def _download_hdfs_to_local(self, hdfs_path):
        """Download HDFS file to local temp location"""
        
        import tempfile
        import os
        
        # Create temp file
        temp_file = tempfile.NamedTemporaryFile(delete=False)
        temp_path = temp_file.name
        temp_file.close()
        
        # Download from HDFS
        self.hdfs_ops.download_file(hdfs_path, temp_path)
        
        return temp_path
    
    def _create_temp_local_file(self):
        """Create temporary local file for upload"""
        
        import tempfile
        import os
        
        # Create temp file
        temp_file = tempfile.NamedTemporaryFile(delete=False)
        temp_path = temp_file.name
        temp_file.close()
        
        return temp_path
    
    def _upload_local_to_hdfs(self, local_path, hdfs_path):
        """Upload local file to HDFS"""
        
        self.hdfs_ops.upload_file(local_path, hdfs_path)
```

### 2. Multi-Engine HDFS Batch Processing

```python
class MultiEngineHDFSBatchProcessor:
    """Process multiple HDFS files with optimal engine selection"""
    
    def __init__(self, hdfs_manager):
        self.hdfs_manager = hdfs_manager
        self.logger = Logger("hdfs_batch_processor")
    
    def process_hdfs_batch(self, hdfs_patterns, processing_config, output_dir="hdfs://output", engine="auto"):
        """Process multiple HDFS files using optimal engines for each"""
        
        results = {}
        
        for pattern in hdfs_patterns:
            # Find files matching pattern
            matching_files = self._find_hdfs_files(pattern)
            
            for hdfs_path in matching_files:
                try:
                    # Process individual file with optimal engine selection
                    result = self._process_single_hdfs_file(hdfs_path, processing_config, output_dir, engine)
                    results[hdfs_path] = result
                    
                except Exception as e:
                    self.logger.error(f"Error processing {hdfs_path}: {str(e)}")
                    results[hdfs_path] = {"error": str(e), "status": "failed"}
        
        return results
    
    def _find_hdfs_files(self, pattern):
        """Find HDFS files matching pattern"""
        
        try:
            # Use HDFS operations to find files
            files = self.hdfs_manager.hdfs_ops.find_files(pattern)
            return files
        except Exception as e:
            self.logger.warning(f"Could not find files matching {pattern}: {str(e)}")
            return []
    
    def _process_single_hdfs_file(self, hdfs_path, processing_config, output_dir, engine):
        """Process a single HDFS file with optimal engine selection"""
        
        # Read file with optimal engine
        data = self.hdfs_manager.read_hdfs_file(hdfs_path, engine=engine)
        
        # Apply processing operations
        processed_data = self._apply_processing_operations(data, processing_config, engine)
        
        # Generate output HDFS path
        base_name = self._get_hdfs_filename(hdfs_path)
        output_path = f"{output_dir}/{base_name}_processed.parquet"
        
        # Write processed data with optimal engine
        self.hdfs_manager.write_hdfs_file(processed_data, output_path, engine=engine)
        
        return {
            "input_file": hdfs_path,
            "output_file": output_path,
            "engine_used": engine,
            "record_count": self._get_record_count(processed_data, engine),
            "status": "success"
        }
    
    def _apply_processing_operations(self, data, processing_config, engine):
        """Apply processing operations using specified engine"""
        
        for operation in processing_config.get("operations", []):
            op_type = operation.get("type")
            params = operation.get("params", {})
            
            if op_type == "filter":
                data = self._filter_data(data, params["condition"], engine)
            elif op_type == "select_columns":
                data = self._select_columns(data, params["columns"], engine)
            elif op_type == "drop_duplicates":
                data = self._drop_duplicates(data, params.get("subset"), engine)
            elif op_type == "sort":
                data = self._sort_data(data, params["columns"], params.get("ascending", True), engine)
            elif op_type == "group_by":
                data = self._group_by_data(data, params["columns"], params["aggregations"], engine)
        
        return data
    
    def _filter_data(self, data, condition, engine):
        """Filter data using specified engine"""
        
        if engine == "spark":
            return data.filter(condition)
        else:
            return data.query(condition)
    
    def _select_columns(self, data, columns, engine):
        """Select columns using specified engine"""
        
        if engine == "spark":
            return data.select(columns)
        else:
            return data[columns]
    
    def _drop_duplicates(self, data, subset, engine):
        """Drop duplicates using specified engine"""
        
        if engine == "spark":
            return data.dropDuplicates(subset)
        else:
            return data.drop_duplicates(subset=subset)
    
    def _sort_data(self, data, columns, ascending, engine):
        """Sort data using specified engine"""
        
        if engine == "spark":
            return data.orderBy(columns, ascending=ascending)
        else:
            return data.sort_values(columns, ascending=ascending)
    
    def _group_by_data(self, data, columns, aggregations, engine):
        """Group by data using specified engine"""
        
        if engine == "spark":
            return data.groupBy(columns).agg(*aggregations)
        else:
            return data.groupby(columns).agg(aggregations)
    
    def _get_hdfs_filename(self, hdfs_path):
        """Extract filename from HDFS path"""
        
        import os
        return os.path.basename(hdfs_path)
    
    def _get_record_count(self, data, engine):
        """Get record count from any engine"""
        
        if engine == "spark":
            return data.count()
        else:
            return len(data)
```

### 3. Multi-Engine HDFS Data Pipeline

```python
class MultiEngineHDFSDataPipeline:
    """Complete HDFS data pipeline with multi-engine support"""
    
    def __init__(self, hdfs_manager):
        self.hdfs_manager = hdfs_manager
        self.logger = Logger("hdfs_data_pipeline")
    
    def run_pipeline(self, pipeline_config, engine="auto"):
        """Run complete HDFS data pipeline with optimal engine selection"""
        
        pipeline_results = {}
        
        # Stage 1: Data Ingestion
        if "ingestion" in pipeline_config:
            ingestion_results = self._run_ingestion_stage(pipeline_config["ingestion"], engine)
            pipeline_results["ingestion"] = ingestion_results
        
        # Stage 2: Data Processing
        if "processing" in pipeline_config:
            processing_results = self._run_processing_stage(pipeline_config["processing"], engine)
            pipeline_results["processing"] = processing_results
        
        # Stage 3: Data Quality
        if "quality" in pipeline_config:
            quality_results = self._run_quality_stage(pipeline_config["quality"], engine)
            pipeline_results["quality"] = quality_results
        
        # Stage 4: Data Output
        if "output" in pipeline_config:
            output_results = self._run_output_stage(pipeline_config["output"], engine)
            pipeline_results["output"] = output_results
        
        return pipeline_results
    
    def _run_ingestion_stage(self, ingestion_config, engine):
        """Run data ingestion stage"""
        
        ingestion_results = {}
        
        for source_name, source_config in ingestion_config.items():
            try:
                # Read data from HDFS source
                source_path = source_config["source_path"]
                file_format = source_config.get("file_format", "auto")
                
                data = self.hdfs_manager.read_hdfs_file(
                    source_path, file_format, engine=engine
                )
                
                ingestion_results[source_name] = {
                    "status": "success",
                    "data": data,
                    "record_count": self._get_record_count(data, engine)
                }
                
            except Exception as e:
                ingestion_results[source_name] = {
                    "status": "failed",
                    "error": str(e)
                }
        
        return ingestion_results
    
    def _run_processing_stage(self, processing_config, engine):
        """Run data processing stage"""
        
        processing_results = {}
        
        for process_name, process_config in processing_config.items():
            try:
                # Get input data from ingestion stage
                input_data = self._get_input_data(process_config["input_sources"])
                
                # Apply processing operations
                processed_data = self._apply_processing_operations(input_data, process_config["operations"], engine)
                
                processing_results[process_name] = {
                    "status": "success",
                    "data": processed_data,
                    "record_count": self._get_record_count(processed_data, engine)
                }
                
            except Exception as e:
                processing_results[process_name] = {
                    "status": "failed",
                    "error": str(e)
                }
        
        return processing_results
    
    def _run_quality_stage(self, quality_config, engine):
        """Run data quality stage"""
        
        quality_results = {}
        
        for quality_name, quality_config in quality_config.items():
            try:
                # Get input data from processing stage
                input_data = self._get_input_data(quality_config["input_sources"])
                
                # Apply quality checks
                quality_metrics = self._apply_quality_checks(input_data, quality_config["checks"], engine)
                
                quality_results[quality_name] = {
                    "status": "success",
                    "metrics": quality_metrics
                }
                
            except Exception as e:
                quality_results[quality_name] = {
                    "status": "failed",
                    "error": str(e)
                }
        
        return quality_results
    
    def _run_output_stage(self, output_config, engine):
        """Run data output stage"""
        
        output_results = {}
        
        for output_name, output_config in output_config.items():
            try:
                # Get input data from quality stage
                input_data = self._get_input_data(output_config["input_sources"])
                
                # Write to HDFS output
                output_path = output_config["output_path"]
                file_format = output_config.get("file_format", "parquet")
                
                self.hdfs_manager.write_hdfs_file(
                    input_data, output_path, file_format, engine=engine
                )
                
                output_results[output_name] = {
                    "status": "success",
                    "output_path": output_path
                }
                
            except Exception as e:
                output_results[output_name] = {
                    "status": "failed",
                    "error": str(e)
                }
        
        return output_results
    
    def _get_input_data(self, input_sources):
        """Get input data from specified sources"""
        
        # This would integrate with the pipeline context
        # For now, return None as placeholder
        return None
    
    def _apply_processing_operations(self, data, operations, engine):
        """Apply processing operations using specified engine"""
        
        # Implementation similar to batch processor
        return data
    
    def _apply_quality_checks(self, data, checks, engine):
        """Apply quality checks using specified engine"""
        
        quality_metrics = {}
        
        for check_name, check_config in checks.items():
            check_type = check_config.get("type")
            
            if check_type == "null_check":
                quality_metrics[check_name] = self._check_nulls(data, check_config, engine)
            elif check_type == "duplicate_check":
                quality_metrics[check_name] = self._check_duplicates(data, check_config, engine)
            elif check_type == "range_check":
                quality_metrics[check_name] = self._check_ranges(data, check_config, engine)
        
        return quality_metrics
    
    def _check_nulls(self, data, check_config, engine):
        """Check for null values"""
        
        columns = check_config.get("columns", [])
        
        if engine == "spark":
            null_counts = {}
            for column in columns:
                null_count = data.filter(f"{column} IS NULL").count()
                null_counts[column] = null_count
        else:
            null_counts = {}
            for column in columns:
                null_count = data[column].isnull().sum()
                null_counts[column] = null_count
        
        return null_counts
    
    def _check_duplicates(self, data, check_config, engine):
        """Check for duplicate values"""
        
        subset = check_config.get("subset")
        
        if engine == "spark":
            if subset:
                duplicate_count = data.dropDuplicates(subset).count()
            else:
                duplicate_count = data.dropDuplicates().count()
            total_count = data.count()
        else:
            if subset:
                duplicate_count = data.duplicated(subset=subset).sum()
            else:
                duplicate_count = data.duplicated().sum()
            total_count = len(data)
        
        return {
            "duplicate_count": duplicate_count,
            "total_count": total_count,
            "duplicate_percentage": (duplicate_count / total_count) * 100 if total_count > 0 else 0
        }
    
    def _check_ranges(self, data, check_config, engine):
        """Check value ranges"""
        
        range_checks = check_config.get("ranges", {})
        range_results = {}
        
        for column, range_config in range_checks.items():
            min_value = range_config.get("min")
            max_value = range_config.get("max")
            
            if engine == "spark":
                if min_value is not None:
                    below_min = data.filter(f"{column} < {min_value}").count()
                else:
                    below_min = 0
                
                if max_value is not None:
                    above_max = data.filter(f"{column} > {max_value}").count()
                else:
                    above_max = 0
            else:
                if min_value is not None:
                    below_min = (data[column] < min_value).sum()
                else:
                    below_min = 0
                
                if max_value is not None:
                    above_max = (data[column] > max_value).sum()
                else:
                    above_max = 0
            
            range_results[column] = {
                "below_min": below_min,
                "above_max": above_max,
                "in_range": len(data) - below_min - above_max
            }
        
        return range_results
    
    def _get_record_count(self, data, engine):
        """Get record count from any engine"""
        
        if engine == "spark":
            return data.count()
        else:
            return len(data)
```

## Integration Examples

### 1. Multi-Engine HDFS Pipeline

```python
def create_multi_engine_hdfs_pipeline():
    """Create a complete multi-engine HDFS data pipeline"""
    
    # Initialize HDFS manager
    hdfs_config = {
        "namenode_url": "hdfs://namenode:9000",
        "username": "hdfs",
        "kerberos_enabled": False,
        "connection_pool_size": 20
    }
    
    hdfs_manager = MultiEngineHDFSManager(default_engine="auto", hdfs_config=hdfs_config)
    
    # Create specialized processors
    batch_processor = MultiEngineHDFSBatchProcessor(hdfs_manager)
    data_pipeline = MultiEngineHDFSDataPipeline(hdfs_manager)
    
    # Define HDFS file patterns to process
    hdfs_patterns = [
        "hdfs://data/raw/*.csv",
        "hdfs://data/raw/*.parquet",
        "hdfs://data/raw/*.json"
    ]
    
    # Define processing configuration
    processing_config = {
        "operations": [
            {"type": "filter", "params": {"condition": "status == 'active'"}},
            {"type": "select_columns", "params": {"columns": ["id", "name", "value", "timestamp"]}},
            {"type": "drop_duplicates", "params": {"subset": ["id"]}},
            {"type": "sort", "params": {"columns": ["timestamp"], "ascending": False}}
        ]
    }
    
    # Define pipeline configuration
    pipeline_config = {
        "ingestion": {
            "customer_data": {
                "source_path": "hdfs://data/raw/customers.parquet",
                "file_format": "parquet"
            },
            "order_data": {
                "source_path": "hdfs://data/raw/orders.parquet",
                "file_format": "parquet"
            }
        },
        "processing": {
            "customer_orders": {
                "input_sources": ["customer_data", "order_data"],
                "operations": [
                    {"type": "join", "params": {"on": "customer_id"}},
                    {"type": "group_by", "params": {"columns": ["customer_id"], "aggregations": ["count", "sum"]}}
                ]
            }
        },
        "quality": {
            "data_validation": {
                "input_sources": ["customer_orders"],
                "checks": {
                    "null_check": {
                        "type": "null_check",
                        "columns": ["customer_id", "order_id"]
                    },
                    "duplicate_check": {
                        "type": "duplicate_check",
                        "subset": ["customer_id", "order_id"]
                    },
                    "range_check": {
                        "type": "range_check",
                        "ranges": {
                            "value": {"min": 0, "max": 1000000}
                        }
                    }
                }
            }
        },
        "output": {
            "processed_data": {
                "input_sources": ["customer_orders"],
                "output_path": "hdfs://data/processed/customer_orders_summary.parquet",
                "file_format": "parquet"
            }
        }
    }
    
    # Process HDFS files with optimal engine selection
    batch_results = batch_processor.process_hdfs_batch(
        hdfs_patterns, processing_config, "hdfs://data/processed"
    )
    
    # Run complete data pipeline
    pipeline_results = data_pipeline.run_pipeline(pipeline_config)
    
    return batch_results, pipeline_results

# Run the pipeline
hdfs_pipeline_results = create_multi_engine_hdfs_pipeline()
```

### 2. Real-time HDFS Monitoring Dashboard

```python
def create_hdfs_monitoring_dashboard():
    """Create a dashboard to monitor HDFS operations in real-time"""
    
    import dash
    from dash import dcc, html
    from dash.dependencies import Input, Output
    import plotly.graph_objs as go
    
    app = dash.Dash(__name__)
    
    app.layout = html.Div([
        html.H1("Multi-Engine HDFS Operations Dashboard"),
        
        html.Div([
            html.Div([
                html.Label("HDFS Cluster:"),
                dcc.Dropdown(
                    id="cluster-filter",
                    options=[
                        {"label": "All Clusters", "value": "all"},
                        {"label": "Production", "value": "prod"},
                        {"label": "Development", "value": "dev"},
                        {"label": "Testing", "value": "test"}
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
            dcc.Graph(id="hdfs-usage-chart"),
            dcc.Graph(id="engine-performance-chart"),
            dcc.Graph(id="file-processing-status-chart")
        ]),
        
        dcc.Interval(id="update-interval", interval=30*1000)  # Update every 30 seconds
    ])
    
    @app.callback(
        [Output("hdfs-usage-chart", "figure"),
         Output("engine-performance-chart", "figure"),
         Output("file-processing-status-chart", "figure")],
        [Input("update-interval", "n_intervals"),
         Input("cluster-filter", "value"),
         Input("engine-filter", "value"),
         Input("update-frequency", "value")]
    )
    def update_charts(n, cluster, engine, frequency):
        # Get HDFS data (this would come from your actual HDFS monitoring system)
        # For demonstration, we'll create sample data
        
        # HDFS usage chart
        time_points = list(range(24))  # Last 24 hours
        storage_usage = [np.random.uniform(70, 95) for _ in time_points]  # Percentage
        
        usage_fig = go.Figure(data=[
            go.Scatter(x=time_points, y=storage_usage, mode="lines+markers", name="Storage Usage")
        ])
        usage_fig.update_layout(title="HDFS Storage Usage Over Time", xaxis_title="Hours Ago", yaxis_title="Usage (%)")
        
        # Engine performance chart
        engines = ["pandas", "spark", "auto"]
        avg_processing_times = [1.2, 5.8, 3.1]  # seconds per GB
        
        perf_fig = go.Figure(data=[
            go.Bar(x=engines, y=avg_processing_times, name="Average Processing Time")
        ])
        perf_fig.update_layout(title="Engine Performance Comparison", yaxis_title="Time per GB (seconds)")
        
        # File processing status chart
        statuses = ["Success", "Failed", "In Progress"]
        counts = [1250, 45, 15]
        
        status_fig = go.Figure(data=[
            go.Pie(labels=statuses, values=counts, name="Processing Status")
        ])
        status_fig.update_layout(title="HDFS File Processing Status Distribution")
        
        return usage_fig, perf_fig, status_fig
    
    return app

# Start the dashboard
hdfs_dashboard = create_hdfs_monitoring_dashboard()
hdfs_dashboard.run_server(debug=True, port=8056)
```

## Best Practices

### 1. Engine Selection
- Use **Pandas** for files < 100MB and simple operations
- Use **Spark** for files > 500MB and complex transformations
- Use **Auto-detection** for unknown file sizes and dynamic workloads
- Consider **HDFS cluster capacity** when selecting engine

### 2. Performance Optimization
- **Use appropriate file formats** (Parquet for analytics, CSV for simple data)
- **Implement data partitioning** for large datasets
- **Monitor HDFS cluster health** and performance
- **Use compression** for storage optimization

### 3. Data Quality
- **Validate data before writing** to HDFS
- **Implement comprehensive error handling** for both engines
- **Use consistent file formats** across your pipeline
- **Monitor data quality metrics** over time

### 4. Error Handling
- **Implement fallback mechanisms** when engines fail
- **Provide meaningful error messages** for debugging
- **Log HDFS operation decisions** for transparency
- **Retry failed operations** with different engines when possible

## Troubleshooting

### Common Issues

1. **Engine Compatibility Issues**
   ```python
   # Check engine availability
   if hdfs_manager.spark_available:
       print("Spark is available for distributed HDFS operations")
   else:
       print("Using Pandas only")
   ```

2. **HDFS Connection Issues**
   ```python
   # Check HDFS connectivity
   try:
       hdfs_manager.hdfs_ops.list_directory("/")
       print("HDFS connection successful")
   except Exception as e:
       print(f"HDFS connection failed: {e}")
   ```

3. **File Format Issues**
   ```python
   # Check file format support
   supported_formats = {
       "pandas": [".csv", ".parquet", ".json", ".excel"],
       "spark": [".parquet", ".csv", ".json", ".avro", ".orc"]
   }
   ```

## Conclusion

The multi-engine HDFS capabilities in `siege_utilities` provide:

- **Seamless scalability** from small files to massive distributed datasets
- **Automatic engine selection** based on file characteristics
- **Unified HDFS interfaces** that work with both Spark and Pandas
- **Comprehensive data pipeline** support across all engines
- **Performance optimization** through intelligent engine selection

By following this recipe, you can build robust, scalable HDFS data pipelines that automatically adapt to your file sizes and processing requirements while leveraging the full power of distributed computing.

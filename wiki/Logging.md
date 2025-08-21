# Logging Recipe

## Overview
This recipe demonstrates how to implement comprehensive application logging, debugging, monitoring, and audit trails using `siege_utilities`, supporting both Apache Spark and Pandas engines for seamless scalability from single applications to distributed systems.

## Prerequisites
- Python 3.7+
- `siege_utilities` library installed
- Apache Spark (optional, for distributed logging)
- Basic understanding of logging concepts

## Installation
```bash
pip install siege_utilities
pip install pyspark pandas numpy  # Core dependencies
```

## Multi-Engine Logging Architecture

### 1. Engine-Agnostic Logging Manager

```python
from siege_utilities.core.logging import Logger, LoggingContext, PerformanceLogger
from siege_utilities.distributed.spark_utils import SparkUtils
from siege_utilities.core.logging import LogLevel

class MultiEngineLoggingManager:
    """Logging manager that works with both Spark and Pandas engines"""
    
    def __init__(self, default_engine="auto", spark_config=None, log_config=None):
        self.default_engine = default_engine
        self.log_config = log_config or {}
        self.logger = Logger("multi_engine_logging_manager")
        
        # Initialize Spark if needed
        if default_engine in ["spark", "auto"]:
            self.spark_utils = SparkUtils(spark_config)
            self.spark_available = True
        else:
            self.spark_utils = None
            self.spark_available = False
        
        # Initialize logging components
        self._setup_logging_components()
    
    def _setup_logging_components(self):
        """Setup logging components based on configuration"""
        
        # Create main logger
        self.main_logger = Logger(
            name=self.log_config.get("logger_name", "multi_engine_app"),
            level=self.log_config.get("log_level", LogLevel.INFO),
            output_format=self.log_config.get("output_format", "json")
        )
        
        # Create performance logger
        self.performance_logger = PerformanceLogger(
            name=self.log_config.get("performance_logger_name", "performance_monitor"),
            metrics_storage=self.log_config.get("metrics_storage", "memory")
        )
        
        # Create logging context manager
        self.context_manager = LoggingContext(
            default_context=self.log_config.get("default_context", "application")
        )
    
    def get_optimal_engine(self, data_size_mb=None, operation_complexity="medium"):
        """Automatically select the best engine for logging operations"""
        
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
    
    def log_operation(self, operation_name, data, operation_config, engine=None, **kwargs):
        """Log operation with optimal engine selection"""
        
        # Estimate data size for engine selection
        data_size_mb = self._estimate_data_size(data)
        
        # Select optimal engine
        if engine is None:
            engine = self.get_optimal_engine(data_size_mb, operation_config.get("complexity", "medium"))
        
        self.main_logger.info(f"Starting {operation_name} with {engine} engine (data size: {data_size_mb:.2f}MB)")
        
        # Start performance monitoring
        with self.performance_logger.measure_operation(operation_name):
            try:
                # Execute operation with selected engine
                if engine == "spark" and self.spark_available:
                    result = self._execute_with_spark(data, operation_config, **kwargs)
                else:
                    result = self._execute_with_pandas(data, operation_config, **kwargs)
                
                # Log successful completion
                self.main_logger.info(f"Successfully completed {operation_name} with {engine} engine")
                
                # Log performance metrics
                operation_metrics = self.performance_logger.get_operation_metrics(operation_name)
                self.main_logger.info(f"Operation metrics: {operation_metrics}")
                
                return result
                
            except Exception as e:
                # Log error with context
                self.main_logger.error(f"Error in {operation_name} with {engine} engine: {str(e)}")
                
                # Log additional context
                with self.context_manager.context(f"error_{operation_name}"):
                    self.main_logger.error(f"Data size: {data_size_mb:.2f}MB")
                    self.main_logger.error(f"Operation config: {operation_config}")
                    self.main_logger.error(f"Engine used: {engine}")
                
                raise
    
    def _execute_with_spark(self, data, operation_config, **kwargs):
        """Execute operation using Spark for large datasets"""
        
        # Log Spark-specific information
        self.main_logger.info("Using Spark engine for execution")
        
        # Get Spark session info
        if hasattr(self.spark_utils, 'get_spark_session'):
            spark_session = self.spark_utils.get_spark_session()
            self.main_logger.info(f"Spark session: {spark_session.sparkContext.applicationId}")
        
        # Execute operation based on configuration
        operation_type = operation_config.get("type")
        
        if operation_type == "data_processing":
            return self._process_data_with_spark(data, operation_config, **kwargs)
        elif operation_type == "aggregation":
            return self._aggregate_data_with_spark(data, operation_config, **kwargs)
        elif operation_type == "transformation":
            return self._transform_data_with_spark(data, operation_config, **kwargs)
        else:
            # Default processing
            return data
    
    def _execute_with_pandas(self, data, operation_config, **kwargs):
        """Execute operation using Pandas for smaller datasets"""
        
        # Log Pandas-specific information
        self.main_logger.info("Using Pandas engine for execution")
        
        # Execute operation based on configuration
        operation_type = operation_config.get("type")
        
        if operation_type == "data_processing":
            return self._process_data_with_pandas(data, operation_config, **kwargs)
        elif operation_type == "aggregation":
            return self._aggregate_data_with_pandas(data, operation_config, **kwargs)
        elif operation_type == "transformation":
            return self._transform_data_with_pandas(data, operation_config, **kwargs)
        else:
            # Default processing
            return data
    
    def _process_data_with_spark(self, data, operation_config, **kwargs):
        """Process data using Spark"""
        
        # Apply filters
        if "filters" in operation_config:
            for filter_condition in operation_config["filters"]:
                data = data.filter(filter_condition)
                self.main_logger.debug(f"Applied filter: {filter_condition}")
        
        # Apply transformations
        if "transformations" in operation_config:
            for transform in operation_config["transformations"]:
                column = transform.get("column")
                operation = transform.get("operation")
                
                if operation == "cast":
                    new_type = transform.get("new_type")
                    data = data.withColumn(column, col(column).cast(new_type))
                    self.main_logger.debug(f"Casted column {column} to {new_type}")
        
        return data
    
    def _process_data_with_pandas(self, data, operation_config, **kwargs):
        """Process data using Pandas"""
        
        # Apply filters
        if "filters" in operation_config:
            for filter_condition in operation_config["filters"]:
                data = data.query(filter_condition)
                self.main_logger.debug(f"Applied filter: {filter_condition}")
        
        # Apply transformations
        if "transformations" in operation_config:
            for transform in operation_config["transformations"]:
                column = transform.get("column")
                operation = transform.get("operation")
                
                if operation == "cast":
                    new_type = transform.get("new_type")
                    data[column] = data[column].astype(new_type)
                    self.main_logger.debug(f"Casted column {column} to {new_type}")
        
        return data
    
    def _aggregate_data_with_spark(self, data, operation_config, **kwargs):
        """Aggregate data using Spark"""
        
        group_columns = operation_config.get("group_columns", [])
        aggregations = operation_config.get("aggregations", [])
        
        if group_columns and aggregations:
            data = data.groupBy(group_columns).agg(*aggregations)
            self.main_logger.debug(f"Aggregated data by {group_columns}")
        
        return data
    
    def _aggregate_data_with_pandas(self, data, operation_config, **kwargs):
        """Aggregate data using Pandas"""
        
        group_columns = operation_config.get("group_columns", [])
        aggregations = operation_config.get("aggregations", {})
        
        if group_columns and aggregations:
            data = data.groupby(group_columns).agg(aggregations)
            self.main_logger.debug(f"Aggregated data by {group_columns}")
        
        return data
    
    def _transform_data_with_spark(self, data, operation_config, **kwargs):
        """Transform data using Spark"""
        
        # Apply column transformations
        if "column_transformations" in operation_config:
            for transform in operation_config["column_transformations"]:
                column = transform.get("column")
                operation = transform.get("operation")
                
                if operation == "rename":
                    new_name = transform.get("new_name")
                    data = data.withColumnRenamed(column, new_name)
                    self.main_logger.debug(f"Renamed column {column} to {new_name}")
        
        return data
    
    def _transform_data_with_pandas(self, data, operation_config, **kwargs):
        """Transform data using Pandas"""
        
        # Apply column transformations
        if "column_transformations" in operation_config:
            for transform in operation_config["column_transformations"]:
                column = transform.get("column")
                operation = transform.get("operation")
                
                if operation == "rename":
                    new_name = transform.get("new_name")
                    data = data.rename(columns={column: new_name})
                    self.main_logger.debug(f"Renamed column {column} to {new_name}")
        
        return data
    
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

### 2. Multi-Engine Distributed Logging

```python
class MultiEngineDistributedLogger:
    """Distributed logging that works across multiple engines and nodes"""
    
    def __init__(self, logging_manager):
        self.logging_manager = logging_manager
        self.logger = Logger("distributed_logger")
        self.node_id = self._get_node_identifier()
    
    def _get_node_identifier(self):
        """Get unique identifier for current node"""
        
        import socket
        import os
        
        hostname = socket.gethostname()
        process_id = os.getpid()
        return f"{hostname}_{process_id}"
    
    def log_distributed_operation(self, operation_name, data, operation_config, engine=None, **kwargs):
        """Log distributed operation with node tracking"""
        
        # Add node information to context
        with self.logging_manager.context_manager.context(f"distributed_{operation_name}"):
            self.logging_manager.main_logger.info(f"Node {self.node_id} starting {operation_name}")
            
            # Log operation with engine selection
            result = self.logging_manager.log_operation(
                operation_name, data, operation_config, engine, **kwargs
            )
            
            self.logging_manager.main_logger.info(f"Node {self.node_id} completed {operation_name}")
            
            return result
    
    def log_cluster_metrics(self, cluster_info):
        """Log cluster-wide metrics and health information"""
        
        with self.logging_manager.context_manager.context("cluster_monitoring"):
            self.logging_manager.main_logger.info(f"Cluster metrics from node {self.node_id}")
            
            # Log cluster information
            for metric_name, metric_value in cluster_info.items():
                self.logging_manager.main_logger.info(f"Cluster metric - {metric_name}: {metric_value}")
            
            # Log performance metrics
            cluster_performance = self.logging_manager.performance_logger.get_cluster_metrics()
            self.logging_manager.main_logger.info(f"Cluster performance: {cluster_performance}")
    
    def log_data_distribution(self, data, distribution_config):
        """Log information about data distribution across cluster"""
        
        with self.logging_manager.context_manager.context("data_distribution"):
            self.logging_manager.main_logger.info(f"Data distribution analysis on node {self.node_id}")
            
            if hasattr(data, 'toPandas'):  # Spark DataFrame
                # Get partition information
                num_partitions = data.rdd.getNumPartitions()
                partition_sizes = data.rdd.mapPartitions(lambda x: [len(list(x))]).collect()
                
                self.logging_manager.main_logger.info(f"Number of partitions: {num_partitions}")
                self.logging_manager.main_logger.info(f"Partition sizes: {partition_sizes}")
                
                # Log data skew information
                avg_partition_size = sum(partition_sizes) / len(partition_sizes)
                max_partition_size = max(partition_sizes)
                skew_ratio = max_partition_size / avg_partition_size if avg_partition_size > 0 else 0
                
                self.logging_manager.main_logger.info(f"Data skew ratio: {skew_ratio:.2f}")
                
                if skew_ratio > 2.0:
                    self.logging_manager.main_logger.warning(f"High data skew detected: {skew_ratio:.2f}")
            
            else:  # Pandas DataFrame
                # For single-node Pandas, log basic information
                self.logging_manager.main_logger.info(f"Single-node Pandas DataFrame with {len(data)} rows")
    
    def log_engine_performance_comparison(self, data, operations, engines=["pandas", "spark"]):
        """Log performance comparison between different engines"""
        
        with self.logging_manager.context_manager.context("engine_performance"):
            self.logging_manager.main_logger.info(f"Performance comparison on node {self.node_id}")
            
            performance_results = {}
            
            for engine in engines:
                if engine == "spark" and not self.logging_manager.spark_available:
                    continue
                
                try:
                    # Measure performance for each engine
                    with self.logging_manager.performance_logger.measure_operation(f"performance_test_{engine}"):
                        if engine == "spark":
                            result = self._execute_with_spark(data, operations)
                        else:
                            result = self._execute_with_pandas(data, operations)
                    
                    # Get performance metrics
                    metrics = self.logging_manager.performance_logger.get_operation_metrics(f"performance_test_{engine}")
                    performance_results[engine] = metrics
                    
                    self.logging_manager.main_logger.info(f"{engine} engine performance: {metrics}")
                    
                except Exception as e:
                    self.logging_manager.main_logger.error(f"Error testing {engine} engine: {str(e)}")
                    performance_results[engine] = {"error": str(e)}
            
            # Log performance comparison summary
            self.logging_manager.main_logger.info(f"Performance comparison summary: {performance_results}")
            
            return performance_results
```

### 3. Multi-Engine Logging Context Management

```python
class MultiEngineLoggingContext:
    """Context manager for multi-engine logging operations"""
    
    def __init__(self, logging_manager):
        self.logging_manager = logging_manager
        self.logger = Logger("logging_context")
        self.active_contexts = []
    
    def __enter__(self):
        """Enter logging context"""
        
        # Create context stack
        context_info = {
            "timestamp": time.time(),
            "context_id": str(uuid.uuid4()),
            "engine": self.logging_manager.default_engine
        }
        
        self.active_contexts.append(context_info)
        
        # Log context entry
        self.logging_manager.main_logger.debug(f"Entered logging context: {context_info}")
        
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit logging context"""
        
        if self.active_contexts:
            context_info = self.active_contexts.pop()
            
            # Log context exit
            duration = time.time() - context_info["timestamp"]
            self.logging_manager.main_logger.debug(f"Exited logging context after {duration:.2f}s")
            
            # Log any exceptions
            if exc_type is not None:
                self.logging_manager.main_logger.error(f"Exception in context: {exc_type.__name__}: {exc_val}")
    
    def log_with_context(self, message, level=LogLevel.INFO, **context_data):
        """Log message with current context information"""
        
        # Get current context
        current_context = self.active_contexts[-1] if self.active_contexts else {}
        
        # Merge context data
        full_context = {**current_context, **context_data}
        
        # Log with context
        if level == LogLevel.DEBUG:
            self.logging_manager.main_logger.debug(f"[{full_context}] {message}")
        elif level == LogLevel.INFO:
            self.logging_manager.main_logger.info(f"[{full_context}] {message}")
        elif level == LogLevel.WARNING:
            self.logging_manager.main_logger.warning(f"[{full_context}] {message}")
        elif level == LogLevel.ERROR:
            self.logging_manager.main_logger.error(f"[{full_context}] {message}")
    
    def set_engine_context(self, engine):
        """Set engine context for current operation"""
        
        if self.active_contexts:
            self.active_contexts[-1]["engine"] = engine
            self.logging_manager.main_logger.debug(f"Set engine context to: {engine}")
    
    def add_custom_context(self, key, value):
        """Add custom context information"""
        
        if self.active_contexts:
            self.active_contexts[-1][key] = value
            self.logging_manager.main_logger.debug(f"Added context: {key} = {value}")
```

### 4. Multi-Engine Performance Monitoring

```python
class MultiEnginePerformanceMonitor:
    """Monitor performance across different engines"""
    
    def __init__(self, logging_manager):
        self.logging_manager = logging_manager
        self.logger = Logger("performance_monitor")
        self.performance_history = {}
    
    def monitor_engine_performance(self, operation_name, data, operation_config, engines=None):
        """Monitor performance across different engines"""
        
        if engines is None:
            engines = ["pandas"]
            if self.logging_manager.spark_available:
                engines.append("spark")
        
        performance_results = {}
        
        for engine in engines:
            try:
                # Measure performance for each engine
                with self.logging_manager.performance_logger.measure_operation(f"{operation_name}_{engine}"):
                    if engine == "spark":
                        result = self.logging_manager._execute_with_spark(data, operation_config)
                    else:
                        result = self.logging_manager._execute_with_pandas(data, operation_config)
                
                # Get performance metrics
                metrics = self.logging_manager.performance_logger.get_operation_metrics(f"{operation_name}_{engine}")
                performance_results[engine] = {
                    "metrics": metrics,
                    "result_size": self._get_result_size(result, engine),
                    "success": True
                }
                
                # Log performance information
                self.logging_manager.main_logger.info(f"{engine} engine performance for {operation_name}: {metrics}")
                
            except Exception as e:
                performance_results[engine] = {
                    "error": str(e),
                    "success": False
                }
                
                self.logging_manager.main_logger.error(f"Error with {engine} engine for {operation_name}: {str(e)}")
        
        # Store performance history
        self.performance_history[operation_name] = {
            "timestamp": time.time(),
            "results": performance_results
        }
        
        return performance_results
    
    def get_performance_trends(self, operation_name, time_window_hours=24):
        """Get performance trends for specific operation"""
        
        current_time = time.time()
        cutoff_time = current_time - (time_window_hours * 3600)
        
        # Filter performance history within time window
        recent_history = {
            timestamp: data for timestamp, data in self.performance_history.items()
            if timestamp >= cutoff_time and operation_name in data
        }
        
        if not recent_history:
            return {}
        
        # Calculate trends for each engine
        trends = {}
        
        for engine in ["pandas", "spark"]:
            engine_metrics = []
            timestamps = []
            
            for timestamp, data in recent_history.items():
                if operation_name in data and engine in data[operation_name]["results"]:
                    result = data[operation_name]["results"][engine]
                    if result.get("success") and "metrics" in result:
                        # Extract execution time
                        execution_time = result["metrics"].get("execution_time", 0)
                        engine_metrics.append(execution_time)
                        timestamps.append(timestamp)
            
            if len(engine_metrics) > 1:
                # Calculate trend
                trend_slope = self._calculate_trend_slope(timestamps, engine_metrics)
                trends[engine] = {
                    "trend_slope": trend_slope,
                    "trend_direction": "improving" if trend_slope < 0 else "degrading" if trend_slope > 0 else "stable",
                    "data_points": len(engine_metrics),
                    "average_performance": sum(engine_metrics) / len(engine_metrics)
                }
        
        return trends
    
    def _get_result_size(self, result, engine):
        """Get size of operation result"""
        
        if hasattr(result, 'toPandas'):  # Spark DataFrame
            return result.count()
        else:  # Pandas DataFrame
            return len(result)
    
    def _calculate_trend_slope(self, timestamps, values):
        """Calculate trend slope using simple linear regression"""
        
        if len(timestamps) < 2:
            return 0
        
        # Normalize timestamps to hours from first timestamp
        first_timestamp = min(timestamps)
        normalized_timestamps = [(t - first_timestamp) / 3600 for t in timestamps]
        
        # Calculate slope using least squares
        n = len(normalized_timestamps)
        sum_x = sum(normalized_timestamps)
        sum_y = sum(values)
        sum_xy = sum(x * y for x, y in zip(normalized_timestamps, values))
        sum_x2 = sum(x * x for x in normalized_timestamps)
        
        if n * sum_x2 - sum_x * sum_x == 0:
            return 0
        
        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x * sum_x)
        return slope
    
    def generate_performance_report(self, operation_name=None):
        """Generate comprehensive performance report"""
        
        if operation_name:
            # Generate report for specific operation
            return self._generate_operation_report(operation_name)
        else:
            # Generate overall performance report
            return self._generate_overall_report()
    
    def _generate_operation_report(self, operation_name):
        """Generate performance report for specific operation"""
        
        if operation_name not in self.performance_history:
            return {"error": f"No performance data for operation: {operation_name}"}
        
        operation_data = self.performance_history[operation_name]
        results = operation_data["results"]
        
        report = {
            "operation_name": operation_name,
            "timestamp": operation_data["timestamp"],
            "engines_tested": list(results.keys()),
            "performance_summary": {}
        }
        
        for engine, result in results.items():
            if result.get("success"):
                report["performance_summary"][engine] = {
                    "execution_time": result["metrics"].get("execution_time", "N/A"),
                    "memory_usage": result["metrics"].get("memory_usage", "N/A"),
                    "result_size": result["result_size"]
                }
            else:
                report["performance_summary"][engine] = {
                    "error": result.get("error", "Unknown error")
                }
        
        return report
    
    def _generate_overall_report(self):
        """Generate overall performance report"""
        
        if not self.performance_history:
            return {"error": "No performance data available"}
        
        report = {
            "total_operations": len(self.performance_history),
            "operations": list(self.performance_history.keys()),
            "overall_summary": {}
        }
        
        # Calculate overall statistics
        engine_stats = {}
        
        for operation_name, operation_data in self.performance_history.items():
            for engine, result in operation_data["results"].items():
                if engine not in engine_stats:
                    engine_stats[engine] = {
                        "total_operations": 0,
                        "successful_operations": 0,
                        "failed_operations": 0,
                        "total_execution_time": 0,
                        "total_result_size": 0
                    }
                
                engine_stats[engine]["total_operations"] += 1
                
                if result.get("success"):
                    engine_stats[engine]["successful_operations"] += 1
                    engine_stats[engine]["total_execution_time"] += result["metrics"].get("execution_time", 0)
                    engine_stats[engine]["total_result_size"] += result["result_size"]
                else:
                    engine_stats[engine]["failed_operations"] += 1
        
        # Calculate averages
        for engine, stats in engine_stats.items():
            if stats["successful_operations"] > 0:
                stats["average_execution_time"] = stats["total_execution_time"] / stats["successful_operations"]
                stats["average_result_size"] = stats["total_result_size"] / stats["successful_operations"]
                stats["success_rate"] = stats["successful_operations"] / stats["total_operations"]
            else:
                stats["average_execution_time"] = 0
                stats["average_result_size"] = 0
                stats["success_rate"] = 0
        
        report["overall_summary"] = engine_stats
        
        return report
```

## Integration Examples

### 1. Multi-Engine Logging Pipeline

```python
def create_multi_engine_logging_pipeline():
    """Create a complete multi-engine logging pipeline"""
    
    # Initialize logging manager
    logging_config = {
        "logger_name": "multi_engine_pipeline",
        "log_level": LogLevel.INFO,
        "output_format": "json",
        "performance_logger_name": "pipeline_monitor",
        "metrics_storage": "file"
    }
    
    logging_manager = MultiEngineLoggingManager(default_engine="auto", log_config=logging_config)
    
    # Create specialized loggers
    distributed_logger = MultiEngineDistributedLogger(logging_manager)
    performance_monitor = MultiEnginePerformanceMonitor(logging_manager)
    
    # Define sample data
    sample_data = create_sample_data()
    
    # Define operation configurations
    operations = {
        "data_cleaning": {
            "type": "data_processing",
            "complexity": "medium",
            "filters": ["value > 0", "status == 'active'"],
            "transformations": [
                {"column": "value", "operation": "cast", "new_type": "double"},
                {"column": "name", "operation": "cast", "new_type": "string"}
            ]
        },
        "data_aggregation": {
            "type": "aggregation",
            "complexity": "simple",
            "group_columns": ["category"],
            "aggregations": ["count", "sum", "avg"]
        },
        "data_transformation": {
            "type": "transformation",
            "complexity": "medium",
            "column_transformations": [
                {"column": "old_name", "operation": "rename", "new_name": "new_name"}
            ]
        }
    }
    
    # Execute operations with logging
    results = {}
    
    for operation_name, operation_config in operations.items():
        try:
            # Log operation with automatic engine selection
            result = logging_manager.log_operation(
                operation_name, sample_data, operation_config
            )
            
            results[operation_name] = {
                "status": "success",
                "result": result
            }
            
        except Exception as e:
            results[operation_name] = {
                "status": "failed",
                "error": str(e)
            }
    
    # Monitor performance across engines
    performance_results = performance_monitor.monitor_engine_performance(
        "comprehensive_test", sample_data, operations["data_cleaning"]
    )
    
    # Generate performance report
    performance_report = performance_monitor.generate_performance_report()
    
    return results, performance_results, performance_report

def create_sample_data():
    """Create sample data for testing"""
    
    import pandas as pd
    import numpy as np
    
    # Create sample DataFrame
    np.random.seed(42)
    n_rows = 10000
    
    data = pd.DataFrame({
        "id": range(1, n_rows + 1),
        "name": [f"Item_{i}" for i in range(1, n_rows + 1)],
        "value": np.random.uniform(0, 1000, n_rows),
        "category": np.random.choice(["A", "B", "C"], n_rows),
        "status": np.random.choice(["active", "inactive"], n_rows),
        "timestamp": pd.date_range("2023-01-01", periods=n_rows, freq="H")
    })
    
    return data

# Run the pipeline
logging_pipeline_results = create_multi_engine_logging_pipeline()
```

### 2. Real-time Logging Dashboard

```python
def create_logging_dashboard():
    """Create a dashboard to monitor logging and performance in real-time"""
    
    import dash
    from dash import dcc, html
    from dash.dependencies import Input, Output
    import plotly.graph_objs as go
    
    app = dash.Dash(__name__)
    
    app.layout = html.Div([
        html.H1("Multi-Engine Logging Dashboard"),
        
        html.Div([
            html.Div([
                html.Label("Log Level:"),
                dcc.Dropdown(
                    id="log-level-filter",
                    options=[
                        {"label": "All Levels", "value": "all"},
                        {"label": "Debug", "value": "debug"},
                        {"label": "Info", "value": "info"},
                        {"label": "Warning", "value": "warning"},
                        {"label": "Error", "value": "error"}
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
            dcc.Graph(id="log-volume-chart"),
            dcc.Graph(id="engine-performance-chart"),
            dcc.Graph(id="error-rate-chart")
        ]),
        
        dcc.Interval(id="update-interval", interval=30*1000)  # Update every 30 seconds
    ])
    
    @app.callback(
        [Output("log-volume-chart", "figure"),
         Output("engine-performance-chart", "figure"),
         Output("error-rate-chart", "figure")],
        [Input("update-interval", "n_intervals"),
         Input("log-level-filter", "value"),
         Input("engine-filter", "value"),
         Input("update-frequency", "value")]
    )
    def update_charts(n, log_level, engine, frequency):
        # Get logging data (this would come from your actual logging system)
        # For demonstration, we'll create sample data
        
        # Log volume chart
        time_points = list(range(24))  # Last 24 hours
        log_volumes = [np.random.randint(100, 1000) for _ in time_points]
        
        log_fig = go.Figure(data=[
            go.Scatter(x=time_points, y=log_volumes, mode="lines+markers", name="Log Volume")
        ])
        log_fig.update_layout(title="Log Volume Over Time", xaxis_title="Hours Ago", yaxis_title="Number of Logs")
        
        # Engine performance chart
        engines = ["pandas", "spark", "auto"]
        avg_execution_times = [2.1, 8.5, 4.2]  # seconds
        
        perf_fig = go.Figure(data=[
            go.Bar(x=engines, y=avg_execution_times, name="Average Execution Time")
        ])
        perf_fig.update_layout(title="Engine Performance Comparison", yaxis_title="Time (seconds)")
        
        # Error rate chart
        error_rates = [2.1, 1.8, 3.2, 2.9, 2.5, 2.8, 2.3]  # percentage
        
        error_fig = go.Figure(data=[
            go.Scatter(x=list(range(7)), y=error_rates, mode="lines+markers", name="Error Rate")
        ])
        error_fig.update_layout(title="Error Rate Trend", xaxis_title="Days Ago", yaxis_title="Error Rate (%)")
        
        return log_fig, perf_fig, error_fig
    
    return app

# Start the dashboard
logging_dashboard = create_logging_dashboard()
logging_dashboard.run_server(debug=True, port=8054)
```

## Best Practices

### 1. Engine Selection
- Use **Pandas** for data < 10MB and simple operations
- Use **Spark** for data > 100MB and complex operations
- Use **Auto-detection** for unknown data sizes and dynamic workloads
- Consider **operation complexity** when selecting engine

### 2. Performance Optimization
- **Cache frequently accessed data** in Spark
- **Use appropriate logging levels** for different environments
- **Implement structured logging** for better analysis
- **Monitor performance trends** and adjust engine selection

### 3. Logging Quality
- **Use consistent log formats** across all engines
- **Implement comprehensive error handling** and logging
- **Add context information** to all log entries
- **Monitor log volume** and performance impact

### 4. Error Handling
- **Implement fallback mechanisms** when engines fail
- **Provide meaningful error messages** for debugging
- **Log engine selection decisions** for transparency
- **Retry failed operations** with different engines when possible

## Troubleshooting

### Common Issues

1. **Engine Compatibility Issues**
   ```python
   # Check engine availability
   if logging_manager.spark_available:
       print("Spark is available for distributed logging")
   else:
       print("Using Pandas only")
   ```

2. **Performance Issues with Large Data**
   ```python
   # Use Spark for very large datasets
   if data_size_mb > 1000:
       engine = "spark"
   else:
       engine = "pandas"
   ```

3. **Log Volume Issues**
   ```python
   # Adjust log level based on environment
   if environment == "production":
       log_level = LogLevel.WARNING
   else:
       log_level = LogLevel.DEBUG
   ```

## Conclusion

The multi-engine logging capabilities in `siege_utilities` provide:

- **Seamless scalability** from single applications to distributed systems
- **Automatic engine selection** based on data characteristics
- **Unified logging interfaces** that work with both Spark and Pandas
- **Comprehensive performance monitoring** across all engines
- **Distributed logging** for cluster-wide visibility

By following this recipe, you can build robust, scalable logging systems that automatically adapt to your data sizes and processing requirements while providing comprehensive visibility into your operations.

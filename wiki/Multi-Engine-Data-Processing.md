# Multi-Engine Data Processing Recipe

## Overview
This recipe demonstrates how to use `siege_utilities` with both Apache Spark and Pandas engines, providing seamless scalability from small datasets to massive distributed processing. All recipes in the library support both engines through unified interfaces.

## Prerequisites
- Python 3.7+
- `siege_utilities` library installed
- Apache Spark (optional, for distributed processing)
- Basic understanding of both Pandas and Spark DataFrames

## Installation
```bash
pip install siege_utilities
pip install pyspark pandas numpy  # Core dependencies
```

## Core Multi-Engine Architecture

### 1. Engine Manager Class

```python
from siege_utilities.distributed.spark_utils import SparkUtils
from siege_utilities.core.logging import Logger

class MultiEngineManager:
    """Central manager for multi-engine operations"""
    
    def __init__(self, default_engine="auto", spark_config=None):
        self.default_engine = default_engine
        self.logger = Logger("multi_engine_manager")
        
        # Initialize Spark if needed
        if default_engine in ["spark", "auto"]:
            self.spark_utils = SparkUtils(spark_config)
            self.spark_available = True
        else:
            self.spark_utils = None
            self.spark_available = False
    
    def get_optimal_engine(self, data_size_mb=None, operation_complexity="medium"):
        """Automatically select the best engine for the task"""
        
        if data_size_mb is None:
            return "auto"
        
        # Engine selection logic
        if data_size_mb < 100 and operation_complexity == "simple":
            return "pandas"
        elif data_size_mb < 500 and operation_complexity == "medium":
            return "pandas"
        elif data_size_mb >= 500 or operation_complexity == "complex":
            return "spark" if self.spark_available else "pandas"
        else:
            return "auto"
    
    def convert_engine(self, data, target_engine, **kwargs):
        """Convert data between engines"""
        
        if target_engine == "spark" and self.spark_available:
            if hasattr(data, 'toPandas'):  # Already Spark DataFrame
                return data
            else:  # Convert from Pandas to Spark
                return self.spark_utils.convert_pandas_to_spark(data, **kwargs)
        
        elif target_engine == "pandas":
            if hasattr(data, 'toPandas'):  # Spark DataFrame
                return data.toPandas()
            else:  # Already Pandas
                return data
        
        else:
            raise ValueError(f"Unsupported target engine: {target_engine}")
```

### 2. Unified Data Loading Interface

```python
class UnifiedDataLoader:
    """Unified interface for loading data with any engine"""
    
    def __init__(self, engine_manager):
        self.engine_manager = engine_manager
    
    def load_data(self, data_source, engine=None, **kwargs):
        """Load data using specified or auto-detected engine"""
        
        engine = engine or self.engine_manager.default_engine
        
        if engine == "spark" and self.engine_manager.spark_available:
            return self._load_with_spark(data_source, **kwargs)
        elif engine == "pandas":
            return self._load_with_pandas(data_source, **kwargs)
        else:  # auto-detect
            return self._auto_detect_and_load(data_source, **kwargs)
    
    def _load_with_spark(self, data_source, **kwargs):
        """Load data using Spark"""
        
        if isinstance(data_source, str):
            if data_source.endswith('.parquet'):
                return self.engine_manager.spark_utils.read_parquet(data_source, **kwargs)
            elif data_source.endswith('.csv'):
                return self.engine_manager.spark_utils.read_csv(data_source, **kwargs)
            elif data_source.endswith('.json'):
                return self.engine_manager.spark_utils.read_json(data_source, **kwargs)
            elif data_source.endswith('.geojson'):
                return self.engine_manager.spark_utils.read_geojson(data_source, **kwargs)
            else:
                return self.engine_manager.spark_utils.read_file(data_source, **kwargs)
        else:
            return data_source
    
    def _load_with_pandas(self, data_source, **kwargs):
        """Load data using Pandas"""
        
        import pandas as pd
        import geopandas as gpd
        
        if isinstance(data_source, str):
            if data_source.endswith('.geojson'):
                return gpd.read_file(data_source, **kwargs)
            elif data_source.endswith('.parquet'):
                return pd.read_parquet(data_source, **kwargs)
            elif data_source.endswith('.csv'):
                return pd.read_csv(data_source, **kwargs)
            elif data_source.endswith('.json'):
                return pd.read_json(data_source, **kwargs)
            else:
                return pd.read_file(data_source, **kwargs)
        else:
            return data_source
    
    def _auto_detect_and_load(self, data_source, **kwargs):
        """Auto-detect best engine and load data"""
        
        try:
            # Try Pandas first for small data
            return self._load_with_pandas(data_source, **kwargs)
        except Exception as e:
            if self.engine_manager.spark_available:
                # Fall back to Spark for large data
                return self._load_with_spark(data_source, **kwargs)
            else:
                raise e
```

### 3. Engine-Agnostic Data Operations

```python
class EngineAgnosticOperations:
    """Common operations that work with both engines"""
    
    def __init__(self, engine_manager):
        self.engine_manager = engine_manager
    
    def filter_data(self, data, condition, engine=None):
        """Filter data using any engine"""
        
        engine = engine or self._detect_engine(data)
        
        if engine == "spark":
            return data.filter(condition)
        else:
            return data.query(condition)
    
    def group_by(self, data, columns, aggregations, engine=None):
        """Group by operations with any engine"""
        
        engine = engine or self._detect_engine(data)
        
        if engine == "spark":
            return data.groupBy(columns).agg(*aggregations)
        else:
            return data.groupby(columns).agg(aggregations)
    
    def join_data(self, data1, data2, on_columns, how="inner", engine=None):
        """Join data using any engine"""
        
        engine = engine or self._detect_engine(data1)
        
        if engine == "spark":
            return data1.join(data2, on_columns, how)
        else:
            return data1.merge(data2, on=on_columns, how=how)
    
    def sort_data(self, data, columns, ascending=True, engine=None):
        """Sort data using any engine"""
        
        engine = engine or self._detect_engine(data)
        
        if engine == "spark":
            return data.orderBy(columns, ascending=ascending)
        else:
            return data.sort_values(columns, ascending=ascending)
    
    def _detect_engine(self, data):
        """Detect the engine of the data"""
        
        if hasattr(data, 'toPandas'):
            return "spark"
        else:
            return "pandas"
```

## Multi-Engine Data Processing Patterns

### 1. Batch Processing with Engine Selection

```python
class MultiEngineBatchProcessor:
    """Batch processing that automatically selects optimal engine"""
    
    def __init__(self, engine_manager):
        self.engine_manager = engine_manager
        self.data_loader = UnifiedDataLoader(engine_manager)
        self.operations = EngineAgnosticOperations(engine_manager)
    
    def process_batch(self, data_sources, operations, output_format="parquet"):
        """Process multiple data sources with optimal engine selection"""
        
        results = {}
        
        for source_name, data_source in data_sources.items():
            # Determine optimal engine
            optimal_engine = self.engine_manager.get_optimal_engine(
                data_size_mb=self._estimate_data_size(data_source),
                operation_complexity=self._assess_complexity(operations)
            )
            
            self.engine_manager.logger.info(
                f"Processing {source_name} with {optimal_engine} engine"
            )
            
            # Load data
            data = self.data_loader.load_data(data_source, engine=optimal_engine)
            
            # Apply operations
            processed_data = self._apply_operations(data, operations, optimal_engine)
            
            # Save results
            output_path = f"output/{source_name}_processed.{output_format}"
            self._save_data(processed_data, output_path, optimal_engine)
            
            results[source_name] = {
                "engine_used": optimal_engine,
                "output_path": output_path,
                "record_count": self._get_record_count(processed_data, optimal_engine)
            }
        
        return results
    
    def _apply_operations(self, data, operations, engine):
        """Apply processing operations using specified engine"""
        
        for operation in operations:
            op_type = operation.get("type")
            params = operation.get("params", {})
            
            if op_type == "filter":
                data = self.operations.filter_data(data, params["condition"], engine)
            elif op_type == "group_by":
                data = self.operations.group_by(data, params["columns"], params["aggregations"], engine)
            elif op_type == "join":
                data = self.operations.join_data(data, params["other_data"], params["on"], params.get("how", "inner"), engine)
            elif op_type == "sort":
                data = self.operations.sort_data(data, params["columns"], params.get("ascending", True), engine)
        
        return data
    
    def _save_data(self, data, output_path, engine):
        """Save data using specified engine"""
        
        if engine == "spark":
            if output_path.endswith('.parquet'):
                data.write.parquet(output_path)
            elif output_path.endswith('.csv'):
                data.write.csv(output_path, header=True)
            else:
                data.write.format("parquet").save(output_path)
        else:
            if output_path.endswith('.parquet'):
                data.to_parquet(output_path)
            elif output_path.endswith('.csv'):
                data.to_csv(output_path, index=False)
            else:
                data.to_parquet(output_path)
    
    def _get_record_count(self, data, engine):
        """Get record count from any engine"""
        
        if engine == "spark":
            return data.count()
        else:
            return len(data)
    
    def _estimate_data_size(self, data_source):
        """Estimate data size in MB"""
        
        try:
            import os
            return os.path.getsize(data_source) / (1024 * 1024)
        except:
            return 100  # Default assumption
    
    def _assess_complexity(self, operations):
        """Assess operation complexity"""
        
        complexity_scores = {
            "filter": 1,
            "sort": 2,
            "group_by": 3,
            "join": 4
        }
        
        total_score = sum(complexity_scores.get(op["type"], 1) for op in operations)
        
        if total_score <= 3:
            return "simple"
        elif total_score <= 6:
            return "medium"
        else:
            return "complex"
```

### 2. Real-time Processing with Engine Switching

```python
class MultiEngineRealTimeProcessor:
    """Real-time processing with dynamic engine switching"""
    
    def __init__(self, engine_manager):
        self.engine_manager = engine_manager
        self.current_engine = "pandas"
        self.performance_metrics = {}
    
    def process_stream(self, data_stream, processing_config):
        """Process streaming data with adaptive engine selection"""
        
        for batch in data_stream:
            # Assess batch characteristics
            batch_size = len(batch) if hasattr(batch, '__len__') else 1000
            complexity = self._assess_batch_complexity(batch, processing_config)
            
            # Select optimal engine for this batch
            optimal_engine = self._select_engine_for_batch(batch_size, complexity)
            
            # Switch engine if needed
            if optimal_engine != self.current_engine:
                self._switch_engine(optimal_engine)
            
            # Process batch
            start_time = time.time()
            processed_batch = self._process_batch(batch, processing_config, optimal_engine)
            processing_time = time.time() - start_time
            
            # Update performance metrics
            self._update_performance_metrics(optimal_engine, batch_size, processing_time)
            
            # Yield processed results
            yield processed_batch
    
    def _select_engine_for_batch(self, batch_size, complexity):
        """Select optimal engine for a specific batch"""
        
        # Dynamic engine selection based on batch characteristics
        if batch_size < 1000 and complexity == "simple":
            return "pandas"
        elif batch_size < 10000 and complexity == "medium":
            return "pandas"
        else:
            return "spark" if self.engine_manager.spark_available else "pandas"
    
    def _switch_engine(self, new_engine):
        """Switch processing engine"""
        
        if new_engine != self.current_engine:
            self.engine_manager.logger.info(f"Switching engine from {self.current_engine} to {new_engine}")
            self.current_engine = new_engine
    
    def _process_batch(self, batch, config, engine):
        """Process a single batch with specified engine"""
        
        # Convert batch to appropriate engine format
        if engine == "spark" and not hasattr(batch, 'toPandas'):
            batch = self.engine_manager.convert_engine(batch, "spark")
        elif engine == "pandas" and hasattr(batch, 'toPandas'):
            batch = batch.toPandas()
        
        # Apply processing operations
        operations = EngineAgnosticOperations(self.engine_manager)
        
        for operation in config["operations"]:
            batch = operations._apply_operations(batch, [operation], engine)
        
        return batch
    
    def _update_performance_metrics(self, engine, batch_size, processing_time):
        """Update performance tracking metrics"""
        
        if engine not in self.performance_metrics:
            self.performance_metrics[engine] = []
        
        self.performance_metrics[engine].append({
            "batch_size": batch_size,
            "processing_time": processing_time,
            "throughput": batch_size / processing_time,
            "timestamp": time.time()
        })
    
    def get_performance_summary(self):
        """Get performance summary across all engines"""
        
        summary = {}
        
        for engine, metrics in self.performance_metrics.items():
            if metrics:
                avg_throughput = sum(m["throughput"] for m in metrics) / len(metrics)
                total_batches = len(metrics)
                avg_batch_size = sum(m["batch_size"] for m in metrics) / len(metrics)
                
                summary[engine] = {
                    "total_batches": total_batches,
                    "average_throughput": avg_throughput,
                    "average_batch_size": avg_batch_size,
                    "total_processing_time": sum(m["processing_time"] for m in metrics)
                }
        
        return summary
```

### 3. Hybrid Processing (Spark + Pandas)

```python
class HybridProcessor:
    """Process data using both engines for optimal performance"""
    
    def __init__(self, engine_manager):
        self.engine_manager = engine_manager
    
    def hybrid_process(self, data_source, processing_pipeline):
        """Use both engines for different stages of processing"""
        
        # Stage 1: Load and preprocess with Spark (if large)
        if self._should_use_spark_for_loading(data_source):
            data = self.engine_manager.spark_utils.load_large_data(data_source)
            data = self._preprocess_with_spark(data, processing_pipeline["preprocessing"])
        else:
            data = self.engine_manager.data_loader.load_data(data_source, "pandas")
            data = self._preprocess_with_pandas(data, processing_pipeline["preprocessing"])
        
        # Stage 2: Complex transformations with Spark
        if processing_pipeline.get("use_spark_for_transformations", False):
            data = self._transform_with_spark(data, processing_pipeline["transformations"])
        
        # Stage 3: Final processing and output with Pandas
        if hasattr(data, 'toPandas'):
            data = data.toPandas()
        
        data = self._finalize_with_pandas(data, processing_pipeline["finalization"])
        
        return data
    
    def _should_use_spark_for_loading(self, data_source):
        """Determine if Spark should be used for data loading"""
        
        try:
            import os
            size_mb = os.path.getsize(data_source) / (1024 * 1024)
            return size_mb > 500  # Use Spark for files > 500MB
        except:
            return False
    
    def _preprocess_with_spark(self, data, preprocessing_config):
        """Apply preprocessing operations with Spark"""
        
        for operation in preprocessing_config:
            if operation["type"] == "filter":
                data = data.filter(operation["condition"])
            elif operation["type"] == "select":
                data = data.select(operation["columns"])
            elif operation["type"] == "drop_duplicates":
                data = data.dropDuplicates(operation.get("subset"))
        
        return data
    
    def _preprocess_with_pandas(self, data, preprocessing_config):
        """Apply preprocessing operations with Pandas"""
        
        for operation in preprocessing_config:
            if operation["type"] == "filter":
                data = data.query(operation["condition"])
            elif operation["type"] == "select":
                data = data[operation["columns"]]
            elif operation["type"] == "drop_duplicates":
                data = data.drop_duplicates(subset=operation.get("subset"))
        
        return data
    
    def _transform_with_spark(self, data, transformations):
        """Apply complex transformations with Spark"""
        
        for transformation in transformations:
            if transformation["type"] == "window_function":
                from pyspark.sql.window import Window
                from pyspark.sql.functions import rank, row_number
                
                window_spec = Window.partitionBy(transformation["partition_by"]).orderBy(transformation["order_by"])
                
                if transformation["function"] == "rank":
                    data = data.withColumn(transformation["output_column"], rank().over(window_spec))
                elif transformation["function"] == "row_number":
                    data = data.withColumn(transformation["output_column"], row_number().over(window_spec))
            
            elif transformation["type"] == "udf":
                # Apply custom UDF
                data = data.withColumn(transformation["output_column"], transformation["udf"](*transformation["input_columns"]))
        
        return data
    
    def _finalize_with_pandas(self, data, finalization_config):
        """Apply final processing with Pandas"""
        
        for operation in finalization_config:
            if operation["type"] == "sort":
                data = data.sort_values(operation["columns"], ascending=operation.get("ascending", True))
            elif operation["type"] == "reset_index":
                data = data.reset_index(drop=operation.get("drop", True))
            elif operation["type"] == "custom_function":
                data = operation["function"](data)
        
        return data
```

## Integration Examples

### 1. Multi-Engine Data Pipeline

```python
def create_multi_engine_pipeline():
    """Create a complete multi-engine data processing pipeline"""
    
    # Initialize engine manager
    engine_manager = MultiEngineManager(default_engine="auto")
    
    # Create processors
    batch_processor = MultiEngineBatchProcessor(engine_manager)
    real_time_processor = MultiEngineRealTimeProcessor(engine_manager)
    hybrid_processor = HybridProcessor(engine_manager)
    
    # Define data sources
    data_sources = {
        "user_activity": "data/user_activity_large.parquet",
        "product_catalog": "data/product_catalog.csv",
        "geographic_data": "data/geographic_boundaries.geojson"
    }
    
    # Define processing operations
    operations = [
        {"type": "filter", "params": {"condition": "status == 'active'"}},
        {"type": "group_by", "params": {"columns": ["category"], "aggregations": ["count", "sum"]}},
        {"type": "join", "params": {"other_data": "product_data", "on": "product_id"}}
    ]
    
    # Process data with optimal engine selection
    results = batch_processor.process_batch(data_sources, operations)
    
    # Create real-time processing stream
    real_time_results = real_time_processor.process_stream(
        data_stream=create_data_stream(),
        processing_config={"operations": operations}
    )
    
    # Use hybrid processing for complex workflows
    hybrid_results = hybrid_processor.hybrid_process(
        data_source="data/complex_dataset.parquet",
        processing_pipeline={
            "preprocessing": [
                {"type": "filter", "condition": "value > 0"},
                {"type": "select", "columns": ["id", "value", "category"]}
            ],
            "use_spark_for_transformations": True,
            "transformations": [
                {
                    "type": "window_function",
                    "function": "rank",
                    "partition_by": ["category"],
                    "order_by": ["value"],
                    "output_column": "rank"
                }
            ],
            "finalization": [
                {"type": "sort", "columns": ["rank"]},
                {"type": "reset_index", "drop": True}
            ]
        }
    )
    
    return results, real_time_results, hybrid_results

def create_data_stream():
    """Create a sample data stream for demonstration"""
    
    import pandas as pd
    import time
    
    while True:
        # Generate sample data
        data = pd.DataFrame({
            "timestamp": [time.time()],
            "user_id": [f"user_{int(time.time()) % 1000}"],
            "action": ["click"],
            "value": [int(time.time()) % 100]
        })
        
        yield data
        time.sleep(1)  # Simulate real-time data

# Run the pipeline
pipeline_results = create_multi_engine_pipeline()
```

### 2. Performance Monitoring Dashboard

```python
def create_performance_dashboard():
    """Create a dashboard to monitor multi-engine performance"""
    
    import dash
    from dash import dcc, html
    from dash.dependencies import Input, Output
    import plotly.graph_objs as go
    
    app = dash.Dash(__name__)
    
    app.layout = html.Div([
        html.H1("Multi-Engine Performance Dashboard"),
        
        html.Div([
            dcc.Graph(id="throughput-chart"),
            dcc.Graph(id="engine-usage-chart"),
            dcc.Interval(id="update-interval", interval=5000)
        ])
    ])
    
    @app.callback(
        [Output("throughput-chart", "figure"),
         Output("engine-usage-chart", "figure")],
        Input("update-interval", "n_intervals")
    )
    def update_charts(n):
        # Get performance data
        engine_manager = MultiEngineManager()
        real_time_processor = MultiEngineRealTimeProcessor(engine_manager)
        performance_summary = real_time_processor.get_performance_summary()
        
        # Create throughput chart
        throughput_fig = go.Figure()
        for engine, metrics in performance_summary.items():
            throughput_fig.add_trace(go.Bar(
                x=[engine],
                y=[metrics["average_throughput"]],
                name=engine
            ))
        
        throughput_fig.update_layout(title="Average Throughput by Engine")
        
        # Create engine usage chart
        usage_fig = go.Figure()
        engines = list(performance_summary.keys())
        batch_counts = [performance_summary[engine]["total_batches"] for engine in engines]
        
        usage_fig.add_trace(go.Pie(
            labels=engines,
            values=batch_counts,
            name="Batch Distribution"
        ))
        
        usage_fig.update_layout(title="Engine Usage Distribution")
        
        return throughput_fig, usage_fig
    
    return app

# Start the dashboard
performance_dashboard = create_performance_dashboard()
performance_dashboard.run_server(debug=True, port=8051)
```

## Best Practices

### 1. Engine Selection
- Use **Pandas** for small datasets (< 100MB) and simple operations
- Use **Spark** for large datasets (> 500MB) and complex transformations
- Use **Auto-detection** for unknown data sizes and dynamic workloads
- Use **Hybrid processing** for complex pipelines with multiple stages

### 2. Performance Optimization
- **Cache frequently used data** in Spark
- **Use appropriate partitioning** for large datasets
- **Monitor performance metrics** and adjust engine selection
- **Batch operations** when possible to reduce overhead

### 3. Data Management
- **Use appropriate file formats** (Parquet for large data, CSV for small data)
- **Implement data validation** at both engine levels
- **Handle missing data** consistently across engines
- **Use schema evolution** for changing data structures

### 4. Error Handling
- **Implement fallback mechanisms** when engines fail
- **Log engine selection decisions** for debugging
- **Handle data type mismatches** between engines
- **Provide meaningful error messages** for users

## Troubleshooting

### Common Issues

1. **Engine Compatibility Issues**
   ```python
   # Check engine availability
   if engine_manager.spark_available:
       print("Spark is available")
   else:
       print("Using Pandas only")
   ```

2. **Performance Degradation**
   ```python
   # Benchmark different engines
   performance_results = benchmark_engines(data_source, operations)
   print(f"Best engine: {performance_results.idxmin()['total_time']}")
   ```

3. **Memory Issues**
   ```python
   # Use data sampling for large datasets
   if data_size_mb > 1000:
       data = data.sample(fraction=0.1, seed=42)
   ```

## Conclusion

The multi-engine data processing capabilities in `siege_utilities` provide:

- **Seamless scalability** from small to massive datasets
- **Automatic engine selection** based on data characteristics
- **Unified interfaces** that work with both Spark and Pandas
- **Performance optimization** through intelligent engine switching
- **Hybrid processing** for complex workflows

By following this recipe, you can build robust, scalable data processing pipelines that automatically adapt to your data size and processing requirements.

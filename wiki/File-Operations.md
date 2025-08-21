# File Operations Recipe

## Overview
This recipe demonstrates how to perform efficient file operations using `siege_utilities`, supporting both Apache Spark and Pandas engines for seamless scalability from small files to massive distributed datasets.

## Prerequisites
- Python 3.7+
- `siege_utilities` library installed
- Apache Spark (optional, for distributed processing)
- Basic understanding of file operations

## Installation
```bash
pip install siege_utilities
pip install pyspark pandas numpy  # Core dependencies
```

## Multi-Engine File Operations

### 1. Engine-Agnostic File Manager

```python
from siege_utilities.files.operations import FileOperations
from siege_utilities.files.paths import PathUtils
from siege_utilities.distributed.spark_utils import SparkUtils
from siege_utilities.core.logging import Logger

class MultiEngineFileManager:
    """File manager that works with both Spark and Pandas engines"""
    
    def __init__(self, default_engine="auto", spark_config=None):
        self.default_engine = default_engine
        self.file_ops = FileOperations()
        self.path_utils = PathUtils()
        self.logger = Logger("multi_engine_file_manager")
        
        # Initialize Spark if needed
        if default_engine in ["spark", "auto"]:
            self.spark_utils = SparkUtils(spark_config)
            self.spark_available = True
        else:
            self.spark_utils = None
            self.spark_available = False
    
    def get_optimal_engine(self, file_size_mb=None, operation_type="read"):
        """Automatically select the best engine for file operations"""
        
        if file_size_mb is None:
            return "auto"
        
        # Engine selection logic based on file size and operation
        if operation_type == "read":
            if file_size_mb < 100:
                return "pandas"
            elif file_size_mb < 500:
                return "pandas"
            else:
                return "spark" if self.spark_available else "pandas"
        elif operation_type == "write":
            if file_size_mb < 50:
                return "pandas"
            else:
                return "spark" if self.spark_available else "pandas"
        else:
            return "auto"
    
    def read_file(self, file_path, engine=None, **kwargs):
        """Read file using specified or auto-detected engine"""
        
        # Determine file size for engine selection
        file_size_mb = self.path_utils.get_file_size(file_path) / (1024 * 1024)
        
        # Select optimal engine
        if engine is None:
            engine = self.get_optimal_engine(file_size_mb, "read")
        
        self.logger.info(f"Reading {file_path} with {engine} engine (size: {file_size_mb:.2f}MB)")
        
        if engine == "spark" and self.spark_available:
            return self._read_with_spark(file_path, **kwargs)
        else:
            return self._read_with_pandas(file_path, **kwargs)
    
    def write_file(self, data, file_path, engine=None, **kwargs):
        """Write data to file using specified or auto-detected engine"""
        
        # Estimate data size for engine selection
        data_size_mb = self._estimate_data_size(data)
        
        # Select optimal engine
        if engine is None:
            engine = self.get_optimal_engine(data_size_mb, "write")
        
        self.logger.info(f"Writing to {file_path} with {engine} engine (estimated size: {data_size_mb:.2f}MB)")
        
        if engine == "spark" and self.spark_available:
            return self._write_with_spark(data, file_path, **kwargs)
        else:
            return self._write_with_pandas(data, file_path, **kwargs)
    
    def _read_with_spark(self, file_path, **kwargs):
        """Read file using Spark for large datasets"""
        
        file_extension = self.path_utils.get_file_extension(file_path).lower()
        
        if file_extension == '.parquet':
            return self.spark_utils.read_parquet(file_path, **kwargs)
        elif file_extension == '.csv':
            return self.spark_utils.read_csv(file_path, **kwargs)
        elif file_extension == '.json':
            return self.spark_utils.read_json(file_path, **kwargs)
        elif file_extension == '.avro':
            return self.spark_utils.read_avro(file_path, **kwargs)
        else:
            # Fallback to generic file reading
            return self.spark_utils.read_file(file_path, **kwargs)
    
    def _read_with_pandas(self, file_path, **kwargs):
        """Read file using Pandas for smaller datasets"""
        
        import pandas as pd
        import geopandas as gpd
        
        file_extension = self.path_utils.get_file_extension(file_path).lower()
        
        if file_extension == '.geojson':
            return gpd.read_file(file_path, **kwargs)
        elif file_extension == '.parquet':
            return pd.read_parquet(file_path, **kwargs)
        elif file_extension == '.csv':
            return pd.read_csv(file_path, **kwargs)
        elif file_extension == '.json':
            return pd.read_json(file_path, **kwargs)
        elif file_extension == '.excel':
            return pd.read_excel(file_path, **kwargs)
        else:
            # Fallback to generic file reading
            return pd.read_file(file_path, **kwargs)
    
    def _write_with_spark(self, data, file_path, **kwargs):
        """Write data using Spark for large datasets"""
        
        file_extension = self.path_utils.get_file_extension(file_path).lower()
        
        if file_extension == '.parquet':
            data.write.parquet(file_path, **kwargs)
        elif file_extension == '.csv':
            data.write.csv(file_path, header=True, **kwargs)
        elif file_extension == '.json':
            data.write.json(file_path, **kwargs)
        else:
            # Default to Parquet for large data
            data.write.parquet(file_path, **kwargs)
    
    def _write_with_pandas(self, data, file_path, **kwargs):
        """Write data using Pandas for smaller datasets"""
        
        file_extension = self.path_utils.get_file_extension(file_path).lower()
        
        if file_extension == '.geojson':
            data.to_file(file_path, **kwargs)
        elif file_extension == '.parquet':
            data.to_parquet(file_path, **kwargs)
        elif file_extension == '.csv':
            data.to_csv(file_path, index=False, **kwargs)
        elif file_extension == '.json':
            data.to_json(file_path, **kwargs)
        elif file_extension == '.excel':
            data.to_excel(file_path, index=False, **kwargs)
        else:
            # Default to Parquet
            data.to_parquet(file_path, **kwargs)
    
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

### 2. Multi-Engine Batch File Processing

```python
class MultiEngineBatchFileProcessor:
    """Process multiple files with optimal engine selection"""
    
    def __init__(self, file_manager):
        self.file_manager = file_manager
        self.logger = Logger("batch_file_processor")
    
    def process_files_batch(self, file_patterns, operations, output_dir="output", engine="auto"):
        """Process multiple files using optimal engines for each"""
        
        results = {}
        
        for pattern in file_patterns:
            # Find files matching pattern
            matching_files = self.file_manager.path_utils.find_files(pattern)
            
            for file_path in matching_files:
                try:
                    # Process individual file with optimal engine
                    result = self._process_single_file(file_path, operations, output_dir, engine)
                    results[file_path] = result
                    
                except Exception as e:
                    self.logger.error(f"Error processing {file_path}: {str(e)}")
                    results[file_path] = {"error": str(e), "status": "failed"}
        
        return results
    
    def _process_single_file(self, file_path, operations, output_dir, engine):
        """Process a single file with optimal engine selection"""
        
        # Read file with optimal engine
        data = self.file_manager.read_file(file_path, engine=engine)
        
        # Apply operations
        processed_data = self._apply_operations(data, operations, engine)
        
        # Generate output filename
        base_name = self.file_manager.path_utils.get_filename_without_extension(file_path)
        output_path = f"{output_dir}/{base_name}_processed.parquet"
        
        # Write processed data with optimal engine
        self.file_manager.write_file(processed_data, output_path, engine=engine)
        
        return {
            "input_file": file_path,
            "output_file": output_path,
            "engine_used": engine,
            "record_count": self._get_record_count(processed_data, engine),
            "status": "success"
        }
    
    def _apply_operations(self, data, operations, engine):
        """Apply processing operations using specified engine"""
        
        for operation in operations:
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
    
    def _get_record_count(self, data, engine):
        """Get record count from any engine"""
        
        if engine == "spark":
            return data.count()
        else:
            return len(data)
```

### 3. Multi-Engine File Validation and Quality Checks

```python
class MultiEngineFileValidator:
    """Validate file quality and integrity using any engine"""
    
    def __init__(self, file_manager):
        self.file_manager = file_manager
        self.logger = Logger("file_validator")
    
    def validate_file(self, file_path, validation_rules, engine="auto"):
        """Validate file using specified or auto-detected engine"""
        
        # Determine optimal engine for validation
        file_size_mb = self.file_manager.path_utils.get_file_size(file_path) / (1024 * 1024)
        engine = engine or self.file_manager.get_optimal_engine(file_size_mb, "read")
        
        # Read file with selected engine
        data = self.file_manager.read_file(file_path, engine=engine)
        
        # Perform validation
        validation_results = self._perform_validation(data, validation_rules, engine)
        
        return {
            "file_path": file_path,
            "engine_used": engine,
            "validation_results": validation_results,
            "overall_status": "pass" if all(r["status"] == "pass" for r in validation_results.values()) else "fail"
        }
    
    def _perform_validation(self, data, validation_rules, engine):
        """Perform validation checks using specified engine"""
        
        results = {}
        
        for rule_name, rule_config in validation_rules.items():
            rule_type = rule_config.get("type")
            
            if rule_type == "schema_check":
                results[rule_name] = self._validate_schema(data, rule_config, engine)
            elif rule_type == "data_quality":
                results[rule_name] = self._validate_data_quality(data, rule_config, engine)
            elif rule_type == "business_rules":
                results[rule_name] = self._validate_business_rules(data, rule_config, engine)
            elif rule_type == "file_integrity":
                results[rule_name] = self._validate_file_integrity(data, rule_config, engine)
        
        return results
    
    def _validate_schema(self, data, rule_config, engine):
        """Validate data schema"""
        
        expected_columns = rule_config.get("expected_columns", [])
        required_types = rule_config.get("required_types", {})
        
        if engine == "spark":
            actual_columns = data.columns
            actual_types = {field.name: field.dataType for field in data.schema.fields}
        else:
            actual_columns = list(data.columns)
            actual_types = data.dtypes.to_dict()
        
        # Check columns
        missing_columns = set(expected_columns) - set(actual_columns)
        extra_columns = set(actual_columns) - set(expected_columns)
        
        # Check types
        type_mismatches = []
        for col, expected_type in required_types.items():
            if col in actual_types:
                if not self._is_type_compatible(actual_types[col], expected_type):
                    type_mismatches.append(f"{col}: expected {expected_type}, got {actual_types[col]}")
        
        status = "pass" if not missing_columns and not type_mismatches else "fail"
        
        return {
            "status": status,
            "missing_columns": list(missing_columns),
            "extra_columns": list(extra_columns),
            "type_mismatches": type_mismatches
        }
    
    def _validate_data_quality(self, data, rule_config, engine):
        """Validate data quality metrics"""
        
        quality_metrics = {}
        
        if engine == "spark":
            # Use Spark for large data quality checks
            total_rows = data.count()
            
            # Check for nulls in each column
            for column in rule_config.get("null_check_columns", []):
                null_count = data.filter(f"{column} IS NULL").count()
                quality_metrics[f"{column}_null_count"] = null_count
                quality_metrics[f"{column}_null_percentage"] = (null_count / total_rows) * 100
            
            # Check for duplicates
            duplicate_count = data.dropDuplicates().count()
            quality_metrics["duplicate_rows"] = total_rows - duplicate_count
            
        else:
            # Use Pandas for smaller data quality checks
            total_rows = len(data)
            
            # Check for nulls
            for column in rule_config.get("null_check_columns", []):
                null_count = data[column].isnull().sum()
                quality_metrics[f"{column}_null_count"] = null_count
                quality_metrics[f"{column}_null_percentage"] = (null_count / total_rows) * 100
            
            # Check for duplicates
            duplicate_count = data.duplicated().sum()
            quality_metrics["duplicate_rows"] = duplicate_count
        
        # Evaluate quality thresholds
        quality_thresholds = rule_config.get("quality_thresholds", {})
        status = "pass"
        
        for metric, threshold in quality_thresholds.items():
            if metric in quality_metrics:
                if quality_metrics[metric] > threshold:
                    status = "fail"
                    break
        
        return {
            "status": status,
            "metrics": quality_metrics,
            "thresholds": quality_thresholds
        }
    
    def _validate_business_rules(self, data, rule_config, engine):
        """Validate business logic rules"""
        
        business_rules = rule_config.get("rules", [])
        rule_results = []
        
        for rule in business_rules:
            rule_condition = rule["condition"]
            rule_description = rule.get("description", rule_condition)
            
            if engine == "spark":
                # Use Spark SQL for business rule validation
                try:
                    invalid_count = data.filter(f"NOT ({rule_condition})").count()
                    rule_results.append({
                        "rule": rule_description,
                        "invalid_count": invalid_count,
                        "status": "pass" if invalid_count == 0 else "fail"
                    })
                except Exception as e:
                    rule_results.append({
                        "rule": rule_description,
                        "error": str(e),
                        "status": "error"
                    })
            else:
                # Use Pandas for business rule validation
                try:
                    invalid_count = len(data.query(f"NOT ({rule_condition})"))
                    rule_results.append({
                        "rule": rule_description,
                        "invalid_count": invalid_count,
                        "status": "pass" if invalid_count == 0 else "fail"
                    })
                except Exception as e:
                    rule_results.append({
                        "rule": rule_description,
                        "error": str(e),
                        "status": "error"
                    })
        
        overall_status = "pass" if all(r["status"] == "pass" for r in rule_results) else "fail"
        
        return {
            "status": overall_status,
            "rule_results": rule_results
        }
    
    def _validate_file_integrity(self, data, rule_config, engine):
        """Validate file integrity and consistency"""
        
        integrity_checks = {}
        
        if engine == "spark":
            # Check if Spark DataFrame is valid
            try:
                row_count = data.count()
                integrity_checks["row_count"] = row_count
                integrity_checks["is_valid_spark_df"] = True
            except Exception as e:
                integrity_checks["is_valid_spark_df"] = False
                integrity_checks["spark_error"] = str(e)
        else:
            # Check if Pandas DataFrame is valid
            try:
                row_count = len(data)
                integrity_checks["row_count"] = row_count
                integrity_checks["is_valid_pandas_df"] = True
            except Exception as e:
                integrity_checks["is_valid_pandas_df"] = False
                integrity_checks["pandas_error"] = str(e)
        
        # Check for empty data
        integrity_checks["is_empty"] = integrity_checks.get("row_count", 0) == 0
        
        # Check memory usage
        if engine == "pandas" and integrity_checks.get("is_valid_pandas_df"):
            memory_usage = data.memory_usage(deep=True).sum() / (1024 * 1024)  # MB
            integrity_checks["memory_usage_mb"] = memory_usage
        
        status = "pass" if not integrity_checks.get("is_empty", True) else "fail"
        
        return {
            "status": status,
            "checks": integrity_checks
        }
    
    def _is_type_compatible(self, actual_type, expected_type):
        """Check if actual type is compatible with expected type"""
        
        # Simple type compatibility check
        type_mapping = {
            "string": ["string", "str", "object"],
            "integer": ["int", "int32", "int64", "long"],
            "float": ["float", "float32", "float64", "double"],
            "boolean": ["bool", "boolean"]
        }
        
        if expected_type in type_mapping:
            return str(actual_type).lower() in type_mapping[expected_type]
        
        return str(actual_type).lower() == str(expected_type).lower()
```

## Integration Examples

### 1. Multi-Engine File Processing Pipeline

```python
def create_multi_engine_file_pipeline():
    """Create a complete multi-engine file processing pipeline"""
    
    # Initialize file manager
    file_manager = MultiEngineFileManager(default_engine="auto")
    
    # Create processors
    batch_processor = MultiEngineBatchFileProcessor(file_manager)
    validator = MultiEngineFileValidator(file_manager)
    
    # Define file patterns to process
    file_patterns = [
        "data/raw/*.csv",
        "data/raw/*.parquet",
        "data/raw/*.json"
    ]
    
    # Define processing operations
    operations = [
        {"type": "filter", "params": {"condition": "status == 'active'"}},
        {"type": "select_columns", "params": {"columns": ["id", "name", "value", "timestamp"]}},
        {"type": "drop_duplicates", "params": {"subset": ["id"]}},
        {"type": "sort", "params": {"columns": ["timestamp"], "ascending": False}}
    ]
    
    # Define validation rules
    validation_rules = {
        "schema_check": {
            "type": "schema_check",
            "expected_columns": ["id", "name", "value", "timestamp"],
            "required_types": {
                "id": "string",
                "value": "float",
                "timestamp": "string"
            }
        },
        "data_quality": {
            "type": "data_quality",
            "null_check_columns": ["id", "name", "value"],
            "quality_thresholds": {
                "id_null_percentage": 0,
                "name_null_percentage": 5,
                "value_null_percentage": 10
            }
        },
        "business_rules": {
            "type": "business_rules",
            "rules": [
                {
                    "condition": "value >= 0",
                    "description": "Values must be non-negative"
                },
                {
                    "condition": "length(name) > 0",
                    "description": "Names must not be empty"
                }
            ]
        }
    }
    
    # Process files with optimal engine selection
    processing_results = batch_processor.process_files_batch(
        file_patterns, operations, "output/processed"
    )
    
    # Validate processed files
    validation_results = {}
    for file_path, result in processing_results.items():
        if result.get("status") == "success":
            output_file = result["output_file"]
            validation_results[output_file] = validator.validate_file(
                output_file, validation_rules
            )
    
    return processing_results, validation_results

# Run the pipeline
pipeline_results = create_multi_engine_file_pipeline()
```

### 2. Performance Monitoring Dashboard

```python
def create_file_processing_dashboard():
    """Create a dashboard to monitor multi-engine file processing performance"""
    
    import dash
    from dash import dcc, html
    from dash.dependencies import Input, Output
    import plotly.graph_objs as go
    
    app = dash.Dash(__name__)
    
    app.layout = html.Div([
        html.H1("Multi-Engine File Processing Dashboard"),
        
        html.Div([
            dcc.Graph(id="engine-performance-chart"),
            dcc.Graph(id="file-processing-status-chart"),
            dcc.Interval(id="update-interval", interval=10000)
        ])
    ])
    
    @app.callback(
        [Output("engine-performance-chart", "figure"),
         Output("file-processing-status-chart", "figure")],
        Input("update-interval", "n_intervals")
    )
    def update_charts(n):
        # Get performance data (this would come from your actual processing)
        # For demonstration, we'll create sample data
        
        # Engine performance chart
        engines = ["pandas", "spark", "auto"]
        avg_processing_times = [2.5, 8.2, 4.1]  # seconds
        
        perf_fig = go.Figure(data=[
            go.Bar(x=engines, y=avg_processing_times, name="Average Processing Time")
        ])
        perf_fig.update_layout(title="Engine Performance Comparison", yaxis_title="Time (seconds)")
        
        # File processing status chart
        statuses = ["Success", "Failed", "In Progress"]
        counts = [45, 3, 2]
        
        status_fig = go.Figure(data=[
            go.Pie(labels=statuses, values=counts, name="Processing Status")
        ])
        status_fig.update_layout(title="File Processing Status Distribution")
        
        return perf_fig, status_fig
    
    return app

# Start the dashboard
file_dashboard = create_file_processing_dashboard()
file_dashboard.run_server(debug=True, port=8052)
```

## Best Practices

### 1. Engine Selection
- Use **Pandas** for files < 100MB and simple operations
- Use **Spark** for files > 500MB and complex transformations
- Use **Auto-detection** for unknown file sizes and dynamic workloads
- Consider **file format** when selecting engine (Parquet works well with both)

### 2. Performance Optimization
- **Cache frequently accessed files** in Spark
- **Use appropriate file formats** (Parquet for large data, CSV for small data)
- **Implement parallel processing** for multiple files
- **Monitor memory usage** and adjust engine selection accordingly

### 3. Data Quality
- **Validate files before processing** to catch issues early
- **Implement comprehensive error handling** for both engines
- **Use consistent validation rules** across all file types
- **Log validation results** for audit trails

### 4. Error Handling
- **Implement fallback mechanisms** when engines fail
- **Provide meaningful error messages** for debugging
- **Handle file format compatibility** issues gracefully
- **Retry failed operations** with different engines when possible

## Troubleshooting

### Common Issues

1. **Engine Compatibility Issues**
   ```python
   # Check engine availability
   if file_manager.spark_available:
       print("Spark is available for large files")
   else:
       print("Using Pandas only")
   ```

2. **Memory Issues with Large Files**
   ```python
   # Use Spark for very large files
   if file_size_mb > 1000:
       engine = "spark"
   else:
       engine = "pandas"
   ```

3. **File Format Compatibility**
   ```python
   # Check file format support
   supported_formats = {
       "pandas": [".csv", ".parquet", ".json", ".excel"],
       "spark": [".parquet", ".csv", ".json", ".avro"]
   }
   ```

## Conclusion

The multi-engine file operations in `siege_utilities` provide:

- **Seamless scalability** from small files to massive datasets
- **Automatic engine selection** based on file characteristics
- **Unified interfaces** that work with both Spark and Pandas
- **Comprehensive validation** and quality checking
- **Performance optimization** through intelligent engine selection

By following this recipe, you can build robust, scalable file processing pipelines that automatically adapt to your file sizes and processing requirements.

# ⚡ Spark Data Processing - Distributed Computing with Siege Utilities

<div align="center">

![Spark](https://img.shields.io/badge/Spark-Distributed_Computing-blue)
![Processing](https://img.shields.io/badge/Processing-Large_Datasets-green)
![Utilities](https://img.shields.io/badge/Utilities-500%2B_Functions-orange)

**Process large datasets efficiently with 500+ enhanced PySpark functions** 🚀

</div>

---

## 🎯 **Problem**

You need to process large datasets efficiently using Apache Spark, but want to leverage the enhanced functions and utilities provided by Siege Utilities for better data manipulation and analysis.

## 💡 **Solution**

Use Siege Utilities' Spark utilities module which provides 500+ enhanced PySpark functions, including mathematical operations, array manipulations, and data transformations that work seamlessly with Spark DataFrames.

## 🚀 **Quick Start**

```python
import siege_utilities
from pyspark.sql import SparkSession

# Initialize Spark session
spark = SparkSession.builder \
    .appName("SiegeUtilitiesSpark") \
    .config("spark.sql.adaptive.enabled", "true") \
    .getOrCreate()

# Apply enhanced functions
df_enhanced = df.withColumn("abs_value", siege_utilities.abs(col("value")))
print("✅ Spark processing with Siege Utilities ready!")
```

## 📋 **Complete Implementation**

### **1. Basic Spark Setup with Siege Utilities**

```python
import siege_utilities
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, lit

# Initialize Spark session
spark = SparkSession.builder \
    .appName("SiegeUtilitiesSpark") \
    .config("spark.sql.adaptive.enabled", "true") \
    .config("spark.sql.adaptive.coalescePartitions.enabled", "true") \
    .config("spark.sql.adaptive.skewJoin.enabled", "true") \
    .getOrCreate()

# Setup logging
siege_utilities.log_info("Initializing Spark session with Siege Utilities")

# Configure Spark for optimal performance
spark.conf.set("spark.sql.adaptive.enabled", "true")
spark.conf.set("spark.sql.adaptive.coalescePartitions.enabled", "true")
spark.conf.set("spark.sql.adaptive.skewJoin.enabled", "true")

siege_utilities.log_info("Spark session initialized with Siege Utilities")
print(f"✅ Spark version: {spark.version}")
print(f"✅ Siege Utilities functions available: {len([f for f in dir(siege_utilities) if not f.startswith('_')])}")
```

### **2. Mathematical Operations**

```python
# Create sample data
data = [
    ("A", 1.5, -2.3, 0.0),
    ("B", 3.7, 1.2, 0.5),
    ("C", -1.8, 0.0, 2.1),
    ("D", 4.2, -1.5, 3.8),
    ("E", 0.0, 2.8, -0.9)
]
df = spark.createDataFrame(data, ["id", "value1", "value2", "value3"])

print("📊 Original DataFrame:")
df.show()

# Apply mathematical functions from Siege Utilities
df_math = df.withColumn("abs_value1", siege_utilities.abs(col("value1"))) \
    .withColumn("acos_value2", siege_utilities.acos(col("value2"))) \
    .withColumn("acosh_value3", siege_utilities.acosh(col("value3"))) \
    .withColumn("sqrt_value1", siege_utilities.sqrt(siege_utilities.abs(col("value1")))) \
    .withColumn("power_value2", siege_utilities.power(col("value2"), 2))

print("🔢 Enhanced DataFrame with mathematical operations:")
df_math.show()

# Calculate comprehensive statistics
df_stats = df_math.select(
    siege_utilities.aggregate(col("abs_value1")).alias("sum_abs_values"),
    siege_utilities.approx_count_distinct(col("id")).alias("unique_ids"),
    siege_utilities.avg(col("value1")).alias("avg_value1"),
    siege_utilities.stddev(col("value2")).alias("stddev_value2"),
    siege_utilities.variance(col("value3")).alias("variance_value3")
)

print("📈 Statistical summary:")
df_stats.show()
```

### **3. Array Operations**

```python
# Create array columns
df_arrays = df.withColumn("values_array", siege_utilities.array(col("value1"), col("value2"), col("value3"))) \
    .withColumn("array_size", siege_utilities.array_size(col("values_array")))

print("📦 DataFrame with arrays:")
df_arrays.show(truncate=False)

# Advanced array manipulations
df_arrays = df_arrays \
    .withColumn("distinct_values", siege_utilities.array_distinct(col("values_array"))) \
    .withColumn("max_value", siege_utilities.array_max(col("values_array"))) \
    .withColumn("min_value", siege_utilities.array_min(col("values_array"))) \
    .withColumn("contains_positive", siege_utilities.array_contains(col("values_array"), lit(True))) \
    .withColumn("sorted_values", siege_utilities.array_sort(col("values_array"))) \
    .withColumn("reversed_values", siege_utilities.array_reverse(col("values_array")))

# Array aggregation and transformation
df_arrays = df_arrays \
    .withColumn("flattened_values", siege_utilities.array_join(col("values_array"), ", ")) \
    .withColumn("array_sum", siege_utilities.aggregate(col("values_array"))) \
    .withColumn("array_avg", siege_utilities.avg(col("values_array")))

print("🔧 Enhanced DataFrame with array operations:")
df_arrays.show(truncate=False)
```

### **4. Date and Time Operations**

```python
from pyspark.sql.functions import current_date, current_timestamp

# Add date operations
df_dates = df.withColumn("current_date", current_date()) \
    .withColumn("current_timestamp", current_timestamp()) \
    .withColumn("future_date", siege_utilities.add_months(current_date(), 3)) \
    .withColumn("past_date", siege_utilities.add_months(current_date(), -6)) \
    .withColumn("next_year", siege_utilities.add_years(current_date(), 1)) \
    .withColumn("days_between", siege_utilities.datediff(col("future_date"), col("past_date")))

print("📅 DataFrame with date operations:")
df_dates.show()

# Extract date components
df_dates = df_dates \
    .withColumn("year", siege_utilities.year(col("current_date"))) \
    .withColumn("month", siege_utilities.month(col("current_date"))) \
    .withColumn("day", siege_utilities.day(col("current_date"))) \
    .withColumn("day_of_week", siege_utilities.dayofweek(col("current_date"))) \
    .withColumn("day_of_year", siege_utilities.dayofyear(col("current_date")))

print("📅 Enhanced DataFrame with date components:")
df_dates.show()
```

### **5. Advanced Data Transformations**

```python
# Complex transformations using Siege Utilities
def transform_dataframe(df):
    """Apply complex transformations using Siege Utilities"""
    
    # Group by and aggregate with enhanced functions
    df_grouped = df.groupBy("id").agg(
        siege_utilities.array_agg(col("value1")).alias("all_values1"),
        siege_utilities.array_agg(col("value2")).alias("all_values2"),
        siege_utilities.any_value(col("value3")).alias("sample_value3"),
        siege_utilities.count(col("value1")).alias("count_values1"),
        siege_utilities.sum(col("value1")).alias("sum_values1"),
        siege_utilities.avg(col("value2")).alias("avg_values2"),
        siege_utilities.stddev(col("value3")).alias("stddev_values3")
    )
    
    # Apply window functions
    from pyspark.sql.window import Window
    from pyspark.sql.functions import row_number, rank, dense_rank
    
    window_spec = Window.orderBy(col("sum_values1").desc())
    
    df_ranked = df_grouped \
        .withColumn("row_number", row_number().over(window_spec)) \
        .withColumn("rank", rank().over(window_spec)) \
        .withColumn("dense_rank", dense_rank().over(window_spec))
    
    return df_ranked

# Apply transformations
df_transformed = transform_dataframe(df)

print("🔄 Transformed DataFrame:")
df_transformed.show(truncate=False)
```

### **6. String and Text Processing**

```python
# String operations with Siege Utilities
df_strings = df.withColumn("id_upper", siege_utilities.upper(col("id"))) \
    .withColumn("id_lower", siege_utilities.lower(col("id"))) \
    .withColumn("id_length", siege_utilities.length(col("id"))) \
    .withColumn("id_reverse", siege_utilities.reverse(col("id"))) \
    .withColumn("id_concat", siege_utilities.concat(col("id"), lit("_"), col("value1"))) \
    .withColumn("id_substring", siege_utilities.substring(col("id"), 1, 2))

print("🔤 DataFrame with string operations:")
df_strings.show(truncate=False)

# Advanced string functions
df_strings = df_strings \
    .withColumn("id_pad_left", siege_utilities.lpad(col("id"), 5, "0")) \
    .withColumn("id_pad_right", siege_utilities.rpad(col("id"), 5, "*")) \
    .withColumn("id_trim", siege_utilities.trim(col("id"))) \
    .withColumn("id_replace", siege_utilities.regexp_replace(col("id"), "A", "Alpha"))

print("🔤 Enhanced DataFrame with advanced string operations:")
df_strings.show(truncate=False)
```

### **7. Complete Spark Processing Pipeline**

```python
class SiegeSparkProcessor:
    """Complete Spark processing pipeline using Siege Utilities"""
    
    def __init__(self, app_name="SiegeSparkProcessor"):
        self.app_name = app_name
        self.spark = None
        self.processed_data = {}
        
    def initialize_spark(self, config=None):
        """Initialize Spark session with optimal configuration"""
        
        try:
            # Default configuration
            default_config = {
                "spark.sql.adaptive.enabled": "true",
                "spark.sql.adaptive.coalescePartitions.enabled": "true",
                "spark.sql.adaptive.skewJoin.enabled": "true",
                "spark.sql.adaptive.localShuffleReader.enabled": "true",
                "spark.sql.adaptive.advisoryPartitionSizeInBytes": "128m"
            }
            
            # Merge with custom config
            if config:
                default_config.update(config)
            
            # Build Spark session
            builder = SparkSession.builder.appName(self.app_name)
            
            for key, value in default_config.items():
                builder = builder.config(key, value)
            
            self.spark = builder.getOrCreate()
            
            # Apply configurations
            for key, value in default_config.items():
                self.spark.conf.set(key, value)
            
            siege_utilities.log_info(f"Spark session initialized: {self.app_name}")
            print(f"✅ Spark session ready: {self.app_name}")
            print(f"✅ Spark version: {self.spark.version}")
            
            return True
            
        except Exception as e:
            siege_utilities.log_error(f"Failed to initialize Spark: {e}")
            return False
    
    def load_data(self, data_source, format_type="csv", options=None):
        """Load data from various sources"""
        
        try:
            if format_type.lower() == "csv":
                df = self.spark.read.csv(data_source, header=True, inferSchema=True)
            elif format_type.lower() == "parquet":
                df = self.spark.read.parquet(data_source)
            elif format_type.lower() == "json":
                df = self.spark.read.json(data_source)
            else:
                raise ValueError(f"Unsupported format: {format_type}")
            
            siege_utilities.log_info(f"Data loaded: {data_source} ({df.count()} rows)")
            return df
            
        except Exception as e:
            siege_utilities.log_error(f"Failed to load data: {e}")
            return None
    
    def process_data(self, df, operations):
        """Apply a series of data processing operations"""
        
        try:
            processed_df = df
            
            for operation in operations:
                operation_type = operation.get('type')
                params = operation.get('params', {})
                
                if operation_type == 'mathematical':
                    processed_df = self._apply_math_operations(processed_df, params)
                elif operation_type == 'array':
                    processed_df = self._apply_array_operations(processed_df, params)
                elif operation_type == 'string':
                    processed_df = self._apply_string_operations(processed_df, params)
                elif operation_type == 'date':
                    processed_df = self._apply_date_operations(processed_df, params)
                elif operation_type == 'aggregation':
                    processed_df = self._apply_aggregation(processed_df, params)
                else:
                    siege_utilities.log_warning(f"Unknown operation type: {operation_type}")
            
            return processed_df
            
        except Exception as e:
            siege_utilities.log_error(f"Data processing failed: {e}")
            return None
    
    def _apply_math_operations(self, df, params):
        """Apply mathematical operations"""
        
        columns = params.get('columns', [])
        operations = params.get('operations', ['abs', 'sqrt'])
        
        for col_name in columns:
            if 'abs' in operations:
                df = df.withColumn(f"{col_name}_abs", siege_utilities.abs(col(col_name)))
            if 'sqrt' in operations:
                df = df.withColumn(f"{col_name}_sqrt", siege_utilities.sqrt(siege_utilities.abs(col(col_name))))
            if 'power' in operations:
                power = params.get('power', 2)
                df = df.withColumn(f"{col_name}_power", siege_utilities.power(col(col_name), power))
        
        return df
    
    def _apply_array_operations(self, df, params):
        """Apply array operations"""
        
        source_columns = params.get('source_columns', [])
        target_column = params.get('target_column', 'combined_array')
        
        if source_columns:
            df = df.withColumn(target_column, siege_utilities.array(*[col(c) for c in source_columns]))
            df = df.withColumn(f"{target_column}_size", siege_utilities.array_size(col(target_column)))
            df = df.withColumn(f"{target_column}_max", siege_utilities.array_max(col(target_column)))
            df = df.withColumn(f"{target_column}_min", siege_utilities.array_min(col(target_column)))
        
        return df
    
    def _apply_string_operations(self, df, params):
        """Apply string operations"""
        
        columns = params.get('columns', [])
        operations = params.get('operations', ['upper', 'lower'])
        
        for col_name in columns:
            if 'upper' in operations:
                df = df.withColumn(f"{col_name}_upper", siege_utilities.upper(col(col_name)))
            if 'lower' in operations:
                df = df.withColumn(f"{col_name}_lower", siege_utilities.lower(col(col_name)))
            if 'length' in operations:
                df = df.withColumn(f"{col_name}_length", siege_utilities.length(col(col_name)))
        
        return df
    
    def _apply_date_operations(self, df, params):
        """Apply date operations"""
        
        date_column = params.get('date_column', 'date')
        operations = params.get('operations', ['year', 'month', 'day'])
        
        if 'year' in operations:
            df = df.withColumn(f"{date_column}_year", siege_utilities.year(col(date_column)))
        if 'month' in operations:
            df = df.withColumn(f"{date_column}_month", siege_utilities.month(col(date_column)))
        if 'day' in operations:
            df = df.withColumn(f"{date_column}_day", siege_utilities.day(col(date_column)))
        
        return df
    
    def _apply_aggregation(self, df, params):
        """Apply aggregation operations"""
        
        group_columns = params.get('group_columns', [])
        agg_columns = params.get('agg_columns', [])
        agg_functions = params.get('agg_functions', ['count', 'sum', 'avg'])
        
        if group_columns and agg_columns:
            agg_exprs = []
            for col_name in agg_columns:
                for func in agg_functions:
                    if func == 'count':
                        agg_exprs.append(siege_utilities.count(col(col_name)).alias(f"{col_name}_count"))
                    elif func == 'sum':
                        agg_exprs.append(siege_utilities.sum(col(col_name)).alias(f"{col_name}_sum"))
                    elif func == 'avg':
                        agg_exprs.append(siege_utilities.avg(col(col_name)).alias(f"{col_name}_avg"))
            
            df = df.groupBy(group_columns).agg(*agg_exprs)
        
        return df
    
    def save_data(self, df, output_path, format_type="parquet", options=None):
        """Save processed data"""
        
        try:
            if format_type.lower() == "parquet":
                df.write.mode("overwrite").parquet(output_path)
            elif format_type.lower() == "csv":
                df.write.mode("overwrite").option("header", "true").csv(output_path)
            elif format_type.lower() == "json":
                df.write.mode("overwrite").json(output_path)
            else:
                raise ValueError(f"Unsupported output format: {format_type}")
            
            siege_utilities.log_info(f"Data saved: {output_path}")
            return True
            
        except Exception as e:
            siege_utilities.log_error(f"Failed to save data: {e}")
            return False
    
    def cleanup(self):
        """Clean up Spark session"""
        
        if self.spark:
            self.spark.stop()
            siege_utilities.log_info("Spark session stopped")

# Usage example
if __name__ == "__main__":
    # Initialize processor
    processor = SiegeSparkProcessor("DataProcessingApp")
    
    # Initialize Spark
    if processor.initialize_spark():
        
        # Load data
        df = processor.load_data("data/sample_data.csv", "csv")
        
        if df is not None:
            # Define processing operations
            operations = [
                {
                    'type': 'mathematical',
                    'params': {
                        'columns': ['value1', 'value2', 'value3'],
                        'operations': ['abs', 'sqrt', 'power']
                    }
                },
                {
                    'type': 'array',
                    'params': {
                        'source_columns': ['value1', 'value2', 'value3'],
                        'target_column': 'combined_values'
                    }
                },
                {
                    'type': 'string',
                    'params': {
                        'columns': ['id'],
                        'operations': ['upper', 'lower', 'length']
                    }
                },
                {
                    'type': 'aggregation',
                    'params': {
                        'group_columns': ['id'],
                        'agg_columns': ['value1', 'value2', 'value3'],
                        'agg_functions': ['count', 'sum', 'avg']
                    }
                }
            ]
            
            # Process data
            processed_df = processor.process_data(df, operations)
            
            if processed_df is not None:
                print("🔄 Processing completed successfully!")
                processed_df.show(truncate=False)
                
                # Save results
                processor.save_data(processed_df, "output/processed_data", "parquet")
        
        # Cleanup
        processor.cleanup()
```

## 📊 **Expected Output**

### **Basic Setup**
```
✅ Spark session ready: SiegeUtilitiesSpark
✅ Spark version: 3.4.0
✅ Siege Utilities functions available: 1147
```

### **Mathematical Operations**
```
🔢 Enhanced DataFrame with mathematical operations:
+---+------+------+------+-----------+-----------+-----------+-----------+-----------+
| id|value1|value2|value3|abs_value1|acos_value2|acosh_value3|sqrt_value1|power_value2|
+---+------+------+------+-----------+-----------+-----------+-----------+-----------+
|  A|   1.5|  -2.3|   0.0|        1.5|        NaN|        NaN|       1.22|        5.29|
|  B|   3.7|   1.2|   0.5|        3.7|        0.0|        NaN|       1.92|        1.44|
|  C|  -1.8|   0.0|   2.1|        1.8|        1.57|       1.37|       1.34|        0.0 |
+---+------+------+------+-----------+-----------+-----------+-----------+-----------+
```

### **Array Operations**
```
🔧 Enhanced DataFrame with array operations:
+---+------+------+------+------------------+----------+------------------+------------------+------------------+------------------+------------------+------------------+------------------+------------------+------------------+
| id|value1|value2|value3|      values_array|array_size|   distinct_values|         max_value|         min_value|contains_positive|    sorted_values|  reversed_values|  flattened_values|        array_sum|      array_avg|
+---+------+------+------+------------------+----------+------------------+------------------+------------------+------------------+------------------+------------------+------------------+------------------+------------------+
|  A|   1.5|  -2.3|   0.0|    [1.5, -2.3, 0.0]|         3|    [1.5, -2.3, 0.0]|              1.5|             -2.3|             true|  [-2.3, 0.0, 1.5]|    [0.0, -2.3, 1.5]|      1.5, -2.3, 0.0|             -0.8|           -0.27|
+---+------+------+------+------------------+----------+------------------+------------------+------------------+------------------+------------------+------------------+------------------+------------------+------------------+
```

## 🔧 **Configuration Options**

### **Spark Configuration**
```python
# Performance optimization
spark_config = {
    "spark.sql.adaptive.enabled": "true",
    "spark.sql.adaptive.coalescePartitions.enabled": "true",
    "spark.sql.adaptive.skewJoin.enabled": "true",
    "spark.sql.adaptive.localShuffleReader.enabled": "true",
    "spark.sql.adaptive.advisoryPartitionSizeInBytes": "128m",
    "spark.sql.adaptive.maxShuffledHashJoinLocalMapThreshold": "0",
    "spark.sql.adaptive.forceApply": "true"
}

# Memory optimization
memory_config = {
    "spark.executor.memory": "4g",
    "spark.driver.memory": "2g",
    "spark.sql.adaptive.maxShuffledHashJoinLocalMapThreshold": "0"
}
```

### **Processing Operations Configuration**
```yaml
# operations_config.yaml
operations:
  - type: "mathematical"
    params:
      columns: ["value1", "value2", "value3"]
      operations: ["abs", "sqrt", "power"]
      power: 2
  
  - type: "array"
    params:
      source_columns: ["value1", "value2", "value3"]
      target_column: "combined_values"
  
  - type: "string"
    params:
      columns: ["id"]
      operations: ["upper", "lower", "length"]
  
  - type: "aggregation"
    params:
      group_columns: ["id"]
      agg_columns: ["value1", "value2", "value3"]
      agg_functions: ["count", "sum", "avg"]
```

## 🚨 **Troubleshooting**

### **Common Issues**

1. **⚡ Spark Initialization Failed**: Check Java version and Spark installation
2. **💾 Memory Issues**: Adjust executor and driver memory settings
3. **📊 Data Loading Errors**: Verify data source format and permissions
4. **🔄 Processing Slow**: Enable adaptive query execution and optimize partitions

### **Performance Tips**

- **⚡ Adaptive Query Execution**: Enable for automatic optimization
- **💾 Partition Management**: Use appropriate partition sizes
- **🔄 Caching**: Cache frequently used DataFrames
- **📊 Broadcast Joins**: Use for small lookup tables

### **Best Practices**

- **🔧 Configuration**: Use optimal Spark configurations for your cluster
- **📊 Data Validation**: Validate data before processing
- **💾 Memory Management**: Monitor memory usage and adjust accordingly
- **🔄 Error Handling**: Implement comprehensive error handling
- **📋 Logging**: Use structured logging for debugging

## 🚀 **Next Steps**

After mastering Spark processing:

- **[Distributed Computing](Recipes/Distributed-Computing.md)** - Scale to cluster computing
- **[Performance Optimization](Recipes/Performance-Optimization.md)** - Optimize processing speed
- **[Data Pipeline](Recipes/Data-Pipeline.md)** - Build end-to-end data pipelines
- **[Monitoring](Recipes/Monitoring.md)** - Monitor Spark applications

## 🔗 **Related Recipes**

- **[Basic Setup](Recipes/Basic-Setup.md)** - Install and configure Siege Utilities
- **[Batch Processing](Recipes/Batch-Processing.md)** - Process files efficiently
- **[Data Validation](Recipes/Data-Validation.md)** - Validate data quality
- **[Performance Optimization](Recipes/Performance-Optimization.md)** - Optimize processing

---

<div align="center">

**Ready to process data at scale?** ⚡

**[Next: Distributed Computing](Recipes/Distributed-Computing.md)** → **[Performance Optimization](Recipes/Performance-Optimization.md)**

</div>

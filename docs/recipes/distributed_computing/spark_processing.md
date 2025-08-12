# Spark Data Processing

## Problem
You need to process large datasets efficiently using Apache Spark, but want to leverage the enhanced functions and utilities provided by Siege Utilities for better data manipulation and analysis.

## Solution
Use Siege Utilities' Spark utilities module which provides 500+ enhanced PySpark functions, including mathematical operations, array manipulations, and data transformations that work seamlessly with Spark DataFrames.

## Code Example

### 1. Basic Spark Setup with Siege Utilities
```python
import siege_utilities
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, lit

# Initialize Spark session
spark = SparkSession.builder \
    .appName("SiegeUtilitiesSpark") \
    .config("spark.sql.adaptive.enabled", "true") \
    .getOrCreate()

# Setup logging
siege_utilities.init_logger(
    name='spark_processor',
    log_to_file=True,
    log_dir='logs',
    level='INFO'
)

siege_utilities.log_info("Spark session initialized with Siege Utilities")
```

### 2. Mathematical Operations
```python
# Create sample data
data = [
    ("A", 1.5, -2.3, 0.0),
    ("B", 3.7, 1.2, 0.5),
    ("C", -1.8, 0.0, 2.1)
]
df = spark.createDataFrame(data, ["id", "value1", "value2", "value3"])

# Apply mathematical functions from Siege Utilities
df_math = df.withColumn("abs_value1", siege_utilities.abs(col("value1"))) \
    .withColumn("acos_value2", siege_utilities.acos(col("value2"))) \
    .withColumn("acosh_value3", siege_utilities.acosh(col("value3")))

df_math.show()

# Calculate statistics
df_stats = df_math.select(
    siege_utilities.aggregate(col("abs_value1")).alias("sum_abs_values"),
    siege_utilities.approx_count_distinct(col("id")).alias("unique_ids")
)

df_stats.show()
```

### 3. Array Operations
```python
# Create array columns
df_arrays = df.withColumn("values_array", siege_utilities.array(col("value1"), col("value2"), col("value3"))) \
    .withColumn("array_size", siege_utilities.array_size(col("values_array")))

# Array manipulations
df_arrays = df_arrays.withColumn("distinct_values", siege_utilities.array_distinct(col("values_array"))) \
    .withColumn("max_value", siege_utilities.array_max(col("values_array"))) \
    .withColumn("contains_positive", siege_utilities.array_contains(col("values_array"), lit(True)))

# Array aggregation
df_arrays = df_arrays.withColumn("flattened_values", siege_utilities.array_join(col("values_array"), ", "))

df_arrays.show(truncate=False)
```

### 4. Date and Time Operations
```python
from pyspark.sql.functions import current_date

# Add date operations
df_dates = df.withColumn("current_date", current_date()) \
    .withColumn("future_date", siege_utilities.add_months(current_date(), 3)) \
    .withColumn("past_date", siege_utilities.add_months(current_date(), -6))

df_dates.show()
```

### 5. Advanced Data Transformations
```python
# Complex transformations using Siege Utilities
def transform_dataframe(df):
    """Apply complex transformations using Siege Utilities"""
    
    # Group by and aggregate
    df_grouped = df.groupBy("id").agg(
        siege_utilities.array_agg(col("value1")).alias("all_values1"),
        siege_utilities.array_agg(col("value2")).alias("all_values2"),
        siege_utilities.any_value(col("value3")).alias("sample_value3")
    )
    
    # Array operations on aggregated data
    df_transformed = df_grouped.withColumn("combined_values", 
        siege_utilities.array_concat(col("all_values1"), col("all_values2"))) \
        .withColumn("unique_combined", 
        siege_utilities.array_distinct(col("combined_values"))) \
        .withColumn("sorted_values", 
        siege_utilities.array_sort(col("unique_combined")))
    
    return df_transformed

# Apply transformations
result_df = transform_dataframe(df)
result_df.show(truncate=False)
```

### 6. Data Quality and Validation
```python
# Data quality checks using Siege Utilities
def validate_dataframe(df):
    """Validate DataFrame using Siege Utilities functions"""
    
    # Check for null values
    null_counts = df.select([
        siege_utilities.count_if(col(c).isNull()).alias(f"{c}_null_count")
        for c in df.columns
    ])
    
    # Check value ranges
    value_ranges = df.select([
        siege_utilities.min(col(c)).alias(f"{c}_min"),
        siege_utilities.max(col(c)).alias(f"{c}_max"),
        siege_utilities.avg(col(c)).alias(f"{c}_avg")
        for c in df.columns if df.schema[c].dataType.typeName() in ['double', 'integer']
    ])
    
    return null_counts, value_ranges

# Run validation
null_summary, value_summary = validate_dataframe(df)
print("Null value summary:")
null_summary.show()
print("Value range summary:")
value_summary.show()
```

### 7. Performance Optimization
```python
# Optimize DataFrame operations
def optimized_processing(df):
    """Optimized data processing with Siege Utilities"""
    
    # Cache frequently used DataFrame
    df.cache()
    
    # Use broadcast joins for small DataFrames
    small_df = spark.createDataFrame([("A", "Category1"), ("B", "Category2")], ["id", "category"])
    
    # Join with broadcast hint
    from pyspark.sql.functions import broadcast
    df_joined = df.join(broadcast(small_df), "id")
    
    # Apply Siege Utilities functions efficiently
    df_result = df_joined.select(
        col("id"),
        col("category"),
        siege_utilities.abs(col("value1")).alias("abs_value1"),
        siege_utilities.array(col("value1", "value2")).alias("value_pair")
    )
    
    # Unpersist to free memory
    df.unpersist()
    
    return df_result

# Run optimized processing
optimized_df = optimized_processing(df)
optimized_df.show()
```

## Expected Output

```
+---+-----+------+-----+----------+-----------+------------+
| id|value1|value2|value3|abs_value1|acos_value2|acosh_value3|
+---+-----+------+-----+----------+-----------+------------+
|  A|  1.5|  -2.3|  0.0|       1.5|        NaN|         NaN|
|  B|  3.7|   1.2|  0.5|       3.7|  0.6435011|         NaN|
|  C| -1.8|   0.0|  2.1|       1.8|   1.570796|   1.372859|
+---+-----+------+-----+----------+-----------+------------+

+---+-------------+-----------+-----------+------------------+
| id|all_values1 |all_values2|sample_value3|combined_values  |
+---+-------------+-----------+-----------+------------------+
|  A|[1.5]       |[-2.3]     |0.0        |[1.5, -2.3]      |
|  B|[3.7]       |[1.2]      |0.5        |[3.7, 1.2]       |
|  C|[-1.8]      |[0.0]      |2.1        |[-1.8, 0.0]      |
+---+-------------+-----------+-----------+------------------+
```

## Notes

- **Performance**: Siege Utilities functions are optimized for Spark operations
- **Memory Management**: Use caching and unpersist for large DataFrames
- **Broadcasting**: Use broadcast joins for small lookup tables
- **Error Handling**: Some mathematical functions may return NaN for invalid inputs
- **Type Safety**: Ensure column types match function expectations
- **Partitioning**: Consider repartitioning for better performance

## Troubleshooting

### Common Issues

1. **Type Errors**: Check column data types before applying functions
2. **Memory Issues**: Reduce DataFrame size or increase Spark memory settings
3. **Performance**: Use appropriate partitioning and caching strategies
4. **Function Availability**: Ensure you're using the correct function names

### Performance Tips

- Cache frequently used DataFrames
- Use broadcast joins for small tables
- Repartition large DataFrames appropriately
- Monitor Spark UI for performance bottlenecks
- Use adaptive query execution when possible

### Next Steps

After mastering Spark processing:
- Explore [HDFS Operations](../distributed_computing/hdfs_operations.md)
- Learn [Cluster Management](../distributed_computing/cluster_management.md)
- Build [Data Pipelines](../data_processing/batch_operations.md)
- Integrate with [Analytics Platforms](../analytics/google_analytics.md)

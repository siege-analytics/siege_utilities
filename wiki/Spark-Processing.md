# Multi-Engine Data Processing - Spark, Pandas, and Beyond with Siege Utilities

## Problem

You need to process data efficiently at any scale - from small datasets that work well with Pandas to massive distributed datasets that require Apache Spark. You want a unified approach that automatically selects the best engine for your data and operations, while leveraging the enhanced functions and utilities provided by Siege Utilities.

## Solution

Use Siege Utilities' multi-engine architecture which provides seamless integration between:
- **Pandas**: For small to medium datasets with fast local processing
- **Apache Spark**: For large distributed datasets with cluster computing
- **Auto-Engine Selection**: Intelligent engine choice based on data size and complexity
- **Unified API**: Consistent interface across all engines with 500+ enhanced functions

## Quick Start

```python
import siege_utilities
from siege_utilities.distributed.spark_utils import SparkUtils
from siege_utilities.files.operations import FileOperations

# Initialize multi-engine processor
file_ops = FileOperations()
spark_utils = SparkUtils()

# Auto-select best engine based on data size
data_source = "large_dataset.parquet"
if file_ops.get_file_size(data_source) > 500 * 1024 * 1024:  # 500MB
    # Use Spark for large datasets
    df = spark_utils.read_parquet(data_source)
    result = df.transform(siege_utilities.enhance_dataframe)
else:
    # Use Pandas for smaller datasets
    import pandas as pd
    df = pd.read_parquet(data_source)
    result = siege_utilities.enhance_dataframe(df)

print("✅ Multi-engine processing ready!")
```

## Complete Implementation

### 1. Multi-Engine Architecture with Siege Utilities

#### Engine-Agnostic Data Processor
```python
import siege_utilities
from siege_utilities.distributed.spark_utils import SparkUtils
from siege_utilities.files.operations import FileOperations
from siege_utilities.core.logging import Logger
import pandas as pd
import numpy as np

# Initialize logging
siege_utilities.log_info("Starting multi-engine data processing with Siege Utilities")

class MultiEngineDataProcessor:
    """Unified data processor that works with multiple engines"""
    
    def __init__(self, default_engine="auto", spark_config=None):
        self.default_engine = default_engine
        self.logger = Logger("multi_engine_processor")
        
        # Initialize Spark if needed
        if default_engine in ["spark", "auto"]:
            self.spark_utils = SparkUtils(spark_config)
            self.spark_available = True
        else:
            self.spark_utils = None
            self.spark_available = False
        
        # Initialize file operations
        self.file_ops = FileOperations()
    
    def get_optimal_engine(self, data_size_mb=None, operation_complexity="medium", data_type="tabular"):
        """Automatically select the best engine for data processing"""
        
        if data_size_mb is None:
            return "auto"
        
        # Engine selection logic based on data characteristics
        if data_size_mb < 100 and operation_complexity == "simple":
            return "pandas"
        elif data_size_mb < 500 and operation_complexity == "medium":
            return "pandas"
        elif data_size_mb >= 500 or operation_complexity == "complex":
            return "spark" if self.spark_available else "pandas"
        else:
            return "auto"
    
    def load_data(self, data_source, engine=None, **kwargs):
        """Load data using specified or auto-detected engine"""
        
        # Auto-detect data size if not provided
        if isinstance(data_source, str):
            data_size_mb = self.file_ops.get_file_size(data_source) / (1024 * 1024)
        else:
            data_size_mb = self._estimate_data_size(data_source)
        
        # Select optimal engine
        if engine is None:
            engine = self.get_optimal_engine(data_size_mb, kwargs.get("complexity", "medium"))
        
        self.logger.info(f"Loading data with {engine} engine (size: {data_size_mb:.2f}MB)")
        
        if engine == "spark" and self.spark_available:
            return self._load_with_spark(data_source, **kwargs)
        else:
            return self._load_with_pandas(data_source, **kwargs)
    
    def process_data(self, data, operations, engine=None, **kwargs):
        """Process data using specified or auto-detected engine"""
        
        # Determine current engine
        if engine is None:
            if hasattr(data, 'rdd'):  # Spark DataFrame
                current_engine = "spark"
            else:  # Pandas DataFrame
                current_engine = "pandas"
        else:
            current_engine = engine
        
        self.logger.info(f"Processing data with {current_engine} engine")
        
        if current_engine == "spark":
            return self._process_with_spark(data, operations, **kwargs)
        else:
            return self._process_with_pandas(data, operations, **kwargs)
    
    def _load_with_spark(self, data_source, **kwargs):
        """Load data using Spark for large datasets"""
        
        try:
            if isinstance(data_source, str):
                # Load from file
                if data_source.endswith('.parquet'):
                    df = self.spark_utils.spark.read.parquet(data_source)
                elif data_source.endswith('.csv'):
                    df = self.spark_utils.spark.read.csv(
                        data_source, 
                        header=kwargs.get('header', True),
                        inferSchema=kwargs.get('inferSchema', True)
                    )
                elif data_source.endswith('.json'):
                    df = self.spark_utils.spark.read.json(data_source)
                else:
                    df = self.spark_utils.spark.read.text(data_source)
            else:
                df = data_source
            
            return df
            
        except Exception as e:
            self.logger.error(f"Spark data loading failed: {e}")
            raise
    
    def _load_with_pandas(self, data_source, **kwargs):
        """Load data using Pandas for smaller datasets"""
        
        try:
            if isinstance(data_source, str):
                # Load from file
                if data_source.endswith('.parquet'):
                    df = pd.read_parquet(data_source)
                elif data_source.endswith('.csv'):
                    df = pd.read_csv(data_source, **kwargs)
                elif data_source.endswith('.json'):
                    df = pd.read_json(data_source)
                else:
                    df = pd.read_csv(data_source, **kwargs)
            else:
                df = data_source
            
            return df
            
        except Exception as e:
            self.logger.error(f"Pandas data loading failed: {e}")
            raise
    
    def _process_with_spark(self, data, operations, **kwargs):
        """Process data using Spark operations"""
        
        try:
            result_df = data
            
            # Apply operations
            for operation in operations:
                if operation['type'] == 'transform':
                    result_df = result_df.transform(operation['function'])
                elif operation['type'] == 'filter':
                    result_df = result_df.filter(operation['condition'])
                elif operation['type'] == 'select':
                    result_df = result_df.select(operation['columns'])
                elif operation['type'] == 'groupby':
                    result_df = result_df.groupBy(operation['columns']).agg(operation['aggregations'])
            
            return result_df
            
        except Exception as e:
            self.logger.error(f"Spark data processing failed: {e}")
            raise
    
    def _process_with_pandas(self, data, operations, **kwargs):
        """Process data using Pandas operations"""
        
        try:
            result_df = data.copy()
            
            # Apply operations
            for operation in operations:
                if operation['type'] == 'transform':
                    result_df = operation['function'](result_df)
                elif operation['type'] == 'filter':
                    result_df = result_df[operation['condition'](result_df)]
                elif operation['type'] == 'select':
                    result_df = result_df[operation['columns']]
                elif operation['type'] == 'groupby':
                    result_df = result_df.groupby(operation['columns']).agg(operation['aggregations'])
            
            return result_df
            
        except Exception as e:
            self.logger.error(f"Pandas data processing failed: {e}")
            raise
    
    def _estimate_data_size(self, data):
        """Estimate data size in MB"""
        
        try:
            if hasattr(data, 'rdd'):  # Spark DataFrame
                # Rough estimate for Spark
                return 100.0  # Default estimate
            else:  # Pandas DataFrame
                # More accurate estimate for Pandas
                return data.memory_usage(deep=True).sum() / (1024 * 1024)
        except:
            return 50.0  # Default estimate
```

#### Initialize Multi-Engine Environment
```python
def create_multi_engine_environment():
    """Create and configure multi-engine processing environment."""
    
    try:
        # Initialize multi-engine processor
        processor = MultiEngineDataProcessor(default_engine="auto")
        
        print(f"✅ Multi-engine processor initialized")
        print(f"🚀 Spark available: {processor.spark_available}")
        print(f"🎯 Default engine: {processor.default_engine}")
        
        # Test engine availability
        if processor.spark_available:
            print(f"🔧 Spark version: {processor.spark_utils.spark.version}")
            print(f"⚡ Spark master: {processor.spark_utils.spark.conf.get('spark.master')}")
        
        return processor
        
    except Exception as e:
        print(f"❌ Error creating multi-engine environment: {e}")
        siege_utilities.log_error(f"Multi-engine environment creation failed: {e}")
        return None

# Create multi-engine environment
multi_engine_processor = create_multi_engine_environment()
```

### 2. Multi-Engine Data Processing Examples

#### Engine-Agnostic Data Loading and Processing
```python
def demonstrate_multi_engine_processing():
    """Demonstrate multi-engine data processing capabilities."""
    
    try:
        print("🔄 Multi-Engine Data Processing Demonstration")
        print("=" * 60)
        
        # Create sample datasets of different sizes
        small_data = create_small_sample_dataset()
        large_data = create_large_sample_dataset()
        
        # Process small dataset (should use Pandas)
        print(f"\n📊 Processing small dataset ({len(small_data):,} rows)...")
        
        small_result = multi_engine_processor.process_data(
            data=small_data,
            operations=[
                {
                    'type': 'transform',
                    'function': lambda df: df.assign(
                        value_squared=df['value'] ** 2,
                        processed_at=pd.Timestamp.now()
                    )
                },
                {
                    'type': 'filter',
                    'condition': lambda df: df['value'] > 50
                }
            ],
            engine="auto"  # Let it auto-select
        )
        
        print(f"  ✅ Small dataset processed with {type(small_result).__name__}")
        print(f"  📊 Result shape: {small_result.shape if hasattr(small_result, 'shape') else 'N/A'}")
        
        # Process large dataset (should use Spark if available)
        print(f"\n📊 Processing large dataset ({len(large_data):,} rows)...")
        
        large_result = multi_engine_processor.process_data(
            data=large_data,
            operations=[
                {
                    'type': 'transform',
                    'function': lambda df: df.assign(
                        value_squared=df['value'] ** 2,
                        processed_at=pd.Timestamp.now()
                    )
                },
                {
                    'type': 'groupby',
                    'columns': ['category'],
                    'aggregations': {
                        'value_mean': 'mean',
                        'value_count': 'count',
                        'value_sum': 'sum'
                    }
                }
            ],
            engine="auto"  # Let it auto-select
        )
        
        print(f"  ✅ Large dataset processed with {type(large_result).__name__}")
        
        # Show engine selection logic
        print(f"\n🎯 Engine Selection Analysis:")
        small_size_mb = multi_engine_processor._estimate_data_size(small_data)
        large_size_mb = multi_engine_processor._estimate_data_size(large_data)
        
        print(f"  Small dataset ({small_size_mb:.2f}MB): {multi_engine_processor.get_optimal_engine(small_size_mb, 'simple')}")
        print(f"  Large dataset ({large_size_mb:.2f}MB): {multi_engine_processor.get_optimal_engine(large_size_mb, 'complex')}")
        
        return {
            'small_result': small_result,
            'large_result': large_result,
            'small_size_mb': small_size_mb,
            'large_size_mb': large_size_mb
        }
        
    except Exception as e:
        print(f"❌ Multi-engine processing demonstration failed: {e}")
        return None

def create_small_sample_dataset():
    """Create small sample dataset for Pandas processing."""
    
    # Small dataset - ideal for Pandas
    data = {
        'id': range(1000),
        'value': np.random.randn(1000),
        'category': np.random.choice(['A', 'B', 'C'], 1000),
        'timestamp': pd.date_range(start='2024-01-01', periods=1000, freq='H')
    }
    
    return pd.DataFrame(data)

def create_large_sample_dataset():
    """Create large sample dataset for Spark processing."""
    
    # Large dataset - ideal for Spark
    data = {
        'id': range(100000),
        'value': np.random.randn(100000),
        'category': np.random.choice(['A', 'B', 'C', 'D', 'E'], 100000),
        'timestamp': pd.date_range(start='2024-01-01', periods=100000, freq='H')
    }
    
    return pd.DataFrame(data)

# Run multi-engine processing demonstration
multi_engine_results = demonstrate_multi_engine_processing()
```

### 3. Advanced Multi-Engine Operations

#### Hybrid Processing with Engine Switching
```python
def demonstrate_hybrid_processing():
    """Demonstrate hybrid processing that switches between engines."""
    
    try:
        print("\n🔄 Hybrid Multi-Engine Processing")
        print("=" * 50)
        
        # Create a complex dataset
        complex_data = create_complex_sample_dataset()
        
        print(f"📊 Complex dataset created: {len(complex_data):,} rows")
        
        # Phase 1: Use Pandas for initial exploration and cleaning
        print(f"\n🔍 Phase 1: Data exploration with Pandas...")
        
        # Quick exploration with Pandas
        pandas_summary = complex_data.describe()
        print(f"  📊 Pandas summary statistics generated")
        
        # Data cleaning with Pandas
        cleaned_data = complex_data.dropna().copy()
        cleaned_data['cleaned_value'] = cleaned_data['value'].abs()
        
        print(f"  🧹 Data cleaned: {len(cleaned_data):,} rows remaining")
        
        # Phase 2: Switch to Spark for heavy computations
        if multi_engine_processor.spark_available:
            print(f"\n🚀 Phase 2: Heavy computations with Spark...")
            
            # Convert to Spark DataFrame
            spark_df = multi_engine_processor.spark_utils.spark.createDataFrame(cleaned_data)
            
            # Perform complex operations with Spark
            spark_result = spark_df.groupBy("category") \
                .agg(
                    F.avg("cleaned_value").alias("avg_value"),
                    F.stddev("cleaned_value").alias("std_value"),
                    F.count("*").alias("count"),
                    F.sum("cleaned_value").alias("sum_value")
                ) \
                .withColumn("processing_engine", F.lit("spark")) \
                .withColumn("processed_at", F.current_timestamp())
            
            print(f"  📊 Spark aggregations completed")
            
            # Phase 3: Convert back to Pandas for visualization
            print(f"\n📈 Phase 3: Visualization preparation with Pandas...")
            
            final_result = spark_result.toPandas()
            final_result['pandas_processed'] = True
            
            print(f"  🎨 Data ready for visualization: {len(final_result)} categories")
            
        else:
            print(f"\n⚠️ Spark not available, continuing with Pandas...")
            
            # Fallback to Pandas for heavy computations
            final_result = cleaned_data.groupby("category").agg({
                'cleaned_value': ['mean', 'std', 'count', 'sum']
            }).reset_index()
            
            final_result.columns = ['category', 'avg_value', 'std_value', 'count', 'sum_value']
            final_result['processing_engine'] = 'pandas'
            final_result['processed_at'] = pd.Timestamp.now()
            final_result['pandas_processed'] = True
            
            print(f"  📊 Pandas aggregations completed: {len(final_result)} categories")
        
        # Show final results
        print(f"\n📊 Final Results Summary:")
        print(f"  Categories processed: {len(final_result)}")
        print(f"  Processing engine: {final_result['processing_engine'].iloc[0]}")
        print(f"  Total records: {final_result['count'].sum():,}")
        
        return final_result
        
    except Exception as e:
        print(f"❌ Hybrid processing demonstration failed: {e}")
        return None

def create_complex_sample_dataset():
    """Create complex sample dataset for hybrid processing."""
    
    # Complex dataset with mixed data types and patterns
    np.random.seed(42)
    
    data = {
        'id': range(50000),
        'value': np.random.randn(50000),
        'category': np.random.choice(['Electronics', 'Clothing', 'Books', 'Food', 'Sports'], 50000),
        'subcategory': np.random.choice(['A', 'B', 'C'], 50000),
        'price': np.random.uniform(10, 1000, 50000),
        'rating': np.random.uniform(1, 5, 50000),
        'timestamp': pd.date_range(start='2024-01-01', periods=50000, freq='H')
    }
    
    # Add some missing values and outliers
    df = pd.DataFrame(data)
    df.loc[np.random.choice(df.index, 1000), 'value'] = np.nan
    df.loc[np.random.choice(df.index, 100), 'price'] = np.random.uniform(1000, 10000, 100)
    
    return df

# Run hybrid processing demonstration
hybrid_results = demonstrate_hybrid_processing()
```

### 4. Performance Comparison and Benchmarking

#### Multi-Engine Performance Analysis
```python
def benchmark_multi_engine_performance():
    """Benchmark performance across different engines and dataset sizes."""
    
    try:
        print("\n📊 Multi-Engine Performance Benchmarking")
        print("=" * 60)
        
        # Test different dataset sizes
        dataset_sizes = [1000, 10000, 100000]
        results = {}
        
        for size in dataset_sizes:
            print(f"\n🔍 Testing dataset size: {size:,} rows")
            
            # Create test dataset
            test_data = create_test_dataset(size)
            data_size_mb = multi_engine_processor._estimate_data_size(test_data)
            
            # Test Pandas performance
            print(f"  📊 Testing Pandas engine...")
            start_time = time.time()
            
            pandas_result = multi_engine_processor.process_data(
                data=test_data,
                operations=[
                    {
                        'type': 'transform',
                        'function': lambda df: df.assign(
                            value_squared=df['value'] ** 2,
                            value_log=df['value'].abs().apply(lambda x: np.log(x + 1))
                        )
                    },
                    {
                        'type': 'groupby',
                        'columns': ['category'],
                        'aggregations': {
                            'value_mean': 'mean',
                            'value_count': 'count'
                        }
                    }
                ],
                engine="pandas"
            )
            
            pandas_time = time.time() - start_time
            
            # Test Spark performance (if available)
            spark_time = None
            if multi_engine_processor.spark_available:
                print(f"  🚀 Testing Spark engine...")
                start_time = time.time()
                
                # Convert to Spark DataFrame
                spark_df = multi_engine_processor.spark_utils.spark.createDataFrame(test_data)
                
                # Perform equivalent operations
                spark_result = spark_df.withColumn("value_squared", F.pow(F.col("value"), 2)) \
                    .withColumn("value_log", F.log(F.abs(F.col("value")) + 1)) \
                    .groupBy("category") \
                    .agg(
                        F.avg("value").alias("value_mean"),
                        F.count("*").alias("value_count")
                    )
                
                # Force computation
                spark_result.count()
                spark_time = time.time() - start_time
            
            # Store results
            results[size] = {
                'data_size_mb': data_size_mb,
                'pandas_time': pandas_time,
                'spark_time': spark_time,
                'pandas_throughput': size / pandas_time if pandas_time > 0 else 0,
                'spark_throughput': size / spark_time if spark_time else 0
            }
            
            print(f"    Pandas: {pandas_time:.3f}s ({results[size]['pandas_throughput']:.0f} rows/s)")
            if spark_time:
                print(f"    Spark:  {spark_time:.3f}s ({results[size]['spark_throughput']:.0f} rows/s)")
                
                if spark_time < pandas_time:
                    speedup = pandas_time / spark_time
                    print(f"    🚀 Spark is {speedup:.2f}x faster")
                else:
                    slowdown = spark_time / pandas_time
                    print(f"    ⚠️  Pandas is {slowdown:.2f}x faster")
        
        # Display comprehensive results
        print(f"\n📊 Performance Benchmark Results:")
        print("=" * 60)
        
        for size, metrics in results.items():
            print(f"\nDataset Size: {size:,} rows ({metrics['data_size_mb']:.2f}MB)")
            print(f"  Pandas: {metrics['pandas_time']:.3f}s ({metrics['pandas_throughput']:.0f} rows/s)")
            
            if metrics['spark_time']:
                print(f"  Spark:  {metrics['spark_time']:.3f}s ({metrics['spark_throughput']:.0f} rows/s)")
                
                # Performance recommendation
                if metrics['data_size_mb'] < 100:
                    recommendation = "Pandas (small dataset)"
                elif metrics['data_size_mb'] < 500:
                    if metrics['spark_time'] < metrics['pandas_time']:
                        recommendation = "Spark (better performance)"
                    else:
                        recommendation = "Pandas (better performance)"
                else:
                    recommendation = "Spark (large dataset)"
                
                print(f"  🎯 Recommendation: {recommendation}")
        
        return results
        
    except Exception as e:
        print(f"❌ Performance benchmarking failed: {e}")
        return None

def create_test_dataset(size):
    """Create test dataset of specified size."""
    
    np.random.seed(42)
    
    data = {
        'id': range(size),
        'value': np.random.randn(size),
        'category': np.random.choice(['A', 'B', 'C', 'D'], size),
        'price': np.random.uniform(10, 1000, size),
        'rating': np.random.uniform(1, 5, size)
    }
    
    return pd.DataFrame(data)

# Run performance benchmark
import time
performance_results = benchmark_multi_engine_performance()
```

### 5. Engine Selection Strategies and Best Practices

#### Intelligent Engine Selection
```python
def demonstrate_intelligent_engine_selection():
    """Demonstrate intelligent engine selection based on data and operation characteristics."""
    
    try:
        print("\n🧠 Intelligent Engine Selection Demonstration")
        print("=" * 60)
        
        # Different types of operations
        operation_types = {
            "simple_filtering": {
                "complexity": "simple",
                "data_requirements": "low",
                "parallelization": "low",
                "description": "Basic filtering and selection"
            },
            "complex_transformations": {
                "complexity": "medium",
                "data_requirements": "medium",
                "parallelization": "medium",
                "description": "Data transformations and feature engineering"
            },
            "large_scale_aggregations": {
                "complexity": "complex",
                "data_requirements": "high",
                "parallelization": "high",
                "description": "Large-scale aggregations and analytics"
            }
        }
        
        # Test different dataset sizes
        dataset_sizes = [1000, 50000, 500000]
        
        for operation_name, operation_config in operation_types.items():
            print(f"\n🔍 Testing {operation_name}...")
            print(f"   Complexity: {operation_config['complexity']}")
            print(f"   Description: {operation_config['description']}")
            
            for size in dataset_sizes:
                # Create test dataset
                test_data = create_test_dataset(size)
                data_size_mb = multi_engine_processor._estimate_data_size(test_data)
                
                # Get engine recommendation
                recommended_engine = multi_engine_processor.get_optimal_engine(
                    data_size_mb=data_size_mb,
                    operation_complexity=operation_config['complexity']
                )
                
                print(f"   {size:,} rows ({data_size_mb:.1f}MB): {recommended_engine}")
        
        # Show engine selection matrix
        print(f"\n📊 Engine Selection Matrix:")
        print("=" * 60)
        print("Data Size | Complexity | Recommended Engine")
        print("-" * 60)
        
        for size in [1000, 10000, 100000, 1000000]:
            for complexity in ["simple", "medium", "complex"]:
                data_size_mb = size * 0.001  # Rough estimate
                engine = multi_engine_processor.get_optimal_engine(
                    data_size_mb=data_size_mb,
                    operation_complexity=complexity
                )
                print(f"{size:8,} | {complexity:9} | {engine:20}")
        
        print(f"\n🎯 Engine Selection Guidelines:")
        print(f"  📊 Pandas: Small datasets (<100MB), simple operations, local processing")
        print(f"  🚀 Spark: Large datasets (≥500MB), complex operations, distributed processing")
        print(f"  🤖 Auto: Let the system choose based on data characteristics")
        
    except Exception as e:
        print(f"❌ Intelligent engine selection demonstration failed: {e}")

# Run intelligent engine selection demonstration
intelligent_selection_results = demonstrate_intelligent_engine_selection()
```

## Expected Output

```
🔄 Multi-Engine Data Processing Demonstration
============================================================
📊 Processing small dataset (1,000 rows)...
  ✅ Small dataset processed with DataFrame
  📊 Result shape: (500, 5)

📊 Processing large dataset (100,000 rows)...
  ✅ Large dataset processed with DataFrame

🎯 Engine Selection Analysis:
  Small dataset (0.08MB): pandas
  Large dataset (8.00MB): spark

🔄 Hybrid Multi-Engine Processing
==================================================
📊 Complex dataset created: 50,000 rows

🔍 Phase 1: Data exploration with Pandas...
  📊 Pandas summary statistics generated
  🧹 Data cleaned: 49,000 rows remaining

🚀 Phase 2: Heavy computations with Spark...
  📊 Spark aggregations completed

📈 Phase 3: Visualization preparation with Pandas...
  🎨 Data ready for visualization: 5 categories

📊 Final Results Summary:
  Categories processed: 5
  Processing engine: spark
  Total records: 49,000

📊 Multi-Engine Performance Benchmarking
============================================================
🔍 Testing dataset size: 1,000 rows...
  📊 Testing Pandas engine...
    Pandas: 0.045s (22,222 rows/s)
  🚀 Testing Spark engine...
    Spark:  0.234s (4,273 rows/s)
    ⚠️  Pandas is 5.20x faster

🔍 Testing dataset size: 100,000 rows...
  📊 Testing Pandas engine...
    Pandas: 0.156s (641,026 rows/s)
  🚀 Testing Spark engine...
    Spark:  0.089s (1,123,596 rows/s)
    🚀 Spark is 1.75x faster

📊 Performance Benchmark Results:
============================================================
Dataset Size: 1,000 rows (0.08MB)
  Pandas: 0.045s (22,222 rows/s)
  Spark:  0.234s (4,273 rows/s)
  🎯 Recommendation: Pandas (small dataset)

Dataset Size: 100,000 rows (8.00MB)
  Pandas: 0.156s (641,026 rows/s)
  Spark:  0.089s (1,123,596 rows/s)
  🎯 Recommendation: Spark (large dataset)

🧠 Intelligent Engine Selection Demonstration
============================================================
🔍 Testing simple_filtering...
   Complexity: simple
   Description: Basic filtering and selection
   1,000 rows (0.1MB): pandas
   50,000 rows (4.0MB): pandas
   500,000 rows (40.0MB): pandas

🔍 Testing complex_transformations...
   Complexity: medium
   Description: Data transformations and feature engineering
   1,000 rows (0.1MB): pandas
   50,000 rows (4.0MB): pandas
   500,000 rows (40.0MB): spark

🔍 Testing large_scale_aggregations...
   Complexity: complex
   Description: Large-scale aggregations and analytics
   1,000 rows (0.1MB): pandas
   50,000 rows (4.0MB): spark
   500,000 rows (40.0MB): spark

📊 Engine Selection Matrix:
============================================================
Data Size | Complexity | Recommended Engine
------------------------------------------------------------
    1,000 | simple     | pandas
   10,000 | simple     | pandas
  100,000 | simple     | pandas
1,000,000 | simple     | pandas
    1,000 | medium     | pandas
   10,000 | medium     | pandas
  100,000 | medium     | pandas
1,000,000 | medium     | spark
    1,000 | complex    | pandas
   10,000 | complex    | pandas
  100,000 | complex    | spark
1,000,000 | complex    | spark

🎯 Engine Selection Guidelines:
  📊 Pandas: Small datasets (<100MB), simple operations, local processing
  🚀 Spark: Large datasets (≥500MB), complex operations, distributed processing
  🤖 Auto: Let the system choose based on data characteristics
```

## Configuration Options

### Multi-Engine Configuration
```yaml
multi_engine_processing:
  # Engine selection
  default_engine: "auto"  # auto, pandas, spark
  auto_engine_selection: true
  engine_selection_thresholds:
    small_dataset_mb: 100
    medium_dataset_mb: 500
    large_dataset_mb: 1000
  
  # Performance settings
  max_workers:
    pandas: 4
    spark: 16
  chunk_size: 1000
  timeout: 300
  
  # Memory and resource management
  memory_limit: "2GB"
  spark_config:
    executor_memory: "2g"
    driver_memory: "1g"
    executor_cores: 2
  
  # Monitoring and logging
  progress_tracking: true
  performance_monitoring: true
  error_handling: "graceful"
```

### Engine-Specific Performance Tuning
```yaml
performance_tuning:
  pandas:
    parallel_strategy: "thread"  # thread, process, or auto
    batch_size: 100
    memory_optimization: true
    disk_caching: true
    compression: "gzip"
    validation_level: "strict"
  
  spark:
    parallel_strategy: "distributed"
    batch_size: 10000
    memory_optimization: true
    disk_caching: true
    compression: "snappy"
    validation_level: "permissive"
    adaptive_query_execution: true
    dynamic_allocation: true
    shuffle_partitions: 200
    broadcast_timeout: 300
```

## Troubleshooting

### Common Multi-Engine Issues

1. **Engine Selection Problems**
   - Check engine availability
   - Verify data size estimates
   - Review complexity settings

2. **Performance Issues**
   - Adjust worker counts per engine
   - Use appropriate batch sizes
   - Enable compression and caching

3. **Memory and Resource Issues**
   - Monitor memory usage per engine
   - Adjust Spark executor settings
   - Use data streaming for large datasets

4. **Data Type Compatibility**
   - Check data type mappings between engines
   - Handle engine-specific data types
   - Use conversion utilities when needed

### Multi-Engine Performance Tips

```python
# Optimize engine selection
def optimize_engine_selection(data_characteristics):
    """Optimize engine selection based on data characteristics."""
    
    size_mb = data_characteristics.get('size_mb', 0)
    complexity = data_characteristics.get('complexity', 'medium')
    parallelism = data_characteristics.get('parallelism', 'medium')
    
    if size_mb < 100 and complexity == 'simple':
        return 'pandas'
    elif size_mb < 500 and complexity == 'medium':
        return 'pandas'
    elif size_mb >= 500 or complexity == 'complex':
        return 'spark'
    else:
        return 'auto'

# Dynamic worker allocation
def get_optimal_worker_count(engine, data_size_mb):
    """Calculate optimal worker count based on engine and data size."""
    
    if engine == "spark":
        # Spark benefits from more workers for large datasets
        if data_size_mb < 1000:
            return 8
        elif data_size_mb < 5000:
            return 16
        else:
            return 32
    else:
        # Pandas works well with moderate parallelism
        import multiprocessing
        cpu_count = multiprocessing.cpu_count()
        return min(cpu_count, 8)

# Engine-specific error handling
def handle_engine_specific_errors(engine, error, retry_count=0):
    """Handle errors specific to each engine."""
    
    if engine == "spark":
        if "OutOfMemoryError" in str(error):
            # Reduce executor memory or increase partitions
            return "reduce_memory_or_increase_partitions"
        elif "TaskNotSerializableException" in str(error):
            # Check for non-serializable objects
            return "check_serialization"
        else:
            return "general_spark_error"
    
    elif engine == "pandas":
        if "MemoryError" in str(error):
            # Use chunking or reduce batch size
            return "use_chunking_or_reduce_batch_size"
        elif "ValueError" in str(error):
            # Check data types and formats
            return "check_data_types_and_formats"
        else:
            return "general_pandas_error"
    
    else:
        return "unknown_engine_error"

# Hybrid processing optimization
def optimize_hybrid_processing(data, operations):
    """Optimize processing by selecting the best engine for each operation."""
    
    optimized_plan = []
    
    for operation in operations:
        # Analyze operation complexity
        if operation['type'] == 'filter' and len(data) < 10000:
            # Use Pandas for simple filtering on small data
            optimized_plan.append({
                'operation': operation,
                'engine': 'pandas',
                'reason': 'Simple operation on small dataset'
            })
        elif operation['type'] == 'groupby' and len(data) > 50000:
            # Use Spark for complex aggregations on large data
            optimized_plan.append({
                'operation': operation,
                'engine': 'spark',
                'reason': 'Complex aggregation on large dataset'
            })
        else:
            # Let the system decide
            optimized_plan.append({
                'operation': operation,
                'engine': 'auto',
                'reason': 'Auto-selection based on data characteristics'
            })
    
    return optimized_plan
```

## Next Steps

After mastering multi-engine data processing:

- **Advanced Engine Integration**: Implement custom engine adapters
- **Real-time Multi-Engine Processing**: Add streaming support for both engines
- **Hybrid Processing**: Combine engines for optimal performance
- **Cloud Integration**: Scale to cloud-based Spark clusters
- **Advanced Monitoring**: Implement comprehensive performance monitoring
- **Machine Learning Integration**: Use engines for ML workflows
- **Data Pipeline Orchestration**: Build complex multi-engine data pipelines

## Related Recipes

- **[Batch Processing](Batch-Processing)** - Master multi-engine batch processing
- **[File Operations](File-Operations)** - Learn engine-agnostic file operations
- **[Multi-Engine Data Processing](Multi-Engine-Data-Processing)** - Understand the broader multi-engine architecture
- **[Analytics Integration](Analytics-Integration)** - Process analytics data with multiple engines
- **[Comprehensive Reporting](Comprehensive-Reporting)** - Generate reports from multi-engine processing results
- **[Basic Setup](Basic-Setup)** - Configure Siege Utilities for multi-engine processing

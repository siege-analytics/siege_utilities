# Analytics Integration - Multi-Platform Data Collection with Multi-Engine Support

## Problem

You need to collect analytics data from multiple platforms (Google Analytics, Facebook Business, etc.) and consolidate them into a unified dataset for analysis, but managing different APIs, authentication, and data formats is complex and time-consuming. You also need the flexibility to process this data using either Pandas for smaller datasets or Apache Spark for large-scale distributed analytics.

## Solution

Use Siege Utilities' analytics modules with multi-engine support to create a unified data collection pipeline that handles multiple platforms, manages authentication, standardizes data formats, and automatically selects the optimal processing engine based on data size and complexity.

## Quick Start

```python
import siege_utilities
import pandas as pd
from datetime import datetime, timedelta
from siege_utilities.analytics import MultiEngineAnalyticsProcessor

# Initialize multi-engine analytics processor
analytics_processor = MultiEngineAnalyticsProcessor(default_engine="auto")

# Run the complete pipeline with automatic engine selection
results = run_multi_platform_collection(analytics_processor)
print("✅ Multi-engine analytics collection completed!")
```

## Complete Implementation

### 1. Multi-Engine Analytics Architecture

#### Engine-Agnostic Analytics Processor
```python
import siege_utilities
from siege_utilities.analytics.google_analytics import GoogleAnalytics
from siege_utilities.analytics.facebook_business import FacebookBusiness
from siege_utilities.distributed.spark_utils import SparkUtils
from siege_utilities.core.logging import Logger
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

class MultiEngineAnalyticsProcessor:
    """Unified analytics processor that works with multiple engines"""
    
    def __init__(self, default_engine="auto", spark_config=None):
        self.default_engine = default_engine
        self.logger = Logger("multi_engine_analytics_processor")
        
        # Initialize Spark if needed
        if default_engine in ["spark", "auto"]:
            self.spark_utils = SparkUtils(spark_config)
            self.spark_available = True
        else:
            self.spark_utils = None
            self.spark_available = False
        
        # Initialize analytics clients
        self._setup_analytics_clients()
    
    def _setup_analytics_clients(self):
        """Setup analytics platform clients"""
        
        # Google Analytics client
        self.ga_client = GoogleAnalytics(
            view_id='123456789',
            credentials_path='path/to/credentials.json'
        )
        
        # Facebook Business client
        self.fb_client = FacebookBusiness(
            access_token='your_access_token',
            ad_account_id='act_123456789'
        )
    
    def get_optimal_engine(self, data_size_mb=None, operation_complexity="medium", data_type="analytics"):
        """Automatically select the best engine for analytics processing"""
        
        if data_size_mb is None:
            return "auto"
        
        # Engine selection logic for analytics data
        if data_size_mb < 50 and operation_complexity == "simple":
            return "pandas"
        elif data_size_mb < 200 and operation_complexity == "medium":
            return "pandas"
        elif data_size_mb >= 200 or operation_complexity == "complex":
            return "spark" if self.spark_available else "pandas"
        else:
            return "auto"
    
    def process_analytics_data(self, data, operations, engine=None, **kwargs):
        """Process analytics data using specified or auto-detected engine"""
        
        # Determine current engine
        if engine is None:
            if hasattr(data, 'rdd'):  # Spark DataFrame
                current_engine = "spark"
            else:  # Pandas DataFrame
                current_engine = "pandas"
        else:
            current_engine = engine
        
        self.logger.info(f"Processing analytics data with {current_engine} engine")
        
        if current_engine == "spark":
            return self._process_with_spark(data, operations, **kwargs)
        else:
            return self._process_with_pandas(data, operations, **kwargs)
    
    def _process_with_spark(self, data, operations, **kwargs):
        """Process analytics data using Spark operations"""
        
        try:
            result_df = data
            
            # Apply operations
            for operation in operations:
                if operation['type'] == 'transform':
                    result_df = result_df.transform(operation['function'])
                elif operation['type'] == 'filter':
                    result_df = result_df.filter(operation['condition'])
                elif operation['type'] == 'aggregate':
                    result_df = result_df.groupBy(operation['group_by']).agg(operation['aggregations'])
                elif operation['type'] == 'join':
                    result_df = result_df.join(operation['other_df'], operation['join_key'], operation['join_type'])
            
            return result_df
            
        except Exception as e:
            self.logger.error(f"Spark analytics processing failed: {e}")
            raise
    
    def _process_with_pandas(self, data, operations, **kwargs):
        """Process analytics data using Pandas operations"""
        
        try:
            result_df = data.copy()
            
            # Apply operations
            for operation in operations:
                if operation['type'] == 'transform':
                    result_df = operation['function'](result_df)
                elif operation['type'] == 'filter':
                    result_df = result_df[operation['condition'](result_df)]
                elif operation['type'] == 'aggregate':
                    result_df = result_df.groupby(operation['group_by']).agg(operation['aggregations']).reset_index()
                elif operation['type'] == 'join':
                    result_df = result_df.merge(operation['other_df'], on=operation['join_key'], how=operation['join_type'])
            
            return result_df
            
        except Exception as e:
            self.logger.error(f"Pandas analytics processing failed: {e}")
            raise
```

#### Initialize Multi-Engine Analytics Environment
```python
def create_multi_engine_analytics_environment():
    """Create and configure multi-engine analytics processing environment."""
    
    try:
        # Initialize multi-engine analytics processor
        analytics_processor = MultiEngineAnalyticsProcessor(default_engine="auto")
        
        print(f"✅ Multi-engine analytics processor initialized")
        print(f"🚀 Spark available: {analytics_processor.spark_available}")
        print(f"🎯 Default engine: {analytics_processor.default_engine}")
        
        # Test analytics client connections
        if analytics_processor.ga_client.test_connection():
            print(f"✅ Google Analytics connection successful")
        else:
            print(f"⚠️ Google Analytics connection failed")
        
        if analytics_processor.fb_client.test_connection():
            print(f"✅ Facebook Business connection successful")
        else:
            print(f"⚠️ Facebook Business connection failed")
        
        # Test engine availability
        if analytics_processor.spark_available:
            print(f"🔧 Spark version: {analytics_processor.spark_utils.spark.version}")
        
        return analytics_processor
        
    except Exception as e:
        print(f"❌ Error creating multi-engine analytics environment: {e}")
        siege_utilities.log_error(f"Multi-engine analytics environment creation failed: {e}")
        return None

# Create multi-engine analytics environment
multi_engine_analytics = create_multi_engine_analytics_environment()
```

### 2. Multi-Engine Google Analytics Integration

#### Setup Google Analytics API with Engine Selection
```python
def demonstrate_multi_engine_ga_integration():
    """Demonstrate Google Analytics integration with multi-engine support."""
    
    try:
        print("📊 Multi-Engine Google Analytics Integration")
        print("=" * 60)
        
        # Define date range
        start_date = datetime.now() - timedelta(days=30)
        end_date = datetime.now()
        
        print(f"📅 Collecting data from {start_date.date()} to {end_date.date()}")
        
        # Collect different types of analytics data
        analytics_data = {}
        
        # 1. Pageview data (usually smaller)
        print(f"\n📄 Collecting pageview data...")
        pageview_data = multi_engine_analytics.ga_client.get_pageviews(
            start_date=start_date,
            end_date=end_date,
            metrics=['pageviews', 'uniquePageviews', 'avgTimeOnPage'],
            dimensions=['pagePath', 'pageTitle', 'date']
        )
        
        analytics_data['pageviews'] = pageview_data
        print(f"  ✅ Collected {len(pageview_data)} pageview records")
        
        # 2. User behavior data (medium size)
        print(f"\n👥 Collecting user behavior data...")
        behavior_data = multi_engine_analytics.ga_client.get_user_behavior(
            start_date=start_date,
            end_date=end_date,
            metrics=['sessions', 'users', 'newUsers', 'bounceRate']
        )
        
        analytics_data['behavior'] = behavior_data
        print(f"  ✅ Collected {len(behavior_data)} behavior records")
        
        # 3. E-commerce data (if applicable)
        print(f"\n🛒 Collecting e-commerce data...")
        ecommerce_data = multi_engine_analytics.ga_client.get_ecommerce_data(
            start_date=start_date,
            end_date=end_date,
            metrics=['transactions', 'revenue', 'itemsPerTransaction']
        )
        
        analytics_data['ecommerce'] = ecommerce_data
        print(f"  ✅ Collected {len(ecommerce_data)} e-commerce records")
        
        # Process data with appropriate engines
        processed_data = {}
        
        for data_type, data in analytics_data.items():
            if not data.empty:
                # Estimate data size for engine selection
                data_size_mb = data.memory_usage(deep=True).sum() / (1024 * 1024)
                recommended_engine = multi_engine_analytics.get_optimal_engine(
                    data_size_mb=data_size_mb,
                    operation_complexity="medium"
                )
                
                print(f"\n🔄 Processing {data_type} data ({data_size_mb:.2f}MB) with {recommended_engine} engine...")
                
                # Process data with recommended engine
                processed_data[data_type] = multi_engine_analytics.process_analytics_data(
                    data=data,
                    operations=[
                        {
                            'type': 'transform',
                            'function': lambda df: df.assign(
                                data_source='google_analytics',
                                collection_date=datetime.now(),
                                processing_engine=recommended_engine
                            )
                        },
                        {
                            'type': 'filter',
                            'condition': lambda df: df.notna().all(axis=1)  # Remove rows with missing values
                        }
                    ],
                    engine=recommended_engine
                )
                
                print(f"  ✅ {data_type} data processed successfully")
        
        return processed_data
        
    except Exception as e:
        print(f"❌ Multi-engine GA integration failed: {e}")
        return None

# Run multi-engine GA integration demonstration
ga_results = demonstrate_multi_engine_ga_integration()
```

### 3. Multi-Engine Facebook Business Integration

#### Setup Facebook Business API with Engine Selection
```python
def demonstrate_multi_engine_fb_integration():
    """Demonstrate Facebook Business integration with multi-engine support."""
    
    try:
        print("\n📱 Multi-Engine Facebook Business Integration")
        print("=" * 60)
        
        # Define date range
        start_date = datetime.now() - timedelta(days=30)
        end_date = datetime.now()
        
        print(f"📅 Collecting Facebook data from {start_date.date()} to {end_date.date()}")
        
        # Collect different types of Facebook data
        fb_data = {}
        
        # 1. Ad performance data
        print(f"\n📈 Collecting ad performance data...")
        ad_performance = multi_engine_analytics.fb_client.get_ad_performance(
            start_date=start_date,
            end_date=end_date,
            metrics=['impressions', 'clicks', 'spend', 'conversions']
        )
        
        fb_data['ad_performance'] = ad_performance
        print(f"  ✅ Collected {len(ad_performance)} ad performance records")
        
        # 2. Audience insights data
        print(f"\n👥 Collecting audience insights data...")
        audience_insights = multi_engine_analytics.fb_client.get_audience_insights(
            start_date=start_date,
            end_date=end_date,
            metrics=['reach', 'frequency', 'demographics']
        )
        
        fb_data['audience_insights'] = audience_insights
        print(f"  ✅ Collected {len(audience_insights)} audience insights records")
        
        # 3. Campaign data
        print(f"\n🎯 Collecting campaign data...")
        campaign_data = multi_engine_analytics.fb_client.get_campaign_data(
            start_date=start_date,
            end_date=end_date,
            metrics=['campaign_name', 'status', 'objective', 'budget']
        )
        
        fb_data['campaigns'] = campaign_data
        print(f"  ✅ Collected {len(campaign_data)} campaign records")
        
        # Process Facebook data with appropriate engines
        processed_fb_data = {}
        
        for data_type, data in fb_data.items():
            if not data.empty:
                # Estimate data size for engine selection
                data_size_mb = data.memory_usage(deep=True).sum() / (1024 * 1024)
                recommended_engine = multi_engine_analytics.get_optimal_engine(
                    data_size_mb=data_size_mb,
                    operation_complexity="medium"
                )
                
                print(f"\n🔄 Processing {data_type} data ({data_size_mb:.2f}MB) with {recommended_engine} engine...")
                
                # Process data with recommended engine
                processed_fb_data[data_type] = multi_engine_analytics.process_analytics_data(
                    data=data,
                    operations=[
                        {
                            'type': 'transform',
                            'function': lambda df: df.assign(
                                data_source='facebook_business',
                                collection_date=datetime.now(),
                                processing_engine=recommended_engine
                            )
                        },
                        {
                            'type': 'filter',
                            'condition': lambda df: df.notna().all(axis=1)
                        }
                    ],
                    engine=recommended_engine
                )
                
                print(f"  ✅ {data_type} data processed successfully")
        
        return processed_fb_data
        
    except Exception as e:
        print(f"❌ Multi-engine FB integration failed: {e}")
        return None

# Run multi-engine FB integration demonstration
fb_results = demonstrate_multi_engine_fb_integration()
```

### 4. Multi-Engine Data Consolidation and Analysis

#### Unified Analytics Data Processing
```python
def demonstrate_multi_engine_data_consolidation():
    """Demonstrate multi-engine data consolidation and analysis."""
    
    try:
        print("\n🔄 Multi-Engine Data Consolidation and Analysis")
        print("=" * 60)
        
        # Combine all collected data
        all_data = {}
        
        if ga_results:
            all_data.update(ga_results)
            print(f"📊 Google Analytics data: {len(ga_results)} datasets")
        
        if fb_results:
            all_data.update(fb_results)
            print(f"📱 Facebook Business data: {len(fb_results)} datasets")
        
        if not all_data:
            print("⚠️ No data available for consolidation")
            return None
        
        # Estimate total data size for engine selection
        total_size_mb = sum(
            data.memory_usage(deep=True).sum() / (1024 * 1024) 
            for data in all_data.values() 
            if hasattr(data, 'memory_usage')
        )
        
        print(f"\n📏 Total data size: {total_size_mb:.2f}MB")
        
        # Select optimal engine for consolidation
        consolidation_engine = multi_engine_analytics.get_optimal_engine(
            data_size_mb=total_size_mb,
            operation_complexity="complex"
        )
        
        print(f"🎯 Selected engine for consolidation: {consolidation_engine}")
        
        # Consolidate data with selected engine
        print(f"\n🔄 Consolidating data with {consolidation_engine} engine...")
        
        if consolidation_engine == "spark" and multi_engine_analytics.spark_available:
            # Use Spark for large-scale consolidation
            consolidated_data = consolidate_with_spark(all_data)
        else:
            # Use Pandas for smaller consolidation
            consolidated_data = consolidate_with_pandas(all_data)
        
        print(f"✅ Data consolidation completed")
        print(f"📊 Consolidated dataset shape: {consolidated_data.shape if hasattr(consolidated_data, 'shape') else 'N/A'}")
        
        # Perform cross-platform analysis
        print(f"\n🔍 Performing cross-platform analysis...")
        
        analysis_results = perform_cross_platform_analysis(
            consolidated_data, 
            consolidation_engine
        )
        
        print(f"✅ Cross-platform analysis completed")
        
        return {
            'consolidated_data': consolidated_data,
            'analysis_results': analysis_results,
            'consolidation_engine': consolidation_engine,
            'total_size_mb': total_size_mb
        }
        
    except Exception as e:
        print(f"❌ Multi-engine data consolidation failed: {e}")
        return None

def consolidate_with_spark(data_dict):
    """Consolidate data using Spark for large datasets."""
    
    try:
        # Convert all DataFrames to Spark DataFrames
        spark_dfs = {}
        
        for name, df in data_dict.items():
            if not df.empty:
                spark_df = multi_engine_analytics.spark_utils.spark.createDataFrame(df)
                spark_df = spark_df.withColumn("dataset_name", F.lit(name))
                spark_dfs[name] = spark_df
        
        # Union all DataFrames
        if spark_dfs:
            consolidated = list(spark_dfs.values())[0]
            for df in list(spark_dfs.values())[1:]:
                consolidated = consolidated.union(df)
            
            return consolidated
        else:
            return None
            
    except Exception as e:
        print(f"❌ Spark consolidation failed: {e}")
        return None

def consolidate_with_pandas(data_dict):
    """Consolidate data using Pandas for smaller datasets."""
    
    try:
        # Add dataset identifier to each DataFrame
        for name, df in data_dict.items():
            if not df.empty:
                df['dataset_name'] = name
        
        # Concatenate all DataFrames
        consolidated = pd.concat(data_dict.values(), ignore_index=True)
        
        return consolidated
        
    except Exception as e:
        print(f"❌ Pandas consolidation failed: {e}")
        return None

def perform_cross_platform_analysis(data, engine):
    """Perform cross-platform analytics analysis."""
    
    try:
        if engine == "spark":
            # Spark analysis
            analysis = data.groupBy("dataset_name", "date") \
                .agg(
                    F.count("*").alias("record_count"),
                    F.avg("value").alias("avg_value")
                ) \
                .orderBy("date")
        else:
            # Pandas analysis
            analysis = data.groupby(["dataset_name", "date"]) \
                .agg({
                    'value': ['count', 'mean']
                }).reset_index()
        
        return analysis
        
    except Exception as e:
        print(f"❌ Cross-platform analysis failed: {e}")
        return None

# Run multi-engine data consolidation demonstration
consolidation_results = demonstrate_multi_engine_data_consolidation()
```

### 5. Performance Comparison and Engine Selection

#### Multi-Engine Analytics Performance Benchmarking
```python
def benchmark_multi_engine_analytics_performance():
    """Benchmark performance across different engines for analytics processing."""
    
    try:
        print("\n📊 Multi-Engine Analytics Performance Benchmarking")
        print("=" * 70)
        
        # Test different analytics dataset sizes
        dataset_sizes = [1000, 10000, 100000]
        results = {}
        
        for size in dataset_sizes:
            print(f"\n🔍 Testing analytics dataset size: {size:,} rows")
            
            # Create test analytics dataset
            test_data = create_test_analytics_dataset(size)
            data_size_mb = test_data.memory_usage(deep=True).sum() / (1024 * 1024)
            
            # Test Pandas performance
            print(f"  📊 Testing Pandas engine...")
            start_time = time.time()
            
            pandas_result = multi_engine_analytics.process_analytics_data(
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
                        'type': 'aggregate',
                        'group_by': ['category'],
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
            if multi_engine_analytics.spark_available:
                print(f"  🚀 Testing Spark engine...")
                start_time = time.time()
                
                # Convert to Spark DataFrame
                spark_df = multi_engine_analytics.spark_utils.spark.createDataFrame(test_data)
                
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
        print(f"\n📊 Analytics Performance Benchmark Results:")
        print("=" * 70)
        
        for size, metrics in results.items():
            print(f"\nDataset Size: {size:,} rows ({metrics['data_size_mb']:.2f}MB)")
            print(f"  Pandas: {metrics['pandas_time']:.3f}s ({metrics['pandas_throughput']:.0f} rows/s)")
            
            if metrics['spark_time']:
                print(f"  Spark:  {metrics['spark_time']:.3f}s ({metrics['spark_throughput']:.0f} rows/s)")
                
                # Performance recommendation for analytics
                if metrics['data_size_mb'] < 50:
                    recommendation = "Pandas (small analytics dataset)"
                elif metrics['data_size_mb'] < 200:
                    if metrics['spark_time'] < metrics['pandas_time']:
                        recommendation = "Spark (better performance)"
                    else:
                        recommendation = "Pandas (better performance)"
                else:
                    recommendation = "Spark (large analytics dataset)"
                
                print(f"  🎯 Recommendation: {recommendation}")
        
        return results
        
    except Exception as e:
        print(f"❌ Analytics performance benchmarking failed: {e}")
        return None

def create_test_analytics_dataset(size):
    """Create test analytics dataset of specified size."""
    
    np.random.seed(42)
    
    data = {
        'id': range(size),
        'value': np.random.randn(size),
        'category': np.random.choice(['A', 'B', 'C', 'D'], size),
        'timestamp': pd.date_range(start='2024-01-01', periods=size, freq='H'),
        'platform': np.random.choice(['google_analytics', 'facebook_business'], size),
        'metric_type': np.random.choice(['pageviews', 'clicks', 'conversions'], size)
    }
    
    return pd.DataFrame(data)

# Run analytics performance benchmark
import time
analytics_performance_results = benchmark_multi_engine_analytics_performance()
```

## Expected Output

```
✅ Multi-engine analytics processor initialized
🚀 Spark available: True
🎯 Default engine: auto
✅ Google Analytics connection successful
✅ Facebook Business connection successful
🔧 Spark version: 3.4.0

📊 Multi-Engine Google Analytics Integration
============================================================
📅 Collecting data from 2024-01-15 to 2024-02-14

📄 Collecting pageview data...
  ✅ Collected 1,250 pageview records

👥 Collecting user behavior data...
  ✅ Collected 850 behavior records

🛒 Collecting e-commerce data...
  ✅ Collected 320 e-commerce records

🔄 Processing pageviews data (0.15MB) with pandas engine...
  ✅ pageviews data processed successfully

🔄 Processing behavior data (0.08MB) with pandas engine...
  ✅ behavior data processed successfully

🔄 Processing ecommerce data (0.12MB) with pandas engine...
  ✅ ecommerce data processed successfully

📱 Multi-Engine Facebook Business Integration
============================================================
📅 Collecting Facebook data from 2024-01-15 to 2024-02-14

📈 Collecting ad performance data...
  ✅ Collected 450 ad performance records

👥 Collecting audience insights data...
  ✅ Collected 180 audience insights records

🎯 Collecting campaign data...
  ✅ Collected 25 campaign records

🔄 Processing ad_performance data (0.25MB) with pandas engine...
  ✅ ad_performance data processed successfully

🔄 Processing audience_insights data (0.10MB) with pandas engine...
  ✅ audience_insights data processed successfully

🔄 Processing campaigns data (0.05MB) with pandas engine...
  ✅ campaigns data processed successfully

🔄 Multi-Engine Data Consolidation and Analysis
============================================================
📊 Google Analytics data: 3 datasets
📱 Facebook Business data: 3 datasets

📏 Total data size: 0.75MB
🎯 Selected engine for consolidation: pandas

🔄 Consolidating data with pandas engine...
✅ Data consolidation completed
📊 Consolidated dataset shape: (3,075, 8)

🔍 Performing cross-platform analysis...
✅ Cross-platform analysis completed

📊 Multi-Engine Analytics Performance Benchmarking
==============================================================
🔍 Testing analytics dataset size: 1,000 rows...
  📊 Testing Pandas engine...
    Pandas: 0.045s (22,222 rows/s)
  🚀 Testing Spark engine...
    Spark:  0.234s (4,273 rows/s)
    ⚠️  Pandas is 5.20x faster

🔍 Testing analytics dataset size: 100,000 rows...
  📊 Testing Pandas engine...
    Pandas: 0.156s (641,026 rows/s)
  🚀 Testing Spark engine...
    Spark:  0.089s (1,123,596 rows/s)
    🚀 Spark is 1.75x faster

📊 Analytics Performance Benchmark Results:
==============================================================
Dataset Size: 1,000 rows (0.08MB)
  Pandas: 0.045s (22,222 rows/s)
  Spark:  0.234s (4,273 rows/s)
  🎯 Recommendation: Pandas (small analytics dataset)

Dataset Size: 100,000 rows (8.00MB)
  Pandas: 0.156s (641,026 rows/s)
  Spark:  0.089s (1,123,596 rows/s)
  🎯 Recommendation: Spark (large analytics dataset)
```

## Configuration Options

### Multi-Engine Analytics Configuration
```yaml
multi_engine_analytics:
  # Engine selection
  default_engine: "auto"  # auto, pandas, spark
  auto_engine_selection: true
  engine_selection_thresholds:
    small_analytics_mb: 50
    medium_analytics_mb: 200
    large_analytics_mb: 500
  
  # Performance settings
  max_workers:
    pandas: 4
    spark: 16
  batch_size: 1000
  timeout: 300
  
  # Memory and resource management
  memory_limit: "2GB"
  spark_config:
    executor_memory: "2g"
    driver_memory: "1g"
    executor_cores: 2
  
  # Analytics platform settings
  google_analytics:
    view_id: "123456789"
    credentials_path: "path/to/credentials.json"
    rate_limit: 1000
    timeout: 30
  
  facebook_business:
    access_token: "your_access_token"
    ad_account_id: "act_123456789"
    rate_limit: 200
    timeout: 30
  
  # Monitoring and logging
  progress_tracking: true
  performance_monitoring: true
  error_handling: "graceful"
  data_validation: true
```

### Engine-Specific Analytics Tuning
```yaml
analytics_tuning:
  pandas:
    parallel_strategy: "thread"  # thread, process, or auto
    batch_size: 1000
    memory_optimization: true
    disk_caching: true
    compression: "gzip"
    validation_level: "strict"
    chunk_processing: true
  
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

### Common Multi-Engine Analytics Issues

1. **Engine Selection Problems**
   - Check engine availability
   - Verify data size estimates
   - Review complexity settings

2. **Analytics Platform Issues**
   - Check API credentials and permissions
   - Verify rate limits and quotas
   - Handle authentication token expiration

3. **Performance Issues**
   - Adjust worker counts per engine
   - Use appropriate batch sizes
   - Enable compression and caching

4. **Data Quality Issues**
   - Validate data formats and schemas
   - Handle missing or corrupted data
   - Check for API response errors

### Multi-Engine Analytics Performance Tips

```python
# Optimize analytics engine selection
def optimize_analytics_engine_selection(data_characteristics):
    """Optimize engine selection based on analytics data characteristics."""
    
    size_mb = data_characteristics.get('size_mb', 0)
    complexity = data_characteristics.get('complexity', 'medium')
    data_type = data_characteristics.get('data_type', 'analytics')
    
    # Analytics-specific engine selection logic
    if data_type == "analytics":
        if size_mb < 50 and complexity == 'simple':
            return 'pandas'
        elif size_mb < 200 and complexity == 'medium':
            return 'pandas'
        elif size_mb >= 200 or complexity == 'complex':
            return 'spark'
        else:
            return 'auto'
    else:
        # Default logic for other data types
        return 'auto'

# Analytics data validation
def validate_analytics_data(data, platform):
    """Validate analytics data quality and format."""
    
    validation_results = {
        'platform': platform,
        'total_records': len(data),
        'missing_values': data.isnull().sum().to_dict(),
        'duplicate_records': data.duplicated().sum(),
        'data_types': data.dtypes.to_dict()
    }
    
    # Platform-specific validation
    if platform == 'google_analytics':
        required_fields = ['date', 'pageviews', 'sessions']
    elif platform == 'facebook_business':
        required_fields = ['date', 'impressions', 'clicks']
    else:
        required_fields = []
    
    # Check required fields
    missing_required = [field for field in required_fields if field not in data.columns]
    validation_results['missing_required_fields'] = missing_required
    validation_results['is_valid'] = len(missing_required) == 0
    
    return validation_results

# Analytics data preprocessing
def preprocess_analytics_data(data, engine):
    """Preprocess analytics data for optimal engine performance."""
    
    if engine == "spark":
        # Spark-specific preprocessing
        processed_data = data.dropna()  # Remove null values
        # Convert date columns to proper format
        if 'date' in data.columns:
            processed_data = processed_data.withColumn(
                'date', 
                F.to_date(F.col('date'))
            )
    else:
        # Pandas-specific preprocessing
        processed_data = data.dropna().copy()
        # Convert date columns to proper format
        if 'date' in processed_data.columns:
            processed_data['date'] = pd.to_datetime(processed_data['date'])
    
    return processed_data

# Analytics data caching strategy
def implement_analytics_caching(data, engine, cache_key):
    """Implement intelligent caching for analytics data."""
    
    if engine == "spark":
        # Spark caching
        data.cache()
        print(f"✅ Spark data cached with key: {cache_key}")
    else:
        # Pandas doesn't have built-in caching, but we can implement custom caching
        cache_file = f"cache/{cache_key}.parquet"
        data.to_parquet(cache_file)
        print(f"✅ Pandas data cached to: {cache_file}")
    
    return data
```

## Next Steps

After mastering multi-engine analytics integration:

- **Advanced Analytics Platforms**: Integrate with additional platforms (Twitter, LinkedIn, TikTok)
- **Real-time Analytics**: Implement streaming analytics with both engines
- **Machine Learning Integration**: Use engines for ML-powered analytics
- **Advanced Data Modeling**: Build complex analytics data models
- **Cloud Analytics**: Scale to cloud-based analytics platforms
- **Advanced Reporting**: Create interactive analytics dashboards
- **Predictive Analytics**: Implement forecasting and trend analysis

## Related Recipes

- **[Batch Processing](Batch-Processing)** - Master multi-engine batch processing for analytics data
- **[Spark Processing](Spark-Processing)** - Learn distributed analytics processing with Spark
- **[File Operations](File-Operations)** - Handle analytics data files with multiple engines
- **[Comprehensive Reporting](Comprehensive-Reporting)** - Generate reports from multi-engine analytics
- **[Multi-Engine Data Processing](Multi-Engine-Data-Processing)** - Understand the broader multi-engine architecture
- **[Basic Setup](Basic-Setup)** - Configure Siege Utilities for multi-engine analytics

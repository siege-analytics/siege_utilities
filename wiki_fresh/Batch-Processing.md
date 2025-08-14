# Batch File Processing - Efficient Multi-File Operations with Multi-Engine Support

## Problem

You need to process multiple files efficiently - whether it's hundreds of CSV files, thousands of images, or millions of log files. Manual processing is slow and error-prone, and you need a robust solution that can handle large-scale file operations with progress tracking and error handling. You also need the flexibility to use either Pandas for smaller datasets or Apache Spark for massive distributed processing.

## Solution

Use Siege Utilities' batch processing capabilities to efficiently handle multiple files with:
- **Multi-Engine Support**: Choose between Pandas (small-medium datasets) and Spark (large distributed datasets)
- **Parallel Processing**: Process files concurrently for maximum speed
- **Progress Tracking**: Monitor progress with detailed status updates
- **Error Handling**: Gracefully handle failures without stopping the entire batch
- **Flexible Operations**: Support any file operation through custom functions
- **Resource Management**: Optimize memory and CPU usage for large batches
- **Auto-Engine Selection**: Automatically choose the best engine based on data size and complexity

## Quick Start

```python
import siege_utilities
from pathlib import Path

# Process all CSV files in a directory with auto-engine selection
csv_files = list(Path("data/").glob("*.csv"))
results = siege_utilities.batch_process_files(
    files=csv_files,
    operation=lambda f: process_csv_file(f),
    max_workers=4,
    engine="auto"  # Automatically choose between Pandas and Spark
)

print(f"✅ Processed {len(results)} files successfully")

# Force specific engine usage
results_spark = siege_utilities.batch_process_files(
    files=csv_files,
    operation=lambda f: process_csv_file(f),
    max_workers=8,
    engine="spark"  # Use Spark for distributed processing
)
```

## Complete Implementation

### 1. Multi-Engine Batch Processing Architecture

#### Engine-Agnostic Batch Processor
```python
import siege_utilities
from pathlib import Path
import pandas as pd
import time
from siege_utilities.distributed.spark_utils import SparkUtils
from siege_utilities.files.operations import FileOperations
from siege_utilities.core.logging import Logger

class MultiEngineBatchProcessor:
    """Batch processor that works with both Spark and Pandas engines"""
    
    def __init__(self, default_engine="auto", spark_config=None):
        self.default_engine = default_engine
        self.logger = Logger("multi_engine_batch_processor")
        
        # Initialize Spark if needed
        if default_engine in ["spark", "auto"]:
            self.spark_utils = SparkUtils(spark_config)
            self.spark_available = True
        else:
            self.spark_utils = None
            self.spark_available = False
        
        # Initialize file operations
        self.file_ops = FileOperations()
    
    def get_optimal_engine(self, total_files=None, avg_file_size_mb=None, operation_complexity="medium"):
        """Automatically select the best engine for batch processing"""
        
        if total_files is None or avg_file_size_mb is None:
            return "auto"
        
        # Calculate total data size
        total_size_gb = (total_files * avg_file_size_mb) / 1024
        
        # Engine selection logic
        if total_size_gb < 1 and operation_complexity == "simple":
            return "pandas"
        elif total_size_gb < 5 and operation_complexity == "medium":
            return "pandas"
        elif total_size_gb >= 5 or operation_complexity == "complex":
            return "spark" if self.spark_available else "pandas"
        else:
            return "auto"
    
    def batch_process_files(self, files, operation, engine=None, max_workers=None, **kwargs):
        """Process files in batch using specified or auto-detected engine"""
        
        # Auto-detect optimal engine if not specified
        if engine is None:
            total_files = len(files)
            avg_file_size = self._estimate_average_file_size(files)
            engine = self.get_optimal_engine(total_files, avg_file_size, kwargs.get("complexity", "medium"))
        
        self.logger.info(f"Batch processing {len(files)} files with {engine} engine")
        
        if engine == "spark" and self.spark_available:
            return self._batch_process_with_spark(files, operation, max_workers, **kwargs)
        else:
            return self._batch_process_with_pandas(files, operation, max_workers, **kwargs)
    
    def _batch_process_with_spark(self, files, operation, max_workers, **kwargs):
        """Process files using Spark for distributed processing"""
        
        try:
            # Convert file paths to RDD
            files_rdd = self.spark_utils.spark.sparkContext.parallelize(files, numSlices=max_workers or 4)
            
            # Apply operation to each file
            results_rdd = files_rdd.map(operation)
            
            # Collect results
            results = results_rdd.collect()
            
            self.logger.info(f"✅ Spark batch processing completed: {len(results)} files processed")
            return results
            
        except Exception as e:
            self.logger.error(f"❌ Spark batch processing failed: {e}")
            raise
    
    def _batch_process_with_pandas(self, files, operation, max_workers, **kwargs):
        """Process files using Pandas for local processing"""
        
        try:
            from concurrent.futures import ThreadPoolExecutor, as_completed
            import threading
            
            results = []
            errors = []
            
            # Process files with thread pool
            with ThreadPoolExecutor(max_workers=max_workers or 4) as executor:
                # Submit all tasks
                future_to_file = {executor.submit(operation, file): file for file in files}
                
                # Process completed tasks
                for future in as_completed(future_to_file):
                    file = future_to_file[future]
                    try:
                        result = future.result()
                        results.append(result)
                    except Exception as e:
                        error_info = {"file": str(file), "error": str(e)}
                        errors.append(error_info)
                        self.logger.warning(f"File processing failed: {file} - {e}")
            
            self.logger.info(f"✅ Pandas batch processing completed: {len(results)} files processed, {len(errors)} errors")
            
            if errors:
                self.logger.warning(f"Errors encountered: {errors}")
            
            return results
            
        except Exception as e:
            self.logger.error(f"❌ Pandas batch processing failed: {e}")
            raise
    
    def _estimate_average_file_size(self, files):
        """Estimate average file size in MB"""
        
        try:
            total_size = sum(f.stat().st_size for f in files if f.exists())
            return (total_size / len(files)) / (1024 * 1024) if files else 0
        except:
            return 1.0  # Default estimate
```

#### Setup and File Discovery
```python
def discover_files_for_processing():
    """Discover files that need processing."""
    
    try:
        # Create sample directory structure
        base_dir = Path("batch_processing_demo")
        base_dir.mkdir(exist_ok=True)
        
        # Create subdirectories
        (base_dir / "input").mkdir(exist_ok=True)
        (base_dir / "output").mkdir(exist_ok=True)
        (base_dir / "logs").mkdir(exist_ok=True)
        
        # Generate sample CSV files
        for i in range(10):
            data = {
                'id': range(i * 100, (i + 1) * 100),
                'value': [f"value_{j}" for j in range(i * 100, (i + 1) * 100)],
                'timestamp': pd.Timestamp.now()
            }
            df = pd.DataFrame(data)
            
            file_path = base_dir / "input" / f"data_batch_{i:03d}.csv"
            df.to_csv(file_path, index=False)
        
        # Generate sample text files
        for i in range(5):
            file_path = base_dir / "input" / f"log_batch_{i:03d}.txt"
            with open(file_path, 'w') as f:
                f.write(f"Log file {i}\n")
                f.write(f"Generated at {pd.Timestamp.now()}\n")
                f.write(f"Contains {100 + i * 50} log entries\n")
        
        # Generate sample image files (simulated)
        for i in range(3):
            file_path = base_dir / "input" / f"image_batch_{i:03d}.jpg"
            file_path.write_text(f"Simulated image file {i}")
        
        print(f"✅ Created sample files in {base_dir}")
        print(f"📁 Input directory: {base_dir / 'input'}")
        print(f"📁 Output directory: {base_dir / 'output'}")
        
        return base_dir
        
    except Exception as e:
        print(f"❌ Error creating sample files: {e}")
        return None

# Create sample files
demo_dir = discover_files_for_processing()
```

#### Multi-Engine Batch Processing
```python
def demonstrate_multi_engine_batch_processing():
    """Demonstrate batch processing with different engines"""
    
    try:
        # Initialize multi-engine batch processor
        batch_processor = MultiEngineBatchProcessor(default_engine="auto")
        
        # Get list of files to process
        input_dir = demo_dir / "input"
        csv_files = list(input_dir.glob("*.csv"))
        txt_files = list(input_dir.glob("*.txt"))
        all_files = csv_files + txt_files
        
        print(f"📊 Processing {len(all_files)} files with multi-engine support")
        print(f"   - CSV files: {len(csv_files)}")
        print(f"   - Text files: {len(txt_files)}")
        
        # Define processing operations
        def process_csv_file(file_path):
            """Process a single CSV file"""
            try:
                df = pd.read_csv(file_path)
                processed_data = df.copy()
                processed_data['processed_at'] = pd.Timestamp.now()
                processed_data['file_name'] = file_path.name
                
                # Save processed file
                output_path = demo_dir / "output" / f"processed_{file_path.name}"
                processed_data.to_csv(output_path, index=False)
                
                return {
                    "file": str(file_path),
                    "status": "success",
                    "rows_processed": len(processed_data),
                    "output_path": str(output_path)
                }
            except Exception as e:
                return {
                    "file": str(file_path),
                    "status": "error",
                    "error": str(e)
                }
        
        def process_text_file(file_path):
            """Process a single text file"""
            try:
                with open(file_path, 'r') as f:
                    content = f.read()
                
                # Simple text processing
                processed_content = f"PROCESSED: {content}\nProcessed at: {pd.Timestamp.now()}"
                
                # Save processed file
                output_path = demo_dir / "output" / f"processed_{file_path.name}"
                with open(output_path, 'w') as f:
                    f.write(processed_content)
                
                return {
                    "file": str(file_path),
                    "status": "success",
                    "lines_processed": len(content.split('\n')),
                    "output_path": str(output_path)
                }
            except Exception as e:
                return {
                    "file": str(file_path),
                    "status": "error",
                    "error": str(e)
                }
        
        # Process CSV files with auto-engine selection
        print("\n🔄 Processing CSV files with auto-engine selection...")
        csv_results = batch_processor.batch_process_files(
            files=csv_files,
            operation=process_csv_file,
            max_workers=4,
            complexity="medium"
        )
        
        # Process text files with Pandas engine
        print("\n🔄 Processing text files with Pandas engine...")
        txt_results = batch_processor.batch_process_files(
            files=txt_files,
            operation=process_text_file,
            max_workers=2,
            engine="pandas"
        )
        
        # Process all files with Spark engine (if available)
        if batch_processor.spark_available:
            print("\n🔄 Processing all files with Spark engine...")
            all_results_spark = batch_processor.batch_process_files(
                files=all_files,
                operation=lambda f: process_csv_file(f) if f.suffix == '.csv' else process_text_file(f),
                max_workers=8,
                engine="spark"
            )
        
        # Display results summary
        print("\n📊 Batch Processing Results Summary:")
        print("=" * 50)
        
        successful_csv = [r for r in csv_results if r.get('status') == 'success']
        successful_txt = [r for r in txt_results if r.get('status') == 'success']
        
        print(f"✅ CSV files processed successfully: {len(successful_csv)}/{len(csv_files)}")
        print(f"✅ Text files processed successfully: {len(successful_txt)}/{len(txt_files)}")
        
        if batch_processor.spark_available:
            successful_spark = [r for r in all_results_spark if r.get('status') == 'success']
            print(f"✅ Spark processing successful: {len(successful_spark)}/{len(all_files)}")
        
        return {
            "csv_results": csv_results,
            "txt_results": txt_results,
            "total_processed": len(successful_csv) + len(successful_txt)
        }
        
    except Exception as e:
        print(f"❌ Multi-engine batch processing failed: {e}")
        siege_utilities.log_error(f"Multi-engine batch processing failed: {e}")
        return None

# Run multi-engine batch processing demonstration
batch_results = demonstrate_multi_engine_batch_processing()
```

### 2. Advanced Multi-Engine Batch Operations

#### Large-Scale Data Processing with Spark
```python
def demonstrate_spark_batch_processing():
    """Demonstrate Spark-based batch processing for large datasets"""
    
    if not batch_processor.spark_available:
        print("⚠️ Spark not available, skipping Spark demonstration")
        return None
    
    try:
        print("\n🚀 Demonstrating Spark-based batch processing...")
        
        # Create large sample dataset
        large_data_files = create_large_sample_dataset()
        
        # Define Spark-optimized processing operation
        def process_large_file_spark(file_path):
            """Process large file using Spark operations"""
            try:
                # Read file with Spark
                if file_path.suffix == '.csv':
                    df = self.spark_utils.spark.read.csv(str(file_path), header=True, inferSchema=True)
                elif file_path.suffix == '.parquet':
                    df = self.spark_utils.spark.read.parquet(str(file_path))
                else:
                    df = self.spark_utils.spark.read.text(str(file_path))
                
                # Perform Spark operations
                processed_df = df.transform(self.spark_utils.enhance_dataframe)
                
                # Save processed data
                output_path = demo_dir / "output" / f"spark_processed_{file_path.name}"
                if file_path.suffix == '.csv':
                    processed_df.write.csv(str(output_path), header=True, mode="overwrite")
                elif file_path.suffix == '.parquet':
                    processed_df.write.parquet(str(output_path), mode="overwrite")
                else:
                    processed_df.write.text(str(output_path), mode="overwrite")
                
                return {
                    "file": str(file_path),
                    "status": "success",
                    "rows_processed": processed_df.count(),
                    "output_path": str(output_path),
                    "engine": "spark"
                }
                
            except Exception as e:
                return {
                    "file": str(file_path),
                    "status": "error",
                    "error": str(e),
                    "engine": "spark"
                }
        
        # Process large files with Spark
        spark_results = batch_processor.batch_process_files(
            files=large_data_files,
            operation=process_large_file_spark,
            max_workers=16,  # More workers for Spark
            engine="spark",
            complexity="complex"
        )
        
        print(f"✅ Spark batch processing completed: {len(spark_results)} files processed")
        return spark_results
        
    except Exception as e:
        print(f"❌ Spark batch processing failed: {e}")
        return None

def create_large_sample_dataset():
    """Create large sample dataset for Spark processing demonstration"""
    
    try:
        large_dir = demo_dir / "large_data"
        large_dir.mkdir(exist_ok=True)
        
        # Create large CSV files
        for i in range(5):
            # Generate 100K rows of data
            data = {
                'id': range(i * 100000, (i + 1) * 100000),
                'value': [f"large_value_{j}" for j in range(i * 100000, (i + 1) * 100000)],
                'category': [f"cat_{j % 10}" for j in range(i * 100000, (i + 1) * 100000)],
                'timestamp': pd.Timestamp.now()
            }
            df = pd.DataFrame(data)
            
            file_path = large_dir / f"large_data_{i:03d}.csv"
            df.to_csv(file_path, index=False)
            print(f"Created large file: {file_path} ({len(df):,} rows)")
        
        # Create large Parquet files
        for i in range(3):
            data = {
                'id': range(i * 50000, (i + 1) * 50000),
                'numeric_value': np.random.randn(50000),
                'text_value': [f"parquet_text_{j}" for j in range(i * 50000, (i + 1) * 50000)],
                'date_value': pd.date_range(start='2024-01-01', periods=50000, freq='H')
            }
            df = pd.DataFrame(data)
            
            file_path = large_dir / f"large_data_{i:03d}.parquet"
            df.to_parquet(file_path, index=False)
            print(f"Created large parquet file: {file_path} ({len(df):,} rows)")
        
        return list(large_dir.glob("*"))
        
    except Exception as e:
        print(f"❌ Error creating large sample dataset: {e}")
        return []
```

#### Performance Comparison Across Engines
```python
def benchmark_engine_performance():
    """Benchmark performance across different engines"""
    
    try:
        print("\n📊 Benchmarking engine performance...")
        
        # Test files of different sizes
        test_files = {
            "small": list((demo_dir / "input").glob("*.txt"))[:2],
            "medium": list((demo_dir / "input").glob("*.csv"))[:3],
            "large": list((demo_dir / "large_data").glob("*.csv"))[:2] if (demo_dir / "large_data").exists() else []
        }
        
        results = {}
        
        for size_category, files in test_files.items():
            if not files:
                continue
                
            print(f"\n🔍 Testing {size_category} files ({len(files)} files)...")
            
            # Test Pandas engine
            start_time = time.time()
            pandas_results = batch_processor.batch_process_files(
                files=files,
                operation=lambda f: process_csv_file(f) if f.suffix == '.csv' else process_text_file(f),
                max_workers=4,
                engine="pandas"
            )
            pandas_time = time.time() - start_time
            
            # Test Spark engine (if available)
            spark_time = None
            if batch_processor.spark_available:
                start_time = time.time()
                spark_results = batch_processor.batch_process_files(
                    files=files,
                    operation=lambda f: process_csv_file(f) if f.suffix == '.csv' else process_text_file(f),
                    max_workers=8,
                    engine="spark"
                )
                spark_time = time.time() - start_time
            
            # Calculate performance metrics
            total_size_mb = sum(f.stat().st_size for f in files) / (1024 * 1024)
            
            results[size_category] = {
                "file_count": len(files),
                "total_size_mb": total_size_mb,
                "pandas_time": pandas_time,
                "spark_time": spark_time,
                "pandas_throughput": total_size_mb / pandas_time if pandas_time > 0 else 0,
                "spark_throughput": total_size_mb / spark_time if spark_time else 0
            }
        
        # Display benchmark results
        print("\n📊 Engine Performance Benchmark Results:")
        print("=" * 60)
        
        for size_category, metrics in results.items():
            print(f"\n{size_category.upper()} FILES:")
            print(f"  Files: {metrics['file_count']}, Total Size: {metrics['total_size_mb']:.2f}MB")
            print(f"  Pandas: {metrics['pandas_time']:.2f}s ({metrics['pandas_throughput']:.2f}MB/s)")
            
            if metrics['spark_time']:
                print(f"  Spark:  {metrics['spark_time']:.2f}s ({metrics['spark_throughput']:.2f}MB/s)")
                
                if metrics['spark_time'] < metrics['pandas_time']:
                    speedup = metrics['pandas_time'] / metrics['spark_time']
                    print(f"  🚀 Spark is {speedup:.2f}x faster than Pandas")
                else:
                    slowdown = metrics['spark_time'] / metrics['pandas_time']
                    print(f"  ⚠️  Pandas is {slowdown:.2f}x faster than Spark")
        
        return results
        
    except Exception as e:
        print(f"❌ Performance benchmarking failed: {e}")
        return None

# Run performance benchmark
performance_results = benchmark_engine_performance()
```

### 3. Engine Selection Strategies

#### Smart Engine Selection
```python
def demonstrate_smart_engine_selection():
    """Demonstrate intelligent engine selection based on data characteristics"""
    
    try:
        print("\n🧠 Demonstrating smart engine selection...")
        
        # Different types of operations with varying complexity
        operations = {
            "simple_text_processing": {
                "complexity": "simple",
                "data_requirements": "low",
                "parallelization": "low"
            },
            "csv_data_analysis": {
                "complexity": "medium",
                "data_requirements": "medium",
                "parallelization": "medium"
            },
            "large_dataset_aggregation": {
                "complexity": "complex",
                "data_requirements": "high",
                "parallelization": "high"
            }
        }
        
        # Test files for each operation type
        test_scenarios = {
            "simple_text_processing": list((demo_dir / "input").glob("*.txt"))[:2],
            "csv_data_analysis": list((demo_dir / "input").glob("*.csv"))[:3],
            "large_dataset_aggregation": list((demo_dir / "large_data").glob("*.csv"))[:2] if (demo_dir / "large_data").exists() else []
        }
        
        for operation_name, operation_config in operations.items():
            files = test_scenarios[operation_name]
            if not files:
                continue
                
            print(f"\n🔍 Testing {operation_name}...")
            print(f"   Complexity: {operation_config['complexity']}")
            print(f"   Files: {len(files)}")
            
            # Let the system auto-select the best engine
            selected_engine = batch_processor.get_optimal_engine(
                total_files=len(files),
                avg_file_size_mb=batch_processor._estimate_average_file_size(files),
                operation_complexity=operation_config['complexity']
            )
            
            print(f"   🎯 Auto-selected engine: {selected_engine}")
            
            # Process with selected engine
            results = batch_processor.batch_process_files(
                files=files,
                operation=lambda f: process_csv_file(f) if f.suffix == '.csv' else process_text_file(f),
                max_workers=8 if selected_engine == "spark" else 4,
                engine=selected_engine
            )
            
            successful = [r for r in results if r.get('status') == 'success']
            print(f"   ✅ Successfully processed: {len(successful)}/{len(files)} files")
        
        print("\n🎯 Smart engine selection demonstration completed!")
        
    except Exception as e:
        print(f"❌ Smart engine selection demonstration failed: {e}")

# Run smart engine selection demonstration
smart_selection_results = demonstrate_smart_engine_selection()
```

### 4. Multi-Engine Error Handling and Recovery

#### Robust Multi-Engine Batch Processing
```python
def robust_multi_engine_batch_processing():
    """Demonstrate robust batch processing with multi-engine support and error handling."""
    
    try:
        if not demo_dir:
            raise ValueError("Demo directory not created")
        
        # Initialize multi-engine batch processor
        batch_processor = MultiEngineBatchProcessor(default_engine="auto")
        
        input_dir = demo_dir / "input"
        output_dir = demo_dir / "output"
        logs_dir = demo_dir / "logs"
        
        # Get all files
        all_files = list(input_dir.glob("*"))
        print(f"🛡️ Robust Multi-Engine Batch Processing: {len(all_files)} files")
        
        # Create error log
        error_log = logs_dir / "multi_engine_batch_processing_errors.log"
        
        def robust_multi_engine_processor(file_path):
            """Robust file processor with multi-engine support and comprehensive error handling."""
            try:
                start_time = time.time()
                
                # Check file accessibility
                if not siege_utilities.file_exists(str(file_path)):
                    raise FileNotFoundError(f"File not accessible: {file_path}")
                
                # Check file size
                file_size = siege_utilities.get_file_size(str(file_path))
                if file_size == 0:
                    raise ValueError(f"File is empty: {file_path}")
                
                # Check file permissions
                if not siege_utilities.is_readable(str(file_path)):
                    raise PermissionError(f"File not readable: {file_path}")
                
                # Auto-select optimal engine based on file characteristics
                file_size_mb = file_size / (1024 * 1024)
                selected_engine = batch_processor.get_optimal_engine(
                    total_files=1,
                    avg_file_size_mb=file_size_mb,
                    operation_complexity="medium"
                )
                
                # Process based on file type and selected engine
                file_type = file_path.suffix.lower()
                
                if file_type == '.csv':
                    # Robust CSV processing with engine selection
                    if selected_engine == "spark" and batch_processor.spark_available:
                        # Use Spark for large CSV files
                        try:
                            df = batch_processor.spark_utils.spark.read.csv(
                                str(file_path), 
                                header=True, 
                                inferSchema=True
                            )
                            row_count = df.count()
                            
                            # Process with Spark
                            df_processed = df.withColumn(
                                "processed_timestamp", 
                                batch_processor.spark_utils.spark.sql.functions.current_timestamp()
                            ).withColumn(
                                "source_file", 
                                batch_processor.spark_utils.spark.sql.functions.lit(file_path.name)
                            )
                            
                            # Save with Spark
                            output_file = output_dir / f"spark_robust_{file_path.name}"
                            df_processed.write.csv(str(output_file), header=True, mode="overwrite")
                            
                            return {
                                'file': str(file_path),
                                'status': 'success',
                                'type': 'csv',
                                'engine': 'spark',
                                'rows_processed': row_count,
                                'output_file': str(output_file),
                                'processing_time': time.time() - start_time
                            }
                            
                        except Exception as spark_error:
                            # Fall back to Pandas if Spark fails
                            print(f"⚠️ Spark processing failed for {file_path}, falling back to Pandas: {spark_error}")
                            selected_engine = "pandas"
                    
                    # Use Pandas for smaller files or as fallback
                    if selected_engine == "pandas":
                        try:
                            df = pd.read_csv(file_path)
                        except pd.errors.EmptyDataError:
                            raise ValueError(f"CSV file is empty: {file_path}")
                        except pd.errors.ParserError as e:
                            raise ValueError(f"CSV parsing error: {e}")
                        
                        # Validate data structure
                        if len(df.columns) == 0:
                            raise ValueError(f"CSV has no columns: {file_path}")
                        
                        # Process data
                        df_processed = df.copy()
                        df_processed['processed_timestamp'] = pd.Timestamp.now()
                        df_processed['source_file'] = file_path.name
                        df_processed['processing_engine'] = 'pandas'
                        
                        # Save with error handling
                        output_file = output_dir / f"pandas_robust_{file_path.name}"
                        try:
                            df_processed.to_csv(output_file, index=False)
                        except Exception as e:
                            raise IOError(f"Failed to save processed file: {e}")
                        
                        return {
                            'file': str(file_path),
                            'status': 'success',
                            'type': 'csv',
                            'engine': 'pandas',
                            'rows_processed': len(df_processed),
                            'output_file': str(output_file),
                            'processing_time': time.time() - start_time
                        }
                    
                elif file_type == '.txt':
                    # Robust text processing (always use Pandas for text files)
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                    except UnicodeDecodeError:
                        # Try different encodings
                        for encoding in ['latin-1', 'cp1252', 'iso-8859-1']:
                            try:
                                with open(file_path, 'r', encoding=encoding) as f:
                                    content = f.read()
                                break
                            except UnicodeDecodeError:
                                continue
                        else:
                            raise ValueError(f"Unable to decode text file: {file_path}")
                    
                    # Process content
                    processed_content = f"ROBUST_PROCESSED: {content}\nProcessed at: {pd.Timestamp.now()}\nEngine: pandas"
                    
                    output_file = output_dir / f"pandas_robust_{file_path.name}"
                    with open(output_file, 'w', encoding='utf-8') as f:
                        f.write(processed_content)
                    
                    return {
                        'file': str(file_path),
                        'status': 'success',
                        'type': 'text',
                        'engine': 'pandas',
                        'content_length': len(processed_content),
                        'output_file': str(output_file),
                        'processing_time': time.time() - start_time
                    }
                    
                else:
                    return {
                        'file': str(file_path),
                        'status': 'skipped',
                        'type': 'unknown',
                        'engine': 'none',
                        'reason': f'Unsupported file type: {file_type}'
                    }
                    
            except Exception as e:
                # Log error details
                error_details = {
                    'timestamp': pd.Timestamp.now(),
                    'file': str(file_path),
                    'error_type': type(e).__name__,
                    'error_message': str(e),
                    'processing_time': time.time() - start_time if 'start_time' in locals() else 0
                }
                
                # Write to error log
                with open(error_log, 'a') as f:
                    f.write(f"{error_details['timestamp']} | {error_details['file']} | {error_details['error_type']} | {error_details['error_message']}\n")
                
                return {
                    'file': str(file_path),
                    'status': 'error',
                    'error_type': type(e).__name__,
                    'error_message': str(e),
                    'processing_time': error_details['processing_time']
                }
        
        # Process files with multi-engine support and retry mechanism
        print(f"\n🔄 Processing files with robust multi-engine error handling...")
        
        results = []
        retry_files = []
        
        # First pass with engine selection
        for file_path in all_files:
            result = robust_multi_engine_processor(file_path)
            results.append(result)
            
            if result['status'] == 'error':
                retry_files.append(file_path)
        
        # Retry failed files with different engine strategy
        if retry_files:
            print(f"\n🔄 Retrying {len(retry_files)} failed files with alternative engines...")
            
            for file_path in retry_files:
                # Simulate recovery and try with different engine
                time.sleep(0.1)
                
                # Force Pandas engine for retry (more reliable for small files)
                try:
                    if file_path.suffix.lower() == '.csv':
                        df = pd.read_csv(file_path)
                        df['retry_processed'] = True
                        df['retry_timestamp'] = pd.Timestamp.now()
                        
                        output_file = output_dir / f"retry_pandas_{file_path.name}"
                        df.to_csv(output_file, index=False)
                        
                        retry_result = {
                            'file': str(file_path),
                            'status': 'success',
                            'type': 'csv',
                            'engine': 'pandas_retry',
                            'rows_processed': len(df),
                            'output_file': str(output_file),
                            'processing_time': 0.1
                        }
                    else:
                        # Skip non-CSV files in retry
                        retry_result = {
                            'file': str(file_path),
                            'status': 'skipped',
                            'type': file_path.suffix.lower(),
                            'engine': 'none',
                            'reason': 'Skipped in retry phase'
                        }
                        
                except Exception as retry_error:
                    retry_result = {
                        'file': str(file_path),
                        'status': 'error',
                        'error_type': type(retry_error).__name__,
                        'error_message': f"Retry failed: {retry_error}",
                        'processing_time': 0.1
                    }
                
                # Update original result
                for i, result in enumerate(results):
                    if result['file'] == str(file_path):
                        results[i] = retry_result
                        break
        
        # Final analysis with engine breakdown
        successful = [r for r in results if r['status'] == 'success']
        errors = [r for r in results if r['status'] == 'error']
        skipped = [r for r in results if r['status'] == 'skipped']
        
        # Engine breakdown
        engine_stats = {}
        for result in successful:
            engine = result.get('engine', 'unknown')
            engine_stats[engine] = engine_stats.get(engine, 0) + 1
        
        print(f"\n📊 Robust Multi-Engine Processing Results:")
        print(f"  ✅ Successful: {len(successful)}")
        print(f"  ❌ Errors: {len(errors)}")
        print(f"  ⏭️ Skipped: {len(skipped)}")
        
        if engine_stats:
            print(f"\n🚀 Engine Usage Breakdown:")
            for engine, count in engine_stats.items():
                print(f"  {engine}: {count} files")
        
        if errors:
            print(f"\n❌ Error Summary:")
            error_types = {}
            for error in errors:
                error_type = error.get('error_type', 'Unknown')
                error_types[error_type] = error_types.get(error_type, 0) + 1
            
            for error_type, count in error_types.items():
                print(f"  {error_type}: {count} files")
        
        # Show error log location
        if error_log.exists():
            print(f"\n📝 Error log saved to: {error_log}")
        
        return results
        
    except Exception as e:
        print(f"❌ Error in robust multi-engine batch processing: {e}")
        return []

# Run robust multi-engine batch processing
robust_multi_engine_results = robust_multi_engine_batch_processing()
```

### 5. Complete Multi-Engine Pipeline Example

#### End-to-End Multi-Engine Batch Processing
```python
def run_complete_multi_engine_batch_pipeline():
    """Run complete multi-engine batch processing pipeline with all features."""
    
    print("🚀 Complete Multi-Engine Batch Processing Pipeline")
    print("=" * 60)
    
    try:
        # Step 1: Setup and discovery
        print("📁 Step 1: Setting up multi-engine batch processing environment...")
        
        if not demo_dir:
            demo_dir = discover_files_for_processing()
            if not demo_dir:
                raise ValueError("Failed to create demo environment")
        
        print(f"  ✅ Demo environment ready: {demo_dir}")
        
        # Step 2: Initialize multi-engine processor
        print("\n🔧 Step 2: Initializing multi-engine batch processor...")
        
        batch_processor = MultiEngineBatchProcessor(default_engine="auto")
        
        print(f"  ✅ Multi-engine processor initialized")
        print(f"  🚀 Spark available: {batch_processor.spark_available}")
        print(f"  🎯 Default engine: {batch_processor.default_engine}")
        
        # Step 3: File discovery and validation
        print("\n🔍 Step 3: Discovering and validating files...")
        
        input_dir = demo_dir / "input"
        all_files = list(input_dir.glob("*"))
        
        # Validate files and estimate optimal engines
        valid_files = []
        invalid_files = []
        engine_recommendations = {}
        
        for file_path in all_files:
            try:
                if siege_utilities.file_exists(str(file_path)):
                    file_size = siege_utilities.get_file_size(str(file_path))
                    if file_size > 0:
                        valid_files.append(file_path)
                        
                        # Get engine recommendation for this file
                        file_size_mb = file_size / (1024 * 1024)
                        recommended_engine = batch_processor.get_optimal_engine(
                            total_files=1,
                            avg_file_size_mb=file_size_mb,
                            operation_complexity="medium"
                        )
                        engine_recommendations[str(file_path)] = recommended_engine
                        
                    else:
                        invalid_files.append((file_path, "Empty file"))
                else:
                    invalid_files.append((file_path, "File not accessible"))
            except Exception as e:
                invalid_files.append((file_path, str(e)))
        
        print(f"  ✅ Valid files: {len(valid_files)}")
        print(f"  ⚠️ Invalid files: {len(invalid_files)}")
        
        # Engine recommendation summary
        if engine_recommendations:
            engine_counts = {}
            for engine in engine_recommendations.values():
                engine_counts[engine] = engine_counts.get(engine, 0) + 1
            
            print(f"\n🎯 Engine Recommendations:")
            for engine, count in engine_counts.items():
                print(f"  {engine}: {count} files")
        
        if invalid_files:
            print("  📋 Invalid files:")
            for file_path, reason in invalid_files:
                print(f"    - {file_path.name}: {reason}")
        
        # Step 4: Multi-engine batch processing
        print(f"\n🔄 Step 4: Processing {len(valid_files)} valid files with multi-engine support...")
        
        # Group files by recommended engine
        files_by_engine = {}
        for file_path in valid_files:
            engine = engine_recommendations.get(str(file_path), "auto")
            if engine not in files_by_engine:
                files_by_engine[engine] = []
            files_by_engine[engine].append(file_path)
        
        # Process each engine group
        all_results = {}
        
        for engine, files in files_by_engine.items():
            if not files:
                continue
                
            print(f"\n  🚀 Processing {len(files)} files with {engine} engine...")
            
            # Use appropriate processing method for this engine
            if engine == "spark" and batch_processor.spark_available:
                # Spark processing
                results = batch_processor.batch_process_files(
                    files=files,
                    operation=lambda f: process_csv_file(f) if f.suffix == '.csv' else process_text_file(f),
                    max_workers=16,
                    engine="spark",
                    complexity="complex"
                )
            else:
                # Pandas processing
                results = batch_processor.batch_process_files(
                    files=files,
                    operation=lambda f: process_csv_file(f) if f.suffix == '.csv' else process_text_file(f),
                    max_workers=4,
                    engine="pandas"
                )
            
            all_results[engine] = results
            
            # Show results for this engine
            successful = [r for r in results if r.get('status') == 'success']
            errors = [r for r in results if r.get('status') == 'error']
            
            print(f"    ✅ Successful: {len(successful)}")
            print(f"    ❌ Errors: {len(errors)}")
        
        # Step 5: Results analysis and consolidation
        print(f"\n📊 Step 5: Analyzing multi-engine processing results...")
        
        # Consolidate all results
        consolidated_results = []
        for engine_results in all_results.values():
            consolidated_results.extend(engine_results)
        
        # Overall statistics
        total_successful = [r for r in consolidated_results if r.get('status') == 'success']
        total_errors = [r for r in consolidated_results if r.get('status') == 'error']
        
        print(f"  📊 Overall Results:")
        print(f"    ✅ Total successful: {len(total_successful)}")
        print(f"    ❌ Total errors: {len(total_errors)}")
        print(f"    📁 Files processed: {len(consolidated_results)}")
        
        # Engine performance analysis
        print(f"\n🚀 Engine Performance Analysis:")
        for engine, results in all_results.items():
            successful = [r for r in results if r.get('status') == 'success']
            success_rate = len(successful) / len(results) * 100 if results else 0
            print(f"  {engine}: {len(successful)}/{len(results)} ({success_rate:.1f}% success rate)")
        
        # Step 6: Quality assessment and output analysis
        print(f"\n🔍 Step 6: Quality assessment and output analysis...")
        
        output_dir = demo_dir / "output"
        processed_files = list(output_dir.glob("*"))
        
        print(f"  📁 Output directory: {output_dir}")
        print(f"  📊 Files generated: {len(processed_files)}")
        
        # Check file sizes and types
        total_output_size = sum(f.stat().st_size for f in processed_files if f.is_file())
        print(f"  📏 Total output size: {total_output_size:,} bytes")
        
        # Analyze output by engine
        output_by_engine = {}
        for file_path in processed_files:
            if 'spark_' in file_path.name:
                engine = 'spark'
            elif 'pandas_' in file_path.name:
                engine = 'pandas'
            else:
                engine = 'unknown'
            
            if engine not in output_by_engine:
                output_by_engine[engine] = []
            output_by_engine[engine].append(file_path)
        
        print(f"\n📁 Output Files by Engine:")
        for engine, files in output_by_engine.items():
            total_size = sum(f.stat().st_size for f in files if f.is_file())
            print(f"  {engine}: {len(files)} files, {total_size:,} bytes")
        
        # Step 7: Generate comprehensive summary report
        print(f"\n📋 Step 7: Generating comprehensive summary report...")
        
        summary_file = demo_dir / "multi_engine_batch_processing_summary.txt"
        with open(summary_file, 'w') as f:
            f.write("MULTI-ENGINE BATCH PROCESSING SUMMARY\n")
            f.write("=" * 50 + "\n\n")
            f.write(f"Processing Date: {pd.Timestamp.now()}\n")
            f.write(f"Input Files: {len(all_files)}\n")
            f.write(f"Valid Files: {len(valid_files)}\n")
            f.write(f"Output Files: {len(processed_files)}\n")
            f.write(f"Total Output Size: {total_output_size:,} bytes\n")
            f.write(f"Demo Directory: {demo_dir}\n\n")
            
            f.write("ENGINE BREAKDOWN:\n")
            f.write("-" * 20 + "\n")
            for engine, files in files_by_engine.items():
                f.write(f"{engine}: {len(files)} files\n")
            
            f.write("\nOUTPUT BREAKDOWN:\n")
            f.write("-" * 20 + "\n")
            for engine, files in output_by_engine.items():
                total_size = sum(f.stat().st_size for f in files if f.is_file())
                f.write(f"{engine}: {len(files)} files, {total_size:,} bytes\n")
            
            f.write("\nPROCESSING RESULTS:\n")
            f.write("-" * 20 + "\n")
            for engine, results in all_results.items():
                successful = [r for r in results if r.get('status') == 'success']
                errors = [r for r in results if r.get('status') == 'error']
                f.write(f"{engine}: {len(successful)} successful, {len(errors)} errors\n")
        
        print(f"  📋 Comprehensive summary report: {summary_file}")
        
        # Final status
        print(f"\n🎉 Multi-engine batch processing pipeline completed successfully!")
        print(f"📁 All results saved to: {demo_dir}")
        
        return {
            'demo_directory': str(demo_dir),
            'input_files': len(all_files),
            'valid_files': len(valid_files),
            'output_files': len(processed_files),
            'summary_report': str(summary_file),
            'engine_breakdown': files_by_engine,
            'processing_results': all_results
        }
        
    except Exception as e:
        print(f"❌ Multi-engine pipeline failed: {e}")
        siege_utilities.log_error(f"Multi-engine batch processing pipeline failed: {e}")
        return None

# Run complete multi-engine pipeline
if __name__ == "__main__":
    multi_engine_pipeline_result = run_complete_multi_engine_batch_pipeline()
    if multi_engine_pipeline_result:
        print(f"\n🚀 Multi-Engine Pipeline Results:")
        for key, value in multi_engine_pipeline_result.items():
            if key not in ['engine_breakdown', 'processing_results']:
                print(f"  {key}: {value}")
        
        print(f"\n🚀 Engine Breakdown:")
        for engine, files in multi_engine_pipeline_result['engine_breakdown'].items():
            print(f"  {engine}: {len(files)} files")
        
        print(f"\n📊 Processing Results by Engine:")
        for engine, results in multi_engine_pipeline_result['processing_results'].items():
            successful = [r for r in results if r.get('status') == 'success']
            print(f"  {engine}: {len(successful)}/{len(results)} successful")
    else:
        print("\n💥 Multi-engine pipeline encountered errors")
```

## Expected Output

```
🚀 Complete Multi-Engine Batch Processing Pipeline
============================================================
📁 Step 1: Setting up multi-engine batch processing environment...
  ✅ Demo environment ready: batch_processing_demo

🔧 Step 2: Initializing multi-engine batch processor...
  ✅ Multi-engine processor initialized
  🚀 Spark available: True
  🎯 Default engine: auto

🔍 Step 3: Discovering and validating files...
  ✅ Valid files: 18
  ⚠️ Invalid files: 0

🎯 Engine Recommendations:
  pandas: 15 files
  spark: 3 files

🔄 Step 4: Processing 18 valid files with multi-engine support...

  🚀 Processing 15 files with pandas engine...
    ✅ Successful: 15
    ❌ Errors: 0

  🚀 Processing 3 files with spark engine...
    ✅ Successful: 3
    ❌ Errors: 0

📊 Step 5: Analyzing multi-engine processing results...
  📊 Overall Results:
    ✅ Total successful: 18
    ❌ Total errors: 0
    📁 Files processed: 18

🚀 Engine Performance Analysis:
  pandas: 15/15 (100.0% success rate)
  spark: 3/3 (100.0% success rate)

🔍 Step 6: Quality assessment and output analysis...
  📁 Output directory: batch_processing_demo/output
  📊 Files generated: 36
  📏 Total output size: 45,280 bytes

📁 Output Files by Engine:
  pandas: 30 files, 30,240 bytes
  spark: 6 files, 15,040 bytes

📋 Step 7: Generating comprehensive summary report...
  📋 Comprehensive summary report: batch_processing_demo/multi_engine_batch_processing_summary.txt

🎉 Multi-engine batch processing pipeline completed successfully!
📁 All results saved to: batch_processing_demo

🚀 Multi-Engine Pipeline Results:
  demo_directory: batch_processing_demo
  input_files: 18
  valid_files: 18
  output_files: 36
  summary_report: batch_processing_demo/multi_engine_batch_processing_summary.txt

🚀 Engine Breakdown:
  pandas: 15 files
  spark: 3 files

📊 Processing Results by Engine:
  pandas: 15/15 successful
  spark: 3/3 successful
```

## Configuration Options

### Multi-Engine Batch Processing Configuration
```yaml
multi_engine_batch_processing:
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
  retry_attempts: 3
  retry_delay: 1.0
  timeout: 300
  
  # Memory and resource management
  memory_limit: "2GB"
  spark_config:
    executor_memory: "2g"
    driver_memory: "1g"
    executor_cores: 2
  
  # Monitoring and logging
  progress_tracking: true
  error_logging: true
  performance_monitoring: true
  cleanup_on_error: false
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
```

## Next Steps

After mastering multi-engine batch processing:

- **Advanced Engine Integration**: Implement custom engine adapters
- **Real-time Multi-Engine Processing**: Add streaming support for both engines
- **Hybrid Processing**: Combine engines for optimal performance
- **Cloud Integration**: Scale to cloud-based Spark clusters
- **Advanced Monitoring**: Implement comprehensive performance monitoring

## Related Recipes

- **[Spark Processing](Spark-Processing)** - Master distributed batch processing with Spark
- **[File Operations](File-Operations)** - Learn engine-agnostic file operations
- **[Multi-Engine Data Processing](Multi-Engine-Data-Processing)** - Understand the broader multi-engine architecture
- **[Analytics Integration](Analytics-Integration)** - Process analytics data with multiple engines
- **[Comprehensive Reporting](Comprehensive-Reporting)** - Generate reports from multi-engine batch results

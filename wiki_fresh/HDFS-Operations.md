# HDFS Operations Recipe

## Overview
This recipe demonstrates how to use the HDFS (Hadoop Distributed File System) utilities in `siege_utilities` for efficient distributed file operations, data management, and cluster coordination.

## Prerequisites
- Python 3.7+
- `siege_utilities` library installed
- Access to Hadoop cluster or HDFS environment
- Basic understanding of distributed systems
- Hadoop client libraries (if using local HDFS)

## Installation
```bash
pip install siege_utilities
pip install hdfs3  # For HDFS client operations
```

## HDFS Configuration

### 1. Basic Configuration

```python
from siege_utilities.distributed.hdfs_config import HDFSConfig
from siege_utilities.distributed.hdfs_operations import HDFSOperations

# Initialize HDFS configuration
hdfs_config = HDFSConfig()

# Set basic configuration
hdfs_config.set_namenode("hdfs://namenode:9000")
hdfs_config.set_user("hdfs_user")
hdfs_config.set_replication_factor(3)

# Load configuration from file
hdfs_config.load_from_file("config/hdfs_config.yaml")

# Initialize HDFS operations
hdfs_ops = HDFSOperations(hdfs_config)
```

### 2. Advanced Configuration

```python
# Set security configuration
hdfs_config.set_security_enabled(True)
hdfs_config.set_kerberos_principal("user@REALM")
hdfs_config.set_keytab_path("/path/to/keytab")

# Set performance tuning
hdfs_config.set_buffer_size(8192)
hdfs_config.set_block_size(134217728)  # 128MB
hdfs_config.set_io_buffer_size(4096)

# Set connection timeouts
hdfs_config.set_connection_timeout(30000)
hdfs_config.set_read_timeout(60000)
```

## Basic HDFS Operations

### 1. File and Directory Operations

```python
# List directory contents
files = hdfs_ops.list_directory("/user/data/input")
print(f"Files in directory: {files}")

# Check if path exists
exists = hdfs_ops.path_exists("/user/data/input/sample.csv")
print(f"Path exists: {exists}")

# Get file status
status = hdfs_ops.get_file_status("/user/data/input/sample.csv")
print(f"File size: {status['size']} bytes")
print(f"Owner: {status['owner']}")
print(f"Permissions: {status['permissions']}")
```

### 2. File Upload and Download

```python
# Upload local file to HDFS
success = hdfs_ops.upload_file(
    local_path="data/local/sample.csv",
    hdfs_path="/user/data/input/sample.csv",
    overwrite=True
)

# Download HDFS file to local
success = hdfs_ops.download_file(
    hdfs_path="/user/data/output/result.csv",
    local_path="data/local/result.csv"
)

# Upload directory recursively
success = hdfs_ops.upload_directory(
    local_dir="data/local/input/",
    hdfs_dir="/user/data/input/"
)
```

### 3. File Reading and Writing

```python
# Read HDFS file content
content = hdfs_ops.read_file("/user/data/input/config.json")
print(f"File content: {content[:100]}...")

# Write content to HDFS file
data = {"setting": "value", "enabled": True}
success = hdfs_ops.write_file(
    "/user/data/config/settings.json",
    data,
    format="json"
)

# Append to HDFS file
hdfs_ops.append_to_file(
    "/user/data/logs/app.log",
    "New log entry\n"
)
```

## Advanced HDFS Operations

### 1. Batch Operations

```python
# Batch upload multiple files
file_list = [
    ("local/file1.csv", "/user/data/input/file1.csv"),
    ("local/file2.csv", "/user/data/input/file2.csv"),
    ("local/file3.csv", "/user/data/input/file3.csv")
]

for local_path, hdfs_path in file_list:
    success = hdfs_ops.upload_file(local_path, hdfs_path)
    print(f"Uploaded {local_path}: {success}")

# Batch download with filtering
hdfs_files = hdfs_ops.list_directory("/user/data/output/")
csv_files = [f for f in hdfs_files if f.endswith('.csv')]

for hdfs_file in csv_files:
    local_path = f"data/downloaded/{hdfs_file.split('/')[-1]}"
    hdfs_ops.download_file(hdfs_file, local_path)
```

### 2. Data Processing with HDFS

```python
# Process large HDFS files in chunks
for chunk in hdfs_ops.read_file_chunks(
    "/user/data/large_dataset.csv",
    chunk_size=8192
):
    # Process each chunk
    processed_chunk = process_data(chunk)
    
    # Write processed chunk
    hdfs_ops.append_to_file(
        "/user/data/processed/result.csv",
        processed_chunk
    )
```

### 3. HDFS Monitoring and Management

```python
# Get HDFS cluster information
cluster_info = hdfs_ops.get_cluster_info()
print(f"Cluster name: {cluster_info['name']}")
print(f"Total capacity: {cluster_info['capacity']}")
print(f"Used space: {cluster_info['used']}")
print(f"Available space: {cluster_info['available']}")

# Get directory usage
usage = hdfs_ops.get_directory_usage("/user/data/")
print(f"Directory size: {usage['size']}")
print(f"File count: {usage['file_count']}")
print(f"Directory count: {usage['directory_count']}")
```

## HDFS Security and Permissions

### 1. Permission Management

```python
# Set file permissions
hdfs_ops.set_permissions(
    "/user/data/input/sample.csv",
    "644"
)

# Set directory permissions recursively
hdfs_ops.set_permissions_recursive(
    "/user/data/input/",
    "755"
)

# Change file ownership
hdfs_ops.set_owner(
    "/user/data/input/sample.csv",
    owner="newuser",
    group="newgroup"
)
```

### 2. Access Control

```python
# Check access permissions
can_read = hdfs_ops.check_access("/user/data/input/", "READ")
can_write = hdfs_ops.check_access("/user/data/output/", "WRITE")
can_execute = hdfs_ops.check_access("/user/data/scripts/", "EXECUTE")

# Set ACL (Access Control Lists)
acl_entries = [
    "user:john:rw-",
    "group:analysts:r--",
    "other::---"
]
hdfs_ops.set_acl("/user/data/input/", acl_entries)
```

## Performance Optimization

### 1. Parallel Operations

```python
from concurrent.futures import ThreadPoolExecutor
import threading

# Parallel file upload
def upload_file(args):
    local_path, hdfs_path = args
    return hdfs_ops.upload_file(local_path, hdfs_path)

with ThreadPoolExecutor(max_workers=4) as executor:
    results = list(executor.map(upload_file, file_list))
```

### 2. Compression and Optimization

```python
# Upload with compression
success = hdfs_ops.upload_file(
    local_path="data/local/large_file.txt",
    hdfs_path="/user/data/input/large_file.txt.gz",
    compress=True,
    compression_type="gzip"
)

# Set optimal block size for large files
hdfs_ops.set_block_size(
    "/user/data/input/large_file.txt",
    block_size=268435456  # 256MB
)
```

## Error Handling and Recovery

### 1. Connection Management

```python
try:
    # Attempt HDFS operation
    files = hdfs_ops.list_directory("/user/data/")
except ConnectionError:
    print("HDFS connection failed, retrying...")
    hdfs_ops.reconnect()
    files = hdfs_ops.list_directory("/user/data/")
except Exception as e:
    print(f"HDFS operation failed: {e}")
    # Implement fallback logic
```

### 2. Retry Logic

```python
from siege_utilities.core.logging import Logger

logger = Logger("hdfs_operations")

def hdfs_operation_with_retry(operation, max_retries=3):
    for attempt in range(max_retries):
        try:
            return operation()
        except Exception as e:
            logger.warning(f"Attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)  # Exponential backoff
            else:
                raise e

# Use retry logic
files = hdfs_operation_with_retry(
    lambda: hdfs_ops.list_directory("/user/data/")
)
```

## Integration Examples

### 1. With Spark Processing

```python
from siege_utilities.distributed.spark_utils import SparkUtils
from siege_utilities.distributed.hdfs_operations import HDFSOperations

spark_utils = SparkUtils()
hdfs_ops = HDFSOperations()

# Read data from HDFS into Spark
df = spark_utils.read_hdfs_file(
    "/user/data/input/sales.csv",
    format="csv"
)

# Process data
result_df = df.groupBy("category").sum("amount")

# Write result back to HDFS
spark_utils.write_hdfs_file(
    result_df,
    "/user/data/output/sales_summary.csv",
    format="csv"
)
```

### 2. With Data Pipeline

```python
def data_pipeline():
    # 1. Upload input data
    hdfs_ops.upload_file("local/input.csv", "/user/data/input/")
    
    # 2. Process with Spark
    df = spark_utils.read_hdfs_file("/user/data/input/input.csv")
    processed_df = process_dataframe(df)
    
    # 3. Save results
    spark_utils.write_hdfs_file(
        processed_df,
        "/user/data/output/processed.csv"
    )
    
    # 4. Clean up temporary files
    hdfs_ops.delete_file("/user/data/temp/")
```

## Monitoring and Logging

### 1. Operation Logging

```python
# Log all HDFS operations
logger = Logger("hdfs_operations")

def logged_hdfs_operation(operation_name, operation_func, *args, **kwargs):
    start_time = time.time()
    logger.info(f"Starting {operation_name}")
    
    try:
        result = operation_func(*args, **kwargs)
        duration = time.time() - start_time
        logger.info(f"Completed {operation_name} in {duration:.2f}s")
        return result
    except Exception as e:
        logger.error(f"Failed {operation_name}: {e}")
        raise

# Use logged operations
files = logged_hdfs_operation(
    "list_directory",
    hdfs_ops.list_directory,
    "/user/data/"
)
```

### 2. Performance Monitoring

```python
# Monitor operation performance
performance_metrics = {}

def monitor_performance(operation_name):
    def decorator(func):
        def wrapper(*args, **kwargs):
            start_time = time.time()
            result = func(*args, **kwargs)
            duration = time.time() - start_time
            
            if operation_name not in performance_metrics:
                performance_metrics[operation_name] = []
            
            performance_metrics[operation_name].append(duration)
            return result
        return wrapper
    return decorator

# Apply monitoring
hdfs_ops.list_directory = monitor_performance("list_directory")(
    hdfs_ops.list_directory
)
```

## Best Practices

### 1. Resource Management
- Close connections properly
- Use connection pooling for multiple operations
- Implement proper cleanup procedures

### 2. Performance
- Use appropriate block sizes for your data
- Implement parallel processing for large datasets
- Use compression for text-based files

### 3. Security
- Always validate file paths
- Use appropriate permissions
- Implement proper authentication

### 4. Error Handling
- Implement retry logic for transient failures
- Log all operations for debugging
- Provide meaningful error messages

## Troubleshooting

### Common Issues

1. **Connection Timeout**
   ```python
   # Increase timeout values
   hdfs_config.set_connection_timeout(60000)
   hdfs_config.set_read_timeout(120000)
   ```

2. **Permission Denied**
   ```python
   # Check current user and permissions
   user = hdfs_ops.get_current_user()
   permissions = hdfs_ops.get_file_status(path)['permissions']
   ```

3. **Disk Space Issues**
   ```python
   # Check available space
   cluster_info = hdfs_ops.get_cluster_info()
   if cluster_info['available'] < required_space:
       print("Insufficient HDFS space")
   ```

## Conclusion

The HDFS operations utilities in `siege_utilities` provide comprehensive tools for distributed file system management. By following this recipe, you can:

- Efficiently manage HDFS files and directories
- Implement robust error handling and recovery
- Optimize performance for large-scale operations
- Integrate with other distributed computing tools
- Maintain security and access control

Remember to always monitor performance, implement proper error handling, and follow security best practices when working with distributed systems.

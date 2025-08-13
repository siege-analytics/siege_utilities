# File Operations Recipe

## Overview
This recipe demonstrates how to use the file operations utilities in `siege_utilities` for efficient file handling, manipulation, and processing.

## Prerequisites
- Python 3.7+
- `siege_utilities` library installed
- Basic understanding of file paths and operations

## Installation
```bash
pip install siege_utilities
```

## Basic File Operations

### 1. File Path Operations

```python
from siege_utilities.files.paths import PathUtils
from siege_utilities.files.operations import FileOperations

# Initialize utilities
path_utils = PathUtils()
file_ops = FileOperations()

# Create safe file paths
safe_path = path_utils.create_safe_path("data/input/file with spaces.txt")
print(f"Safe path: {safe_path}")

# Get file extension
extension = path_utils.get_file_extension("document.pdf")
print(f"File extension: {extension}")

# Check if path is absolute
is_absolute = path_utils.is_absolute_path("/absolute/path/file.txt")
print(f"Is absolute: {is_absolute}")
```

### 2. File Information

```python
# Get file metadata
file_info = file_ops.get_file_info("data/input/sample.csv")
print(f"File size: {file_info['size']} bytes")
print(f"Created: {file_info['created']}")
print(f"Modified: {file_info['modified']}")

# Check file existence and type
exists = file_ops.file_exists("data/input/sample.csv")
is_file = file_ops.is_file("data/input/sample.csv")
is_dir = file_ops.is_directory("data/input/")
```

### 3. File Copying and Moving

```python
# Copy file with metadata preservation
success = file_ops.copy_file(
    source="data/input/sample.csv",
    destination="data/backup/sample_backup.csv",
    preserve_metadata=True
)

# Move file
success = file_ops.move_file(
    source="data/temp/file.txt",
    destination="data/processed/file.txt"
)

# Copy directory recursively
success = file_ops.copy_directory(
    source="data/input/",
    destination="data/backup/input_backup/"
)
```

### 4. File Content Operations

```python
# Read file content
content = file_ops.read_file("data/input/config.json")
print(f"File content: {content[:100]}...")

# Write content to file
data = {"key": "value", "number": 42}
success = file_ops.write_file("data/output/config.json", data, format="json")

# Append content to file
file_ops.append_to_file("data/logs/app.log", "New log entry\n")

# Read file line by line
for line in file_ops.read_lines("data/input/large_file.txt"):
    print(line.strip())
```

### 5. File Search and Filtering

```python
# Find files by pattern
csv_files = file_ops.find_files("data/input/", pattern="*.csv")
print(f"Found CSV files: {csv_files}")

# Find files by content
matching_files = file_ops.find_files_by_content(
    "data/input/",
    search_text="important data",
    file_types=["*.txt", "*.md"]
)

# Filter files by size
large_files = file_ops.filter_files_by_size(
    "data/input/",
    min_size="1MB",
    max_size="100MB"
)
```

## Advanced File Operations

### 1. Batch File Processing

```python
# Process multiple files
file_list = ["file1.txt", "file2.txt", "file3.txt"]
for filename in file_list:
    file_path = f"data/input/{filename}"
    if file_ops.file_exists(file_path):
        # Process each file
        content = file_ops.read_file(file_path)
        processed_content = content.upper()
        
        # Save processed file
        output_path = f"data/processed/{filename}"
        file_ops.write_file(output_path, processed_content)
        print(f"Processed: {filename}")
```

### 2. File Validation

```python
# Validate file integrity
is_valid = file_ops.validate_file("data/input/sample.csv")
print(f"File is valid: {is_valid}")

# Check file permissions
permissions = file_ops.get_file_permissions("data/input/sample.csv")
print(f"File permissions: {permissions}")

# Set file permissions
file_ops.set_file_permissions("data/output/result.txt", "644")
```

### 3. File Compression

```python
# Compress file
compressed_path = file_ops.compress_file(
    "data/input/large_file.txt",
    compression_type="gzip"
)

# Decompress file
decompressed_path = file_ops.decompress_file(
    "data/input/large_file.txt.gz",
    output_path="data/output/large_file.txt"
)
```

## Error Handling

```python
try:
    # Attempt file operation
    content = file_ops.read_file("nonexistent_file.txt")
except FileNotFoundError:
    print("File not found")
except PermissionError:
    print("Permission denied")
except Exception as e:
    print(f"Unexpected error: {e}")
```

## Best Practices

### 1. Path Safety
- Always use `PathUtils.create_safe_path()` for user-provided paths
- Validate file paths before operations
- Use absolute paths when possible

### 2. Resource Management
- Close file handles properly
- Use context managers when available
- Clean up temporary files

### 3. Performance
- Use streaming for large files
- Batch operations when possible
- Cache frequently accessed file information

### 4. Security
- Validate file types before processing
- Check file permissions
- Sanitize file names

## Troubleshooting

### Common Issues

1. **Permission Denied**
   ```python
   # Check file permissions
   permissions = file_ops.get_file_permissions("file.txt")
   # Ensure proper access rights
   ```

2. **File Not Found**
   ```python
   # Verify file existence
   if file_ops.file_exists("file.txt"):
       # Proceed with operation
   ```

3. **Disk Space Issues**
   ```python
   # Check available space
   available_space = file_ops.get_disk_space("data/")
   if available_space < required_space:
       print("Insufficient disk space")
   ```

## Integration Examples

### 1. With Data Processing

```python
import pandas as pd
from siege_utilities.files.operations import FileOperations

file_ops = FileOperations()

# Read CSV file
csv_content = file_ops.read_file("data/input/sales.csv")
df = pd.read_csv(csv_content)

# Process data
processed_df = df.groupby('category').sum()

# Save processed data
file_ops.write_file("data/output/sales_summary.csv", processed_df.to_csv())
```

### 2. With Logging

```python
from siege_utilities.core.logging import Logger
from siege_utilities.files.operations import FileOperations

logger = Logger("file_operations")
file_ops = FileOperations()

# Log file operations
logger.info("Starting file processing")
try:
    file_ops.copy_file("source.txt", "destination.txt")
    logger.info("File copied successfully")
except Exception as e:
    logger.error(f"File copy failed: {e}")
```

## Performance Tips

1. **Use Streaming for Large Files**
   ```python
   # Instead of reading entire file
   for chunk in file_ops.read_file_chunks("large_file.txt", chunk_size=8192):
       process_chunk(chunk)
   ```

2. **Batch Operations**
   ```python
   # Process multiple files at once
   file_ops.batch_copy_files(source_dir, dest_dir, file_list)
   ```

3. **Caching**
   ```python
   # Cache file metadata
   file_cache = {}
   for file_path in file_list:
       if file_path not in file_cache:
           file_cache[file_path] = file_ops.get_file_info(file_path)
   ```

## Conclusion

The file operations utilities in `siege_utilities` provide a comprehensive set of tools for efficient file handling. By following this recipe, you can:

- Safely manipulate files and directories
- Process files in batches
- Handle errors gracefully
- Optimize performance for large files
- Integrate with other library components

Remember to always validate inputs, handle errors appropriately, and follow security best practices when working with files.

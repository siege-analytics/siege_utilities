# Batch File Processing

## Problem
You have a large number of files that need to be processed, transformed, or analyzed. Processing them one by one would be inefficient and time-consuming.

## Solution
Use Siege Utilities to create efficient batch processing workflows that can handle multiple files simultaneously with proper error handling and logging.

## Code Example

### 1. Basic Batch Processing
```python
import siege_utilities
import os
from pathlib import Path

# Setup logging for batch operations
siege_utilities.init_logger(
    name='batch_processor',
    log_to_file=True,
    log_dir='logs',
    level='INFO'
)

def process_single_file(file_path):
    """Process a single file and return results"""
    try:
        # Get file information
        file_size = os.path.getsize(file_path)
        file_ext = siege_utilities.get_file_extension(file_path)
        
        # Process based on file type
        if file_ext == '.csv':
            return {'file': file_path, 'type': 'csv', 'size': file_size, 'status': 'processed'}
        elif file_ext == '.txt':
            return {'file': file_path, 'type': 'text', 'size': file_size, 'status': 'processed'}
        else:
            return {'file': file_path, 'type': file_ext, 'size': file_size, 'status': 'skipped'}
            
    except Exception as e:
        siege_utilities.log_error(f"Error processing {file_path}: {e}")
        return {'file': file_path, 'type': 'unknown', 'size': 0, 'status': 'error', 'error': str(e)}

# Process all files in a directory
input_dir = 'input_files'
output_dir = 'processed_files'

# Create output directory
siege_utilities.create_directory(output_dir)

# Get all files
all_files = siege_utilities.list_files(input_dir)
siege_utilities.log_info(f"Found {len(all_files)} files to process")

# Process files in batch
results = []
for filename in all_files:
    file_path = os.path.join(input_dir, filename)
    result = process_single_file(file_path)
    results.append(result)
    
    # Log progress
    if result['status'] == 'processed':
        siege_utilities.log_info(f"✅ Processed: {filename}")
    elif result['status'] == 'skipped':
        siege_utilities.log_warning(f"⚠️ Skipped: {filename}")
    else:
        siege_utilities.log_error(f"❌ Error: {filename}")

# Summary
processed = len([r for r in results if r['status'] == 'processed'])
skipped = len([r for r in results if r['status'] == 'skipped'])
errors = len([r for r in results if r['status'] == 'error'])

siege_utilities.log_info(f"Batch processing complete: {processed} processed, {skipped} skipped, {errors} errors")
```

### 2. Advanced Batch Processing with Parallel Execution
```python
import siege_utilities
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

def advanced_batch_processor(input_dir, output_dir, max_workers=4):
    """Advanced batch processor with parallel execution"""
    
    # Setup
    siege_utilities.create_directory(output_dir)
    files = siege_utilities.list_files(input_dir)
    
    siege_utilities.log_info(f"Starting advanced batch processing of {len(files)} files with {max_workers} workers")
    
    # Process files in parallel
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        future_to_file = {
            executor.submit(process_single_file, os.path.join(input_dir, filename)): filename 
            for filename in files
        }
        
        # Process completed tasks
        completed = 0
        for future in as_completed(future_to_file):
            filename = future_to_file[future]
            try:
                result = future.result()
                completed += 1
                
                if result['status'] == 'processed':
                    siege_utilities.log_info(f"✅ [{completed}/{len(files)}] Processed: {filename}")
                else:
                    siege_utilities.log_warning(f"⚠️ [{completed}/{len(files)}] {result['status']}: {filename}")
                    
            except Exception as e:
                siege_utilities.log_error(f"❌ [{completed}/{len(files)}] Exception processing {filename}: {e}")
    
    siege_utilities.log_info("Advanced batch processing complete!")

# Usage
advanced_batch_processor('input_files', 'processed_files', max_workers=8)
```

### 3. File Type-Specific Processing
```python
import siege_utilities
import os
import json

def process_by_file_type(input_dir, output_dir):
    """Process files based on their type with specific logic"""
    
    # Group files by type
    files_by_type = {}
    for filename in siege_utilities.list_files(input_dir):
        file_path = os.path.join(input_dir, filename)
        file_ext = siege_utilities.get_file_extension(file_path)
        
        if file_ext not in files_by_type:
            files_by_type[file_ext] = []
        files_by_type[file_ext].append(file_path)
    
    # Process each file type
    for file_type, file_paths in files_by_type.items():
        siege_utilities.log_info(f"Processing {len(file_paths)} {file_type} files")
        
        if file_type == '.csv':
            process_csv_files(file_paths, output_dir)
        elif file_type == '.json':
            process_json_files(file_paths, output_dir)
        elif file_type == '.txt':
            process_text_files(file_paths, output_dir)
        else:
            siege_utilities.log_warning(f"Unknown file type: {file_type}")

def process_csv_files(file_paths, output_dir):
    """Process CSV files specifically"""
    for file_path in file_paths:
        filename = siege_utilities.get_file_name(file_path)
        output_path = os.path.join(output_dir, f"processed_{filename}")
        
        # Add CSV-specific processing logic here
        siege_utilities.copy_file(file_path, output_path)
        siege_utilities.log_info(f"Processed CSV: {filename}")

def process_json_files(file_paths, output_dir):
    """Process JSON files specifically"""
    for file_path in file_paths:
        filename = siege_utilities.get_file_name(file_path)
        output_path = os.path.join(output_dir, f"validated_{filename}")
        
        try:
            # Validate JSON
            with open(file_path, 'r') as f:
                json.load(f)  # This will raise an error if JSON is invalid
            
            siege_utilities.copy_file(file_path, output_path)
            siege_utilities.log_info(f"Validated JSON: {filename}")
        except json.JSONDecodeError:
            siege_utilities.log_error(f"Invalid JSON: {filename}")

def process_text_files(file_paths, output_dir):
    """Process text files specifically"""
    for file_path in file_paths:
        filename = siege_utilities.get_file_name(file_path)
        output_path = os.path.join(output_dir, f"analyzed_{filename}")
        
        # Add text analysis logic here
        siege_utilities.copy_file(file_path, output_path)
        siege_utilities.log_info(f"Analyzed text: {filename}")

# Usage
process_by_file_type('input_files', 'processed_files')
```

## Expected Output

```
2024-01-15 10:30:00 - batch_processor - INFO - Found 25 files to process
2024-01-15 10:30:01 - batch_processor - INFO - ✅ Processed: data1.csv
2024-01-15 10:30:01 - batch_processor - INFO - ✅ Processed: data2.csv
2024-01-15 10:30:01 - batch_processor - WARNING - ⚠️ Skipped: config.ini
2024-01-15 10:30:02 - batch_processor - INFO - ✅ Processed: report.txt
2024-01-15 10:30:02 - batch_processor - INFO - Batch processing complete: 20 processed, 3 skipped, 2 errors
```

## Notes

- **Performance**: Use parallel processing for large numbers of files
- **Error Handling**: Always implement proper error handling for batch operations
- **Logging**: Comprehensive logging helps track progress and debug issues
- **Memory Management**: For very large files, consider streaming processing
- **File Types**: Different file types may require different processing logic
- **Cleanup**: Consider implementing cleanup procedures for temporary files

## Troubleshooting

### Common Issues

1. **Memory Errors**: Reduce `max_workers` or process files in smaller batches
2. **Permission Errors**: Check file permissions and output directory access
3. **File Locking**: Some files may be locked by other processes
4. **Network Issues**: For remote files, implement retry logic

### Performance Tips

- Use `ThreadPoolExecutor` for I/O-bound operations
- Use `ProcessPoolExecutor` for CPU-bound operations
- Implement progress tracking for long-running operations
- Consider using generators for memory-efficient processing

### Next Steps

After mastering batch processing:
- Explore [File Integrity Checking](../file_operations/integrity_checking.md)
- Learn [Remote File Management](../file_operations/remote_management.md)
- Build [Data Processing Pipelines](../data_processing/batch_operations.md)

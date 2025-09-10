# 📁 Batch File Processing - Efficient Multi-File Operations

<div align="center">

![Batch Processing](https://img.shields.io/badge/Batch_Processing-Multi_File-blue)
![Efficiency](https://img.shields.io/badge/Efficiency-Parallel_Execution-green)
![Error Handling](https://img.shields.io/badge/Error_Handling-Comprehensive-orange)

**Process multiple files efficiently with proper error handling and logging** ⚡

</div>

---

## 🎯 **Problem**

You have a large number of files that need to be processed, transformed, or analyzed. Processing them one by one would be inefficient and time-consuming.

## 💡 **Solution**

Use Siege Utilities to create efficient batch processing workflows that can handle multiple files simultaneously with proper error handling, logging, and parallel execution.

## 🚀 **Quick Start**

```python
import siege_utilities
from pathlib import Path

# Process all files in a directory
input_dir = 'input_files'
output_dir = 'processed_files'

# Create output directory
siege_utilities.ensure_path_exists(output_dir)

# Get all files and process
files = siege_utilities.list_directory(input_dir)
results = [process_single_file(f) for f in files]

print(f"✅ Processed {len(results)} files")
```

## 📋 **Complete Implementation**

### **1. Basic Batch Processing**

```python
import siege_utilities
import os
from pathlib import Path

# Setup logging for batch operations
siege_utilities.log_info("Starting batch processing operations")

def process_single_file(file_path):
    """Process a single file and return results"""
    try:
        # Get file information
        file_size = siege_utilities.get_file_size(file_path)
        file_ext = Path(file_path).suffix
        
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
siege_utilities.ensure_path_exists(output_dir)

# Get all files
all_files = siege_utilities.list_directory(input_dir)
siege_utilities.log_info(f"Found {len(all_files)} files to process")

# Process files in batch
results = []
for filename in all_files:
    file_path = Path(input_dir) / filename
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

### **2. Advanced Batch Processing with Parallel Execution**

```python
import siege_utilities
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

def advanced_batch_processor(input_dir, output_dir, max_workers=4):
    """Advanced batch processor with parallel execution"""
    
    # Setup
    siege_utilities.ensure_path_exists(output_dir)
    files = siege_utilities.list_directory(input_dir)
    
    siege_utilities.log_info(f"Starting advanced batch processing of {len(files)} files with {max_workers} workers")
    
    # Process files in parallel
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        future_to_file = {
            executor.submit(process_single_file, Path(input_dir) / filename): filename 
            for filename in files
        }
        
        # Process completed tasks
        results = []
        for future in as_completed(future_to_file):
            filename = future_to_file[future]
            try:
                result = future.result()
                results.append(result)
                
                # Log progress
                if result['status'] == 'processed':
                    siege_utilities.log_info(f"✅ Processed: {filename}")
                elif result['status'] == 'skipped':
                    siege_utilities.log_warning(f"⚠️ Skipped: {filename}")
                else:
                    siege_utilities.log_error(f"❌ Error: {filename}")
                    
            except Exception as e:
                siege_utilities.log_error(f"❌ Exception processing {filename}: {e}")
                results.append({
                    'file': filename,
                    'status': 'error',
                    'error': str(e)
                })
    
    return results

# Run advanced batch processing
results = advanced_batch_processor('input_files', 'processed_files', max_workers=4)
```

### **3. File Type-Specific Processing**

```python
def process_csv_file(file_path):
    """Process CSV files with data validation"""
    try:
        import pandas as pd
        
        # Read CSV file
        df = pd.read_csv(file_path)
        
        # Basic validation
        row_count = len(df)
        column_count = len(df.columns)
        
        # Check for missing values
        missing_values = df.isnull().sum().sum()
        
        # Process data (example: remove duplicates)
        df_clean = df.drop_duplicates()
        duplicates_removed = row_count - len(df_clean)
        
        # Save processed file
        output_path = Path(file_path).parent / f"processed_{Path(file_path).name}"
        df_clean.to_csv(output_path, index=False)
        
        return {
            'file': file_path,
            'type': 'csv',
            'original_rows': row_count,
            'processed_rows': len(df_clean),
            'columns': column_count,
            'missing_values': missing_values,
            'duplicates_removed': duplicates_removed,
            'output_file': str(output_path),
            'status': 'processed'
        }
        
    except Exception as e:
        siege_utilities.log_error(f"Error processing CSV {file_path}: {e}")
        return {'file': file_path, 'type': 'csv', 'status': 'error', 'error': str(e)}

def process_text_file(file_path):
    """Process text files with content analysis"""
    try:
        # Read text file
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Analyze content
        lines = content.split('\n')
        words = content.split()
        characters = len(content)
        
        # Basic text processing (example: remove empty lines)
        non_empty_lines = [line for line in lines if line.strip()]
        
        # Save processed file
        output_path = Path(file_path).parent / f"processed_{Path(file_path).name}"
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(non_empty_lines))
        
        return {
            'file': file_path,
            'type': 'text',
            'original_lines': len(lines),
            'processed_lines': len(non_empty_lines),
            'words': len(words),
            'characters': characters,
            'output_file': str(output_path),
            'status': 'processed'
        }
        
    except Exception as e:
        siege_utilities.log_error(f"Error processing text {file_path}: {e}")
        return {'file': file_path, 'type': 'text', 'status': 'error', 'error': str(e)}

def smart_file_processor(file_path):
    """Smart processor that handles different file types"""
    file_ext = Path(file_path).suffix.lower()
    
    if file_ext == '.csv':
        return process_csv_file(file_path)
    elif file_ext == '.txt':
        return process_text_file(file_path)
    elif file_ext in ['.json', '.xml']:
        return process_structured_file(file_path)
    else:
        return {'file': file_path, 'type': file_ext, 'status': 'skipped', 'reason': 'Unsupported file type'}
```

### **4. Progress Tracking and Reporting**

```python
def batch_processor_with_progress(input_dir, output_dir, file_types=None):
    """Batch processor with detailed progress tracking"""
    
    # Setup
    siege_utilities.ensure_path_exists(output_dir)
    files = siege_utilities.list_directory(input_dir)
    
    if file_types:
        files = [f for f in files if Path(f).suffix.lower() in file_types]
    
    total_files = len(files)
    siege_utilities.log_info(f"Starting batch processing of {total_files} files")
    
    # Initialize counters
    processed = 0
    skipped = 0
    errors = 0
    results = []
    
    # Process files with progress tracking
    for i, filename in enumerate(files, 1):
        file_path = Path(input_dir) / filename
        
        # Show progress
        progress = (i / total_files) * 100
        siege_utilities.log_info(f"Progress: {progress:.1f}% ({i}/{total_files}) - Processing {filename}")
        
        # Process file
        result = smart_file_processor(file_path)
        results.append(result)
        
        # Update counters
        if result['status'] == 'processed':
            processed += 1
            siege_utilities.log_info(f"✅ {filename} - {result.get('type', 'unknown')}")
        elif result['status'] == 'skipped':
            skipped += 1
            siege_utilities.log_warning(f"⚠️ {filename} - {result.get('reason', 'skipped')}")
        else:
            errors += 1
            siege_utilities.log_error(f"❌ {filename} - {result.get('error', 'unknown error')}")
    
    # Generate comprehensive report
    report = generate_batch_report(results, input_dir, output_dir)
    
    return results, report

def generate_batch_report(results, input_dir, output_dir):
    """Generate comprehensive batch processing report"""
    
    # Calculate statistics
    total_files = len(results)
    processed = len([r for r in results if r['status'] == 'processed'])
    skipped = len([r for r in results if r['status'] == 'skipped'])
    errors = len([r for r in results if r['status'] == 'error'])
    
    # File type breakdown
    file_types = {}
    for result in results:
        file_type = result.get('type', 'unknown')
        if file_type not in file_types:
            file_types[file_type] = {'processed': 0, 'skipped': 0, 'errors': 0}
        
        status = result['status']
        file_types[file_type][status] += 1
    
    # Generate report
    report = {
        'summary': {
            'total_files': total_files,
            'processed': processed,
            'skipped': skipped,
            'errors': errors,
            'success_rate': (processed / total_files) * 100 if total_files > 0 else 0
        },
        'file_types': file_types,
        'input_directory': input_dir,
        'output_directory': output_dir,
        'timestamp': siege_utilities.get_current_timestamp(),
        'details': results
    }
    
    # Save report
    report_path = Path(output_dir) / 'batch_processing_report.json'
    siege_utilities.save_json(report, report_path)
    
    return report
```

### **5. Error Handling and Recovery**

```python
def robust_batch_processor(input_dir, output_dir, max_retries=3):
    """Robust batch processor with error handling and recovery"""
    
    siege_utilities.ensure_path_exists(output_dir)
    files = siege_utilities.list_directory(input_dir)
    
    results = []
    retry_queue = []
    
    # First pass: process all files
    for filename in files:
        file_path = Path(input_dir) / filename
        
        try:
            result = smart_file_processor(file_path)
            results.append(result)
            
            if result['status'] == 'error':
                retry_queue.append((filename, 1))  # (filename, retry_count)
                
        except Exception as e:
            siege_utilities.log_error(f"Unexpected error processing {filename}: {e}")
            results.append({
                'file': filename,
                'status': 'error',
                'error': str(e)
            })
            retry_queue.append((filename, 1))
    
    # Retry failed files
    while retry_queue and max_retries > 0:
        siege_utilities.log_info(f"Retrying {len(retry_queue)} failed files (attempt {max_retries})")
        
        current_retry_queue = retry_queue.copy()
        retry_queue.clear()
        
        for filename, retry_count in current_retry_queue:
            if retry_count >= max_retries:
                siege_utilities.log_warning(f"Max retries reached for {filename}")
                continue
                
            file_path = Path(input_dir) / filename
            
            try:
                # Wait before retry
                import time
                time.sleep(1)  # Simple backoff
                
                result = smart_file_processor(file_path)
                
                # Update result in results list
                for i, r in enumerate(results):
                    if r['file'] == filename:
                        results[i] = result
                        break
                
                if result['status'] == 'error':
                    retry_queue.append((filename, retry_count + 1))
                    
            except Exception as e:
                siege_utilities.log_error(f"Retry {retry_count + 1} failed for {filename}: {e}")
                retry_queue.append((filename, retry_count + 1))
        
        max_retries -= 1
    
    return results
```

## 📊 **Expected Output**

```
2024-01-15 10:30:00 - Starting batch processing operations
2024-01-15 10:30:01 - Found 25 files to process
2024-01-15 10:30:01 - Progress: 4.0% (1/25) - Processing data_2024_01.csv
2024-01-15 10:30:01 - ✅ data_2024_01.csv - csv
2024-01-15 10:30:01 - Progress: 8.0% (2/25) - Processing report_2024_01.txt
2024-01-15 10:30:01 - ✅ report_2024_01.txt - text
2024-01-15 10:30:01 - Progress: 12.0% (3/25) - Processing config.json
2024-01-15 10:30:01 - ⚠️ config.json - Unsupported file type
...
2024-01-15 10:30:05 - Batch processing complete: 20 processed, 3 skipped, 2 errors
2024-01-15 10:30:05 - Generated batch processing report: processed_files/batch_processing_report.json
```

## 🔧 **Configuration Options**

### **File Type Filters**
```python
# Process only specific file types
file_types = ['.csv', '.txt', '.json']
results = batch_processor_with_progress('input_files', 'processed_files', file_types)
```

### **Parallel Processing**
```python
# Adjust worker count based on system resources
max_workers = min(8, os.cpu_count())  # Use up to 8 workers or CPU count
results = advanced_batch_processor('input_files', 'processed_files', max_workers)
```

### **Error Handling**
```python
# Configure retry behavior
max_retries = 3
results = robust_batch_processor('input_files', 'processed_files', max_retries)
```

## 🚨 **Troubleshooting**

### **Common Issues**

1. **📁 Directory Permissions**: Ensure write access to output directory
2. **💾 Disk Space**: Check available disk space for processed files
3. **🔒 File Locks**: Some files may be locked by other processes
4. **⏱️ Timeouts**: Large files may need longer processing time

### **Performance Tips**

- **⚡ Parallel Processing**: Use ThreadPoolExecutor for I/O-bound operations
- **💾 Memory Management**: Process large files in chunks
- **📊 Progress Tracking**: Monitor progress for long-running operations
- **🔄 Incremental Processing**: Process only new or changed files

### **Best Practices**

- **📝 Logging**: Always log operations for debugging and monitoring
- **🛡️ Error Handling**: Implement comprehensive error handling
- **📊 Reporting**: Generate detailed reports for quality assurance
- **🔄 Recovery**: Implement retry mechanisms for transient failures
- **📁 Organization**: Use consistent naming conventions for output files

## 🚀 **Next Steps**

After mastering batch processing:

- **[Data Validation](Data-Validation.md)** - Validate processed data quality
- **[Automation](Automation-Guide.md)** - Automate batch processing workflows
- **[Performance Optimization](Performance-Optimization.md)** - Optimize processing speed
- **[Monitoring](Monitoring-Guide.md)** - Monitor batch processing operations

## 🔗 **Related Recipes**

- **[File Operations](File-Operations.md)** - Basic file handling operations
- **[Data Processing](Data-Processing.md)** - Process and transform data
- **[Error Handling](Error-Handling.md)** - Comprehensive error management
- **[Performance Optimization](Performance-Optimization.md)** - Optimize processing workflows

---

<div align="center">

**Ready to process files efficiently?** 📁

**[Next: Data Validation](Data-Validation.md)** → **[Automation Guide](Automation-Guide.md)**

</div>

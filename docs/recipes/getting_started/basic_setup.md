# Basic Setup

## Problem
You need to install and configure Siege Utilities on your system to start using its powerful utilities for data engineering, analytics, and file operations.

## Solution
Install Siege Utilities using pip and verify the installation with a simple test script.

## Code Example

### 1. Install Siege Utilities
```bash
# Install from PyPI
pip install siege-utilities

# Or install from source
git clone https://github.com/siege-analytics/siege_utilities.git
cd siege_utilities
pip install -e .
```

### 2. Verify Installation
```python
import siege_utilities

# Check available functions
print(f"Available functions: {len(dir(siege_utilities))}")
print(f"First 10 functions: {dir(siege_utilities)[:10]}")

# Test basic functionality
print(f"Package version: {siege_utilities.__version__}")
```

### 3. Basic Configuration
```python
import siege_utilities

# Initialize logging
siege_utilities.init_logger(
    name='my_app',
    log_to_file=True,
    log_dir='logs',
    level='INFO'
)

# Test logging
siege_utilities.log_info("Siege Utilities initialized successfully!")
siege_utilities.log_debug("Debug information available")
```

### 4. Test File Operations
```python
import siege_utilities
import os

# Create a test directory
test_dir = 'test_siege_utilities'
siege_utilities.create_directory(test_dir)

# Create a test file
test_file = os.path.join(test_dir, 'test.txt')
with open(test_file, 'w') as f:
    f.write('Hello Siege Utilities!')

# Test file operations
files = siege_utilities.list_files(test_dir)
print(f"Files in {test_dir}: {files}")

# Clean up
siege_utilities.delete_file(test_file)
siege_utilities.delete_file(test_dir)
```

## Expected Output

```
Available functions: 568
First 10 functions: ['__builtins__', '__cached__', '__doc__', '__file__', '__loader__', '__name__', '__package__', '__path__', '__spec__', '__version__']
Package version: 1.0.0
2024-01-15 10:30:00 - my_app - INFO - Siege Utilities initialized successfully!
2024-01-15 10:30:00 - my_app - DEBUG - Debug information available
Files in test_siege_utilities: ['test.txt']
```

## Notes

- **Python Version**: Siege Utilities requires Python 3.8 or higher
- **Dependencies**: The package will automatically install required dependencies
- **Virtual Environment**: It's recommended to use a virtual environment
- **Permissions**: Some operations may require appropriate file system permissions
- **Logging**: Logs are created in the specified directory with automatic rotation

## Troubleshooting

### Common Issues

1. **Import Error**: Make sure you're using the correct Python environment
2. **Permission Denied**: Check file permissions for logging and file operations
3. **Missing Dependencies**: Run `pip install -r requirements.txt` if installing from source

### Next Steps

After successful installation:
- Try the [First Steps](first_steps.md) recipe
- Explore [File Operations](../file_operations/batch_processing.md) recipes
- Set up [Logging](../system_admin/log_management.md) for your application

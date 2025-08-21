# Basic Setup - Getting Started with Siege Utilities

## Problem

You need to install and configure Siege Utilities on your system to start using its powerful utilities for data engineering, analytics, and file operations.

## Solution

Install Siege Utilities using pip and verify the installation with a simple test script. Configure logging and test basic functionality to ensure everything is working correctly.

## Quick Start

```bash
# Install from PyPI
pip install siege-utilities

# Verify installation
python -c "import siege_utilities; print('Installation successful!')"
```

## Complete Implementation

### 1. Installation Methods

#### Option A: Install from PyPI (Recommended)
```bash
# Install the latest stable version
pip install siege-utilities

# Install with specific version
pip install siege-utilities==2.0.0

# Install with extra dependencies
pip install siege-utilities[full]
```

#### Option B: Install from Source
```bash
# Clone the repository
git clone https://github.com/siege-analytics/siege_utilities.git
cd siege_utilities

# Install in development mode
pip install -e .
```

#### Option C: Install in Virtual Environment (Recommended)
```bash
# Create virtual environment
python -m venv siege_env

# Activate virtual environment
# On Windows: siege_env\Scripts\activate
# On macOS/Linux: source siege_env/bin/activate

# Install Siege Utilities
pip install siege-utilities
```

### 2. Verify Installation

```python
import siege_utilities

# Check available functions
print(f"Available functions: {len(dir(siege_utilities))}")
print(f"First 10 functions: {dir(siege_utilities)[:10]}")

# Test basic functionality
print(f"Package version: {siege_utilities.__version__}")

# Check specific modules
print(f"Core modules: {[m for m in dir(siege_utilities) if not m.startswith('_')]}")
```

### 3. Basic Configuration

```python
import siege_utilities
from pathlib import Path

# Initialize logging
siege_utilities.log_info("Starting Siege Utilities configuration")

# Initialize logging with custom configuration
siege_utilities.init_logger(
    name='my_app',
    log_to_file=True,
    log_dir='logs',
    level='INFO'
)

# Test logging functionality
siege_utilities.log_info("Siege Utilities initialized successfully!")
siege_utilities.log_debug("Debug information available")
siege_utilities.log_warning("Warning messages work")
siege_utilities.log_error("Error logging functional")

# Check logging configuration
print("Logging system initialized")
```

### 4. Test File Operations

```python
import siege_utilities
from pathlib import Path

# Create a test directory
test_dir = Path('test_siege_utilities')
siege_utilities.ensure_path_exists(test_dir)

# Create a test file
test_file = test_dir / 'test.txt'
with open(test_file, 'w') as f:
    f.write('Hello Siege Utilities!')

# Test file operations
files = siege_utilities.list_directory(test_dir)
print(f"Files in {test_dir}: {files}")

# Test file existence
file_exists = siege_utilities.file_exists(test_file)
print(f"Test file exists: {file_exists}")

# Test file size
file_size = siege_utilities.get_file_size(test_file)
print(f"Test file size: {file_size} bytes")

# Clean up
siege_utilities.remove_tree(test_dir)
print("Cleanup completed")
```

### 5. Test Core Utilities

```python
import siege_utilities
import pandas as pd

# Test string utilities
text = "Hello World"
uppercase = siege_utilities.to_uppercase(text)
print(f"String utility test: {text} -> {uppercase}")

# Test path utilities
test_path = "path/to/file.txt"
normalized = siege_utilities.normalize_path(test_path)
print(f"Path utility test: {test_path} -> {normalized}")

# Test data utilities
data = pd.DataFrame({'A': [1, 2, 3], 'B': ['a', 'b', 'c']})
print(f"DataFrame created: {data.shape}")

print("Core utilities test completed")
```

## Expected Output

```
Available functions: 1147
First 10 functions: ['__builtins__', '__cached__', '__doc__', '__file__', '__loader__', '__name__', '__package__', '__path__', '__spec__', '__version__']
Package version: 2.0.0
Core modules: ['abs', 'acos', 'acosh', 'add_months', 'aggregate', 'any_value', 'approx_count_distinct', 'approx_percentile', 'array', 'array_agg']
Logging system initialized
Files in test_siege_utilities: ['test.txt']
Test file exists: True
Test file size: 22 bytes
Cleanup completed
String utility test: Hello World -> HELLO WORLD
Path utility test: path/to/file.txt -> path/to/file.txt
DataFrame created: (3, 2)
Core utilities test completed
```

## Configuration Options

### Logging Configuration
```python
# Custom logging configuration
siege_utilities.init_logger(
    name='my_app',
    log_to_file=True,
    log_dir='logs',
    level='DEBUG',  # DEBUG, INFO, WARNING, ERROR
    max_bytes=10485760,  # 10MB
    backup_count=5
)
```

### Environment Variables
```bash
# Set environment variables for configuration
export SIEGE_LOG_LEVEL=DEBUG
export SIEGE_LOG_DIR=/var/log/siege
export SIEGE_CONFIG_PATH=/etc/siege/config.yaml
```

## Troubleshooting

### Common Issues

1. **Import Error**: Make sure you're using the correct Python environment
2. **Permission Denied**: Check file permissions for logging and file operations
3. **Missing Dependencies**: Run `pip install -r requirements.txt` if installing from source
4. **Python Version**: Ensure Python 3.8+ is installed
5. **Network Issues**: Check internet connection for PyPI installation

### Installation Problems

```bash
# Force reinstall
pip install --force-reinstall siege-utilities

# Install with specific Python version
python3.9 -m pip install siege-utilities

# Check installed packages
pip list | grep siege

# Uninstall and reinstall
pip uninstall siege-utilities
pip install siege-utilities
```

## System Requirements

### Minimum Requirements
- **Python**: 3.8 or higher
- **RAM**: 512MB available
- **Disk Space**: 100MB for installation
- **OS**: Windows 10+, macOS 10.14+, Linux (Ubuntu 18.04+)

### Recommended Requirements
- **Python**: 3.9 or higher
- **RAM**: 2GB available
- **Disk Space**: 500MB for installation and data
- **OS**: Latest stable versions

## Next Steps

After successful setup:

- Learn basic usage patterns
- Set up client profiles and branding
- Master file handling operations
- Run comprehensive tests
- Explore advanced features

## Related Documentation

- **Getting Started Guide** - First steps with Siege Utilities
- **Testing Guide** - Verify your installation
- **Client Management** - Set up client profiles
- **Analytics Integration** - Connect data sources

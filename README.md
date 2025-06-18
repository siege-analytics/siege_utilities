# Siege Utilities

A comprehensive Python utilities package with **enhanced auto-discovery** that automatically imports and makes all functions mutually available across modules.

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## ✨ Key Features

- 🔄 **Auto-Discovery**: Automatically finds and imports all functions from new modules
- 🌐 **Mutual Availability**: All 500+ functions accessible from any module without imports
- 📝 **Universal Logging**: Comprehensive logging system available everywhere
- 🛡️ **Graceful Dependencies**: Optional features (PySpark, geospatial) fail gracefully
- 📊 **Built-in Diagnostics**: Monitor package health and function availability
- ⚡ **Zero Configuration**: Just `import siege_utilities` and everything works

## 🚀 Quick Start

```bash
pip install siege-utilities
```

```python
import siege_utilities

# All 500+ functions are immediately available
siege_utilities.log_info("Package loaded successfully!")

# File operations
hash_value = siege_utilities.get_file_hash("myfile.txt")
siege_utilities.ensure_path_exists("data/processed")

# String utilities  
clean_text = siege_utilities.remove_wrapping_quotes_and_trim('  "hello"  ')

# Distributed computing (if PySpark available)
try:
    config = siege_utilities.create_hdfs_config("/data")
    spark, data_path = siege_utilities.setup_distributed_environment()
except NameError:
    siege_utilities.log_warning("Distributed features not available")

# Package diagnostics
info = siege_utilities.get_package_info()
print(f"Available functions: {info['total_functions']}")
print(f"Failed imports: {len(info['failed_imports'])}")
```

## 📦 What's Included

### Core Utilities (`siege_utilities.core`)
- **Logging**: Comprehensive logging with file rotation, multiple levels
- **String Utils**: Text processing, quote removal, trimming

### File Utilities (`siege_utilities.files`) 
- **Hashing**: SHA256, MD5, quick signatures, integrity verification
- **Operations**: File existence, row counting, duplicate detection, data writing
- **Paths**: Directory creation, zip extraction, path management
- **Remote**: HTTP downloads with progress bars, URL-to-path conversion
- **Shell**: Subprocess management, command execution

### Distributed Computing (`siege_utilities.distributed`)
- **HDFS Operations**: Hadoop filesystem integration, data syncing
- **Spark Utils**: PySpark workflows, DataFrame processing, geospatial operations
- **Configuration**: Environment setup, cluster management

### Geospatial (`siege_utilities.geo`)
- **Geocoding**: Nominatim integration, address processing, coordinate validation
- **Spatial Analysis**: Geographic data processing, coordinate systems

## 🌟 Unique Auto-Discovery System

Unlike traditional packages, Siege Utilities uses an **enhanced auto-discovery system**:

```python
# Traditional approach - lots of imports needed
from package.module1 import function_a
from package.module2 import function_b
from package.core.logging import log_info

def my_function():
    log_info("Starting process")
    result_a = function_a()
    result_b = function_b()

# Siege Utilities approach - everything just works
import siege_utilities

def my_function():
    log_info("Starting process")      # Available everywhere
    result_a = function_a()           # Available everywhere  
    result_b = function_b()           # Available everywhere
```

### How It Works

1. **Phase 1**: Bootstrap core logging system
2. **Phase 2**: Import modules in dependency order
3. **Phase 3**: Auto-discover all `.py` files and subpackages
4. **Phase 4**: Inject all functions into all modules (mutual availability)
5. **Phase 5**: Provide comprehensive diagnostics

**Result**: 500+ functions accessible from anywhere with zero imports!

## 📊 Package Diagnostics

Monitor your package health:

```python
import siege_utilities

# Get comprehensive package information
info = siege_utilities.get_package_info()
print(f"Total functions: {info['total_functions']}")
print(f"Loaded modules: {info['total_modules']}")
print(f"Failed imports: {info['failed_imports']}")

# List functions by pattern
log_functions = siege_utilities.list_available_functions("log_")
file_functions = siege_utilities.list_available_functions("file")

# Check dependencies
deps = siege_utilities.check_dependencies()
print(f"PySpark available: {deps['pyspark']}")
print(f"Geopy available: {deps['geopy']}")

# Get function information
func_info = siege_utilities.get_function_info("get_file_hash")
print(f"Function from module: {func_info['module']}")
```

## 🔧 Installation Options

```bash
# Basic installation
pip install siege-utilities

# With distributed computing support
pip install siege-utilities[distributed]

# With geospatial support  
pip install siege-utilities[geo]

# Full installation (all optional dependencies)
pip install siege-utilities[distributed,geo,dev]

# Development installation
git clone https://github.com/siege-analytics/siege_utilities.git
cd siege_utilities
pip install -e ".[distributed,geo,dev]"
```

## 📖 Detailed Examples

### File Processing Pipeline

```python
import siege_utilities

def process_data_files(input_dir, output_dir):
    """Complete file processing pipeline using siege utilities."""
    
    # Setup with logging
    siege_utilities.init_logger("data_processor", log_to_file=True)
    siege_utilities.log_info(f"Starting processing: {input_dir} -> {output_dir}")
    
    # Ensure output directory exists
    siege_utilities.ensure_path_exists(output_dir)
    
    # Process each file
    for file_path in pathlib.Path(input_dir).glob("*.txt"):
        if siege_utilities.check_if_file_exists_at_path(file_path):
            
            # Generate file hash for integrity
            file_hash = siege_utilities.get_file_hash(file_path)
            siege_utilities.log_info(f"Processing {file_path.name}: {file_hash}")
            
            # Count rows and check for issues
            total_rows = siege_utilities.count_total_rows_in_file_using_sed(file_path)
            empty_rows = siege_utilities.count_empty_rows_in_file_using_awk(file_path)
            
            siege_utilities.log_info(f"File stats: {total_rows} total, {empty_rows} empty")
            
            # Process and save results
            output_path = output_dir / f"processed_{file_path.name}"
            # ... your processing logic here
            
    siege_utilities.log_info("Processing complete!")
```

### Distributed Computing Workflow

```python
import siege_utilities

def distributed_geocoding_pipeline(data_path):
    """Distributed geocoding using Spark and HDFS."""
    
    # Check if distributed features are available
    deps = siege_utilities.check_dependencies()
    if not deps['pyspark']:
        siege_utilities.log_error("PySpark required for distributed processing")
        return
    
    # Setup distributed environment
    config = siege_utilities.create_cluster_config(data_path)
    spark, hdfs_path = siege_utilities.setup_distributed_environment(config)
    
    if spark and hdfs_path:
        siege_utilities.log_info(f"Distributed environment ready: {hdfs_path}")
        
        # Load and process data
        df = spark.read.parquet(hdfs_path)
        df = siege_utilities.sanitise_dataframe_column_names(df)
        df = siege_utilities.validate_geocode_data(df, "latitude", "longitude")
        
        # Geocoding operations
        geocoder = siege_utilities.NominatimGeoClassifier()
        # ... geocoding logic here
        
        # Save results
        output_path = hdfs_path.replace("input", "output")
        siege_utilities.write_df_to_parquet(df, output_path)
        
        spark.stop()
    else:
        siege_utilities.log_error("Failed to setup distributed environment")
```

## 🏗️ Development

### Adding New Functions

Just create a new `.py` file anywhere in the package:

```python
# siege_utilities/my_new_module.py

def my_awesome_function(data):
    """This function will be auto-discovered!"""
    log_info("my_awesome_function called")  # Logging available automatically
    
    # All other siege utilities functions are available
    file_hash = get_file_hash(data)  # No import needed!
    ensure_path_exists("output")     # No import needed!
    
    return f"processed_{file_hash}"

def another_function():
    """This will also be auto-discovered!"""
    return "Hello from auto-discovery!"
```

**That's it!** Next time you import siege_utilities, these functions will be automatically available:

```python
import siege_utilities

# Your new functions are automatically available
result = siege_utilities.my_awesome_function("data.txt")
greeting = siege_utilities.another_function()

# And they're mutually available in other modules too!
```

### Running Diagnostics

```bash
# Check package health (run from package directory)
python3 check_imports.py

# Or from Python
python3 -c "
import siege_utilities
info = siege_utilities.get_package_info()
print(f'Functions: {info[\"total_functions\"]}')
print(f'Modules: {info[\"total_modules\"]}')
print(f'Failed: {len(info[\"failed_imports\"])}')
"
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Add your functions to existing modules or create new ones
4. Test with: `python3 check_imports.py`
5. Commit changes: `git commit -am 'Add new feature'`
6. Push: `git push origin feature-name`
7. Submit a Pull Request

The auto-discovery system will automatically find and integrate your new functions!

## 📝 License

MIT License - see LICENSE file for details.

## 🙏 Acknowledgments

- Built by [Siege Analytics](https://github.com/siege-analytics)
- Inspired by the need for truly seamless Python utilities
- Special thanks to the auto-discovery pattern that makes this possible

---

**Siege Utilities**: Where every function is available everywhere! 🚀

---

## Updated setup.py for PyPI

```python
from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="siege-utilities",
    version="1.0.0",
    author="Dheeraj Chand",
    author_email="dheeraj@siegeanalytics.com",
    description="A comprehensive Python utilities package with enhanced auto-discovery",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/siege-analytics/siege_utilities",
    project_urls={
        "Bug Tracker": "https://github.com/siege-analytics/siege_utilities/issues",
        "Documentation": "https://github.com/siege-analytics/siege_utilities#readme",
        "Source Code": "https://github.com/siege-analytics/siege_utilities",
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Utilities",
    ],
    packages=find_packages(),
    python_requires=">=3.8",
    install_requires=[
        "pathlib2; python_version<'3.4'",
        "requests>=2.25.0",
        "tqdm>=4.60.0",
    ],
    extras_require={
        "distributed": [
            "pyspark>=3.0.0",
        ],
        "geo": [
            "geopy>=2.0.0",
            "apache-sedona>=1.4.0",
        ],
        "dev": [
            "pytest>=6.0.0",
            "black>=21.0.0",
            "flake8>=3.8.0",
            "twine>=3.4.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "siege-utils-check=siege_utilities.check_imports:main",
        ],
    },
    keywords="utilities, auto-discovery, logging, file-operations, distributed-computing, geocoding",
    include_package_data=True,
    zip_safe=False,
)
```

## PyPI Publishing Commands

```bash
# 1. Install build dependencies
pip install build twine

# 2. Clean previous builds
rm -rf dist/ build/ *.egg-info/

# 3. Build the package
python -m build

# 4. Check the package
twine check dist/*

# 5. Upload to Test PyPI first
twine upload --repository testpypi dist/*

# 6. Test installation from Test PyPI
pip install --index-url https://test.pypi.org/simple/ siege-utilities

# 7. If everything works, upload to real PyPI
twine upload dist/*
```



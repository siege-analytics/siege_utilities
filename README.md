# Siege Utilities

A Python utilities package with **enhanced auto-discovery** that automatically imports and makes all functions mutually available across modules.

Because this makes use of Spark, you will need to have all relevant environment variables configured to get access to Spark/Sedona functionality, such as

- `JAVA_HOME`
- `SPARK_HOME`
- `HADOOP_HOME`
- `SCALA_HOME`

My recommendation is to install things with [SDK Man](https://sdkman.io). I have a fairly intense `.zshrc` configuration that you can discover more about in my [backup repository](https://github.com/dheerajchand/zshrc_backups/tree/main).

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Documentation](https://img.shields.io/badge/docs-GitHub%20Pages-blue)](https://siege-analytics.github.io/siege_utilities/)

## ✨ Key Features

- 🔄 **Auto-Discovery**: Automatically finds and imports all functions from new modules
- 🌐 **Mutual Availability**: All 500+ functions accessible from any module without imports
- 📝 **Universal Logging**: Comprehensive logging system available everywhere
- 🛡️ **Graceful Dependencies**: Optional features (PySpark, geospatial) fail gracefully
- 📊 **Built-in Diagnostics**: Monitor package health and function availability
- ⚡ **Zero Configuration**: Just `import siege_utilities` and everything works
- 👥 **Client Management**: Comprehensive client profile management with contact info and design artifacts
- 🔌 **Connection Persistence**: Notebook, Spark, and database connection management and testing
- 🔗 **Project Association**: Link clients with projects for better organization

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

### Hygiene (`siege_utilities.hygiene`)
- **Generate Docstrings**: Add docstrings to functions according to a template

### Configuration Management (`siege_utilities.config`)
- **Client Profiles**: Contact information, design artifacts, preferences, and project associations
- **Connection Profiles**: Notebook, Spark, database, and API connection management
- **Project Management**: Project setup, directory structures, and configuration
- **Database Configuration**: Connection strings, JDBC support, and connection testing

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

### Client and Connection Management

```python
import siege_utilities

def setup_client_project():
    """Complete client and project setup using siege utilities."""
    
    # Create client profile with contact info and design artifacts
    contact_info = {
        "primary_contact": "Jane Smith",
        "email": "jane.smith@acmecorp.com",
        "phone": "+1-555-0123",
        "address": "123 Business Ave, Tech City, TC 12345"
    }
    
    client = siege_utilities.create_client_profile(
        "Acme Corporation",
        "ACME001",
        contact_info,
        industry="Technology",
        logo_path="/assets/logos/acme_logo.png",
        brand_colors=["#0066CC", "#FF6600"],
        data_format="parquet",
        report_style="executive"
    )
    
    # Create project configuration
    project = siege_utilities.create_project_config(
        "Acme Data Analytics Platform",
        "ACME001",
        description="Comprehensive analytics platform for Acme Corporation"
    )
    
    # Setup project directories
    siege_utilities.setup_project_directories(project)
    
    # Associate client with project
    siege_utilities.associate_client_with_project("ACME001", "ACME001")
    
    # Create and test connections
    notebook_conn = siege_utilities.create_connection_profile(
        "Acme Jupyter Lab",
        "notebook",
        {"url": "http://localhost:8888", "token": "abc123"}
    )
    
    spark_conn = siege_utilities.create_connection_profile(
        "Acme Spark Cluster",
        "spark",
        {"master_url": "spark://spark-master:7077"}
    )
    
    # Test connections
    notebook_result = siege_utilities.test_connection(notebook_conn['connection_id'])
    spark_result = siege_utilities.test_connection(spark_conn['connection_id'])
    
    if notebook_result['success'] and spark_result['success']:
        siege_utilities.log_info("All connections successful!")
    else:
        siege_utilities.log_warning("Some connections failed")
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

## 🧪 Testing & Quality Assurance

This package includes a comprehensive test suite designed to **smoke out broken functions** and ensure reliability.

### Quick Smoke Test

```bash
# Basic functionality check (30 seconds)
python run_tests.py

# Or with specific mode
python run_tests.py --mode smoke
```

### Test Installation

```bash
# Install test dependencies
pip install -r test_requirements.txt

# Or install with development extras
pip install -e ".[dev]"
```

### Test Modes

#### 🔥 Smoke Tests (Recommended First)
```bash
python run_tests.py --mode smoke
```
- **Purpose**: Quickly find broken functions
- **Duration**: ~30 seconds
- **Stops after**: 10 failures
- **Best for**: Initial assessment

#### ⚡ Fast Tests
```bash
python run_tests.py --mode fast
```
- **Purpose**: Skip slow tests, focus on core functionality
- **Duration**: ~2 minutes
- **Excludes**: Network tests, large file operations

#### 🧪 Unit Tests
```bash
python run_tests.py --mode unit
```
- **Purpose**: Test individual functions in isolation
- **Duration**: ~5 minutes
- **Includes**: All unit tests

#### 📊 Coverage Analysis
```bash
python run_tests.py --mode coverage
```
- **Purpose**: Generate code coverage report
- **Duration**: ~10 minutes
- **Output**: HTML coverage report in `htmlcov/`

#### 🎯 All Tests
```bash
python run_tests.py --mode all
```
- **Purpose**: Run complete test suite
- **Duration**: ~15 minutes
- **Includes**: Everything

### Module-Specific Testing

Test specific modules to focus on particular areas:

```bash
# Test core functions only
python run_tests.py --module core

# Test file operations
python run_tests.py --module files

# Test distributed computing
python run_tests.py --module distributed

# Test geocoding
python run_tests.py --module geo

# Test package discovery
python run_tests.py --module discovery
```

### Performance Options

```bash
# Parallel execution (requires pytest-xdist)
python run_tests.py --mode smoke --parallel

# Verbose output for debugging
python run_tests.py --mode smoke --verbose

# Install dependencies automatically
python run_tests.py --install-deps --mode smoke
```

### 🐛 Expected Test Results

The tests are **designed to find issues**. Here's what to expect:

#### ✅ **Should Pass**
- Package discovery and import mechanisms
- Basic string manipulation
- File hashing operations
- Path creation and management
- Geocoding (if geopy is installed)

#### ❌ **Known Issues** (Will Fail)
1. **File Operations**:
   - `count_total_rows_in_file_pythonically()` - **BUG**: Uses filename in loop instead of file handle
   - `count_empty_rows_in_file_pythonically()` - **BUG**: Same issue as above

2. **Shell Operations**:
   - Missing import for `io` module in `remove_empty_rows_in_file_using_sed()`
   - Undefined variables in error handling paths

3. **Distributed Computing**:
   - `move_column_to_front_of_dataframe()` - **BUG**: Returns original DataFrame instead of reordered one
   - Multiple functions use undefined variables like `RESULTS_OUTPUT_FORMAT`
   - Easter egg: `reproject_geom_columns()` prints "I LOVE LEENA" 🎉

#### ⚠️ **Conditional Tests**
- Spark utilities (require PySpark installation)
- Geocoding (requires geopy)
- Remote operations (require network access)

### Debugging Failed Tests

```bash
# Run specific test
pytest tests/test_file_operations.py::TestFileOperations::test_count_total_rows_in_file_pythonically_bug -v

# Run with debugging
pytest tests/test_file_operations.py -v -s --tb=long

# Focus on one module
pytest tests/test_core_*.py -v
```

### Test Reports

After running tests with coverage:

```bash
python run_tests.py --mode coverage
```

View reports:
- **HTML Coverage**: `htmlcov/index.html`
- **Test Report**: `reports/pytest_report.html`
- **JSON Report**: `reports/pytest_report.json`

### 💡 Testing Tips

1. **Start with Smoke Tests**: Always run smoke tests first
2. **Fix High-Impact Issues**: Focus on functions that completely fail
3. **Test After Each Fix**: Re-run tests after making changes
4. **Use Verbose Mode**: When debugging specific issues
5. **Check Dependencies**: Some tests require optional packages

**Remember**: Finding issues is **success** - it means the tests are working! 🔥

## 🧪 Testing and Development

### Running Tests

The package includes comprehensive tests for all functionality:

```bash
# Run all tests
pytest

# Run specific test modules
pytest tests/test_client_and_connection_config.py -v
pytest tests/test_core_logging.py -v
pytest tests/test_file_operations.py -v

# Run tests with coverage
pytest --cov=siege_utilities --cov-report=html

# Run tests in parallel
pytest -n auto

# Run tests and stop on first failure
pytest -x
```

### Test Structure

```
tests/
├── conftest.py                           # Shared test fixtures
├── test_client_and_connection_config.py  # Client & connection tests
├── test_core_logging.py                  # Logging system tests
├── test_file_operations.py               # File operation tests
├── test_geocoding.py                     # Geospatial tests
├── test_package_discovery.py             # Auto-discovery tests
├── test_paths.py                         # Path utility tests
├── test_remote.py                        # Remote file tests
├── test_shell.py                         # Shell command tests
├── test_spark_utils.py                   # Spark utility tests
└── test_string_utils.py                  # String utility tests
```

### Adding New Tests

To add tests for new functionality:

1. **Create test file**: `tests/test_new_feature.py`
2. **Follow naming convention**: Test classes should be named `TestFeatureName`
3. **Use descriptive test names**: `test_function_name_expected_behavior`
4. **Include edge cases**: Test error conditions and boundary cases
5. **Use fixtures**: Leverage `conftest.py` for shared test data

Example test structure:

```python
import pytest
from siege_utilities.new_feature import new_function

class TestNewFeature:
    """Test the new feature functionality."""
    
    def test_new_function_basic_usage(self):
        """Test basic functionality of new_function."""
        result = new_function("test_input")
        assert result == "expected_output"
    
    def test_new_function_with_invalid_input(self):
        """Test that new_function handles invalid input gracefully."""
        with pytest.raises(ValueError, match="Invalid input"):
            new_function("")
    
    def test_new_function_edge_case(self):
        """Test edge case behavior."""
        result = new_function(None)
        assert result is None
```

### Test Dependencies

Tests use these key dependencies:

- **pytest**: Main testing framework
- **pytest-cov**: Coverage reporting
- **pytest-xdist**: Parallel test execution
- **unittest.mock**: Mocking external dependencies

Install test dependencies:

```bash
pip install -r test_requirements.txt
```

### Continuous Integration

The package includes GitHub Actions for automated testing:

- **Python versions**: 3.8, 3.9, 3.10, 3.11, 3.12
- **Test coverage**: Minimum 90% coverage required
- **Code quality**: Flake8 and black formatting checks
- **Documentation**: Sphinx build verification

### Running Tests Locally

```bash
# Setup development environment
git clone https://github.com/siege-analytics/siege_utilities.git
cd siege_utilities
pip install -e ".[dev]"

# Run tests
pytest

# Run with specific Python version
python3.9 -m pytest

# Run tests and generate coverage report
pytest --cov=siege_utilities --cov-report=term-missing
```

### Debugging Tests

```bash
# Run single test with verbose output
pytest tests/test_client_and_connection_config.py::TestClientConfiguration::test_create_client_profile_basic -v -s

# Run tests with debugger
pytest --pdb

# Run tests and show local variables on failure
pytest --tb=short --showlocals
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

### Development Workflow

1. **Add new functions** to existing modules or create new ones
2. **Test with diagnostics**: `python3 check_imports.py`
3. **Run smoke tests**: `python run_tests.py --mode smoke`
4. **Fix any issues** found by tests
5. **Run full tests**: `python run_tests.py --mode all`
6. **Check coverage**: `python run_tests.py --mode coverage`

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Add your functions to existing modules or create new ones
4. **Run tests**: `python run_tests.py --mode smoke`
5. Test with: `python3 check_imports.py`
6. Commit changes: `git commit -am 'Add new feature'`
7. Push: `git push origin feature-name`
8. Submit a Pull Request

The auto-discovery system will automatically find and integrate your new functions!

## 📝 License

MIT License - see LICENSE file for details.

## 🙏 Acknowledgments

- Built by [Siege Analytics](https://github.com/siege-analytics)
- Inspired by the need for truly seamless Python utilities
- Special thanks to the auto-discovery pattern that makes this possible

---

**Siege Utilities**:Spatial Intelligence, In Python! 🚀

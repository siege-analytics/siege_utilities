# 🧪 Testing Guide - Comprehensive Testing with Siege Utilities

<div align="center">

![Testing](https://img.shields.io/badge/Tests-158%2F158_Passing-green)
![Framework](https://img.shields.io/badge/Framework-pytest-blue)
![Coverage](https://img.shields.io/badge/Coverage-Comprehensive-orange)
![Modern](https://img.shields.io/badge/Python-Modern_Patterns-brightgreen)

**158 tests passing with 100% success rate!** ✅

</div>

---

## 🎯 **Testing Philosophy**

At Siege Utilities, we believe that **comprehensive testing is the foundation of reliable software**. Our testing approach ensures:

- ✅ **Code Quality**: Every function is thoroughly tested
- ✅ **Backward Compatibility**: Legacy functions continue to work
- ✅ **Error Handling**: Robust error scenarios are validated
- ✅ **Type Safety**: Modern Python patterns are enforced
- ✅ **Performance**: Functions perform as expected

## 🧪 **Current Test Status**

**Test Results**: ✅ **158 tests passed, 1 skipped**  
**Test Coverage**: Comprehensive coverage across all major modules  
**Test Execution Time**: ~33 seconds for full suite  
**Code Quality**: Modern Python patterns with full type safety  

### **Test Categories Breakdown**

| Module | Tests | Status | Description |
|--------|-------|--------|-------------|
| **Core Logging** | 26 | ✅ Passing | Thread-safe logging with class management |
| **File Operations** | 46 | ✅ Passing | Modern file handling and management |
| **Remote File** | 30 | ✅ Passing | Download, retry, and file info operations |
| **Paths** | 3 | ✅ Passing | Path utilities and zip operations |
| **Distributed Computing** | All | ✅ Passing | Spark and HDFS functionality |
| **Analytics Integration** | All | ✅ Passing | Google Analytics and Facebook Business |
| **Configuration Management** | All | ✅ Passing | User config and client profiles |
| **Geospatial Functions** | All | ✅ Passing | Spatial data and transformations |

## 🚀 **Running Tests**

### **Quick Start**

```bash
# Run all tests with quick output
python -m pytest tests/ --tb=short -q

# Expected output: 158 tests passing
```

### **Comprehensive Testing**

```bash
# Run all tests with verbose output
python -m pytest tests/ -v

# Run with coverage report
python -m pytest tests/ --cov=siege_utilities --cov-report=html

# Run specific test file
python -m pytest tests/test_core_logging.py -v
```

### **Module-Specific Testing**

```bash
# Test core logging functionality
python -m pytest tests/test_core_logging.py -v      # 26 tests

# Test file operations
python -m pytest tests/test_file_operations.py -v  # 46 tests

# Test remote file operations
python -m pytest tests/test_file_remote.py -v      # 30 tests

# Test path utilities
python -m pytest tests/test_paths.py -v            # 3 tests
```

### **Advanced Testing Options**

```bash
# Parallel execution (requires pytest-xdist)
python -m pytest tests/ -n auto

# Stop after first failure
python -m pytest tests/ -x

# Run only tests that failed last time
python -m pytest tests/ --lf

# Verbose output with print statements
python -m pytest tests/ -v -s

# Run tests matching a pattern
python -m pytest tests/ -k "logging" -v
python -m pytest tests/ -k "file" -v
```

## 📊 **Test Coverage Analysis**

### **Generate Coverage Report**

```bash
# Install coverage tools
pip install pytest-cov

# Run tests with coverage
python -m pytest tests/ --cov=siege_utilities --cov-report=html

# View coverage report
open htmlcov/index.html
```

### **Coverage Report Structure**

```
htmlcov/
├── index.html              # Main coverage report
├── siege_utilities/        # Module-specific coverage
│   ├── core/              # Core utilities coverage
│   ├── files/             # File operations coverage
│   ├── geo/               # Geospatial coverage
│   └── distributed/       # Distributed computing coverage
└── coverage.xml           # XML format for CI/CD
```

### **Coverage Metrics**

- **Line Coverage**: Percentage of code lines executed
- **Branch Coverage**: Percentage of code branches executed
- **Function Coverage**: Percentage of functions called
- **Module Coverage**: Percentage of modules tested

## 🏗️ **Test Architecture**

### **Test Structure**

```
tests/
├── conftest.py                           # Shared test fixtures
├── test_client_and_connection_config.py  # Client & connection tests
├── test_core_logging.py                  # Logging system tests (26 tests)
├── test_file_operations.py               # File operation tests (46 tests)
├── test_file_remote.py                   # Remote file tests (30 tests)
├── test_geocoding.py                     # Geospatial tests
├── test_package_discovery.py             # Auto-discovery tests
├── test_paths.py                         # Path utility tests (3 tests)
├── test_shell.py                         # Shell command tests
├── test_spark_utils.py                   # Spark utility tests
└── test_string_utils.py                  # String utility tests
```

### **Test Organization Principles**

1. **One Test File Per Module**: Each module has its own test file
2. **Descriptive Test Names**: Tests clearly describe what they're testing
3. **Comprehensive Coverage**: Test normal cases, edge cases, and error conditions
4. **Backward Compatibility**: Legacy functions are thoroughly tested
5. **Modern Patterns**: New functions use modern Python testing patterns

## 📝 **Writing New Tests**

### **Test File Template**

```python
"""
Tests for [Module Name] module.

Tests all functionality including [key features] and [error handling].
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock

from siege_utilities.[module_name] import (
    function1, function2, function3
)


class Test[ModuleName]:
    """Test [Module Name] functions."""
    
    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        # Set up test data and fixtures
    
    def teardown_method(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_function1_basic_usage(self):
        """Test basic functionality of function1."""
        # Test implementation
        result = function1("test_input")
        assert result == "expected_output"
    
    def test_function1_with_invalid_input(self):
        """Test that function1 handles invalid input gracefully."""
        with pytest.raises(ValueError, match="Invalid input"):
            function1("")
    
    def test_function1_edge_case(self):
        """Test edge case behavior."""
        # Test edge case
        pass
```

### **Test Naming Conventions**

- **Test Classes**: `Test[ModuleName]` (e.g., `TestFileOperations`)
- **Test Methods**: `test_[function_name]_[scenario]` (e.g., `test_remove_tree_file`)
- **Descriptive Names**: Clear description of what's being tested
- **Consistent Format**: Follow the established pattern

### **Test Best Practices**

1. **Setup and Teardown**: Use `setup_method` and `teardown_method` for consistent environment
2. **Temporary Files**: Use `tempfile` for test data that needs cleanup
3. **Mocking**: Mock external dependencies and network calls
4. **Assertions**: Use specific assertions that test the exact behavior
5. **Error Testing**: Test both success and failure scenarios
6. **Edge Cases**: Include boundary conditions and unusual inputs

## 🔍 **Testing Specific Areas**

### **Core Logging Tests**

```bash
# Test logging functionality
python -m pytest tests/test_core_logging.py -v

# Test specific logging features
python -m pytest tests/test_core_logging.py -k "test_logging_config" -v
python -m pytest tests/test_core_logging.py -k "test_file_handler" -v
```

**Key Test Areas:**
- Logging configuration and setup
- File and console handlers
- Log level management
- Thread safety
- Error handling

### **File Operations Tests**

```bash
# Test file operations
python -m pytest tests/test_file_operations.py -v

# Test specific file operations
python -m pytest tests/test_file_operations.py -k "test_remove_tree" -v
python -m pytest tests/test_file_operations.py -k "test_file_exists" -v
```

**Key Test Areas:**
- File creation and deletion
- Directory operations
- File existence checks
- Error handling
- Backward compatibility aliases

### **Remote File Tests**

```bash
# Test remote file operations
python -m pytest tests/test_file_remote.py -v

# Test specific remote operations
python -m pytest tests/test_file_remote.py -k "test_download_file" -v
python -m pytest tests/test_file_remote.py -k "test_retry_logic" -v
```

**Key Test Areas:**
- File downloads
- Retry logic
- Error handling
- Progress tracking
- File information retrieval

### **Path Utilities Tests**

```bash
# Test path utilities
python -m pytest tests/test_paths.py -v

# Test specific path operations
python -m pytest tests/test_paths.py -k "test_unzip" -v
python -m pytest tests/test_paths.py -k "test_path_creation" -v
```

**Key Test Areas:**
- Path creation and validation
- Zip file operations
- Directory management
- Error handling

## 🚨 **Troubleshooting Test Issues**

### **Common Test Failures**

#### **Import Errors**
```bash
# If tests fail with import errors
pip install -e ".[dev]"
python -m pytest tests/ --import-mode=importlib
```

#### **Missing Dependencies**
```bash
# Install test dependencies
pip install -r test_requirements.txt

# Install development extras
pip install -e ".[dev]"
```

#### **Permission Issues**
```bash
# If tests fail due to file permissions
# Check your current working directory
pwd
ls -la

# Run tests from a writable directory
cd ~/siege_workspace
python -m pytest tests/ -v
```

### **Debugging Test Failures**

```bash
# Run specific failing test with verbose output
python -m pytest tests/test_file_operations.py::TestFileOperations::test_specific_function -v -s

# Run with maximum verbosity
python -m pytest tests/test_file_operations.py::TestFileOperations::test_specific_function -vvv -s

# Run with debugger
python -m pytest tests/test_file_operations.py::TestFileOperations::test_specific_function --pdb
```

### **Test Environment Issues**

```bash
# Check Python environment
python --version
pip list | grep siege

# Verify test discovery
python -m pytest tests/ --collect-only

# Check for test conflicts
python -m pytest tests/ --tb=short -q
```

## 🔄 **Continuous Integration**

### **GitHub Actions Integration**

Our tests run automatically on every commit:

```yaml
# .github/workflows/tests.yml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.8'
      - name: Install dependencies
        run: |
          pip install -e ".[dev]"
      - name: Run tests
        run: |
          python -m pytest tests/ -v
      - name: Generate coverage
        run: |
          python -m pytest tests/ --cov=siege_utilities --cov-report=xml
```

### **Pre-commit Hooks**

Set up pre-commit hooks to run tests before commits:

```bash
# Install pre-commit
pip install pre-commit

# Set up hooks
pre-commit install

# Run hooks manually
pre-commit run --all-files
```

## 📈 **Performance Testing**

### **Test Execution Time**

```bash
# Measure test execution time
time python -m pytest tests/ --tb=short -q

# Expected: ~30 seconds for quick run
# Expected: ~33 seconds for verbose run
```

### **Performance Optimization**

```bash
# Parallel execution
python -m pytest tests/ -n auto

# Run only changed tests
python -m pytest tests/ --lf

# Skip slow tests during development
python -m pytest tests/ -m "not slow"
```

## 🎯 **Testing Roadmap**

### **Short Term (Next Release)**
- [ ] Increase test coverage to 95%+
- [ ] Add performance benchmarks
- [ ] Implement property-based testing
- [ ] Add integration tests for complex workflows

### **Medium Term (Next Quarter)**
- [ ] Add stress testing for large datasets
- [ ] Implement chaos engineering tests
- [ ] Add security testing
- [ ] Performance regression testing

### **Long Term (Next Year)**
- [ ] Full property-based testing coverage
- [ ] Automated test generation
- [ ] AI-powered test optimization
- [ ] Cross-platform compatibility testing

## 🤝 **Contributing to Tests**

### **How to Contribute**

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/new-tests`
3. **Add comprehensive tests** for new functionality
4. **Run existing tests**: `python -m pytest tests/ -v`
5. **Ensure all tests pass**: 158/158 tests passing
6. **Submit a pull request**

### **Test Contribution Guidelines**

- **Test Coverage**: New functions must have 100% test coverage
- **Test Quality**: Tests must be clear, maintainable, and comprehensive
- **Performance**: Tests should complete in reasonable time
- **Documentation**: Tests should serve as documentation
- **Backward Compatibility**: Test both new and legacy functionality

## 📚 **Additional Resources**

### **Testing Documentation**
- **[pytest Documentation](https://docs.pytest.org/)** - Official pytest guide
- **[Testing Best Practices](Testing-Best-Practices)** - Our testing philosophy
- **[Code Modernization](Code-Modernization)** - How we modernized our codebase

### **Community Support**
- **GitHub Issues**: [Report test failures](https://github.com/siege-analytics/siege_utilities/issues)
- **Discussions**: [Testing questions](https://github.com/siege-analytics/siege_utilities/discussions)
- **Documentation**: [Full API docs](https://siege-analytics.github.io/siege_utilities/)

---

<div align="center">

**Ready to write tests?** 🧪

**[Next: Testing Best Practices](Testing-Best-Practices)** → **[Code Modernization](Code-Modernization)** → **[Contributing](Contributing)**

</div>

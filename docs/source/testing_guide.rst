Testing Guide
============

This guide covers testing the Siege Utilities package, including running tests, writing new tests, and understanding the test architecture.

.. contents::
   :local:

Overview
--------

Siege Utilities includes a comprehensive test suite covering all functionality:

- **Unit Tests**: Fast, isolated tests for individual functions
- **Integration Tests**: Tests that verify module interactions
- **Configuration Tests**: Client and connection management tests
- **Performance Tests**: Tests for distributed computing features

Test Structure
--------------

The test suite is organized as follows:

.. code-block:: text

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

Running Tests
-------------

Basic Test Execution
~~~~~~~~~~~~~~~~~~~

Run all tests:

.. code-block:: bash

   pytest

Run with verbose output:

.. code-block:: bash

   pytest -v

Run specific test modules:

.. code-block:: bash

   pytest tests/test_client_and_connection_config.py -v
   pytest tests/test_core_logging.py -v
   pytest tests/test_file_operations.py -v

Test Runner Script
~~~~~~~~~~~~~~~~~

Use the interactive test runner:

.. code-block:: bash

   python run_tests.py

Or run specific test types:

.. code-block:: bash

   python run_tests.py --coverage    # With coverage reporting
   python run_tests.py --fast        # Fast tests only
   python run_tests.py --parallel    # Parallel execution
   python run_tests.py --debug       # Debug mode

Coverage and Reporting
~~~~~~~~~~~~~~~~~~~~~~

Generate coverage reports:

.. code-block:: bash

   pytest --cov=siege_utilities --cov-report=html
   pytest --cov=siege_utilities --cov-report=term-missing

View coverage in browser:

.. code-block:: bash

   open htmlcov/index.html
   # or
   xdg-open htmlcov/index.html  # Linux
   start htmlcov/index.html      # Windows

Parallel Execution
~~~~~~~~~~~~~~~~~

Run tests in parallel for faster execution:

.. code-block:: bash

   pytest -n auto  # Auto-detect CPU cores
   pytest -n 4     # Use 4 processes

Test Markers
------------

Tests are categorized using pytest markers:

.. code-block:: python

   import pytest

   @pytest.mark.unit
   def test_basic_functionality():
       """Fast unit test."""
       pass

   @pytest.mark.integration
   def test_module_integration():
       """Slower integration test."""
       pass

   @pytest.mark.slow
   def test_performance():
       """Slow performance test."""
       pass

   @pytest.mark.client
   def test_client_profile():
       """Client configuration test."""
       pass

   @pytest.mark.connection
   def test_connection_management():
       """Connection management test."""
       pass

Run tests by marker:

.. code-block:: bash

   pytest -m unit              # Only unit tests
   pytest -m "not slow"        # Exclude slow tests
   pytest -m "client or connection"  # Client or connection tests

Writing New Tests
----------------

Test File Structure
~~~~~~~~~~~~~~~~~~

Create new test files following this pattern:

.. code-block:: python

   """
   Tests for new_feature module.
   """

   import pytest
   from siege_utilities.new_feature import new_function

   class TestNewFeature:
       """Test the new feature functionality."""
       
       def test_new_function_basic_usage(self):
           """Test basic functionality."""
           result = new_function("test_input")
           assert result == "expected_output"
       
       def test_new_function_with_invalid_input(self):
           """Test error handling."""
           with pytest.raises(ValueError, match="Invalid input"):
               new_function("")
       
       def test_new_function_edge_case(self):
           """Test edge case behavior."""
           result = new_function(None)
           assert result is None

Test Naming Conventions
~~~~~~~~~~~~~~~~~~~~~~~

- **Test files**: `test_module_name.py`
- **Test classes**: `TestClassName`
- **Test methods**: `test_function_name_expected_behavior`
- **Test descriptions**: Clear, descriptive docstrings

Example Test Patterns
~~~~~~~~~~~~~~~~~~~~

Testing with fixtures:

.. code-block:: python

   import pytest
   import tempfile
   import pathlib

   @pytest.fixture
   def temp_config_dir():
       """Create temporary configuration directory."""
       with tempfile.TemporaryDirectory() as tmp_dir:
           yield pathlib.Path(tmp_dir)

   def test_save_configuration(temp_config_dir):
       """Test saving configuration to temporary directory."""
       config = {"key": "value"}
       result = save_config(config, str(temp_config_dir))
       assert result.exists()

Testing error conditions:

.. code-block:: python

   def test_function_handles_missing_file():
       """Test that function handles missing files gracefully."""
       with pytest.raises(FileNotFoundError):
           process_file("nonexistent_file.txt")

Testing with mocks:

.. code-block:: python

   from unittest.mock import patch, MagicMock

   @patch('requests.get')
   def test_api_call_success(mock_get):
       """Test successful API call."""
       mock_response = MagicMock()
       mock_response.status_code = 200
       mock_response.json.return_value = {"data": "test"}
       mock_get.return_value = mock_response
       
       result = make_api_call("http://test.com")
       assert result["data"] == "test"

Test Fixtures
------------

Shared test fixtures are defined in `tests/conftest.py`:

.. code-block:: python

   import pytest
   import tempfile
   import pathlib

   @pytest.fixture(scope="session")
   def sample_data():
       """Sample data for testing."""
       return {
           "numbers": [1, 2, 3, 4, 5],
           "strings": ["hello", "world"],
           "nested": {"key": "value"}
       }

   @pytest.fixture
   def temp_workspace():
       """Temporary workspace for file operations."""
       with tempfile.TemporaryDirectory() as tmp_dir:
           workspace = pathlib.Path(tmp_dir)
           # Create some test files
           (workspace / "test.txt").write_text("test content")
           (workspace / "data.csv").write_text("col1,col2\n1,2\n3,4")
           yield workspace

Using fixtures in tests:

.. code-block:: python

   def test_process_data(sample_data, temp_workspace):
       """Test data processing with fixtures."""
       result = process_data(sample_data, temp_workspace)
       assert result.success
       assert (temp_workspace / "output.txt").exists()

Test Configuration
-----------------

Pytest Configuration
~~~~~~~~~~~~~~~~~~~

The package includes `pytest.ini` with optimized settings:

.. code-block:: ini

   [tool:pytest]
   testpaths = tests
   python_files = test_*.py
   python_classes = Test*
   python_functions = test_*
   addopts = 
       -v
       --tb=short
       --strict-markers
       --disable-warnings
       --cov=siege_utilities
       --cov-report=term-missing
       --cov-report=html:htmlcov
       --cov-fail-under=85

Coverage Configuration
~~~~~~~~~~~~~~~~~~~~~

Coverage settings in `pytest.ini`:

.. code-block:: ini

   [coverage:run]
   source = siege_utilities
   omit = 
       */tests/*
       */test_*
       setup.py
       */__init__.py

   [coverage:report]
   exclude_lines =
       pragma: no cover
       def __repr__
       if self.debug:
       raise AssertionError
       raise NotImplementedError

Continuous Integration
---------------------

GitHub Actions automatically run tests on:

- **Python versions**: 3.8, 3.9, 3.10, 3.11, 3.12
- **Test coverage**: Minimum 85% coverage required
- **Code quality**: Flake8 and black formatting checks
- **Documentation**: Sphinx build verification

CI Pipeline
~~~~~~~~~~~

.. code-block:: yaml

   name: Tests
   on: [push, pull_request]
   
   jobs:
     test:
       runs-on: ubuntu-latest
       strategy:
         matrix:
           python-version: [3.8, 3.9, 3.10, 3.11, 3.12]
       
       steps:
       - uses: actions/checkout@v3
       - name: Set up Python ${{ matrix.python-version }}
         uses: actions/setup-python@v4
         with:
           python-version: ${{ matrix.python-version }}
       
       - name: Install dependencies
         run: |
           pip install -r test_requirements.txt
           pip install -e .
       
       - name: Run tests
         run: |
           pytest --cov=siege_utilities --cov-report=xml
       
       - name: Upload coverage
         uses: codecov/codecov-action@v3

Debugging Tests
--------------

Verbose Output
~~~~~~~~~~~~~

Get detailed test information:

.. code-block:: bash

   pytest -v -s                    # Verbose with print statements
   pytest --tb=long               # Full traceback
   pytest --tb=short --showlocals # Show local variables on failure

Debug Mode
~~~~~~~~~~

Run tests with debugger:

.. code-block:: bash

   pytest --pdb                   # Drop into debugger on failure
   pytest --pdbcls=IPython.terminal.debugger:Pdb  # Use IPython debugger

Single Test Execution
~~~~~~~~~~~~~~~~~~~~

Run specific tests for debugging:

.. code-block:: bash

   pytest tests/test_file.py::TestClass::test_method -v -s
   pytest tests/test_file.py::test_function -v -s

Test Isolation
~~~~~~~~~~~~~

Ensure tests don't interfere with each other:

.. code-block:: bash

   pytest --maxfail=1             # Stop on first failure
   pytest -x                      # Same as above
   pytest --lf                    # Run only failed tests from last run

Performance Testing
------------------

Benchmark Tests
~~~~~~~~~~~~~~

Measure function performance:

.. code-block:: python

   import time
   import pytest

   def test_function_performance():
       """Test that function completes within acceptable time."""
       start_time = time.time()
       
       result = expensive_function()
       
       execution_time = time.time() - start_time
       assert execution_time < 1.0  # Should complete in under 1 second
       assert result is not None

Load Testing
~~~~~~~~~~~

Test with large datasets:

.. code-block:: python

   def test_large_data_processing():
       """Test processing large datasets."""
       large_dataset = ["data"] * 10000
       
       result = process_large_dataset(large_dataset)
       
       assert len(result) == 10000
       assert all(item.processed for item in result)

Test Data Management
-------------------

Test Data Generation
~~~~~~~~~~~~~~~~~~~

Generate test data programmatically:

.. code-block:: python

   import random
   import string

   def generate_test_data(size=100):
       """Generate random test data."""
       return [
           {
               "id": i,
               "name": ''.join(random.choices(string.ascii_letters, k=10)),
               "value": random.randint(1, 1000)
           }
           for i in range(size)
       ]

   def test_data_processing():
       """Test with generated data."""
       test_data = generate_test_data(1000)
       result = process_data(test_data)
       assert len(result) == 1000

Data Cleanup
~~~~~~~~~~~

Ensure test data is cleaned up:

.. code-block:: python

   import tempfile
   import pathlib

   def test_with_cleanup():
       """Test that creates and cleans up test data."""
       temp_dir = tempfile.mkdtemp()
       try:
           # Test operations
           test_file = pathlib.Path(temp_dir) / "test.txt"
           test_file.write_text("test content")
           
           result = process_file(test_file)
           assert result.success
           
       finally:
           # Cleanup
           import shutil
           shutil.rmtree(temp_dir)

Best Practices
-------------

Test Organization
~~~~~~~~~~~~~~~~

1. **Group related tests** in test classes
2. **Use descriptive test names** that explain the expected behavior
3. **Keep tests focused** on a single piece of functionality
4. **Use fixtures** for common setup and teardown
5. **Test both success and failure cases**

Test Independence
~~~~~~~~~~~~~~~~

1. **Each test should be independent** and not rely on other tests
2. **Use fresh data** for each test
3. **Clean up resources** after tests
4. **Avoid test ordering dependencies**

Test Coverage
~~~~~~~~~~~~

1. **Aim for high coverage** (85%+ minimum)
2. **Test edge cases** and error conditions
3. **Test boundary conditions** (empty lists, None values, etc.)
4. **Test integration points** between modules

Performance Considerations
~~~~~~~~~~~~~~~~~~~~~~~~

1. **Keep unit tests fast** (< 1 second each)
2. **Use markers** to categorize slow tests
3. **Run slow tests separately** in CI
4. **Use parallel execution** for faster feedback

Common Patterns
---------------

Configuration Testing
~~~~~~~~~~~~~~~~~~~~

Test configuration management:

.. code-block:: python

   def test_config_creation():
       """Test configuration creation and validation."""
       config = create_config(
           name="test_config",
           settings={"key": "value"}
       )
       
       assert config.name == "test_config"
       assert config.settings["key"] == "value"
       assert config.is_valid()

   def test_config_validation():
       """Test configuration validation."""
       invalid_config = {"name": "", "settings": {}}
       
       with pytest.raises(ValueError, match="Name cannot be empty"):
           validate_config(invalid_config)

File Operation Testing
~~~~~~~~~~~~~~~~~~~~~

Test file operations:

.. code-block:: python

   def test_file_processing(temp_workspace):
       """Test file processing operations."""
       input_file = temp_workspace / "input.txt"
       input_file.write_text("test content")
       
       result = process_file(input_file)
       
       assert result.success
       assert (temp_workspace / "output.txt").exists()
       assert result.processed_lines == 1

API Testing
~~~~~~~~~~~

Test API interactions:

.. code-block:: python

   @patch('requests.post')
   def test_api_integration(mock_post):
       """Test API integration."""
       mock_post.return_value.status_code = 200
       mock_post.return_value.json.return_value = {"status": "success"}
       
       result = call_api("http://api.test.com", {"data": "test"})
       
       assert result["status"] == "success"
       mock_post.assert_called_once()

Troubleshooting
--------------

Common Issues
~~~~~~~~~~~~

**Import errors**: Ensure package is installed in development mode
   .. code-block:: bash

      pip install -e .

**Missing dependencies**: Install test requirements
   .. code-block:: bash

      pip install -r test_requirements.txt

**Test discovery issues**: Check test file naming and structure
   .. code-block:: bash

      pytest --collect-only

**Coverage issues**: Verify coverage configuration
   .. code-block:: bash

      pytest --cov=siege_utilities --cov-report=term

Getting Help
-----------

- **Test failures**: Check the test output and traceback
- **Coverage issues**: Review coverage reports in `htmlcov/`
- **Performance problems**: Use `pytest --durations=10` to identify slow tests
- **Documentation**: See the test files themselves for examples

Remember: **Finding issues is success** - it means the tests are working! 🔥

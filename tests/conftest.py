# ================================================================
# FILE: conftest.py
# ================================================================
"""
Shared pytest configuration and fixtures for siege-utilities tests.
"""
import pytest
import tempfile
import os
import sys
import pathlib
import shutil
from unittest.mock import Mock, patch, MagicMock
import logging

# Add the package to Python path for testing
sys.path.insert(0, os.path.abspath('.'))


@pytest.fixture
def temp_directory():
    """Create a temporary directory for file-based tests."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield pathlib.Path(temp_dir)


@pytest.fixture
def sample_file(temp_directory):
    """Create a sample file for testing."""
    content = "Hello, World!\nThis is a test file.\nLine 3\n"
    file_path = temp_directory / "sample.txt"
    file_path.write_text(content)
    return file_path


@pytest.fixture
def large_sample_file(temp_directory):
    """Create a larger sample file for testing."""
    content = "Large file content line\n" * 10000  # ~200KB
    file_path = temp_directory / "large_sample.txt"
    file_path.write_text(content)
    return file_path


@pytest.fixture
def sample_zip_file(temp_directory):
    """Create a sample ZIP file for testing."""
    import zipfile
    zip_path = temp_directory / "sample.zip"
    with zipfile.ZipFile(zip_path, 'w') as zf:
        zf.writestr("file1.txt", "Content of file 1")
        zf.writestr("dir/file2.txt", "Content of file 2")
        zf.writestr("empty_file.txt", "")
    return zip_path


@pytest.fixture
def sample_csv_file(temp_directory):
    """Create a sample CSV file for testing."""
    content = """name,age,city
John,30,New York
Jane,25,Los Angeles
Bob,35,Chicago
"""
    file_path = temp_directory / "sample.csv"
    file_path.write_text(content)
    return file_path


@pytest.fixture
def file_with_empty_lines(temp_directory):
    """Create a file with empty lines for testing."""
    content = """Line 1

Line 3


Line 6

"""
    file_path = temp_directory / "empty_lines.txt"
    file_path.write_text(content)
    return file_path


@pytest.fixture
def file_with_duplicates(temp_directory):
    """Create a file with duplicate lines for testing."""
    content = """apple
banana
apple
cherry
banana
date
apple
"""
    file_path = temp_directory / "duplicates.txt"
    file_path.write_text(content)
    return file_path


@pytest.fixture
def mock_spark_session():
    """Mock Spark session for distributed computing tests."""
    mock_spark = Mock()
    mock_spark.sparkContext.setLogLevel = Mock()
    mock_spark.read.parquet = Mock()
    mock_spark.createDataFrame = Mock()
    mock_spark.sql = Mock()
    return mock_spark


@pytest.fixture
def mock_hdfs_config():
    """Mock HDFS configuration for testing."""
    from siege_utilities.distributed.hdfs_config import HDFSConfig
    return HDFSConfig(
        data_path='/test/data',
        hdfs_base_directory='/test/hdfs/',
        cache_directory='/tmp/test_cache',
        app_name='TestApp',
        spark_log_level='WARN',
        enable_sedona=False,
        num_executors=2,
        executor_cores=1,
        executor_memory='1g'
    )


@pytest.fixture
def capture_logs():
    """Capture log output for testing."""
    import io
    import logging

    log_capture = io.StringIO()
    handler = logging.StreamHandler(log_capture)
    logger = logging.getLogger()
    old_level = logger.level
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)

    yield log_capture

    logger.removeHandler(handler)
    logger.setLevel(old_level)


@pytest.fixture
def mock_requests_response():
    """Mock requests response for testing remote operations."""
    mock_response = Mock()
    mock_response.ok = True
    mock_response.status_code = 200
    mock_response.headers = {'content-length': '1024'}
    mock_response.iter_content = Mock(return_value=[b'chunk1', b'chunk2'])
    return mock_response
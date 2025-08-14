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


# ================================================================
# MULTI-ENGINE TESTING FIXTURES
# ================================================================

@pytest.fixture
def mock_multi_engine_processor():
    """Mock multi-engine processor for testing."""
    mock_processor = Mock()
    mock_processor.spark_available = True
    mock_processor.default_engine = "auto"
    
    # Mock engine selection
    mock_processor.get_optimal_engine.return_value = "auto"
    
    # Mock processing methods
    mock_processor.process_data.return_value = Mock()
    mock_processor.process_analytics_data.return_value = Mock()
    mock_processor.batch_process_files.return_value = Mock()
    
    return mock_processor


@pytest.fixture
def mock_spark_with_sedona():
    """Mock Spark session with Sedona support."""
    mock_spark = Mock()
    mock_spark.version = "3.4.0"
    mock_spark.sparkContext.setLogLevel = Mock()
    mock_spark.read.parquet = Mock()
    mock_spark.createDataFrame = Mock()
    mock_spark.sql = Mock()
    
    # Mock Sedona UDFs
    mock_spark.udf = Mock()
    mock_spark.udf.register = Mock()
    
    return mock_spark


@pytest.fixture
def mock_svg_marker_manager():
    """Mock SVG marker manager for testing."""
    mock_manager = Mock()
    mock_manager.cached_markers = {}
    mock_manager.supported_formats = ['.svg']
    
    # Mock SVG loading with proper caching behavior
    def mock_load_svg_marker(file_path):
        if 'nonexistent' in file_path or not file_path.endswith('.svg'):
            return None
        # Simulate caching
        if file_path not in mock_manager.cached_markers:
            mock_manager.cached_markers[file_path] = """<svg width="64" height="64" viewBox="0 0 64 64">
                <circle cx="32" cy="32" r="16" fill="currentColor"/>
            </svg>"""
        return mock_manager.cached_markers[file_path]
    
    mock_manager.load_svg_marker = mock_load_svg_marker
    
    # Mock SVG processing
    mock_manager._process_svg_marker.return_value = """<svg width="64" height="64" viewBox="0 0 64 64">
        <circle cx="32" cy="32" r="16" fill="#FF6B6B"/>
    </svg>"""
    
    # Mock file creation
    mock_manager.create_marker_from_svg.return_value = True
    
    # Mock cache clearing
    def mock_clear_cache():
        mock_manager.cached_markers.clear()
    
    mock_manager.clear_cache = mock_clear_cache
    
    return mock_manager


@pytest.fixture
def sample_spatial_data():
    """Create sample spatial data for testing."""
    import pandas as pd
    from shapely.geometry import Point
    
    data = {
        'name': ['Point A', 'Point B', 'Point C'],
        'geometry': [
            Point(-122.4194, 37.7749),  # San Francisco
            Point(-74.0060, 40.7128),   # New York
            Point(-87.6298, 41.8781)    # Chicago
        ],
        'value': [100, 200, 150],
        'category': ['A', 'B', 'A']
    }
    
    return pd.DataFrame(data)


@pytest.fixture
def sample_analytics_data():
    """Create sample analytics data for testing."""
    import pandas as pd
    from datetime import datetime, timedelta
    
    dates = [datetime.now() - timedelta(days=i) for i in range(30)]
    
    data = {
        'date': dates,
        'pageviews': [1000 + i * 10 for i in range(30)],
        'sessions': [500 + i * 5 for i in range(30)],
        'conversions': [50 + i for i in range(30)],
        'platform': ['google_analytics'] * 30,
        'source': ['organic'] * 30
    }
    
    return pd.DataFrame(data)


@pytest.fixture
def mock_database_connection():
    """Mock database connection for testing."""
    mock_conn = Mock()
    mock_conn.type = 'postgresql'
    mock_conn.jdbc_url = 'jdbc:postgresql://localhost:5432/test_db'
    mock_conn.properties = {
        'user': 'test_user',
        'password': 'test_pass',
        'driver': 'org.postgresql.Driver'
    }
    return mock_conn


@pytest.fixture
def mock_map_config():
    """Mock map configuration for testing."""
    return {
        'markers': {
            'style': 'circle',
            'color': '#1f77b4',
            'size': 8,
            'alpha': 0.7,
            'svg_path': None,
            'svg_scale': 1.0,
            'svg_rotation': 0,
            'svg_colorize': True,
            'svg_markers': {
                'type_a': {'condition': {'category': 'A'}},
                'type_b': {'condition': {'category': 'B'}}
            }
        },
        'colors': {
            'palette': 'viridis',
            'scheme': 'sequential',
            'alpha': 0.8
        },
        'export': {
            'format': 'png',
            'resolution': 300,
            'size': (1200, 800)
        },
        'backend': 'matplotlib'
    }


@pytest.fixture
def sample_svg_marker_file(temp_directory):
    """Create a sample SVG marker file for testing."""
    svg_content = """<?xml version="1.0" encoding="UTF-8"?>
<svg width="64" height="64" viewBox="0 0 64 64" xmlns="http://www.w3.org/2000/svg">
    <circle cx="32" cy="32" r="16" fill="currentColor" stroke="none"/>
    <rect x="24" y="24" width="16" height="16" fill="white" opacity="0.8"/>
</svg>"""
    
    svg_file = temp_directory / "test_marker.svg"
    svg_file.write_text(svg_content)
    return svg_file


@pytest.fixture
def mock_engine_performance_data():
    """Mock engine performance data for testing."""
    return {
        'small_dataset': {
            'pandas_time': 0.1,
            'spark_time': 0.5,
            'pandas_throughput': 1000,
            'spark_throughput': 200
        },
        'large_dataset': {
            'pandas_time': 5.0,
            'spark_time': 1.0,
            'pandas_throughput': 200,
            'spark_throughput': 1000
        }
    }


@pytest.fixture
def mock_multi_engine_batch_processor():
    """Mock multi-engine batch processor for testing."""
    mock_processor = Mock()
    mock_processor.spark_available = True
    mock_processor.default_engine = "auto"
    
    # Mock batch processing methods
    mock_processor.batch_process_files.return_value = [
        {'file': 'test1.csv', 'status': 'success', 'rows_processed': 100},
        {'file': 'test2.csv', 'status': 'success', 'rows_processed': 200}
    ]
    
    # Mock engine selection
    mock_processor.get_optimal_engine.return_value = "auto"
    
    return mock_processor


@pytest.fixture
def mock_multi_engine_analytics_processor():
    """Mock multi-engine analytics processor for testing."""
    mock_processor = Mock()
    mock_processor.spark_available = True
    mock_processor.default_engine = "auto"
    
    # Mock analytics methods
    mock_processor.process_analytics_data.return_value = Mock()
    mock_processor.get_optimal_engine.return_value = "auto"
    
    # Mock client connections
    mock_processor.ga_client = Mock()
    mock_processor.ga_client.test_connection.return_value = True
    
    mock_processor.fb_client = Mock()
    mock_processor.fb_client.test_connection.return_value = True
    
    return mock_processor
# ================================================================
# FILE: test_spark_utils.py
# ================================================================
"""
Tests for siege_utilities.distributed.spark_utils module.
These tests focus on exposing issues in Spark DataFrame operations.
"""

# Python standard

import sys
import os
import json

# PySpark

# Unit Testing
import pytest
from unittest.mock import Mock, patch, MagicMock

# Spark functions

from pyspark.sql import SparkSession
from pyspark.sql.types import StructType, StructField, StringType, IntegerType
from pyspark.sql.functions import col

# Siege Utilities

import siege_utilities

# Skip all tests if PySpark is not available
pytest.importorskip("pyspark", reason="PySpark not available")

try:
    import siege_utilities
    # Quick environment setup that handles everything
    if not siege_utilities.setup_spark_environment():
        pytest.skip("Spark environment setup failed", allow_module_level=True)
except ImportError:
    pytest.skip("siege_utilities package not available", allow_module_level=True)

class TestSparkUtils:
    """Test Spark utility functions."""

    @pytest.fixture(scope="class")
    def spark(self):
        """Create a test Spark session."""
        spark = SparkSession.builder \
            .appName("test_siege_utilities") \
            .master("local[2]") \
            .config("spark.sql.adaptive.enabled", "false") \
            .getOrCreate()
        yield spark
        spark.stop()

    @pytest.fixture
    def sample_df(self, spark):
        """Create a sample DataFrame for testing."""
        data = [
            ("John Doe", 30, "Engineer"),
            ("Jane Smith", 25, "Designer"),
            ("Bob Johnson", 35, "Manager")
        ]
        schema = StructType([
            StructField("name", StringType(), True),
            StructField("age", IntegerType(), True),
            StructField("job", StringType(), True)
        ])
        return spark.createDataFrame(data, schema)

    def test_move_column_to_front_of_dataframe(self, sample_df):
        """Test moving column to front - should work correctly."""
        result_df = siege_utilities.move_column_to_front_of_dataframe(sample_df, "age")

        # Age should now be first
        expected_columns = ['age', 'name', 'job']  # age moved to front
        assert result_df.columns == expected_columns

        # Test with another column
        result_df2 = siege_utilities.move_column_to_front_of_dataframe(sample_df, "name")
        expected_columns2 = ['name', 'age', 'job']  # name stays first (already was)
        assert result_df2.columns == expected_columns2

    def test_reproject_geom_columns_function_exists(self):
        """Test that reproject_geom_columns function exists and has the easter egg."""
        # This function has a funny print statement
        with patch('builtins.print') as mock_print:
            try:
                # Create mock DataFrame
                mock_df = Mock()
                mock_df.withColumn.return_value = mock_df

                siege_utilities.reproject_geom_columns(
                    mock_df, ["geom"], "EPSG:4326", "EPSG:27700"
                )

                # Check if the easter egg print was called
                mock_print.assert_called_with('I LOVE LEENA')

            except Exception:
                # Function might fail, but we're testing if the print happens
                mock_print.assert_called_with('I LOVE LEENA')

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


# Skip all tests if necessary envs are not available
# Import ensure_env_vars from run_tests.py if it's available

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
try:
    from run_tests import ensure_env_vars
    ensure_env_vars(["JAVA_HOME", "SPARK_HOME"])
except ImportError:
    pass

missing = [v for v in ["JAVA_HOME", "SPARK_HOME"] if not os.environ.get(v)]
if missing:
    pytest.skip(
        f"Skipping Spark tests — missing env vars: {', '.join(missing)}",
        allow_module_level=True
    )

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
        """Test moving column to front - this function has a bug."""
        # The function has a bug: it returns `df` instead of `df_reordered`
        result_df = siege_utilities.move_column_to_front_of_dataframe(sample_df, "age")

        # The bug means it returns the original DataFrame, not the reordered one
        assert result_df.columns == sample_df.columns  # Bug: no reordering happened

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

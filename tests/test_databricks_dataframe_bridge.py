"""Tests for dataframe bridge helpers."""

import pandas as pd
import pytest

from siege_utilities.databricks.dataframe_bridge import (
    _validate_geometry_format,
    pandas_to_spark,
    spark_to_pandas,
)


def test_pandas_to_spark_uses_create_dataframe():
    """Pandas conversion should call Spark createDataFrame."""
    called = {"value": None}

    class SparkStub:
        def createDataFrame(self, dataframe):
            called["value"] = dataframe
            return "SPARK_DF"

    pandas_df = pd.DataFrame({"id": [1, 2], "name": ["a", "b"]})
    output = pandas_to_spark(pandas_df, spark=SparkStub())
    assert output == "SPARK_DF"
    assert called["value"].equals(pandas_df)


def test_spark_to_pandas_with_limit():
    """Spark conversion should support optional row limit."""
    expected = pd.DataFrame({"id": [1]})

    class LimitedSparkDf:
        def toPandas(self):
            return expected

    class SparkDf:
        def limit(self, value):
            assert value == 1
            return LimitedSparkDf()

    output = spark_to_pandas(SparkDf(), limit=1)
    assert output.equals(expected)


def test_validate_geometry_format():
    """Geometry format validator should accept supported formats."""
    assert _validate_geometry_format("wkt") == "wkt"
    assert _validate_geometry_format("WKB_HEX") == "wkb_hex"

    with pytest.raises(ValueError):
        _validate_geometry_format("geojson")

"""Error-path tests for the engine-agnostic DataFrame abstraction.

Validates that invalid inputs, missing dependencies, and misconfigured
engines raise clear, specific exceptions rather than returning silent
empty results.
"""

from __future__ import annotations

import pandas as pd
import pytest

from siege_utilities.engines.dataframe_engine import (
    DataFrameEngine,
    DuckDBEngine,
    Engine,
    PandasEngine,
    PostGISEngine,
    SparkEngine,
    _validate_agg_names,
    get_engine,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sample_df() -> pd.DataFrame:
    return pd.DataFrame(
        {"name": ["alice", "bob", "charlie"], "value": [10, 20, 30], "group": ["a", "a", "b"]}
    )


# ---------------------------------------------------------------------------
# get_engine — invalid engine names
# ---------------------------------------------------------------------------

class TestGetEngineInvalidName:
    def test_invalid_engine_name_raises(self):
        with pytest.raises(ValueError, match="Unknown engine"):
            get_engine("nonexistent")

    def test_invalid_engine_name_empty_raises(self):
        with pytest.raises(ValueError, match="Unknown engine"):
            get_engine("")

    def test_invalid_engine_name_numeric_raises(self):
        with pytest.raises((ValueError, AttributeError, KeyError)):
            get_engine(42)  # type: ignore[arg-type]

    def test_invalid_engine_name_none_raises(self):
        with pytest.raises((ValueError, AttributeError, KeyError)):
            get_engine(None)  # type: ignore[arg-type]

    def test_invalid_engine_case_sensitivity_raises(self):
        """Engine names that don't match after lowering should fail."""
        with pytest.raises(ValueError, match="Unknown engine"):
            get_engine("NONEXISTENT")


# ---------------------------------------------------------------------------
# _validate_agg_names — shared aggregation validation
# ---------------------------------------------------------------------------

class TestValidateAggNamesErrors:
    def test_empty_agg_dict_raises(self):
        with pytest.raises(ValueError, match="must not be empty"):
            _validate_agg_names({}, "TestEngine")

    def test_invalid_agg_function_raises(self):
        with pytest.raises(ValueError, match="unsupported aggregation"):
            _validate_agg_names({"col": "bogus"}, "TestEngine")

    def test_invalid_agg_multiple_raises(self):
        with pytest.raises(ValueError, match="unsupported aggregation"):
            _validate_agg_names({"a": "sum", "b": "median"}, "TestEngine")

    def test_invalid_agg_function_name_in_error_message(self):
        with pytest.raises(ValueError, match="median"):
            _validate_agg_names({"col": "median"}, "TestEngine")


# ---------------------------------------------------------------------------
# ABC — cannot instantiate
# ---------------------------------------------------------------------------

class TestABCErrors:
    def test_cannot_instantiate_abc_raises(self):
        with pytest.raises(TypeError):
            DataFrameEngine()  # type: ignore[abstract]


# ---------------------------------------------------------------------------
# PandasEngine error paths
# ---------------------------------------------------------------------------

class TestPandasEngineErrors:
    @pytest.fixture
    def engine(self):
        return PandasEngine()

    def test_query_missing_connection_raises(self, engine):
        with pytest.raises(ValueError, match="connection"):
            engine.query("SELECT 1")

    def test_groupby_empty_agg_dict_raises(self, engine):
        df = _sample_df()
        with pytest.raises(ValueError, match="must not be empty"):
            engine.groupby_agg(df, ["group"], {})

    def test_groupby_invalid_agg_name_raises(self, engine):
        df = _sample_df()
        with pytest.raises(ValueError, match="unsupported aggregation"):
            engine.groupby_agg(df, ["group"], {"value": "mode"})

    def test_to_geodataframe_missing_geometry_col_raises(self, engine):
        df = _sample_df()
        with pytest.raises(ValueError, match="geometry.*not found"):
            engine.to_geodataframe(df, geometry_col="geometry")

    def test_to_geodataframe_custom_col_missing_raises(self, engine):
        df = _sample_df()
        with pytest.raises(ValueError, match="geom.*not found"):
            engine.to_geodataframe(df, geometry_col="geom")

    def test_read_csv_nonexistent_file_raises(self, engine, tmp_path):
        with pytest.raises(FileNotFoundError):
            engine.read_csv(str(tmp_path / "does_not_exist.csv"))

    def test_read_parquet_nonexistent_file_raises(self, engine, tmp_path):
        with pytest.raises((FileNotFoundError, OSError)):
            engine.read_parquet(str(tmp_path / "does_not_exist.parquet"))


# ---------------------------------------------------------------------------
# DuckDBEngine error paths
# ---------------------------------------------------------------------------

duckdb = pytest.importorskip("duckdb")


class TestDuckDBEngineErrors:
    @pytest.fixture
    def engine(self):
        return DuckDBEngine()

    def test_groupby_empty_agg_dict_raises(self, engine):
        df = _sample_df()
        with pytest.raises(ValueError, match="must not be empty"):
            engine.groupby_agg(df, ["group"], {})

    def test_groupby_invalid_agg_name_raises(self, engine):
        df = _sample_df()
        with pytest.raises(ValueError, match="unsupported aggregation"):
            engine.groupby_agg(df, ["group"], {"value": "mode"})

    def test_groupby_non_dataframe_raises(self, engine):
        with pytest.raises(TypeError, match="expects a pandas DataFrame"):
            engine.groupby_agg("not a dataframe", ["group"], {"value": "sum"})

    def test_filter_non_dataframe_raises(self, engine):
        with pytest.raises(TypeError, match="expects a pandas DataFrame"):
            engine.filter("not a dataframe", "some_condition")

    def test_join_non_dataframe_raises(self, engine):
        with pytest.raises(TypeError, match="expects pandas DataFrames"):
            engine.join("not a df", "also not a df", on="id")

    def test_read_csv_with_kwargs_raises(self, engine, tmp_path):
        csv_path = tmp_path / "test.csv"
        csv_path.write_text("a,b\n1,2\n")
        with pytest.raises(NotImplementedError, match="does not yet forward kwargs"):
            engine.read_csv(str(csv_path), header=True)

    def test_read_parquet_with_kwargs_raises(self, engine, tmp_path):
        with pytest.raises(NotImplementedError, match="does not yet forward kwargs"):
            engine.read_parquet("/fake/path.parquet", columns=["a"])

    def test_to_geodataframe_missing_col_raises(self, engine):
        df = _sample_df()
        with pytest.raises(ValueError, match="geometry.*not found"):
            engine.to_geodataframe(df, geometry_col="geometry")

    def test_read_csv_nonexistent_file_raises(self, engine, tmp_path):
        with pytest.raises(Exception):
            engine.read_csv(str(tmp_path / "does_not_exist.csv"))


# ---------------------------------------------------------------------------
# SparkEngine — import guard only (no actual Spark)
# ---------------------------------------------------------------------------

class TestSparkEngineImportError:
    def test_spark_missing_import_raises(self):
        """When pyspark is not installed, SparkEngine() should raise ImportError."""
        try:
            import pyspark  # noqa: F401
            pytest.skip("pyspark is installed; cannot test missing-import path")
        except ImportError:
            with pytest.raises(ImportError, match="PySpark is not installed"):
                SparkEngine()


# ---------------------------------------------------------------------------
# PostGISEngine — import guard only (no actual PostGIS)
# ---------------------------------------------------------------------------

class TestPostGISEngineErrors:
    def test_postgis_missing_sqlalchemy_raises(self):
        """When sqlalchemy is not installed, PostGISEngine() should raise ImportError."""
        try:
            import sqlalchemy  # noqa: F401
        except ImportError:
            with pytest.raises(ImportError, match="SQLAlchemy is not installed"):
                PostGISEngine("postgresql://fake:fake@localhost/fake")
            return
        # sqlalchemy is available; test geopandas guard instead
        try:
            import geopandas  # noqa: F401
        except ImportError:
            with pytest.raises(ImportError, match="GeoPandas is not installed"):
                PostGISEngine("postgresql://fake:fake@localhost/fake")
            return
        # Both are available — test that it at least doesn't explode
        engine = PostGISEngine("postgresql://fake:fake@localhost/fake")
        assert engine.name == "postgis"

    def test_postgis_index_points_raises(self):
        """PostGISEngine.index_points always raises NotImplementedError."""
        try:
            import sqlalchemy  # noqa: F401
            import geopandas  # noqa: F401
        except ImportError:
            pytest.skip("sqlalchemy or geopandas not installed")
        engine = PostGISEngine("postgresql://fake:fake@localhost/fake")
        with pytest.raises(NotImplementedError, match="compute cell IDs at ingest time"):
            engine.index_points(_sample_df(), "lat", "lon")

    def test_postgis_to_geodataframe_missing_col_raises(self):
        """PostGISEngine.to_geodataframe raises on missing geometry column."""
        try:
            import sqlalchemy  # noqa: F401
            import geopandas  # noqa: F401
        except ImportError:
            pytest.skip("sqlalchemy or geopandas not installed")
        engine = PostGISEngine("postgresql://fake:fake@localhost/fake")
        df = _sample_df()
        with pytest.raises(ValueError, match="geometry.*not found"):
            engine.to_geodataframe(df, geometry_col="geometry")


# ---------------------------------------------------------------------------
# Engine enum exhaustiveness
# ---------------------------------------------------------------------------

class TestEngineMapExhaustivenessError:
    def test_all_engine_members_are_mapped(self):
        """The _ENGINE_MAP should cover every Engine enum member.
        If not, the module raises RuntimeError at import time.
        This test just confirms the module imported successfully."""
        from siege_utilities.engines.dataframe_engine import _ENGINE_MAP
        for member in Engine:
            assert member in _ENGINE_MAP, f"Engine.{member.name} missing from _ENGINE_MAP"


# ---------------------------------------------------------------------------
# get_engine — valid names produce engines (sanity check)
# ---------------------------------------------------------------------------

class TestGetEngineValidNames:
    def test_pandas_engine_valid(self):
        engine = get_engine("pandas")
        assert engine.name == "pandas"

    def test_pandas_engine_from_enum_valid(self):
        engine = get_engine(Engine.PANDAS)
        assert engine.name == "pandas"

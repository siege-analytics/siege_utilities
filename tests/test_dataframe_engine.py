"""Tests for the engine-agnostic DataFrame abstraction.

See: https://github.com/siege-analytics/siege_utilities/issues/92
"""

from __future__ import annotations

import csv
import os
import tempfile
from pathlib import Path
from unittest import mock

import pandas as pd
import pytest

from siege_utilities.data.dataframe_engine import (
    DUCKDB,
    PANDAS,
    POSTGIS,
    SPARK,
    DataFrameEngine,
    DuckDBEngine,
    Engine,
    PandasEngine,
    PostGISEngine,
    SparkEngine,
    get_engine,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sample_csv(tmp_path: Path) -> Path:
    """Write a small CSV and return the path."""
    p = tmp_path / "sample.csv"
    p.write_text("name,value,group\nalice,10,a\nbob,20,a\ncharlie,30,b\n")
    return p


def _sample_df() -> pd.DataFrame:
    return pd.DataFrame(
        {"name": ["alice", "bob", "charlie"], "value": [10, 20, 30], "group": ["a", "a", "b"]}
    )


# ---------------------------------------------------------------------------
# Engine enum
# ---------------------------------------------------------------------------

class TestEngineEnum:
    def test_values(self):
        assert Engine.PANDAS.value == "pandas"
        assert Engine.DUCKDB.value == "duckdb"
        assert Engine.SPARK.value == "spark"
        assert Engine.POSTGIS.value == "postgis"

    def test_string_constants(self):
        assert PANDAS == "pandas"
        assert DUCKDB == "duckdb"
        assert SPARK == "spark"
        assert POSTGIS == "postgis"

    def test_enum_from_string(self):
        assert Engine("pandas") is Engine.PANDAS
        assert Engine("duckdb") is Engine.DUCKDB


# ---------------------------------------------------------------------------
# ABC contract
# ---------------------------------------------------------------------------

class TestABC:
    def test_cannot_instantiate_abc(self):
        with pytest.raises(TypeError):
            DataFrameEngine()  # type: ignore[abstract]


# ---------------------------------------------------------------------------
# PandasEngine — thorough tests
# ---------------------------------------------------------------------------

class TestPandasEngine:
    def test_name(self):
        engine = PandasEngine()
        assert engine.name == "pandas"

    def test_isinstance_abc(self):
        assert isinstance(PandasEngine(), DataFrameEngine)

    # -- read_csv -----------------------------------------------------------

    def test_read_csv(self, tmp_path: Path):
        csv_path = _sample_csv(tmp_path)
        engine = PandasEngine()
        df = engine.read_csv(str(csv_path))
        assert isinstance(df, pd.DataFrame)
        assert list(df.columns) == ["name", "value", "group"]
        assert len(df) == 3

    def test_read_csv_kwargs(self, tmp_path: Path):
        csv_path = _sample_csv(tmp_path)
        engine = PandasEngine()
        df = engine.read_csv(str(csv_path), usecols=["name", "value"])
        assert list(df.columns) == ["name", "value"]

    # -- read_parquet -------------------------------------------------------

    def test_read_parquet(self, tmp_path: Path):
        pq_path = tmp_path / "sample.parquet"
        _sample_df().to_parquet(pq_path)
        engine = PandasEngine()
        df = engine.read_parquet(str(pq_path))
        assert len(df) == 3

    # -- query --------------------------------------------------------------

    def test_query_requires_connection(self):
        engine = PandasEngine()
        with pytest.raises(ValueError, match="connection"):
            engine.query("SELECT 1")

    # -- to_pandas ----------------------------------------------------------

    def test_to_pandas_passthrough(self):
        engine = PandasEngine()
        df = _sample_df()
        result = engine.to_pandas(df)
        assert isinstance(result, pd.DataFrame)
        pd.testing.assert_frame_equal(result, df)

    def test_to_pandas_from_dict(self):
        engine = PandasEngine()
        result = engine.to_pandas({"a": [1, 2], "b": [3, 4]})
        assert isinstance(result, pd.DataFrame)
        assert list(result.columns) == ["a", "b"]

    # -- groupby_agg --------------------------------------------------------

    def test_groupby_agg_sum(self):
        engine = PandasEngine()
        df = _sample_df()
        result = engine.groupby_agg(df, ["group"], {"value": "sum"})
        assert isinstance(result, pd.DataFrame)
        assert set(result["group"]) == {"a", "b"}
        row_a = result.loc[result["group"] == "a", "value"].iloc[0]
        assert row_a == 30  # 10 + 20

    def test_groupby_agg_multiple_cols(self):
        engine = PandasEngine()
        df = pd.DataFrame({
            "g1": ["x", "x", "y", "y"],
            "g2": ["a", "b", "a", "b"],
            "v": [1, 2, 3, 4],
        })
        result = engine.groupby_agg(df, ["g1", "g2"], {"v": "sum"})
        assert len(result) == 4

    def test_groupby_agg_mean(self):
        engine = PandasEngine()
        df = _sample_df()
        result = engine.groupby_agg(df, ["group"], {"value": "mean"})
        row_a = result.loc[result["group"] == "a", "value"].iloc[0]
        assert row_a == 15.0  # (10 + 20) / 2

    # -- filter -------------------------------------------------------------

    def test_filter_boolean_series(self):
        engine = PandasEngine()
        df = _sample_df()
        result = engine.filter(df, df["value"] > 10)
        assert len(result) == 2
        assert list(result["name"]) == ["bob", "charlie"]

    def test_filter_resets_index(self):
        engine = PandasEngine()
        df = _sample_df()
        result = engine.filter(df, df["group"] == "b")
        assert list(result.index) == [0]

    # -- join ---------------------------------------------------------------

    def test_join_inner(self):
        engine = PandasEngine()
        left = pd.DataFrame({"key": [1, 2, 3], "lval": ["a", "b", "c"]})
        right = pd.DataFrame({"key": [2, 3, 4], "rval": ["x", "y", "z"]})
        result = engine.join(left, right, on="key", how="inner")
        assert len(result) == 2
        assert set(result["key"]) == {2, 3}

    def test_join_left(self):
        engine = PandasEngine()
        left = pd.DataFrame({"key": [1, 2], "lval": ["a", "b"]})
        right = pd.DataFrame({"key": [2, 3], "rval": ["x", "y"]})
        result = engine.join(left, right, on="key", how="left")
        assert len(result) == 2

    def test_join_on_list(self):
        engine = PandasEngine()
        left = pd.DataFrame({"k1": [1, 2], "k2": ["a", "b"], "v": [10, 20]})
        right = pd.DataFrame({"k1": [1, 2], "k2": ["a", "b"], "w": [30, 40]})
        result = engine.join(left, right, on=["k1", "k2"])
        assert len(result) == 2
        assert "w" in result.columns


# ---------------------------------------------------------------------------
# get_engine factory
# ---------------------------------------------------------------------------

class TestGetEngine:
    def test_pandas_by_enum(self):
        engine = get_engine(Engine.PANDAS)
        assert isinstance(engine, PandasEngine)

    def test_pandas_by_string(self):
        engine = get_engine("pandas")
        assert isinstance(engine, PandasEngine)

    def test_pandas_case_insensitive(self):
        engine = get_engine("PANDAS")
        assert isinstance(engine, PandasEngine)

    def test_invalid_engine_raises(self):
        with pytest.raises(ValueError, match="Unknown engine"):
            get_engine("nonexistent")


# ---------------------------------------------------------------------------
# DuckDB engine — import error handling
# ---------------------------------------------------------------------------

def _duckdb_available() -> bool:
    try:
        import duckdb  # noqa: F401
        return True
    except ImportError:
        return False


class TestDuckDBEngine:
    def test_import_error_when_not_installed(self):
        with mock.patch.dict("sys.modules", {"duckdb": None}):
            with pytest.raises(ImportError, match="DuckDB is not installed"):
                DuckDBEngine()

    def test_factory_returns_duckdb(self):
        """get_engine('duckdb') returns a DuckDBEngine if duckdb is installed."""
        if not _duckdb_available():
            pytest.skip("duckdb not installed")
        engine = get_engine("duckdb")
        assert isinstance(engine, DuckDBEngine)
        assert engine.name == "duckdb"


def _pyspark_available() -> bool:
    try:
        import pyspark  # noqa: F401
        return True
    except ImportError:
        return False


class TestDuckDBIntegration:
    """Integration tests that run only when duckdb is installed."""

    @pytest.fixture(autouse=True)
    def _skip_if_no_duckdb(self):
        if not _duckdb_available():
            pytest.skip("duckdb not installed")

    def test_read_csv(self, tmp_path: Path):
        csv_path = _sample_csv(tmp_path)
        engine = get_engine("duckdb")
        df = engine.read_csv(str(csv_path))
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 3

    def test_read_parquet(self, tmp_path: Path):
        pq_path = tmp_path / "sample.parquet"
        _sample_df().to_parquet(pq_path)
        engine = get_engine("duckdb")
        df = engine.read_parquet(str(pq_path))
        assert len(df) == 3

    def test_query_with_table(self):
        engine = get_engine("duckdb")
        src = _sample_df()
        result = engine.query("SELECT * FROM tbl WHERE value > 10", table="tbl", df=src)
        assert len(result) == 2

    def test_groupby_agg(self):
        engine = get_engine("duckdb")
        df = _sample_df()
        result = engine.groupby_agg(df, ["group"], {"value": "sum"})
        assert len(result) == 2

    def test_join(self):
        engine = get_engine("duckdb")
        left = pd.DataFrame({"key": [1, 2], "v": [10, 20]})
        right = pd.DataFrame({"key": [2, 3], "w": [30, 40]})
        result = engine.join(left, right, on="key", how="inner")
        assert len(result) == 1

    def test_to_pandas(self):
        engine = get_engine("duckdb")
        df = _sample_df()
        result = engine.to_pandas(df)
        assert isinstance(result, pd.DataFrame)


# ---------------------------------------------------------------------------
# Spark engine — import error handling
# ---------------------------------------------------------------------------

class TestSparkEngine:
    def test_import_error_when_not_installed(self):
        with mock.patch.dict("sys.modules", {"pyspark": None}):
            with pytest.raises(ImportError, match="PySpark is not installed"):
                SparkEngine()


class TestSparkIntegration:
    """Integration tests that run only when pyspark is installed."""

    @pytest.fixture(autouse=True)
    def _skip_if_no_pyspark(self):
        if not _pyspark_available():
            pytest.skip("pyspark not installed")

    def test_factory_returns_spark(self):
        engine = get_engine("spark")
        assert isinstance(engine, SparkEngine)
        assert engine.name == "spark"


# ---------------------------------------------------------------------------
# PostGIS engine — import error handling
# ---------------------------------------------------------------------------

class TestPostGISEngine:
    def test_import_error_no_sqlalchemy(self):
        with mock.patch.dict("sys.modules", {"sqlalchemy": None}):
            with pytest.raises(ImportError, match="SQLAlchemy is not installed"):
                PostGISEngine(connection_string="postgresql://localhost/test")

    def test_import_error_no_geopandas(self):
        # sqlalchemy is available but geopandas is not
        with mock.patch.dict("sys.modules", {"geopandas": None}):
            try:
                import sqlalchemy  # noqa: F401
            except ImportError:
                pytest.skip("sqlalchemy not installed")
            with pytest.raises(ImportError, match="GeoPandas is not installed"):
                PostGISEngine(connection_string="postgresql://localhost/test")

    def test_factory_requires_connection_string(self):
        """PostGIS engine needs connection_string kwarg."""
        try:
            import sqlalchemy, geopandas  # noqa: F401
        except ImportError:
            pytest.skip("sqlalchemy or geopandas not installed")
        with pytest.raises(TypeError):
            get_engine("postgis")  # missing connection_string


# ---------------------------------------------------------------------------
# Round-trip integration: read -> transform -> to_pandas (Pandas engine)
# ---------------------------------------------------------------------------

class TestPandasRoundTrip:
    def test_csv_filter_groupby_join(self, tmp_path: Path):
        csv_path = _sample_csv(tmp_path)
        engine = get_engine("pandas")

        # Read
        df = engine.read_csv(str(csv_path))
        assert len(df) == 3

        # Filter
        filtered = engine.filter(df, df["value"] >= 20)
        assert len(filtered) == 2

        # GroupBy
        agged = engine.groupby_agg(filtered, ["group"], {"value": "sum"})
        assert len(agged) <= 2

        # Join with another frame
        lookup = pd.DataFrame({"group": ["a", "b"], "label": ["Alpha", "Beta"]})
        joined = engine.join(agged, lookup, on="group")
        assert "label" in joined.columns

        # To pandas (idempotent)
        result = engine.to_pandas(joined)
        assert isinstance(result, pd.DataFrame)

    def test_parquet_round_trip(self, tmp_path: Path):
        pq_path = tmp_path / "rt.parquet"
        _sample_df().to_parquet(pq_path)
        engine = get_engine("pandas")
        df = engine.read_parquet(str(pq_path))
        result = engine.groupby_agg(df, ["group"], {"value": "max"})
        assert result.loc[result["group"] == "b", "value"].iloc[0] == 30

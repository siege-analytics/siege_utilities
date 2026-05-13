"""Cross-engine tests for the to_geodataframe error contract.

INVARIANTS.md says every engine must raise `ValueError` when the
geometry column is missing. Pin this on every engine whose constructor
works without external dependencies (PandasEngine, DuckDBEngine,
PostGISEngine; SparkEngine deferred because it requires a session).
"""

from __future__ import annotations

import pytest

pd = pytest.importorskip("pandas")


@pytest.fixture
def df_without_geometry():
    return pd.DataFrame({"id": [1, 2, 3], "name": ["a", "b", "c"]})


def _pandas_engine():
    from siege_utilities.engines.dataframe_engine import PandasEngine
    return PandasEngine()


def _duckdb_engine_or_skip():
    try:
        from siege_utilities.engines.dataframe_engine import DuckDBEngine
        return DuckDBEngine()
    except ImportError:
        pytest.skip("DuckDB not installed")


def _postgis_engine_or_skip():
    """to_geodataframe is pure-pandas and never touches the connection,
    so a placeholder DSN is fine. PostGISEngine requires a
    connection_string at construct time though."""
    try:
        from siege_utilities.engines.dataframe_engine import PostGISEngine
        return PostGISEngine("postgresql://placeholder@invalid:5432/none")
    except ImportError:
        pytest.skip("psycopg2 / SQLAlchemy not installed")


def test_pandas_to_geodataframe_missing_column_raises_value_error(df_without_geometry):
    pytest.importorskip("geopandas")
    with pytest.raises(ValueError, match="geometry"):
        _pandas_engine().to_geodataframe(df_without_geometry, geometry_col="geometry")


def test_duckdb_to_geodataframe_missing_column_raises_value_error(df_without_geometry):
    pytest.importorskip("geopandas")
    engine = _duckdb_engine_or_skip()
    with pytest.raises(ValueError, match="geometry"):
        engine.to_geodataframe(df_without_geometry, geometry_col="geometry")


def test_postgis_to_geodataframe_missing_column_raises_value_error(df_without_geometry):
    pytest.importorskip("geopandas")
    engine = _postgis_engine_or_skip()
    with pytest.raises(ValueError, match="geometry"):
        engine.to_geodataframe(df_without_geometry, geometry_col="geometry")


def test_pandas_to_geodataframe_custom_column_name_in_message(df_without_geometry):
    """The custom column name appears in the error message verbatim
    so users can find the typo quickly. The current message format is
    `Cannot construct GeoDataFrame: column 'X' not found`."""
    pytest.importorskip("geopandas")
    with pytest.raises(ValueError, match="'geom_typo' not found"):
        _pandas_engine().to_geodataframe(df_without_geometry, geometry_col="geom_typo")

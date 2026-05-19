"""Tests for DataFrameEngine.index_points / index_polygon (ELE-2485).

The default ABC implementation round-trips through pandas; per-engine
overrides (PostGISEngine in particular) are also covered.
"""

from __future__ import annotations

import pandas as pd
import pytest


# ---------------------------------------------------------------------------
# PandasEngine path — exercises the ABC default end-to-end
# ---------------------------------------------------------------------------

class TestPandasEngineIndexPoints:
    @pytest.fixture
    def df(self):
        return pd.DataFrame({"lat": [33.5, 40.7], "lon": [-86.8, -74.0]})

    def test_default_resolves_to_s2(self, df):
        """No grid kwargs → engine default picks S2 at level 12."""
        pytest.importorskip("s2sphere")
        from siege_utilities.engines.dataframe_engine import PandasEngine
        engine = PandasEngine()
        result = engine.index_points(df, "lat", "lon")
        assert "s2_index" in result.columns
        assert len(result) == 2
        assert result["s2_index"].iloc[0] != result["s2_index"].iloc[1]

    def test_h3_via_resolution_kwarg(self, df):
        pytest.importorskip("h3")
        from siege_utilities.engines.dataframe_engine import PandasEngine
        engine = PandasEngine()
        result = engine.index_points(df, "lat", "lon", resolution=8)
        assert "h3_index" in result.columns

    def test_s2_via_level_kwarg(self, df):
        pytest.importorskip("s2sphere")
        from siege_utilities.engines.dataframe_engine import PandasEngine
        engine = PandasEngine()
        result = engine.index_points(df, "lat", "lon", level=10)
        assert "s2_index" in result.columns

    def test_explicit_grid_h3(self, df):
        pytest.importorskip("h3")
        from siege_utilities.engines.dataframe_engine import PandasEngine
        engine = PandasEngine()
        result = engine.index_points(df, "lat", "lon", grid="h3", resolution=7)
        assert "h3_index" in result.columns

    def test_index_polygon(self, df):
        pytest.importorskip("s2sphere")
        from shapely.geometry import box
        from siege_utilities.engines.dataframe_engine import PandasEngine
        engine = PandasEngine()
        cells = engine.index_polygon(box(-87, 33, -86, 34), level=8)
        assert isinstance(cells, set)
        assert len(cells) > 0

    def test_index_polygon_region_cover(self):
        pytest.importorskip("s2sphere")
        from shapely.geometry import box
        from siege_utilities.engines.dataframe_engine import PandasEngine
        engine = PandasEngine()
        cells = engine.index_polygon(box(-87, 33, -86, 34), max_cells=10)
        assert isinstance(cells, list)
        assert len(cells) <= 10


# ---------------------------------------------------------------------------
# Dispatcher (`grids.index_points`) with `engine=` kwarg
# ---------------------------------------------------------------------------

class TestDispatcherEngineRouting:
    @pytest.fixture
    def df(self):
        return pd.DataFrame({"lat": [33.5], "lon": [-86.8]})

    def test_engine_kwarg_routes_to_engine(self, df):
        pytest.importorskip("s2sphere")
        from siege_utilities.geo.grids import index_points
        from siege_utilities.engines.dataframe_engine import PandasEngine
        engine = PandasEngine()
        result = index_points(df, "lat", "lon", engine=engine, level=10)
        # Engine path returns the augmented DataFrame, not just a Series.
        assert isinstance(result, pd.DataFrame)
        assert "s2_index" in result.columns

    def test_no_engine_returns_series(self, df):
        """Backward-compat: without engine=, returns a pd.Series of cells."""
        pytest.importorskip("s2sphere")
        from siege_utilities.geo.grids import index_points
        result = index_points(df, "lat", "lon", level=10)
        assert isinstance(result, pd.Series)


# ---------------------------------------------------------------------------
# PostGISEngine override — index_points raises with the documented pattern
# ---------------------------------------------------------------------------

class TestPostGISEngineIndexPoints:
    def test_postgis_raises_with_helpful_pointer(self):
        from siege_utilities.engines.dataframe_engine import PostGISEngine
        engine = PostGISEngine.__new__(PostGISEngine)  # skip __init__ (needs DSN)
        df = pd.DataFrame({"lat": [33.5], "lon": [-86.8]})
        with pytest.raises(NotImplementedError, match="ingest time"):
            engine.index_points(df, "lat", "lon", level=10)


# ---------------------------------------------------------------------------
# Cross-engine consistency property test
# ---------------------------------------------------------------------------

class TestCrossEngineConsistency:
    """The default ABC path round-trips through pandas, so any engine
    using the default produces the same cell IDs as PandasEngine. The
    test covers PandasEngine (only one without specialised dependencies
    in the test env) — the other engines slot in identically when
    available.
    """

    def test_pandas_engine_matches_standalone(self):
        pytest.importorskip("s2sphere")
        from siege_utilities.geo.s2_utils import s2_index_points
        from siege_utilities.engines.dataframe_engine import PandasEngine
        df = pd.DataFrame({
            "lat": [33.5, 40.7, 51.5, -33.9],
            "lon": [-86.8, -74.0, -0.1, 18.4],
        })
        engine = PandasEngine()
        engine_result = engine.index_points(df, "lat", "lon", level=10)
        standalone = s2_index_points(df, "lat", "lon", level=10)
        assert list(engine_result["s2_index"]) == list(standalone)

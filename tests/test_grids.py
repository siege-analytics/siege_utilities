"""Tests for the grid-agnostic dispatch wrapper in siege_utilities.geo.grids."""

from __future__ import annotations

import pandas as pd
import pytest

from siege_utilities.geo import grids


# ---------------------------------------------------------------------------
# infer_grid (pure inference, no extra-deps)
# ---------------------------------------------------------------------------

class TestInferGrid:
    def test_explicit_h3_wins(self):
        assert grids.infer_grid("h3", {"level": 12}) == "h3"

    def test_explicit_s2_wins(self):
        assert grids.infer_grid("s2", {"resolution": 8}) == "s2"

    def test_invalid_grid_raises(self):
        with pytest.raises(ValueError, match="grid must be"):
            grids.infer_grid("hex", {})

    def test_s2_kwarg_implies_s2(self):
        assert grids.infer_grid(None, {"max_cells": 50}) == "s2"
        assert grids.infer_grid(None, {"min_level": 5}) == "s2"
        assert grids.infer_grid(None, {"max_level": 12}) == "s2"
        assert grids.infer_grid(None, {"level": 12}) == "s2"

    def test_resolution_kwarg_implies_h3(self):
        assert grids.infer_grid(None, {"resolution": 8}) == "h3"

    def test_no_kwargs_defaults_h3(self):
        assert grids.infer_grid(None, {}) == "h3"

    def test_none_values_ignored(self):
        # None values should not trigger inference for that kwarg.
        assert grids.infer_grid(None, {"level": None, "resolution": None}) == "h3"
        assert grids.infer_grid(None, {"level": None, "max_cells": 50}) == "s2"

    def test_mixed_kwargs_raises(self):
        with pytest.raises(ValueError, match="Ambiguous"):
            grids.infer_grid(None, {"resolution": 8, "level": 12})


# ---------------------------------------------------------------------------
# index_points dispatch (skip when underlying grid lib missing)
# ---------------------------------------------------------------------------

class TestIndexPointsDispatch:
    @pytest.fixture
    def df(self):
        return pd.DataFrame({"lat": [33.5, 40.7], "lon": [-86.8, -74.0]})

    def test_h3_path(self, df):
        h3 = pytest.importorskip("h3")  # noqa: F841
        out = grids.index_points(df, "lat", "lon", resolution=8)
        assert len(out) == 2
        # H3 cells are 15-char hex strings
        assert all(isinstance(v, str) and len(v) == 15 for v in out)

    def test_s2_path(self, df):
        pytest.importorskip("s2sphere")
        out = grids.index_points(df, "lat", "lon", level=12)
        assert len(out) == 2
        # Default S2 returns hex tokens
        assert all(isinstance(v, str) for v in out)

    def test_explicit_grid_overrides_default(self, df):
        pytest.importorskip("s2sphere")
        out = grids.index_points(df, "lat", "lon", grid="s2")
        assert len(out) == 2


# ---------------------------------------------------------------------------
# index_polygon dispatch
# ---------------------------------------------------------------------------

class TestIndexPolygonDispatch:
    @pytest.fixture
    def square(self):
        shapely = pytest.importorskip("shapely.geometry")
        return shapely.box(-87.0, 33.0, -86.0, 34.0)

    def test_h3_returns_set(self, square):
        pytest.importorskip("h3")
        result = grids.index_polygon(square, resolution=7)
        assert isinstance(result, set)

    def test_s2_single_level_returns_set(self, square):
        pytest.importorskip("s2sphere")
        result = grids.index_polygon(square, level=8)
        assert isinstance(result, set)

    def test_s2_region_cover_returns_list(self, square):
        pytest.importorskip("s2sphere")
        result = grids.index_polygon(square, max_cells=20)
        assert isinstance(result, list)
        assert len(result) <= 20

    def test_s2_min_level_triggers_region_cover(self, square):
        pytest.importorskip("s2sphere")
        result = grids.index_polygon(
            square, min_level=4, max_level=12, max_cells=30,
        )
        assert isinstance(result, list)

    def test_ambiguous_kwargs_raises(self, square):
        with pytest.raises(ValueError, match="Ambiguous"):
            grids.index_polygon(square, resolution=8, level=10)

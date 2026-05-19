"""Tests for siege_utilities.reporting.hex_cartogram (ELE-2482)."""

from __future__ import annotations

import pandas as pd
import pytest


# ---------------------------------------------------------------------------
# Fixtures: synthetic GeoDataFrame of contiguous + non-contiguous polygons
# ---------------------------------------------------------------------------

@pytest.fixture
def gpd_box():
    pytest.importorskip("geopandas")
    pytest.importorskip("shapely")
    from shapely.geometry import box  # noqa: F401
    return box


@pytest.fixture
def grid_3x3(gpd_box):
    """A 3x3 contiguous grid of unit squares — 9 polygons, all touching neighbours."""
    import geopandas as gpd
    rows = []
    for i in range(3):
        for j in range(3):
            rows.append({
                "code": f"r{i}c{j}",
                "geometry": gpd_box(j, i, j + 1, i + 1),
            })
    return gpd.GeoDataFrame(rows, geometry="geometry")


@pytest.fixture
def disconnected_groups(gpd_box):
    """3 disconnected groups: 3 cells + 2 cells + 1 cell = 6 polygons total."""
    import geopandas as gpd
    rows = []
    # Group A: 3 in a row at y=0
    for j in range(3):
        rows.append({"code": f"a{j}", "geometry": gpd_box(j, 0, j + 1, 1)})
    # Group B: 2 squares far away at y=10
    for j in range(2):
        rows.append({"code": f"b{j}", "geometry": gpd_box(j + 20, 10, j + 21, 11)})
    # Group C: lonely square far far away
    rows.append({"code": "c0", "geometry": gpd_box(40, -10, 41, -9)})
    return gpd.GeoDataFrame(rows, geometry="geometry")


# ---------------------------------------------------------------------------
# Algorithms
# ---------------------------------------------------------------------------

class TestPlacePolygons:
    def test_greedy_assigns_every_polygon(self, grid_3x3):
        from siege_utilities.reporting.hex_cartogram.algorithms import (
            Algorithm, place_polygons,
        )
        out = place_polygons(grid_3x3, "code", algorithm=Algorithm.GREEDY)
        assert set(out) == set(grid_3x3["code"])
        # No two polygons assigned to the same hex.
        assert len(set(out.values())) == len(out)

    def test_hungarian_assigns_optimally(self, grid_3x3):
        pytest.importorskip("scipy")
        from siege_utilities.reporting.hex_cartogram.algorithms import (
            Algorithm, place_polygons,
        )
        out = place_polygons(grid_3x3, "code", algorithm=Algorithm.HUNGARIAN)
        assert set(out) == set(grid_3x3["code"])
        assert len(set(out.values())) == len(out)

    def test_annealing_runs(self, grid_3x3):
        from siege_utilities.reporting.hex_cartogram.algorithms import (
            Algorithm, place_polygons,
        )
        out = place_polygons(
            grid_3x3, "code", algorithm=Algorithm.ANNEALING,
            iterations=200, seed=42,
        )
        assert set(out) == set(grid_3x3["code"])
        assert len(set(out.values())) == len(out)

    def test_force_directed_reserved(self, grid_3x3):
        from siege_utilities.reporting.hex_cartogram.algorithms import (
            Algorithm, place_polygons,
        )
        with pytest.raises(NotImplementedError, match="force_directed"):
            place_polygons(
                grid_3x3, "code", algorithm=Algorithm.FORCE_DIRECTED,
            )

    def test_ilp_reserved(self, grid_3x3):
        from siege_utilities.reporting.hex_cartogram.algorithms import (
            Algorithm, place_polygons,
        )
        with pytest.raises(NotImplementedError, match="ilp"):
            place_polygons(grid_3x3, "code", algorithm=Algorithm.ILP)

    def test_empty_gdf_raises(self):
        pytest.importorskip("geopandas")
        import geopandas as gpd
        from siege_utilities.reporting.hex_cartogram.algorithms import (
            Algorithm, place_polygons,
        )
        empty = gpd.GeoDataFrame({"code": [], "geometry": []})
        with pytest.raises(ValueError, match="empty"):
            place_polygons(empty, "code", algorithm=Algorithm.GREEDY)

    def test_missing_code_col_raises(self, grid_3x3):
        from siege_utilities.reporting.hex_cartogram.algorithms import (
            place_polygons,
        )
        with pytest.raises(ValueError, match="not in gdf"):
            place_polygons(grid_3x3, "nonexistent_col")


# ---------------------------------------------------------------------------
# Connected-component splitting
# ---------------------------------------------------------------------------

class TestComponents:
    def test_single_component_for_grid(self, grid_3x3):
        from siege_utilities.reporting.hex_cartogram.components import (
            find_components,
        )
        comps = find_components(grid_3x3, "code")
        assert len(comps) == 1
        assert set(comps[0]) == set(grid_3x3["code"])

    def test_three_components_for_disconnected(self, disconnected_groups):
        from siege_utilities.reporting.hex_cartogram.components import (
            find_components,
        )
        comps = find_components(disconnected_groups, "code")
        assert len(comps) == 3
        # Largest first.
        assert len(comps[0]) >= len(comps[1]) >= len(comps[2])
        assert sum(len(c) for c in comps) == 6

    def test_stitch_separates_components(self):
        from siege_utilities.reporting.hex_cartogram.components import (
            stitch_components,
        )
        a = {"a0": (0, 0), "a1": (1, 0)}
        b = {"b0": (0, 0), "b1": (1, 0)}
        merged = stitch_components([a, b], component_gap=2)
        # b cells should not collide with a cells.
        all_cells = list(merged.values())
        assert len(set(all_cells)) == len(all_cells)
        # b should be shifted right of a.
        assert merged["b0"][0] > merged["a1"][0]


# ---------------------------------------------------------------------------
# hex_tile_layout dispatcher
# ---------------------------------------------------------------------------

class TestHexTileLayout:
    def test_geodataframe_input_produces_layout(self, grid_3x3):
        from siege_utilities.reporting.hex_cartogram.layouts import (
            hex_tile_layout,
        )
        layout = hex_tile_layout(grid_3x3, code_col="code", algorithm="greedy")
        assert "geometry" in layout.columns
        assert "code" in layout.columns
        assert "q" in layout.columns
        assert "r" in layout.columns
        assert len(layout) == len(grid_3x3)

    def test_disconnected_uses_component_split(self, disconnected_groups):
        from siege_utilities.reporting.hex_cartogram.layouts import (
            hex_tile_layout,
        )
        layout = hex_tile_layout(
            disconnected_groups, code_col="code",
            algorithm="greedy", components="auto", component_gap=1,
        )
        assert len(layout) == 6

    def test_components_single_forces_one_layout(self, disconnected_groups):
        from siege_utilities.reporting.hex_cartogram.layouts import (
            hex_tile_layout,
        )
        layout = hex_tile_layout(
            disconnected_groups, code_col="code",
            algorithm="greedy", components="single",
        )
        assert len(layout) == 6

    def test_register_and_use_named_layout(self):
        from siege_utilities.reporting.hex_cartogram.layouts import (
            hex_tile_layout, register_layout, REGISTERED_LAYOUTS,
        )
        register_layout("test_layout", {"a": (0, 0), "b": (1, 0)})
        try:
            layout = hex_tile_layout("test_layout")
            assert len(layout) == 2
            assert set(layout["code"]) == {"a", "b"}
        finally:
            REGISTERED_LAYOUTS.pop("test_layout", None)

    def test_register_duplicate_cells_raises(self):
        from siege_utilities.reporting.hex_cartogram.layouts import (
            register_layout,
        )
        with pytest.raises(ValueError, match="duplicate hex"):
            register_layout("dup", {"a": (0, 0), "b": (0, 0)})

    def test_unknown_layout_raises(self):
        from siege_utilities.reporting.hex_cartogram.layouts import (
            hex_tile_layout,
        )
        with pytest.raises(KeyError, match="Unknown layout"):
            hex_tile_layout("does_not_exist")


# ---------------------------------------------------------------------------
# Renderer
# ---------------------------------------------------------------------------

class TestHexTileMap:
    @pytest.fixture
    def small_layout(self, grid_3x3):
        from siege_utilities.reporting.hex_cartogram.layouts import (
            hex_tile_layout,
        )
        return hex_tile_layout(grid_3x3, code_col="code", algorithm="greedy")

    @pytest.fixture
    def values(self, grid_3x3):
        # Increasing values 0..8.
        return pd.Series(
            range(9),
            index=grid_3x3["code"].tolist(),
        )

    def test_equal_sizing_produces_figure(self, small_layout, values):
        pytest.importorskip("matplotlib")
        from siege_utilities.reporting.hex_cartogram.renderer import (
            hex_tile_map, Sizing,
        )
        fig = hex_tile_map(values, small_layout, sizing=Sizing.EQUAL)
        assert fig is not None

    def test_value_proportional_sizing(self, small_layout, values):
        pytest.importorskip("matplotlib")
        from siege_utilities.reporting.hex_cartogram.renderer import (
            hex_tile_map,
        )
        fig = hex_tile_map(values, small_layout, sizing="value_proportional")
        assert fig is not None

    def test_value_sqrt_sizing(self, small_layout, values):
        pytest.importorskip("matplotlib")
        from siege_utilities.reporting.hex_cartogram.renderer import (
            hex_tile_map,
        )
        fig = hex_tile_map(values, small_layout, sizing="value_sqrt")
        assert fig is not None

    def test_missing_values_render_as_missing_color(self, small_layout):
        pytest.importorskip("matplotlib")
        from siege_utilities.reporting.hex_cartogram.renderer import (
            hex_tile_map,
        )
        # Provide values for only some codes.
        partial = pd.Series([1.0, 2.0], index=["r0c0", "r1c1"])
        fig = hex_tile_map(partial, small_layout)
        assert fig is not None  # didn't crash

    def test_no_aligned_values_warns_but_renders(self, small_layout, caplog):
        pytest.importorskip("matplotlib")
        from siege_utilities.reporting.hex_cartogram.renderer import (
            hex_tile_map,
        )
        fig = hex_tile_map(pd.Series(dtype=float), small_layout)
        assert fig is not None

    def test_unknown_sizing_raises(self, small_layout, values):
        pytest.importorskip("matplotlib")
        from siege_utilities.reporting.hex_cartogram.renderer import (
            hex_tile_map,
        )
        with pytest.raises(ValueError, match="not a valid Sizing"):
            hex_tile_map(values, small_layout, sizing="invalid")


# ---------------------------------------------------------------------------
# Coords
# ---------------------------------------------------------------------------

class TestCoords:
    def test_neighbors_are_six(self):
        from siege_utilities.reporting.hex_cartogram.coords import (
            axial_neighbors,
        )
        assert len(axial_neighbors((0, 0))) == 6

    def test_distance_zero_to_self(self):
        from siege_utilities.reporting.hex_cartogram.coords import (
            axial_distance,
        )
        assert axial_distance((3, 4), (3, 4)) == 0

    def test_distance_one_for_neighbor(self):
        from siege_utilities.reporting.hex_cartogram.coords import (
            axial_distance, axial_neighbors,
        )
        for n in axial_neighbors((0, 0)):
            assert axial_distance((0, 0), n) == 1

    def test_hexagon_polygon_has_six_vertices(self):
        from siege_utilities.reporting.hex_cartogram.coords import (
            hexagon_polygon,
        )
        verts = hexagon_polygon((0, 0))
        assert len(verts) == 6

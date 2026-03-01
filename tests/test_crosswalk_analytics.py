"""Tests for crosswalk time-series analytics.

Uses synthetic crosswalk data representing boundary changes between
Census vintages.
"""

import pytest
import pandas as pd


@pytest.fixture
def simple_crosswalk():
    """A simple crosswalk where one tract splits into two."""
    return pd.DataFrame({
        "source_geoid": ["06001400100", "06001400100", "06001400200"],
        "target_geoid": ["06001400101", "06001400102", "06001400200"],
        "weight": [0.6, 0.4, 1.0],
        "relationship": ["SPLIT", "SPLIT", "IDENTICAL"],
    })


@pytest.fixture
def multi_vintage_crosswalks():
    """Two transitions: 2000→2010 and 2010→2020."""
    cw_2000_2010 = pd.DataFrame({
        "source_geoid": ["0601", "0601", "0602"],
        "target_geoid": ["0601A", "0601B", "0602"],
        "weight": [0.7, 0.3, 1.0],
    })
    cw_2010_2020 = pd.DataFrame({
        "source_geoid": ["0601A", "0601B", "0602"],
        "target_geoid": ["0601X", "0601X", "0602"],
        "weight": [0.5, 0.5, 1.0],
    })
    return [
        (2000, 2010, cw_2000_2010),
        (2010, 2020, cw_2010_2020),
    ]


@pytest.fixture
def fragmented_crosswalk():
    """Crosswalk with a highly fragmented boundary."""
    return pd.DataFrame({
        "source_geoid": ["A", "A", "A", "A", "B"],
        "target_geoid": ["X", "Y", "Z", "W", "V"],
        "weight": [0.25, 0.25, 0.25, 0.25, 1.0],
    })


class TestBoundaryStability:
    """Tests for compute_boundary_stability."""

    def test_simple_split(self, simple_crosswalk):
        from siege_utilities.geo.timeseries.crosswalk_analytics import (
            compute_boundary_stability,
        )

        result = compute_boundary_stability(
            simple_crosswalk, 2010, 2020, "tract"
        )
        assert result.total_source == 2
        assert result.total_target == 3
        assert result.unchanged == 1  # 06001400200
        assert result.split == 1  # 06001400100
        assert result.net_change == 1

    def test_pct_unchanged(self, simple_crosswalk):
        from siege_utilities.geo.timeseries.crosswalk_analytics import (
            compute_boundary_stability,
        )

        result = compute_boundary_stability(
            simple_crosswalk, 2010, 2020, "tract"
        )
        assert result.pct_unchanged == 0.5  # 1 of 2 unchanged
        assert result.churn_rate == 0.5

    def test_empty_crosswalk(self):
        from siege_utilities.geo.timeseries.crosswalk_analytics import (
            compute_boundary_stability,
        )

        result = compute_boundary_stability(
            pd.DataFrame(), 2010, 2020, "tract"
        )
        assert result.total_source == 0
        assert result.total_target == 0
        assert result.pct_unchanged == 0.0

    def test_all_unchanged(self):
        from siege_utilities.geo.timeseries.crosswalk_analytics import (
            compute_boundary_stability,
        )

        df = pd.DataFrame({
            "source_geoid": ["A", "B", "C"],
            "target_geoid": ["A", "B", "C"],
            "weight": [1.0, 1.0, 1.0],
        })
        result = compute_boundary_stability(df, 2010, 2020, "tract")
        assert result.unchanged == 3
        assert result.pct_unchanged == 1.0
        assert result.churn_rate == 0.0

    def test_merged_detection(self):
        from siege_utilities.geo.timeseries.crosswalk_analytics import (
            compute_boundary_stability,
        )

        df = pd.DataFrame({
            "source_geoid": ["A", "B"],
            "target_geoid": ["X", "X"],
            "weight": [0.5, 0.5],
        })
        result = compute_boundary_stability(df, 2010, 2020, "tract")
        assert result.merged == 1  # X receives from A and B


class TestAllocationEfficiency:
    """Tests for compute_allocation_efficiency."""

    def test_perfect_allocation(self):
        from siege_utilities.geo.timeseries.crosswalk_analytics import (
            compute_allocation_efficiency,
        )

        df = pd.DataFrame({
            "source_geoid": ["A", "B"],
            "target_geoid": ["A", "B"],
            "weight": [1.0, 1.0],
        })
        result = compute_allocation_efficiency(df)
        assert result.mean_weight == 1.0
        assert result.pct_above_90 == 1.0
        assert result.n_relationships == 2

    def test_fragmented_allocation(self, fragmented_crosswalk):
        from siege_utilities.geo.timeseries.crosswalk_analytics import (
            compute_allocation_efficiency,
        )

        result = compute_allocation_efficiency(fragmented_crosswalk)
        assert result.n_relationships == 5
        assert result.pct_above_90 == pytest.approx(0.2)  # Only B→V
        assert result.pct_below_10 == 0.0  # All weights are 0.25 or 1.0

    def test_empty(self):
        from siege_utilities.geo.timeseries.crosswalk_analytics import (
            compute_allocation_efficiency,
        )

        result = compute_allocation_efficiency(pd.DataFrame())
        assert result.n_relationships == 0
        assert result.mean_weight == 0.0


class TestReallocationChain:
    """Tests for build_reallocation_chain."""

    def test_single_transition(self, simple_crosswalk):
        from siege_utilities.geo.timeseries.crosswalk_analytics import (
            build_reallocation_chain,
        )

        chain = build_reallocation_chain(
            [(2010, 2020, simple_crosswalk)],
            origin_geoid="06001400100",
        )
        assert chain.origin_geoid == "06001400100"
        assert chain.origin_year == 2010
        assert len(chain.terminal_geoids) == 2
        assert "06001400101" in chain.terminal_geoids
        assert "06001400102" in chain.terminal_geoids

    def test_multi_vintage_chain(self, multi_vintage_crosswalks):
        from siege_utilities.geo.timeseries.crosswalk_analytics import (
            build_reallocation_chain,
        )

        chain = build_reallocation_chain(
            multi_vintage_crosswalks,
            origin_geoid="0601",
        )
        assert chain.origin_year == 2000
        # 0601 → 0601A/0601B → 0601X (both merge to 0601X)
        assert "0601X" in chain.terminal_geoids

    def test_unchanged_geoid(self, multi_vintage_crosswalks):
        from siege_utilities.geo.timeseries.crosswalk_analytics import (
            build_reallocation_chain,
        )

        chain = build_reallocation_chain(
            multi_vintage_crosswalks,
            origin_geoid="0602",
        )
        assert chain.terminal_geoids == ["0602"]

    def test_min_weight_filter(self, multi_vintage_crosswalks):
        from siege_utilities.geo.timeseries.crosswalk_analytics import (
            build_reallocation_chain,
        )

        chain = build_reallocation_chain(
            multi_vintage_crosswalks,
            origin_geoid="0601",
            min_weight=0.2,
        )
        # 0601→0601A (w=0.7) → 0601X (w=0.5) → cumulative 0.35 > 0.2 ✓
        # 0601→0601B (w=0.3) → 0601X (w=0.5) → cumulative 0.15 < 0.2 ✗
        assert "0601X" in chain.terminal_geoids

    def test_empty_crosswalks(self):
        from siege_utilities.geo.timeseries.crosswalk_analytics import (
            build_reallocation_chain,
        )

        chain = build_reallocation_chain([], origin_geoid="X")
        assert chain.terminal_geoids == ["X"]


class TestCompareVintageStability:
    """Tests for compare_vintage_stability."""

    def test_multi_vintage_comparison(self, multi_vintage_crosswalks):
        from siege_utilities.geo.timeseries.crosswalk_analytics import (
            compare_vintage_stability,
        )

        result = compare_vintage_stability(
            multi_vintage_crosswalks, "tract"
        )
        assert len(result) == 2
        assert result.iloc[0]["source_year"] == 2000
        assert result.iloc[1]["source_year"] == 2010
        assert "churn_rate" in result.columns
        assert "mean_weight" in result.columns


class TestIdentifyVolatileBoundaries:
    """Tests for identify_volatile_boundaries."""

    def test_finds_fragmented(self, fragmented_crosswalk):
        from siege_utilities.geo.timeseries.crosswalk_analytics import (
            identify_volatile_boundaries,
        )

        result = identify_volatile_boundaries(fragmented_crosswalk, threshold=0.5)
        assert len(result) == 1  # Only A (max_weight=0.25 < 0.5)
        assert result.iloc[0]["source_geoid"] == "A"
        assert result.iloc[0]["n_targets"] == 4

    def test_top_n(self, fragmented_crosswalk):
        from siege_utilities.geo.timeseries.crosswalk_analytics import (
            identify_volatile_boundaries,
        )

        result = identify_volatile_boundaries(
            fragmented_crosswalk, threshold=1.1, top_n=1
        )
        assert len(result) <= 1

    def test_empty(self):
        from siege_utilities.geo.timeseries.crosswalk_analytics import (
            identify_volatile_boundaries,
        )

        result = identify_volatile_boundaries(pd.DataFrame())
        assert len(result) == 0


class TestColumnNormalization:
    """Tests for handling different column naming conventions."""

    def test_uppercase_columns(self):
        from siege_utilities.geo.timeseries.crosswalk_analytics import (
            compute_boundary_stability,
        )

        df = pd.DataFrame({
            "GEOID_SOURCE": ["A", "B"],
            "GEOID_TARGET": ["X", "Y"],
            "WEIGHT": [1.0, 1.0],
        })
        result = compute_boundary_stability(df, 2010, 2020, "tract")
        assert result.total_source == 2
        assert result.unchanged == 2

    def test_model_field_columns(self):
        from siege_utilities.geo.timeseries.crosswalk_analytics import (
            compute_boundary_stability,
        )

        df = pd.DataFrame({
            "source_boundary_id": ["A", "B"],
            "target_boundary_id": ["X", "Y"],
            "weight": [1.0, 1.0],
        })
        result = compute_boundary_stability(df, 2010, 2020, "tract")
        assert result.total_source == 2

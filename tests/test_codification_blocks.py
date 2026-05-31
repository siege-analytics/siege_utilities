"""Tests for block assignment (SU#628)."""

from __future__ import annotations

import pytest

from siege_utilities.geo.providers.batch_geocoder import GeocodingResult, MatchQuality
from siege_utilities.geo.codification_blocks import (
    BlockAssignment,
    BlockGroup,
    SpreadMetrics,
    assign_blocks,
    compute_spread,
    group_by_block,
)


def _gr(block="B1", tract="T1", county="C1", state="S1",
        lat=41.0, lon=-87.0, matched=True, input_id="0"):
    return GeocodingResult(
        input_address="addr",
        input_id=input_id,
        lat=lat if matched else None,
        lon=lon if matched else None,
        match_quality=MatchQuality.EXACT.value if matched else MatchQuality.NO_MATCH.value,
        block_geoid=block if matched else "",
        tract_geoid=tract if matched else "",
        county_geoid=county if matched else "",
        state_geoid=state if matched else "",
        backend="test",
    )


def _ba(block="B1", tract="T1", county="C1", state="S1",
        lat=41.0, lon=-87.0, input_id="0"):
    return BlockAssignment(
        block_geoid=block, tract_geoid=tract, county_geoid=county,
        state_geoid=state, lat=lat, lon=lon, input_id=input_id,
    )


class TestAssignBlocks:
    def test_empty(self):
        assert assign_blocks([]) == []

    def test_skips_unmatched(self):
        results = [_gr(matched=False)]
        assert assign_blocks(results) == []

    def test_converts_matched(self):
        results = [_gr(block="B1", lat=41.0, lon=-87.0)]
        assignments = assign_blocks(results)
        assert len(assignments) == 1
        assert assignments[0].block_geoid == "B1"
        assert assignments[0].lat == 41.0

    def test_preserves_input_id(self):
        results = [_gr(input_id="MY-ID")]
        assert assign_blocks(results)[0].input_id == "MY-ID"

    def test_multiple(self):
        results = [_gr(block="A"), _gr(block="B"), _gr(matched=False)]
        assert len(assign_blocks(results)) == 2


class TestGroupByBlock:
    def test_empty(self):
        assert group_by_block([]) == []

    def test_single_group(self):
        assignments = [_ba(block="B1"), _ba(block="B1"), _ba(block="B1")]
        groups = group_by_block(assignments)
        assert len(groups) == 1
        assert groups[0].address_count == 3

    def test_multiple_groups(self):
        assignments = [_ba(block="A"), _ba(block="A"), _ba(block="B")]
        groups = group_by_block(assignments)
        assert len(groups) == 2
        assert groups[0].block_geoid == "A"
        assert groups[0].address_count == 2

    def test_sorted_by_count(self):
        assignments = [_ba(block="B"), _ba(block="A"), _ba(block="A"), _ba(block="A")]
        groups = group_by_block(assignments)
        assert groups[0].block_geoid == "A"

    def test_centroid(self):
        assignments = [
            _ba(block="B1", lat=40.0, lon=-86.0),
            _ba(block="B1", lat=42.0, lon=-88.0),
        ]
        groups = group_by_block(assignments)
        assert groups[0].centroid_lat == pytest.approx(41.0)
        assert groups[0].centroid_lon == pytest.approx(-87.0)

    def test_falls_back_to_tract(self):
        assignments = [_ba(block="", tract="T1")]
        groups = group_by_block(assignments)
        assert len(groups) == 1
        assert groups[0].tract_geoid == "T1"


class TestComputeSpread:
    def test_empty(self):
        m = compute_spread([])
        assert m.block_count == 0
        assert m.concentration == 0.0

    def test_single_block(self):
        assignments = [_ba(block="B1"), _ba(block="B1")]
        m = compute_spread(assignments)
        assert m.block_count == 1
        assert m.concentration == pytest.approx(1.0)
        assert m.max_block_pct == pytest.approx(1.0)

    def test_two_equal_blocks(self):
        assignments = [_ba(block="A"), _ba(block="B")]
        m = compute_spread(assignments)
        assert m.block_count == 2
        assert m.concentration == pytest.approx(0.5)
        assert m.max_block_pct == pytest.approx(0.5)

    def test_geographic_counts(self):
        assignments = [
            _ba(block="A1", tract="A", county="X", state="1"),
            _ba(block="A2", tract="A", county="X", state="1"),
            _ba(block="B1", tract="B", county="Y", state="2"),
        ]
        m = compute_spread(assignments)
        assert m.block_count == 3
        assert m.tract_count == 2
        assert m.county_count == 2
        assert m.state_count == 2

    def test_bbox(self):
        assignments = [
            _ba(lat=40.0, lon=-86.0, block="A"),
            _ba(lat=42.0, lon=-88.0, block="B"),
        ]
        m = compute_spread(assignments)
        assert m.bbox_lat_range == pytest.approx(2.0)
        assert m.bbox_lon_range == pytest.approx(2.0)

    def test_accepts_precomputed_groups(self):
        assignments = [_ba(block="A"), _ba(block="B")]
        groups = group_by_block(assignments)
        m = compute_spread(assignments, groups=groups)
        assert m.block_count == 2

    def test_concentration_skewed(self):
        assignments = [_ba(block="A")] * 9 + [_ba(block="B")]
        m = compute_spread(assignments)
        assert m.max_block_pct == pytest.approx(0.9)
        assert m.concentration == pytest.approx(0.82)


# ── Error-path tests ──────────────────────────────────────────────────


class TestAssignBlocksEmptyAndInvalid:
    """assign_blocks() with empty input and unmatched results."""

    def test_empty_list_returns_empty(self):
        result = assign_blocks([])
        assert result == []
        assert isinstance(result, list)

    def test_all_unmatched_returns_empty(self):
        """All geocoding results have no match -- no assignments."""
        results = [
            _gr(matched=False, input_id="1"),
            _gr(matched=False, input_id="2"),
            _gr(matched=False, input_id="3"),
        ]
        assignments = assign_blocks(results)
        assert assignments == []

    def test_mixed_matched_and_no_geocoding_results(self):
        """Only matched results with coordinates become assignments."""
        results = [
            _gr(matched=True, block="B1", input_id="ok"),
            _gr(matched=False, input_id="fail1"),
            _gr(matched=False, input_id="fail2"),
        ]
        assignments = assign_blocks(results)
        assert len(assignments) == 1
        assert assignments[0].input_id == "ok"


class TestComputeSpreadEmpty:
    """compute_spread() with empty assignments."""

    def test_empty_returns_zero_metrics(self):
        m = compute_spread([])
        assert m.block_count == 0
        assert m.tract_count == 0
        assert m.county_count == 0
        assert m.state_count == 0
        assert m.concentration == 0.0
        assert m.max_block_pct == 0.0
        assert m.bbox_lat_range == 0.0
        assert m.bbox_lon_range == 0.0


class TestComputeSpreadSingleBlock:
    """compute_spread() with all assignments to the same block (no spread)."""

    def test_all_same_block_max_concentration(self):
        assignments = [
            _ba(block="B1", tract="T1", county="C1", state="S1", lat=41.0, lon=-87.0),
            _ba(block="B1", tract="T1", county="C1", state="S1", lat=41.0, lon=-87.0),
            _ba(block="B1", tract="T1", county="C1", state="S1", lat=41.0, lon=-87.0),
        ]
        m = compute_spread(assignments)
        assert m.block_count == 1
        assert m.tract_count == 1
        assert m.county_count == 1
        assert m.state_count == 1
        assert m.concentration == pytest.approx(1.0)
        assert m.max_block_pct == pytest.approx(1.0)
        # All at same location, so range is 0
        assert m.bbox_lat_range == pytest.approx(0.0)
        assert m.bbox_lon_range == pytest.approx(0.0)


class TestGroupByBlockDuplicateIds:
    """group_by_block() with multiple assignments sharing the same block GEOID."""

    def test_duplicate_block_ids_aggregated(self):
        assignments = [
            _ba(block="B1", lat=40.0, lon=-86.0, input_id="a1"),
            _ba(block="B1", lat=42.0, lon=-88.0, input_id="a2"),
            _ba(block="B1", lat=41.0, lon=-87.0, input_id="a3"),
        ]
        groups = group_by_block(assignments)
        assert len(groups) == 1
        assert groups[0].block_geoid == "B1"
        assert groups[0].address_count == 3
        assert groups[0].centroid_lat == pytest.approx(41.0)
        assert groups[0].centroid_lon == pytest.approx(-87.0)

    def test_duplicate_ids_across_different_blocks(self):
        """Two blocks that each have duplicate assignments."""
        assignments = [
            _ba(block="X", lat=40.0, lon=-86.0),
            _ba(block="X", lat=40.0, lon=-86.0),
            _ba(block="Y", lat=42.0, lon=-88.0),
            _ba(block="Y", lat=42.0, lon=-88.0),
            _ba(block="Y", lat=42.0, lon=-88.0),
        ]
        groups = group_by_block(assignments)
        assert len(groups) == 2
        # Sorted by count descending, Y has 3, X has 2
        assert groups[0].block_geoid == "Y"
        assert groups[0].address_count == 3
        assert groups[1].block_geoid == "X"
        assert groups[1].address_count == 2

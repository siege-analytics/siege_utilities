"""Tests for core codification function (SU#627)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from siege_utilities.geo.providers.batch_geocoder import (
    BatchGeocodingResult,
    GeocodingResult,
    MatchQuality,
)
from siege_utilities.geo.codification import (
    BlockProfile,
    CodificationResult,
    _build_block_profiles,
    codify_area,
)


def _gr(
    block_geoid="170310101001001",
    tract_geoid="17031010100",
    county_geoid="17031",
    state_geoid="17",
    matched=True,
):
    return GeocodingResult(
        input_address="123 Main St",
        input_id="0",
        lat=41.8781 if matched else None,
        lon=-87.6298 if matched else None,
        match_quality=MatchQuality.EXACT.value if matched else MatchQuality.NO_MATCH.value,
        block_geoid=block_geoid if matched else "",
        tract_geoid=tract_geoid if matched else "",
        county_geoid=county_geoid if matched else "",
        state_geoid=state_geoid if matched else "",
        backend="census",
    )


def _mock_geocoder(results, backend_name="census"):
    geocoder = MagicMock()
    geocoder.backend_name = backend_name
    geocoder.geocode.return_value = BatchGeocodingResult(
        results=results, backend=backend_name,
    )
    return geocoder


# ---------------------------------------------------------------------------
# BlockProfile
# ---------------------------------------------------------------------------


class TestBlockProfile:
    def test_defaults(self):
        b = BlockProfile()
        assert b.block_geoid == ""
        assert b.address_count == 0

    def test_fields(self):
        b = BlockProfile(
            block_geoid="170310101001001",
            tract_geoid="17031010100",
            address_count=42,
        )
        assert b.address_count == 42
        assert b.tract_geoid == "17031010100"


# ---------------------------------------------------------------------------
# CodificationResult
# ---------------------------------------------------------------------------


class TestCodificationResult:
    def test_empty(self):
        r = CodificationResult()
        assert r.block_count == 0
        assert r.tract_count == 0
        assert r.county_count == 0

    def test_counts(self):
        r = CodificationResult(
            blocks=[
                BlockProfile(block_geoid="A1", tract_geoid="A", county_geoid="X", state_geoid="1"),
                BlockProfile(block_geoid="A2", tract_geoid="A", county_geoid="X", state_geoid="1"),
                BlockProfile(block_geoid="B1", tract_geoid="B", county_geoid="Y", state_geoid="2"),
            ],
        )
        assert r.block_count == 3
        assert r.tract_count == 2
        assert r.county_count == 2
        assert r.state_count == 2

    def test_top_blocks(self):
        r = CodificationResult(
            blocks=[
                BlockProfile(block_geoid="A", address_count=10),
                BlockProfile(block_geoid="B", address_count=50),
                BlockProfile(block_geoid="C", address_count=30),
            ],
        )
        top = r.top_blocks(2)
        assert len(top) == 2
        assert top[0].block_geoid == "B"
        assert top[1].block_geoid == "C"

    def test_summarize(self):
        r = CodificationResult(
            total_addresses=100,
            matched_addresses=90,
            match_rate=0.9,
            blocks=[BlockProfile(block_geoid="A", tract_geoid="T", county_geoid="C", state_geoid="S")],
            geocoding_backend="census",
            census_year=2020,
        )
        s = r.summarize()
        assert s["total_addresses"] == 100
        assert s["match_rate"] == 0.9
        assert s["block_count"] == 1
        assert s["geocoding_backend"] == "census"


# ---------------------------------------------------------------------------
# _build_block_profiles
# ---------------------------------------------------------------------------


class TestBuildBlockProfiles:
    def test_empty(self):
        assert _build_block_profiles([]) == []

    def test_single_block(self):
        results = [_gr(), _gr(), _gr()]
        profiles = _build_block_profiles(results)
        assert len(profiles) == 1
        assert profiles[0].address_count == 3
        assert profiles[0].block_geoid == "170310101001001"

    def test_multiple_blocks(self):
        results = [
            _gr(block_geoid="A"),
            _gr(block_geoid="A"),
            _gr(block_geoid="B"),
        ]
        profiles = _build_block_profiles(results)
        assert len(profiles) == 2
        assert profiles[0].address_count == 2
        assert profiles[0].block_geoid == "A"

    def test_sorted_by_count(self):
        results = [
            _gr(block_geoid="B"),
            _gr(block_geoid="A"),
            _gr(block_geoid="A"),
            _gr(block_geoid="A"),
        ]
        profiles = _build_block_profiles(results)
        assert profiles[0].block_geoid == "A"
        assert profiles[0].address_count == 3

    def test_falls_back_to_tract(self):
        results = [_gr(block_geoid="", tract_geoid="T1")]
        profiles = _build_block_profiles(results)
        assert len(profiles) == 1
        assert profiles[0].tract_geoid == "T1"

    def test_preserves_geoid_hierarchy(self):
        results = [_gr()]
        profiles = _build_block_profiles(results)
        assert profiles[0].state_geoid == "17"
        assert profiles[0].county_geoid == "17031"
        assert profiles[0].tract_geoid == "17031010100"


# ---------------------------------------------------------------------------
# codify_area
# ---------------------------------------------------------------------------


class TestCodifyArea:
    def test_empty_addresses(self):
        result = codify_area([])
        assert result.total_addresses == 0
        assert result.block_count == 0

    def test_no_geocoder_uses_default(self):
        result = codify_area(["123 Main St"], geocoder=None)
        assert result.geocoding_backend in ("census", "")
        assert result.total_addresses == 1

    def test_basic_codification(self):
        geocoder = _mock_geocoder([
            _gr(block_geoid="A"),
            _gr(block_geoid="A"),
            _gr(block_geoid="B"),
        ])
        result = codify_area(["a", "b", "c"], geocoder=geocoder)

        assert result.total_addresses == 3
        assert result.matched_addresses == 3
        assert result.match_rate == 1.0
        assert result.block_count == 2
        assert result.geocoding_backend == "census"

    def test_partial_match(self):
        geocoder = _mock_geocoder([
            _gr(matched=True),
            _gr(matched=False),
        ])
        result = codify_area(["a", "b"], geocoder=geocoder)

        assert result.total_addresses == 2
        assert result.matched_addresses == 1
        assert result.match_rate == 0.5

    def test_geocoder_exception(self):
        geocoder = MagicMock()
        geocoder.backend_name = "test"
        geocoder.geocode.side_effect = RuntimeError("API down")

        result = codify_area(["a"], geocoder=geocoder)
        assert len(result.errors) == 1
        assert "Geocoding failed" in result.errors[0]

    def test_census_year_passed_through(self):
        geocoder = _mock_geocoder([_gr()])
        result = codify_area(["a"], geocoder=geocoder, census_year=2020)
        assert result.census_year == 2020

    def test_multiple_blocks_and_tracts(self):
        geocoder = _mock_geocoder([
            _gr(block_geoid="A1", tract_geoid="A", county_geoid="X", state_geoid="1"),
            _gr(block_geoid="A2", tract_geoid="A", county_geoid="X", state_geoid="1"),
            _gr(block_geoid="B1", tract_geoid="B", county_geoid="Y", state_geoid="2"),
        ])
        result = codify_area(["a", "b", "c"], geocoder=geocoder)

        assert result.block_count == 3
        assert result.tract_count == 2
        assert result.county_count == 2

    def test_summarize_integration(self):
        geocoder = _mock_geocoder([_gr()])
        result = codify_area(["a"], geocoder=geocoder, census_year=2020)
        summary = result.summarize()
        assert summary["total_addresses"] == 1
        assert summary["census_year"] == 2020

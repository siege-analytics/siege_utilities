"""Tests for demographic enrichment (SU#629)."""

from __future__ import annotations

import pytest

from siege_utilities.geo.codification_demographics import (
    BlockDemographics,
    DemographicSignature,
    DictBlockDemographicsProvider,
    compute_demographic_signature,
)


def _bd(block="B1", pop=1000, vap=750, white=600, black=200,
        hispanic=100, asian=50, other=50,
        housing_total=400, housing_occupied=360, housing_vacant=40):
    return BlockDemographics(
        block_geoid=block,
        total_population=pop,
        voting_age_population=vap,
        white=white, black=black, hispanic=hispanic,
        asian=asian, other_race=other,
        housing_total=housing_total,
        housing_occupied=housing_occupied,
        housing_vacant=housing_vacant,
    )


class TestBlockDemographics:
    def test_defaults(self):
        d = BlockDemographics()
        assert d.total_population == 0

    def test_fields(self):
        d = _bd(pop=5000)
        assert d.total_population == 5000


class TestDictBlockDemographicsProvider:
    def test_empty(self):
        p = DictBlockDemographicsProvider()
        assert p.get_demographics(["B1"]) == {}

    def test_add_and_get(self):
        p = DictBlockDemographicsProvider()
        p.add(_bd(block="B1"))
        result = p.get_demographics(["B1"])
        assert "B1" in result

    def test_missing_blocks(self):
        p = DictBlockDemographicsProvider()
        p.add(_bd(block="B1"))
        result = p.get_demographics(["B1", "B2"])
        assert len(result) == 1


class TestComputeDemographicSignature:
    def test_empty(self):
        sig = compute_demographic_signature({}, {})
        assert sig.weighted_blocks == 0
        assert sig.pct_white == 0.0

    def test_single_block(self):
        counts = {"B1": 10}
        demos = {"B1": _bd(pop=1000, white=600, black=200, hispanic=100, asian=50, other=50)}
        sig = compute_demographic_signature(counts, demos)
        assert sig.weighted_blocks == 1
        assert sig.pct_white == pytest.approx(0.6)
        assert sig.pct_black == pytest.approx(0.2)
        assert sig.pct_hispanic == pytest.approx(0.1)

    def test_address_weighted(self):
        counts = {"B1": 9, "B2": 1}
        demos = {
            "B1": _bd(block="B1", pop=1000, white=1000, black=0, hispanic=0, asian=0, other=0),
            "B2": _bd(block="B2", pop=1000, white=0, black=1000, hispanic=0, asian=0, other=0),
        }
        sig = compute_demographic_signature(counts, demos)
        assert sig.pct_white == pytest.approx(0.9)
        assert sig.pct_black == pytest.approx(0.1)

    def test_skips_zero_population(self):
        counts = {"B1": 10, "B2": 5}
        demos = {
            "B1": _bd(block="B1", pop=1000, white=500),
            "B2": _bd(block="B2", pop=0),
        }
        sig = compute_demographic_signature(counts, demos)
        assert sig.weighted_blocks == 1

    def test_skips_missing_demographics(self):
        counts = {"B1": 10, "B2": 5}
        demos = {"B1": _bd(block="B1")}
        sig = compute_demographic_signature(counts, demos)
        assert sig.weighted_blocks == 1

    def test_voting_age(self):
        counts = {"B1": 10}
        demos = {"B1": _bd(pop=1000, vap=750)}
        sig = compute_demographic_signature(counts, demos)
        assert sig.pct_voting_age == pytest.approx(0.75)

    def test_housing(self):
        counts = {"B1": 10}
        demos = {"B1": _bd(housing_total=400, housing_occupied=360, housing_vacant=40)}
        sig = compute_demographic_signature(counts, demos)
        assert sig.pct_housing_occupied == pytest.approx(0.9)
        assert sig.pct_housing_vacant == pytest.approx(0.1)

    def test_total_population(self):
        counts = {"B1": 5, "B2": 5}
        demos = {
            "B1": _bd(block="B1", pop=1000),
            "B2": _bd(block="B2", pop=2000),
        }
        sig = compute_demographic_signature(counts, demos)
        assert sig.total_block_population == 3000

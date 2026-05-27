"""Tests for summary portrait (SU#632)."""

from __future__ import annotations

import pytest

from siege_utilities.geo.codification import BlockProfile, CodificationResult
from siege_utilities.geo.codification_blocks import BlockGroup, SpreadMetrics
from siege_utilities.geo.codification_demographics import DemographicSignature
from siege_utilities.geo.codification_urbanicity import UrbanicityDistribution
from siege_utilities.geo.codification_recency import RecencyAnalysis
from siege_utilities.geo.codification_summary import AreaPortrait, build_portrait


def _spread(**kw):
    defaults = dict(
        block_count=5, tract_count=3, county_count=2, state_count=1,
        concentration=0.45, max_block_pct=0.30,
    )
    defaults.update(kw)
    return SpreadMetrics(**defaults)


def _demographics(**kw):
    defaults = dict(
        total_block_population=5000, weighted_blocks=5,
        pct_white=0.55, pct_black=0.20, pct_hispanic=0.15,
        pct_asian=0.05, pct_other=0.05,
        pct_voting_age=0.72, pct_housing_occupied=0.90,
        pct_housing_vacant=0.10,
    )
    defaults.update(kw)
    return DemographicSignature(**defaults)


def _urbanicity(**kw):
    defaults = dict(
        total_classified=100,
        distribution={"11": 0.7, "21": 0.3},
        category_distribution={"city": 0.7, "suburb": 0.3},
        dominant_locale="11",
        dominant_category="city",
    )
    defaults.update(kw)
    return UrbanicityDistribution(**defaults)


def _recency(**kw):
    defaults = dict(
        total_analyzed=50,
        vintage_distribution={2016: 20, 2020: 30},
        vintage_pct={2016: 0.4, 2020: 0.6},
        new_construction_count=30,
        new_construction_pct=0.6,
        median_vintage=2020,
    )
    defaults.update(kw)
    return RecencyAnalysis(**defaults)


def _codification_result(n_blocks=3):
    blocks = [
        BlockProfile(
            block_geoid=f"48045300{i:02d}001{i:03d}",
            tract_geoid=f"48045300{i:02d}00",
            county_geoid=f"4804{i}",
            state_geoid="48",
            address_count=(n_blocks - i) * 10,
        )
        for i in range(n_blocks)
    ]
    return CodificationResult(
        total_addresses=sum(b.address_count for b in blocks),
        matched_addresses=sum(b.address_count for b in blocks),
        match_rate=1.0,
        blocks=blocks,
        geocoding_backend="test",
        census_year=2020,
    )


class TestAreaPortraitDefaults:
    def test_empty_portrait(self):
        p = AreaPortrait()
        assert p.geocoding_summary == {}
        assert p.spread is None
        assert p.demographics is None
        assert p.urbanicity is None
        assert p.recency is None
        assert p.top_blocks == []

    def test_headline_metrics_empty(self):
        p = AreaPortrait()
        assert p.headline_metrics() == {}

    def test_to_dict_empty(self):
        d = AreaPortrait().to_dict()
        assert d == {"geocoding": {}}


class TestHeadlineMetrics:
    def test_spread_metrics(self):
        p = AreaPortrait(spread=_spread())
        m = p.headline_metrics()
        assert m["block_count"] == 5
        assert m["tract_count"] == 3
        assert m["county_count"] == 2
        assert m["concentration"] == 0.45

    def test_demographic_metrics(self):
        p = AreaPortrait(demographics=_demographics())
        m = p.headline_metrics()
        assert m["pct_white"] == 0.55
        assert m["pct_black"] == 0.2
        assert m["pct_hispanic"] == 0.15
        assert m["pct_voting_age"] == 0.72

    def test_urbanicity_metrics(self):
        p = AreaPortrait(urbanicity=_urbanicity())
        m = p.headline_metrics()
        assert m["dominant_category"] == "city"
        assert m["dominant_locale"] == "11"

    def test_recency_metrics(self):
        p = AreaPortrait(recency=_recency())
        m = p.headline_metrics()
        assert m["median_vintage"] == 2020
        assert m["new_construction_pct"] == 0.6

    def test_all_layers(self):
        p = AreaPortrait(
            geocoding_summary={"total_addresses": 100},
            spread=_spread(),
            demographics=_demographics(),
            urbanicity=_urbanicity(),
            recency=_recency(),
        )
        m = p.headline_metrics()
        assert m["total_addresses"] == 100
        assert "block_count" in m
        assert "pct_white" in m
        assert "dominant_category" in m
        assert "median_vintage" in m

    def test_rounding(self):
        p = AreaPortrait(
            spread=_spread(concentration=0.33333),
            demographics=_demographics(pct_white=0.55555),
            recency=_recency(new_construction_pct=0.66666),
        )
        m = p.headline_metrics()
        assert m["concentration"] == 0.333
        assert m["pct_white"] == 0.556
        assert m["new_construction_pct"] == 0.667


class TestToDict:
    def test_spread_section(self):
        p = AreaPortrait(spread=_spread())
        d = p.to_dict()
        assert d["spread"]["block_count"] == 5
        assert d["spread"]["state_count"] == 1
        assert d["spread"]["max_block_pct"] == 0.30

    def test_demographics_section(self):
        p = AreaPortrait(demographics=_demographics())
        d = p.to_dict()
        assert d["demographics"]["total_block_population"] == 5000
        assert d["demographics"]["pct_asian"] == 0.05
        assert d["demographics"]["pct_housing_occupied"] == 0.90
        assert d["demographics"]["pct_housing_vacant"] == 0.10

    def test_urbanicity_section(self):
        p = AreaPortrait(urbanicity=_urbanicity())
        d = p.to_dict()
        assert d["urbanicity"]["dominant_locale"] == "11"
        assert d["urbanicity"]["distribution"] == {"11": 0.7, "21": 0.3}
        assert d["urbanicity"]["category_distribution"] == {"city": 0.7, "suburb": 0.3}

    def test_recency_section(self):
        p = AreaPortrait(recency=_recency())
        d = p.to_dict()
        assert d["recency"]["total_analyzed"] == 50
        assert d["recency"]["vintage_distribution"] == {2016: 20, 2020: 30}

    def test_top_blocks_section(self):
        blocks = [
            BlockGroup(block_geoid="B1", tract_geoid="T1", address_count=10),
            BlockGroup(block_geoid="B2", tract_geoid="T2", address_count=5),
        ]
        p = AreaPortrait(top_blocks=blocks)
        d = p.to_dict()
        assert len(d["top_blocks"]) == 2
        assert d["top_blocks"][0]["block_geoid"] == "B1"
        assert d["top_blocks"][0]["address_count"] == 10

    def test_no_optional_sections(self):
        p = AreaPortrait(geocoding_summary={"test": True})
        d = p.to_dict()
        assert d == {"geocoding": {"test": True}}
        assert "spread" not in d
        assert "demographics" not in d
        assert "urbanicity" not in d
        assert "recency" not in d
        assert "top_blocks" not in d


class TestBuildPortrait:
    def test_basic(self):
        cr = _codification_result(3)
        p = build_portrait(cr)
        assert p.geocoding_summary["total_addresses"] == cr.total_addresses
        assert len(p.top_blocks) == 3

    def test_top_n_limit(self):
        cr = _codification_result(5)
        p = build_portrait(cr, top_n=2)
        assert len(p.top_blocks) == 2
        assert p.top_blocks[0].address_count >= p.top_blocks[1].address_count

    def test_enrichment_passthrough(self):
        cr = _codification_result()
        s = _spread()
        d = _demographics()
        u = _urbanicity()
        r = _recency()
        p = build_portrait(cr, spread=s, demographics=d, urbanicity=u, recency=r)
        assert p.spread is s
        assert p.demographics is d
        assert p.urbanicity is u
        assert p.recency is r

    def test_empty_codification(self):
        cr = CodificationResult()
        p = build_portrait(cr)
        assert p.top_blocks == []
        assert p.geocoding_summary == cr.summarize()

    def test_block_ordering(self):
        cr = _codification_result(5)
        p = build_portrait(cr, top_n=5)
        counts = [b.address_count for b in p.top_blocks]
        assert counts == sorted(counts, reverse=True)

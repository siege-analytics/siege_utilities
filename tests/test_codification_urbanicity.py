"""Tests for urbanicity enrichment (SU#630)."""

from __future__ import annotations

import pytest

from siege_utilities.geo.codification_urbanicity import (
    BlockLocale,
    DictBlockLocaleProvider,
    UrbanicityDistribution,
    compute_urbanicity_distribution,
)


def _bl(block="B1", code="11", label="City-Large", category="city"):
    return BlockLocale(block_geoid=block, locale_code=code,
                       locale_label=label, category=category)


class TestBlockLocale:
    def test_defaults(self):
        b = BlockLocale()
        assert b.locale_code == ""

    def test_fields(self):
        b = _bl()
        assert b.locale_code == "11"
        assert b.category == "city"


class TestDictBlockLocaleProvider:
    def test_empty(self):
        p = DictBlockLocaleProvider()
        assert p.classify_blocks(["B1"]) == {}

    def test_add_and_get(self):
        p = DictBlockLocaleProvider()
        p.add(_bl(block="B1"))
        assert "B1" in p.classify_blocks(["B1"])


class TestComputeUrbanicityDistribution:
    def test_empty(self):
        d = compute_urbanicity_distribution({}, {})
        assert d.total_classified == 0

    def test_single_locale(self):
        counts = {"B1": 10}
        locales = {"B1": _bl(code="11", category="city")}
        d = compute_urbanicity_distribution(counts, locales)
        assert d.total_classified == 10
        assert d.distribution["11"] == pytest.approx(1.0)
        assert d.dominant_locale == "11"
        assert d.dominant_category == "city"

    def test_mixed_locales(self):
        counts = {"B1": 7, "B2": 3}
        locales = {
            "B1": _bl(block="B1", code="11", category="city"),
            "B2": _bl(block="B2", code="21", category="suburb"),
        }
        d = compute_urbanicity_distribution(counts, locales)
        assert d.distribution["11"] == pytest.approx(0.7)
        assert d.distribution["21"] == pytest.approx(0.3)
        assert d.category_distribution["city"] == pytest.approx(0.7)
        assert d.dominant_locale == "11"

    def test_skips_unclassified(self):
        counts = {"B1": 10, "B2": 5}
        locales = {"B1": _bl(block="B1")}
        d = compute_urbanicity_distribution(counts, locales)
        assert d.total_classified == 10

    def test_same_category_different_codes(self):
        counts = {"B1": 5, "B2": 5}
        locales = {
            "B1": _bl(block="B1", code="11", category="city"),
            "B2": _bl(block="B2", code="12", category="city"),
        }
        d = compute_urbanicity_distribution(counts, locales)
        assert d.category_distribution["city"] == pytest.approx(1.0)
        assert len(d.distribution) == 2

"""Tests for urbanicity overlay (SU#611)."""

from __future__ import annotations

import pytest

from siege_utilities.geo.overlay_registry import PlaceHistoryOverlay
from siege_utilities.geo.overlays.urbanicity import (
    DictUrbanicityProvider,
    UrbanicityOverlay,
    UrbanicityOverlayResult,
    UrbanicityPoint,
)


def _up(year=2020, geoid="17031010100", locale_code="11",
        locale_label="City-Large", category="city", size="large"):
    return UrbanicityPoint(
        year=year, geoid=geoid, locale_code=locale_code,
        locale_label=locale_label, category=category, size=size,
    )


# ---------------------------------------------------------------------------
# UrbanicityPoint
# ---------------------------------------------------------------------------


class TestUrbanicityPoint:
    def test_defaults(self):
        p = UrbanicityPoint()
        assert p.year == 0
        assert p.locale_code == ""

    def test_fields(self):
        p = _up()
        assert p.locale_code == "11"
        assert p.category == "city"


# ---------------------------------------------------------------------------
# UrbanicityOverlayResult
# ---------------------------------------------------------------------------


class TestUrbanicityOverlayResult:
    def test_empty(self):
        r = UrbanicityOverlayResult(geoid="A")
        assert not r.has_data
        assert r.years == []
        assert r.current_category == ""

    def test_years(self):
        r = UrbanicityOverlayResult(
            geoid="A",
            classifications=[_up(year=2000), _up(year=2020), _up(year=2010)],
        )
        assert r.years == [2000, 2010, 2020]

    def test_for_year(self):
        r = UrbanicityOverlayResult(
            geoid="A", classifications=[_up(year=2010), _up(year=2020)],
        )
        assert r.for_year(2020).year == 2020
        assert r.for_year(2015) is None

    def test_changed_true(self):
        r = UrbanicityOverlayResult(
            geoid="A",
            classifications=[
                _up(year=2010, locale_code="11"),
                _up(year=2020, locale_code="21"),
            ],
        )
        assert r.changed

    def test_changed_false(self):
        r = UrbanicityOverlayResult(
            geoid="A",
            classifications=[
                _up(year=2010, locale_code="11"),
                _up(year=2020, locale_code="11"),
            ],
        )
        assert not r.changed

    def test_current_category(self):
        r = UrbanicityOverlayResult(
            geoid="A",
            classifications=[
                _up(year=2010, category="city"),
                _up(year=2020, category="suburb"),
            ],
        )
        assert r.current_category == "suburb"

    def test_has_data(self):
        r = UrbanicityOverlayResult(geoid="A", classifications=[_up()])
        assert r.has_data


# ---------------------------------------------------------------------------
# DictUrbanicityProvider
# ---------------------------------------------------------------------------


class TestDictUrbanicityProvider:
    def test_empty(self):
        p = DictUrbanicityProvider()
        assert p.classify("A", 2020) is None

    def test_add_and_classify(self):
        p = DictUrbanicityProvider()
        p.add(_up(geoid="A", year=2020))
        result = p.classify("A", 2020)
        assert result is not None
        assert result.locale_code == "11"

    def test_wrong_geoid(self):
        p = DictUrbanicityProvider()
        p.add(_up(geoid="A", year=2020))
        assert p.classify("B", 2020) is None

    def test_wrong_year(self):
        p = DictUrbanicityProvider()
        p.add(_up(geoid="A", year=2020))
        assert p.classify("A", 2010) is None


# ---------------------------------------------------------------------------
# UrbanicityOverlay
# ---------------------------------------------------------------------------


class TestUrbanicityOverlay:
    def test_is_overlay(self):
        o = UrbanicityOverlay(provider=DictUrbanicityProvider())
        assert isinstance(o, PlaceHistoryOverlay)
        assert o.name == "urbanicity"

    def test_fetch_single_vintage(self):
        p = DictUrbanicityProvider()
        p.add(_up(geoid="A", year=2020))
        o = UrbanicityOverlay(provider=p)
        result = o.fetch("A", 2015, 2025)
        assert len(result.classifications) == 1

    def test_fetch_multiple_vintages(self):
        p = DictUrbanicityProvider()
        p.add(_up(geoid="A", year=2000))
        p.add(_up(geoid="A", year=2010))
        p.add(_up(geoid="A", year=2020))
        o = UrbanicityOverlay(provider=p)
        result = o.fetch("A", 1995, 2025)
        assert len(result.classifications) == 3

    def test_fetch_filters_by_range(self):
        p = DictUrbanicityProvider()
        p.add(_up(geoid="A", year=2000))
        p.add(_up(geoid="A", year=2010))
        p.add(_up(geoid="A", year=2020))
        o = UrbanicityOverlay(provider=p)
        result = o.fetch("A", 2005, 2015)
        assert len(result.classifications) == 1
        assert result.classifications[0].year == 2010

    def test_fetch_empty(self):
        p = DictUrbanicityProvider()
        o = UrbanicityOverlay(provider=p)
        result = o.fetch("A", 2000, 2020)
        assert not result.has_data

    def test_no_provider_raises(self):
        o = UrbanicityOverlay(provider=None)
        with pytest.raises(RuntimeError, match="No urbanicity data provider"):
            o.fetch("A", 2000, 2020)

    def test_reverse_year_range(self):
        p = DictUrbanicityProvider()
        p.add(_up(geoid="A", year=2010))
        o = UrbanicityOverlay(provider=p)
        result = o.fetch("A", 2020, 2005)
        assert len(result.classifications) == 1

    def test_custom_vintage_years(self):
        p = DictUrbanicityProvider()
        p.add(_up(geoid="A", year=2015))
        o = UrbanicityOverlay(provider=p, vintage_years=[2005, 2015, 2025])
        result = o.fetch("A", 2010, 2020)
        assert len(result.classifications) == 1

    def test_sorted_output(self):
        p = DictUrbanicityProvider()
        p.add(_up(geoid="A", year=2020))
        p.add(_up(geoid="A", year=2010))
        p.add(_up(geoid="A", year=2000))
        o = UrbanicityOverlay(provider=p)
        result = o.fetch("A", 1995, 2025)
        years = [c.year for c in result.classifications]
        assert years == [2000, 2010, 2020]

    def test_missing_vintage_skipped(self):
        p = DictUrbanicityProvider()
        p.add(_up(geoid="A", year=2010))
        o = UrbanicityOverlay(provider=p)
        result = o.fetch("A", 1995, 2025)
        assert len(result.classifications) == 1

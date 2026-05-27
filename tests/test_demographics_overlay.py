"""Tests for demographics overlay (SU#610)."""

from __future__ import annotations

import pytest

from siege_utilities.geo.overlay_registry import PlaceHistoryOverlay
from siege_utilities.geo.overlays.demographics import (
    DemographicPoint,
    DemographicsOverlay,
    DemographicsOverlayResult,
    DictDemographicsProvider,
)


def _dp(year=2020, geoid="17031010100", dataset="acs5",
        total_population=5000, median_household_income=65000.0,
        median_age=35.0, values=None):
    return DemographicPoint(
        year=year, geoid=geoid, dataset=dataset,
        total_population=total_population,
        median_household_income=median_household_income,
        median_age=median_age,
        values=values or {},
    )


# ---------------------------------------------------------------------------
# DemographicPoint
# ---------------------------------------------------------------------------


class TestDemographicPoint:
    def test_defaults(self):
        p = DemographicPoint()
        assert p.year == 0
        assert p.total_population is None

    def test_fields(self):
        p = _dp()
        assert p.year == 2020
        assert p.total_population == 5000
        assert p.dataset == "acs5"


# ---------------------------------------------------------------------------
# DemographicsOverlayResult
# ---------------------------------------------------------------------------


class TestDemographicsOverlayResult:
    def test_empty(self):
        r = DemographicsOverlayResult(geoid="A")
        assert not r.has_data
        assert r.years == []

    def test_years(self):
        r = DemographicsOverlayResult(
            geoid="A",
            time_series=[_dp(year=2010), _dp(year=2020), _dp(year=2015)],
        )
        assert r.years == [2010, 2015, 2020]

    def test_for_year(self):
        r = DemographicsOverlayResult(
            geoid="A",
            time_series=[_dp(year=2010), _dp(year=2020)],
        )
        assert len(r.for_year(2020)) == 1
        assert len(r.for_year(2015)) == 0

    def test_population_series(self):
        r = DemographicsOverlayResult(
            geoid="A",
            time_series=[
                _dp(year=2010, total_population=4000),
                _dp(year=2020, total_population=5000),
            ],
        )
        series = r.population_series()
        assert series == [(2010, 4000), (2020, 5000)]

    def test_population_series_skips_none(self):
        r = DemographicsOverlayResult(
            geoid="A",
            time_series=[
                _dp(year=2010, total_population=None),
                _dp(year=2020, total_population=5000),
            ],
        )
        assert len(r.population_series()) == 1

    def test_has_data(self):
        r = DemographicsOverlayResult(
            geoid="A", time_series=[_dp()],
        )
        assert r.has_data


# ---------------------------------------------------------------------------
# DictDemographicsProvider
# ---------------------------------------------------------------------------


class TestDictDemographicsProvider:
    def test_empty(self):
        p = DictDemographicsProvider()
        assert p.get_snapshots("A", 2000, 2020) == []

    def test_add_and_get(self):
        p = DictDemographicsProvider()
        p.add(_dp(geoid="A", year=2020))
        results = p.get_snapshots("A", 2018, 2022)
        assert len(results) == 1

    def test_geoid_filtering(self):
        p = DictDemographicsProvider()
        p.add(_dp(geoid="A", year=2020))
        p.add(_dp(geoid="B", year=2020))
        assert len(p.get_snapshots("A", 2018, 2022)) == 1

    def test_year_range_filtering(self):
        p = DictDemographicsProvider()
        p.add(_dp(geoid="A", year=2010))
        p.add(_dp(geoid="A", year=2015))
        p.add(_dp(geoid="A", year=2020))
        assert len(p.get_snapshots("A", 2012, 2018)) == 1

    def test_dataset_filtering(self):
        p = DictDemographicsProvider()
        p.add(_dp(geoid="A", year=2020, dataset="acs5"))
        p.add(_dp(geoid="A", year=2020, dataset="dec"))
        assert len(p.get_snapshots("A", 2018, 2022, dataset="acs5")) == 1

    def test_sorted_by_year(self):
        p = DictDemographicsProvider()
        p.add(_dp(geoid="A", year=2020))
        p.add(_dp(geoid="A", year=2010))
        results = p.get_snapshots("A", 2005, 2025)
        assert results[0].year == 2010
        assert results[1].year == 2020

    def test_reverse_year_range(self):
        p = DictDemographicsProvider()
        p.add(_dp(geoid="A", year=2015))
        results = p.get_snapshots("A", 2020, 2010)
        assert len(results) == 1


# ---------------------------------------------------------------------------
# DemographicsOverlay
# ---------------------------------------------------------------------------


class TestDemographicsOverlay:
    def test_is_overlay(self):
        o = DemographicsOverlay(provider=DictDemographicsProvider())
        assert isinstance(o, PlaceHistoryOverlay)
        assert o.name == "demographics"

    def test_fetch_single_geoid(self):
        p = DictDemographicsProvider()
        p.add(_dp(geoid="A", year=2020))
        o = DemographicsOverlay(provider=p)
        result = o.fetch("A", 2018, 2022)
        assert result.geoid == "A"
        assert len(result.time_series) == 1
        assert result.geoids_queried == ["A"]

    def test_fetch_empty(self):
        p = DictDemographicsProvider()
        o = DemographicsOverlay(provider=p)
        result = o.fetch("A", 2000, 2020)
        assert not result.has_data

    def test_no_provider_raises(self):
        o = DemographicsOverlay(provider=None)
        with pytest.raises(RuntimeError, match="No demographics data provider"):
            o.fetch("A", 2000, 2020)

    def test_with_terminal_geoids(self):
        p = DictDemographicsProvider()
        p.add(_dp(geoid="A", year=2010))
        p.add(_dp(geoid="B", year=2020))
        o = DemographicsOverlay(provider=p)
        result = o.fetch("A", 2005, 2025, terminal_geoids=["B"])
        assert len(result.time_series) == 2
        assert set(result.geoids_queried) == {"A", "B"}

    def test_deduplicates_geoids(self):
        p = DictDemographicsProvider()
        p.add(_dp(geoid="A", year=2020))
        o = DemographicsOverlay(provider=p)
        result = o.fetch("A", 2018, 2022, terminal_geoids=["A", "A"])
        assert result.geoids_queried == ["A"]

    def test_dataset_filter(self):
        p = DictDemographicsProvider()
        p.add(_dp(geoid="A", year=2020, dataset="acs5"))
        p.add(_dp(geoid="A", year=2020, dataset="dec"))
        o = DemographicsOverlay(provider=p, dataset="acs5")
        result = o.fetch("A", 2018, 2022)
        assert len(result.time_series) == 1
        assert result.time_series[0].dataset == "acs5"

    def test_sorted_output(self):
        p = DictDemographicsProvider()
        p.add(_dp(geoid="B", year=2020))
        p.add(_dp(geoid="A", year=2010))
        o = DemographicsOverlay(provider=p)
        result = o.fetch("A", 2005, 2025, terminal_geoids=["B"])
        assert result.time_series[0].year == 2010
        assert result.time_series[1].year == 2020

    def test_multi_year_timeline(self):
        p = DictDemographicsProvider()
        for yr in [2010, 2012, 2015, 2018, 2020]:
            p.add(_dp(geoid="A", year=yr, total_population=yr * 2))
        o = DemographicsOverlay(provider=p)
        result = o.fetch("A", 2010, 2020)
        assert len(result.time_series) == 5
        series = result.population_series()
        assert len(series) == 5
        assert series[0] == (2010, 4020)

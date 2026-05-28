"""Tests for events overlay (SU#612)."""

from __future__ import annotations

from datetime import date

import pytest

from siege_utilities.geo.overlay_registry import PlaceHistoryOverlay
from siege_utilities.geo.overlays.events import (
    DictEventsProvider,
    EventRecord,
    EventsOverlay,
    EventsOverlayResult,
)


def _er(
    event_id="EVT-1",
    event_type="court_ruling",
    title="Redistricting ruling",
    event_date=date(2020, 6, 15),
    geoids_affected=None,
    end_date=None,
):
    return EventRecord(
        event_id=event_id,
        event_type=event_type,
        title=title,
        date=event_date,
        end_date=end_date,
        geoids_affected=geoids_affected or ["17031010100"],
    )


# ---------------------------------------------------------------------------
# EventRecord
# ---------------------------------------------------------------------------


class TestEventRecord:
    def test_defaults(self):
        e = EventRecord()
        assert e.event_id == ""
        assert e.year == 0
        assert not e.has_duration

    def test_year(self):
        e = _er(event_date=date(2020, 3, 1))
        assert e.year == 2020

    def test_has_duration(self):
        e = _er(event_date=date(2020, 1, 1), end_date=date(2020, 12, 31))
        assert e.has_duration

    def test_no_duration(self):
        e = _er(end_date=None)
        assert not e.has_duration


# ---------------------------------------------------------------------------
# EventsOverlayResult
# ---------------------------------------------------------------------------


class TestEventsOverlayResult:
    def test_empty(self):
        r = EventsOverlayResult(geoid="A")
        assert not r.has_events
        assert r.count == 0
        assert r.event_types == []

    def test_has_events(self):
        r = EventsOverlayResult(geoid="A", events=[_er()])
        assert r.has_events
        assert r.count == 1

    def test_event_types(self):
        r = EventsOverlayResult(
            geoid="A",
            events=[
                _er(event_type="court_ruling"),
                _er(event_type="natural_disaster"),
                _er(event_type="court_ruling"),
            ],
        )
        assert r.event_types == ["court_ruling", "natural_disaster"]

    def test_for_type(self):
        r = EventsOverlayResult(
            geoid="A",
            events=[
                _er(event_type="court_ruling", event_id="1"),
                _er(event_type="natural_disaster", event_id="2"),
                _er(event_type="court_ruling", event_id="3"),
            ],
        )
        rulings = r.for_type("court_ruling")
        assert len(rulings) == 2


# ---------------------------------------------------------------------------
# DictEventsProvider
# ---------------------------------------------------------------------------


class TestDictEventsProvider:
    def test_empty(self):
        p = DictEventsProvider()
        assert p.get_events("A", 2000, 2020) == []

    def test_add_and_get(self):
        p = DictEventsProvider()
        p.add(_er(geoids_affected=["A"]))
        results = p.get_events("A", 2018, 2022)
        assert len(results) == 1

    def test_geoid_filtering(self):
        p = DictEventsProvider()
        p.add(_er(geoids_affected=["A"]))
        assert len(p.get_events("B", 2018, 2022)) == 0

    def test_year_range_filtering(self):
        p = DictEventsProvider()
        p.add(_er(event_date=date(2015, 1, 1), geoids_affected=["A"]))
        p.add(_er(event_date=date(2020, 1, 1), geoids_affected=["A"]))
        assert len(p.get_events("A", 2018, 2022)) == 1

    def test_event_type_filtering(self):
        p = DictEventsProvider()
        p.add(_er(event_type="court_ruling", geoids_affected=["A"]))
        p.add(_er(event_type="natural_disaster", geoids_affected=["A"]))
        results = p.get_events("A", 2018, 2022, event_types=["court_ruling"])
        assert len(results) == 1

    def test_sorted_by_date(self):
        p = DictEventsProvider()
        p.add(_er(event_date=date(2020, 12, 1), event_id="2", geoids_affected=["A"]))
        p.add(_er(event_date=date(2020, 1, 1), event_id="1", geoids_affected=["A"]))
        results = p.get_events("A", 2019, 2021)
        assert results[0].event_id == "1"
        assert results[1].event_id == "2"

    def test_reverse_year_range(self):
        p = DictEventsProvider()
        p.add(_er(event_date=date(2015, 1, 1), geoids_affected=["A"]))
        results = p.get_events("A", 2020, 2010)
        assert len(results) == 1

    def test_multi_geoid_event(self):
        p = DictEventsProvider()
        p.add(_er(geoids_affected=["A", "B", "C"]))
        assert len(p.get_events("A", 2018, 2022)) == 1
        assert len(p.get_events("B", 2018, 2022)) == 1
        assert len(p.get_events("D", 2018, 2022)) == 0


# ---------------------------------------------------------------------------
# EventsOverlay
# ---------------------------------------------------------------------------


class TestEventsOverlay:
    def test_is_overlay(self):
        o = EventsOverlay(provider=DictEventsProvider())
        assert isinstance(o, PlaceHistoryOverlay)
        assert o.name == "events"

    def test_fetch_returns_result(self):
        p = DictEventsProvider()
        p.add(_er(geoids_affected=["A"]))
        o = EventsOverlay(provider=p)
        result = o.fetch("A", 2018, 2022)
        assert isinstance(result, EventsOverlayResult)
        assert result.geoid == "A"
        assert result.has_events

    def test_fetch_empty(self):
        p = DictEventsProvider()
        o = EventsOverlay(provider=p)
        result = o.fetch("A", 2000, 2020)
        assert not result.has_events

    def test_no_provider_raises(self):
        o = EventsOverlay(provider=None)
        with pytest.raises(RuntimeError, match="No events data provider"):
            o.fetch("A", 2000, 2020)

    def test_event_type_filter(self):
        p = DictEventsProvider()
        p.add(_er(event_type="court_ruling", geoids_affected=["A"]))
        p.add(_er(event_type="natural_disaster", geoids_affected=["A"]))
        o = EventsOverlay(provider=p, event_types=["court_ruling"])
        result = o.fetch("A", 2018, 2022)
        assert len(result.events) == 1

    def test_multiple_events(self):
        p = DictEventsProvider()
        p.add(_er(event_id="1", event_date=date(2020, 1, 1), geoids_affected=["A"]))
        p.add(_er(event_id="2", event_date=date(2020, 6, 1), geoids_affected=["A"]))
        p.add(_er(event_id="3", event_date=date(2021, 1, 1), geoids_affected=["A"]))
        o = EventsOverlay(provider=p)
        result = o.fetch("A", 2020, 2021)
        assert result.count == 3

"""Tests for place history query API (SU#607)."""

from __future__ import annotations


from siege_utilities.geo.place_history import (
    DictCrosswalkProvider,
    Lineage,
    LineageStep,
    PlaceHistoryResult,
    _build_lineage,
    _decade_transitions,
    place_history,
)


# ---------------------------------------------------------------------------
# Decade transitions
# ---------------------------------------------------------------------------


class TestDecadeTransitions:
    def test_same_year(self):
        assert _decade_transitions(2010, 2010) == []

    def test_same_decade(self):
        assert _decade_transitions(2012, 2018) == []

    def test_single_forward(self):
        assert _decade_transitions(2005, 2015) == [(2000, 2010)]

    def test_single_forward_exact_decades(self):
        assert _decade_transitions(2000, 2010) == [(2000, 2010)]

    def test_two_decades_forward(self):
        assert _decade_transitions(2000, 2020) == [(2000, 2010), (2010, 2020)]

    def test_three_decades_forward(self):
        result = _decade_transitions(1995, 2025)
        assert result == [(1990, 2000), (2000, 2010), (2010, 2020)]

    def test_single_reverse(self):
        result = _decade_transitions(2015, 2005)
        assert result == [(2010, 2000)]

    def test_two_decades_reverse(self):
        result = _decade_transitions(2020, 2000)
        assert result == [(2020, 2010), (2010, 2000)]


# ---------------------------------------------------------------------------
# LineageStep / Lineage dataclasses
# ---------------------------------------------------------------------------


class TestLineageDataclasses:
    def test_lineage_step_defaults(self):
        step = LineageStep(
            source_geoid="A", target_geoid="B",
            source_year=2000, target_year=2010,
        )
        assert step.weight == 1.0
        assert step.relationship == "IDENTICAL"

    def test_lineage_is_unchanged_true(self):
        lin = Lineage(
            origin_geoid="17031010100",
            origin_year=2000,
            terminal_geoids=["17031010100"],
        )
        assert lin.is_unchanged

    def test_lineage_is_unchanged_false_different(self):
        lin = Lineage(
            origin_geoid="17031010100",
            origin_year=2000,
            terminal_geoids=["17031010200"],
        )
        assert not lin.is_unchanged

    def test_lineage_is_unchanged_false_split(self):
        lin = Lineage(
            origin_geoid="17031010100",
            origin_year=2000,
            terminal_geoids=["17031010100", "17031010200"],
        )
        assert not lin.is_unchanged


# ---------------------------------------------------------------------------
# PlaceHistoryResult
# ---------------------------------------------------------------------------


class TestPlaceHistoryResult:
    def test_direction_forward(self):
        r = PlaceHistoryResult(geoid="A", from_year=2000, to_year=2020)
        assert r.direction == "forward"

    def test_direction_reverse(self):
        r = PlaceHistoryResult(geoid="A", from_year=2020, to_year=2000)
        assert r.direction == "reverse"

    def test_has_lineage_false(self):
        r = PlaceHistoryResult(geoid="A", from_year=2000, to_year=2020)
        assert not r.has_lineage

    def test_has_lineage_true(self):
        r = PlaceHistoryResult(
            geoid="A", from_year=2000, to_year=2020,
            lineage=Lineage(
                origin_geoid="A", origin_year=2000,
                steps=[LineageStep("A", "B", 2000, 2010)],
            ),
        )
        assert r.has_lineage


# ---------------------------------------------------------------------------
# DictCrosswalkProvider
# ---------------------------------------------------------------------------


class TestDictCrosswalkProvider:
    def test_empty_provider(self):
        p = DictCrosswalkProvider()
        assert p.get_forward_mappings("A", 2000, 2010) == []

    def test_add_and_get_forward(self):
        p = DictCrosswalkProvider()
        p.add(2000, 2010, "A", "B", weight=0.8, relationship="PARTIAL")
        records = p.get_forward_mappings("A", 2000, 2010)
        assert len(records) == 1
        assert records[0].target_geoid == "B"
        assert records[0].weight == 0.8

    def test_get_reverse(self):
        p = DictCrosswalkProvider()
        p.add(2000, 2010, "A", "B")
        records = p.get_reverse_mappings("B", 2000, 2010)
        assert len(records) == 1
        assert records[0].source_geoid == "A"

    def test_split(self):
        p = DictCrosswalkProvider()
        p.add(2000, 2010, "A", "B1", weight=0.6, relationship="SPLIT")
        p.add(2000, 2010, "A", "B2", weight=0.4, relationship="SPLIT")
        records = p.get_forward_mappings("A", 2000, 2010)
        assert len(records) == 2

    def test_wrong_transition(self):
        p = DictCrosswalkProvider()
        p.add(2000, 2010, "A", "B")
        assert p.get_forward_mappings("A", 2010, 2020) == []


# ---------------------------------------------------------------------------
# Lineage building
# ---------------------------------------------------------------------------


class TestBuildLineage:
    def test_same_decade_no_steps(self):
        p = DictCrosswalkProvider()
        lin = _build_lineage("A", 2005, 2008, p)
        assert lin.terminal_geoids == ["A"]
        assert len(lin.steps) == 0

    def test_identical_transition(self):
        p = DictCrosswalkProvider()
        p.add(2000, 2010, "A", "A", weight=1.0, relationship="IDENTICAL")
        lin = _build_lineage("A", 2000, 2015, p)
        assert lin.terminal_geoids == ["A"]
        assert len(lin.steps) == 1
        assert lin.steps[0].relationship == "IDENTICAL"

    def test_renamed(self):
        p = DictCrosswalkProvider()
        p.add(2000, 2010, "A", "B", weight=1.0, relationship="RENAMED")
        lin = _build_lineage("A", 2000, 2015, p)
        assert lin.terminal_geoids == ["B"]

    def test_split(self):
        p = DictCrosswalkProvider()
        p.add(2000, 2010, "A", "B1", weight=0.6, relationship="SPLIT")
        p.add(2000, 2010, "A", "B2", weight=0.4, relationship="SPLIT")
        lin = _build_lineage("A", 2000, 2015, p)
        assert set(lin.terminal_geoids) == {"B1", "B2"}
        assert len(lin.steps) == 2

    def test_multi_decade_chain(self):
        p = DictCrosswalkProvider()
        p.add(2000, 2010, "A", "B", weight=1.0, relationship="RENAMED")
        p.add(2010, 2020, "B", "C", weight=1.0, relationship="RENAMED")
        lin = _build_lineage("A", 2000, 2025, p)
        assert lin.terminal_geoids == ["C"]
        assert len(lin.steps) == 2

    def test_no_crosswalk_data_preserves_geoid(self):
        p = DictCrosswalkProvider()
        lin = _build_lineage("A", 2000, 2015, p)
        assert lin.terminal_geoids == ["A"]

    def test_min_weight_filter(self):
        p = DictCrosswalkProvider()
        p.add(2000, 2010, "A", "B1", weight=0.005, relationship="SPLIT")
        p.add(2000, 2010, "A", "B2", weight=0.995, relationship="SPLIT")
        lin = _build_lineage("A", 2000, 2015, p, min_weight=0.01)
        assert lin.terminal_geoids == ["B2"]

    def test_reverse_direction(self):
        p = DictCrosswalkProvider()
        p.add(2000, 2010, "A", "B", weight=1.0, relationship="RENAMED")
        lin = _build_lineage("B", 2015, 2005, p)
        assert lin.direction == "reverse"
        assert lin.terminal_geoids == ["A"]

    def test_forward_direction_flag(self):
        p = DictCrosswalkProvider()
        lin = _build_lineage("A", 2005, 2015, p)
        assert lin.direction == "forward"


# ---------------------------------------------------------------------------
# place_history() integration
# ---------------------------------------------------------------------------


class TestPlaceHistory:
    def test_basic_query(self):
        p = DictCrosswalkProvider()
        p.add(2000, 2010, "17031010100", "17031010100", weight=1.0)
        result = place_history("17031010100", 2000, 2015, provider=p)

        assert result.geoid == "17031010100"
        assert result.from_year == 2000
        assert result.to_year == 2015
        assert result.has_lineage
        assert result.lineage.terminal_geoids == ["17031010100"]
        assert len(result.errors) == 0

    def test_no_provider_returns_error(self):
        result = place_history("A", 2000, 2020, provider=None)
        assert len(result.errors) >= 1

    def test_with_split(self):
        p = DictCrosswalkProvider()
        p.add(2010, 2020, "T1", "T1a", weight=0.6, relationship="SPLIT")
        p.add(2010, 2020, "T1", "T1b", weight=0.4, relationship="SPLIT")
        result = place_history("T1", 2010, 2025, provider=p)

        assert set(result.lineage.terminal_geoids) == {"T1a", "T1b"}

    def test_overlays_without_registry(self):
        p = DictCrosswalkProvider()
        result = place_history("A", 2000, 2020, overlays=["seats"], provider=p)
        assert result.overlays == {}

    def test_overlays_with_registry(self):
        p = DictCrosswalkProvider()

        class MockOverlay:
            def fetch(self, geoid, from_year, to_year, state_fips):
                return {"districts": ["CD-1"]}

        class MockRegistry:
            def get(self, name):
                if name == "seats":
                    return MockOverlay()
                return None

        result = place_history(
            "A", 2000, 2020,
            overlays=["seats"],
            provider=p,
            overlay_registry=MockRegistry(),
        )
        assert "seats" in result.overlays
        assert result.overlays["seats"]["districts"] == ["CD-1"]

    def test_unknown_overlay_reports_error(self):
        p = DictCrosswalkProvider()

        class MockRegistry:
            def get(self, name):
                return None

        result = place_history(
            "A", 2000, 2020,
            overlays=["unknown"],
            provider=p,
            overlay_registry=MockRegistry(),
        )
        assert any("Unknown overlay" in e for e in result.errors)

    def test_overlay_exception_handled(self):
        p = DictCrosswalkProvider()

        class FailingOverlay:
            def fetch(self, geoid, from_year, to_year, state_fips):
                raise RuntimeError("DB down")

        class MockRegistry:
            def get(self, name):
                return FailingOverlay()

        result = place_history(
            "A", 2000, 2020,
            overlays=["broken"],
            provider=p,
            overlay_registry=MockRegistry(),
        )
        assert any("broken" in e for e in result.errors)

    def test_same_decade_no_lineage_steps(self):
        p = DictCrosswalkProvider()
        result = place_history("A", 2012, 2018, provider=p)
        assert not result.has_lineage
        assert result.lineage.terminal_geoids == ["A"]

    def test_reverse_query(self):
        p = DictCrosswalkProvider()
        p.add(2010, 2020, "X", "Y", weight=1.0, relationship="RENAMED")
        result = place_history("Y", 2025, 2005, provider=p)

        assert result.direction == "reverse"
        assert result.lineage.terminal_geoids == ["X"]

    def test_state_fips_passed_through(self):
        calls = []

        class TrackingProvider(DictCrosswalkProvider):
            def get_forward_mappings(self, geoid, src, tgt, state_fips=None):
                calls.append(state_fips)
                return super().get_forward_mappings(geoid, src, tgt, state_fips)

        p = TrackingProvider()
        place_history("A", 2000, 2015, state_fips="17", provider=p)
        assert "17" in calls

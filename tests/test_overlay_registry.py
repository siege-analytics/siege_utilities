"""Tests for overlay registry (SU#608)."""

from __future__ import annotations

import pytest

from siege_utilities.geo.overlay_registry import (
    OverlayRegistry,
    PlaceHistoryOverlay,
    overlay_registry,
)


# ---------------------------------------------------------------------------
# Concrete overlay for testing
# ---------------------------------------------------------------------------


class _TestOverlay(PlaceHistoryOverlay):
    @property
    def name(self):
        return "test"

    def fetch(self, geoid, from_year, to_year, state_fips=None):
        return {"geoid": geoid, "years": (from_year, to_year)}


class _UnavailableOverlay(PlaceHistoryOverlay):
    @property
    def name(self):
        return "unavailable"

    def fetch(self, geoid, from_year, to_year, state_fips=None):
        raise RuntimeError("not available")

    def is_available(self):
        return False


# ---------------------------------------------------------------------------
# PlaceHistoryOverlay ABC
# ---------------------------------------------------------------------------


class TestPlaceHistoryOverlay:
    def test_cannot_instantiate_abc(self):
        with pytest.raises(TypeError):
            PlaceHistoryOverlay()

    def test_concrete_overlay(self):
        o = _TestOverlay()
        assert o.name == "test"
        assert o.is_available()

    def test_fetch_returns_data(self):
        o = _TestOverlay()
        result = o.fetch("17031", 2000, 2020)
        assert result["geoid"] == "17031"

    def test_is_available_override(self):
        o = _UnavailableOverlay()
        assert not o.is_available()


# ---------------------------------------------------------------------------
# OverlayRegistry
# ---------------------------------------------------------------------------


class TestOverlayRegistry:
    def setup_method(self):
        self.registry = OverlayRegistry()

    def test_empty_registry(self):
        assert self.registry.list_overlays() == []
        assert self.registry.get("anything") is None

    def test_register_instance(self):
        o = _TestOverlay()
        self.registry.register_instance("test", o)
        assert self.registry.get("test") is o
        assert self.registry.is_registered("test")

    def test_register_instance_type_check(self):
        with pytest.raises(TypeError, match="PlaceHistoryOverlay"):
            self.registry.register_instance("bad", "not an overlay")

    def test_decorator_registration(self):
        @self.registry.register("decorated")
        class DecoratedOverlay(PlaceHistoryOverlay):
            @property
            def name(self):
                return "decorated"

            def fetch(self, geoid, from_year, to_year, state_fips=None):
                return "data"

        assert self.registry.is_registered("decorated")
        result = self.registry.get("decorated")
        assert isinstance(result, DecoratedOverlay)

    def test_decorator_type_check(self):
        with pytest.raises(TypeError, match="PlaceHistoryOverlay"):
            @self.registry.register("bad")
            class NotAnOverlay:
                pass

    def test_lazy_instantiation(self):
        instantiated = []

        @self.registry.register("lazy")
        class LazyOverlay(PlaceHistoryOverlay):
            def __init__(self):
                instantiated.append(True)

            @property
            def name(self):
                return "lazy"

            def fetch(self, geoid, from_year, to_year, state_fips=None):
                return None

        assert len(instantiated) == 0
        self.registry.get("lazy")
        assert len(instantiated) == 1
        self.registry.get("lazy")
        assert len(instantiated) == 1

    def test_list_overlays(self):
        self.registry.register_instance("b", _TestOverlay())
        self.registry.register_instance("a", _TestOverlay())
        assert self.registry.list_overlays() == ["a", "b"]

    def test_list_includes_classes(self):
        @self.registry.register("cls_only")
        class Cls(PlaceHistoryOverlay):
            @property
            def name(self):
                return "cls_only"

            def fetch(self, geoid, from_year, to_year, state_fips=None):
                return None

        self.registry.register_instance("inst", _TestOverlay())
        names = self.registry.list_overlays()
        assert "cls_only" in names
        assert "inst" in names

    def test_unregister_instance(self):
        self.registry.register_instance("test", _TestOverlay())
        assert self.registry.unregister("test")
        assert not self.registry.is_registered("test")
        assert self.registry.get("test") is None

    def test_unregister_class(self):
        @self.registry.register("cls")
        class Cls(PlaceHistoryOverlay):
            @property
            def name(self):
                return "cls"

            def fetch(self, geoid, from_year, to_year, state_fips=None):
                return None

        assert self.registry.unregister("cls")
        assert not self.registry.is_registered("cls")

    def test_unregister_nonexistent(self):
        assert not self.registry.unregister("nope")

    def test_clear(self):
        self.registry.register_instance("a", _TestOverlay())
        self.registry.register_instance("b", _TestOverlay())
        self.registry.clear()
        assert self.registry.list_overlays() == []

    def test_get_unknown(self):
        assert self.registry.get("unknown") is None

    def test_instantiation_failure_raises(self):
        @self.registry.register("broken")
        class BrokenOverlay(PlaceHistoryOverlay):
            def __init__(self):
                raise RuntimeError("init failed")

            @property
            def name(self):
                return "broken"

            def fetch(self, geoid, from_year, to_year, state_fips=None):
                return None

        # get() lazily instantiates and documents "Raises: Exception if the
        # registered overlay class fails to instantiate" (SU-1: surface the
        # broken provider, don't hide it as a None lookup miss). Previously
        # asserted None.
        with pytest.raises(RuntimeError):
            self.registry.get("broken")

    def test_instance_overrides_class(self):
        @self.registry.register("dup")
        class DupOverlay(PlaceHistoryOverlay):
            @property
            def name(self):
                return "dup"

            def fetch(self, geoid, from_year, to_year, state_fips=None):
                return "from_class"

        instance = _TestOverlay()
        self.registry.register_instance("dup", instance)
        assert self.registry.get("dup") is instance


# ---------------------------------------------------------------------------
# Global registry
# ---------------------------------------------------------------------------


class TestGlobalRegistry:
    def test_global_exists(self):
        assert isinstance(overlay_registry, OverlayRegistry)

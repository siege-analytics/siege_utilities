"""Tests for siege_utilities.geo.providers.etter_to_geometry (ELE-2483 PR-C).

Gazetteer is mocked — these tests cover the relation-semantics
dispatch, buffer-distance precedence, directional geometry math,
and predicate behaviour. No network calls.
"""

from __future__ import annotations

import pytest

pytest.importorskip("shapely")

from shapely.geometry import Point, Polygon

from siege_utilities.geo.providers.etter_filter import EtterFilter
from siege_utilities.geo.providers.etter_to_geometry import (
    EtterGeometryResult,
    EtterReferenceNotFoundError,
    EtterUnknownRelationError,
    RelationSemantics,
    etter_to_geometry,
)
from siege_utilities.geo.gazetteers.base import GazetteerResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_gazetteer(geometry):
    """Return a minimal Gazetteer that always resolves to *geometry*."""
    centroid = geometry.centroid

    class _G:
        provider_name = "test"

        def lookup(self, name, *, country_hint=None, admin_hint=None):
            return GazetteerResult(
                name=name,
                canonical_path=(name,),
                geometry=geometry,
                centroid=centroid,
            )

        def search(self, name, *, country_hint=None, limit=10):
            return []

        def is_available(self):
            return True

    return _G()


def _make_failing_gazetteer():
    class _G:
        provider_name = "test"

        def lookup(self, name, *, country_hint=None, admin_hint=None):
            raise RuntimeError("not found")

        def search(self, name, *, country_hint=None, limit=10):
            return []

        def is_available(self):
            return True

    return _G()


def _filter(*, relation, ref="Lausanne", buffer_m=None):
    return EtterFilter(
        original_query="(test)",
        spatial_relation=relation,
        reference_location=ref,
        buffer_distance_m=buffer_m,
        confidence=1.0,
        raw=None,
    )


# Reference geometry: a small square around Lausanne (lon=6.6, lat=46.5).
_LAUSANNE = Polygon([
    (6.55, 46.45), (6.65, 46.45), (6.65, 46.55), (6.55, 46.55), (6.55, 46.45),
])


# ---------------------------------------------------------------------------
# No-relation / containment / proximity
# ---------------------------------------------------------------------------

class TestNoRelation:
    def test_bare_reference_returns_geometry_verbatim(self):
        gz = _make_gazetteer(_LAUSANNE)
        f = _filter(relation=None)
        result = etter_to_geometry(f, gazetteer=gz)
        assert result.geometry.equals(_LAUSANNE)
        assert result.relation is None
        assert result.buffer_km is None

    def test_missing_reference_raises_value_error(self):
        gz = _make_gazetteer(_LAUSANNE)
        f = EtterFilter(
            original_query="(empty)",
            spatial_relation="near",
            reference_location=None,
        )
        with pytest.raises(ValueError, match="reference_location"):
            etter_to_geometry(f, gazetteer=gz)


class TestContainment:
    def test_in_returns_reference_geometry(self):
        gz = _make_gazetteer(_LAUSANNE)
        f = _filter(relation="in")
        result = etter_to_geometry(f, gazetteer=gz)
        assert result.geometry.equals(_LAUSANNE)
        assert result.relation == "in"

    def test_within_alias(self):
        gz = _make_gazetteer(_LAUSANNE)
        f = _filter(relation="within")
        result = etter_to_geometry(f, gazetteer=gz)
        assert result.geometry.equals(_LAUSANNE)


class TestNearProximity:
    def test_near_buffers_reference_using_default(self):
        gz = _make_gazetteer(_LAUSANNE)
        f = _filter(relation="near")
        result = etter_to_geometry(f, gazetteer=gz, default_buffer_km=10)
        assert result.geometry.area > _LAUSANNE.area
        assert result.buffer_km == 10

    def test_filter_distance_overrides_default(self):
        gz = _make_gazetteer(_LAUSANNE)
        f = _filter(relation="near", buffer_m=2000.0)
        result = etter_to_geometry(f, gazetteer=gz, default_buffer_km=100)
        assert result.buffer_km == 2.0  # 2000 m


# ---------------------------------------------------------------------------
# Directional relations
# ---------------------------------------------------------------------------

class TestBoundedDirectional:
    def test_north_of_produces_finite_polygon(self):
        gz = _make_gazetteer(_LAUSANNE)
        f = _filter(relation="north_of")
        result = etter_to_geometry(
            f, gazetteer=gz,
            semantics=RelationSemantics.BOUNDED,
            default_buffer_km=20,
        )
        # Bounded polygon's centroid should be north of Lausanne's.
        assert result.geometry.centroid.y > _LAUSANNE.centroid.y
        # And it should be a finite (non-empty) polygon.
        assert result.geometry.area > 0
        # Bounded result must not be the entire upper halfplane.
        assert result.geometry.area < (360 * 90)

    def test_south_of_pushes_centroid_south(self):
        gz = _make_gazetteer(_LAUSANNE)
        f = _filter(relation="south_of")
        result = etter_to_geometry(f, gazetteer=gz)
        assert result.geometry.centroid.y < _LAUSANNE.centroid.y

    def test_east_west_shift(self):
        gz = _make_gazetteer(_LAUSANNE)
        east = etter_to_geometry(_filter(relation="east_of"), gazetteer=gz)
        west = etter_to_geometry(_filter(relation="west_of"), gazetteer=gz)
        assert east.geometry.centroid.x > _LAUSANNE.centroid.x
        assert west.geometry.centroid.x < _LAUSANNE.centroid.x


class TestHalfplane:
    def test_north_of_is_unbounded_upper_halfplane(self):
        gz = _make_gazetteer(_LAUSANNE)
        f = _filter(relation="north_of")
        result = etter_to_geometry(
            f, gazetteer=gz, semantics=RelationSemantics.HALFPLANE,
        )
        # World bbox lon: [-180, 180], lat: [cy, 90].
        minx, miny, maxx, maxy = result.geometry.bounds
        assert minx == pytest.approx(-180)
        assert maxx == pytest.approx(180)
        assert miny == pytest.approx(_LAUSANNE.centroid.y)
        assert maxy == pytest.approx(90)

    def test_buffer_km_is_none_for_halfplane(self):
        gz = _make_gazetteer(_LAUSANNE)
        result = etter_to_geometry(
            _filter(relation="east_of"), gazetteer=gz,
            semantics=RelationSemantics.HALFPLANE,
        )
        assert result.buffer_km is None


class TestContainsCentroid:
    def test_returns_predicate_for_directional(self):
        gz = _make_gazetteer(_LAUSANNE)
        result = etter_to_geometry(
            _filter(relation="north_of"), gazetteer=gz,
            semantics=RelationSemantics.CONTAINS_CENTROID,
        )
        predicate = result.geometry
        assert callable(predicate)
        # A point north of Lausanne should pass.
        assert predicate(Point(6.6, 50.0)) is True
        # A point south should fail.
        assert predicate(Point(6.6, 40.0)) is False

    def test_predicate_works_on_geometry_with_centroid(self):
        gz = _make_gazetteer(_LAUSANNE)
        result = etter_to_geometry(
            _filter(relation="east_of"), gazetteer=gz,
            semantics=RelationSemantics.CONTAINS_CENTROID,
        )
        # A polygon east of Lausanne (centroid at lon=10).
        eastern = Polygon([(9, 45), (11, 45), (11, 47), (9, 47), (9, 45)])
        assert result.geometry(eastern) is True


# ---------------------------------------------------------------------------
# Error paths
# ---------------------------------------------------------------------------

class TestErrorPaths:
    def test_gazetteer_failure_translated(self):
        gz = _make_failing_gazetteer()
        f = _filter(relation="near")
        with pytest.raises(EtterReferenceNotFoundError, match="could not resolve"):
            etter_to_geometry(f, gazetteer=gz)

    def test_unknown_relation_raises(self):
        gz = _make_gazetteer(_LAUSANNE)
        f = _filter(relation="northwest_of")  # not in our table
        with pytest.raises(EtterUnknownRelationError, match="unsupported"):
            etter_to_geometry(f, gazetteer=gz)


# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------

class TestEtterGeometryResult:
    def test_includes_reference_and_notes(self):
        gz = _make_gazetteer(_LAUSANNE)
        f = _filter(relation="near", buffer_m=5000)
        result = etter_to_geometry(f, gazetteer=gz)
        assert isinstance(result, EtterGeometryResult)
        assert result.reference is not None
        assert result.reference.name == "Lausanne"
        assert any("buffer" in n for n in result.notes)

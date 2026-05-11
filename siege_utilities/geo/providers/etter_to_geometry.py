"""Etter → geometry resolver.

Turns a parsed :class:`siege_utilities.geo.providers.etter_filter.EtterFilter`
into a shapely geometry, using a :class:`siege_utilities.geo.gazetteers.Gazetteer`
to look up the reference location.

The interesting design decision is *what geometry "X near Y" means*. We
ship three modes:

* :attr:`RelationSemantics.BOUNDED` — default; produces a finite
  polygon. Directional relations ("north of Y") are evaluated as a
  bounded buffer (``default_buffer_km`` × 2) on the directional side
  of Y's centroid. This is the safe default for indexed-lookup
  workloads — the output is always intersectable with a polygon set.
* :attr:`RelationSemantics.HALFPLANE` — directional relations produce
  an *infinite* halfplane. "North of Lake Geneva" → the entire
  northern halfplane from Lake Geneva's latitude. Useful for filter
  semantics where the consumer will intersect with a country / region
  boundary later. Not ideal for indexed lookups; the geometry is
  unbounded.
* :attr:`RelationSemantics.CONTAINS_CENTROID` — instead of returning a
  region geometry, returns a :class:`PointPredicate` callable that
  evaluates ``contains(candidate.centroid)`` for each candidate. Use
  when you want directional filtering without producing a polygon at
  all.

Buffer-distance precedence:

1. If the Etter filter parsed an explicit distance ("within 5 km of …"),
   that wins.
2. Else, ``default_buffer_km`` on the resolver (default 25 km).
"""

from __future__ import annotations

import enum
import logging
import math
from dataclasses import dataclass
from typing import Any, Callable, Optional

from .etter_filter import EtterFilter
from ..gazetteers.base import Gazetteer, GazetteerResult

log = logging.getLogger(__name__)


__all__ = [
    "RelationSemantics",
    "EtterGeometryResult",
    "PointPredicate",
    "EtterToGeometryError",
    "etter_to_geometry",
]


class RelationSemantics(str, enum.Enum):
    """How to interpret directional/proximity relations.

    See module docstring for the full rationale.
    """

    BOUNDED = "bounded"
    HALFPLANE = "halfplane"
    CONTAINS_CENTROID = "contains_centroid"


class EtterToGeometryError(RuntimeError):
    """Raised when an EtterFilter cannot be turned into a geometry.

    Carries the parsed filter and the failure reason. The most common
    causes — the reference location not being found in the gazetteer,
    or a relation Etter parsed that we don't know how to translate —
    each have their own subclass so callers can branch.
    """


class EtterReferenceNotFoundError(EtterToGeometryError):
    """The reference location couldn't be resolved by the gazetteer."""


class EtterUnknownRelationError(EtterToGeometryError):
    """Etter returned a relation we don't have a translation for."""


@dataclass(frozen=True)
class EtterGeometryResult:
    """The resolved geometry plus diagnostic context.

    Attributes:
        geometry: The shapely geometry (or :class:`PointPredicate` for
            ``CONTAINS_CENTROID`` mode).
        relation: The Etter spatial_relation that was applied, or
            ``None`` if the input had no relation (just a bare
            reference location → the reference geometry itself).
        reference: The :class:`GazetteerResult` that anchored the
            relation. ``None`` only when the filter had no
            reference_location either, which is a degenerate input.
        buffer_km: Buffer distance actually used (filter wins over
            default; ``None`` for relations that don't buffer).
        semantics: Which :class:`RelationSemantics` mode produced this
            result.
        notes: Free-text diagnostic notes (e.g., "halfplane truncated
            to ±90° lat to remain valid GeoJSON").
    """

    geometry: Any
    relation: Optional[str]
    reference: Optional[GazetteerResult]
    buffer_km: Optional[float]
    semantics: RelationSemantics
    notes: tuple[str, ...] = ()


# A callable that takes a candidate geometry (or its centroid) and
# returns whether it satisfies the filter. Used by
# RelationSemantics.CONTAINS_CENTROID.
PointPredicate = Callable[[Any], bool]


# Directional unit vectors in (lon_offset, lat_offset). The "off" axis
# stays at 0 — we don't try to model NW vs N for now; Etter doesn't
# emit diagonal-only relations as a single token.
_DIRECTIONS: dict[str, tuple[float, float]] = {
    "north_of": (0.0, 1.0),
    "south_of": (0.0, -1.0),
    "east_of": (1.0, 0.0),
    "west_of": (-1.0, 0.0),
}

# Non-directional relations and how to handle them.
#
# * "in" / "within" — return the reference geometry verbatim.
# * "near" — buffer around the reference geometry.
# * "around" / "outside" — same as near (caller can invert).
_NON_DIRECTIONAL_NEAR = {"near", "around", "close_to"}
_NON_DIRECTIONAL_CONTAIN = {"in", "within", "inside"}


def etter_to_geometry(
    filter_: EtterFilter,
    *,
    gazetteer: Gazetteer,
    semantics: RelationSemantics = RelationSemantics.BOUNDED,
    default_buffer_km: float = 25.0,
    country_hint: Optional[str] = None,
    admin_hint: Optional[str] = None,
) -> EtterGeometryResult:
    """Resolve an :class:`EtterFilter` to a geometry.

    Args:
        filter_: The parsed query.
        gazetteer: The gazetteer that resolves the reference location.
            Pass the result of
            :func:`siege_utilities.geo.gazetteers.resolve_gazetteer`.
        semantics: Which mode of relation interpretation to use. The
            default :attr:`RelationSemantics.BOUNDED` is safe for
            most indexed-lookup workloads.
        default_buffer_km: Buffer to apply for "near"-style relations
            and as the half-width of bounded directional buffers when
            the filter doesn't carry an explicit distance.
        country_hint / admin_hint: Forwarded to ``gazetteer.lookup`` to
            disambiguate the reference location. Etter often emits
            just the place name; the consumer may know the country
            from a sibling field.

    Returns:
        :class:`EtterGeometryResult` with the geometry (or a
        :class:`PointPredicate`) and diagnostic context.

    Raises:
        :class:`EtterReferenceNotFoundError`: Gazetteer couldn't find
            the reference location.
        :class:`EtterUnknownRelationError`: Etter parsed a relation
            we don't know how to translate.
        :class:`ValueError`: ``filter_.reference_location`` is missing.
    """
    if not filter_.reference_location:
        raise ValueError(
            "EtterFilter has no reference_location; nothing to resolve. "
            "Etter parsed a query that mentions no place — the caller "
            "needs to feed a different query or handle this case before "
            "calling etter_to_geometry."
        )

    # 1. Resolve the reference place → geometry.
    try:
        reference = gazetteer.lookup(
            filter_.reference_location,
            country_hint=country_hint,
            admin_hint=admin_hint,
        )
    except Exception as exc:
        # We catch broadly here because gazetteer backends can raise
        # their own typed exceptions; we want to surface a single
        # well-named one to the caller. The original is preserved via
        # __cause__.
        raise EtterReferenceNotFoundError(
            f"could not resolve reference location "
            f"{filter_.reference_location!r}: {exc}"
        ) from exc

    relation = filter_.spatial_relation
    notes: list[str] = []

    # 2. No relation → just return the reference geometry itself.
    if not relation:
        return EtterGeometryResult(
            geometry=reference.geometry,
            relation=None,
            reference=reference,
            buffer_km=None,
            semantics=semantics,
            notes=("no spatial_relation; returning reference geometry verbatim",),
        )

    relation_key = relation.lower().replace(" ", "_")
    buffer_km = (
        (filter_.buffer_distance_m / 1000.0)
        if filter_.buffer_distance_m is not None
        else default_buffer_km
    )

    # 3. Non-directional containment relations: just return the
    #    reference geometry — "voters in Texas" means Texas's polygon.
    if relation_key in _NON_DIRECTIONAL_CONTAIN:
        return EtterGeometryResult(
            geometry=reference.geometry,
            relation=relation_key,
            reference=reference,
            buffer_km=None,
            semantics=semantics,
            notes=("containment relation; using reference geometry verbatim",),
        )

    # 4. Non-directional proximity: buffer the reference geometry.
    if relation_key in _NON_DIRECTIONAL_NEAR:
        geom = _buffer_geometry(reference.geometry, buffer_km)
        return EtterGeometryResult(
            geometry=geom,
            relation=relation_key,
            reference=reference,
            buffer_km=buffer_km,
            semantics=semantics,
            notes=(f"proximity buffer = {buffer_km} km",),
        )

    # 5. Directional relations — dispatch on semantics mode.
    if relation_key not in _DIRECTIONS:
        raise EtterUnknownRelationError(
            f"unsupported spatial_relation {relation!r}; "
            f"known: {sorted(set(_DIRECTIONS) | _NON_DIRECTIONAL_NEAR | _NON_DIRECTIONAL_CONTAIN)}"
        )

    dx, dy = _DIRECTIONS[relation_key]
    centroid = reference.centroid

    if semantics is RelationSemantics.BOUNDED:
        # Bounded directional: a buffer placed `buffer_km` away in the
        # direction of (dx, dy) from the reference centroid. Width and
        # height are 2 * buffer_km so the result is a finite polygon.
        geom = _bounded_directional_buffer(centroid, dx, dy, buffer_km)
        notes.append(f"bounded directional buffer ({buffer_km} km on each side)")
        return EtterGeometryResult(
            geometry=geom,
            relation=relation_key,
            reference=reference,
            buffer_km=buffer_km,
            semantics=semantics,
            notes=tuple(notes),
        )

    if semantics is RelationSemantics.HALFPLANE:
        # Halfplane: an unbounded polygon to the directional side of
        # the reference centroid. We clip to a generous bbox so the
        # output remains valid GeoJSON / shapely (no infinite
        # coordinates), but it's effectively unbounded for most
        # downstream uses.
        geom = _halfplane_geometry(centroid, dx, dy)
        notes.append("halfplane clipped to ±180° lon, ±90° lat")
        return EtterGeometryResult(
            geometry=geom,
            relation=relation_key,
            reference=reference,
            buffer_km=None,
            semantics=semantics,
            notes=tuple(notes),
        )

    if semantics is RelationSemantics.CONTAINS_CENTROID:
        # Return a callable rather than a geometry. Caller applies it
        # per-candidate; we don't materialise a polygon at all.
        predicate = _make_centroid_predicate(centroid, dx, dy)
        notes.append(
            "predicate: lat/lon comparison against reference centroid; "
            "no polygon produced"
        )
        return EtterGeometryResult(
            geometry=predicate,
            relation=relation_key,
            reference=reference,
            buffer_km=None,
            semantics=semantics,
            notes=tuple(notes),
        )

    raise ValueError(f"unknown RelationSemantics: {semantics!r}")  # pragma: no cover


# ---------------------------------------------------------------------------
# Geometry constructors
# ---------------------------------------------------------------------------

# 1 degree of latitude ≈ 111.32 km everywhere; 1 degree of longitude
# varies with cos(latitude). We use these crude conversions for the
# buffer math — the alternative is reprojecting to a metric CRS per
# call, which is overkill for the "bounded buffer near a city" use
# case Etter is meant for.
_KM_PER_DEG_LAT = 111.32


def _km_per_deg_lon(lat_deg: float) -> float:
    return _KM_PER_DEG_LAT * math.cos(math.radians(lat_deg))


def _buffer_geometry(geometry: Any, buffer_km: float) -> Any:
    """Buffer *geometry* by *buffer_km* (in lat-degree-equivalent units)."""
    centroid = geometry.centroid
    # Convert km to degrees. Use the geometry's own centroid latitude
    # to scale longitude. For polygons spanning many degrees of
    # latitude this is approximate; consumers needing precise buffers
    # should reproject to a metric CRS first.
    lat = float(centroid.y)
    lat_deg = buffer_km / _KM_PER_DEG_LAT
    lon_deg = buffer_km / max(_km_per_deg_lon(lat), 1e-6)
    # shapely's .buffer takes a single distance — using the larger of
    # the two avoids producing a polygon smaller than buffer_km in
    # either axis. Slightly over-buffers near the equator but consumers
    # asking for "near" want a generous boundary.
    return geometry.buffer(max(lat_deg, lon_deg))


def _bounded_directional_buffer(
    centroid: Any, dx: float, dy: float, buffer_km: float,
) -> Any:
    """Return a square polygon `buffer_km` away from *centroid* in
    direction (dx, dy)."""
    from shapely.geometry import box

    cx, cy = float(centroid.x), float(centroid.y)
    half_lat = buffer_km / _KM_PER_DEG_LAT
    half_lon = buffer_km / max(_km_per_deg_lon(cy), 1e-6)
    # Center of the directional buffer is shifted by buffer_km in the
    # (dx, dy) direction, then we draw a 2*buffer_km square around it.
    ox = cx + dx * half_lon * 2
    oy = cy + dy * half_lat * 2
    minx = ox - half_lon
    miny = oy - half_lat
    maxx = ox + half_lon
    maxy = oy + half_lat
    # Clamp to valid lat/lon — directional buffers near a pole can
    # otherwise go past ±90°.
    miny = max(miny, -90.0)
    maxy = min(maxy, 90.0)
    return box(minx, miny, maxx, maxy)


def _halfplane_geometry(centroid: Any, dx: float, dy: float) -> Any:
    """Return a halfplane polygon clipped to the world bbox."""
    from shapely.geometry import box

    cx, cy = float(centroid.x), float(centroid.y)
    # Lon range is the full world; lat range is clipped to ±90.
    WORLD_MINX, WORLD_MAXX = -180.0, 180.0
    WORLD_MINY, WORLD_MAXY = -90.0, 90.0
    if dy > 0:    # north_of
        return box(WORLD_MINX, cy, WORLD_MAXX, WORLD_MAXY)
    if dy < 0:    # south_of
        return box(WORLD_MINX, WORLD_MINY, WORLD_MAXX, cy)
    if dx > 0:    # east_of
        return box(cx, WORLD_MINY, WORLD_MAXX, WORLD_MAXY)
    if dx < 0:    # west_of
        return box(WORLD_MINX, WORLD_MINY, cx, WORLD_MAXY)
    raise ValueError(f"_halfplane_geometry called with zero direction ({dx},{dy})")  # pragma: no cover


def _make_centroid_predicate(
    centroid: Any, dx: float, dy: float,
) -> PointPredicate:
    """Build a callable that returns True when a candidate's centroid
    falls on the directional side of *centroid*."""
    cx, cy = float(centroid.x), float(centroid.y)

    def predicate(candidate: Any) -> bool:
        # Accept anything with a `.centroid` (geometries) OR `.x/.y`
        # (Points / coord pairs).
        pt = getattr(candidate, "centroid", candidate)
        x, y = float(getattr(pt, "x")), float(getattr(pt, "y"))
        if dy > 0:
            return y > cy
        if dy < 0:
            return y < cy
        if dx > 0:
            return x > cx
        if dx < 0:
            return x < cx
        return False

    return predicate

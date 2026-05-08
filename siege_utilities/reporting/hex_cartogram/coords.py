"""Axial hex-grid coordinate math.

Uses axial ``(q, r)`` coordinates with **pointy-top** hexagons (the
visual convention for cartograms — wider than tall, easier to read state
abbreviations inside). All distance / Cartesian math derives from here;
having one canonical conversion module keeps algorithms / rendering
internally consistent.

Conventions
-----------
* ``(q, r)`` are integers; the third cube coord ``s = -q - r`` is
  implicit.
* Cartesian conversion uses unit-side-length hexes — caller can rescale.
* Neighbor offsets: 6 directions, returned in the standard order
  (E, NE, NW, W, SW, SE).
"""

from __future__ import annotations

import math

__all__ = [
    "AxialCoord",
    "axial_distance",
    "axial_neighbors",
    "axial_to_cartesian",
    "hexagon_polygon",
]


# Type alias kept simple — a tuple is fine for hashing into dicts/sets.
AxialCoord = tuple[int, int]


# Pointy-top neighbor offsets, in (E, NE, NW, W, SW, SE) order.
_AXIAL_NEIGHBORS: tuple[AxialCoord, ...] = (
    (+1, 0),
    (+1, -1),
    (0, -1),
    (-1, 0),
    (-1, +1),
    (0, +1),
)


def axial_neighbors(qr: AxialCoord) -> tuple[AxialCoord, ...]:
    """Return the six neighbors of ``qr`` in standard order."""
    q, r = qr
    return tuple((q + dq, r + dr) for dq, dr in _AXIAL_NEIGHBORS)


def axial_distance(a: AxialCoord, b: AxialCoord) -> int:
    """Hex-grid Manhattan distance between two axial coordinates.

    Equivalent to half the cube-coordinate L1 distance.
    """
    aq, ar = a
    bq, br = b
    return (abs(aq - bq) + abs(ar - br) + abs((aq + ar) - (bq + br))) // 2


def axial_to_cartesian(qr: AxialCoord, *, size: float = 1.0) -> tuple[float, float]:
    """Convert an axial coord to a Cartesian ``(x, y)`` for a pointy-top hex.

    ``size`` is the hex circumradius (corner distance). For unit
    side-length hexes the natural choice is ``size = 1``.
    """
    q, r = qr
    x = size * math.sqrt(3.0) * (q + r / 2.0)
    y = size * 1.5 * r
    return x, y


def hexagon_polygon(
    qr: AxialCoord,
    *,
    size: float = 1.0,
    scale: float = 1.0,
) -> list[tuple[float, float]]:
    """Return the 6 vertices of a pointy-top hexagon at ``qr``.

    Args:
        qr: Axial coordinate of the cell center.
        size: The grid's hex circumradius. Controls grid spacing.
        scale: Multiplier on the **drawn** hex radius. ``< 1.0`` shrinks
            individual hexagons within the grid (used by the
            value-proportional / value-sqrt sizing modes).

    Returns:
        A list of 6 ``(x, y)`` tuples in counter-clockwise order. The
        polygon is open (no duplicate-first-point); callers that need a
        closed ring (matplotlib ``Polygon``, shapely) typically don't —
        matplotlib closes automatically; shapely's ``Polygon`` constructor
        accepts the open form.
    """
    cx, cy = axial_to_cartesian(qr, size=size)
    radius = size * scale
    # Pointy-top: first vertex at the top (90°), step 60°.
    angles = (math.pi / 2 + i * math.pi / 3 for i in range(6))
    return [(cx + radius * math.cos(a), cy + radius * math.sin(a)) for a in angles]


def bounding_grid(
    n_cells: int,
    *,
    aspect_ratio: float = 1.3,
) -> list[AxialCoord]:
    """Generate enough hex cells to plausibly hold ``n_cells`` polygons.

    Picks a roughly oval grid sized to ``aspect_ratio`` (slightly wider
    than tall by default — matches the way countries are usually drawn
    on a page). The grid is generated as offset axial coords centered
    at ``(0, 0)``. Used by greedy and annealing algorithms as the
    candidate cell pool.
    """
    if n_cells < 1:
        raise ValueError(f"n_cells must be >= 1, got {n_cells}")
    # Target: an ellipse of integer hexes with major/minor axes that
    # together cover at least n_cells. Ellipse area ≈ π * a * b. For a
    # hex grid we want ~1.3× slack so the algorithm has room to shuffle.
    target = max(1, int(math.ceil(n_cells * 1.3)))
    a_axis = math.ceil(math.sqrt(target * aspect_ratio / math.pi))
    b_axis = math.ceil(math.sqrt(target / (aspect_ratio * math.pi)))
    out: list[AxialCoord] = []
    for r in range(-b_axis, b_axis + 1):
        for q in range(-a_axis - (r // 2 if r > 0 else 0), a_axis + 1 - (r // 2 if r < 0 else 0)):
            # Inside-ellipse test in Cartesian space.
            x, y = axial_to_cartesian((q, r))
            if (x / (a_axis * math.sqrt(3))) ** 2 + (y / (b_axis * 1.5)) ** 2 <= 1.05:
                out.append((q, r))
    if len(out) < n_cells:
        # Pathological tiny grids — fall back to a slightly larger box.
        out = [(q, r) for r in range(-b_axis - 1, b_axis + 2)
               for q in range(-a_axis - 1, a_axis + 2)]
    return out

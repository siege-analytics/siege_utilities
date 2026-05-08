"""Placement algorithms for hex cartograms.

Three algorithms shipped in v1:

* **Greedy** — sort polygons by area (largest first), assign each to the
  nearest unoccupied hex by centroid distance. Fast, baseline quality.
* **Hungarian** — bipartite matching via :func:`scipy.optimize.linear_sum_assignment`.
  Provably optimal for the centroid-distance objective. Doesn't model
  topology, but sets a strong baseline.
* **Simulated annealing** — start from greedy or Hungarian, repeatedly
  swap pairs whose swap improves a weighted ``α·centroid_error +
  β·topology_violation`` cost. The default for ≤ 200 polygons.

``force_directed`` and ``ilp`` are documented as future work in the
ticket; the API allows callers to pass the enum but raises
NotImplementedError so the surface is forward-compatible.

Each algorithm returns a ``dict[code, AxialCoord]`` — a mapping from
input polygon ID to its assigned hex cell.
"""

from __future__ import annotations

import enum
import logging
import math
import random
from typing import TYPE_CHECKING, Optional

from .coords import (
    AxialCoord,
    axial_distance,
    axial_to_cartesian,
    bounding_grid,
)

if TYPE_CHECKING:  # pragma: no cover
    import geopandas as gpd

log = logging.getLogger(__name__)

__all__ = [
    "Algorithm",
    "place_polygons",
]


class Algorithm(str, enum.Enum):
    """Placement-algorithm choices for :func:`hex_tile_layout`."""

    #: Sort by area, place in nearest unoccupied hex. < 100 ms typical.
    GREEDY = "greedy"
    #: Optimal centroid-distance assignment (no topology term).
    HUNGARIAN = "hungarian"
    #: Centroid + topology weighted; SA refinement of an initial layout.
    ANNEALING = "annealing"
    #: Reserved — not implemented in v1.
    FORCE_DIRECTED = "force_directed"
    #: Reserved — not implemented in v1.
    ILP = "ilp"


# ---------------------------------------------------------------------------
# Public entry
# ---------------------------------------------------------------------------

def place_polygons(
    gdf: "gpd.GeoDataFrame",
    code_col: str,
    *,
    algorithm: Algorithm = Algorithm.ANNEALING,
    candidate_cells: Optional[list[AxialCoord]] = None,
    # Annealing tuning:
    iterations: int = 5000,
    initial_temperature: float = 1.0,
    cooling_rate: float = 0.9995,
    centroid_weight: float = 1.0,
    topology_weight: float = 0.5,
    seed: Optional[int] = None,
) -> dict[str, AxialCoord]:
    """Assign each polygon in *gdf* to a hex cell.

    Args:
        gdf: GeoDataFrame of input polygons. Must have a geometry column
            and a string-valued *code_col* identifying each polygon.
        code_col: Column name holding the polygon identifier (used as
            the key in the returned mapping).
        algorithm: One of :class:`Algorithm`.
        candidate_cells: Pre-computed pool of axial coords to assign
            into. If None, uses :func:`bounding_grid` sized to the
            polygon count.
        iterations / initial_temperature / cooling_rate / centroid_weight
        / topology_weight / seed: Annealing-specific knobs. Ignored by
            greedy / hungarian.

    Returns:
        ``dict[code, (q, r)]`` mapping each polygon's code to its hex
        coordinate.

    Raises:
        ValueError: Empty GeoDataFrame.
        NotImplementedError: ``force_directed`` / ``ilp`` (reserved).
    """
    if len(gdf) == 0:
        raise ValueError("place_polygons: empty GeoDataFrame")
    if code_col not in gdf.columns:
        raise ValueError(
            f"place_polygons: code_col {code_col!r} not in gdf columns"
        )
    if algorithm in (Algorithm.FORCE_DIRECTED, Algorithm.ILP):
        raise NotImplementedError(
            f"Algorithm {algorithm.value!r} is reserved for follow-up "
            "work (see ELE-2482). Use 'greedy', 'hungarian', or "
            "'annealing' for now."
        )

    codes, centroids = _normalized_centroids(gdf, code_col)
    cells = list(candidate_cells) if candidate_cells is not None else list(bounding_grid(len(codes)))
    if len(cells) < len(codes):
        raise ValueError(
            f"Not enough candidate hex cells: have {len(cells)}, need "
            f"{len(codes)}. Pass a larger `candidate_cells` or accept the "
            "default bounding grid."
        )

    if algorithm == Algorithm.GREEDY:
        return _greedy_place(codes, centroids, cells, gdf, code_col)
    if algorithm == Algorithm.HUNGARIAN:
        return _hungarian_place(codes, centroids, cells)
    # Annealing: start from Hungarian if scipy is available, else greedy.
    try:
        initial = _hungarian_place(codes, centroids, cells)
    except ImportError:
        initial = _greedy_place(codes, centroids, cells, gdf, code_col)
    return _anneal(
        codes, centroids, cells, gdf, code_col, initial,
        iterations=iterations,
        initial_temperature=initial_temperature,
        cooling_rate=cooling_rate,
        centroid_weight=centroid_weight,
        topology_weight=topology_weight,
        seed=seed,
    )


# ---------------------------------------------------------------------------
# Greedy
# ---------------------------------------------------------------------------

def _greedy_place(
    codes: list[str],
    centroids: dict[str, tuple[float, float]],
    cells: list[AxialCoord],
    gdf: "gpd.GeoDataFrame",
    code_col: str,
) -> dict[str, AxialCoord]:
    """Largest-area first, nearest unoccupied hex."""
    # Order by polygon area descending so the largest get first pick.
    area_by_code = {
        str(row[code_col]): float(row.geometry.area)
        for _, row in gdf.iterrows()
    }
    order = sorted(codes, key=lambda c: area_by_code.get(c, 0.0), reverse=True)
    cell_centroids = {c: axial_to_cartesian(c) for c in cells}
    available = set(cells)
    out: dict[str, AxialCoord] = {}
    for code in order:
        cx, cy = centroids[code]
        # Pick nearest available cell by Cartesian distance.
        best_cell = min(
            available,
            key=lambda c: (cell_centroids[c][0] - cx) ** 2
                          + (cell_centroids[c][1] - cy) ** 2,
        )
        out[code] = best_cell
        available.remove(best_cell)
    return out


# ---------------------------------------------------------------------------
# Hungarian
# ---------------------------------------------------------------------------

def _hungarian_place(
    codes: list[str],
    centroids: dict[str, tuple[float, float]],
    cells: list[AxialCoord],
) -> dict[str, AxialCoord]:
    """Provably optimal centroid-distance assignment.

    Uses ``scipy.optimize.linear_sum_assignment``. Raises ImportError if
    scipy isn't installed; callers should fall back to greedy.
    """
    try:
        from scipy.optimize import linear_sum_assignment
        import numpy as np
    except ImportError as exc:
        raise ImportError(
            "Hungarian assignment requires scipy + numpy. Install "
            "via 'pip install siege-utilities[analytics]' or fall back "
            "to algorithm='greedy'."
        ) from exc

    n_polys = len(codes)
    n_cells = len(cells)
    # Cost matrix: rows are polygons, cols are cells.
    cell_centroids = [axial_to_cartesian(c) for c in cells]
    cost = np.zeros((n_polys, n_cells), dtype=float)
    for i, code in enumerate(codes):
        cx, cy = centroids[code]
        for j, (xx, yy) in enumerate(cell_centroids):
            cost[i, j] = math.hypot(cx - xx, cy - yy)
    row_idx, col_idx = linear_sum_assignment(cost)
    return {codes[r]: cells[c] for r, c in zip(row_idx, col_idx)}


# ---------------------------------------------------------------------------
# Simulated annealing
# ---------------------------------------------------------------------------

def _anneal(
    codes: list[str],
    centroids: dict[str, tuple[float, float]],
    cells: list[AxialCoord],
    gdf: "gpd.GeoDataFrame",
    code_col: str,
    initial: dict[str, AxialCoord],
    *,
    iterations: int,
    initial_temperature: float,
    cooling_rate: float,
    centroid_weight: float,
    topology_weight: float,
    seed: Optional[int],
) -> dict[str, AxialCoord]:
    """Refine *initial* with random pair swaps under SA cooling.

    The cost function balances:

    * Centroid error — sum of Cartesian distances between each polygon's
      normalized centroid and its assigned hex's Cartesian center.
    * Topology violation — number of input-adjacent polygon pairs whose
      assigned hexes are NOT grid-neighbors. (Adjacency is computed from
      the input geometry's ``touches`` predicate.)
    """
    rng = random.Random(seed)
    adjacency = _polygon_adjacency(gdf, code_col, codes)
    cell_xy = {c: axial_to_cartesian(c) for c in cells}
    # Per-code adjacency for O(deg) incremental cost updates.
    adj_by_code: dict[str, set[str]] = {c: set() for c in codes}
    for a, b in adjacency:
        adj_by_code[a].add(b)
        adj_by_code[b].add(a)

    def centroid_term(code: str, cell: AxialCoord) -> float:
        cx, cy = centroids[code]
        xx, yy = cell_xy[cell]
        return math.hypot(cx - xx, cy - yy)

    def local_violations(code: str, assignment: dict[str, AxialCoord]) -> int:
        """Count violating edges incident to *code* (each edge once)."""
        cell = assignment[code]
        return sum(
            1 for nb in adj_by_code[code]
            if nb in assignment and axial_distance(cell, assignment[nb]) > 1
        )

    def total_cost(assignment: dict[str, AxialCoord]) -> float:
        c_term = sum(centroid_term(code, cell) for code, cell in assignment.items())
        # Sum local violations and halve — each violating pair is touched
        # from both endpoints.
        violations = sum(local_violations(c, assignment) for c in assignment) // 2
        return centroid_weight * c_term + topology_weight * violations

    current = dict(initial)
    current_cost = total_cost(current)
    best = dict(current)
    best_cost = current_cost
    temperature = initial_temperature
    code_list = list(codes)

    for _ in range(iterations):
        a = rng.choice(code_list)
        b = rng.choice(code_list)
        if a == b:
            continue
        # Compute the delta from swapping a and b without rescanning the
        # whole assignment. Only edges incident to {a, b} can change
        # state, and only a's and b's centroid terms change.
        affected = {a, b} | adj_by_code[a] | adj_by_code[b]
        old_v = _violation_pairs_in(affected, adj_by_code, current)
        old_c = centroid_term(a, current[a]) + centroid_term(b, current[b])
        current[a], current[b] = current[b], current[a]
        new_v = _violation_pairs_in(affected, adj_by_code, current)
        new_c = centroid_term(a, current[a]) + centroid_term(b, current[b])
        delta = (
            centroid_weight * (new_c - old_c)
            + topology_weight * (new_v - old_v)
        )
        if delta < 0 or rng.random() < math.exp(-delta / max(temperature, 1e-9)):
            current_cost += delta
            if current_cost < best_cost:
                best = dict(current)
                best_cost = current_cost
        else:
            # Reject: undo.
            current[a], current[b] = current[b], current[a]
        temperature *= cooling_rate

    log.debug(
        "Annealing finished: initial_cost=%.3f best_cost=%.3f",
        total_cost(initial), best_cost,
    )
    return best


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _violation_pairs_in(
    codes: set[str],
    adj_by_code: dict[str, set[str]],
    assignment: dict[str, AxialCoord],
) -> int:
    """Count violating adjacency pairs with at least one endpoint in *codes*.

    Each pair is counted once even when both endpoints are in *codes*.
    """
    seen: set[tuple[str, str]] = set()
    n = 0
    for code in codes:
        if code not in assignment:
            continue
        cell = assignment[code]
        for nb in adj_by_code[code]:
            if nb not in assignment:
                continue
            key = (code, nb) if code < nb else (nb, code)
            if key in seen:
                continue
            seen.add(key)
            if axial_distance(cell, assignment[nb]) > 1:
                n += 1
    return n


def _normalized_centroids(
    gdf: "gpd.GeoDataFrame",
    code_col: str,
) -> tuple[list[str], dict[str, tuple[float, float]]]:
    """Return ``(codes, centroids)`` with centroids in a unit-square frame.

    Normalizing decouples downstream Cartesian distances from the input
    CRS scale (degrees vs metres) so the algorithm's tuning constants
    don't have to know about the projection.
    """
    raw = []
    codes: list[str] = []
    polygonal = {"Polygon", "MultiPolygon"}
    for _, row in gdf.iterrows():
        geom = row.geometry
        gtype = getattr(geom, "geom_type", None)
        if gtype not in polygonal:
            raise ValueError(
                f"hex cartogram requires Polygon/MultiPolygon geometries; "
                f"row {row[code_col]!r} has {gtype!r}"
            )
        codes.append(str(row[code_col]))
        c = geom.centroid
        raw.append((float(c.x), float(c.y)))
    xs = [p[0] for p in raw]
    ys = [p[1] for p in raw]
    minx, maxx = min(xs), max(xs)
    miny, maxy = min(ys), max(ys)
    span_x = max(maxx - minx, 1e-9)
    span_y = max(maxy - miny, 1e-9)
    # Map into roughly the same range as the bounding_grid Cartesian
    # output (which spans a few units in each direction).
    centroids = {}
    for code, (x, y) in zip(codes, raw):
        nx = (x - minx) / span_x * 6.0 - 3.0
        ny = (y - miny) / span_y * 6.0 - 3.0
        centroids[code] = (nx, ny)
    return codes, centroids


def _polygon_adjacency(
    gdf: "gpd.GeoDataFrame",
    code_col: str,
    codes: list[str],
) -> list[tuple[str, str]]:
    """Pairs of input-polygon codes that share a border.

    Uses shapely's ``touches`` predicate. O(n²); acceptable for the
    n ≤ 200 sweet spot the algorithms target.
    """
    by_code = {
        str(row[code_col]): row.geometry
        for _, row in gdf.iterrows()
    }
    pairs: list[tuple[str, str]] = []
    for i, a in enumerate(codes):
        for b in codes[i + 1:]:
            if by_code[a].touches(by_code[b]):
                pairs.append((a, b))
    return pairs

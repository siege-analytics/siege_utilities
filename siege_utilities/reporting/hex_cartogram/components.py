"""Connected-component splitting for non-contiguous admin sets.

CONUS + Alaska + Hawaii is the canonical case: three disconnected groups
that each deserve their own sub-grid, with empty hexes between groups so
the result reads as separated.

The wrapper:

1. Build a graph where nodes are polygons and edges are "share a border"
   (or "centroids within a tunable distance").
2. Find connected components.
3. Lay each component out independently using one of the placement
   algorithms.
4. Position the per-component layouts in the output grid by their
   *group* centroid, with ``component_gap`` empty hexes between groups.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from .coords import AxialCoord

if TYPE_CHECKING:  # pragma: no cover
    import geopandas as gpd

log = logging.getLogger(__name__)

__all__ = [
    "find_components",
]


def find_components(
    gdf: "gpd.GeoDataFrame",
    code_col: str,
) -> list[list[str]]:
    """Split *gdf* into connected components by polygon adjacency.

    Two polygons are considered adjacent if their geometries share a
    border (shapely ``touches``). Returns a list of lists of polygon
    codes — each inner list is one component.

    The result is sorted with the largest component first, then by
    representative-centroid x-coordinate for stable output across
    runs.
    """
    if len(gdf) == 0:
        return []
    by_code: dict[str, object] = {
        str(row[code_col]): row.geometry
        for _, row in gdf.iterrows()
    }
    codes = list(by_code)

    # Adjacency: undirected graph as adjacency-list dict.
    neighbors: dict[str, set[str]] = {c: set() for c in codes}
    for i, a in enumerate(codes):
        for b in codes[i + 1:]:
            if by_code[a].touches(by_code[b]):
                neighbors[a].add(b)
                neighbors[b].add(a)

    # Union-find via simple BFS.
    visited: set[str] = set()
    components: list[list[str]] = []
    for start in codes:
        if start in visited:
            continue
        stack = [start]
        comp: list[str] = []
        while stack:
            node = stack.pop()
            if node in visited:
                continue
            visited.add(node)
            comp.append(node)
            stack.extend(n for n in neighbors[node] if n not in visited)
        components.append(comp)

    # Stable ordering: largest first, ties broken by leftmost centroid.
    def _key(comp: list[str]) -> tuple[int, float]:
        xs = [float(by_code[c].centroid.x) for c in comp]
        return (-len(comp), min(xs) if xs else 0.0)

    components.sort(key=_key)
    return components


def offset_layout(
    layout: dict[str, AxialCoord],
    *,
    dq: int,
    dr: int,
) -> dict[str, AxialCoord]:
    """Shift every cell in *layout* by ``(dq, dr)``.

    Used by the multi-component pipeline after each per-component
    placement, to position the sub-grid in the final output.
    """
    return {code: (q + dq, r + dr) for code, (q, r) in layout.items()}


def _group_bounding_box(layout: dict[str, AxialCoord]) -> tuple[int, int, int, int]:
    """Return ``(min_q, min_r, max_q, max_r)`` for a layout (inclusive)."""
    qs = [q for q, _ in layout.values()]
    rs = [r for _, r in layout.values()]
    return min(qs), min(rs), max(qs), max(rs)


def stitch_components(
    component_layouts: list[dict[str, AxialCoord]],
    *,
    component_gap: int = 1,
) -> dict[str, AxialCoord]:
    """Combine per-component layouts into one, separated by ``component_gap`` cells.

    Components are laid out left-to-right in the order received (which
    :func:`find_components` already biases by size). Each subsequent
    component's q-axis starts ``component_gap`` cells past the previous
    component's max q.
    """
    if not component_layouts:
        return {}
    if component_gap < 0:
        raise ValueError(f"component_gap must be >= 0, got {component_gap}")

    final: dict[str, AxialCoord] = {}
    cursor_q = 0
    for layout in component_layouts:
        if not layout:
            continue
        min_q, _, max_q, _ = _group_bounding_box(layout)
        # Shift this component's min_q to cursor_q.
        shifted = offset_layout(layout, dq=cursor_q - min_q, dr=0)
        final.update(shifted)
        cursor_q = cursor_q + (max_q - min_q) + 1 + component_gap
    return final

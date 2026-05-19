"""S2 cell-grid utilities.

Sibling of :mod:`siege_utilities.geo.h3_utils`. Where H3 gives you uniform
hexagonal cells at a single resolution, S2 gives you square cells with
**integer IDs that sort by spatial proximity**. The same lat/lon-to-cell
operations are mirrored across both modules; the S2-specific functions
exposed here (cell-id ↔ uint64, bbox-to-cells, parent/children, region
cover with cell-count budget, range-bound generation for SQL) are the
reason to reach for S2 rather than H3.

Why both
--------

================================  ===========================  ===========================
Use case                          Reach for                    Why
================================  ===========================  ===========================
Density choropleth, hex-bins      H3                           Uniform cell area
K-nearest-neighbors via k-ring    H3                           Uniform neighbor distances
Spatial primary key in DB         S2                           Sortable int64 IDs
Bbox / range queries in SQL       S2                           Cell-id ranges = bboxes
Hierarchical rollups              S2                           4 children per cell, clean
Apple Photos / iOS data           S2                           Native to that ecosystem
================================  ===========================  ===========================

Polygon coverage limitation
---------------------------
The pure-Python ``s2sphere`` package supports ``LatLngRect`` (bounding
boxes) but **not** the full ``Loop`` / ``Polygon`` types from C++ S2.
:func:`s2_index_polygon` covers the polygon's *bounding box* and
optionally post-filters cells against the actual geometry using shapely.
For a heavily concave polygon (e.g. Idaho), the bbox cover is loose; the
post-filter step (default on) trims cells whose centers fall outside.

Requires: s2sphere>=0.2.5.
"""

from __future__ import annotations

import logging
import math
from collections.abc import Iterable
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:  # pragma: no cover
    # pandas is only needed for the DataFrame-batch helpers (e.g.
    # s2_index_points, s2_spatial_join). Cell-level functions —
    # s2_cell_to_boundary, s2_kring, s2_parent / _children, the ID
    # converters — work without it. We don't want `pip install
    # siege-utilities[s2]` to require pandas just to import this module,
    # so the actual import lives inside the functions that need it.
    import pandas as pd

log = logging.getLogger(__name__)

try:
    import s2sphere as _s2
    S2_AVAILABLE = True
except ImportError:
    _s2 = None  # type: ignore[assignment]
    S2_AVAILABLE = False
    log.info("s2sphere not available — S2 grid functions will raise ImportError")


__all__ = [
    "S2_AVAILABLE",
    "ADMIN_LEVEL_AVG_AREA_KM2",
    "S2_LEVEL_AREA_KM2",
    "s2_index_points",
    "s2_index_polygon",
    "s2_region_cover",
    "s2_spatial_join",
    "s2_cell_to_boundary",
    "s2_level_for_area",
    "s2_level_for_admin_level",
    "s2_kring",
    "s2_distance",
    "s2_parent",
    "s2_children",
    "s2_cell_id_to_uint64",
    "s2_uint64_to_cell_id",
    "s2_cell_id_to_token",
    "s2_token_to_cell_id",
    "s2_bbox_to_cells",
    "s2_cells_to_ranges",
]


def _require_s2():
    if not S2_AVAILABLE:
        raise ImportError(
            "s2sphere is required for S2 grid operations. Install with: "
            "pip install 'siege-utilities[s2]' or pip install 's2sphere>=0.2.5'."
        )


# ---------------------------------------------------------------------------
# Reference tables
# ---------------------------------------------------------------------------

# Average S2 cell area per level. Source: https://s2geometry.io/resources/s2cell_statistics
# (ratio of min to max within a level is ~1.4×; the average is what we use
# for "what level approximately matches a target area" decisions, mirroring
# the H3 _H3_RESOLUTION_AREA_KM2 table in h3_utils).
S2_LEVEL_AREA_KM2 = {
    0: 85_011_012.19,
    1: 21_252_753.05,
    2: 6_073_647.27,
    3: 1_517_403.93,
    4: 379_172.62,
    5: 94_899.62,
    6: 23_775.37,
    7: 5_944.13,
    8: 1_485.37,
    9: 371.39,
    10: 92.85,
    11: 23.21,
    12: 5.80,
    13: 1.45,
    14: 0.36,
    15: 0.0904,
    16: 0.0226,
    17: 0.00565,
    18: 0.00141,
    19: 0.000353,
    20: 0.0000882,
    21: 0.0000220,
    22: 0.0000055,
    23: 0.00000138,
    24: 0.00000034,
    25: 0.00000009,
    26: 0.00000002,
    27: 0.00000001,
    28: 0.000000001,
    29: 0.0000000003,
    30: 0.00000000007,
}

# Same admin-level table the H3 module uses; S2 just picks a different
# level from the same target areas.
ADMIN_LEVEL_AVG_AREA_KM2 = {
    "state": 196_600.0,
    "county": 3_000.0,
    "zcta": 110.0,
    "tract": 5.0,
    "block_group": 1.0,
    "block": 0.04,
}

_ADMIN_LEVEL_ALIASES = {
    "states": "state", "us_state": "state",
    "counties": "county", "us_county": "county",
    "zip": "zcta", "zip_code": "zcta", "zipcode": "zcta", "zctas": "zcta",
    "tracts": "tract", "census_tract": "tract",
    "bg": "block_group", "block_groups": "block_group", "blockgroup": "block_group",
    "blocks": "block", "census_block": "block",
}


def s2_level_for_area(target_area_km2: float) -> int:
    """Suggest the S2 level whose average cell area matches *target_area_km2*.

    Comparison is in log-space, mirroring :func:`h3_resolution_for_area`.
    """
    _require_s2()
    if target_area_km2 <= 0:
        raise ValueError(f"target_area_km2 must be positive, got {target_area_km2}")
    log_target = math.log10(target_area_km2)
    best_level = 0
    best_diff = float("inf")
    for level, area in S2_LEVEL_AREA_KM2.items():
        diff = abs(math.log10(area) - log_target)
        if diff < best_diff:
            best_diff = diff
            best_level = level
    return best_level


def s2_level_for_admin_level(level: str) -> int:
    """Suggest an S2 level whose average cell area matches a US admin level.

    Same admin levels recognised by :func:`h3_resolution_for_admin_level`
    (state / county / zcta / tract / block_group / block, with the usual
    aliases). Returns the S2 level that's closest in log-space.
    """
    _require_s2()
    normalized = level.strip().lower()
    canonical = _ADMIN_LEVEL_ALIASES.get(normalized, normalized)
    if canonical not in ADMIN_LEVEL_AVG_AREA_KM2:
        valid = sorted(ADMIN_LEVEL_AVG_AREA_KM2)
        raise ValueError(
            f"Unknown admin level {level!r}. Recognised levels: {valid}."
        )
    return s2_level_for_area(ADMIN_LEVEL_AVG_AREA_KM2[canonical])


# ---------------------------------------------------------------------------
# Point indexing
# ---------------------------------------------------------------------------

def s2_index_points(
    df: "pd.DataFrame",
    lat_col: str,
    lon_col: str,
    level: int = 12,
    *,
    as_token: bool = True,
) -> "pd.Series":
    """Compute the S2 cell ID for each point.

    Args:
        df: DataFrame with latitude / longitude columns.
        lat_col: Name of the latitude column.
        lon_col: Name of the longitude column.
        level: S2 level (0–30). Default 12 (~5.8 km² per cell).
        as_token: If True (default), return the cell as a 16-char hex
            *token* string (compact, human-readable, JSON-safe). If
            False, return the int64 cell ID (sortable, ideal for
            database keys). Both round-trip via the
            :func:`s2_cell_id_to_token` / :func:`s2_token_to_cell_id`
            helpers.

    Returns:
        ``pd.Series`` indexed like the input. Name: ``"s2_index"``.

    Raises:
        ImportError: If s2sphere is not installed.
        ValueError: If level is out of range or columns are missing.
    """
    _require_s2()
    _validate_level(level)
    for col in (lat_col, lon_col):
        if col not in df.columns:
            raise ValueError(f"Column '{col}' not found in DataFrame")

    def _one(row) -> object:
        ll = _s2.LatLng.from_degrees(row[lat_col], row[lon_col])
        cell = _s2.CellId.from_lat_lng(ll).parent(level)
        return cell.to_token() if as_token else cell.id()

    out = df.apply(_one, axis=1)
    out.name = "s2_index"
    return out


def s2_index_polygon(
    geometry,
    level: int = 12,
    *,
    refine: bool = True,
) -> set:
    """Return the set of S2 cells at *level* covering *geometry*.

    Single-level coverage — symmetric with :func:`h3_index_polygon`. For
    variable-resolution coverage with a cell-count budget, see
    :func:`s2_region_cover`.

    Because the pure-Python ``s2sphere`` lacks polygon support, this
    function covers the polygon's *bounding box* and (by default) post-
    filters the result to cells whose centers fall inside the actual
    geometry, using shapely. Set ``refine=False`` to skip the filter
    when the input is a near-rectangle (e.g. a county) and you want the
    bbox cover unchanged.

    Args:
        geometry: A shapely Polygon / MultiPolygon, or a GeoJSON-like dict.
        level: S2 level (0–30). All returned cells are at this level.
        refine: Filter cells by checking whether the cell center lies
            inside the polygon (default True).

    Returns:
        ``set`` of int64 cell IDs.

    Raises:
        ImportError: If s2sphere (or shapely, when refine=True) is missing.
        ValueError: If level is out of range.
        TypeError: If geometry can't be converted to a shapely shape.
    """
    _require_s2()
    _validate_level(level)
    poly = _coerce_polygon(geometry)
    minx, miny, maxx, maxy = poly.bounds

    coverer = _s2.RegionCoverer()
    coverer.min_level = level
    coverer.max_level = level
    coverer.max_cells = 1_000_000  # effectively unlimited at fixed level
    rect = _s2.LatLngRect(
        _s2.LatLng.from_degrees(miny, minx),
        _s2.LatLng.from_degrees(maxy, maxx),
    )
    covering = coverer.get_covering(rect)
    cells = set()
    for cell_id in covering:
        if cell_id.level() != level:
            # RegionCoverer occasionally returns coarser cells when a
            # single coarse cell exactly covers the bbox at min_level;
            # expand them to the requested level.
            for child in _expand_to_level(cell_id, level):
                cells.add(child)
        else:
            cells.add(cell_id.id())

    if not refine:
        return cells

    # shapely-based refine: keep only cells whose centers are inside.
    from shapely.geometry import Point
    refined = set()
    for cid in cells:
        center_ll = _s2.CellId(cid).to_lat_lng()
        pt = Point(center_ll.lng().degrees, center_ll.lat().degrees)
        if poly.contains(pt) or poly.touches(pt):
            refined.add(cid)
    return refined


def s2_region_cover(
    geometry,
    *,
    min_level: int = 0,
    max_level: int = 30,
    max_cells: int = 100,
) -> list[int]:
    """Cover *geometry*'s bounding box with at most *max_cells* S2 cells.

    The S2-specific operation: returns a *mixed-resolution* set of cells
    that together cover the bounding box, preferring coarse cells in the
    interior and fine cells along boundaries. The output is what you
    want for a database-side spatial-index lookup.

    Use :func:`s2_cells_to_ranges` to turn the result into ``(min, max)``
    int64 ranges suitable for a SQL ``BETWEEN`` clause.

    Args:
        geometry: shapely shape or GeoJSON dict.
        min_level: Minimum S2 level the coverer may use.
        max_level: Maximum S2 level the coverer may use.
        max_cells: Cell-count budget. The coverer returns at most this
            many cells (often fewer).

    Returns:
        A list of int64 cell IDs at varying levels, ordered as the
        coverer produced them (sortable but not sorted).
    """
    _require_s2()
    _validate_level(min_level)
    _validate_level(max_level)
    if min_level > max_level:
        raise ValueError(
            f"min_level ({min_level}) must be <= max_level ({max_level})"
        )
    if max_cells < 1:
        raise ValueError(f"max_cells must be >= 1, got {max_cells}")

    poly = _coerce_polygon(geometry)
    minx, miny, maxx, maxy = poly.bounds
    coverer = _s2.RegionCoverer()
    coverer.min_level = min_level
    coverer.max_level = max_level
    coverer.max_cells = max_cells
    rect = _s2.LatLngRect(
        _s2.LatLng.from_degrees(miny, minx),
        _s2.LatLng.from_degrees(maxy, maxx),
    )
    return [c.id() for c in coverer.get_covering(rect)]


def s2_cells_to_ranges(cell_ids: Iterable[int]) -> list[tuple[int, int]]:
    """Convert cell IDs to ``(range_min, range_max)`` pairs for SQL.

    Each S2 cell, regardless of level, has a contiguous range of leaf
    cell IDs that lie within it: ``[cell.range_min, cell.range_max]``.
    Pre-computing those ranges lets a SQL query test "is point's cell
    inside this region" with a simple ``WHERE leaf_cell_id BETWEEN min
    AND max`` (one comparison per cell in the cover, no spatial library
    needed at query time).
    """
    _require_s2()
    out = []
    for cid in cell_ids:
        cell = _s2.CellId(cid)
        out.append((cell.range_min().id(), cell.range_max().id()))
    return out


# ---------------------------------------------------------------------------
# Spatial join (lite point-in-polygon via S2 cell matching)
# ---------------------------------------------------------------------------

def s2_spatial_join(
    points_df: "pd.DataFrame",
    polygons_gdf,
    lat_col: str,
    lon_col: str,
    level: int = 12,
    polygon_id_col: Optional[str] = None,
) -> "pd.DataFrame":
    """Join points to polygons via S2 cell matching (approximate PiP).

    Same shape as :func:`h3_spatial_join`. Points and polygons sharing
    a cell are joined; polygons are decomposed into S2 cells via
    :func:`s2_index_polygon`. First-polygon-wins on overlap.
    """
    _require_s2()
    _validate_level(level)
    import pandas as pd  # local import; see TYPE_CHECKING note at top
    point_cells = s2_index_points(points_df, lat_col, lon_col, level, as_token=False)
    indexed = points_df.copy()
    indexed["_s2_index"] = point_cells

    cell_to_polygon: dict = {}
    polygon_attrs: dict = {}
    for idx, row in polygons_gdf.iterrows():
        poly_id = row[polygon_id_col] if polygon_id_col else idx
        cells = s2_index_polygon(row["geometry"], level)
        polygon_attrs[poly_id] = {
            col: row[col] for col in polygons_gdf.columns if col != "geometry"
        }
        for cid in cells:
            cell_to_polygon.setdefault(cid, poly_id)

    indexed["_poly_id"] = indexed["_s2_index"].map(cell_to_polygon)
    matched = indexed.dropna(subset=["_poly_id"]).copy()
    if matched.empty:
        for col in (c for c in polygons_gdf.columns if c != "geometry"):
            matched[col] = pd.Series(dtype="object")
        matched.drop(columns=["_s2_index", "_poly_id"], inplace=True)
        return matched

    poly_attr_df = pd.DataFrame.from_dict(polygon_attrs, orient="index")
    poly_attr_df.index.name = "_poly_id"
    poly_attr_df = poly_attr_df.reset_index()
    matched = matched.merge(poly_attr_df, on="_poly_id", how="left")
    matched.drop(columns=["_s2_index", "_poly_id"], inplace=True)
    return matched.reset_index(drop=True)


# ---------------------------------------------------------------------------
# Cell metadata
# ---------------------------------------------------------------------------

def s2_cell_to_boundary(cell_id) -> list[tuple[float, float]]:
    """Return the 4 vertex coordinates of a cell as ``(lat, lng)`` tuples.

    Accepts an int64 cell ID or a hex token string.
    """
    _require_s2()
    cid = _coerce_cell_id(cell_id)
    cell = _s2.Cell(cid)
    out = []
    for i in range(4):
        ll = _s2.LatLng.from_point(cell.get_vertex(i))
        out.append((ll.lat().degrees, ll.lng().degrees))
    return out


def s2_kring(cell_id, k: int = 1) -> list[int]:
    """Return cell IDs within k steps of *cell_id* on the same level.

    The k-ring is approximate for S2 (squares don't tile uniformly); we
    walk neighbors recursively. For exact k-ring on a uniform grid use
    :func:`h3_kring` instead.
    """
    _require_s2()
    if k < 0:
        raise ValueError(f"k must be >= 0, got {k}")
    cid = _coerce_cell_id(cell_id)
    seen = {cid.id()}
    frontier = {cid}
    for _ in range(k):
        next_frontier = set()
        for c in frontier:
            for n in c.get_all_neighbors(c.level()):
                if n.id() not in seen:
                    seen.add(n.id())
                    next_frontier.add(n)
        frontier = next_frontier
    return sorted(seen)


def s2_distance(a, b) -> int:
    """Edge-step distance between two S2 cells at the same level.

    Counts cell-boundary crossings via repeated neighbor expansion until
    *b* is reached. ``O(distance)``; use only for small radii. For large
    distances, switch to great-circle distance on the cell centers.
    """
    _require_s2()
    a_id = _coerce_cell_id(a)
    b_id = _coerce_cell_id(b)
    if a_id.level() != b_id.level():
        raise ValueError(
            f"s2_distance: a is at level {a_id.level()}, b is at level "
            f"{b_id.level()}; level must match."
        )
    if a_id == b_id:
        return 0
    target = b_id.id()
    seen = {a_id.id()}
    frontier = {a_id}
    for d in range(1, 1_000_000):  # generous upper bound
        next_frontier = set()
        for c in frontier:
            for n in c.get_all_neighbors(c.level()):
                if n.id() == target:
                    return d
                if n.id() not in seen:
                    seen.add(n.id())
                    next_frontier.add(n)
        frontier = next_frontier
        if not frontier:
            raise ValueError("s2_distance: cells appear disconnected")
    raise ValueError("s2_distance: exceeded search budget")


def s2_parent(cell_id, level: int) -> int:
    """Return the ancestor cell at *level* (must be ≤ current level)."""
    _require_s2()
    cid = _coerce_cell_id(cell_id)
    if level > cid.level():
        raise ValueError(
            f"s2_parent: target level {level} > current level {cid.level()}; "
            "use s2_children for refinement."
        )
    return cid.parent(level).id()


def s2_children(cell_id) -> list[int]:
    """Return the four immediate children of a cell.

    Raises if called on a leaf cell (level 30).
    """
    _require_s2()
    cid = _coerce_cell_id(cell_id)
    if cid.level() >= 30:
        raise ValueError("s2_children: cell is at leaf level (30); no children.")
    return [c.id() for c in cid.children()]


# ---------------------------------------------------------------------------
# ID format conversions
# ---------------------------------------------------------------------------

def s2_cell_id_to_uint64(cell_or_token) -> int:
    """Return the int64 form of a cell, accepting either a token or an id.

    Useful when receiving a token string (e.g. ``"88891b"``) and needing
    the integer for a database column. Accepts any integer-like type
    (Python int, numpy.int64, numpy.uint64) for round-trip convenience.
    """
    _require_s2()
    if isinstance(cell_or_token, str):
        return _s2.CellId.from_token(cell_or_token).id()
    try:
        return int(cell_or_token)
    except (TypeError, ValueError) as exc:
        raise TypeError(
            f"Expected int64 cell id or hex token string, got "
            f"{type(cell_or_token).__name__}"
        ) from exc


def s2_uint64_to_cell_id(n: int):
    """Return an :class:`s2sphere.CellId` from an int64 value."""
    _require_s2()
    return _s2.CellId(int(n))


def s2_cell_id_to_token(cell_id) -> str:
    """Return the compact hex token form of a cell.

    Tokens are stable, JSON-safe, and 16 characters or fewer.
    """
    _require_s2()
    return _coerce_cell_id(cell_id).to_token()


def s2_token_to_cell_id(token: str) -> int:
    """Parse a hex token back to its int64 cell ID."""
    _require_s2()
    return _s2.CellId.from_token(token).id()


# ---------------------------------------------------------------------------
# Bbox helpers
# ---------------------------------------------------------------------------

def s2_bbox_to_cells(
    min_lat: float, min_lon: float, max_lat: float, max_lon: float,
    *,
    max_level: int = 18,
    max_cells: int = 64,
) -> list[int]:
    """Cover an axis-aligned bounding box with at most *max_cells* cells.

    Convenience wrapper around :func:`s2_region_cover` for the common
    case of a map-viewport query. Returns int64 cell IDs at varying
    levels.
    """
    _require_s2()
    _validate_level(max_level)
    if max_cells < 1:
        raise ValueError(f"max_cells must be >= 1, got {max_cells}")
    coverer = _s2.RegionCoverer()
    coverer.min_level = 0
    coverer.max_level = max_level
    coverer.max_cells = max_cells
    rect = _s2.LatLngRect(
        _s2.LatLng.from_degrees(min_lat, min_lon),
        _s2.LatLng.from_degrees(max_lat, max_lon),
    )
    return [c.id() for c in coverer.get_covering(rect)]


# ---------------------------------------------------------------------------
# Helpers (private)
# ---------------------------------------------------------------------------

def _validate_level(level: int) -> None:
    if not 0 <= level <= 30:
        raise ValueError(f"S2 level must be 0-30, got {level}")


def _coerce_cell_id(value):
    """Accept int, str token, or :class:`CellId`; return CellId.

    Accepts any integer-like type (int, numpy.int64, numpy.uint64, etc.)
    via the ``__int__`` protocol — pandas-derived cell IDs come back as
    numpy types which would otherwise fail an ``isinstance(value, int)``
    check.
    """
    if isinstance(value, _s2.CellId):
        return value
    if isinstance(value, str):
        return _s2.CellId.from_token(value)
    # Try integer-like (covers Python int, numpy.int64, numpy.uint64).
    try:
        return _s2.CellId(int(value))
    except (TypeError, ValueError) as exc:
        raise TypeError(
            f"Expected CellId, int64, or token string, got "
            f"{type(value).__name__}"
        ) from exc


_POLYGON_TYPES = ("Polygon", "MultiPolygon")


def _coerce_polygon(geometry):
    """Convert input to a shapely Polygon / MultiPolygon.

    Rejects Point / LineString / GeometryCollection — they have ``.bounds``
    and ``.contains`` so a duck-typed check would let them through, but
    a Point's bbox is degenerate and ``s2_index_polygon`` would silently
    return the wrong cells.
    """
    try:
        from shapely.geometry import shape, mapping  # noqa: F401
    except ImportError as exc:
        raise ImportError(
            "shapely is required for S2 polygon coverage. Install with: "
            "pip install 'siege-utilities[geo]' or pip install 'shapely>=2.0'."
        ) from exc

    # Convert to a shapely object first.
    if isinstance(geometry, dict):
        from shapely.geometry import shape
        candidate = shape(geometry)
    elif hasattr(geometry, "__geo_interface__"):
        from shapely.geometry import shape
        candidate = shape(geometry.__geo_interface__)
    elif hasattr(geometry, "geom_type") and hasattr(geometry, "bounds"):
        candidate = geometry  # already a shapely shape
    else:
        raise TypeError(
            f"Cannot coerce {type(geometry).__name__} to a polygon. "
            "Provide a shapely shape or a GeoJSON dict."
        )

    # Now enforce the polygon type — duck typing is too permissive here.
    geom_type = getattr(candidate, "geom_type", None)
    if geom_type not in _POLYGON_TYPES:
        raise TypeError(
            f"S2 polygon coverage requires a Polygon or MultiPolygon, got "
            f"{geom_type!r}. Convert points/lines via .buffer(...) first if "
            "you want a non-zero-area region."
        )
    return candidate


def _expand_to_level(cell_id, target_level: int) -> Iterable[int]:
    """Walk children until reaching *target_level*; yields int64 IDs."""
    if cell_id.level() == target_level:
        yield cell_id.id()
        return
    if cell_id.level() > target_level:
        # Caller asked for a coarser cell than the input; just yield
        # the parent at target_level.
        yield cell_id.parent(target_level).id()
        return
    stack = [cell_id]
    while stack:
        c = stack.pop()
        if c.level() == target_level:
            yield c.id()
        else:
            stack.extend(c.children())

"""Grid-agnostic dispatch wrappers over H3 and S2.

Lets consumer code call :func:`index_points` / :func:`index_polygon`
without committing to one grid system at the call site. The wrappers
infer the grid from which keyword arguments are present, with explicit
override via ``grid="h3"`` or ``grid="s2"``.

Inference rules (applied in order):

    1. If ``grid=`` is passed → that wins.
    2. Else if any S2-only kwarg is present (``max_cells``, ``min_level``,
       ``max_level``, ``level``) → S2.
    3. Else if ``resolution=`` is present → H3.
    4. Else → H3 (the more common viz path).

Mixing ``resolution=`` with S2-only kwargs in one call raises
:class:`ValueError` rather than guessing — the caller should pass
``grid=`` explicitly to disambiguate.

These wrappers exist to keep ``reporting/`` and consumer modules
backend-agnostic; they don't add functionality beyond what the underlying
``h3_utils`` / ``s2_utils`` modules already do.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

import pandas as pd

log = logging.getLogger(__name__)

__all__ = [
    "Grid",
    "index_points",
    "index_polygon",
    "infer_grid",
]

#: Recognised ``grid=`` argument values. ``None`` means "infer".
Grid = Optional[str]  # Literal["h3", "s2", None] in 3.8+ — staying loose for older callers

_S2_ONLY_KWARGS = frozenset({"max_cells", "min_level", "max_level", "level"})
_H3_ONLY_KWARGS = frozenset({"resolution"})


def infer_grid(grid: Grid, kwargs: dict) -> str:
    """Resolve ``grid=`` per the documented inference rules.

    Returns ``"h3"`` or ``"s2"``; raises :class:`ValueError` on
    ambiguous input. Pure function — does not mutate *kwargs*.
    """
    if grid is not None:
        if grid not in ("h3", "s2"):
            raise ValueError(f"grid must be 'h3' or 's2' (or None), got {grid!r}")
        return grid

    has_s2 = any(k in kwargs and kwargs[k] is not None for k in _S2_ONLY_KWARGS)
    has_h3 = any(k in kwargs and kwargs[k] is not None for k in _H3_ONLY_KWARGS)

    if has_s2 and has_h3:
        raise ValueError(
            "Ambiguous: passed both H3 (resolution) and S2 (level / max_cells) "
            "kwargs in one call. Pass grid='h3' or grid='s2' explicitly."
        )
    if has_s2:
        return "s2"
    if has_h3:
        return "h3"
    return "h3"  # default: visualization-friendly


def index_points(
    df: pd.DataFrame,
    lat_col: str,
    lon_col: str,
    *,
    grid: Grid = None,
    resolution: Optional[int] = None,
    level: Optional[int] = None,
    **kwargs: Any,
) -> pd.Series:
    """Compute a grid cell ID for each row in *df*.

    Dispatches to :func:`h3_index_points` or :func:`s2_index_points`
    based on the inference rules. Pass ``resolution=`` for H3 (default
    8) or ``level=`` for S2 (default 12). Extra keyword arguments are
    forwarded to the underlying function (e.g. ``as_token=False`` for
    S2).

    Returns:
        ``pd.Series`` of cell IDs (H3 hex strings or S2 cell tokens by
        default).
    """
    chosen = infer_grid(grid, {"resolution": resolution, "level": level})
    if chosen == "h3":
        from .h3_utils import h3_index_points
        if level is not None and resolution is None:
            # Caller asked for grid='h3' but used 'level'; honour it.
            resolution = level
        return h3_index_points(df, lat_col, lon_col, resolution or 8)
    else:
        from .s2_utils import s2_index_points
        if resolution is not None and level is None:
            level = resolution
        return s2_index_points(df, lat_col, lon_col, level or 12, **kwargs)


def index_polygon(
    geometry,
    *,
    grid: Grid = None,
    resolution: Optional[int] = None,
    level: Optional[int] = None,
    max_cells: Optional[int] = None,
    min_level: Optional[int] = None,
    max_level: Optional[int] = None,
    refine: bool = True,
):
    """Cover a polygon with grid cells.

    With H3: returns a :class:`set` of hex IDs at the requested
    resolution (uniform).

    With S2: if ``max_cells`` is provided (or any of ``min_level``,
    ``max_level``), returns a :class:`list` of int64 cell IDs from
    :func:`s2_region_cover` (variable-resolution coverage with a cell-
    count budget). Otherwise returns a :class:`set` of int64 cell IDs
    at a single ``level`` from :func:`s2_index_polygon`.

    The shape of the return value (set vs list) intentionally signals
    which mode you got. For SQL-friendly cell-id ranges, see
    :func:`s2_cells_to_ranges`.
    """
    kwargs_for_inference = {
        "resolution": resolution,
        "level": level,
        "max_cells": max_cells,
        "min_level": min_level,
        "max_level": max_level,
    }
    chosen = infer_grid(grid, kwargs_for_inference)

    if chosen == "h3":
        from .h3_utils import h3_index_polygon
        # Caller may have used 'level' under grid='h3' — honour it.
        res = resolution if resolution is not None else level
        return h3_index_polygon(geometry, res or 8)

    # S2 path
    from .s2_utils import s2_index_polygon, s2_region_cover
    use_region_cover = max_cells is not None or min_level is not None or max_level is not None
    if use_region_cover:
        return s2_region_cover(
            geometry,
            min_level=min_level if min_level is not None else 0,
            max_level=max_level if max_level is not None else 30,
            max_cells=max_cells if max_cells is not None else 100,
        )
    # Single-level coverage
    lvl = level if level is not None else (resolution if resolution is not None else 12)
    return s2_index_polygon(geometry, lvl, refine=refine)

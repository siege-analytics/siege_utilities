"""Matplotlib renderer for hex cartograms.

Three sizing modes per the design discussion:

* ``Sizing.EQUAL`` — every hex same size. Most charming, perceptually
  honest for "states are equal political units" (NPR's pick). Default.
* ``Sizing.VALUE_PROPORTIONAL`` — hex area ∝ value. Tilegram-style.
* ``Sizing.VALUE_SQRT`` — hex side ∝ √value, perception-corrected for
  size-encoding.

The renderer takes a layout :class:`GeoDataFrame` (from
:func:`hex_tile_layout`) plus a values series indexed by code, and
returns a :class:`matplotlib.figure.Figure`.
"""

from __future__ import annotations

import enum
import logging
import math
from typing import TYPE_CHECKING, Optional, Union

from .coords import axial_to_cartesian, hexagon_polygon

if TYPE_CHECKING:  # pragma: no cover
    import geopandas as gpd
    import matplotlib.figure
    import pandas as pd

log = logging.getLogger(__name__)

__all__ = [
    "Sizing",
    "hex_tile_map",
]


class Sizing(str, enum.Enum):
    """Sizing-mode choices for :func:`hex_tile_map`."""

    #: Every hex same size; values map to colour only.
    EQUAL = "equal"
    #: Hex area proportional to value.
    VALUE_PROPORTIONAL = "value_proportional"
    #: Hex side proportional to ``√value`` (perception-correct).
    VALUE_SQRT = "value_sqrt"


def hex_tile_map(
    values: "pd.Series",
    layout: "gpd.GeoDataFrame",
    *,
    sizing: Union[Sizing, str] = Sizing.EQUAL,
    cmap: str = "viridis",
    code_col: str = "code",
    label_col: Optional[str] = "code",
    title: Optional[str] = None,
    figsize: tuple[float, float] = (10.0, 7.0),
    edge_color: str = "#888",
    missing_color: str = "#eeeeee",
) -> "matplotlib.figure.Figure":
    """Render a hex cartogram.

    Args:
        values: Values to encode, indexed by polygon code (matching the
            ``code_col`` of *layout*). Codes present in the layout but
            absent from *values* render in *missing_color*.
        layout: GeoDataFrame from :func:`hex_tile_layout` — needs at
            minimum ``code``, ``q``, ``r`` columns.
        sizing: One of :class:`Sizing` (or its string value). ``EQUAL``
            uses the layout's geometry as-is; the proportional modes
            scale per-hex around the cell center.
        cmap: matplotlib colour map name.
        code_col: Name of the code column on *layout*.
        label_col: Column to write inside each hex (typically the
            code). Pass ``None`` to omit labels.
        title / figsize / edge_color / missing_color: Standard mpl knobs.
    """
    try:
        import matplotlib.pyplot as plt
        import matplotlib.colors as mcolors
        from matplotlib.patches import Polygon as MplPolygon
    except ImportError as exc:
        raise ImportError(
            "hex_tile_map requires matplotlib. Install via "
            "'pip install siege-utilities[reporting]'."
        ) from exc

    if isinstance(sizing, str):
        sizing = Sizing(sizing)
    if code_col not in layout.columns:
        raise ValueError(
            f"hex_tile_map: code_col={code_col!r} not in layout columns"
        )

    # Align values to layout codes.
    layout_codes = [str(c) for c in layout[code_col]]
    aligned = values.reindex(layout_codes)
    finite = aligned.dropna()
    if len(finite) == 0:
        log.warning(
            "hex_tile_map: no values aligned with the layout — every hex "
            "will render as 'missing'."
        )
        vmin, vmax = 0.0, 1.0
    else:
        vmin = float(finite.min())
        vmax = float(finite.max())
        if vmin == vmax:
            # Avoid divide-by-zero in the normalizer.
            vmax = vmin + 1.0

    # Sizing scale per hex.
    if sizing == Sizing.EQUAL:
        def scale_for(v: float) -> float:
            return 1.0
    elif sizing == Sizing.VALUE_PROPORTIONAL:
        # Area ∝ value → side ∝ √(value / max). Tilegram-style; faithful
        # to the data but the eye reads area non-linearly.
        v_max = max(abs(vmax), 1e-9)
        def scale_for(v: float) -> float:
            return math.sqrt(max(v, 0.0) / v_max) if v == v else 0.0
    elif sizing == Sizing.VALUE_SQRT:
        # Perception-correct: human area perception scales sublinearly
        # with true area, so to make perceived size track value linearly
        # we want area ∝ √value ⇒ side ∝ value^(1/4).
        v_max = max(abs(vmax), 1e-9)
        def scale_for(v: float) -> float:
            return (max(v, 0.0) / v_max) ** 0.25 if v == v else 0.0
    else:  # pragma: no cover - exhaustive enum
        raise ValueError(f"Unknown sizing mode: {sizing!r}")

    norm = mcolors.Normalize(vmin=vmin, vmax=vmax)
    cmap_obj = plt.get_cmap(cmap)

    fig, ax = plt.subplots(figsize=figsize)
    ax.set_aspect("equal")
    ax.set_axis_off()
    if title is not None:
        ax.set_title(title)

    # Determine grid hex size from the layout's first row geometry.
    # The hexagon_polygon call in layouts uses size=1.0 by default; we
    # respect whatever size the GeoDataFrame already has.
    # Easier: just iterate rows and re-compute polygons at the chosen
    # scale (the layout's stored geometry is the equal-size one).
    for _, row in layout.iterrows():
        code = str(row[code_col])
        q, r = int(row["q"]), int(row["r"])
        v = aligned.get(code)
        if v is None or (isinstance(v, float) and math.isnan(v)):
            face = missing_color
            scale = 1.0
        else:
            face = cmap_obj(norm(float(v)))
            scale = scale_for(float(v))
        verts = hexagon_polygon((q, r), size=1.0, scale=scale)
        ax.add_patch(MplPolygon(verts, facecolor=face, edgecolor=edge_color, lw=0.7))
        if label_col is not None and label_col in layout.columns:
            cx, cy = axial_to_cartesian((q, r))
            ax.text(
                cx, cy, str(row[label_col]),
                ha="center", va="center",
                fontsize=8, color="white" if scale > 0.6 else "black",
            )

    # Frame the figure: iterate the actual placed cells, not the
    # Cartesian product of every q with every r.
    cell_xy = [
        axial_to_cartesian((int(r["q"]), int(r["r"])))
        for _, r in layout.iterrows()
    ]
    if cell_xy:
        xs = [x for x, _ in cell_xy]
        ys = [y for _, y in cell_xy]
        pad = 1.5
        ax.set_xlim(min(xs) - pad, max(xs) + pad)
        ax.set_ylim(min(ys) - pad, max(ys) + pad)

    # Colourbar.
    sm = plt.cm.ScalarMappable(norm=norm, cmap=cmap_obj)
    sm.set_array([])
    fig.colorbar(sm, ax=ax, fraction=0.04, pad=0.02)

    return fig

"""Plain-matplotlib heatmap used when seaborn is not installed (#2041).

seaborn is an optional styling dependency. Heatmaps call ``sns.heatmap`` when
seaborn is importable and fall back to :func:`matplotlib_heatmap`, which
reproduces seaborn's layout: cells on a unit grid with the first row at the
top, tick labels centred on cells, axis labels from the index/column names,
per-cell annotations with a contrasting text colour, and a colorbar.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

__all__ = ["matplotlib_heatmap"]


def matplotlib_heatmap(
    ax: Any,
    data: Any,
    *,
    cmap: str = "YlOrRd",
    annot: bool = True,
    fmt: str = ".2g",
    linewidths: float = 0.0,
    square: bool = False,
    cbar_kws: Optional[Dict[str, Any]] = None,
) -> Any:
    """Draw ``data`` (a 2-D DataFrame) as a heatmap on ``ax``.

    Parameters mirror the subset of ``seaborn.heatmap`` the library uses.
    NaN cells are left blank and unannotated. Annotations format the original
    cell values, so ``fmt="d"`` works for integer frames.

    Returns
    -------
    matplotlib.collections.QuadMesh
        The drawn mesh (also the colorbar's mappable).
    """
    import numpy as np  # matplotlib depends on numpy, so it is present here

    raw = np.asarray(data)
    values = np.ma.masked_invalid(raw.astype(float))
    n_rows, n_cols = values.shape

    mesh = ax.pcolormesh(
        values, cmap=cmap, edgecolors="white", linewidth=linewidths,
    )
    ax.set_xlim(0, n_cols)
    ax.set_ylim(n_rows, 0)  # first row at the top, as seaborn draws it
    ax.set_xticks(np.arange(n_cols) + 0.5)
    ax.set_xticklabels([str(c) for c in data.columns])
    ax.set_yticks(np.arange(n_rows) + 0.5)
    ax.set_yticklabels([str(i) for i in data.index], rotation=0)
    ax.tick_params(length=0)
    for spine in ax.spines.values():
        spine.set_visible(False)
    if data.columns.name is not None:
        ax.set_xlabel(str(data.columns.name))
    if data.index.name is not None:
        ax.set_ylabel(str(data.index.name))
    if square:
        ax.set_aspect("equal")

    if annot:
        for (row, col), masked in np.ndenumerate(np.ma.getmaskarray(values)):
            if masked:
                continue
            r, g, b, _ = mesh.cmap(mesh.norm(values[row, col]))
            luminance = 0.2126 * r + 0.7152 * g + 0.0722 * b
            ax.text(
                col + 0.5, row + 0.5, format(raw[row, col], fmt),
                ha="center", va="center",
                color="black" if luminance > 0.408 else "white",
            )

    ax.figure.colorbar(mesh, ax=ax, **(cbar_kws or {}))
    return mesh

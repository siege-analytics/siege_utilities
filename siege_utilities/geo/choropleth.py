"""
Choropleth map creation utilities for GeoDataFrames.

Provides standalone functions that accept GeoDataFrames and return
matplotlib (fig, ax) tuples. Designed for notebooks, scripts, and
interactive exploration.

For ReportLab PDF integration, see reporting.chart_generator.ChartGenerator
which provides parallel implementations returning ReportLab Image objects.

Functions:
    create_choropleth            -- Single-variable choropleth
    create_choropleth_comparison -- Multiple variables side by side
    create_classified_comparison -- Same variable, different classification schemes
    create_bivariate_choropleth  -- Two-variable bivariate map with legend
    save_map                     -- Save figure to file with sensible defaults
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import matplotlib.figure

try:
    from siege_utilities.core.logging import log_info, log_warning
except ImportError:
    def log_info(msg): logging.getLogger(__name__).info(msg)
    def log_warning(msg): logging.getLogger(__name__).warning(msg)

log = logging.getLogger(__name__)

# Check for mapclassify (used by geopandas scheme= parameter)
try:
    import mapclassify  # noqa: F401
    HAS_MAPCLASSIFY = True
except ImportError:
    HAS_MAPCLASSIFY = False


# =============================================================================
# CONSTANTS
# =============================================================================

# Named 3x3 bivariate color schemes.
# Each list has n_classes^2 colors (9 for 3x3), ordered row-major:
# [var2_low/var1_low, var2_low/var1_mid, var2_low/var1_high,
#  var2_mid/var1_low, var2_mid/var1_mid, var2_mid/var1_high,
#  var2_high/var1_low, var2_high/var1_mid, var2_high/var1_high]

BIVARIATE_COLOR_SCHEMES: Dict[str, List[str]] = {
    'purple_blue': [
        '#e8e8e8', '#ace4e4', '#5ac8c8',
        '#dfb0d6', '#a5add3', '#5698b9',
        '#be64ac', '#8c62aa', '#3b4994',
    ],
    'teuling': [
        '#e8e8e8', '#c1a5cc', '#9972af',
        '#b8d6be', '#909eb1', '#6771a5',
        '#7fc97f', '#5db08a', '#3a9c95',
    ],
    'blue_red': [
        '#e8e8e8', '#e4acac', '#c85a5a',
        '#b8d6be', '#90b4a6', '#627f8c',
        '#7fc97f', '#5aae61', '#2d8a49',
    ],
    'green_orange': [
        '#f7f7f7', '#fdd49e', '#fc8d59',
        '#d9f0a3', '#addd8e', '#78c679',
        '#41b6c4', '#225ea8', '#253494',
    ],
}

# Human-readable labels for mapclassify classification schemes.
SCHEME_LABELS: Dict[str, str] = {
    'quantiles': 'Quantiles (equal count)',
    'equal_interval': 'Equal Interval',
    'fisher_jenks': 'Fisher-Jenks (natural breaks)',
    'natural_breaks': 'Natural Breaks',
    'percentiles': 'Percentiles',
    'std_mean': 'Standard Deviation',
    'max_p': 'Max-P Regionalization',
    'boxplot': 'Box Plot',
    'headtailbreaks': 'Head/Tail Breaks',
}


# =============================================================================
# INTERNAL HELPERS
# =============================================================================

def _resolve_color_scheme(
    color_scheme: Union[str, List[str]],
    n_classes: int,
) -> List[str]:
    """Validate and resolve a bivariate color scheme.

    Args:
        color_scheme: Key into BIVARIATE_COLOR_SCHEMES or a raw list of hex colors.
        n_classes: Number of classes per variable. Total colors must be n_classes^2.

    Returns:
        List of hex color strings.

    Raises:
        ValueError: If scheme name is unknown or color count is wrong.
    """
    if isinstance(color_scheme, str):
        if color_scheme not in BIVARIATE_COLOR_SCHEMES:
            available = ', '.join(sorted(BIVARIATE_COLOR_SCHEMES.keys()))
            raise ValueError(
                f"Unknown bivariate color scheme '{color_scheme}'. "
                f"Available: {available}"
            )
        colors = BIVARIATE_COLOR_SCHEMES[color_scheme]
    else:
        colors = list(color_scheme)

    expected = n_classes * n_classes
    if len(colors) != expected:
        raise ValueError(
            f"Color scheme has {len(colors)} colors but "
            f"{n_classes}x{n_classes} = {expected} required"
        )
    return colors


# =============================================================================
# PUBLIC FUNCTIONS
# =============================================================================

def create_choropleth(
    gdf: gpd.GeoDataFrame,
    column: str,
    *,
    title: str = '',
    cmap: str = 'YlOrRd',
    figsize: Tuple[float, float] = (10, 12),
    legend: bool = True,
    legend_kwds: Optional[Dict] = None,
    edgecolor: str = 'black',
    linewidth: float = 0.5,
    scheme: Optional[str] = None,
    k: int = 5,
    ax: Optional[plt.Axes] = None,
    missing_kwds: Optional[Dict] = None,
) -> Tuple[matplotlib.figure.Figure, plt.Axes]:
    """Create a single-variable choropleth map.

    Args:
        gdf: GeoDataFrame with geometry and a numeric column to visualize.
        column: Column name to color by.
        title: Map title.
        cmap: Matplotlib colormap name.
        figsize: Figure size (width, height) in inches. Ignored when ax is provided.
        legend: Whether to show the color legend.
        legend_kwds: Dict passed to geopandas legend_kwds (e.g. label, shrink, format).
        edgecolor: Color of polygon edges.
        linewidth: Width of polygon edges.
        scheme: Classification scheme name (requires mapclassify). None for continuous.
        k: Number of classes when using a classification scheme.
        ax: Optional matplotlib Axes to plot onto (for subplot embedding).
        missing_kwds: Dict for styling missing/NaN geometries.

    Returns:
        (fig, ax) tuple.

    Raises:
        ImportError: If scheme is requested but mapclassify is not installed.
    """
    if scheme is not None and not HAS_MAPCLASSIFY:
        raise ImportError(
            f"Classification scheme '{scheme}' requires mapclassify. "
            f"Install it: pip install mapclassify"
        )

    if ax is None:
        fig, ax = plt.subplots(1, 1, figsize=figsize)
    else:
        fig = ax.get_figure()

    plot_kwargs = dict(
        column=column,
        ax=ax,
        legend=legend,
        cmap=cmap,
        edgecolor=edgecolor,
        linewidth=linewidth,
    )

    if legend_kwds is not None:
        plot_kwargs['legend_kwds'] = legend_kwds
    if missing_kwds is not None:
        plot_kwargs['missing_kwds'] = missing_kwds
    if scheme is not None:
        plot_kwargs['scheme'] = scheme
        plot_kwargs['k'] = k

    gdf.plot(**plot_kwargs)

    if title:
        ax.set_title(title, fontsize=14)
    ax.axis('off')

    return fig, ax


def create_choropleth_comparison(
    gdf: gpd.GeoDataFrame,
    columns: List[Dict[str, str]],
    *,
    figsize: Optional[Tuple[float, float]] = None,
    ncols: int = 3,
    edgecolor: str = 'gray',
    linewidth: float = 0.3,
) -> Tuple[matplotlib.figure.Figure, np.ndarray]:
    """Create multiple choropleths side by side.

    Args:
        gdf: GeoDataFrame with geometry and data columns.
        columns: List of dicts, each with keys:
            - 'column' (required): Column name to visualize.
            - 'title' (optional): Subplot title.
            - 'cmap' (optional): Colormap name (default 'YlOrRd').
        figsize: Figure size. If None, auto-calculated from ncols.
        ncols: Number of columns in the subplot grid.
        edgecolor: Edge color for all subplots.
        linewidth: Edge width for all subplots.

    Returns:
        (fig, axes) tuple where axes is a numpy array of Axes.
    """
    n = len(columns)
    nrows = max(1, (n + ncols - 1) // ncols)

    if figsize is None:
        figsize = (6 * ncols, 8 * nrows)

    fig, axes = plt.subplots(nrows, ncols, figsize=figsize)
    axes_flat = np.atleast_1d(axes).flat

    for i, spec in enumerate(columns):
        col = spec['column']
        title = spec.get('title', col)
        cmap = spec.get('cmap', 'YlOrRd')
        create_choropleth(
            gdf, col,
            title=title,
            cmap=cmap,
            edgecolor=edgecolor,
            linewidth=linewidth,
            legend=True,
            ax=axes_flat[i],
        )

    # Hide unused axes
    for j in range(n, nrows * ncols):
        axes_flat[j].set_visible(False)

    plt.tight_layout()
    return fig, np.atleast_1d(axes)


def create_classified_comparison(
    gdf: gpd.GeoDataFrame,
    column: str,
    schemes: List[str],
    *,
    k: int = 5,
    cmap: str = 'YlOrRd',
    figsize: Optional[Tuple[float, float]] = None,
    ncols: int = 2,
    edgecolor: str = 'black',
    linewidth: float = 0.3,
    titles: Optional[List[str]] = None,
) -> Tuple[matplotlib.figure.Figure, np.ndarray]:
    """Compare classification schemes for the same variable.

    Args:
        gdf: GeoDataFrame with geometry and a numeric column.
        column: Column name to classify and visualize.
        schemes: List of mapclassify scheme names (e.g. 'quantiles', 'fisher_jenks').
        k: Number of classes for each scheme.
        cmap: Colormap name applied to all subplots.
        figsize: Figure size. If None, auto-calculated.
        ncols: Number of columns in the subplot grid.
        edgecolor: Edge color.
        linewidth: Edge width.
        titles: Custom titles for each subplot. If None, uses SCHEME_LABELS.

    Returns:
        (fig, axes) tuple.

    Raises:
        ImportError: If mapclassify is not installed.
    """
    if not HAS_MAPCLASSIFY:
        raise ImportError(
            "Classification comparison requires mapclassify. "
            "Install it: pip install mapclassify"
        )

    n = len(schemes)
    nrows = max(1, (n + ncols - 1) // ncols)

    if figsize is None:
        figsize = (7 * ncols, 7 * nrows)

    fig, axes = plt.subplots(nrows, ncols, figsize=figsize)
    axes_flat = np.atleast_1d(axes).flat

    for i, scheme in enumerate(schemes):
        if titles is not None:
            title = titles[i]
        else:
            title = SCHEME_LABELS.get(scheme, scheme)

        create_choropleth(
            gdf, column,
            title=title,
            cmap=cmap,
            scheme=scheme,
            k=k,
            edgecolor=edgecolor,
            linewidth=linewidth,
            ax=axes_flat[i],
        )

    # Hide unused axes
    for j in range(n, nrows * ncols):
        axes_flat[j].set_visible(False)

    plt.tight_layout()
    return fig, np.atleast_1d(axes)


def create_bivariate_choropleth(
    gdf: gpd.GeoDataFrame,
    var1: str,
    var2: str,
    *,
    title: str = 'Bivariate Choropleth',
    n_classes: int = 3,
    color_scheme: Union[str, List[str]] = 'purple_blue',
    figsize: Tuple[float, float] = (14, 10),
    edgecolor: str = 'white',
    linewidth: float = 0.5,
    legend_size_ratio: float = 0.25,
) -> Tuple[matplotlib.figure.Figure, np.ndarray]:
    """Create a bivariate choropleth map showing two variables.

    Bins each variable into quantile classes and combines them into a 2D
    color index, rendered with a proper NxN legend grid.

    Args:
        gdf: GeoDataFrame with geometry and two numeric columns.
        var1: Column name for first variable (x-axis of legend).
        var2: Column name for second variable (y-axis of legend).
        title: Map title.
        n_classes: Number of quantile classes per variable (default 3 = 9 colors).
        color_scheme: Key into BIVARIATE_COLOR_SCHEMES or a raw list of hex colors.
        figsize: Figure size (width, height) in inches.
        edgecolor: Color of polygon edges.
        linewidth: Width of polygon edges.
        legend_size_ratio: Width ratio of the legend panel relative to the map.

    Returns:
        (fig, axes) tuple where axes is an array [ax_map, ax_legend].

    Raises:
        ValueError: If color scheme is unknown or has wrong number of colors.
    """
    colors = _resolve_color_scheme(color_scheme, n_classes)
    cmap = mcolors.ListedColormap(colors)

    gdf = gdf.copy()
    gdf['_var1_class'] = pd.qcut(
        gdf[var1], n_classes, labels=False, duplicates='drop'
    )
    gdf['_var2_class'] = pd.qcut(
        gdf[var2], n_classes, labels=False, duplicates='drop'
    )
    gdf['_bivar_class'] = gdf['_var1_class'] + gdf['_var2_class'] * n_classes

    fig, (ax_map, ax_legend) = plt.subplots(
        1, 2, figsize=figsize,
        gridspec_kw={'width_ratios': [1, legend_size_ratio]},
    )

    gdf.plot(
        column='_bivar_class',
        ax=ax_map,
        cmap=cmap,
        edgecolor=edgecolor,
        linewidth=linewidth,
        vmin=0,
        vmax=n_classes * n_classes - 1,
    )
    ax_map.set_title(title, fontsize=14)
    ax_map.axis('off')

    # Create NxN legend grid
    legend_array = np.arange(n_classes * n_classes).reshape(n_classes, n_classes)
    ax_legend.imshow(legend_array, cmap=cmap, origin='lower')
    ax_legend.set_xlabel(f'{var1} \u2192', fontsize=10)
    ax_legend.set_ylabel(f'{var2} \u2192', fontsize=10)
    ax_legend.set_xticks([])
    ax_legend.set_yticks([])
    ax_legend.set_title('Legend', fontsize=10)

    # Clean up temp columns
    gdf.drop(columns=['_var1_class', '_var2_class', '_bivar_class'],
             inplace=True, errors='ignore')

    plt.tight_layout()
    axes = np.array([ax_map, ax_legend])
    return fig, axes


def save_map(
    fig: matplotlib.figure.Figure,
    path: Union[str, Path],
    *,
    dpi: int = 150,
    bbox_inches: str = 'tight',
    facecolor: str = 'white',
    transparent: bool = False,
) -> Path:
    """Save a map figure to file.

    Args:
        fig: Matplotlib figure to save.
        path: Output file path (PNG, PDF, SVG, etc.).
        dpi: Resolution in dots per inch.
        bbox_inches: Bounding box ('tight' removes whitespace).
        facecolor: Background color.
        transparent: Whether to save with transparent background.

    Returns:
        Resolved Path object of the saved file.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    fig.savefig(
        str(path),
        dpi=dpi,
        bbox_inches=bbox_inches,
        facecolor=facecolor,
        transparent=transparent,
    )
    log_info(f"Map saved to: {path}")
    return path

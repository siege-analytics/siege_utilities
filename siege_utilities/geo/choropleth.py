"""
Choropleth map creation utilities for GeoDataFrames.

Provides standalone functions that accept GeoDataFrames and return
matplotlib (fig, ax) tuples. Designed for notebooks, scripts, and
interactive exploration.

For ReportLab PDF integration, see reporting.chart_generator.ChartGenerator
which provides parallel implementations returning ReportLab Image objects.

Functions:
    create_choropleth                -- Single-variable choropleth
    create_choropleth_comparison     -- Multiple variables side by side
    create_classified_comparison     -- Same variable, different classification schemes
    create_bivariate_choropleth      -- Two-variable bivariate map with legend
    create_bivariate_crosstab        -- NxN count table for bivariate bins
    create_bivariate_companion_maps  -- Side-by-side monovariate maps with same bins
    verify_bivariate_classification  -- Data-level verification of classification
    create_bivariate_analysis        -- Orchestrator returning all artifacts
    save_map                         -- Save figure to file with sensible defaults
"""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

try:
    import geopandas as gpd
    _GEOPANDAS_AVAILABLE = True
except ImportError:
    gpd = None
    _GEOPANDAS_AVAILABLE = False
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


def _format_breakpoint(value: float) -> str:
    """Format a numeric breakpoint for compact display on legend ticks.

    Examples:
        50000    → "50.0K"
        1500000  → "1.5M"
        0.034    → "0.034"
        123      → "123"
    """
    abs_val = abs(value)
    sign = '-' if value < 0 else ''
    if abs_val >= 1_000_000:
        return f"{sign}{abs_val / 1_000_000:.1f}M"
    if abs_val >= 1_000:
        return f"{sign}{abs_val / 1_000:.1f}K"
    if abs_val == 0:
        return "0"
    if abs_val < 1:
        return f"{value:.3g}"
    if abs_val == int(abs_val):
        return f"{sign}{int(abs_val)}"
    return f"{value:.1f}"


def _compute_bivariate_classes(
    gdf: gpd.GeoDataFrame,
    var1: str,
    var2: str,
    n_classes: int = 3,
) -> Tuple[gpd.GeoDataFrame, np.ndarray, np.ndarray]:
    """Compute quantile-based bivariate class assignments with breakpoints.

    Args:
        gdf: GeoDataFrame with two numeric columns.
        var1: Column name for first variable (x-axis).
        var2: Column name for second variable (y-axis).
        n_classes: Number of quantile classes per variable.

    Returns:
        Tuple of:
            - GeoDataFrame copy with columns '_var1_class', '_var2_class', '_bivar_class'
            - var1_breaks: numpy array of breakpoint values (length n_classes + 1)
            - var2_breaks: numpy array of breakpoint values (length n_classes + 1)
    """
    gdf = gdf.copy()

    _, var1_bins = pd.qcut(gdf[var1], n_classes, labels=False,
                           duplicates='drop', retbins=True)
    _, var2_bins = pd.qcut(gdf[var2], n_classes, labels=False,
                           duplicates='drop', retbins=True)

    gdf['_var1_class'] = pd.qcut(
        gdf[var1], n_classes, labels=False, duplicates='drop'
    )
    gdf['_var2_class'] = pd.qcut(
        gdf[var2], n_classes, labels=False, duplicates='drop'
    )
    gdf['_bivar_class'] = gdf['_var1_class'] + gdf['_var2_class'] * n_classes

    return gdf, np.asarray(var1_bins), np.asarray(var2_bins)


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

    classified, var1_breaks, var2_breaks = _compute_bivariate_classes(
        gdf, var1, var2, n_classes
    )

    fig, (ax_map, ax_legend) = plt.subplots(
        1, 2, figsize=figsize,
        gridspec_kw={'width_ratios': [1, legend_size_ratio]},
    )

    classified.plot(
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

    # Create NxN legend grid with magnitude tick labels
    legend_array = np.arange(n_classes * n_classes).reshape(n_classes, n_classes)
    ax_legend.imshow(legend_array, cmap=cmap, origin='lower')

    # Tick positions at cell boundaries (edges between cells + outer edges)
    tick_positions = np.arange(n_classes + 1) - 0.5
    var1_labels = [_format_breakpoint(v) for v in var1_breaks]
    var2_labels = [_format_breakpoint(v) for v in var2_breaks]

    ax_legend.set_xticks(tick_positions)
    ax_legend.set_xticklabels(var1_labels, fontsize=7, rotation=45, ha='right')
    ax_legend.set_yticks(tick_positions)
    ax_legend.set_yticklabels(var2_labels, fontsize=7)

    ax_legend.set_xlabel(f'{var1} \u2192', fontsize=10)
    ax_legend.set_ylabel(f'{var2} \u2192', fontsize=10)
    ax_legend.set_title('Legend', fontsize=10)

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


# =============================================================================
# BIVARIATE VERIFICATION ARTIFACTS
# =============================================================================

def create_bivariate_crosstab(
    gdf: gpd.GeoDataFrame,
    var1: str,
    var2: str,
    *,
    n_classes: int = 3,
    color_scheme: Union[str, List[str]] = 'purple_blue',
    render: bool = False,
    figsize: Tuple[float, float] = (6, 5),
) -> Union[pd.DataFrame, Tuple[pd.DataFrame, matplotlib.figure.Figure, plt.Axes]]:
    """Create a cross-tabulation of bivariate class counts.

    Args:
        gdf: GeoDataFrame with two numeric columns.
        var1: Column name for first variable (columns of crosstab).
        var2: Column name for second variable (rows of crosstab).
        n_classes: Number of quantile classes per variable.
        color_scheme: Key into BIVARIATE_COLOR_SCHEMES or raw list (for render colors).
        render: If True, also return a colored matplotlib figure.
        figsize: Figure size for rendered crosstab.

    Returns:
        If render=False: DataFrame with counts (n_classes rows × n_classes cols).
        If render=True: Tuple of (DataFrame, fig, ax).
    """
    classified, var1_breaks, var2_breaks = _compute_bivariate_classes(
        gdf, var1, var2, n_classes
    )

    # Build range labels from breakpoints
    def _range_labels(breaks: np.ndarray) -> List[str]:
        labels = []
        for i in range(len(breaks) - 1):
            labels.append(
                f"{_format_breakpoint(breaks[i])}\u2013{_format_breakpoint(breaks[i + 1])}"
            )
        return labels

    var1_labels = _range_labels(var1_breaks)
    var2_labels = _range_labels(var2_breaks)

    ct = pd.crosstab(
        classified['_var2_class'],
        classified['_var1_class'],
    )

    # Ensure all classes present even if empty
    for i in range(n_classes):
        if i not in ct.index:
            ct.loc[i] = 0
        if i not in ct.columns:
            ct[i] = 0
    ct = ct.sort_index(axis=0).sort_index(axis=1)

    # Apply readable labels
    ct.index = var2_labels[:ct.shape[0]]
    ct.columns = var1_labels[:ct.shape[1]]
    ct.index.name = var2
    ct.columns.name = var1

    if not render:
        return ct

    # Render colored figure
    colors = _resolve_color_scheme(color_scheme, n_classes)
    fig, ax = plt.subplots(1, 1, figsize=figsize)

    color_array = np.array(colors).reshape(n_classes, n_classes)
    for row in range(ct.shape[0]):
        for col in range(ct.shape[1]):
            cell_color = color_array[row, col]
            ax.add_patch(plt.Rectangle(
                (col, row), 1, 1, facecolor=cell_color, edgecolor='white', linewidth=1,
            ))
            count = ct.iloc[row, col]
            # Choose text color based on luminance
            rgb = mcolors.to_rgb(cell_color)
            lum = 0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2]
            text_color = 'white' if lum < 0.5 else 'black'
            ax.text(
                col + 0.5, row + 0.5, str(count),
                ha='center', va='center', fontsize=12, fontweight='bold',
                color=text_color,
            )

    ax.set_xlim(0, n_classes)
    ax.set_ylim(0, n_classes)
    ax.set_xticks(np.arange(n_classes) + 0.5)
    ax.set_xticklabels(ct.columns, fontsize=8, rotation=45, ha='right')
    ax.set_yticks(np.arange(n_classes) + 0.5)
    ax.set_yticklabels(ct.index, fontsize=8)
    ax.set_xlabel(f'{var1} \u2192', fontsize=10)
    ax.set_ylabel(f'{var2} \u2192', fontsize=10)
    ax.set_title('Bivariate Classification Crosstab', fontsize=11)
    ax.set_aspect('equal')
    plt.tight_layout()

    return ct, fig, ax


def create_bivariate_companion_maps(
    gdf: gpd.GeoDataFrame,
    var1: str,
    var2: str,
    *,
    n_classes: int = 3,
    cmap1: str = 'YlOrRd',
    cmap2: str = 'YlGnBu',
    figsize: Tuple[float, float] = (16, 8),
    edgecolor: str = 'black',
    linewidth: float = 0.3,
) -> Tuple[matplotlib.figure.Figure, np.ndarray]:
    """Create two side-by-side monovariate choropleths using the same quantile bins.

    Useful as companion maps alongside a bivariate choropleth to let readers
    see each variable independently with the same classification.

    Args:
        gdf: GeoDataFrame with geometry and two numeric columns.
        var1: Column name for first variable (left map).
        var2: Column name for second variable (right map).
        n_classes: Number of quantile classes (same as bivariate map).
        cmap1: Colormap for var1.
        cmap2: Colormap for var2.
        figsize: Figure size (width, height) in inches.
        edgecolor: Edge color.
        linewidth: Edge width.

    Returns:
        (fig, axes) tuple where axes is a numpy array of 2 Axes.
    """
    fig, axes = plt.subplots(1, 2, figsize=figsize)

    for ax, var, cmap_name in [(axes[0], var1, cmap1), (axes[1], var2, cmap2)]:
        create_choropleth(
            gdf, var,
            title=var,
            cmap=cmap_name,
            scheme='quantiles',
            k=n_classes,
            edgecolor=edgecolor,
            linewidth=linewidth,
            ax=ax,
        )

    plt.tight_layout()
    return fig, np.array(axes)


def verify_bivariate_classification(
    gdf: gpd.GeoDataFrame,
    var1: str,
    var2: str,
    *,
    n_classes: int = 3,
) -> Dict[str, Any]:
    """Verify the integrity of a bivariate quantile classification.

    Pure data function — no plotting. Checks that the classification is
    complete, breakpoints are monotonic, and counts sum correctly.

    Args:
        gdf: GeoDataFrame with two numeric columns.
        var1: Column name for first variable.
        var2: Column name for second variable.
        n_classes: Number of quantile classes per variable.

    Returns:
        Dict with keys:
            valid (bool): True if all checks pass.
            total_units (int): Total number of geographic units.
            classified_units (int): Number successfully classified.
            crosstab (pd.DataFrame): Raw count crosstab.
            var1_breaks (np.ndarray): Breakpoint values for var1.
            var2_breaks (np.ndarray): Breakpoint values for var2.
            errors (List[str]): List of error messages (empty if valid).
    """
    errors: List[str] = []

    classified, var1_breaks, var2_breaks = _compute_bivariate_classes(
        gdf, var1, var2, n_classes
    )

    total_units = len(classified)
    classified_mask = classified['_bivar_class'].notna()
    classified_units = int(classified_mask.sum())

    if classified_units != total_units:
        errors.append(
            f"Unclassified units: {total_units - classified_units} of {total_units}"
        )

    # Check breakpoints are monotonically increasing
    for name, breaks in [('var1', var1_breaks), ('var2', var2_breaks)]:
        diffs = np.diff(breaks)
        if not np.all(diffs >= 0):
            errors.append(f"{name} breakpoints are not monotonically increasing")

    # Build crosstab
    ct = pd.crosstab(classified['_var2_class'], classified['_var1_class'])
    crosstab_sum = ct.values.sum()
    if crosstab_sum != classified_units:
        errors.append(
            f"Crosstab sum ({crosstab_sum}) != classified units ({classified_units})"
        )

    return {
        'valid': len(errors) == 0,
        'total_units': total_units,
        'classified_units': classified_units,
        'crosstab': ct,
        'var1_breaks': var1_breaks,
        'var2_breaks': var2_breaks,
        'errors': errors,
    }


# =============================================================================
# BIVARIATE ANALYSIS ORCHESTRATOR
# =============================================================================

@dataclass
class BivariateAnalysisResult:
    """Container for all bivariate choropleth analysis artifacts.

    Attributes:
        bivariate_fig: Figure containing the bivariate choropleth map.
        bivariate_axes: Axes array [ax_map, ax_legend].
        crosstab: DataFrame of class-pair unit counts.
        crosstab_fig: Figure of the rendered crosstab (colored grid).
        crosstab_ax: Axes for the rendered crosstab.
        companion_fig: Figure with two monovariate companion maps.
        companion_axes: Axes array [ax_var1, ax_var2].
        verification: Dict from verify_bivariate_classification().
        var1_breaks: Breakpoint array for variable 1.
        var2_breaks: Breakpoint array for variable 2.
    """
    bivariate_fig: matplotlib.figure.Figure
    bivariate_axes: np.ndarray
    crosstab: pd.DataFrame
    crosstab_fig: matplotlib.figure.Figure
    crosstab_ax: plt.Axes
    companion_fig: matplotlib.figure.Figure
    companion_axes: np.ndarray
    verification: Dict[str, Any]
    var1_breaks: np.ndarray
    var2_breaks: np.ndarray


def create_bivariate_analysis(
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
    cmap1: str = 'YlOrRd',
    cmap2: str = 'YlGnBu',
    companion_figsize: Tuple[float, float] = (16, 8),
    crosstab_figsize: Tuple[float, float] = (6, 5),
) -> BivariateAnalysisResult:
    """Create a complete bivariate choropleth analysis with all verification artifacts.

    One call produces:
    - Bivariate choropleth map with magnitude legend
    - Rendered crosstab showing unit counts per class pair
    - Two companion monovariate maps (one per variable)
    - Verification dict confirming classification integrity

    Args:
        gdf: GeoDataFrame with geometry and two numeric columns.
        var1: Column name for first variable (x-axis).
        var2: Column name for second variable (y-axis).
        title: Title for the bivariate map.
        n_classes: Number of quantile classes per variable.
        color_scheme: Bivariate color scheme name or raw list.
        figsize: Size of the bivariate map figure.
        edgecolor: Polygon edge color on the bivariate map.
        linewidth: Polygon edge width on the bivariate map.
        legend_size_ratio: Legend panel width ratio.
        cmap1: Colormap for var1 companion map.
        cmap2: Colormap for var2 companion map.
        companion_figsize: Size of the companion maps figure.
        crosstab_figsize: Size of the rendered crosstab figure.

    Returns:
        BivariateAnalysisResult dataclass with all artifacts.
    """
    bivar_fig, bivar_axes = create_bivariate_choropleth(
        gdf, var1, var2,
        title=title,
        n_classes=n_classes,
        color_scheme=color_scheme,
        figsize=figsize,
        edgecolor=edgecolor,
        linewidth=linewidth,
        legend_size_ratio=legend_size_ratio,
    )

    ct, ct_fig, ct_ax = create_bivariate_crosstab(
        gdf, var1, var2,
        n_classes=n_classes,
        color_scheme=color_scheme,
        render=True,
        figsize=crosstab_figsize,
    )

    comp_fig, comp_axes = create_bivariate_companion_maps(
        gdf, var1, var2,
        n_classes=n_classes,
        cmap1=cmap1,
        cmap2=cmap2,
        figsize=companion_figsize,
    )

    verification = verify_bivariate_classification(
        gdf, var1, var2,
        n_classes=n_classes,
    )

    return BivariateAnalysisResult(
        bivariate_fig=bivar_fig,
        bivariate_axes=bivar_axes,
        crosstab=ct,
        crosstab_fig=ct_fig,
        crosstab_ax=ct_ax,
        companion_fig=comp_fig,
        companion_axes=comp_axes,
        verification=verification,
        var1_breaks=verification['var1_breaks'],
        var2_breaks=verification['var2_breaks'],
    )

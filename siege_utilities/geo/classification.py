"""
Pure-numpy choropleth classification schemes.

Provides map classification (quantiles, equal interval, natural breaks, etc.)
without geopandas or mapclassify. When mapclassify is available it is used
as the primary backend; when it is not, equivalent numpy implementations
provide the same bin edges and assignments.

Backend dispatch (in priority order):
1. **mapclassify** — PySAL's mapclassify library (when installed)
2. **numpy** — pure-numpy implementations (always available)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Union

import numpy as np
import pandas as pd

try:
    import mapclassify as _mc
    _MAPCLASSIFY_AVAILABLE = True
except ImportError:
    _MAPCLASSIFY_AVAILABLE = False

try:
    import matplotlib.colors as _mcolors
    import matplotlib.pyplot as _plt
    _MATPLOTLIB_AVAILABLE = True
except ImportError:
    _MATPLOTLIB_AVAILABLE = False

log = logging.getLogger(__name__)

__all__ = [
    "ClassificationResult",
    "classify_series",
    "classify_choropleth",
    "AVAILABLE_SCHEMES",
]

ArrayLike = Union[np.ndarray, pd.Series, list]


@dataclass
class ClassificationResult:
    """Result of a classification operation.

    Attributes:
        bins: Bin assignment per value (0 .. k-1). NaN inputs get -1.
        breaks: k+1 break points (bin edges, including min and max).
        k: Number of classes actually produced (may be < requested if data
            has fewer unique values).
        scheme: Scheme name used.
        backend: 'mapclassify' or 'numpy'.
    """

    bins: np.ndarray
    breaks: np.ndarray
    k: int
    scheme: str
    backend: str = ""


# ---------------------------------------------------------------------------
# Pure-numpy scheme implementations
# ---------------------------------------------------------------------------

def _classify_quantiles(values: np.ndarray, k: int) -> tuple[np.ndarray, int]:
    percentiles = np.linspace(0, 100, k + 1)
    breaks = np.percentile(values, percentiles)
    breaks = np.unique(breaks)
    actual_k = len(breaks) - 1
    return breaks, actual_k


def _classify_equal_interval(values: np.ndarray, k: int) -> tuple[np.ndarray, int]:
    breaks = np.linspace(values.min(), values.max(), k + 1)
    return breaks, k


def _classify_natural_breaks(values: np.ndarray, k: int) -> tuple[np.ndarray, int]:
    """Fisher-Jenks optimal breaks via dynamic programming."""
    sorted_vals = np.sort(values)
    n = len(sorted_vals)

    if n <= k:
        breaks = np.unique(sorted_vals)
        return np.concatenate([[sorted_vals[0]], breaks]), len(breaks)

    ssm = np.zeros((n, k), dtype=np.float64)
    bp = np.zeros((n, k), dtype=np.int64)

    cumsum = np.cumsum(sorted_vals)
    cumsum2 = np.cumsum(sorted_vals ** 2)

    def _ss(i: int, j: int) -> float:
        if i == 0:
            s = cumsum[j]
            s2 = cumsum2[j]
            cnt = j + 1
        else:
            s = cumsum[j] - cumsum[i - 1]
            s2 = cumsum2[j] - cumsum2[i - 1]
            cnt = j - i + 1
        return s2 - (s * s) / cnt

    for i in range(n):
        ssm[i, 0] = _ss(0, i)
        bp[i, 0] = 0

    for j in range(1, k):
        for i in range(j, n):
            best_cost = np.inf
            best_bp = j
            for m in range(j - 1, i):
                cost = ssm[m, j - 1] + _ss(m + 1, i)
                if cost < best_cost:
                    best_cost = cost
                    best_bp = m + 1
            ssm[i, j] = best_cost
            bp[i, j] = best_bp

    breaks_idx = [n - 1]
    kk = k - 1
    while kk > 0:
        breaks_idx.append(bp[breaks_idx[-1], kk] - 1)
        kk -= 1
    breaks_idx.reverse()

    break_values = [sorted_vals[0]]
    for idx in breaks_idx[:-1]:
        if idx + 1 < n:
            break_values.append(sorted_vals[idx + 1])
    break_values.append(sorted_vals[-1])

    breaks = np.unique(break_values)
    actual_k = len(breaks) - 1
    return breaks, actual_k


def _classify_percentiles(values: np.ndarray, k: int) -> tuple[np.ndarray, int]:
    """Fixed percentile breakpoints: [0, 1, 10, 50, 90, 99, 100]."""
    pcts = [0, 1, 10, 50, 90, 99, 100]
    breaks = np.percentile(values, pcts)
    breaks = np.unique(breaks)
    actual_k = len(breaks) - 1
    return breaks, actual_k


def _classify_std_mean(values: np.ndarray, k: int) -> tuple[np.ndarray, int]:
    """Standard deviation classification around the mean."""
    mean = values.mean()
    std = values.std()
    if std == 0:
        return np.array([values.min(), values.max()]), 1

    half = k // 2
    lower = [mean - i * std for i in range(half, 0, -1)]
    upper = [mean + i * std for i in range(1, half + 1)]
    breaks = np.array([values.min()] + lower + [mean] + upper + [values.max()])
    breaks = np.clip(breaks, values.min(), values.max())
    breaks = np.unique(breaks)
    actual_k = len(breaks) - 1
    return breaks, actual_k


def _classify_headtailbreaks(values: np.ndarray, k: int) -> tuple[np.ndarray, int]:
    """Head/tail breaks (Jiang 2013) — recursive mean splitting."""
    breaks = [values.min()]
    remaining = values.copy()
    max_iter = min(k, 40)

    for _ in range(max_iter):
        if len(remaining) < 2:
            break
        mean = remaining.mean()
        breaks.append(mean)
        head = remaining[remaining > mean]
        if len(head) == 0 or len(head) / len(remaining) >= 0.40:
            break
        remaining = head

    breaks.append(values.max())
    breaks = np.unique(breaks)
    actual_k = len(breaks) - 1
    return breaks, actual_k


def _classify_boxplot(values: np.ndarray, k: int) -> tuple[np.ndarray, int]:
    """Box plot classification: whiskers, Q1, median, Q3."""
    q1, q2, q3 = np.percentile(values, [25, 50, 75])
    iqr = q3 - q1
    lower_whisker = max(values.min(), q1 - 1.5 * iqr)
    upper_whisker = min(values.max(), q3 + 1.5 * iqr)

    breaks = np.array([values.min(), lower_whisker, q1, q2, q3, upper_whisker, values.max()])
    breaks = np.unique(breaks)
    actual_k = len(breaks) - 1
    return breaks, actual_k


_NUMPY_SCHEMES = {
    "quantiles": _classify_quantiles,
    "equal_interval": _classify_equal_interval,
    "natural_breaks": _classify_natural_breaks,
    "fisher_jenks": _classify_natural_breaks,
    "percentiles": _classify_percentiles,
    "std_mean": _classify_std_mean,
    "headtailbreaks": _classify_headtailbreaks,
    "boxplot": _classify_boxplot,
}

AVAILABLE_SCHEMES: dict[str, str] = {
    "quantiles": "Quantiles (equal count)",
    "equal_interval": "Equal Interval",
    "natural_breaks": "Natural Breaks (Fisher-Jenks)",
    "fisher_jenks": "Fisher-Jenks (natural breaks)",
    "percentiles": "Percentiles",
    "std_mean": "Standard Deviation",
    "headtailbreaks": "Head/Tail Breaks",
    "boxplot": "Box Plot",
}


# ---------------------------------------------------------------------------
# mapclassify backend
# ---------------------------------------------------------------------------

_MC_SCHEME_MAP = {
    "quantiles": "Quantiles",
    "equal_interval": "EqualInterval",
    "natural_breaks": "NaturalBreaks",
    "fisher_jenks": "FisherJenks",
    "percentiles": "Percentiles",
    "std_mean": "StdMean",
    "headtailbreaks": "HeadTailBreaks",
    "boxplot": "BoxPlot",
    "max_p": "MaxP",
}


def _classify_with_mapclassify(
    values: np.ndarray, scheme: str, k: int,
) -> ClassificationResult:
    mc_name = _MC_SCHEME_MAP.get(scheme)
    if mc_name is None:
        raise ValueError(
            f"Unknown scheme '{scheme}' for mapclassify backend. "
            f"Available: {sorted(_MC_SCHEME_MAP.keys())}"
        )

    cls = getattr(_mc, mc_name)
    if scheme in ("percentiles", "boxplot"):
        classifier = cls(values)
    else:
        classifier = cls(values, k=k)

    breaks = np.concatenate([[values.min()], classifier.bins])
    breaks = np.unique(breaks)
    actual_k = len(breaks) - 1

    bins = np.searchsorted(breaks[1:-1], values, side="right").astype(np.intp)

    return ClassificationResult(
        bins=bins,
        breaks=breaks,
        k=actual_k,
        scheme=scheme,
        backend="mapclassify",
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def classify_series(
    values: ArrayLike,
    scheme: str = "quantiles",
    k: int = 5,
) -> ClassificationResult:
    """Classify numeric values into k bins using the named scheme.

    Backend dispatch: mapclassify (when installed) → pure numpy.

    Args:
        values: Numeric array, Series, or list.
        scheme: Classification scheme name (see AVAILABLE_SCHEMES).
        k: Number of classes. Some schemes (percentiles, boxplot) ignore k.

    Returns:
        ClassificationResult with bin assignments, break points, and metadata.

    Raises:
        ValueError: If scheme is unknown or values are empty.
    """
    arr = np.asarray(values, dtype=np.float64).ravel()

    nan_mask = np.isnan(arr)
    clean = arr[~nan_mask]

    if len(clean) == 0:
        raise ValueError("Cannot classify empty or all-NaN values.")

    if k < 1:
        raise ValueError(f"k must be >= 1, got {k}")

    if len(np.unique(clean)) == 1:
        log.warning("All values are identical; producing single-bin classification.")
        bins_clean = np.zeros(len(clean), dtype=np.intp)
        breaks = np.array([clean[0], clean[0]])
        result_bins = np.full(len(arr), -1, dtype=np.intp)
        result_bins[~nan_mask] = bins_clean
        return ClassificationResult(
            bins=result_bins, breaks=breaks, k=1, scheme=scheme, backend="numpy",
        )

    if k > len(clean):
        log.warning(
            "k=%d exceeds data size (%d); reducing to %d.",
            k, len(clean), len(clean),
        )
        k = len(clean)

    if _MAPCLASSIFY_AVAILABLE and scheme in _MC_SCHEME_MAP:
        try:
            result = _classify_with_mapclassify(clean, scheme, k)
            full_bins = np.full(len(arr), -1, dtype=np.intp)
            full_bins[~nan_mask] = result.bins
            result.bins = full_bins
            log.info(
                "Classified %d values into %d bins (scheme=%s, backend=mapclassify)",
                len(clean), result.k, scheme,
            )
            return result
        except Exception:
            log.warning(
                "mapclassify failed for scheme '%s'; falling back to numpy.", scheme,
            )

    if scheme not in _NUMPY_SCHEMES:
        available = sorted(set(list(_NUMPY_SCHEMES.keys()) + (
            list(_MC_SCHEME_MAP.keys()) if _MAPCLASSIFY_AVAILABLE else []
        )))
        raise ValueError(
            f"Unknown classification scheme '{scheme}'. Available: {available}"
        )

    breaks, actual_k = _NUMPY_SCHEMES[scheme](clean, k)

    bins_clean = np.searchsorted(breaks[1:-1], clean, side="right").astype(np.intp)

    full_bins = np.full(len(arr), -1, dtype=np.intp)
    full_bins[~nan_mask] = bins_clean

    log.info(
        "Classified %d values into %d bins (scheme=%s, backend=numpy)",
        len(clean), actual_k, scheme,
    )

    return ClassificationResult(
        bins=full_bins,
        breaks=breaks,
        k=actual_k,
        scheme=scheme,
        backend="numpy",
    )


def classify_choropleth(
    df: pd.DataFrame,
    column: str,
    scheme: str = "quantiles",
    k: int = 5,
    cmap: str = "YlOrRd",
) -> pd.DataFrame:
    """Classify a DataFrame column and add bin/color columns.

    This is the non-GDAL entry point for choropleth classification. It
    produces the data layer (bin assignments + hex colors) that consumers
    render using their platform's native visualization.

    Args:
        df: DataFrame (or GeoDataFrame) with a numeric column.
        column: Column name to classify.
        scheme: Classification scheme name.
        k: Number of classes.
        cmap: Matplotlib colormap name for color assignment. Requires
            matplotlib; omitted columns if unavailable.

    Returns:
        Copy of df with added columns:
            _bin: int bin assignment (0..k-1, or -1 for NaN)
            _break_low: lower bound of the bin
            _break_high: upper bound of the bin
            _color: hex color string (if matplotlib available)

    Raises:
        ValueError: If column not in df or values are empty.
    """
    if column not in df.columns:
        raise ValueError(f"Column '{column}' not found in DataFrame.")

    result = classify_series(df[column], scheme=scheme, k=k)

    out = df.copy()
    out["_bin"] = result.bins
    out["_break_low"] = np.where(
        result.bins >= 0,
        result.breaks[np.clip(result.bins, 0, result.k - 1)],
        np.nan,
    )
    out["_break_high"] = np.where(
        result.bins >= 0,
        result.breaks[np.clip(result.bins + 1, 1, result.k)],
        np.nan,
    )

    if _MATPLOTLIB_AVAILABLE:
        colormap = _plt.get_cmap(cmap, result.k)
        colors = []
        for b in result.bins:
            if b < 0:
                colors.append("")
            else:
                rgba = colormap(b / max(result.k - 1, 1))
                colors.append(_mcolors.to_hex(rgba))
        out["_color"] = colors
    else:
        log.warning("matplotlib not available; _color column omitted.")

    return out

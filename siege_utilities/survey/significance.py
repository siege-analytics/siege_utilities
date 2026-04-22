"""
Significance testing for survey chains.

column_proportion_test: two-proportion z-test across all column pairs.
chi_square_flag: wraps data.cross_tabulation.chi_square_test.
"""

from __future__ import annotations

import string
from typing import TYPE_CHECKING

import numpy as np

from siege_utilities.core.logging import log_error

try:
    from scipy.stats import norm as _scipy_norm
    _SCIPY_AVAILABLE = True
except ImportError:
    _scipy_norm = None
    _SCIPY_AVAILABLE = False

if TYPE_CHECKING:
    from .models import Chain


class SignificanceError(RuntimeError):
    """Raised when significance testing cannot complete on the given chain."""


# Critical z-values for the scipy-less fallback. Only exact matches are honored;
# any other alpha raises rather than silently using 1.96.
_FALLBACK_Z_CRIT = {0.05: 1.96, 0.01: 2.576, 0.10: 1.645}


def column_proportion_test(chain: "Chain", alpha: float = 0.05) -> "Chain":
    """Add significance markers (letters A/B/C…) to Chain Views.

    Tests each column proportion against every other column using a
    two-proportion z-test. When column j is significantly higher than
    column i (at *alpha*), appends column i's letter to column j's
    sig_flag for that row category.

    Mutates *chain* in place and returns it.
    """
    keys = list(chain.views.keys())
    n_cols = len(keys)
    if n_cols < 2:
        return chain

    letters = list(string.ascii_uppercase)
    col_labels = {key: letters[i] for i, key in enumerate(keys)}

    # Collect per-column proportions and bases
    col_data: dict[str, dict] = {}
    for key, views in chain.views.items():
        col_data[key] = {
            "base": views[0].base if views else 0,
            "pcts": {v.metric: (v.pct if v.pct is not None else 0.0) for v in views},
        }

    # For each row category, run all pairwise tests
    all_metrics = {v.metric for views in chain.views.values() for v in views}
    for metric in all_metrics:
        for i, key_i in enumerate(keys):
            for j, key_j in enumerate(keys):
                if i >= j:
                    continue
                p1 = col_data[key_i]["pcts"].get(metric, 0.0)
                p2 = col_data[key_j]["pcts"].get(metric, 0.0)
                n1 = col_data[key_i]["base"]
                n2 = col_data[key_j]["base"]
                if n1 == 0 or n2 == 0:
                    continue
                p_pool = (p1 * n1 + p2 * n2) / (n1 + n2)
                se = np.sqrt(p_pool * (1 - p_pool) * (1 / n1 + 1 / n2))
                if se == 0:
                    continue
                z = abs(p1 - p2) / se
                if _SCIPY_AVAILABLE:
                    z_crit = _scipy_norm.ppf(1 - alpha / 2)
                elif alpha in _FALLBACK_Z_CRIT:
                    z_crit = _FALLBACK_Z_CRIT[alpha]
                else:
                    # Without scipy, only exact matches are honored — silently
                    # coercing to 1.96 would run tests at the wrong alpha and
                    # corrupt the output.
                    raise SignificanceError(
                        f"alpha={alpha!r} requires scipy; install scipy or use "
                        f"one of {sorted(_FALLBACK_Z_CRIT)}"
                    )
                if z > z_crit:
                    # Mark the higher column with the lower column's letter
                    higher_key = key_i if p1 > p2 else key_j
                    lower_label = col_labels[key_j if p1 > p2 else key_i]
                    for v in chain.views[higher_key]:
                        if v.metric == metric:
                            v.sig_flag = (v.sig_flag or "") + lower_label
                            break

    return chain


def chi_square_flag(chain: "Chain", alpha: float = 0.05) -> "Chain":
    """Add an overall chi-square flag to *chain*.

    Delegates to siege_utilities.data.cross_tabulation.chi_square_test.
    Sets chain.chi_square_significant = True/False and chain.chi_square_p.

    Mutates *chain* in place and returns it.
    """
    from ..data.cross_tabulation import chi_square_test
    import pandas as pd

    # Build count-based (not pct-based) contingency table for valid chi-square
    records: dict = {}
    for col_key, views in chain.views.items():
        if col_key == chain.delta_column:
            continue
        for v in views:
            if v.metric not in records:
                records[v.metric] = {}
            records[v.metric][col_key] = v.count

    df = pd.DataFrame.from_dict(records, orient="index").fillna(0)
    df.index.name = chain.row_var

    if "Total" in df.columns:
        df = df.drop(columns=["Total"])
    if "Total" in df.index:
        df = df.drop(index=["Total"])

    if df.empty or df.shape[0] < 2 or df.shape[1] < 2:
        chain.chi_square_significant = False  # type: ignore[attr-defined]
        chain.chi_square_p = None             # type: ignore[attr-defined]
        return chain

    try:
        result = chi_square_test(df)
    except (ValueError, TypeError, ZeroDivisionError) as e:
        # A degenerate contingency table (zeros, singleton dimensions) is
        # distinguishable from "test was run and wasn't significant" — tag
        # the result as failed rather than collapsing both cases to False.
        log_error(
            f"chi_square_test failed on chain row_var={chain.row_var!r}, "
            f"shape={df.shape}: {e}"
        )
        raise SignificanceError(
            f"chi-square test failed for chain row_var={chain.row_var!r}"
        ) from e

    chain.chi_square_significant = bool(result.p_value < alpha)
    chain.chi_square_p = float(result.p_value)
    return chain

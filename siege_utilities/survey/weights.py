"""
RIM (raking) weighting wrapper around weightipy.

Install: pip install siege-utilities[survey]
"""

from __future__ import annotations

from typing import Any, Dict, Optional

import pandas as pd


class WeightingConvergenceError(RuntimeError):
    """Raised when weightipy fails to converge within max_iterations."""


def apply_rim_weights(
    df: pd.DataFrame,
    targets: Dict[str, Dict[Any, float]],
    weight_col: str = "weight",
    max_iterations: int = 1000,
    convergence: float = 1e-6,
) -> pd.DataFrame:
    """Apply RIM (raking / iterative proportional fitting) weights.

    Adds *weight_col* to *df* in-place and returns *df*.

    Parameters
    ----------
    df:
        Respondent-level DataFrame.  Each row is one respondent.
    targets:
        Dict mapping column name → {category: proportion}.
        Proportions per variable must sum to 1.0.
        Example::

            {
                "age_group": {"18-34": 0.25, "35-54": 0.40, "55+": 0.35},
                "gender":    {"M": 0.48, "F": 0.52},
            }
    weight_col:
        Name of the weight column to add/overwrite.
    max_iterations:
        Maximum raking iterations.
    convergence:
        Convergence threshold (L-inf norm on marginal differences).

    Returns
    -------
    df with *weight_col* added/updated.

    Raises
    ------
    WeightingConvergenceError
        If weightipy fails to converge.
    ImportError
        If weightipy is not installed (pip install siege-utilities[survey]).
    """
    try:
        from weightipy import rake
    except ImportError as exc:
        raise ImportError(
            "weightipy is required for RIM weighting. "
            "Install it with: pip install siege-utilities[survey]"
        ) from exc

    result = df.copy()
    try:
        weights = rake(
            result,
            targets=targets,
            max_iterations=max_iterations,
            convergence=convergence,
        )
    except Exception as exc:
        raise WeightingConvergenceError(
            f"RIM weighting failed to converge: {exc}"
        ) from exc

    result[weight_col] = weights
    return result

"""
RIM (raking) weighting wrapper around weightipy.

Install: pip install siege-utilities[survey]

weightipy's public API uses :func:`weightipy.scheme_from_dict` + \
:func:`weightipy.weight_dataframe`; pass iteration / convergence parameters
via the :class:`weightipy.internal.rim.Rim` constructor's ``rim_params`` dict.
"""

from __future__ import annotations

from typing import Any, Dict

import pandas as pd


class WeightingConvergenceError(RuntimeError):
    """Raised when weightipy fails to converge within max_iterations."""


def apply_rim_weights(
    df: pd.DataFrame,
    targets: Dict[str, Dict[Any, float]],
    *,
    weight_col: str = "weight",
    max_iterations: int = 1000,
    convergence: float = 1e-6,
    verbose: bool = False,
) -> pd.DataFrame:
    """Apply RIM (raking / iterative proportional fitting) weights.

    Adds *weight_col* to a copy of *df* and returns the result. Does NOT
    mutate the input.

    Parameters
    ----------
    df : pd.DataFrame
        Respondent-level DataFrame; each row is one respondent.
    targets : dict
        Mapping of column name → {category: proportion}. Proportions per
        variable must sum to 1.0. Example::

            {
                "age_group": {"18-34": 0.25, "35-54": 0.40, "55+": 0.35},
                "gender":    {"M": 0.48, "F": 0.52},
            }
    weight_col : str, keyword-only, default ``"weight"``
        Column name for the computed weight values.
    max_iterations : int, keyword-only, default 1000
        Upper bound on raking iterations.
    convergence : float, keyword-only, default ``1e-6``
        Convergence threshold (``convcrit`` in weightipy terms).
    verbose : bool, keyword-only, default False
        If True, weightipy prints per-iteration progress.

    Returns
    -------
    pd.DataFrame
        Copy of *df* with *weight_col* populated.

    Raises
    ------
    ImportError
        If weightipy is not installed.
    WeightingConvergenceError
        If weightipy fails to converge.
    """
    try:
        import weightipy as wp
    except ImportError as exc:
        raise ImportError(
            "weightipy is required for RIM weighting. "
            "Install it with: pip install siege-utilities[survey]"
        ) from exc

    # Map our convergence param to weightipy's Rim-class ``convcrit`` via
    # the rim_params passthrough. See weightipy.internal.rim.Rim.__init__.
    scheme = wp.scheme_from_dict(
        targets,
        rim_params={"max_iterations": max_iterations, "convcrit": convergence},
    )

    try:
        return wp.weight_dataframe(
            df.copy(),
            scheme,
            weight_column=weight_col,
            verbose=verbose,
        )
    except (ValueError, RuntimeError) as exc:
        raise WeightingConvergenceError(
            f"RIM weighting failed (max_iterations={max_iterations}, "
            f"convergence={convergence}): {exc}"
        ) from exc

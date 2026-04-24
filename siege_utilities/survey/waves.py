"""Longitudinal analysis over a WaveSet.

Builds per-wave Chains via :func:`survey.crosstab.build_chain` and merges
them into a single LONGITUDINAL Chain whose columns are wave ids (ordered
by date). A delta column (last − first) is appended when ≥2 waves exist,
matching the single-DataFrame LONGITUDINAL builder.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Dict, List, Optional

from ..reporting.pages.page_models import TableType
from .crosstab import build_chain
from .models import Chain, View

if TYPE_CHECKING:
    from .models import WaveSet


class WavesError(ValueError):
    """Raised when a WaveSet operation is given incomplete or mismatched data."""


def compare_waves(
    waveset: "WaveSet",
    row_var: str,
    break_vars: Optional[List[str]] = None,
    *,
    metric: str = "value",
    weight_var: Optional[str] = None,
    top_n: Optional[int] = None,
) -> Chain:
    """Merge per-wave crosstabs into one LONGITUDINAL Chain.

    Parameters
    ----------
    waveset:
        The WaveSet to compare. Every Wave must have a non-None ``df``.
    row_var:
        Column whose categories become rows (same across all waves).
    break_vars:
        Optional secondary breaks applied within each wave (rare for
        wave comparison but supported). If omitted or empty, each wave
        contributes a single column keyed by wave id.
    metric, weight_var, top_n:
        Passed through to :func:`build_chain` for each wave.

    Returns
    -------
    Chain
        ``table_type == TableType.LONGITUDINAL``; ``views`` keyed by
        wave id (or ``"{wave_id}|{break_key}"`` when break_vars are used);
        ``delta_column`` set when ≥2 waves exist.

    Raises
    ------
    WavesError
        If ``waveset`` has no waves, or any wave lacks a DataFrame.
    """
    waves = waveset.ordered
    if not waves:
        raise WavesError(f"WaveSet {waveset.name!r} has no waves")
    missing = [w.id for w in waves if w.df is None]
    if missing:
        raise WavesError(
            f"WaveSet {waveset.name!r} waves missing df: {missing}. "
            "Attach respondent-level DataFrames before calling compare_chain."
        )

    use_breaks = list(break_vars) if break_vars else []
    merged: Dict[str, List[View]] = {}

    for wave in waves:
        # When no break_vars given, synthesize a single "_all" break so
        # build_chain has something to iterate. That synthetic column is
        # collapsed back into the wave id below.
        if not use_breaks:
            per_wave_df = wave.df.assign(_all="all")
            per_wave_breaks = ["_all"]
        else:
            per_wave_df = wave.df
            per_wave_breaks = use_breaks

        per_wave = build_chain(
            per_wave_df,
            row_var=row_var,
            break_vars=per_wave_breaks,
            metric=metric,
            weight_var=weight_var,
            table_type=TableType.SINGLE_RESPONSE,
            top_n=top_n,
        )

        for key, views in per_wave.views.items():
            if not use_breaks:
                merged_key = wave.id
            else:
                merged_key = f"{wave.id}|{key}"
            merged[merged_key] = views

    delta_col: Optional[str] = None
    if len(waves) >= 2 and not use_breaks:
        first_id, last_id = waves[0].id, waves[-1].id
        first_map = {v.metric: v.count for v in merged.get(first_id, [])}
        last_map = {v.metric: v.count for v in merged.get(last_id, [])}
        first_pct = {v.metric: v.pct for v in merged.get(first_id, []) if v.pct is not None}
        last_pct = {v.metric: v.pct for v in merged.get(last_id, []) if v.pct is not None}
        all_cats = set(first_map) | set(last_map)
        base_sum = sum(
            (merged[w.id][0].base if merged.get(w.id) else 0.0) for w in waves
        )
        delta_views = []
        for cat in sorted(all_cats):
            count_delta = last_map.get(cat, 0.0) - first_map.get(cat, 0.0)
            pct_delta: Optional[float] = None
            if cat in first_pct and cat in last_pct:
                pct_delta = last_pct[cat] - first_pct[cat]
            delta_views.append(
                View(metric=cat, base=base_sum, count=count_delta, pct=pct_delta)
            )
        delta_col = "Δ (last − first)"
        merged[delta_col] = delta_views

    return Chain(
        row_var=row_var,
        break_vars=use_breaks or ["wave"],
        views=merged,
        table_type=TableType.LONGITUDINAL,
        delta_column=delta_col,
    )

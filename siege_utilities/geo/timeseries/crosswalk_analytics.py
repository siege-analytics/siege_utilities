"""
Time-series analytics for geographic crosswalk data.

Analyzes how boundary relationships evolve across Census vintages:
- Allocation efficiency: how cleanly do source boundaries map to targets?
- Boundary stability: which geographies change the most between vintages?
- Reallocation chains: tracking a GEOID through multiple vintage transitions.

Builds on TemporalCrosswalk model data and the crosswalk module.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

import pandas as pd

log = logging.getLogger(__name__)


@dataclass
class BoundaryStabilityMetrics:
    """Stability metrics for a set of boundaries between two vintages.

    Attributes:
        source_year: Earlier Census vintage.
        target_year: Later Census vintage.
        geography_type: Geography level (tract, county, etc.).
        total_source: Number of source boundaries.
        total_target: Number of target boundaries.
        unchanged: Boundaries with weight >= threshold (effectively identical).
        split: Source boundaries that map to multiple targets.
        merged: Target boundaries that receive from multiple sources.
        net_change: target_count - source_count.
        pct_unchanged: Fraction of source boundaries unchanged.
        churn_rate: 1 - pct_unchanged.
    """

    source_year: int
    target_year: int
    geography_type: str
    total_source: int = 0
    total_target: int = 0
    unchanged: int = 0
    split: int = 0
    merged: int = 0
    net_change: int = 0
    pct_unchanged: float = 0.0
    churn_rate: float = 0.0


@dataclass
class AllocationEfficiencyMetrics:
    """Metrics describing how cleanly crosswalk weights allocate values.

    Attributes:
        mean_weight: Average crosswalk weight across all relationships.
        median_weight: Median weight.
        std_weight: Standard deviation of weights.
        pct_above_90: Fraction of relationships with weight > 0.9.
        pct_above_50: Fraction of relationships with weight > 0.5.
        pct_below_10: Fraction of relationships with weight < 0.1.
        n_relationships: Total number of crosswalk relationships.
    """

    mean_weight: float = 0.0
    median_weight: float = 0.0
    std_weight: float = 0.0
    pct_above_90: float = 0.0
    pct_above_50: float = 0.0
    pct_below_10: float = 0.0
    n_relationships: int = 0


@dataclass
class ChainLink:
    """A single step in a reallocation chain.

    Attributes:
        source_geoid: Source boundary GEOID.
        target_geoid: Target boundary GEOID.
        source_year: Source vintage year.
        target_year: Target vintage year.
        weight: Allocation weight for this link.
        relationship: IDENTICAL, SPLIT, MERGED, PARTIAL, RENAMED.
    """

    source_geoid: str
    target_geoid: str
    source_year: int
    target_year: int
    weight: float
    relationship: str


@dataclass
class ReallocationChain:
    """A complete chain tracking one GEOID through multiple vintages.

    Attributes:
        origin_geoid: Starting GEOID.
        origin_year: Starting vintage year.
        links: Ordered list of chain links.
        terminal_geoids: Final GEOIDs at the end of the chain.
        cumulative_weight: Product of weights along the chain (data quality).
    """

    origin_geoid: str
    origin_year: int
    links: list[ChainLink] = field(default_factory=list)
    terminal_geoids: list[str] = field(default_factory=list)
    cumulative_weight: float = 1.0


def compute_boundary_stability(
    crosswalk_df: pd.DataFrame,
    source_year: int,
    target_year: int,
    geography_type: str = "tract",
    unchanged_threshold: float = 0.999,
) -> BoundaryStabilityMetrics:
    """Compute stability metrics for boundaries between two vintages.

    Args:
        crosswalk_df: DataFrame with columns: source_geoid, target_geoid, weight.
        source_year: Earlier vintage year.
        target_year: Later vintage year.
        geography_type: Geography level name.
        unchanged_threshold: Weight threshold to consider a boundary unchanged.

    Returns:
        BoundaryStabilityMetrics with counts and rates.
    """
    if crosswalk_df.empty:
        return BoundaryStabilityMetrics(
            source_year=source_year,
            target_year=target_year,
            geography_type=geography_type,
        )

    # Normalize column names
    df = _normalize_crosswalk_columns(crosswalk_df)

    total_source = df["source_geoid"].nunique()
    total_target = df["target_geoid"].nunique()

    # Count source boundaries with a single target and weight >= threshold
    source_counts = df.groupby("source_geoid").agg(
        n_targets=("target_geoid", "nunique"),
        max_weight=("weight", "max"),
    )
    unchanged = int(
        ((source_counts["n_targets"] == 1) & (source_counts["max_weight"] >= unchanged_threshold)).sum()
    )
    split = int((source_counts["n_targets"] > 1).sum())

    # Count target boundaries receiving from multiple sources
    target_counts = df.groupby("target_geoid")["source_geoid"].nunique()
    merged = int((target_counts > 1).sum())

    pct_unchanged = unchanged / total_source if total_source > 0 else 0.0

    return BoundaryStabilityMetrics(
        source_year=source_year,
        target_year=target_year,
        geography_type=geography_type,
        total_source=total_source,
        total_target=total_target,
        unchanged=unchanged,
        split=split,
        merged=merged,
        net_change=total_target - total_source,
        pct_unchanged=pct_unchanged,
        churn_rate=1.0 - pct_unchanged,
    )


def compute_allocation_efficiency(
    crosswalk_df: pd.DataFrame,
) -> AllocationEfficiencyMetrics:
    """Compute metrics describing crosswalk weight distribution.

    High-quality crosswalks have most weights near 1.0 (clean mappings).
    Low-quality crosswalks have many small weights (fragmented boundaries).

    Args:
        crosswalk_df: DataFrame with a weight column.

    Returns:
        AllocationEfficiencyMetrics.
    """
    df = _normalize_crosswalk_columns(crosswalk_df)

    if df.empty or "weight" not in df.columns:
        return AllocationEfficiencyMetrics()

    weights = df["weight"].astype(float)
    n = len(weights)

    return AllocationEfficiencyMetrics(
        mean_weight=float(weights.mean()),
        median_weight=float(weights.median()),
        std_weight=float(weights.std()),
        pct_above_90=float((weights > 0.9).sum() / n) if n > 0 else 0.0,
        pct_above_50=float((weights > 0.5).sum() / n) if n > 0 else 0.0,
        pct_below_10=float((weights < 0.1).sum() / n) if n > 0 else 0.0,
        n_relationships=n,
    )


def build_reallocation_chain(
    crosswalk_dfs: list[tuple[int, int, pd.DataFrame]],
    origin_geoid: str,
    min_weight: float = 0.01,
) -> ReallocationChain:
    """Track a GEOID through multiple vintage transitions.

    Given a sequence of crosswalk DataFrames (one per transition), follows
    the origin GEOID forward through each step, accumulating weights.

    Args:
        crosswalk_dfs: List of (source_year, target_year, crosswalk_df) tuples,
            ordered chronologically.
        origin_geoid: Starting GEOID to track.
        min_weight: Minimum cumulative weight to continue tracking.

    Returns:
        ReallocationChain with links and terminal GEOIDs.
    """
    if not crosswalk_dfs:
        return ReallocationChain(
            origin_geoid=origin_geoid,
            origin_year=0,
            terminal_geoids=[origin_geoid],
        )

    chain = ReallocationChain(
        origin_geoid=origin_geoid,
        origin_year=crosswalk_dfs[0][0],
    )

    # Track current set of (geoid, cumulative_weight) pairs
    current_geoids = [(origin_geoid, 1.0)]

    for source_year, target_year, crosswalk_df in crosswalk_dfs:
        df = _normalize_crosswalk_columns(crosswalk_df)
        next_geoids = []

        for geoid, cum_weight in current_geoids:
            matches = df[df["source_geoid"] == geoid]

            if matches.empty:
                # No mapping found — GEOID may be unchanged
                next_geoids.append((geoid, cum_weight))
                continue

            for _, row in matches.iterrows():
                link_weight = float(row["weight"])
                new_cum = cum_weight * link_weight

                if new_cum < min_weight:
                    continue

                link = ChainLink(
                    source_geoid=geoid,
                    target_geoid=str(row["target_geoid"]),
                    source_year=source_year,
                    target_year=target_year,
                    weight=link_weight,
                    relationship=str(row.get("relationship", "PARTIAL")),
                )
                chain.links.append(link)
                next_geoids.append((str(row["target_geoid"]), new_cum))

        current_geoids = next_geoids

    chain.terminal_geoids = [g for g, _ in current_geoids]
    chain.cumulative_weight = sum(w for _, w in current_geoids)

    return chain


def compare_vintage_stability(
    crosswalk_dfs: list[tuple[int, int, pd.DataFrame]],
    geography_type: str = "tract",
) -> pd.DataFrame:
    """Compare boundary stability across multiple vintage transitions.

    Args:
        crosswalk_dfs: List of (source_year, target_year, crosswalk_df) tuples.
        geography_type: Geography level name.

    Returns:
        DataFrame with one row per transition and stability metrics.
    """
    records = []

    for source_year, target_year, crosswalk_df in crosswalk_dfs:
        stability = compute_boundary_stability(
            crosswalk_df, source_year, target_year, geography_type
        )
        efficiency = compute_allocation_efficiency(crosswalk_df)

        records.append({
            "source_year": source_year,
            "target_year": target_year,
            "geography_type": geography_type,
            "total_source": stability.total_source,
            "total_target": stability.total_target,
            "unchanged": stability.unchanged,
            "split": stability.split,
            "merged": stability.merged,
            "net_change": stability.net_change,
            "pct_unchanged": stability.pct_unchanged,
            "churn_rate": stability.churn_rate,
            "mean_weight": efficiency.mean_weight,
            "median_weight": efficiency.median_weight,
            "pct_clean": efficiency.pct_above_90,
        })

    return pd.DataFrame(records)


def identify_volatile_boundaries(
    crosswalk_df: pd.DataFrame,
    threshold: float = 0.5,
    top_n: Optional[int] = None,
) -> pd.DataFrame:
    """Identify source boundaries with the most fragmented mappings.

    "Volatile" boundaries are those that split into many targets with
    small weights, indicating significant boundary changes.

    Args:
        crosswalk_df: DataFrame with crosswalk relationships.
        threshold: Maximum weight to consider "fragmented" (default 0.5).
        top_n: Return only the top N most volatile (None for all).

    Returns:
        DataFrame with columns: source_geoid, n_targets, max_weight,
        min_weight, mean_weight, total_weight.
    """
    df = _normalize_crosswalk_columns(crosswalk_df)

    if df.empty:
        return pd.DataFrame(
            columns=["source_geoid", "n_targets", "max_weight",
                      "min_weight", "mean_weight", "total_weight"]
        )

    agg = df.groupby("source_geoid").agg(
        n_targets=("target_geoid", "nunique"),
        max_weight=("weight", "max"),
        min_weight=("weight", "min"),
        mean_weight=("weight", "mean"),
        total_weight=("weight", "sum"),
    ).reset_index()

    # Filter to boundaries where max_weight < threshold (truly fragmented)
    volatile = agg[agg["max_weight"] < threshold].sort_values(
        "n_targets", ascending=False
    )

    if top_n is not None:
        volatile = volatile.head(top_n)

    return volatile


def _normalize_crosswalk_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize crosswalk DataFrame column names to a standard schema."""
    col_map = {
        "GEOID_SOURCE": "source_geoid",
        "GEOID_TARGET": "target_geoid",
        "WEIGHT": "weight",
        "source_boundary_id": "source_geoid",
        "target_boundary_id": "target_geoid",
    }
    renamed = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})
    return renamed

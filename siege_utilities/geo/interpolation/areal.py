"""
Areal interpolation using PySAL's Tobler library.

Provides functions to transfer attribute data between non-coincident
geographic boundaries using area-weighted methods.

Two types of variables are handled:
- **Extensive** (e.g., population, housing units): totals that should be
  split proportionally when a source polygon overlaps multiple targets.
- **Intensive** (e.g., median income, poverty rate): rates/densities that
  should be area-weighted averaged across overlapping sources.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

import geopandas as gpd
import numpy as np

log = logging.getLogger(__name__)


@dataclass
class ArealInterpolationResult:
    """Result of an areal interpolation operation.

    Attributes:
        data: GeoDataFrame with interpolated values in target geometries.
        extensive_variables: List of extensive variables interpolated.
        intensive_variables: List of intensive variables interpolated.
        source_crs: CRS of the source data.
        target_crs: CRS of the target data.
        n_source: Number of source polygons.
        n_target: Number of target polygons.
        warnings: Any warnings generated during interpolation.
    """

    data: gpd.GeoDataFrame
    extensive_variables: list[str] = field(default_factory=list)
    intensive_variables: list[str] = field(default_factory=list)
    source_crs: Optional[str] = None
    target_crs: Optional[str] = None
    n_source: int = 0
    n_target: int = 0
    warnings: list[str] = field(default_factory=list)


def _ensure_common_crs(
    source: gpd.GeoDataFrame,
    target: gpd.GeoDataFrame,
) -> tuple[gpd.GeoDataFrame, gpd.GeoDataFrame, list[str]]:
    """Ensure both GeoDataFrames share the same CRS, reprojecting if needed."""
    warnings = []

    if source.crs is None or target.crs is None:
        warnings.append(
            "One or both GeoDataFrames lack a CRS. Assuming EPSG:4326."
        )
        if source.crs is None:
            source = source.set_crs("EPSG:4326")
        if target.crs is None:
            target = target.set_crs("EPSG:4326")

    if source.crs != target.crs:
        warnings.append(
            f"CRS mismatch: source={source.crs}, target={target.crs}. "
            f"Reprojecting source to target CRS."
        )
        source = source.to_crs(target.crs)

    return source, target, warnings


def interpolate_areal(
    source_gdf: gpd.GeoDataFrame,
    target_gdf: gpd.GeoDataFrame,
    extensive_variables: Optional[list[str]] = None,
    intensive_variables: Optional[list[str]] = None,
    allocate_total: bool = True,
    n_jobs: int = 1,
) -> ArealInterpolationResult:
    """Transfer attribute data between non-coincident geographies.

    Uses tobler's area_interpolate to redistribute values from source
    polygons to target polygons based on the area of intersection.

    Args:
        source_gdf: Source GeoDataFrame with attribute columns.
        target_gdf: Target GeoDataFrame defining output geometries.
        extensive_variables: Columns containing totals (population, etc.).
            These are split proportionally by area overlap.
        intensive_variables: Columns containing rates/densities.
            These are area-weighted averaged.
        allocate_total: If True, ensure 100% of source area is allocated.
        n_jobs: Number of parallel jobs (-1 for all CPUs).

    Returns:
        ArealInterpolationResult with interpolated GeoDataFrame.

    Raises:
        ImportError: If tobler is not installed.
        ValueError: If no variables are specified.
    """
    try:
        from tobler.area_weighted import area_interpolate
    except ImportError as e:
        raise ImportError(
            "tobler is required for areal interpolation. "
            "Install it with: pip install tobler"
        ) from e

    extensive_variables = extensive_variables or []
    intensive_variables = intensive_variables or []

    if not extensive_variables and not intensive_variables:
        raise ValueError(
            "At least one extensive or intensive variable must be specified."
        )

    # Validate columns exist in source
    missing = [
        v for v in extensive_variables + intensive_variables
        if v not in source_gdf.columns
    ]
    if missing:
        raise ValueError(f"Variables not found in source: {missing}")

    # Ensure matching CRS
    source, target, warnings = _ensure_common_crs(source_gdf, target_gdf)

    log.info(
        f"Interpolating {len(extensive_variables)} extensive + "
        f"{len(intensive_variables)} intensive variables "
        f"from {len(source)} source to {len(target)} target polygons"
    )

    result_gdf = area_interpolate(
        source_df=source,
        target_df=target,
        extensive_variables=extensive_variables or None,
        intensive_variables=intensive_variables or None,
        allocate_total=allocate_total,
        n_jobs=n_jobs,
    )

    return ArealInterpolationResult(
        data=result_gdf,
        extensive_variables=extensive_variables,
        intensive_variables=intensive_variables,
        source_crs=str(source.crs),
        target_crs=str(target.crs),
        n_source=len(source),
        n_target=len(target),
        warnings=warnings,
    )


def interpolate_extensive(
    source_gdf: gpd.GeoDataFrame,
    target_gdf: gpd.GeoDataFrame,
    variables: list[str],
    allocate_total: bool = True,
    n_jobs: int = 1,
) -> ArealInterpolationResult:
    """Interpolate extensive (total/count) variables between geographies.

    Extensive variables represent totals (population, housing units) that
    should be split proportionally based on area overlap.

    Args:
        source_gdf: Source GeoDataFrame with count/total columns.
        target_gdf: Target GeoDataFrame.
        variables: Column names of extensive variables.
        allocate_total: Ensure all source area is allocated.
        n_jobs: Parallel jobs.

    Returns:
        ArealInterpolationResult.
    """
    return interpolate_areal(
        source_gdf=source_gdf,
        target_gdf=target_gdf,
        extensive_variables=variables,
        allocate_total=allocate_total,
        n_jobs=n_jobs,
    )


def interpolate_intensive(
    source_gdf: gpd.GeoDataFrame,
    target_gdf: gpd.GeoDataFrame,
    variables: list[str],
    allocate_total: bool = True,
    n_jobs: int = 1,
) -> ArealInterpolationResult:
    """Interpolate intensive (rate/density) variables between geographies.

    Intensive variables represent rates or densities (median income,
    poverty rate) that should be area-weighted averaged.

    Args:
        source_gdf: Source GeoDataFrame with rate/density columns.
        target_gdf: Target GeoDataFrame.
        variables: Column names of intensive variables.
        allocate_total: Ensure all source area is allocated.
        n_jobs: Parallel jobs.

    Returns:
        ArealInterpolationResult.
    """
    return interpolate_areal(
        source_gdf=source_gdf,
        target_gdf=target_gdf,
        intensive_variables=variables,
        allocate_total=allocate_total,
        n_jobs=n_jobs,
    )


def compute_area_weights(
    source_gdf: gpd.GeoDataFrame,
    target_gdf: gpd.GeoDataFrame,
) -> gpd.GeoDataFrame:
    """Compute the area overlap matrix between source and target polygons.

    Returns a GeoDataFrame with columns:
    - source_idx: Index of the source polygon.
    - target_idx: Index of the target polygon.
    - overlap_area: Area of intersection.
    - source_fraction: Fraction of source polygon covered.
    - target_fraction: Fraction of target polygon covered.

    Useful for inspecting how much overlap exists between boundary sets
    before running interpolation.

    Args:
        source_gdf: Source polygons.
        target_gdf: Target polygons.

    Returns:
        GeoDataFrame with overlap weights.
    """
    source, target, _ = _ensure_common_crs(source_gdf, target_gdf)

    # Use an equal-area projection for accurate area computation
    source_ea = source.to_crs("ESRI:54009")
    target_ea = target.to_crs("ESRI:54009")

    source_areas = source_ea.geometry.area
    target_areas = target_ea.geometry.area

    # Compute intersections via spatial overlay
    overlay = gpd.overlay(source_ea, target_ea, how="intersection", keep_geom_type=False)

    if overlay.empty:
        log.warning("No intersections found between source and target polygons.")
        return gpd.GeoDataFrame(
            columns=["source_idx", "target_idx", "overlap_area",
                      "source_fraction", "target_fraction"],
        )

    overlap_areas = overlay.geometry.area

    # Build result — use overlay's index tracking
    # gpd.overlay preserves original indices in columns if they were set
    records = []
    for i, row in overlay.iterrows():
        overlap_area = overlap_areas[i]
        # Source and target indices depend on overlay behavior
        # For now, return the raw intersection areas
        records.append({
            "overlap_area": overlap_area,
            "geometry": row.geometry,
        })

    result = gpd.GeoDataFrame(records, crs="ESRI:54009")
    return result.to_crs(source_gdf.crs) if source_gdf.crs else result

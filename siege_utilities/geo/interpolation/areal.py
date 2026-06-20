"""
Areal interpolation using PySAL's Tobler library.

Provides functions to transfer attribute data between non-coincident
geographic boundaries using area-weighted methods.

Two types of variables are handled:
- **Extensive** (e.g., population, housing units): totals that should be
  split proportionally when a source polygon overlaps multiple targets.
- **Intensive** (e.g., median income, poverty rate): rates/densities that
  should be area-weighted averaged across overlapping sources.

Backend dispatch (in priority order):
1. **tobler** — PySAL's area_interpolate (requires geopandas + tobler)
2. **duckdb** — DuckDB spatial extension (ST_Intersection / ST_Area)
3. **shapely** — Pure Shapely STRtree + intersection (always available)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

import numpy as np

try:
    import geopandas as gpd
    _GEOPANDAS_AVAILABLE = True
except ImportError:
    gpd = None
    _GEOPANDAS_AVAILABLE = False

try:
    from shapely import STRtree
    _SHAPELY_AVAILABLE = True
except ImportError:
    _SHAPELY_AVAILABLE = False

try:
    import duckdb as _duckdb
    _DUCKDB_AVAILABLE = True
except ImportError:
    _DUCKDB_AVAILABLE = False

try:
    from tobler.area_weighted import area_interpolate as _tobler_area_interpolate
    _TOBLER_AVAILABLE = True
except ImportError:
    _TOBLER_AVAILABLE = False

from siege_utilities.geo.crs import reproject_if_needed

__all__ = [
    'ArealInterpolationResult',
    'interpolate_areal',
    'interpolate_extensive',
    'interpolate_intensive',
    'compute_area_weights',
]

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
        backend: Which backend performed the interpolation.
    """

    data: gpd.GeoDataFrame
    extensive_variables: list[str] = field(default_factory=list)
    intensive_variables: list[str] = field(default_factory=list)
    source_crs: Optional[str] = None
    target_crs: Optional[str] = None
    n_source: int = 0
    n_target: int = 0
    warnings: list[str] = field(default_factory=list)
    backend: str = ""


def _ensure_common_crs(
    source: gpd.GeoDataFrame,
    target: gpd.GeoDataFrame,
) -> tuple[gpd.GeoDataFrame, gpd.GeoDataFrame, list[str]]:
    """Ensure both GeoDataFrames share the same CRS, reprojecting if needed."""
    warnings = []

    if source.crs is None:
        raise ValueError(
            "source GeoDataFrame has no CRS. Set one with .set_crs() before interpolation."
        )
    if target.crs is None:
        raise ValueError(
            "target GeoDataFrame has no CRS. Set one with .set_crs() before interpolation."
        )

    if source.crs != target.crs:
        warnings.append(
            f"CRS mismatch: source={source.crs}, target={target.crs}. "
            f"Reprojecting source to target CRS."
        )
        source = source.to_crs(target.crs)

    return source, target, warnings


# ---------------------------------------------------------------------------
# Backend: tobler (geopandas + PySAL)
# ---------------------------------------------------------------------------

def _interpolate_tobler(
    source: gpd.GeoDataFrame,
    target: gpd.GeoDataFrame,
    extensive_variables: list[str],
    intensive_variables: list[str],
    allocate_total: bool,
    n_jobs: int,
) -> gpd.GeoDataFrame:
    result_gdf = _tobler_area_interpolate(
        source_df=source,
        target_df=target,
        extensive_variables=extensive_variables or None,
        intensive_variables=intensive_variables or None,
        allocate_total=allocate_total,
        n_jobs=n_jobs,
    )
    return result_gdf


# ---------------------------------------------------------------------------
# Backend: DuckDB spatial
# ---------------------------------------------------------------------------

def _interpolate_duckdb(
    source: gpd.GeoDataFrame,
    target: gpd.GeoDataFrame,
    extensive_variables: list[str],
    intensive_variables: list[str],
) -> gpd.GeoDataFrame:
    """Area-weighted interpolation via DuckDB spatial SQL."""
    import pandas as pd

    con = _duckdb.connect()
    con.execute("INSTALL spatial; LOAD spatial;")

    src_df = pd.DataFrame(source.drop(columns="geometry"))
    src_df["_geom_wkb"] = source.geometry.apply(lambda g: g.wkb_hex)
    src_df["_src_idx"] = range(len(src_df))

    tgt_df = pd.DataFrame(target.drop(columns="geometry"))
    tgt_df["_geom_wkb"] = target.geometry.apply(lambda g: g.wkb_hex)
    tgt_df["_tgt_idx"] = range(len(tgt_df))

    con.register("source_tbl", src_df)
    con.register("target_tbl", tgt_df)

    overlap_sql = """
        SELECT
            s._src_idx,
            t._tgt_idx,
            ST_Area(ST_Intersection(
                ST_GeomFromWKB(UNHEX(s._geom_wkb)),
                ST_GeomFromWKB(UNHEX(t._geom_wkb))
            )) AS overlap_area,
            ST_Area(ST_GeomFromWKB(UNHEX(s._geom_wkb))) AS src_area,
            ST_Area(ST_GeomFromWKB(UNHEX(t._geom_wkb))) AS tgt_area
        FROM source_tbl s, target_tbl t
        WHERE ST_Intersects(
            ST_GeomFromWKB(UNHEX(s._geom_wkb)),
            ST_GeomFromWKB(UNHEX(t._geom_wkb))
        )
        AND ST_Area(ST_Intersection(
            ST_GeomFromWKB(UNHEX(s._geom_wkb)),
            ST_GeomFromWKB(UNHEX(t._geom_wkb))
        )) > 0
    """
    overlaps = con.execute(overlap_sql).fetchdf()
    con.close()

    if overlaps.empty:
        log.warning("No intersections found between source and target (DuckDB).")
        result_df = target.copy()
        for v in extensive_variables + intensive_variables:
            result_df[v] = 0.0
        return result_df

    overlaps["src_fraction"] = overlaps["overlap_area"] / overlaps["src_area"]
    overlaps["tgt_fraction"] = overlaps["overlap_area"] / overlaps["tgt_area"]

    result_df = target.copy()

    for var in extensive_variables:
        src_vals = source[var].values
        weighted = overlaps.copy()
        weighted["contribution"] = src_vals[weighted["_src_idx"].values] * weighted["src_fraction"]
        result_df[var] = weighted.groupby("_tgt_idx")["contribution"].sum().reindex(
            range(len(target)), fill_value=0.0
        ).values

    for var in intensive_variables:
        src_vals = source[var].values
        weighted = overlaps.copy()
        weighted["weighted_val"] = src_vals[weighted["_src_idx"].values] * weighted["overlap_area"]
        tgt_total_overlap = weighted.groupby("_tgt_idx")["overlap_area"].sum()
        tgt_weighted_sum = weighted.groupby("_tgt_idx")["weighted_val"].sum()
        with np.errstate(divide="ignore", invalid="ignore"):
            avg = (tgt_weighted_sum / tgt_total_overlap).fillna(0.0)
        result_df[var] = avg.reindex(range(len(target)), fill_value=0.0).values

    return result_df


# ---------------------------------------------------------------------------
# Backend: pure Shapely (STRtree)
# ---------------------------------------------------------------------------

def _interpolate_shapely(
    source: gpd.GeoDataFrame,
    target: gpd.GeoDataFrame,
    extensive_variables: list[str],
    intensive_variables: list[str],
) -> gpd.GeoDataFrame:
    """Area-weighted interpolation via Shapely STRtree (no GDAL, no DuckDB)."""
    src_geoms = source.geometry.values
    tgt_geoms = target.geometry.values

    tree = STRtree(src_geoms)

    src_areas = np.array([g.area for g in src_geoms])
    n_tgt = len(tgt_geoms)

    ext_results = {v: np.zeros(n_tgt) for v in extensive_variables}
    int_weighted_sums = {v: np.zeros(n_tgt) for v in intensive_variables}
    int_total_overlaps = np.zeros(n_tgt)

    for tgt_i, tgt_geom in enumerate(tgt_geoms):
        candidates = tree.query(tgt_geom)
        for src_i in candidates:
            src_geom = src_geoms[src_i]
            if not tgt_geom.intersects(src_geom):
                continue
            intersection = tgt_geom.intersection(src_geom)
            ov_area = intersection.area
            if ov_area <= 0:
                continue

            src_frac = ov_area / src_areas[src_i] if src_areas[src_i] > 0 else 0.0

            for var in extensive_variables:
                ext_results[var][tgt_i] += source[var].iat[src_i] * src_frac

            for var in intensive_variables:
                int_weighted_sums[var][tgt_i] += source[var].iat[src_i] * ov_area
            int_total_overlaps[tgt_i] += ov_area

    result_df = target.copy()
    for var in extensive_variables:
        result_df[var] = ext_results[var]
    for var in intensive_variables:
        with np.errstate(divide="ignore", invalid="ignore"):
            result_df[var] = np.where(
                int_total_overlaps > 0,
                int_weighted_sums[var] / int_total_overlaps,
                0.0,
            )

    return result_df


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def _select_backend(
    extensive_variables: list[str],
    intensive_variables: list[str],
) -> str:
    """Select the best available backend."""
    if _TOBLER_AVAILABLE and _GEOPANDAS_AVAILABLE:
        return "tobler"
    if _DUCKDB_AVAILABLE and _GEOPANDAS_AVAILABLE:
        return "duckdb"
    if _SHAPELY_AVAILABLE and _GEOPANDAS_AVAILABLE:
        return "shapely"
    raise ImportError(
        "Areal interpolation requires at least shapely + geopandas. "
        "Install with: pip install geopandas shapely"
    )


def interpolate_areal(
    source_gdf: gpd.GeoDataFrame,
    target_gdf: gpd.GeoDataFrame,
    extensive_variables: Optional[list[str]] = None,
    intensive_variables: Optional[list[str]] = None,
    allocate_total: bool = True,
    n_jobs: int = 1,
    *,
    crs: str | None = None,
) -> ArealInterpolationResult:
    """Transfer attribute data between non-coincident geographies.

    Uses area-weighted interpolation to redistribute values from source
    polygons to target polygons based on the area of intersection.

    Backend dispatch (in priority order):
    1. tobler (PySAL) — when tobler + geopandas are installed
    2. DuckDB spatial — when duckdb is installed (no GDAL needed)
    3. pure Shapely — STRtree + intersection (always available with geopandas)

    Args:
        source_gdf: Source GeoDataFrame with attribute columns.
        target_gdf: Target GeoDataFrame defining output geometries.
        extensive_variables: Columns containing totals (population, etc.).
            These are split proportionally by area overlap.
        intensive_variables: Columns containing rates/densities.
            These are area-weighted averaged.
        allocate_total: If True, ensure 100% of source area is allocated
            (only applies to tobler backend).
        n_jobs: Number of parallel jobs (only applies to tobler backend).
        crs: Output CRS for the result GeoDataFrame (default: source CRS).

    Returns:
        ArealInterpolationResult with interpolated GeoDataFrame in *crs*.

    Raises:
        ImportError: If no suitable backend is available.
        ValueError: If no variables are specified or columns missing.
    """
    extensive_variables = extensive_variables or []
    intensive_variables = intensive_variables or []

    if not extensive_variables and not intensive_variables:
        raise ValueError(
            "At least one extensive or intensive variable must be specified."
        )

    missing = [
        v for v in extensive_variables + intensive_variables
        if v not in source_gdf.columns
    ]
    if missing:
        raise ValueError(f"Variables not found in source: {missing}")

    source, target, warnings = _ensure_common_crs(source_gdf, target_gdf)

    backend = _select_backend(extensive_variables, intensive_variables)
    log.info(
        "Interpolating %d extensive + %d intensive variables "
        "from %d source to %d target polygons (backend=%s)",
        len(extensive_variables), len(intensive_variables),
        len(source), len(target), backend,
    )

    if backend == "tobler":
        result_gdf = _interpolate_tobler(
            source, target, extensive_variables, intensive_variables,
            allocate_total, n_jobs,
        )
    elif backend == "duckdb":
        result_gdf = _interpolate_duckdb(
            source, target, extensive_variables, intensive_variables,
        )
    else:
        result_gdf = _interpolate_shapely(
            source, target, extensive_variables, intensive_variables,
        )

    result_gdf = reproject_if_needed(result_gdf, crs)

    return ArealInterpolationResult(
        data=result_gdf,
        extensive_variables=extensive_variables,
        intensive_variables=intensive_variables,
        source_crs=str(source.crs),
        target_crs=str(target.crs),
        n_source=len(source),
        n_target=len(target),
        warnings=warnings,
        backend=backend,
    )


def interpolate_extensive(
    source_gdf: gpd.GeoDataFrame,
    target_gdf: gpd.GeoDataFrame,
    variables: list[str],
    allocate_total: bool = True,
    n_jobs: int = 1,
    *,
    crs: str | None = None,
) -> ArealInterpolationResult:
    """Interpolate extensive (total/count) variables between geographies."""
    return interpolate_areal(
        source_gdf=source_gdf,
        target_gdf=target_gdf,
        extensive_variables=variables,
        allocate_total=allocate_total,
        n_jobs=n_jobs,
        crs=crs,
    )


def interpolate_intensive(
    source_gdf: gpd.GeoDataFrame,
    target_gdf: gpd.GeoDataFrame,
    variables: list[str],
    allocate_total: bool = True,
    n_jobs: int = 1,
    *,
    crs: str | None = None,
) -> ArealInterpolationResult:
    """Interpolate intensive (rate/density) variables between geographies."""
    return interpolate_areal(
        source_gdf=source_gdf,
        target_gdf=target_gdf,
        intensive_variables=variables,
        allocate_total=allocate_total,
        n_jobs=n_jobs,
        crs=crs,
    )


def compute_area_weights(
    source_gdf: gpd.GeoDataFrame,
    target_gdf: gpd.GeoDataFrame,
    *,
    crs: str | None = None,
) -> gpd.GeoDataFrame:
    """Compute the area overlap matrix between source and target polygons.

    Returns a GeoDataFrame with columns:
    - source_idx: Index of the source polygon.
    - target_idx: Index of the target polygon.
    - overlap_area: Area of intersection.
    - source_fraction: Fraction of source polygon covered.
    - target_fraction: Fraction of target polygon covered.

    Args:
        source_gdf: Source polygons.
        target_gdf: Target polygons.
        crs: Output CRS (default: source CRS).

    Returns:
        GeoDataFrame with overlap weights in *crs*.
    """
    source, target, _ = _ensure_common_crs(source_gdf, target_gdf)

    source_ea = source.to_crs("ESRI:54009")
    target_ea = target.to_crs("ESRI:54009")

    source_areas = source_ea.geometry.area
    target_areas = target_ea.geometry.area

    source_ea = source_ea.copy()
    target_ea = target_ea.copy()
    source_ea["_src_idx"] = range(len(source_ea))
    target_ea["_tgt_idx"] = range(len(target_ea))

    overlay = gpd.overlay(source_ea, target_ea, how="intersection", keep_geom_type=False)

    if overlay.empty:
        log.warning("No intersections found between source and target polygons.")
        return gpd.GeoDataFrame(
            columns=["source_idx", "target_idx", "overlap_area",
                      "source_fraction", "target_fraction"],
        )

    overlap_areas = overlay.geometry.area

    records = []
    for i, row in overlay.iterrows():
        src_i = int(row["_src_idx"])
        tgt_i = int(row["_tgt_idx"])
        ov_area = overlap_areas[i]
        records.append({
            "source_idx": src_i,
            "target_idx": tgt_i,
            "overlap_area": ov_area,
            "source_fraction": ov_area / source_areas.iloc[src_i] if source_areas.iloc[src_i] > 0 else 0.0,
            "target_fraction": ov_area / target_areas.iloc[tgt_i] if target_areas.iloc[tgt_i] > 0 else 0.0,
            "geometry": row.geometry,
        })

    result = gpd.GeoDataFrame(records, crs="ESRI:54009")
    return reproject_if_needed(result, crs)

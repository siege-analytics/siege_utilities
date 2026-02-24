"""Databricks-oriented fallback planning for spatial ingestion workflows."""

from dataclasses import dataclass
from typing import Iterable, List

from siege_utilities.config.census_constants import resolve_geographic_level


@dataclass(frozen=True)
class SpatialLoaderPlan:
    """Chosen loader with deterministic fallback ordering."""

    primary_loader: str
    loader_order: List[str]
    reason: str


def select_spatial_loader(
    ogr2ogr_available: bool,
    sedona_available: bool,
) -> SpatialLoaderPlan:
    """
    Select a spatial loader strategy for Databricks-style environments.

    Loader order:
    1. ogr2ogr
    2. sedona
    3. python
    """
    if ogr2ogr_available:
        return SpatialLoaderPlan(
            primary_loader="ogr2ogr",
            loader_order=["ogr2ogr", "sedona", "python"],
            reason="ogr2ogr available",
        )
    if sedona_available:
        return SpatialLoaderPlan(
            primary_loader="sedona",
            loader_order=["sedona", "python"],
            reason="ogr2ogr unavailable, sedona available",
        )
    return SpatialLoaderPlan(
        primary_loader="python",
        loader_order=["python"],
        reason="ogr2ogr and sedona unavailable",
    )


def build_census_table_name(
    year: int,
    geography_level: str,
    prefix: str = "census",
) -> str:
    """Build a normalized census table name like `census_2024_block_group`."""
    canonical = resolve_geographic_level(geography_level)
    safe_level = canonical.replace("-", "_")
    return f"{prefix}_{int(year)}_{safe_level}"


def build_census_ingest_targets(
    year: int,
    geography_levels: Iterable[str],
    prefix: str = "census",
) -> List[str]:
    """Build de-duplicated target table names for ingest planning."""
    seen = set()
    targets: List[str] = []
    for level in geography_levels:
        name = build_census_table_name(year=year, geography_level=level, prefix=prefix)
        if name in seen:
            continue
        seen.add(name)
        targets.append(name)
    return targets

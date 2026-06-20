"""Block assignment for codification.

Groups geocoded addresses by Census block GEOID and computes
geographic spread metrics (block count, spatial extent, concentration).
"""

from __future__ import annotations

import logging
from collections import Counter
from dataclasses import dataclass
from typing import Optional

__all__ = [
    'BlockAssignment',
    'BlockGroup',
    'SpreadMetrics',
    'assign_blocks',
    'group_by_block',
    'compute_spread',
]

log = logging.getLogger(__name__)


@dataclass
class BlockAssignment:
    """Geocoded address assigned to a Census block.

    Attributes:
        block_geoid: 15-digit block GEOID.
        tract_geoid: 11-digit tract GEOID.
        county_geoid: 5-digit county GEOID.
        state_geoid: 2-digit state GEOID.
        lat: Latitude.
        lon: Longitude.
        input_id: Caller's address identifier.
    """

    block_geoid: str = ""
    tract_geoid: str = ""
    county_geoid: str = ""
    state_geoid: str = ""
    lat: Optional[float] = None
    lon: Optional[float] = None
    input_id: str = ""


@dataclass
class BlockGroup:
    """Addresses grouped by Census block.

    Attributes:
        block_geoid: Block identifier.
        tract_geoid: Parent tract.
        county_geoid: Parent county.
        state_geoid: Parent state.
        address_count: Number of addresses in this block.
        centroid_lat: Mean latitude of addresses.
        centroid_lon: Mean longitude of addresses.
    """

    block_geoid: str = ""
    tract_geoid: str = ""
    county_geoid: str = ""
    state_geoid: str = ""
    address_count: int = 0
    centroid_lat: Optional[float] = None
    centroid_lon: Optional[float] = None


@dataclass
class SpreadMetrics:
    """Geographic spread metrics for a set of block assignments.

    Attributes:
        block_count: Distinct blocks with addresses.
        tract_count: Distinct tracts.
        county_count: Distinct counties.
        state_count: Distinct states.
        concentration: Herfindahl index of block address distribution
            (0=evenly spread, 1=all in one block).
        max_block_pct: Fraction of addresses in the most populated block.
        bbox_lat_range: Latitude range (max - min) of all addresses.
        bbox_lon_range: Longitude range (max - min) of all addresses.
    """

    block_count: int = 0
    tract_count: int = 0
    county_count: int = 0
    state_count: int = 0
    concentration: float = 0.0
    max_block_pct: float = 0.0
    bbox_lat_range: float = 0.0
    bbox_lon_range: float = 0.0


def assign_blocks(geocoded_results) -> list[BlockAssignment]:
    """Convert geocoding results to block assignments.

    Args:
        geocoded_results: List of GeocodingResult from a BatchGeocoder.

    Returns:
        List of BlockAssignment for matched results with coordinates.
    """
    assignments = []
    for gr in geocoded_results:
        if not gr.matched or gr.lat is None or gr.lon is None:
            continue
        assignments.append(BlockAssignment(
            block_geoid=gr.block_geoid,
            tract_geoid=gr.tract_geoid,
            county_geoid=gr.county_geoid,
            state_geoid=gr.state_geoid,
            lat=gr.lat,
            lon=gr.lon,
            input_id=gr.input_id,
        ))
    return assignments


def group_by_block(assignments: list[BlockAssignment]) -> list[BlockGroup]:
    """Group block assignments by block GEOID.

    Returns groups sorted by address count (descending).
    """
    counts: Counter = Counter()
    meta: dict[str, dict] = {}
    lats: dict[str, list[float]] = {}
    lons: dict[str, list[float]] = {}

    for a in assignments:
        geoid = a.block_geoid or a.tract_geoid or a.county_geoid or "unknown"
        counts[geoid] += 1

        if geoid not in meta:
            meta[geoid] = {
                "block_geoid": a.block_geoid,
                "tract_geoid": a.tract_geoid,
                "county_geoid": a.county_geoid,
                "state_geoid": a.state_geoid,
            }
            lats[geoid] = []
            lons[geoid] = []

        if a.lat is not None:
            lats[geoid].append(a.lat)
        if a.lon is not None:
            lons[geoid].append(a.lon)

    groups = []
    for geoid, count in counts.most_common():
        m = meta[geoid]
        clat = sum(lats[geoid]) / len(lats[geoid]) if lats[geoid] else None
        clon = sum(lons[geoid]) / len(lons[geoid]) if lons[geoid] else None
        groups.append(BlockGroup(
            block_geoid=m["block_geoid"],
            tract_geoid=m["tract_geoid"],
            county_geoid=m["county_geoid"],
            state_geoid=m["state_geoid"],
            address_count=count,
            centroid_lat=clat,
            centroid_lon=clon,
        ))

    return groups


def compute_spread(
    assignments: list[BlockAssignment],
    groups: Optional[list[BlockGroup]] = None,
) -> SpreadMetrics:
    """Compute geographic spread metrics for block assignments.

    Args:
        assignments: All block assignments.
        groups: Pre-computed block groups (optional, computed if not provided).
    """
    if not assignments:
        return SpreadMetrics()

    if groups is None:
        groups = group_by_block(assignments)

    total = sum(g.address_count for g in groups)
    blocks = set(g.block_geoid for g in groups if g.block_geoid)
    tracts = set(g.tract_geoid for g in groups if g.tract_geoid)
    counties = set(g.county_geoid for g in groups if g.county_geoid)
    states = set(g.state_geoid for g in groups if g.state_geoid)

    hhi = 0.0
    max_pct = 0.0
    if total > 0:
        for g in groups:
            pct = g.address_count / total
            hhi += pct * pct
            max_pct = max(max_pct, pct)

    all_lats = [a.lat for a in assignments if a.lat is not None]
    all_lons = [a.lon for a in assignments if a.lon is not None]

    lat_range = (max(all_lats) - min(all_lats)) if all_lats else 0.0
    lon_range = (max(all_lons) - min(all_lons)) if all_lons else 0.0

    return SpreadMetrics(
        block_count=len(blocks),
        tract_count=len(tracts),
        county_count=len(counties),
        state_count=len(states),
        concentration=hhi,
        max_block_pct=max_pct,
        bbox_lat_range=lat_range,
        bbox_lon_range=lon_range,
    )

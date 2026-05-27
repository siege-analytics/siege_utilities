"""Address-based area codification.

Given a set of addresses, geocodes them, assigns to Census blocks,
and builds a structured area portrait with demographics, urbanicity,
and recency analysis.

Usage::

    from siege_utilities.geo.codification import codify_area
    result = codify_area(["123 Main St, Austin, TX", ...])
    print(result.block_count)
    print(result.summarize())
"""

from __future__ import annotations

import logging
from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Optional, Union

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------


@dataclass
class BlockProfile:
    """Profile of a single Census block within the codified area.

    Attributes:
        block_geoid: 15-digit Census block GEOID.
        tract_geoid: 11-digit Census tract GEOID.
        county_geoid: 5-digit county GEOID.
        state_geoid: 2-digit state GEOID.
        address_count: Number of geocoded addresses in this block.
        demographics: Block-level demographic data (populated by T3).
        urbanicity: NCES locale classification (populated by T4).
        recency: Address vintage data (populated by T5).
    """

    block_geoid: str = ""
    tract_geoid: str = ""
    county_geoid: str = ""
    state_geoid: str = ""
    address_count: int = 0
    demographics: dict[str, Any] = field(default_factory=dict)
    urbanicity: dict[str, Any] = field(default_factory=dict)
    recency: dict[str, Any] = field(default_factory=dict)


@dataclass
class CodificationResult:
    """Structured area portrait from address codification.

    Attributes:
        total_addresses: Total addresses submitted.
        matched_addresses: Successfully geocoded addresses.
        match_rate: Fraction geocoded.
        blocks: Per-block profiles.
        geocoding_backend: Which geocoder was used.
        census_year: Census vintage for geography.
        errors: Any errors encountered.
    """

    total_addresses: int = 0
    matched_addresses: int = 0
    match_rate: float = 0.0
    blocks: list[BlockProfile] = field(default_factory=list)
    geocoding_backend: str = ""
    census_year: Optional[int] = None
    errors: list[str] = field(default_factory=list)

    @property
    def block_count(self) -> int:
        return len(self.blocks)

    @property
    def tract_count(self) -> int:
        return len(set(b.tract_geoid for b in self.blocks if b.tract_geoid))

    @property
    def county_count(self) -> int:
        return len(set(b.county_geoid for b in self.blocks if b.county_geoid))

    @property
    def state_count(self) -> int:
        return len(set(b.state_geoid for b in self.blocks if b.state_geoid))

    def top_blocks(self, n: int = 10) -> list[BlockProfile]:
        return sorted(self.blocks, key=lambda b: b.address_count, reverse=True)[:n]

    def summarize(self) -> dict[str, Any]:
        return {
            "total_addresses": self.total_addresses,
            "matched_addresses": self.matched_addresses,
            "match_rate": self.match_rate,
            "block_count": self.block_count,
            "tract_count": self.tract_count,
            "county_count": self.county_count,
            "state_count": self.state_count,
            "geocoding_backend": self.geocoding_backend,
            "census_year": self.census_year,
        }


# ---------------------------------------------------------------------------
# Core codification function
# ---------------------------------------------------------------------------


def codify_area(
    addresses: Union[list[str], list[dict]],
    geocoder=None,
    census_year: Optional[int] = None,
    **kwargs,
) -> CodificationResult:
    """Codify an area from a set of addresses.

    Geocodes the addresses, assigns them to Census blocks, and
    builds a structured area portrait.

    Args:
        addresses: Addresses to codify (strings or dicts).
        geocoder: BatchGeocoder instance. If None, uses CensusBatchGeocoder.
        census_year: Census vintage for geography.
        **kwargs: Passed through to the geocoder.

    Returns:
        CodificationResult with block-level profiles.
    """
    result = CodificationResult(
        total_addresses=len(addresses),
        census_year=census_year,
    )

    if not addresses:
        return result

    if geocoder is None:
        geocoder = _get_default_geocoder()

    if geocoder is None:
        result.errors.append("No geocoder available")
        return result

    result.geocoding_backend = geocoder.backend_name

    try:
        geocode_result = geocoder.geocode(addresses, **kwargs)
    except Exception as exc:
        result.errors.append(f"Geocoding failed: {exc}")
        log.error("Codification geocoding failed: %s", exc)
        return result

    matched = [r for r in geocode_result.results if r.matched]
    result.matched_addresses = len(matched)
    result.match_rate = (
        len(matched) / len(addresses) if addresses else 0.0
    )

    result.blocks = _build_block_profiles(matched)

    return result


def _build_block_profiles(geocoded_results) -> list[BlockProfile]:
    """Group geocoded results into block-level profiles."""
    block_counts: Counter = Counter()
    block_meta: dict[str, dict] = {}

    for gr in geocoded_results:
        geoid = gr.block_geoid
        if not geoid:
            geoid = gr.tract_geoid or gr.county_geoid or "unknown"

        block_counts[geoid] += 1

        if geoid not in block_meta:
            block_meta[geoid] = {
                "block_geoid": gr.block_geoid,
                "tract_geoid": gr.tract_geoid,
                "county_geoid": gr.county_geoid,
                "state_geoid": gr.state_geoid,
            }

    profiles = []
    for geoid, count in block_counts.most_common():
        meta = block_meta[geoid]
        profiles.append(BlockProfile(
            block_geoid=meta["block_geoid"],
            tract_geoid=meta["tract_geoid"],
            county_geoid=meta["county_geoid"],
            state_geoid=meta["state_geoid"],
            address_count=count,
        ))

    return profiles


def _get_default_geocoder():
    """Attempt to create a default CensusBatchGeocoder."""
    try:
        from siege_utilities.geo.providers.census_batch import CensusBatchGeocoder
        return CensusBatchGeocoder()
    except Exception:
        return None

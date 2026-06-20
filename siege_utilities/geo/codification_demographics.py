"""Demographic enrichment for codification.

Fetches block-level demographics for matched blocks and produces
an address-weighted demographic signature: race/ethnicity distribution,
housing occupancy, voting-age composition.
"""

from __future__ import annotations

import abc
import logging
from dataclasses import dataclass
from typing import Optional

__all__ = [
    'BlockDemographics',
    'DemographicSignature',
    'BlockDemographicsProvider',
    'DictBlockDemographicsProvider',
    'compute_demographic_signature',
]

log = logging.getLogger(__name__)


@dataclass
class BlockDemographics:
    """PL 94-171 demographics for a single Census block.

    Attributes:
        block_geoid: Block GEOID.
        total_population: Total population.
        voting_age_population: 18+ population.
        white: White alone.
        black: Black alone.
        hispanic: Hispanic or Latino.
        asian: Asian alone.
        other_race: All other races.
        housing_total: Total housing units.
        housing_occupied: Occupied housing units.
        housing_vacant: Vacant housing units.
    """

    block_geoid: str = ""
    total_population: int = 0
    voting_age_population: int = 0
    white: int = 0
    black: int = 0
    hispanic: int = 0
    asian: int = 0
    other_race: int = 0
    housing_total: int = 0
    housing_occupied: int = 0
    housing_vacant: int = 0


@dataclass
class DemographicSignature:
    """Address-weighted demographic signature for a codified area.

    All percentages are weighted by address count per block.

    Attributes:
        total_block_population: Sum of block populations (unweighted).
        weighted_blocks: Number of blocks with both addresses and demographics.
        pct_white: Address-weighted white percentage.
        pct_black: Address-weighted black percentage.
        pct_hispanic: Address-weighted Hispanic percentage.
        pct_asian: Address-weighted Asian percentage.
        pct_other: Address-weighted other race percentage.
        pct_voting_age: Address-weighted voting-age percentage.
        pct_housing_occupied: Address-weighted housing occupancy rate.
        pct_housing_vacant: Address-weighted vacancy rate.
    """

    total_block_population: int = 0
    weighted_blocks: int = 0
    pct_white: float = 0.0
    pct_black: float = 0.0
    pct_hispanic: float = 0.0
    pct_asian: float = 0.0
    pct_other: float = 0.0
    pct_voting_age: float = 0.0
    pct_housing_occupied: float = 0.0
    pct_housing_vacant: float = 0.0


class BlockDemographicsProvider(abc.ABC):
    """Protocol for fetching block-level demographics."""

    @abc.abstractmethod
    def get_demographics(
        self,
        block_geoids: list[str],
        census_year: Optional[int] = None,
    ) -> dict[str, BlockDemographics]:
        """Fetch demographics for given block GEOIDs.

        Returns dict of block_geoid → BlockDemographics.
        """


class DictBlockDemographicsProvider(BlockDemographicsProvider):
    """In-memory demographics provider for testing."""

    def __init__(self):
        self._data: dict[str, BlockDemographics] = {}

    def add(self, demo: BlockDemographics):
        self._data[demo.block_geoid] = demo

    def get_demographics(
        self,
        block_geoids: list[str],
        census_year: Optional[int] = None,
    ) -> dict[str, BlockDemographics]:
        return {g: self._data[g] for g in block_geoids if g in self._data}


def compute_demographic_signature(
    block_address_counts: dict[str, int],
    demographics: dict[str, BlockDemographics],
) -> DemographicSignature:
    """Compute address-weighted demographic signature.

    Args:
        block_address_counts: Dict of block_geoid → address count.
        demographics: Dict of block_geoid → BlockDemographics.

    Returns:
        DemographicSignature with address-weighted percentages.
    """
    total_addresses = 0
    weighted_pct_white = 0.0
    weighted_pct_black = 0.0
    weighted_pct_hispanic = 0.0
    weighted_pct_asian = 0.0
    weighted_pct_other = 0.0
    weighted_pct_vap = 0.0
    weighted_pct_occupied = 0.0
    weighted_pct_vacant = 0.0
    total_pop = 0
    matched_blocks = 0

    for geoid, addr_count in block_address_counts.items():
        demo = demographics.get(geoid)
        if demo is None or demo.total_population == 0:
            continue

        matched_blocks += 1
        total_addresses += addr_count
        total_pop += demo.total_population

        pop = demo.total_population
        weighted_pct_white += addr_count * (demo.white / pop)
        weighted_pct_black += addr_count * (demo.black / pop)
        weighted_pct_hispanic += addr_count * (demo.hispanic / pop)
        weighted_pct_asian += addr_count * (demo.asian / pop)
        weighted_pct_other += addr_count * (demo.other_race / pop)

        if pop > 0:
            weighted_pct_vap += addr_count * (demo.voting_age_population / pop)

        if demo.housing_total > 0:
            weighted_pct_occupied += addr_count * (demo.housing_occupied / demo.housing_total)
            weighted_pct_vacant += addr_count * (demo.housing_vacant / demo.housing_total)

    if total_addresses == 0:
        return DemographicSignature()

    return DemographicSignature(
        total_block_population=total_pop,
        weighted_blocks=matched_blocks,
        pct_white=weighted_pct_white / total_addresses,
        pct_black=weighted_pct_black / total_addresses,
        pct_hispanic=weighted_pct_hispanic / total_addresses,
        pct_asian=weighted_pct_asian / total_addresses,
        pct_other=weighted_pct_other / total_addresses,
        pct_voting_age=weighted_pct_vap / total_addresses,
        pct_housing_occupied=weighted_pct_occupied / total_addresses,
        pct_housing_vacant=weighted_pct_vacant / total_addresses,
    )

"""Recency analysis for codification.

Compares address presence across TIGER vintages to produce a
construction timeline: when did these addresses first appear?
"""

from __future__ import annotations

import abc
import logging
from collections import Counter
from dataclasses import dataclass, field
from typing import Optional

log = logging.getLogger(__name__)

TIGER_VINTAGES = [2010, 2012, 2014, 2016, 2018, 2020, 2022, 2024]


@dataclass
class AddressVintage:
    """Earliest known TIGER vintage for an address.

    Attributes:
        input_id: Address identifier.
        first_vintage: Year the address first appeared in TIGER.
        present_in: List of vintages where the address was found.
    """

    input_id: str = ""
    first_vintage: Optional[int] = None
    present_in: list[int] = field(default_factory=list)

    @property
    def is_new_construction(self) -> bool:
        if not self.present_in:
            return False
        return self.first_vintage == max(self.present_in)


@dataclass
class RecencyAnalysis:
    """Address vintage distribution for a codified area.

    Attributes:
        total_analyzed: Total addresses with vintage data.
        vintage_distribution: Dict of vintage_year → count of addresses.
        vintage_pct: Dict of vintage_year → fraction of addresses.
        new_construction_count: Addresses first appearing in most recent vintage.
        new_construction_pct: Fraction of addresses that are new construction.
        median_vintage: Median first-appearance year.
    """

    total_analyzed: int = 0
    vintage_distribution: dict[int, int] = field(default_factory=dict)
    vintage_pct: dict[int, float] = field(default_factory=dict)
    new_construction_count: int = 0
    new_construction_pct: float = 0.0
    median_vintage: Optional[int] = None


class AddressVintageProvider(abc.ABC):
    """Protocol for determining address vintage from TIGER data."""

    @abc.abstractmethod
    def get_vintages(
        self,
        input_ids: list[str],
    ) -> list[AddressVintage]:
        """Determine first TIGER vintage for each address."""


class DictAddressVintageProvider(AddressVintageProvider):
    """In-memory vintage provider for testing."""

    def __init__(self):
        self._data: dict[str, AddressVintage] = {}

    def add(self, vintage: AddressVintage):
        self._data[vintage.input_id] = vintage

    def get_vintages(self, input_ids: list[str]) -> list[AddressVintage]:
        return [self._data[i] for i in input_ids if i in self._data]


def compute_recency(vintages: list[AddressVintage]) -> RecencyAnalysis:
    """Compute recency analysis from address vintages.

    Args:
        vintages: List of AddressVintage with first_vintage set.
    """
    if not vintages:
        return RecencyAnalysis()

    first_years = [v.first_vintage for v in vintages if v.first_vintage is not None]
    if not first_years:
        return RecencyAnalysis()

    counts = Counter(first_years)
    total = len(first_years)

    distribution = dict(sorted(counts.items()))
    pct = {yr: count / total for yr, count in distribution.items()}

    most_recent = max(first_years)
    new_count = counts[most_recent]

    sorted_years = sorted(first_years)
    mid = len(sorted_years) // 2
    if len(sorted_years) % 2 == 0:
        median = (sorted_years[mid - 1] + sorted_years[mid]) // 2
    else:
        median = sorted_years[mid]

    return RecencyAnalysis(
        total_analyzed=total,
        vintage_distribution=distribution,
        vintage_pct=pct,
        new_construction_count=new_count,
        new_construction_pct=new_count / total,
        median_vintage=median,
    )

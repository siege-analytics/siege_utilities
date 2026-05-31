"""Urbanicity enrichment for codification.

Classifies each matched block's urbanicity using the NCES locale system
and produces an address-weighted distribution.
"""

from __future__ import annotations

import abc
import logging
from collections import Counter
from dataclasses import dataclass, field
from typing import Optional

__all__ = [
    'BlockLocale',
    'UrbanicityDistribution',
    'BlockLocaleProvider',
    'DictBlockLocaleProvider',
    'compute_urbanicity_distribution',
]

log = logging.getLogger(__name__)


@dataclass
class BlockLocale:
    """NCES locale classification for a Census block.

    Attributes:
        block_geoid: Block GEOID.
        locale_code: NCES 2-digit code (e.g., "11").
        locale_label: Human-readable label (e.g., "City-Large").
        category: Top-level (city, suburb, town, rural).
    """

    block_geoid: str = ""
    locale_code: str = ""
    locale_label: str = ""
    category: str = ""


@dataclass
class UrbanicityDistribution:
    """Address-weighted urbanicity distribution for a codified area.

    Attributes:
        total_classified: Number of addresses with urbanicity classification.
        distribution: Dict of locale_code → fraction of addresses.
        category_distribution: Dict of category → fraction of addresses.
        dominant_locale: Most common locale code.
        dominant_category: Most common category.
    """

    total_classified: int = 0
    distribution: dict[str, float] = field(default_factory=dict)
    category_distribution: dict[str, float] = field(default_factory=dict)
    dominant_locale: str = ""
    dominant_category: str = ""


class BlockLocaleProvider(abc.ABC):
    """Protocol for fetching block urbanicity classifications."""

    @abc.abstractmethod
    def classify_blocks(
        self,
        block_geoids: list[str],
        census_year: Optional[int] = None,
    ) -> dict[str, BlockLocale]:
        """Classify blocks by NCES locale.

        Returns dict of block_geoid → BlockLocale.
        """


class DictBlockLocaleProvider(BlockLocaleProvider):
    """In-memory locale provider for testing."""

    def __init__(self):
        self._data: dict[str, BlockLocale] = {}

    def add(self, locale: BlockLocale):
        self._data[locale.block_geoid] = locale

    def classify_blocks(
        self,
        block_geoids: list[str],
        census_year: Optional[int] = None,
    ) -> dict[str, BlockLocale]:
        return {g: self._data[g] for g in block_geoids if g in self._data}


def compute_urbanicity_distribution(
    block_address_counts: dict[str, int],
    locales: dict[str, BlockLocale],
) -> UrbanicityDistribution:
    """Compute address-weighted urbanicity distribution.

    Args:
        block_address_counts: Dict of block_geoid → address count.
        locales: Dict of block_geoid → BlockLocale.
    """
    locale_counts: Counter = Counter()
    category_counts: Counter = Counter()
    total = 0

    for geoid, addr_count in block_address_counts.items():
        locale = locales.get(geoid)
        if locale is None:
            continue
        locale_counts[locale.locale_code] += addr_count
        category_counts[locale.category] += addr_count
        total += addr_count

    if total == 0:
        return UrbanicityDistribution()

    distribution = {code: count / total for code, count in locale_counts.items()}
    category_dist = {cat: count / total for cat, count in category_counts.items()}

    dominant_locale = locale_counts.most_common(1)[0][0] if locale_counts else ""
    dominant_category = category_counts.most_common(1)[0][0] if category_counts else ""

    return UrbanicityDistribution(
        total_classified=total,
        distribution=distribution,
        category_distribution=category_dist,
        dominant_locale=dominant_locale,
        dominant_category=dominant_category,
    )

"""Urbanicity overlay for place history.

NCES locale classification per vintage for a queried geography.
Calls NCESLocaleClassifier (WS3) for each vintage in the range.
"""

from __future__ import annotations

import abc
import logging
from dataclasses import dataclass, field
from typing import Optional

from siege_utilities.geo.overlay_registry import PlaceHistoryOverlay

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------


@dataclass
class UrbanicityPoint:
    """NCES locale classification for a single vintage.

    Attributes:
        year: Vintage year of the classification.
        geoid: GEOID classified.
        locale_code: NCES 2-digit locale code (e.g., "11" for City-Large).
        locale_label: Human-readable label (e.g., "City-Large").
        category: Top-level category (city, suburb, town, rural).
        size: Size qualifier (large, midsize, small, fringe, distant, remote).
    """

    year: int = 0
    geoid: str = ""
    locale_code: str = ""
    locale_label: str = ""
    category: str = ""
    size: str = ""


@dataclass
class UrbanicityOverlayResult:
    """Result of the urbanicity overlay query.

    Attributes:
        geoid: Queried GEOID.
        classifications: Ordered list of urbanicity points by year.
    """

    geoid: str = ""
    classifications: list[UrbanicityPoint] = field(default_factory=list)

    @property
    def years(self) -> list[int]:
        return sorted(set(p.year for p in self.classifications))

    @property
    def has_data(self) -> bool:
        return len(self.classifications) > 0

    def for_year(self, year: int) -> Optional[UrbanicityPoint]:
        for p in self.classifications:
            if p.year == year:
                return p
        return None

    @property
    def changed(self) -> bool:
        codes = set(p.locale_code for p in self.classifications)
        return len(codes) > 1

    @property
    def current_category(self) -> str:
        if not self.classifications:
            return ""
        return self.classifications[-1].category


# ---------------------------------------------------------------------------
# Data provider protocol
# ---------------------------------------------------------------------------


class UrbanicityDataProvider(abc.ABC):
    """Protocol for fetching NCES locale classification data."""

    @abc.abstractmethod
    def classify(
        self,
        geoid: str,
        year: int,
    ) -> Optional[UrbanicityPoint]:
        """Classify a GEOID for a given vintage year."""


class DictUrbanicityProvider(UrbanicityDataProvider):
    """In-memory urbanicity provider for testing."""

    def __init__(self):
        self._data: dict[tuple[str, int], UrbanicityPoint] = {}

    def add(self, point: UrbanicityPoint):
        self._data[(point.geoid, point.year)] = point

    def classify(
        self,
        geoid: str,
        year: int,
    ) -> Optional[UrbanicityPoint]:
        return self._data.get((geoid, year))


# ---------------------------------------------------------------------------
# Overlay implementation
# ---------------------------------------------------------------------------

NCES_VINTAGE_YEARS = [2000, 2010, 2020]


class UrbanicityOverlay(PlaceHistoryOverlay):
    """Place history overlay for NCES urbanicity classification.

    Classifies the queried GEOID using the NCES 12-code locale system
    for each relevant vintage in the query range.

    Args:
        provider: UrbanicityDataProvider for classification.
        vintage_years: Years to check. Defaults to NCES vintages.
    """

    def __init__(
        self,
        provider: Optional[UrbanicityDataProvider] = None,
        vintage_years: Optional[list[int]] = None,
    ):
        self._provider = provider
        self._vintage_years = vintage_years or NCES_VINTAGE_YEARS

    @property
    def name(self) -> str:
        return "urbanicity"

    def fetch(
        self,
        geoid: str,
        from_year: int,
        to_year: int,
        state_fips: Optional[str] = None,
    ) -> UrbanicityOverlayResult:
        provider = self._provider or self._get_default_provider()
        if provider is None:
            raise RuntimeError("No urbanicity data provider available")

        lo = min(from_year, to_year)
        hi = max(from_year, to_year)

        classifications = []
        for vintage in self._vintage_years:
            if vintage < lo or vintage > hi:
                continue
            point = provider.classify(geoid, vintage)
            if point is not None:
                classifications.append(point)

        classifications.sort(key=lambda p: p.year)

        return UrbanicityOverlayResult(
            geoid=geoid,
            classifications=classifications,
        )

    def _get_default_provider(self) -> Optional[UrbanicityDataProvider]:
        try:
            from siege_utilities.geo.django.providers import DjangoUrbanicityProvider
            return DjangoUrbanicityProvider()
        except ImportError:
            log.debug("Django urbanicity provider not available (Django not installed or not configured)")
            return None
        except (RuntimeError, ValueError, TypeError, AttributeError, OSError) as exc:
            log.warning("Failed to initialise Django urbanicity provider: %s", exc)
            return None

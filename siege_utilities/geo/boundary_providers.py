"""
Boundary provider abstraction for geographic boundary data.

Provides a pluggable architecture for fetching administrative boundary geometries
from different sources:

- **CensusTIGERProvider**: US boundaries via Census TIGER/Line shapefiles
- **GADMProvider**: International boundaries via the Database of Global Administrative Areas
- **resolve_boundary_provider()**: Factory that selects the appropriate provider by country

Usage::

    from siege_utilities.geo.boundary_providers import resolve_boundary_provider

    provider = resolve_boundary_provider('US')
    gdf = provider.get_boundary('county', state_fips='06')

    intl_provider = resolve_boundary_provider('DE')
    gdf = intl_provider.get_boundary('admin1', country_code='DEU')
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any, Optional

logger = logging.getLogger(__name__)

__all__ = [
    'BoundaryProvider',
    'CensusTIGERProvider',
    'GADMProvider',
    'resolve_boundary_provider',
]


class BoundaryProvider(ABC):
    """Abstract base class for geographic boundary data providers."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Human-readable name for this provider."""

    @abstractmethod
    def get_boundary(self, level: str, identifier: Optional[str] = None, **kwargs: Any):
        """
        Fetch boundary geometry for a given geographic level.

        Args:
            level: Geographic level (e.g. 'county', 'tract', 'admin1').
            identifier: Optional identifier to narrow the query (e.g. state FIPS).
            **kwargs: Provider-specific options.

        Returns:
            GeoDataFrame with boundary geometries.
        """

    @abstractmethod
    def list_levels(self) -> list[str]:
        """Return the geographic levels this provider supports."""

    @abstractmethod
    def is_available(self) -> bool:
        """Return True if this provider's dependencies are installed and reachable."""


class CensusTIGERProvider(BoundaryProvider):
    """
    US Census TIGER/Line boundary provider.

    Wraps :class:`siege_utilities.geo.spatial_data.CensusDataSource` and
    :data:`siege_utilities.config.census_constants.CANONICAL_GEOGRAPHIC_LEVELS`.
    """

    @property
    def provider_name(self) -> str:
        return 'Census TIGER/Line'

    def get_boundary(self, level: str, identifier: Optional[str] = None, **kwargs: Any):
        """
        Fetch US Census TIGER boundaries.

        Args:
            level: A canonical geographic level (e.g. 'county', 'tract', 'cd').
            identifier: State FIPS code when the level requires it.
            **kwargs: Forwarded to ``CensusDataSource.fetch_geographic_boundaries``
                      (e.g. ``year``, ``congress_number``).

        Returns:
            GeoDataFrame or None.
        """
        from .spatial_data import CensusDataSource

        kwargs.pop('geographic_level', None)  # level arg is authoritative
        call_kwargs: dict[str, Any] = {
            'geographic_level': level,
            **kwargs,
        }
        if identifier is not None:
            call_kwargs['state_fips'] = identifier

        ds = CensusDataSource()
        result = ds.fetch_geographic_boundaries(**call_kwargs)
        if not result.success:
            logger.warning(
                'CensusTIGERProvider: boundary retrieval failed [%s] %s',
                result.error_stage,
                result.message,
            )
            return None
        return result.geodataframe

    def list_levels(self) -> list[str]:
        """Return canonical Census geographic level names."""
        from siege_utilities.config.census_constants import CANONICAL_GEOGRAPHIC_LEVELS
        return sorted(CANONICAL_GEOGRAPHIC_LEVELS.keys())

    def is_available(self) -> bool:
        """Census TIGER provider is always available (pure-HTTP downloads)."""
        return True


# ---------------------------------------------------------------------------
# GADM (Database of Global Administrative Areas)
# ---------------------------------------------------------------------------

# GADM download URL template.  Level 0 = country, 1 = admin1, etc.
_GADM_VERSION = '4.1'
_GADM_BASE_URL = (
    'https://geodata.ucdavis.edu/gadm/gadm{version}/json/gadm{version}_{country}_{level}.json'
)

_GADM_LEVELS = ['country', 'admin1', 'admin2', 'admin3']
_GADM_LEVEL_MAP = {
    'country': 0,
    'admin1': 1,
    'admin2': 2,
    'admin3': 3,
}


class GADMProvider(BoundaryProvider):
    """
    GADM (Global Administrative Areas) boundary provider.

    Downloads GeoJSON boundary files from the GADM project for non-US countries.
    Requires *geopandas* at runtime.
    """

    def __init__(self, version: str = _GADM_VERSION) -> None:
        self._version = version

    @property
    def provider_name(self) -> str:
        return 'GADM'

    def get_boundary(self, level: str, identifier: Optional[str] = None, **kwargs: Any):
        """
        Fetch GADM boundaries for a country.

        Args:
            level: One of 'country', 'admin1', 'admin2', 'admin3'.
            identifier: ISO-3 country code (e.g. 'DEU', 'FRA').
                        Can also be passed as ``country_code`` kwarg.
            **kwargs: ``country_code`` accepted as an alias for *identifier*.

        Returns:
            GeoDataFrame with boundary geometries.

        Raises:
            ValueError: If *level* is unknown or *country_code* is missing.
            ImportError: If geopandas is not installed.
        """
        country_code = kwargs.pop('country_code', None) or identifier
        if country_code is None:
            raise ValueError('GADMProvider.get_boundary() requires a country_code or identifier.')

        numeric_level = _GADM_LEVEL_MAP.get(level)
        if numeric_level is None:
            raise ValueError(
                f"Unknown GADM level {level!r}. Choose from {_GADM_LEVELS}."
            )

        url = _GADM_BASE_URL.format(
            version=self._version,
            country=country_code,
            level=numeric_level,
        )

        try:
            import geopandas as gpd
        except ImportError:
            raise ImportError(
                'GADMProvider requires geopandas. Install with: pip install siege_utilities[geo]'
            )

        logger.info('Downloading GADM boundaries: %s', url)
        return gpd.read_file(url)

    def list_levels(self) -> list[str]:
        """Return GADM administrative levels."""
        return list(_GADM_LEVELS)

    def is_available(self) -> bool:
        """Return True if geopandas is importable."""
        try:
            import geopandas as gpd  # noqa: F401
            return True
        except ImportError:
            return False


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

# ISO-2 codes that should use Census TIGER (US + territories).
_US_CODES = frozenset({
    'US', 'USA',
    'PR', 'PRI',  # Puerto Rico
    'GU', 'GUM',  # Guam
    'VI', 'VIR',  # US Virgin Islands
    'AS', 'ASM',  # American Samoa
    'MP', 'MNP',  # Northern Mariana Islands
})


def resolve_boundary_provider(country: str = 'US', **kwargs: Any) -> BoundaryProvider:
    """
    Return an appropriate :class:`BoundaryProvider` for the given country.

    Args:
        country: ISO-2 or ISO-3 country code (default ``'US'``).
        **kwargs: Forwarded to the provider constructor.

    Returns:
        CensusTIGERProvider for US / US territories, GADMProvider otherwise.
    """
    if country.upper() in _US_CODES:
        return CensusTIGERProvider()
    return GADMProvider(**kwargs)

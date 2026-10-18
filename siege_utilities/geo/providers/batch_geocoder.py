"""Unified batch geocoding interface.

Defines the :class:`BatchGeocoder` abstract base class and
:class:`GeocodingResult` schema for consistent geocoding across
multiple backends (Census, Nominatim, TAMU, etc.).

Usage::

    from siege_utilities.geo.providers.batch_geocoder import (
        BatchGeocoder, GeocodingResult, MatchQuality,
    )
"""

from __future__ import annotations

import abc
import logging
import math
from dataclasses import dataclass, field, asdict
from enum import Enum
from numbers import Number, Real
from typing import Optional, Union

log = logging.getLogger(__name__)

__all__ = ["AddressInput", "BatchGeocoder", "BatchGeocodingResult", "GeocodingResult", "MatchQuality", "normalize_addresses"]


# ---------------------------------------------------------------------------
# Result schema
# ---------------------------------------------------------------------------


class MatchQuality(str, Enum):
    """Geocoding match quality levels."""

    EXACT = "exact"
    INTERPOLATED = "interpolated"
    APPROXIMATE = "approximate"
    CENTROID = "centroid"
    NO_MATCH = "no_match"


@dataclass
class GeocodingResult:
    """Unified geocoding result across all backends.

    Attributes:
        input_address: Original address as submitted.
        input_id: Caller-supplied identifier (preserved through geocoding).
        matched_address: Standardized matched address from the geocoder.
        lat: Latitude of the matched location.
        lon: Longitude of the matched location.
        match_quality: How precise the match is.
        block_geoid: 15-digit Census block GEOID (if available).
        tract_geoid: 11-digit Census tract GEOID (if available).
        county_geoid: 5-digit county GEOID (if available).
        state_geoid: 2-digit state GEOID (if available).
        backend: Name of the geocoding backend that produced this result.
    """

    input_address: str = ""
    input_id: str = ""
    matched_address: str = ""
    lat: Optional[float] = None
    lon: Optional[float] = None
    match_quality: str = MatchQuality.NO_MATCH.value
    block_geoid: str = ""
    tract_geoid: str = ""
    county_geoid: str = ""
    state_geoid: str = ""
    backend: str = ""

    @property
    def matched(self) -> bool:
        return self.match_quality != MatchQuality.NO_MATCH.value

    @property
    def has_block(self) -> bool:
        return len(self.block_geoid) == 15

    @property
    def has_tract(self) -> bool:
        return len(self.tract_geoid) == 11

    def to_dict(self) -> dict:
        d = asdict(self)
        d["matched"] = self.matched
        return d


@dataclass
class BatchGeocodingResult:
    """Container for a batch geocoding run."""

    results: list[GeocodingResult] = field(default_factory=list)
    backend: str = ""
    errors: list[str] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.results)

    @property
    def matched_count(self) -> int:
        return sum(1 for r in self.results if r.matched)

    @property
    def match_rate(self) -> float:
        if not self.results:
            return 0.0
        return self.matched_count / len(self.results)

    def to_dataframe(self):
        """Convert results to a pandas DataFrame.

        Returns:
            DataFrame with one row per result, including all fields.
        """
        import pandas as pd

        if not self.results:
            return pd.DataFrame()
        return pd.DataFrame([r.to_dict() for r in self.results])

    def to_geodataframe(self):
        """Convert results to a GeoDataFrame with point geometry.

        Only includes matched results (those with lat/lon coordinates).

        Returns:
            GeoDataFrame with point geometry in EPSG:4326.
        """
        import geopandas as gpd
        import pandas as pd
        from shapely.geometry import Point

        matched = [r for r in self.results if r.matched and r.lat and r.lon]
        if not matched:
            return gpd.GeoDataFrame()

        df = pd.DataFrame([r.to_dict() for r in matched])
        geometry = [Point(r.lon, r.lat) for r in matched]
        return gpd.GeoDataFrame(df, geometry=geometry, crs="EPSG:4326")


# ---------------------------------------------------------------------------
# Address normalization
# ---------------------------------------------------------------------------


@dataclass
class AddressInput:
    """Normalized address input for batch geocoding."""

    street: str = ""
    city: str = ""
    state: str = ""
    zipcode: str = ""
    input_id: str = ""

    @property
    def one_line(self) -> str:
        parts = [self.street, self.city, self.state, self.zipcode]
        return ", ".join(p for p in parts if isinstance(p, str) and p)


def _normalize_field(value, *, zipcode: bool = False) -> str:
    """Coerce a scalar field, restoring leading zeros only for numeric ZIPs."""
    if value is None or (isinstance(value, Number) and value != value):
        return ""
    if zipcode and isinstance(value, Real):
        return str(int(float(value))).zfill(5) if math.isfinite(value) else ""
    return str(value)


def normalize_addresses(
    addresses: list[Union[dict, str, AddressInput]],
) -> list[AddressInput]:
    """Normalize address input to a list of AddressInput.

    Accepts a mixed list of dicts (street, city, state, zipcode, optional id),
    one-line strings, and AddressInput instances (returned as-is). Dict fields
    become strings, with None and numeric NaN replaced by an empty string.
    Numeric ZIPs are padded to five digits; string ZIPs are preserved verbatim,
    including ZIP+4 values.
    """
    if not addresses:
        return []

    result = []
    for i, addr in enumerate(addresses):
        if isinstance(addr, AddressInput):
            result.append(addr)
        elif isinstance(addr, str):
            result.append(AddressInput(street=addr, input_id=str(i)))
        elif isinstance(addr, dict):
            result.append(AddressInput(
                street=_normalize_field(addr.get("street", addr.get("address", ""))),
                city=_normalize_field(addr.get("city", "")),
                state=_normalize_field(addr.get("state", "")),
                zipcode=_normalize_field(addr.get("zipcode", addr.get("zip", "")), zipcode=True),
                input_id=_normalize_field(addr.get("id", addr.get("input_id", str(i)))),
            ))
        else:
            raise TypeError(f"Unsupported address type: {type(addr)}")
    return result


# ---------------------------------------------------------------------------
# Abstract base class
# ---------------------------------------------------------------------------


class BatchGeocoder(abc.ABC):
    """Abstract base class for batch geocoding backends.

    Subclasses implement :meth:`geocode` to process a list of addresses
    through a specific geocoding service. The interface accepts flexible
    input formats and returns a :class:`BatchGeocodingResult`.

    Example::

        class MyGeocoder(BatchGeocoder):
            @property
            def backend_name(self) -> str:
                return "my_service"

            def geocode(self, addresses, **kwargs):
                normalized = normalize_addresses(addresses)
                results = []
                for addr in normalized:
                    # ... call service ...
                    results.append(GeocodingResult(...))
                return BatchGeocodingResult(results=results, backend=self.backend_name)
    """

    @property
    @abc.abstractmethod
    def backend_name(self) -> str:
        """Short identifier for this backend (e.g., 'census', 'nominatim')."""

    @abc.abstractmethod
    def geocode(
        self,
        addresses: Union[list[dict], list[str], list[AddressInput]],
    ) -> BatchGeocodingResult:
        """Geocode a batch of addresses.

        Args:
            addresses: List of addresses in any supported format.

        Returns:
            BatchGeocodingResult with one GeocodingResult per input address.
        """

    def is_available(self) -> bool:
        """Check if this backend is currently available.

        Default returns True. Override for backends that need API keys
        or network connectivity checks.
        """
        return True

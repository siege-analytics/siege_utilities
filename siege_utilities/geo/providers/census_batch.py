"""Census Bureau batch geocoder backend.

Wraps :func:`geocode_batch_chunked` behind the :class:`BatchGeocoder` ABC,
converting :class:`CensusGeocodeResult` to the unified
:class:`GeocodingResult` schema.
"""

from __future__ import annotations

import logging
from typing import Optional, Union

from .batch_geocoder import (
    AddressInput,
    BatchGeocoder,
    BatchGeocodingResult,
    GeocodingResult,
    MatchQuality,
    normalize_addresses,
)

log = logging.getLogger(__name__)

_MATCH_TYPE_MAP = {
    "Exact": MatchQuality.EXACT.value,
    "Non_Exact": MatchQuality.INTERPOLATED.value,
    "No_Match": MatchQuality.NO_MATCH.value,
}


def _census_result_to_geocoding_result(cr) -> GeocodingResult:
    """Convert a CensusGeocodeResult to a unified GeocodingResult."""
    return GeocodingResult(
        input_address=cr.input_address,
        input_id=cr.input_id,
        matched_address=cr.matched_address,
        lat=cr.lat,
        lon=cr.lon,
        match_quality=_MATCH_TYPE_MAP.get(cr.match_type, MatchQuality.NO_MATCH.value),
        block_geoid=cr.block_geoid,
        tract_geoid=cr.tract_geoid,
        county_geoid=cr.county_geoid,
        state_geoid=cr.state_geoid,
        backend="census",
    )


class CensusBatchGeocoder(BatchGeocoder):
    """Census Bureau batch geocoding backend.

    Wraps the existing Census geocoder functions with automatic chunking
    for datasets larger than 10,000 addresses. Returns block-level GEOIDs
    directly from the Census API (no spatial join needed).

    Args:
        vintage: Census vintage to use. Defaults to Current.
        chunk_size: Max addresses per API call. Default 10,000.
    """

    def __init__(
        self,
        vintage=None,
        chunk_size: int = 10_000,
    ):
        self._vintage = vintage
        self._chunk_size = chunk_size

    @property
    def backend_name(self) -> str:
        return "census"

    def geocode(
        self,
        addresses: Union[list[dict], list[str], list[AddressInput]],
    ) -> BatchGeocodingResult:
        """Geocode addresses via the Census Bureau batch API.

        Args:
            addresses: Addresses in any supported format.
        """
        from .census_geocoder import (
            CensusVintage,
            geocode_batch_chunked,
        )

        normalized = normalize_addresses(addresses)
        if not normalized:
            return BatchGeocodingResult(backend=self.backend_name)

        vintage = self._vintage or CensusVintage.CURRENT

        batch_input = [
            {
                "id": addr.input_id,
                "street": addr.street,
                "city": addr.city,
                "state": addr.state,
                "zipcode": addr.zipcode,
            }
            for addr in normalized
        ]

        result = BatchGeocodingResult(backend=self.backend_name)
        try:
            census_results = geocode_batch_chunked(
                batch_input,
                vintage=vintage,
                chunk_size=self._chunk_size,
            )
            result.results = [
                _census_result_to_geocoding_result(cr)
                for cr in census_results
            ]
        except (OSError, ValueError, TypeError, KeyError, AttributeError, RuntimeError) as exc:
            result.errors.append(f"Census batch geocode error: {exc}")
            log.error("Census batch geocode failed: %s", exc)

        log.info(
            "Census batch: %d/%d matched (%.1f%%)",
            result.matched_count,
            result.total,
            result.match_rate * 100,
        )
        return result

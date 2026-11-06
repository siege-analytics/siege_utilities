"""Census Bureau batch geocoder backend.

Wraps :func:`geocode_batch` behind the :class:`BatchGeocoder` ABC,
converting :class:`CensusGeocodeResult` to the unified
:class:`GeocodingResult` schema.
"""

from __future__ import annotations

import logging
from dataclasses import replace
from typing import Union

from ._batch_ids import _assign_batch_ids
from .batch_geocoder import (
    AddressInput,
    BatchGeocoder,
    BatchGeocodingResult,
    GeocodingResult,
    MatchQuality,
    normalize_addresses,
)

log = logging.getLogger(__name__)

__all__ = [
    'CensusBatchGeocoder',
]

_MATCH_TYPE_MAP = {
    "Exact": MatchQuality.EXACT.value,
    "Non_Exact": MatchQuality.INTERPOLATED.value,
    "No_Match": MatchQuality.NO_MATCH.value,
    "Error": MatchQuality.ERROR.value,
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
        if chunk_size <= 0:
            raise ValueError("chunk_size must be positive")
        self._vintage = vintage
        self._chunk_size = min(chunk_size, 10_000)

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

        Returns:
            One result per input in input order. Failed chunks have "error"
            quality and entries in errors; successful chunks are preserved.
            Caller IDs are metadata, never submission or response join keys.
        """
        from .census_geocoder import (
            CensusVintage,
            geocode_batch,
        )

        normalized = normalize_addresses(addresses)
        if not normalized:
            return BatchGeocodingResult(backend=self.backend_name)

        vintage = self._vintage or CensusVintage.CURRENT
        batch_ids = _assign_batch_ids([addr.input_id for addr in normalized])
        inputs = {batch_ids[i]: addr for i, addr in enumerate(normalized)}

        batch_input = [
            {
                "id": batch_id,
                "street": addr.street,
                "city": addr.city,
                "state": addr.state,
                "zipcode": addr.zipcode,
            }
            for batch_id, addr in inputs.items()
        ]

        result = BatchGeocodingResult(backend=self.backend_name)
        for start in range(0, len(batch_input), self._chunk_size):
            chunk = batch_input[start:start + self._chunk_size]
            chunk_number = start // self._chunk_size + 1
            log.info("Census batch chunk %d (%d addresses)", chunk_number, len(chunk))
            try:
                census_results = geocode_batch(chunk, vintage=vintage)
                chunk_results = {}
                chunk_ids = {addr["id"] for addr in chunk}
                for cr in census_results:
                    if cr.input_id not in chunk_ids or cr.input_id in chunk_results:
                        raise ValueError(f"Unknown or duplicate Census input_id {cr.input_id!r}")
                    chunk_results[cr.input_id] = _census_result_to_geocoding_result(cr)
            except (OSError, ValueError, TypeError, KeyError, AttributeError, RuntimeError) as exc:
                result.errors.append(f"Census batch geocode error in chunk {chunk_number}: {exc}")
                log.error("Census batch chunk %d failed: %s", chunk_number, exc)
                chunk_results = {}

            for addr in chunk:
                batch_id = addr["id"]
                original = inputs[batch_id]
                gr = chunk_results.get(batch_id)
                if gr is None:
                    gr = GeocodingResult(
                        input_address=original.one_line,
                        match_quality=MatchQuality.ERROR.value,
                        backend=self.backend_name,
                    )
                if gr.match_quality == MatchQuality.ERROR.value:
                    result.errors.append(
                        f"Census chunk {chunk_number}: no result for input_id {batch_id!r} "
                        f"(caller id {original.input_id!r})"
                    )
                result.results.append(replace(gr, input_id=original.input_id))

        log.info(
            "Census batch: %d/%d matched (%.1f%%)",
            result.matched_count,
            result.total,
            result.match_rate * 100,
        )
        return result

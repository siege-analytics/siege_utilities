"""Composite batch geocoder with fallback chaining.

Chains multiple :class:`BatchGeocoder` backends by priority,
falling back to the next backend for addresses that fail or
match below a quality threshold.

Typical usage: Census first (free, returns GEOIDs), then
Nominatim or TAMU for failures.
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

__all__ = [
    'CompositeBatchGeocoder',
]

_QUALITY_RANK = {
    MatchQuality.EXACT.value: 4,
    MatchQuality.INTERPOLATED.value: 3,
    MatchQuality.APPROXIMATE.value: 2,
    MatchQuality.CENTROID.value: 1,
    MatchQuality.NO_MATCH.value: 0,
}


def _quality_rank(quality: str) -> int:
    return _QUALITY_RANK.get(quality, 0)


class CompositeBatchGeocoder(BatchGeocoder):
    """Chains geocoding backends by priority with fallback.

    For each address, tries backends in order. If a backend returns
    a match below the minimum quality threshold, the next backend
    is tried. The best result across all backends is kept.

    Args:
        backends: Ordered list of geocoder backends (highest priority first).
        min_quality: Minimum match quality to accept without fallback.
            Default "approximate" — only "centroid" and "no_match" trigger fallback.
        skip_unavailable: Skip backends where is_available() returns False.
            Default True.
    """

    def __init__(
        self,
        backends: list[BatchGeocoder],
        min_quality: str = MatchQuality.APPROXIMATE.value,
        skip_unavailable: bool = True,
    ):
        if not backends:
            raise ValueError("At least one backend is required")
        self._backends = backends
        self._min_quality_rank = _quality_rank(min_quality)
        self._skip_unavailable = skip_unavailable

    @property
    def backend_name(self) -> str:
        return "composite"

    def geocode(
        self,
        addresses: Union[list[dict], list[str], list[AddressInput]],
    ) -> BatchGeocodingResult:
        """Geocode addresses through chained backends.

        Each address is tried against backends in order until a result
        meeting the quality threshold is found, or all backends are
        exhausted. The best result is kept.
        """
        normalized = normalize_addresses(addresses)
        if not normalized:
            return BatchGeocodingResult(backend=self.backend_name)

        available = self._get_available_backends()
        if not available:
            result = BatchGeocodingResult(backend=self.backend_name)
            result.errors.append("No available geocoding backends")
            return result

        best: dict[int, GeocodingResult] = {}
        pending = set(range(len(normalized)))

        for backend in available:
            if not pending:
                break

            pending_addrs = [normalized[i] for i in sorted(pending)]
            pending_indices = sorted(pending)

            try:
                batch_result = backend.geocode(pending_addrs)
            except (OSError, ValueError, TypeError, KeyError, AttributeError, RuntimeError) as exc:
                log.warning(
                    "Backend %s failed: %s", backend.backend_name, exc
                )
                continue

            for idx, gr in zip(pending_indices, batch_result.results):
                current_rank = _quality_rank(gr.match_quality)
                prev = best.get(idx)

                if prev is None or current_rank > _quality_rank(prev.match_quality):
                    best[idx] = gr

                if current_rank >= self._min_quality_rank:
                    pending.discard(idx)

        results = []
        for i in range(len(normalized)):
            if i in best:
                results.append(best[i])
            else:
                results.append(GeocodingResult(
                    input_address=normalized[i].one_line,
                    input_id=normalized[i].input_id,
                    match_quality=MatchQuality.NO_MATCH.value,
                    backend=self.backend_name,
                ))

        result = BatchGeocodingResult(
            results=results,
            backend=self.backend_name,
        )

        log.info(
            "Composite batch: %d/%d matched (%.1f%%) across %d backends",
            result.matched_count,
            result.total,
            result.match_rate * 100,
            len(available),
        )
        return result

    def _get_available_backends(self) -> list[BatchGeocoder]:
        if self._skip_unavailable:
            return [b for b in self._backends if b.is_available()]
        return list(self._backends)

"""Composite batch geocoder with fallback chaining.

Chains multiple :class:`BatchGeocoder` backends by priority,
falling back to the next backend for addresses that fail or
match below a quality threshold.

Typical usage: Census first (free, returns GEOIDs), then
Nominatim or TAMU for failures.
"""

from __future__ import annotations

import logging
from collections import Counter
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
            Default "approximate"; "centroid", "no_match", and "error"
            trigger fallback.
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
        exhausted. The best result is kept. Backends receive library IDs;
        caller IDs are restored on output. Backend failures and missing or
        ambiguous response rows are errors, distinct from a genuine no match.
        Errors remain visible even if a later backend succeeds.
        """
        normalized = normalize_addresses(addresses)
        if not normalized:
            return BatchGeocodingResult(backend=self.backend_name)

        batch_ids = _assign_batch_ids([addr.input_id for addr in normalized])
        inputs = {batch_ids[i]: addr for i, addr in enumerate(normalized)}
        available = self._get_available_backends()
        errors = [] if available else ["No available geocoding backends"]
        best: dict[str, GeocodingResult] = {}
        pending = set(inputs)

        for backend in available:
            if not pending:
                break

            pending_addrs = [
                replace(addr, input_id=batch_id)
                for batch_id, addr in inputs.items() if batch_id in pending
            ]

            try:
                batch_result = backend.geocode(pending_addrs)
            except (OSError, ValueError, TypeError, KeyError, AttributeError, RuntimeError) as exc:
                log.warning(
                    "Backend %s failed: %s", backend.backend_name, exc
                )
                batch_result = BatchGeocodingResult(
                    errors=[f"Backend {backend.backend_name} failed: {exc}"],
                )

            errors.extend(batch_result.errors)
            counts = Counter(gr.input_id for gr in batch_result.results)
            returned = {}
            for gr in batch_result.results:
                if gr.input_id not in pending:
                    errors.append(f"Backend {backend.backend_name} returned unknown input_id {gr.input_id!r}")
                elif counts[gr.input_id] == 1:
                    returned[gr.input_id] = gr

            for addr in pending_addrs:
                batch_id = addr.input_id
                gr = returned.get(batch_id)
                if gr is None:
                    reason = "duplicate" if counts[batch_id] else "missing"
                    errors.append(f"Backend {backend.backend_name}: {reason} result for input_id {batch_id!r}")
                    gr = GeocodingResult(
                        input_id=batch_id,
                        input_address=addr.one_line,
                        match_quality=MatchQuality.ERROR.value,
                        backend=backend.backend_name,
                    )
                current_rank = _quality_rank(gr.match_quality)
                prev = best.get(batch_id)

                if (
                    prev is None
                    or current_rank > _quality_rank(prev.match_quality)
                    or (not prev.matched and gr.match_quality == MatchQuality.ERROR.value)
                ):
                    best[batch_id] = gr

                if gr.match_quality != MatchQuality.ERROR.value and current_rank >= self._min_quality_rank:
                    pending.discard(batch_id)

        results = []
        for batch_id, addr in inputs.items():
            if batch_id in best:
                results.append(replace(best[batch_id], input_id=addr.input_id))
            else:
                results.append(GeocodingResult(
                    input_address=addr.one_line,
                    input_id=addr.input_id,
                    match_quality=MatchQuality.ERROR.value,
                    backend=self.backend_name,
                ))

        result = BatchGeocodingResult(
            results=results,
            backend=self.backend_name,
            errors=errors,
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

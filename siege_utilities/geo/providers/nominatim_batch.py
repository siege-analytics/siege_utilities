"""Nominatim batch geocoder backend.

Wraps Nominatim geocoding (public or self-hosted) behind the
:class:`BatchGeocoder` ABC with configurable rate limiting.

Nominatim does not return Census GEOIDs — those must be assigned
via spatial join if needed.
"""

from __future__ import annotations

import json
import logging
import time
import urllib.parse
import urllib.request
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
    'NominatimBatchGeocoder',
    'PUBLIC_NOMINATIM_URL',
    'DEFAULT_RATE_LIMIT',
    'SELF_HOSTED_RATE_LIMIT',
]

PUBLIC_NOMINATIM_URL = "https://nominatim.openstreetmap.org"
DEFAULT_RATE_LIMIT = 1.0  # seconds between requests for public instance
SELF_HOSTED_RATE_LIMIT = 0.05


class NominatimBatchGeocoder(BatchGeocoder):
    """Nominatim geocoding backend with rate limiting.

    Uses the existing geocoding infrastructure to query Nominatim
    one address at a time (Nominatim has no true batch API).

    Args:
        server_url: Nominatim endpoint. Defaults to public instance.
        rate_limit: Seconds between requests. Default 1.0 for public,
            0.05 for self-hosted (auto-detected from URL).
        country_codes: Restrict results to these countries (e.g., ['us']).
        max_retries: Max retries per address on transient failure.
    """

    def __init__(
        self,
        server_url: Optional[str] = None,
        rate_limit: Optional[float] = None,
        country_codes: Optional[list[str]] = None,
        max_retries: int = 2,
    ):
        self._server_url = server_url or PUBLIC_NOMINATIM_URL
        if rate_limit is not None:
            self._rate_limit = rate_limit
        elif self._server_url == PUBLIC_NOMINATIM_URL:
            self._rate_limit = DEFAULT_RATE_LIMIT
        else:
            self._rate_limit = SELF_HOSTED_RATE_LIMIT
        self._country_codes = country_codes or ["us"]
        self._max_retries = max_retries

    @property
    def backend_name(self) -> str:
        return "nominatim"

    def geocode(
        self,
        addresses: Union[list[dict], list[str], list[AddressInput]],
    ) -> BatchGeocodingResult:
        """Geocode addresses via Nominatim (one at a time with rate limiting).

        Args:
            addresses: Addresses in any supported format.
        """
        normalized = normalize_addresses(addresses)
        if not normalized:
            return BatchGeocodingResult(backend=self.backend_name)

        result = BatchGeocodingResult(backend=self.backend_name)
        last_request_time = 0.0

        for addr in normalized:
            elapsed = time.monotonic() - last_request_time
            if elapsed < self._rate_limit:
                time.sleep(self._rate_limit - elapsed)

            gr = self._geocode_single(addr)
            result.results.append(gr)
            last_request_time = time.monotonic()

        log.info(
            "Nominatim batch: %d/%d matched (%.1f%%)",
            result.matched_count,
            result.total,
            result.match_rate * 100,
        )
        return result

    def _geocode_single(self, addr: AddressInput) -> GeocodingResult:
        """Geocode a single address via Nominatim HTTP API."""
        query = addr.one_line
        if not query:
            return GeocodingResult(
                input_address=query,
                input_id=addr.input_id,
                match_quality=MatchQuality.NO_MATCH.value,
                backend=self.backend_name,
            )

        try:
            coords = self._nominatim_request(query)
            if coords is not None:
                lat, lon = coords
                return GeocodingResult(
                    input_address=query,
                    input_id=addr.input_id,
                    lat=lat,
                    lon=lon,
                    match_quality=MatchQuality.APPROXIMATE.value,
                    backend=self.backend_name,
                )
        except (OSError, ValueError, TypeError, KeyError, AttributeError) as exc:
            log.warning("Nominatim geocode failed for %s: %s", addr.input_id, exc)

        return GeocodingResult(
            input_address=query,
            input_id=addr.input_id,
            match_quality=MatchQuality.NO_MATCH.value,
            backend=self.backend_name,
        )

    def _nominatim_request(self, query: str) -> Optional[tuple[float, float]]:
        """Make a single Nominatim search request.

        Returns (lat, lon) or None if no match.
        """
        params = urllib.parse.urlencode({
            "q": query,
            "format": "json",
            "limit": "1",
            "countrycodes": ",".join(self._country_codes),
        })
        url = f"{self._server_url}/search?{params}"

        req = urllib.request.Request(url, headers={
            "User-Agent": "siege_utilities geocoder",
        })

        for attempt in range(self._max_retries + 1):
            try:
                with urllib.request.urlopen(req, timeout=10) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    if data and len(data) > 0:
                        lat = float(data[0]["lat"])
                        lon = float(data[0]["lon"])
                        return (lat, lon)
                    return None
            except (OSError, ValueError, TypeError):
                if attempt == self._max_retries:
                    raise
                time.sleep(self._rate_limit)

        return None

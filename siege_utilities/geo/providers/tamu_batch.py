"""Texas A&M Geoservices batch geocoder backend.

Wraps the TAMU geocoding API behind the :class:`BatchGeocoder` ABC.
TAMU returns Census geography (state, county, tract, block GEOIDs)
directly in its response, so no spatial join is needed.

Requires an API key — get one at https://geoservices.tamu.edu/.
"""

from __future__ import annotations

import json
import logging
import os
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

TAMU_BASE_URL = "https://geoservices.tamu.edu/Services/Geocode/WebService/GeocoderWebServiceHttpNonParsed_V04_01.aspx"
DEFAULT_RATE_LIMIT = 0.25
ENV_API_KEY = "TAMU_API_KEY"

_MATCH_QUALITY_MAP = {
    "exact": MatchQuality.EXACT.value,
    "nearexact": MatchQuality.EXACT.value,
    "interpolated": MatchQuality.INTERPOLATED.value,
    "approximate": MatchQuality.APPROXIMATE.value,
}


class TAMUBatchGeocoder(BatchGeocoder):
    """Texas A&M Geoservices geocoding backend.

    Geocodes addresses one at a time via TAMU's HTTP API.
    Returns Census geography (block-level GEOIDs) directly.

    Args:
        api_key: TAMU API key. Falls back to TAMU_API_KEY env var.
        rate_limit: Seconds between requests. Default 0.25.
        census_year: Census year for geography lookup. Default "2020".
        max_retries: Max retries per address on transient failure.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        rate_limit: float = DEFAULT_RATE_LIMIT,
        census_year: str = "2020",
        max_retries: int = 2,
    ):
        self._api_key = api_key or os.environ.get(ENV_API_KEY, "")
        self._rate_limit = rate_limit
        self._census_year = census_year
        self._max_retries = max_retries

    @property
    def backend_name(self) -> str:
        return "tamu"

    def is_available(self) -> bool:
        return bool(self._api_key)

    def geocode(
        self,
        addresses: Union[list[dict], list[str], list[AddressInput]],
        **kwargs,
    ) -> BatchGeocodingResult:
        """Geocode addresses via the TAMU Geoservices API.

        Args:
            addresses: Addresses in any supported format.
        """
        normalized = normalize_addresses(addresses)
        if not normalized:
            return BatchGeocodingResult(backend=self.backend_name)

        if not self._api_key:
            result = BatchGeocodingResult(backend=self.backend_name)
            result.errors.append("TAMU API key not configured")
            return result

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
            "TAMU batch: %d/%d matched (%.1f%%)",
            result.matched_count,
            result.total,
            result.match_rate * 100,
        )
        return result

    def _geocode_single(self, addr: AddressInput) -> GeocodingResult:
        """Geocode a single address via TAMU."""
        query = addr.one_line
        if not query:
            return GeocodingResult(
                input_address=query,
                input_id=addr.input_id,
                match_quality=MatchQuality.NO_MATCH.value,
                backend=self.backend_name,
            )

        try:
            resp = self._tamu_request(addr)
            if resp is not None:
                return resp
        except Exception as exc:
            log.warning("TAMU geocode failed for %s: %s", addr.input_id, exc)

        return GeocodingResult(
            input_address=query,
            input_id=addr.input_id,
            match_quality=MatchQuality.NO_MATCH.value,
            backend=self.backend_name,
        )

    def _tamu_request(self, addr: AddressInput) -> Optional[GeocodingResult]:
        """Make a single TAMU geocoding request.

        Returns a GeocodingResult or None if no match.
        """
        params = {
            "streetAddress": addr.street,
            "city": addr.city,
            "state": addr.state,
            "zip": addr.zipcode,
            "apiKey": self._api_key,
            "format": "json",
            "census": "true",
            "censusYear": self._census_year,
            "version": "4.01",
        }
        url = f"{TAMU_BASE_URL}?{urllib.parse.urlencode(params)}"

        req = urllib.request.Request(url, headers={
            "User-Agent": "siege_utilities geocoder",
        })

        for attempt in range(self._max_retries + 1):
            try:
                with urllib.request.urlopen(req, timeout=15) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    return self._parse_response(data, addr)
            except Exception:
                if attempt == self._max_retries:
                    raise
                time.sleep(self._rate_limit)

        return None

    def _parse_response(
        self, data: dict, addr: AddressInput
    ) -> Optional[GeocodingResult]:
        """Parse TAMU JSON response into a GeocodingResult."""
        output_geocodes = data.get("OutputGeocodes", [])
        if not output_geocodes:
            return None

        geocode = output_geocodes[0]
        geocode_attrs = geocode.get("OutputGeocode", {})
        matched_address = geocode_attrs.get("MatchedAddress", "")
        lat_str = geocode_attrs.get("Latitude", "")
        lon_str = geocode_attrs.get("Longitude", "")

        match_type = geocode_attrs.get("MatchType", "").lower()
        quality = _MATCH_QUALITY_MAP.get(match_type, MatchQuality.APPROXIMATE.value)

        if not lat_str or not lon_str:
            return None

        try:
            lat = float(lat_str)
            lon = float(lon_str)
        except (ValueError, TypeError):
            return None

        if lat == 0.0 and lon == 0.0:
            return None

        state_geoid = ""
        county_geoid = ""
        tract_geoid = ""
        block_geoid = ""

        census_values = geocode.get("CensusValues", [])
        if census_values:
            cv = census_values[0].get("CensusValue1", {})
            state_fips = cv.get("CensusStateFips", "")
            county_fips = cv.get("CensusCountyFips", "")
            tract = cv.get("CensusTract", "")
            block = cv.get("CensusBlock", "")

            if state_fips:
                state_geoid = state_fips
            if state_fips and county_fips:
                county_geoid = f"{state_fips}{county_fips}"
            if state_fips and county_fips and tract:
                tract_geoid = f"{state_fips}{county_fips}{tract}"
            if state_fips and county_fips and tract and block:
                block_geoid = f"{state_fips}{county_fips}{tract}{block}"

        return GeocodingResult(
            input_address=addr.one_line,
            input_id=addr.input_id,
            matched_address=matched_address,
            lat=lat,
            lon=lon,
            match_quality=quality,
            state_geoid=state_geoid,
            county_geoid=county_geoid,
            tract_geoid=tract_geoid,
            block_geoid=block_geoid,
            backend=self.backend_name,
        )

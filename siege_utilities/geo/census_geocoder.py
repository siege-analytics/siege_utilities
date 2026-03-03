"""
Census Bureau Geocoder integration with historical vintage support.

Wraps the Census Bureau's geocoding API for US address geocoding. Returns
FIPS codes directly (state, county, tract, block) so most addresses don't
need a spatial join. Supports historical vintages for temporal accuracy.

Usage:
    from siege_utilities.geo import (
        CensusVintage, select_vintage_for_cycle,
        geocode_single, geocode_batch, CensusGeocodeResult,
    )

    # Single address
    result = geocode_single("1600 Pennsylvania Ave", "Washington", "DC", "20500")

    # Batch (up to 10,000)
    results = geocode_batch(addresses, vintage=CensusVintage.CENSUS_2020)

    # Auto-select vintage for an FEC cycle year
    vintage = select_vintage_for_cycle(2018)  # -> CensusVintage.CENSUS_2020
"""

import csv
import io
import logging
import tempfile
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

try:
    from siege_utilities import log_warning, log_info, log_debug, log_error
except ImportError:
    def log_warning(message): print(f"WARNING: {message}")
    def log_info(message): print(f"INFO: {message}")
    def log_debug(message): print(f"DEBUG: {message}")
    def log_error(message): print(f"ERROR: {message}")

logger = logging.getLogger(__name__)


class CensusVintage(str, Enum):
    """Census geocoder benchmark/vintage pairs.

    Each value is the benchmark string accepted by the Census Geocoder API.
    The vintage determines which geographic boundaries are used for matching.
    """
    CENSUS_2010 = "Census2010_Census2010"
    CENSUS_2020 = "Census2020_Census2020"
    CURRENT = "Public_Current"
    ACS_2022 = "Public_ACS2022"
    ACS_2023 = "Public_ACS2023"

    @property
    def benchmark(self) -> str:
        """Extract the benchmark portion (before underscore)."""
        return self.value.split("_")[0]

    @property
    def vintage(self) -> str:
        """Extract the vintage portion (after underscore)."""
        parts = self.value.split("_", 1)
        return parts[1] if len(parts) > 1 else parts[0]


# Year boundaries for vintage selection
_VINTAGE_THRESHOLDS = [
    (2020, CensusVintage.CURRENT),
    (2012, CensusVintage.CENSUS_2020),
    (1980, CensusVintage.CENSUS_2010),
]


def select_vintage_for_cycle(year: int) -> CensusVintage:
    """Select the appropriate Census vintage for an FEC cycle year.

    Args:
        year: The FEC election cycle year.

    Returns:
        CensusVintage matching the boundaries in effect for that cycle.

    Examples:
        >>> select_vintage_for_cycle(2024)
        <CensusVintage.CURRENT: 'Public_Current'>
        >>> select_vintage_for_cycle(2016)
        <CensusVintage.CENSUS_2020: 'Census2020_Census2020'>
        >>> select_vintage_for_cycle(2008)
        <CensusVintage.CENSUS_2010: 'Census2010_Census2010'>
    """
    for threshold, vintage in _VINTAGE_THRESHOLDS:
        if year >= threshold:
            return vintage
    return CensusVintage.CENSUS_2010


@dataclass
class CensusGeocodeResult:
    """Result from Census Bureau geocoding.

    Attributes:
        matched: Whether the address was matched.
        input_address: The original input address string.
        matched_address: The standardized matched address (if matched).
        lat: Latitude (if matched).
        lon: Longitude (if matched).
        state_fips: 2-digit state FIPS code.
        county_fips: 3-digit county FIPS code.
        tract: 6-digit tract code.
        block: 4-digit block code.
        match_type: "Exact", "Non_Exact", or "No_Match".
        side: Street side ("L" or "R", from TIGER).
        tiger_line_id: TIGER/Line feature ID.
    """
    matched: bool = False
    input_address: str = ""
    matched_address: str = ""
    lat: Optional[float] = None
    lon: Optional[float] = None
    state_fips: str = ""
    county_fips: str = ""
    tract: str = ""
    block: str = ""
    match_type: str = "No_Match"
    side: str = ""
    tiger_line_id: str = ""
    # Populated by id if provided in batch input
    input_id: str = ""

    @property
    def state_geoid(self) -> str:
        """2-digit state GEOID."""
        return self.state_fips if self.state_fips else ""

    @property
    def county_geoid(self) -> str:
        """5-digit county GEOID (state + county FIPS)."""
        if self.state_fips and self.county_fips:
            return f"{self.state_fips}{self.county_fips}"
        return ""

    @property
    def tract_geoid(self) -> str:
        """11-digit tract GEOID (state + county + tract)."""
        if self.state_fips and self.county_fips and self.tract:
            return f"{self.state_fips}{self.county_fips}{self.tract}"
        return ""

    @property
    def block_geoid(self) -> str:
        """15-digit block GEOID (state + county + tract + block)."""
        if self.state_fips and self.county_fips and self.tract and self.block:
            return f"{self.state_fips}{self.county_fips}{self.tract}{self.block}"
        return ""

    @property
    def block_group_geoid(self) -> str:
        """12-digit block group GEOID (block GEOID truncated to 12 chars)."""
        bg = self.block_geoid
        return bg[:12] if len(bg) >= 12 else ""


def _get_geocoder(vintage: CensusVintage = CensusVintage.CURRENT):
    """Get a censusgeocode.CensusGeocode instance with the specified vintage."""
    try:
        import censusgeocode
    except ImportError:
        raise ImportError(
            "censusgeocode is required for Census geocoding. "
            "Install it with: pip install 'siege-utilities[geo]' or pip install censusgeocode"
        )
    return censusgeocode.CensusGeocode(
        benchmark=vintage.benchmark,
        vintage=vintage.vintage,
    )


def _parse_single_result(result: dict) -> CensusGeocodeResult:
    """Parse a single result dict from censusgeocode into a CensusGeocodeResult."""
    if not result:
        return CensusGeocodeResult()

    matched_address = result.get("matchedAddress", "")
    coords = result.get("coordinates", {})
    geographies = result.get("geographies", {})
    tiger = result.get("addressComponents", {})

    # Census Blocks is the most detailed geography; extract FIPS from there
    blocks = geographies.get("Census Blocks", geographies.get("2020 Census Blocks", []))
    if not blocks:
        # Try other geography keys
        for key in geographies:
            if "block" in key.lower() or "tract" in key.lower():
                blocks = geographies[key]
                break

    geo_data = blocks[0] if blocks else {}

    return CensusGeocodeResult(
        matched=True,
        matched_address=matched_address,
        lat=coords.get("y"),
        lon=coords.get("x"),
        state_fips=geo_data.get("STATE", ""),
        county_fips=geo_data.get("COUNTY", ""),
        tract=geo_data.get("TRACT", ""),
        block=geo_data.get("BLOCK", ""),
        match_type="Exact",
        side=tiger.get("side", ""),
        tiger_line_id=tiger.get("tigerLineId", ""),
    )


def geocode_single(
    street: str,
    city: str,
    state: str,
    zipcode: str,
    vintage: CensusVintage = CensusVintage.CURRENT,
) -> CensusGeocodeResult:
    """Geocode a single address via the Census Bureau API.

    Args:
        street: Street address (e.g., "1600 Pennsylvania Ave NW").
        city: City name.
        state: State abbreviation or name.
        zipcode: ZIP code.
        vintage: Census vintage for boundary matching.

    Returns:
        CensusGeocodeResult with lat/lon and FIPS codes if matched.
    """
    cg = _get_geocoder(vintage)
    input_addr = f"{street}, {city}, {state} {zipcode}"

    try:
        result = cg.onelineaddress(input_addr, returntype="geographies")
        matches = result.get("result", {}).get("addressMatches", [])
        if not matches:
            log_info(f"No match for: {input_addr}")
            return CensusGeocodeResult(input_address=input_addr)

        parsed = _parse_single_result(matches[0])
        parsed.input_address = input_addr
        log_debug(f"Matched: {input_addr} -> {parsed.matched_address}")
        return parsed

    except Exception as e:
        log_error(f"Census geocode failed for {input_addr}: {e}")
        return CensusGeocodeResult(input_address=input_addr)


def geocode_batch(
    addresses: list[dict],
    vintage: CensusVintage = CensusVintage.CURRENT,
) -> list[CensusGeocodeResult]:
    """Geocode a batch of addresses via the Census Bureau batch API.

    The Census batch API accepts up to 10,000 addresses per request.
    Each address dict should have keys: id, street, city, state, zipcode.

    Args:
        addresses: List of dicts with keys {id, street, city, state, zipcode}.
        vintage: Census vintage for boundary matching.

    Returns:
        List of CensusGeocodeResult, one per input address (order preserved).

    Raises:
        ValueError: If batch exceeds 10,000 addresses.
    """
    if len(addresses) > 10_000:
        raise ValueError(
            f"Census batch API accepts max 10,000 addresses, got {len(addresses)}. "
            "Use geocode_batch_chunked() for larger sets."
        )

    if not addresses:
        return []

    cg = _get_geocoder(vintage)

    # Build CSV for batch submission
    csv_buffer = io.StringIO()
    writer = csv.writer(csv_buffer)
    for addr in addresses:
        writer.writerow([
            addr.get("id", ""),
            addr.get("street", ""),
            addr.get("city", ""),
            addr.get("state", ""),
            addr.get("zipcode", ""),
        ])

    # Write to temp file for censusgeocode
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        f.write(csv_buffer.getvalue())
        csv_path = f.name

    try:
        result = cg.addressbatch(csv_path, returntype="geographies")
    except Exception as e:
        log_error(f"Census batch geocode failed: {e}")
        return [
            CensusGeocodeResult(
                input_id=addr.get("id", ""),
                input_address=f"{addr.get('street', '')}, {addr.get('city', '')}, {addr.get('state', '')} {addr.get('zipcode', '')}",
            )
            for addr in addresses
        ]

    # Parse batch results
    results_by_id = {}
    if isinstance(result, list):
        for row in result:
            row_id = str(row.get("id", ""))
            matched = row.get("is_match", "").strip().lower() == "match"
            if matched:
                parsed = CensusGeocodeResult(
                    matched=True,
                    input_id=row_id,
                    input_address=row.get("address", ""),
                    matched_address=row.get("match_address", ""),
                    lat=_safe_float(row.get("lat")),
                    lon=_safe_float(row.get("lon")),
                    state_fips=row.get("statefp", ""),
                    county_fips=row.get("countyfp", ""),
                    tract=row.get("tract", ""),
                    block=row.get("block", ""),
                    match_type=row.get("match_type", ""),
                    tiger_line_id=row.get("tigerlineid", ""),
                    side=row.get("side", ""),
                )
            else:
                parsed = CensusGeocodeResult(
                    input_id=row_id,
                    input_address=row.get("address", ""),
                )
            results_by_id[row_id] = parsed

    # Return in input order
    output = []
    for addr in addresses:
        addr_id = str(addr.get("id", ""))
        if addr_id in results_by_id:
            output.append(results_by_id[addr_id])
        else:
            output.append(CensusGeocodeResult(
                input_id=addr_id,
                input_address=f"{addr.get('street', '')}, {addr.get('city', '')}, {addr.get('state', '')} {addr.get('zipcode', '')}",
            ))

    matched_count = sum(1 for r in output if r.matched)
    log_info(f"Census batch: {matched_count}/{len(output)} matched")
    return output


def geocode_batch_chunked(
    addresses: list[dict],
    vintage: CensusVintage = CensusVintage.CURRENT,
    chunk_size: int = 10_000,
) -> list[CensusGeocodeResult]:
    """Geocode addresses in chunks of up to chunk_size (default 10,000).

    Convenience wrapper around geocode_batch() for larger datasets.

    Args:
        addresses: List of dicts with keys {id, street, city, state, zipcode}.
        vintage: Census vintage for boundary matching.
        chunk_size: Max addresses per API call (max 10,000).

    Returns:
        List of CensusGeocodeResult, one per input address.
    """
    chunk_size = min(chunk_size, 10_000)
    results = []
    total = len(addresses)

    for i in range(0, total, chunk_size):
        chunk = addresses[i:i + chunk_size]
        chunk_num = (i // chunk_size) + 1
        total_chunks = (total + chunk_size - 1) // chunk_size
        log_info(f"Census batch chunk {chunk_num}/{total_chunks} ({len(chunk)} addresses)")
        results.extend(geocode_batch(chunk, vintage=vintage))

    return results


def _safe_float(val) -> Optional[float]:
    """Safely convert a value to float, returning None on failure."""
    if val is None:
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None

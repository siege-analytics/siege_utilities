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
    vintage = select_vintage_for_cycle(2018)  # -> CensusVintage.CENSUS_2010
"""

import csv
import io
import logging
import os
import tempfile
from dataclasses import dataclass
from enum import Enum
from typing import Optional, TYPE_CHECKING

from ._batch_ids import _assign_batch_ids

if TYPE_CHECKING:
    import pandas as pd

logger = logging.getLogger(__name__)

__all__ = [
    'CensusGeocodeError',
    'CensusGeocodeResult',
    'CensusVintage',
    'geocode_batch',
    'geocode_batch_chunked',
    'geocode_results_to_dataframe',
    'geocode_single',
    'select_vintage_for_cycle',
]


def log_warning(message: str) -> None:
    logger.warning(message)


def log_info(message: str) -> None:
    logger.info(message)


def log_debug(message: str) -> None:
    logger.debug(message)


def log_error(message: str) -> None:
    logger.error(message)


class CensusGeocodeError(RuntimeError):
    """Raised when the Census geocoder API call fails unexpectedly.

    Distinct from "no match" results (which return a CensusGeocodeResult with
    matched=False). This exception indicates an API / network / parse failure
    where the geocoder could not even attempt to match. Use `__cause__` to
    inspect the underlying exception.
    """


class CensusVintage(str, Enum):
    """Census geocoder benchmark/vintage pairs.

    Each member's value encodes ``<benchmark>|<vintage>`` where both halves
    are the exact strings the Census Geocoder API expects.  Use the
    ``.benchmark`` and ``.vintage`` properties to extract them.

    The benchmark names follow the ``Public_AR_<label>`` pattern used by
    ``https://geocoding.geo.census.gov/geocoder/benchmarks``.  The vintage
    names follow the ``<label>_<benchmark-label>`` pattern returned by
    ``https://geocoding.geo.census.gov/geocoder/vintages?benchmark=…``.
    """
    CENSUS_2010 = "Public_AR_Census2020|Census2010_Census2020"
    CENSUS_2020 = "Public_AR_Census2020|Census2020_Census2020"
    CURRENT = "Public_AR_Current|Current_Current"
    ACS_2022 = "Public_AR_Current|ACS2022_Current"
    ACS_2023 = "Public_AR_Current|ACS2023_Current"

    @property
    def benchmark(self) -> str:
        """The benchmark string accepted by the Census Geocoder API."""
        return self.value.split("|")[0]

    @property
    def vintage(self) -> str:
        """The vintage string accepted by the Census Geocoder API."""
        return self.value.split("|")[1]


# Descending year boundaries for vintage selection; the first match wins.
_VINTAGE_THRESHOLDS = [
    (2022, CensusVintage.CURRENT),
    (2012, CensusVintage.CENSUS_2010),
    (1980, CensusVintage.CENSUS_2010),
]


def select_vintage_for_cycle(year: int) -> CensusVintage:
    """Select the appropriate Census vintage for an FEC cycle year.

    The 2012-2020 election cycles used districts drawn on 2010 Census
    geography, so years from 2012 through 2021 use CENSUS_2010 on the
    Census2020 benchmark. Years from 2022 onward preserve the CURRENT
    tier, which currently supplies 2020 Census blocks. CURRENT follows
    Census updates; use CENSUS_2020 explicitly for a fixed 2020 vintage.

    Years before 2012 retain the CENSUS_2010 fallback. CensusVintage does
    not offer 2000 or earlier geography, so this fallback does not match
    the historical district boundaries for those cycles.

    Args:
        year: The FEC election cycle year.

    Returns:
        CensusVintage for the cycle's decennial geography, subject to the
        pre-2012 fallback and the CURRENT tier described above.

    Examples:
        >>> select_vintage_for_cycle(2024)
        <CensusVintage.CURRENT: 'Public_AR_Current|Current_Current'>
        >>> select_vintage_for_cycle(2016)
        <CensusVintage.CENSUS_2010: 'Public_AR_Census2020|Census2010_Census2020'>
        >>> select_vintage_for_cycle(2012)
        <CensusVintage.CENSUS_2010: 'Public_AR_Census2020|Census2010_Census2020'>
        >>> select_vintage_for_cycle(2020)
        <CensusVintage.CENSUS_2010: 'Public_AR_Census2020|Census2010_Census2020'>
        >>> select_vintage_for_cycle(2022)
        <CensusVintage.CURRENT: 'Public_AR_Current|Current_Current'>
        >>> select_vintage_for_cycle(2008)
        <CensusVintage.CENSUS_2010: 'Public_AR_Census2020|Census2010_Census2020'>
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
        match_type: "Exact", "Non_Exact", "No_Match", or "Error" for a missing row.
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
    # Caller metadata on public output; library ID between provider layers.
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
    except ImportError as e:
        raise ImportError(
            "censusgeocode is required for Census geocoding. "
            "Install it with: pip install 'siege-utilities[geo]' or pip install censusgeocode"
        ) from e
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
    tiger = result.get("tigerLine", {})

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
        # censusgeocode v0.5+ returns an AddressResult (list-like) of
        # match dicts, not a nested {"result": {"addressMatches": [...]}}
        # structure.
        result = cg.onelineaddress(input_addr, returntype="geographies")
        if not result or len(result) == 0:
            log_info(f"No match for: {input_addr}")
            return CensusGeocodeResult(input_address=input_addr)

        parsed = _parse_single_result(result[0])
        parsed.input_address = input_addr
        log_debug(f"Matched: {input_addr} -> {parsed.matched_address}")
        return parsed

    except Exception as e:
        raise CensusGeocodeError(
            f"Census geocode failed for {input_addr}: {e}"
        ) from e


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
        Caller IDs are passthrough metadata, including missing or duplicate
        IDs. Submission and response alignment use library-assigned IDs.
        A missing response row has match_type="Error", not "No_Match".

    Raises:
        ValueError: If batch exceeds 10,000 addresses.
        CensusGeocodeError: On API failure or ambiguous response IDs.
    """
    if len(addresses) > 10_000:
        raise ValueError(
            f"Census batch API accepts max 10,000 addresses, got {len(addresses)}. "
            "Use geocode_batch_chunked() for larger sets."
        )

    if not addresses:
        return []

    cg = _get_geocoder(vintage)
    batch_ids = _assign_batch_ids([addr.get("id", "") for addr in addresses])
    inputs = {batch_ids[i]: addr for i, addr in enumerate(addresses)}

    # Build CSV for batch submission
    csv_buffer = io.StringIO()
    writer = csv.writer(csv_buffer)
    for batch_id, addr in inputs.items():
        writer.writerow([
            batch_id,
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
        raise CensusGeocodeError(
            f"Census batch geocode failed for {len(addresses)} addresses: {e}"
        ) from e
    finally:
        os.unlink(csv_path)

    # Parse batch results.
    #
    # censusgeocode v0.5+ returns dicts with these keys (after its own
    # internal parsing):
    #   id, address, match (bool), matchtype, parsed (matched address),
    #   tigerlineid, side, statefp, countyfp, tract, block, lat (float),
    #   lon (float)
    if not isinstance(result, list):
        raise CensusGeocodeError("Census batch returned a non-list response")
    results_by_id = {}
    for row in result:
        if not isinstance(row, dict):
            raise CensusGeocodeError("Census batch returned a non-dict row")
        row_id = str(row.get("id", ""))
        if row_id not in inputs or row_id in results_by_id:
            raise CensusGeocodeError(f"Census batch returned unknown or duplicate input_id {row_id!r}")
        matched = bool(row.get("match", False))
        if matched:
            parsed = CensusGeocodeResult(
                matched=True,
                input_id=row_id,
                input_address=row.get("address", ""),
                matched_address=row.get("parsed", ""),
                lat=_safe_float(row.get("lat")),
                lon=_safe_float(row.get("lon")),
                state_fips=row.get("statefp", "") or "",
                county_fips=row.get("countyfp", "") or "",
                tract=row.get("tract", "") or "",
                block=row.get("block", "") or "",
                match_type=row.get("matchtype", "") or "",
                tiger_line_id=row.get("tigerlineid", "") or "",
                side=row.get("side", "") or "",
            )
        else:
            parsed = CensusGeocodeResult(
                input_id=row_id,
                input_address=row.get("address", ""),
            )
        results_by_id[row_id] = parsed

    # Return in input order
    output = []
    for batch_id, addr in inputs.items():
        if batch_id in results_by_id:
            parsed = results_by_id[batch_id]
            parsed.input_id = addr.get("id", "")
            output.append(parsed)
        else:
            output.append(CensusGeocodeResult(
                input_id=addr.get("id", ""),
                match_type="Error",
                input_address=(
                    f"{addr.get('street', '')}, {addr.get('city', '')}, "
                    f"{addr.get('state', '')} {addr.get('zipcode', '')}"
                ),
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
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
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


def geocode_results_to_dataframe(
    results: list[CensusGeocodeResult],
) -> "pd.DataFrame":
    """Convert a list of CensusGeocodeResult to a pandas DataFrame.

    Extracts all dataclass fields and computed GEOID properties into a
    flat DataFrame with standard column names. This eliminates the
    per-field list-comprehension boilerplate that every caller of
    :func:`geocode_batch` otherwise has to write.

    Args:
        results: List of :class:`CensusGeocodeResult` objects, typically
            returned by :func:`geocode_batch` or :func:`geocode_batch_chunked`.

    Returns:
        DataFrame with columns: ``input_id``, ``input_address``, ``matched``,
        ``match_type``, ``matched_address``, ``latitude``, ``longitude``,
        ``state_geoid``, ``county_geoid``, ``tract_geoid``, ``block_geoid``,
        ``block_group_geoid``, ``state_fips``, ``county_fips``, ``tract``,
        ``block``, ``side``, ``tiger_line_id``.
        For unmatched rows, latitude/longitude are ``None`` and GEOID
        columns are empty strings.

    Raises:
        TypeError: If *results* is not a list.

    Example::

        results = geocode_batch(addresses)
        df = geocode_results_to_dataframe(results)
        # df now has tract_geoid, block_geoid, lat/lon, etc.
    """
    import pandas as pd

    if not isinstance(results, list):
        raise TypeError(
            f"results must be a list of CensusGeocodeResult, got {type(results).__name__}"
        )

    _COLUMNS = [
        "input_id",
        "input_address",
        "matched",
        "match_type",
        "matched_address",
        "latitude",
        "longitude",
        "state_geoid",
        "county_geoid",
        "tract_geoid",
        "block_geoid",
        "block_group_geoid",
        "state_fips",
        "county_fips",
        "tract",
        "block",
        "side",
        "tiger_line_id",
    ]

    if not results:
        return pd.DataFrame(columns=_COLUMNS)

    rows = []
    for r in results:
        rows.append(
            {
                "input_id": r.input_id,
                "input_address": r.input_address,
                "matched": r.matched,
                "match_type": r.match_type,
                "matched_address": r.matched_address,
                "latitude": r.lat,
                "longitude": r.lon,
                "state_geoid": r.state_geoid,
                "county_geoid": r.county_geoid,
                "tract_geoid": r.tract_geoid,
                "block_geoid": r.block_geoid,
                "block_group_geoid": r.block_group_geoid,
                "state_fips": r.state_fips,
                "county_fips": r.county_fips,
                "tract": r.tract,
                "block": r.block,
                "side": r.side,
                "tiger_line_id": r.tiger_line_id,
            }
        )

    return pd.DataFrame(rows, columns=_COLUMNS)

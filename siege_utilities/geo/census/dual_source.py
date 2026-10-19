"""Tabular Census retrieval with explicit fallback and provenance.

Compose ``DualSourceCensusClient(ApiSource(api), secondary, policy)`` with
sources accepting the keyword arguments of :meth:`CensusAPI.fetch_data`.
Every success returns the source's unchanged DataFrame and provenance;
failures raise. ``BulkFileSource`` reads ACS table-based Summary Files.
"""

import asyncio
from concurrent.futures import ThreadPoolExecutor
import csv
from dataclasses import dataclass, replace
import hashlib
import logging
import math
from pathlib import Path
import re
from tempfile import NamedTemporaryFile, TemporaryDirectory
from typing import Any, BinaryIO, Protocol

import httpx
import numpy as np
import pandas as pd
import requests
from requests.exceptions import Timeout

from siege_utilities.geo.census_api_client import (
    CensusAPIError,
    CensusRateLimitError,
)
from siege_utilities.files.operations import atomic_write_path
from .api import CensusAPI
from .dataset_selector import DatasetSelector
from .variable_registry import VariableRegistry

__all__ = [
    "Provenance",
    "CensusDataSource",
    "ApiSource",
    "BulkFileSource",
    "api_to_summary_variable",
    "summary_to_api_variable",
    "AlternationPolicy",
    "DualSourceCensusClient",
]

log = logging.getLogger(__name__)

SUMMARY_FILE_BASE_URL = "https://www2.census.gov/programs-surveys/acs/summary_file"
_SUMMARY_LEVELS = {
    "nation": ("010", 0),
    "state": ("040", 2),
    "county": ("050", 5),
    "tract": ("140", 11),
    "block_group": ("150", 12),
    "place": ("160", 7),
}
_SENTINELS = frozenset(-int(str(digit) * 9) for digit in range(1, 10))
_SENTINEL_STRINGS = frozenset(str(value) for value in _SENTINELS)


def api_to_summary_variable(variable: str) -> str:
    """Translate an ACS detailed-table estimate/MOE code; raise on other codes."""
    match = re.fullmatch(r"([BC][0-9]{5}[A-Z]*)_([0-9]{3})([EM])", variable)
    if match is None:
        raise ValueError(f"Unsupported ACS estimate/MOE variable: {variable!r}")
    table, line, measure = match.groups()
    return f"{table}_{measure}{line}"


def summary_to_api_variable(variable: str) -> str:
    """Translate a Summary File estimate/MOE column; raise on other columns."""
    match = re.fullmatch(r"([BC][0-9]{5}[A-Z]*)_([EM])([0-9]{3})", variable)
    if match is None:
        raise ValueError(f"Unsupported Summary File estimate/MOE column: {variable!r}")
    table, measure, line = match.groups()
    return f"{table}_{line}{measure}"


@dataclass(frozen=True)
class Provenance:
    """Origin and retrieval history for one returned frame.

    ``source`` is ``"api"`` or ``"bulk"``. ``location`` lists every origin URL
    (with API secrets redacted), even when a cache supplies the data.
    ``cache_hit`` is True if any input was cached; ``cache_paths`` identifies
    those inputs (filesystem paths or Django cache keys). ``url_or_path``
    retains the first served URL/path for callers using the v4.0.0 field.
    ``attempts`` counts source-level
    fetch calls for this request, including failed calls across both sources;
    transport retries and cache access inside a source are not counted.
    ``degraded`` indicates that the secondary source served the request.
    """

    source: str
    url_or_path: str | None
    attempts: int
    degraded: bool
    location: tuple[str, ...] = ()
    cache_hit: bool = False
    cache_paths: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.location and self.url_or_path is not None:
            object.__setattr__(self, "location", (self.url_or_path,))


class CensusDataSource(Protocol):
    """A tabular source accepting CensusAPI.fetch_data keyword arguments."""

    name: str

    def fetch(self, **request: Any) -> tuple[pd.DataFrame, Provenance]:
        """Return a frame and its provenance, or raise a retrieval error."""
        ...


class ApiSource:
    """Adapt an injected CensusAPI without adding transport retries."""

    name: str = "api"

    def __init__(self, api: CensusAPI) -> None:
        self.api = api

    def fetch(self, **request: Any) -> tuple[pd.DataFrame, Provenance]:
        """Forward the request and report one source call, or raise its error.

        CensusAPI wraps exhausted transport timeouts in CensusAPIError.
        Expose that Timeout cause so the default fallback policy recognizes
        it; other API errors propagate unchanged. CensusAPI attaches retrieval
        metadata to the returned frame, keeping concurrent requests separate.
        """
        log.debug("Fetching Census tabular data through the API source")
        try:
            frame = self.api.fetch_data(**request)
        except CensusAPIError as error:
            if isinstance(error.__cause__, Timeout):
                raise error.__cause__ from None
            raise
        metadata = frame.attrs.get("census_source", {})
        locations = tuple(metadata.get("location", ()))
        cache_paths = tuple(metadata.get("cache_paths", ()))
        served = cache_paths or locations
        return frame, Provenance(
            source="api", url_or_path=served[0] if served else None,
            attempts=1, degraded=False, location=locations,
            cache_hit=metadata.get("cache_hit", False), cache_paths=cache_paths,
        )


class BulkFileSource:
    """Read ACS detailed tables from the table-based Summary File service.

    Downloads are streamed to ``cache_dir`` and reused by (year, period,
    table), with no expiry. Each cache reuse verifies a SHA-256 sidecar;
    missing/mismatched checksums trigger a fresh download. This detects local
    corruption, not changes on the server. Delete cached files to refresh them.
    If omitted, a source-owned temporary directory lasts for this instance.
    ``timeout`` bounds individual HTTP operations; ``total_timeout`` bounds a
    whole table download, including redirects and a stalled response body.
    Parsing retains only requested columns and matching geography rows.

    ``NAME`` is an object column of missing values: downloading the separate
    geography lookup (about 87 MB for ACS 5-year) is deliberately deferred.
    Estimates, MOEs and FIPS GEOIDs use API column names and numeric dtypes;
    ACS negative sentinels become NaN. Nation has an empty FIPS tail.
    HTTP, transport, filesystem and parsing errors propagate.
    """

    name: str = "bulk"

    def __init__(
        self,
        cache_dir: str | Path | None = None,
        *,
        timeout: float = 15,
        total_timeout: float = 300,
        chunksize: int = 50_000,
        registry: VariableRegistry | None = None,
    ) -> None:
        if not math.isfinite(timeout) or timeout <= 0:
            raise ValueError("timeout must be finite and positive")
        if not math.isfinite(total_timeout) or total_timeout <= 0:
            raise ValueError("total_timeout must be finite and positive")
        if isinstance(chunksize, bool) or not isinstance(chunksize, int) or chunksize < 1:
            raise ValueError("chunksize must be a positive integer")
        self.timeout = timeout
        self.total_timeout = total_timeout
        self.chunksize = chunksize
        self._registry = registry if registry is not None else VariableRegistry()
        self._temporary_cache = (
            TemporaryDirectory(prefix="census-summary-") if cache_dir is None else None
        )
        self.cache_dir = Path(
            self._temporary_cache.name if self._temporary_cache is not None else cache_dir
        )

    def fetch(
        self,
        variables: str | list[str],
        year: int,
        dataset: str = "acs5",
        geography: str = "county",
        state_fips: str | None = None,
        county_fips: str | None = None,
        include_moe: bool = True,
    ) -> tuple[pd.DataFrame, Provenance]:
        """Fetch numeric ACS estimates/MOEs, or raise for invalid/unavailable data.

        Accept the same request keywords and defaults as CensusAPI.fetch_data.
        Only ``acs1``/``acs5`` and nation/state/county/tract/block_group/place
        are supported. County filters apply only to counties, tracts and
        block groups. Tables are joined by GEOID, never row position.
        """
        if dataset not in ("acs1", "acs5"):
            raise ValueError(f"Bulk Summary Files support acs1/acs5, not {dataset!r}")
        if isinstance(year, bool) or not isinstance(year, int) or not 1000 <= year <= 9999:
            raise ValueError("year must be a four-digit integer")
        if geography != "nation":
            geography = DatasetSelector.validate_geography(geography, state_fips, county_fips)
        if geography not in _SUMMARY_LEVELS:
            raise ValueError(f"Unsupported Summary File geography: {geography!r}")
        if geography == "nation" and (state_fips or county_fips):
            raise ValueError("Nation geography does not accept state/county filters")
        if state_fips:
            state_fips = DatasetSelector.normalize_state(state_fips)
        if county_fips:
            if geography not in ("county", "tract", "block_group"):
                raise ValueError("County filters require county, tract or block_group geography")
            if county_fips != "*" and not re.fullmatch(r"[0-9]{3}", county_fips):
                raise ValueError("county_fips must contain three digits or '*'")

        concrete = self._registry.resolve_variables(variables)
        if include_moe:
            concrete = self._registry.add_moe_variables(concrete)
        concrete = list(dict.fromkeys(concrete))
        if not concrete:
            raise ValueError("At least one ACS estimate/MOE variable is required")
        tables: dict[str, list[str]] = {}
        for variable in concrete:
            column = api_to_summary_variable(variable)
            tables.setdefault(variable.split("_", 1)[0], []).append(column)

        period = int(dataset[-1])
        frames = []
        urls = []
        served = []
        cache_paths = []
        for table, columns in tables.items():
            filename = f"acsdt{period}y{year}-{table.lower()}.dat"
            url = f"{SUMMARY_FILE_BASE_URL}/{year}/table-based-SF/data/{period}YRData/{filename}"
            urls.append(url)
            path, cache_hit = self._download(url, filename)
            served.append(str(path) if cache_hit else url)
            if cache_hit:
                cache_paths.append(str(path))
            frames.append(self._read_table(path, columns, geography, state_fips, county_fips))

        frame = pd.concat(frames, axis=1).reset_index()
        for variable in concrete:
            raw = frame[variable]
            # Known ACS missing-value sentinels become NaN. Any other
            # non-numeric token -- garbage, or an empty cell from a truncated
            # record -- means a corrupt or format-drifted file and must raise
            # rather than silently coerce to NaN (SU-1: errors are not data).
            is_sentinel = raw.isin(_SENTINEL_STRINGS)
            # An empty/whitespace cell is a truncated or corrupt record, not a
            # value; pd.to_numeric would silently coerce it to NaN, so reject it
            # explicitly before the strict numeric parse.
            empty = (~is_sentinel) & raw.astype(str).str.strip().eq("")
            if empty.any():
                raise ValueError(
                    f"Empty {variable} cell in Summary File (truncated or corrupt record)"
                )
            parsed = pd.to_numeric(raw.where(~is_sentinel), errors="raise")
            # pd.to_numeric accepts "inf"/"-Infinity"/"nan" as non-finite floats.
            # These are neither finite ACS values nor masked sentinels, so a file
            # carrying them is corrupt and must raise (SU-1), not surface Inf/NaN.
            nonfinite = (~is_sentinel) & ~np.isfinite(parsed)
            if nonfinite.any():
                raise ValueError(
                    f"Non-finite {variable} value in Summary File (corrupt record)"
                )
            frame[variable] = parsed
        frame.insert(1, "NAME", None)
        frame = frame[["GEOID", "NAME", *concrete]]
        log.info("Read %s %s rows from %s Summary File tables", len(frame), geography, len(tables))
        return frame, Provenance(
            "bulk", served[0], 1, False, location=tuple(urls),
            cache_hit=bool(cache_paths), cache_paths=tuple(cache_paths),
        )

    def _download(self, url: str, filename: str) -> tuple[Path, bool]:
        path = self.cache_dir / filename
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        checksum_path = path.with_suffix(path.suffix + ".sha256")
        try:
            expected = checksum_path.read_text(encoding="ascii").strip()
            with path.open("rb") as cached:
                actual = hashlib.file_digest(cached, "sha256").hexdigest()
            if actual == expected:
                log.debug("Using verified cached Summary File %s", path)
                return path, True
            log.warning("Summary File checksum mismatch; downloading %s again", path)
        except (FileNotFoundError, UnicodeError):
            log.debug("Summary File cache/checksum missing or unreadable for %s", path)
        log.info("Downloading Summary File %s", url)
        with NamedTemporaryFile(dir=self.cache_dir, suffix=".part", delete=False) as output:
            temporary_path = Path(output.name)
            try:
                # Own a separate event loop so this synchronous API also works
                # inside notebooks/async applications. Cancellation interrupts
                # a pending network read, not just the gaps between chunks.
                with ThreadPoolExecutor(max_workers=1) as executor:
                    checksum = executor.submit(
                        asyncio.run, self._stream_download(url, output),
                    ).result(timeout=self.total_timeout + self.timeout)
                output.close()
                temporary_path.replace(path)
                with atomic_write_path(checksum_path) as temporary_checksum:
                    temporary_checksum.write_text(checksum + "\n", encoding="ascii")
            finally:
                temporary_path.unlink(missing_ok=True)
        log.info("Cached Summary File %s", path)
        return path, False

    async def _stream_download(self, url: str, output: BinaryIO) -> str:
        """Stream one table under a cancellable wall-clock deadline."""
        checksum = hashlib.sha256()
        size = 0
        try:
            async with asyncio.timeout(self.total_timeout):
                async with httpx.AsyncClient(
                    timeout=self.timeout, follow_redirects=True,
                    headers={"Accept-Encoding": "identity"},
                ) as client:
                    async with client.stream("GET", url) as response:
                        response.raise_for_status()
                        async for chunk in response.aiter_bytes(1024 * 1024):
                            output.write(chunk)
                            checksum.update(chunk)
                            size += len(chunk)
                            await asyncio.sleep(0)
                        length = response.headers.get("content-length")
                        if length is not None and not response.headers.get("content-encoding"):
                            if size != int(length):
                                raise OSError(f"Incomplete Summary File {url}: expected {length} bytes, got {size}")
        except TimeoutError:
            raise Timeout(f"Summary File total download timeout after {self.total_timeout}s") from None
        except httpx.TimeoutException as error:
            raise Timeout(str(error)) from None
        except httpx.HTTPStatusError as error:
            raise requests.HTTPError(str(error)) from None
        except httpx.RequestError as error:
            raise requests.ConnectionError(str(error)) from None
        return checksum.hexdigest()

    def _read_table(
        self,
        path: Path,
        columns: list[str],
        geography: str,
        state_fips: str | None,
        county_fips: str | None,
    ) -> pd.DataFrame:
        summary_level, fips_length = _SUMMARY_LEVELS[geography]
        # The Census Summary File is fixed-width per table: every data record
        # carries exactly as many pipe-delimited fields as the header. pandas'
        # usecols projection silently drops surplus fields and the python engine
        # silently shifts them, so a corrupt or truncated record would otherwise
        # parse as a successful (misaligned) result. Validate record width up
        # front against the file's own header and reject any drift.
        #
        # The validation must see the same record boundaries pandas' C parser
        # does. pandas treats a bare embedded '\r' as a record terminator and
        # truncates a cell at an embedded NUL, so either byte inside a logical
        # line splits or shortens the record behind this check. Reject both
        # outright (CRLF line endings are stripped first and remain allowed).
        def _record_body(raw: bytes) -> bytes:
            if raw.endswith(b"\r\n"):
                return raw[:-2]
            if raw.endswith(b"\n"):
                return raw[:-1]
            return raw

        with path.open("rb") as handle:
            header = handle.readline()
            if not header:
                raise ValueError(f"Empty Summary File {path.name}")
            header_body = _record_body(header)
            # The header is validated on the same footing as data rows: a CR or
            # NUL in the header would let pandas split or truncate it behind this
            # check, shifting every downstream column.
            if b"\x00" in header_body or b"\r" in header_body:
                raise ValueError(
                    f"Malformed header in Summary File {path.name}: "
                    f"embedded control character"
                )
            # Duplicate column names would be silently de-duplicated by pandas
            # (renamed `name.1`), so a requested column could resolve to the
            # wrong data. Reject duplicate header fields up front. pandas strips
            # a leading UTF-8 BOM before de-duplicating, so strip it here too or
            # a BOM-masked duplicate first column would slip past this check.
            header_fields = header_body.removeprefix(b"\xef\xbb\xbf").split(b"|")
            if len(header_fields) != len(set(header_fields)):
                raise ValueError(
                    f"Duplicate column name in Summary File header {path.name}"
                )
            expected = header_body.count(b"|")
            for lineno, line in enumerate(handle, start=2):
                body = _record_body(line)
                if not body.strip():
                    continue
                if b"\x00" in body or b"\r" in body:
                    raise ValueError(
                        f"Malformed record at line {lineno} in Summary File "
                        f"{path.name}: embedded control character"
                    )
                if body.count(b"|") != expected:
                    raise ValueError(
                        f"Malformed record at line {lineno} in Summary File "
                        f"{path.name}: expected {expected + 1} fields"
                    )
        selected = []
        with pd.read_csv(
            path, sep="|", usecols=["GEO_ID", *columns], dtype=str,
            keep_default_na=False, chunksize=self.chunksize,
            on_bad_lines="error",
            # The Summary File is unquoted; disabling quote handling keeps
            # pandas' field tokenization identical to the raw pipe-count
            # validation above, so a stray '"' cannot absorb a delimiter.
            quoting=csv.QUOTE_NONE,
        ) as chunks:
            for chunk in chunks:
                geo_ids = chunk["GEO_ID"]
                fips = geo_ids.str.slice(9)
                # Geographic components (e.g. 04000A0US) are not whole states/counties.
                matches = (
                    geo_ids.str.slice(0, 3).eq(summary_level)
                    & geo_ids.str.slice(3, 9).eq("0000US")
                    & fips.str.fullmatch(rf"[0-9]{{{fips_length}}}")
                )
                if state_fips:
                    matches &= fips.str.slice(0, 2).eq(state_fips)
                if county_fips and county_fips != "*":
                    matches &= fips.str.slice(2, 5).eq(county_fips)
                if matches.any():
                    rows = chunk.loc[matches, columns].copy()
                    rows.index = pd.Index(fips.loc[matches], name="GEOID")
                    selected.append(rows)
        if not selected:
            raise CensusAPIError(
                f"No {geography} rows for state={state_fips!r}, county={county_fips!r} "
                f"in Summary File {path.name}"
            )
        frame = pd.concat(selected)
        if not frame.index.is_unique:
            raise ValueError(f"Duplicate GEOIDs in Summary File {path.name}")
        return frame.rename(columns={column: summary_to_api_variable(column) for column in columns})


@dataclass(frozen=True)
class AlternationPolicy:
    """Pure configuration for a bounded primary-then-secondary attempt order.

    ``max_api_attempts`` is a positive source-call budget for the primary.
    Only ``fallback_on`` errors consume that retry budget; other errors
    propagate immediately. An empty tuple disables retries and fallback.
    ``alternate_under_sustained_pressure`` defaults to False and is reserved
    for a future cross-request scheduling policy. This framework does not
    track pressure across requests; each fetch starts with the primary.
    """

    max_api_attempts: int = 3
    fallback_on: tuple[type[Exception], ...] = (CensusRateLimitError, Timeout)
    alternate_under_sustained_pressure: bool = False

    def __post_init__(self) -> None:
        if (
            isinstance(self.max_api_attempts, bool)
            or not isinstance(self.max_api_attempts, int)
            or self.max_api_attempts < 1
        ):
            raise ValueError("max_api_attempts must be a positive integer")


class DualSourceCensusClient:
    """Retry the primary on configured errors, then try the secondary once.

    The last retrieval error propagates if no source succeeds. Each return
    includes provenance with this request's total source-call count.
    Source frames, source names, and locations are preserved.
    """

    def __init__(
        self,
        primary: CensusDataSource,
        secondary: CensusDataSource,
        policy: AlternationPolicy | None = None,
    ) -> None:
        self.primary = primary
        self.secondary = secondary
        self.policy = policy if policy is not None else AlternationPolicy()

    def fetch(self, **request: Any) -> tuple[pd.DataFrame, Provenance]:
        """Return an unchanged source frame and provenance, or raise.

        Forward the same CensusAPI.fetch_data keyword arguments to each
        attempted source. Secondary errors propagate without retrying.
        """
        attempt = 0
        while True:
            attempt += 1
            log.debug(
                "Fetching Census data from %s (attempt %s/%s)",
                self.primary.name, attempt, self.policy.max_api_attempts,
            )
            try:
                frame, provenance = self.primary.fetch(**request)
            except self.policy.fallback_on as error:
                log.warning(
                    "Census source %s attempt %s/%s failed (%s)",
                    self.primary.name, attempt, self.policy.max_api_attempts,
                    type(error).__name__,
                )
                if attempt == self.policy.max_api_attempts:
                    log.warning(
                        "Falling back to Census source %s",
                        self.secondary.name,
                    )
                    frame, provenance = self.secondary.fetch(**request)
                    return frame, replace(
                        provenance, attempts=attempt + 1, degraded=True,
                    )
            else:
                return frame, replace(provenance, attempts=attempt)

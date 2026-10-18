"""BLS Quarterly Census of Employment and Wages — open data downloader + parser.

BLS publishes QCEW open data files (no API key needed) at data.bls.gov.
Each quarter ships as a CSV inside a zip. This module downloads,
unzips, caches, and filters into a DataFrame retaining BLS source columns
and flagging suppressed observations.

Lift origin: this module was first written in socialwarehouse and
graduated to siege_utilities per the SU-first rule (SU#533).
Downstream consumers should `from siege_utilities.economic.bls import QCEWFiles`.

Phase 1 scope: files-only path (no BLS API key required). Phase 2
will add an `APIClient` that uses the keyed BLS API for incremental
loads.
"""

from __future__ import annotations

import logging
import zipfile
from pathlib import Path
from typing import Literal, Optional

import pandas as pd
import requests

from siege_utilities.files.operations import atomic_write_path


logger = logging.getLogger(__name__)

__all__ = [
    "DEFAULT_CACHE_DIR",
    "QCEW_FILE_URL",
    "QCEWFiles",
]


# QCEW open-data URL pattern.
# Example: https://data.bls.gov/cew/data/files/2024/csv/2024_qtrly_singlefile.zip
QCEW_FILE_URL = "https://data.bls.gov/cew/data/files/{year}/csv/{year}_qtrly_singlefile.zip"

# Default cache location.
DEFAULT_CACHE_DIR = Path.home() / ".siege_utilities" / "cache" / "qcew"

# The 20 NAICS sectors, excluding QCEW's total (10), supersectors (101x/
# 102x), and unclassified (99). Manufacturing, retail, and transportation
# are published as ranges, not individual two-digit codes.
# https://www.bls.gov/cew/classifications/industry/industry-titles.htm
_NAICS_SECTOR_CODES = frozenset({
    "11", "21", "22", "23", "31-33", "42", "44-45", "48-49", "51", "52",
    "53", "54", "55", "56", "61", "62", "71", "72", "81", "92",
})

# BLS agglvl_code combines geography with industry detail: base + 4 is
# sector level, and base + 5 through 8 are NAICS depths 3 through 6.
# Excludes the separate national/state establishment-size aggregations.
# https://www.bls.gov/cew/classifications/aggregation/agg-level-titles.htm
_AREA_AGGREGATION_BASES = {"national": 10, "msa": 40, "state": 50, "county": 70}


class QCEWFiles:
    """Thin wrapper around BLS QCEW open-data files.

    Network-only on the first download for a `(year)` tuple; cached on
    disk thereafter. `parse()` filters by time, geography, ownership, and
    NAICS depth without re-hitting the network. By default it returns
    private-sector, statewide NAICS sectors with suppression flags.

    Example:
        files = QCEWFiles()
        df = files.load(year=2024, quarter=3, state_fips="06", naics_depth=2)
    """

    _MAX_DOWNLOAD_BYTES = 512 * 1024 * 1024  # 512 MB cap
    _CHUNK_SIZE = 64 * 1024

    def __init__(self, cache_dir: Optional[Path] = None, timeout: int = 120):
        self.cache_dir = Path(cache_dir) if cache_dir else DEFAULT_CACHE_DIR
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.timeout = timeout

    def _stream_download_to_file(self, url: str, dest: Path) -> None:
        """Stream an HTTP response directly to disk with a size cap."""
        downloaded = 0
        with requests.get(url, stream=True, timeout=self.timeout) as resp:
            resp.raise_for_status()
            with atomic_write_path(dest) as tmp:
                with open(tmp, 'wb') as f:
                    for chunk in resp.iter_content(chunk_size=self._CHUNK_SIZE):
                        downloaded += len(chunk)
                        if downloaded > self._MAX_DOWNLOAD_BYTES:
                            raise ValueError(
                                f"Download from {url} exceeds "
                                f"{self._MAX_DOWNLOAD_BYTES / 1024 / 1024:.0f} MB limit"
                            )
                        f.write(chunk)

    def download(self, year: int) -> Path:
        """Download (or return cached) the year's QCEW zip; return CSV path."""
        zip_path = self.cache_dir / f"{year}_qtrly_singlefile.zip"
        csv_path = self.cache_dir / f"{year}.qcew.csv"

        if csv_path.exists():
            logger.debug("QCEW year %s already cached at %s", year, csv_path)
            return csv_path

        url = QCEW_FILE_URL.format(year=year)
        logger.info("Downloading QCEW %s from %s", year, url)
        self._stream_download_to_file(url, zip_path)

        with zipfile.ZipFile(zip_path) as zf:
            csv_name = next(
                (n for n in zf.namelist() if n.endswith(".csv")),
                None,
            )
            if not csv_name:
                raise ValueError(f"No CSV found inside {zip_path}")
            with atomic_write_path(csv_path) as tmp:
                with zf.open(csv_name) as src, open(tmp, "wb") as dst:
                    dst.write(src.read())
        zip_path.unlink(missing_ok=True)
        return csv_path

    def parse(
        self,
        csv_path: Path,
        *,
        year: int,
        quarter: int,
        state_fips: Optional[str] = None,
        naics_depth: int = 2,
        own_code: int = 5,
        area_level: Literal["state", "county", "national", "msa"] = "state",
    ) -> pd.DataFrame:
        """Filter a QCEW quarterly CSV, preserving its source columns.

        Filters:
          - `year`: the BLS `year` column matches, when present.
          - `quarter`: the BLS `qtr` column matches; 1-4.
          - `state_fips`: optional two-digit state FIPS. At state level,
            select exactly its statewide area (e.g. "06000"); at county
            level, select counties with that prefix. Not supported for
            national/MSA data, whose area codes are not state FIPS.
          - `naics_depth`: 2-6; defaults to the 20 NAICS sectors, including
            "31-33", "44-45", and "48-49", excluding total "10" and
            unclassified "99". Depths 3-6 select numeric industry codes.
            Domain and supersector aggregates are always excluded.
          - `own_code`: one BLS ownership code; defaults to 5 (private).
            Codes 1, 2, and 3 select federal, state, and local government.
            Ownership totals are not synthesized; combinations absent
            from the source yield an empty result.
          - `area_level`: "state" (default), "county", "national", or "msa".
            Select exactly one `agglvl_code` for this area and NAICS depth:
            at depth 2 these are 54, 74, 14, and 44, respectively. Separate
            establishment-size aggregations are excluded.

        Returns every input column with its original name and values,
        plus boolean `is_suppressed`, true when `disclosure_code` is "N".
        Suppressed employment/wage zeros remain source sentinels and must
        not be treated as measured zeros; exclude flagged rows before
        calculations. `area_fips` and `industry_code` are read as strings
        to retain leading zeros. The result has a fresh integer index.
        Requires the BLS `own_code`, `agglvl_code`, and `disclosure_code`
        columns in addition to the time, area, and industry columns.

        BLS code references:
        https://www.bls.gov/cew/classifications/industry/industry-titles.htm
        https://www.bls.gov/cew/classifications/aggregation/agg-level-titles.htm
        """
        if not isinstance(naics_depth, int) or not 2 <= naics_depth <= 6:
            raise ValueError("naics_depth must be an integer from 2 through 6")
        if area_level not in _AREA_AGGREGATION_BASES:
            raise ValueError("area_level must be state, county, national, or msa")
        if state_fips is not None:
            if len(state_fips) != 2 or not state_fips.isascii() or not state_fips.isdigit():
                raise ValueError("state_fips must be a two-digit state FIPS code")
            if area_level not in {"state", "county"}:
                raise ValueError("state_fips is only supported for state or county area_level")

        agglvl_code = _AREA_AGGREGATION_BASES[area_level] + naics_depth + 2
        df = pd.read_csv(csv_path, dtype={"area_fips": str, "industry_code": str})
        if "year" in df.columns:
            df = df[df["year"] == year]
        df = df[
            (df["qtr"] == quarter)
            & (df["own_code"] == own_code)
            & (df["agglvl_code"] == agglvl_code)
        ]
        if state_fips is not None:
            if area_level == "state":
                df = df[df["area_fips"] == f"{state_fips}000"]
            else:
                df = df[df["area_fips"].str.startswith(state_fips, na=False)]
        if naics_depth == 2:
            df = df[df["industry_code"].isin(_NAICS_SECTOR_CODES)]
        else:
            df = df[df["industry_code"].str.fullmatch(rf"[0-9]{{{naics_depth}}}", na=False)]
        df = df.reset_index(drop=True)
        df["is_suppressed"] = df["disclosure_code"].eq("N")
        return df

    def load(
        self,
        *,
        year: int,
        quarter: int,
        state_fips: Optional[str] = None,
        naics_depth: int = 2,
        own_code: int = 5,
        area_level: Literal["state", "county", "national", "msa"] = "state",
    ) -> pd.DataFrame:
        """Download and parse using the filters documented by `parse()`.

        Defaults to private ownership (`own_code=5`) and statewide NAICS
        sectors (`area_level="state"`, `naics_depth=2`, `agglvl_code=54`).
        Returns source columns plus the boolean `is_suppressed` flag.
        """
        csv_path = self.download(year)
        return self.parse(
            csv_path,
            year=year, quarter=quarter,
            state_fips=state_fips, naics_depth=naics_depth,
            own_code=own_code, area_level=area_level,
        )

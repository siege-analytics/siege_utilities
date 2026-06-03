"""IRS Statistics of Income — ZIP-code-level data downloader + parser.

The IRS publishes per-state individual income tax return statistics
grouped by ZIP code.  Files are published annually at
``irs.gov/pub/irs-soi/`` with no API key required.

Lift origin: this module was first written in socialwarehouse and
graduated to siege_utilities per the SU-first rule (SU#539).
Downstream consumers should ``from siege_utilities.economic.irs import IRSSOIFiles``.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import pandas as pd
import requests

logger = logging.getLogger(__name__)

__all__ = [
    "DEFAULT_CACHE_DIR",
    "IRSSOIFiles",
]

DEFAULT_CACHE_DIR = Path.home() / ".siege_utilities" / "cache" / "irs_soi"

_SOI_URL_PATTERN = (
    "https://www.irs.gov/pub/irs-soi/{tax_year}zpallagi{state_abbrev}.csv"
)


class IRSSOIFiles:
    """Thin wrapper around IRS SOI ZIP-code data files.

    Downloads per-state CSV files for a given tax year from
    ``irs.gov/pub/irs-soi/``, caches locally, and parses into a
    DataFrame.

    Example::

        files = IRSSOIFiles()
        df = files.load(tax_year=2020, state_abbrev="tx")
    """

    _MAX_DOWNLOAD_BYTES = 128 * 1024 * 1024  # 128 MB cap
    _CHUNK_SIZE = 64 * 1024

    def __init__(
        self,
        cache_dir: Optional[Path] = None,
        timeout: int = 60,
    ):
        self.cache_dir = Path(cache_dir) if cache_dir else DEFAULT_CACHE_DIR
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.timeout = timeout

    def url_for(self, tax_year: int, state_abbrev: str) -> str:
        """Build the download URL for a given tax year and state.

        Override this method if the IRS changes their URL conventions.

        Args:
            tax_year: The tax year (e.g. 2020).
            state_abbrev: Two-letter state abbreviation, lowercase.

        Returns:
            Full URL to the CSV file.
        """
        return _SOI_URL_PATTERN.format(
            tax_year=tax_year,
            state_abbrev=state_abbrev.lower(),
        )

    def _stream_download_to_file(self, url: str, dest: Path) -> None:
        """Stream an HTTP response directly to disk with a size cap."""
        downloaded = 0
        with requests.get(url, stream=True, timeout=self.timeout) as resp:
            resp.raise_for_status()
            with open(dest, "wb") as f:
                for chunk in resp.iter_content(chunk_size=self._CHUNK_SIZE):
                    downloaded += len(chunk)
                    if downloaded > self._MAX_DOWNLOAD_BYTES:
                        dest.unlink(missing_ok=True)
                        raise ValueError(
                            f"Download from {url} exceeds "
                            f"{self._MAX_DOWNLOAD_BYTES / 1024 / 1024:.0f} MB limit"
                        )
                    f.write(chunk)

    def download(self, tax_year: int, state_abbrev: str) -> Path:
        """Download (or return cached) a state's SOI CSV.

        Args:
            tax_year: Tax year to fetch.
            state_abbrev: Two-letter state abbreviation.

        Returns:
            Path to the local CSV file.
        """
        state_abbrev = state_abbrev.lower()
        csv_path = self.cache_dir / f"{tax_year}_{state_abbrev}_soi.csv"

        if csv_path.exists():
            logger.debug(
                "IRS SOI %s/%s already cached at %s",
                tax_year, state_abbrev, csv_path,
            )
            return csv_path

        url = self.url_for(tax_year, state_abbrev)
        logger.info("Downloading IRS SOI %s/%s from %s", tax_year, state_abbrev, url)
        self._stream_download_to_file(url, csv_path)
        return csv_path

    def parse(self, csv_path: Path) -> pd.DataFrame:
        """Parse a downloaded IRS SOI CSV into a DataFrame.

        The IRS SOI files use a ``ZIPCODE`` column (5-digit string) as
        the geographic key.  ``STATEFIPS`` and ``STATE`` identify the
        state.  ``agi_stub`` encodes the AGI bracket (1-6).

        Returns:
            DataFrame with string-typed ZIP and FIPS columns.
        """
        dtype = {"ZIPCODE": str, "STATEFIPS": str}
        df = pd.read_csv(csv_path, dtype=dtype)
        if "ZIPCODE" in df.columns:
            df["ZIPCODE"] = df["ZIPCODE"].str.zfill(5)
        if "STATEFIPS" in df.columns:
            df["STATEFIPS"] = df["STATEFIPS"].str.zfill(2)
        return df

    def load(self, tax_year: int, state_abbrev: str) -> pd.DataFrame:
        """Download + parse in one call.

        Args:
            tax_year: Tax year to fetch.
            state_abbrev: Two-letter state abbreviation.

        Returns:
            Parsed DataFrame of IRS SOI data for the state and year.
        """
        csv_path = self.download(tax_year, state_abbrev)
        return self.parse(csv_path)

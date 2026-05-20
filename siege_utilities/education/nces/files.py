"""NCES CCD + EDGE open data files — downloader + parser.

NCES publishes Common Core of Data (CCD) and Education Demographic and
Geographic Estimates (EDGE) as open data files (no API key). This
module covers downstream warehouse needs (e.g., socialwarehouse F):

- CCD Directory (LEA + per-school)
- CCD Nonfiscal Survey (enrollment + staff)
- CCD F-33 Finance Survey (revenues + expenditures)
- EDGE per-district demographic estimates

Lift origin: this module was first written in socialwarehouse and
graduated to siege_utilities per the SU-first rule (SU#534).
Downstream consumers should `from siege_utilities.education.nces import NCESFiles`.
"""

from __future__ import annotations

import io
import logging
import zipfile
from pathlib import Path
from typing import Optional

import pandas as pd
import requests


logger = logging.getLogger(__name__)

# Default cache location.
DEFAULT_CACHE_DIR = Path.home() / ".siege_utilities" / "cache" / "nces"

# NCES URL patterns. These URLs evolve per release; the helper accepts
# a `url_override` kwarg if NCES reshapes a file's pattern.
CCD_DIRECTORY_URL = (
    "https://nces.ed.gov/ccd/data/zip/ccd_lea_029_{end_2digit}_l_1a.zip"
)
CCD_NONFISCAL_URL = (
    "https://nces.ed.gov/ccd/data/zip/ccd_lea_052_{end_2digit}_l_1a.zip"
)
CCD_F33_URL = (
    "https://nces.ed.gov/ccd/data/zip/sdf{end_2digit}_1a.zip"
)
CCD_SCHOOL_DIRECTORY_URL = (
    "https://nces.ed.gov/ccd/data/zip/ccd_sch_029_{end_2digit}_l_1a.zip"
)
CCD_SCHOOL_NONFISCAL_URL = (
    "https://nces.ed.gov/ccd/data/zip/ccd_sch_052_{end_2digit}_l_1a.zip"
)
EDGE_DISTRICT_DEMOGRAPHICS_URL = (
    "https://nces.ed.gov/programs/edge/data/EDGE_ACS_{acs_endpoint}_DISTRICT.csv"
)


class NCESFiles:
    """Thin wrapper around NCES CCD + EDGE open data files.

    Loads (district directory + nonfiscal + finance) per school-year +
    (school directory + nonfiscal) per school-year + EDGE demographics
    per ACS endpoint. Cached on disk after first download.

    Example:
        files = NCESFiles()
        district = files.load_ccd_directory("2022-23")
        nonfiscal = files.load_ccd_nonfiscal("2022-23")
        finance = files.load_ccd_finance("2022-23")
        edge = files.load_edge_district_demographics("2018-22")
    """

    def __init__(self, cache_dir: Optional[Path] = None, timeout: int = 120):
        self.cache_dir = Path(cache_dir) if cache_dir else DEFAULT_CACHE_DIR
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.timeout = timeout

    @staticmethod
    def _parse_school_year(school_year: str) -> tuple[int, int]:
        """'2022-23' -> (2022, 2023); '2099-00' -> (2099, 2100).

        School years span two consecutive calendar years; the '-NN'
        suffix is decorative for the human reader. We just take the
        start year and add 1.
        """
        if "-" not in school_year:
            raise ValueError(f"school_year must be like '2022-23'; got {school_year!r}")
        start_str, _ = school_year.split("-", 1)
        start = int(start_str)
        return start, start + 1

    def _download_zip(self, url: str, cache_name: str) -> Path:
        """Download + cache one NCES zip; return CSV path inside cache_dir."""
        csv_path = self.cache_dir / f"{cache_name}.csv"
        if csv_path.exists():
            return csv_path
        logger.info("Downloading NCES file: %s", url)
        resp = requests.get(url, timeout=self.timeout)
        resp.raise_for_status()
        with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
            csv_name = next((n for n in zf.namelist() if n.endswith((".csv", ".txt"))), None)
            if not csv_name:
                raise ValueError(f"No CSV/TXT inside {url}")
            with zf.open(csv_name) as src, open(csv_path, "wb") as dst:
                dst.write(src.read())
        return csv_path

    # ── District-level CCD loaders ────────────────────────────────────

    def load_ccd_directory(self, school_year: str) -> pd.DataFrame:
        _, end = self._parse_school_year(school_year)
        url = CCD_DIRECTORY_URL.format(end_2digit=str(end)[-2:])
        path = self._download_zip(url, f"ccd_lea_directory_{school_year}")
        return pd.read_csv(path, dtype={"LEAID": str, "STATEFIPS": str}, low_memory=False)

    def load_ccd_nonfiscal(self, school_year: str) -> pd.DataFrame:
        _, end = self._parse_school_year(school_year)
        url = CCD_NONFISCAL_URL.format(end_2digit=str(end)[-2:])
        path = self._download_zip(url, f"ccd_lea_nonfiscal_{school_year}")
        return pd.read_csv(path, dtype={"LEAID": str}, low_memory=False)

    def load_ccd_finance(self, school_year: str) -> pd.DataFrame:
        _, end = self._parse_school_year(school_year)
        url = CCD_F33_URL.format(end_2digit=str(end)[-2:])
        path = self._download_zip(url, f"ccd_lea_finance_{school_year}")
        return pd.read_csv(path, dtype={"LEAID": str}, low_memory=False)

    # ── School-level CCD loaders ─────────────────────────────────────

    def load_ccd_school_directory(self, school_year: str) -> pd.DataFrame:
        _, end = self._parse_school_year(school_year)
        url = CCD_SCHOOL_DIRECTORY_URL.format(end_2digit=str(end)[-2:])
        path = self._download_zip(url, f"ccd_sch_directory_{school_year}")
        return pd.read_csv(
            path,
            dtype={"NCESSCH": str, "LEAID": str, "STATEFIPS": str},
            low_memory=False,
        )

    def load_ccd_school_nonfiscal(self, school_year: str) -> pd.DataFrame:
        _, end = self._parse_school_year(school_year)
        url = CCD_SCHOOL_NONFISCAL_URL.format(end_2digit=str(end)[-2:])
        path = self._download_zip(url, f"ccd_sch_nonfiscal_{school_year}")
        return pd.read_csv(path, dtype={"NCESSCH": str, "LEAID": str}, low_memory=False)

    # ── EDGE per-district demographics ───────────────────────────────

    def load_edge_district_demographics(self, acs_endpoint: str) -> pd.DataFrame:
        """Load EDGE per-school-district demographic estimates.

        `acs_endpoint` is the ACS 5-year endpoint range like "2018-22".
        Returns a DataFrame with LEAID + the EDGE demographic variables.
        Unlike CCD files, EDGE is a direct CSV (no zip).
        """
        url = EDGE_DISTRICT_DEMOGRAPHICS_URL.format(acs_endpoint=acs_endpoint)
        cache_name = f"edge_district_{acs_endpoint}"
        csv_path = self.cache_dir / f"{cache_name}.csv"
        if not csv_path.exists():
            logger.info("Downloading EDGE district demographics: %s", url)
            resp = requests.get(url, timeout=self.timeout)
            resp.raise_for_status()
            csv_path.write_bytes(resp.content)
        return pd.read_csv(
            csv_path,
            dtype={"LEAID": str, "STATEFP": str, "STATEFIPS": str},
            low_memory=False,
        )

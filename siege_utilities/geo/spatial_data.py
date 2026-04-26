"""
Modern spatial data sources for siege_utilities.
Provides clean, type-safe access to Census, Government, and OpenStreetMap data.
"""

import logging
import geopandas as gpd
from pathlib import Path

from siege_utilities.geo.crs import reproject_if_needed
from typing import Dict, Any, Optional, List, Union
import os
import time
import warnings as _warnings_mod
from datetime import datetime
import requests
from bs4 import BeautifulSoup
import re
import warnings

# Suppress SSL warnings when using verify=False
warnings.filterwarnings('ignore', message='Unverified HTTPS request')

# Import existing library functions
from ..files.remote import download_file, generate_local_path_from_url
from ..files.paths import unzip_file_to_directory, ensure_path_exists
from ..config.user_config import get_user_config, get_download_directory

# Import centralized constants
from ..config import (
    CENSUS_BASE_URL,
    CENSUS_CACHE_TIMEOUT,
    CENSUS_RETRY_ATTEMPTS,
    DEFAULT_CENSUS_YEAR,
    FIPS_TO_STATE,
    STATE_NAMES,
    normalize_state_identifier,
    get_fips_info,
    get_service_timeout
)

# Structured boundary diagnostics
from .boundary_result import (
    BoundaryFetchResult,
    BoundaryRetrievalError,
    BoundaryInputError,
    BoundaryDiscoveryError,
    BoundaryConfigurationError,
    BoundaryUrlValidationError,
    BoundaryDownloadError,
    BoundaryParseError,
)

# Get logger for this module
log = logging.getLogger(__name__)


class SpatialDataError(RuntimeError):
    """Raised when a non-boundary spatial data fetch fails unexpectedly.

    Used by GovernmentDataSource and OpenStreetMapDataSource, which load
    generic portal datasets and OSM Overpass results respectively. Boundary
    retrieval has its own exception hierarchy in boundary_result.py.

    Use the ``__cause__`` attribute (set via ``raise ... from e``) to inspect
    the underlying exception (HTTPError, JSONDecodeError, etc.).
    """

# Type aliases
FilePath = Union[str, Path]
GeoDataFrame = gpd.GeoDataFrame

# ---------------------------------------------------------------------------
# Congressional District number by TIGER year
# ---------------------------------------------------------------------------
# All values verified by direct URL probing against Census FTP (2026-04-26).
# cd117 (117th Congress) is entirely absent from TIGER — Census held on
# the pre-redistricting 116th boundaries for 2020 and 2021, then jumped
# directly to cd118 when per-state files appeared for 2022.
YEAR_TO_CONGRESS: Dict[int, int] = {
    2010: 111,
    2011: 112,
    2012: 112,  # 113th elected Nov 2012 but TIGER 2012 still uses seated 112th
    2013: 113,  # 113th seated Jan 2013; direct URL confirmed 200
    2014: 114,
    2015: 114,
    2016: 115,
    2017: 115,
    2018: 116,
    2019: 116,
    2020: 116,  # pre-redistricting hold; 117th elected but old districts kept
    2021: 116,  # still pre-redistricting; cd117 entirely absent from TIGER
    2022: 118,  # post-redistricting; per-state files only (national = 404)
    2023: 118,
    2024: 119,
    2025: 119,
    2026: 119,
}

# ---------------------------------------------------------------------------
# Boundary Type Catalog
# ---------------------------------------------------------------------------
# Reference data for Census TIGER/Line boundary types.
# Keys match the internal names returned by discover_boundary_types().
# Each entry: category (redistricting | general), Census abbreviation, human name.

BOUNDARY_TYPE_CATALOG = {
    # --- Redistricting & Electoral ---
    'state':        {'category': 'redistricting', 'abbrev': 'STATE',      'name': 'State Boundaries',                  'geometry_type': 'MultiPolygon'},
    'county':       {'category': 'redistricting', 'abbrev': 'COUNTY',     'name': 'County Boundaries',                 'geometry_type': 'MultiPolygon'},
    'cousub':       {'category': 'redistricting', 'abbrev': 'COUSUB',     'name': 'County Subdivisions (townships)',    'geometry_type': 'MultiPolygon'},
    'tract':        {'category': 'redistricting', 'abbrev': 'TRACT',      'name': 'Census Tracts',                     'geometry_type': 'MultiPolygon'},
    'block_group':  {'category': 'redistricting', 'abbrev': 'BG',         'name': 'Block Groups',                      'geometry_type': 'MultiPolygon'},
    'block':        {'category': 'redistricting', 'abbrev': 'TABBLOCK',   'name': 'Census Blocks (atomic unit)',        'geometry_type': 'MultiPolygon'},
    'tabblock20':   {'category': 'redistricting', 'abbrev': 'TABBLOCK20', 'name': 'Census Blocks (2020)',              'geometry_type': 'MultiPolygon'},
    'tabblock10':   {'category': 'redistricting', 'abbrev': 'TABBLOCK10', 'name': 'Census Blocks (2010)',              'geometry_type': 'MultiPolygon'},
    'place':        {'category': 'redistricting', 'abbrev': 'PLACE',      'name': 'Places (cities/towns)',              'geometry_type': 'MultiPolygon'},
    'cd':           {'category': 'redistricting', 'abbrev': 'CD',         'name': 'Congressional Districts',            'geometry_type': 'MultiPolygon'},
    'cd116':        {'category': 'redistricting', 'abbrev': 'CD116',      'name': 'Congressional Districts (116th)',    'geometry_type': 'MultiPolygon'},
    'cd118':        {'category': 'redistricting', 'abbrev': 'CD118',      'name': 'Congressional Districts (118th)',    'geometry_type': 'MultiPolygon'},
    'cd119':        {'category': 'redistricting', 'abbrev': 'CD119',      'name': 'Congressional Districts (119th)',    'geometry_type': 'MultiPolygon'},
    'sldu':         {'category': 'redistricting', 'abbrev': 'SLDU',       'name': 'State Legislative Upper (Senate)',   'geometry_type': 'MultiPolygon'},
    'sldl':         {'category': 'redistricting', 'abbrev': 'SLDL',       'name': 'State Legislative Lower (House)',    'geometry_type': 'MultiPolygon'},
    'vtd':          {'category': 'redistricting', 'abbrev': 'VTD',        'name': 'Voting Districts / Precincts',       'geometry_type': 'MultiPolygon'},
    'vtd20':        {'category': 'redistricting', 'abbrev': 'VTD20',      'name': 'Voting Districts (2020)',            'geometry_type': 'MultiPolygon'},
    'zcta':         {'category': 'redistricting', 'abbrev': 'ZCTA5',      'name': 'ZIP Code Tabulation Areas',          'geometry_type': 'MultiPolygon'},
    # --- General ---
    'cbsa':         {'category': 'general', 'abbrev': 'CBSA',        'name': 'Core-Based Statistical Areas',     'geometry_type': 'MultiPolygon'},
    'csa':          {'category': 'general', 'abbrev': 'CSA',         'name': 'Combined Statistical Areas',       'geometry_type': 'MultiPolygon'},
    'metdiv':       {'category': 'general', 'abbrev': 'METDIV',      'name': 'Metropolitan Divisions',           'geometry_type': 'MultiPolygon'},
    'micro':        {'category': 'general', 'abbrev': 'MICRO',       'name': 'Micropolitan Statistical Areas',   'geometry_type': 'MultiPolygon'},
    'necta':        {'category': 'general', 'abbrev': 'NECTA',       'name': 'New England City & Town Areas',    'geometry_type': 'MultiPolygon'},
    'nectadiv':     {'category': 'general', 'abbrev': 'NECTADIV',    'name': 'NECTA Divisions',                  'geometry_type': 'MultiPolygon'},
    'cnecta':       {'category': 'general', 'abbrev': 'CNECTA',      'name': 'Combined NECTAs',                  'geometry_type': 'MultiPolygon'},
    'aiannh':       {'category': 'general', 'abbrev': 'AIANNH',      'name': 'American Indian / Alaska Native Areas', 'geometry_type': 'MultiPolygon'},
    'aitsce':       {'category': 'general', 'abbrev': 'AITSCE',      'name': 'Tribal Subdivisions',              'geometry_type': 'MultiPolygon'},
    'ttract':       {'category': 'general', 'abbrev': 'TTRACT',      'name': 'Tribal Census Tracts',             'geometry_type': 'MultiPolygon'},
    'tbg':          {'category': 'general', 'abbrev': 'TBG',         'name': 'Tribal Block Groups',              'geometry_type': 'MultiPolygon'},
    'elsd':         {'category': 'general', 'abbrev': 'ELSD',        'name': 'Elementary School Districts',      'geometry_type': 'MultiPolygon'},
    'scsd':         {'category': 'general', 'abbrev': 'SCSD',        'name': 'Secondary School Districts',       'geometry_type': 'MultiPolygon'},
    'unsd':         {'category': 'general', 'abbrev': 'UNSD',        'name': 'Unified School Districts',         'geometry_type': 'MultiPolygon'},
    'address_features': {'category': 'general', 'abbrev': 'ADDRFEAT',    'name': 'Address Features',             'geometry_type': 'MultiLineString'},
    'linear_water': {'category': 'general', 'abbrev': 'LINEARWATER', 'name': 'Linear Water Features',            'geometry_type': 'MultiLineString'},
    'area_water':   {'category': 'general', 'abbrev': 'AREAWATER',   'name': 'Area Water Features',              'geometry_type': 'MultiPolygon'},
    'roads':        {'category': 'general', 'abbrev': 'ROADS',       'name': 'Roads',                            'geometry_type': 'MultiLineString'},
    'rails':        {'category': 'general', 'abbrev': 'RAILS',       'name': 'Railroads',                        'geometry_type': 'MultiLineString'},
    'edges':        {'category': 'general', 'abbrev': 'EDGES',       'name': 'All Edges (roads, hydro, etc.)',   'geometry_type': 'MultiLineString'},
    'anrc':         {'category': 'general', 'abbrev': 'ANRC',        'name': 'Alaska Native Regional Corps',     'geometry_type': 'MultiPolygon'},
    'concity':      {'category': 'general', 'abbrev': 'CONCITY',     'name': 'Consolidated Cities',              'geometry_type': 'MultiPolygon'},
    'submcd':       {'category': 'general', 'abbrev': 'SUBMCD',      'name': 'Sub-Minor Civil Divisions',        'geometry_type': 'MultiPolygon'},
    'uac':          {'category': 'general', 'abbrev': 'UAC',         'name': 'Urban Areas',                      'geometry_type': 'MultiPolygon'},
    'uac20':        {'category': 'general', 'abbrev': 'UAC20',       'name': 'Urban Areas (2020)',               'geometry_type': 'MultiPolygon'},
    'puma':         {'category': 'general', 'abbrev': 'PUMA',        'name': 'Public Use Microdata Areas',       'geometry_type': 'MultiPolygon'},
    'pointlm':      {'category': 'general', 'abbrev': 'POINTLM',    'name': 'Point Landmarks',                  'geometry_type': 'Point'},
    'arealm':       {'category': 'general', 'abbrev': 'AREALM',     'name': 'Area Landmarks',                   'geometry_type': 'MultiPolygon'},
}

# ---------------------------------------------------------------------------
# TIGER Redistricting (PL 94-171) URL constants
# ---------------------------------------------------------------------------
# VTD (Voting Tabulation District) boundaries for decennial census years are
# published in the PL 94-171 redistricting product, NOT in the standard annual
# TIGER release.  The standard TIGER{year}/ server has no VTD20/ directory.
#
# 2020 URL pattern:
#   TIGER2020PL/STATE/{FIPS}_{STATE_NAME_UPPER}/{FIPS}/tl_2020_{fips}_vtd20.zip
# 2010 URL pattern (same structure, different vintage):
#   TIGER2010PL/tabblock_vtd/{FIPS}_{STATE_NAME_UPPER}/{FIPS}/tl_2010_{fips}_vtd10.zip

TIGER_PL_BASE_URL = "https://www2.census.gov/geo/tiger"

# State names used in TIGER PL directory paths, uppercase with underscores.
# Territories that publish VTD data in PL files are included; others (GU, AS,
# VI, MP) do not appear in TIGER2020PL/STATE and are intentionally omitted.
_VTD_PL_STATE_NAMES: Dict[str, str] = {
    "01": "ALABAMA",               "02": "ALASKA",
    "04": "ARIZONA",               "05": "ARKANSAS",
    "06": "CALIFORNIA",            "08": "COLORADO",
    "09": "CONNECTICUT",           "10": "DELAWARE",
    "11": "DISTRICT_OF_COLUMBIA",  "12": "FLORIDA",
    "13": "GEORGIA",               "15": "HAWAII",
    "16": "IDAHO",                 "17": "ILLINOIS",
    "18": "INDIANA",               "19": "IOWA",
    "20": "KANSAS",                "21": "KENTUCKY",
    "22": "LOUISIANA",             "23": "MAINE",
    "24": "MARYLAND",              "25": "MASSACHUSETTS",
    "26": "MICHIGAN",              "27": "MINNESOTA",
    "28": "MISSISSIPPI",           "29": "MISSOURI",
    "30": "MONTANA",               "31": "NEBRASKA",
    "32": "NEVADA",                "33": "NEW_HAMPSHIRE",
    "34": "NEW_JERSEY",            "35": "NEW_MEXICO",
    "36": "NEW_YORK",              "37": "NORTH_CAROLINA",
    "38": "NORTH_DAKOTA",          "39": "OHIO",
    "40": "OKLAHOMA",              "41": "OREGON",
    "42": "PENNSYLVANIA",          "44": "RHODE_ISLAND",
    "45": "SOUTH_CAROLINA",        "46": "SOUTH_DAKOTA",
    "47": "TENNESSEE",             "48": "TEXAS",
    "49": "UTAH",                  "50": "VERMONT",
    "51": "VIRGINIA",              "53": "WASHINGTON",
    "54": "WEST_VIRGINIA",         "55": "WISCONSIN",
    "56": "WYOMING",               "72": "PUERTO_RICO",
}


# ---------------------------------------------------------------------------
# Census inventory: crawled directory map + disk-backed fallback
# ---------------------------------------------------------------------------

_DEFAULT_INVENTORY_PATH = Path.home() / ".cache" / "siege_utilities" / "census_inventory.json"
_TIGER_BASE = "https://www2.census.gov/geo/tiger/"
_GENZ_BASE = "https://www2.census.gov/geo/tiger/"   # GENZ lives under the same tree


def update_census_inventory(
    years: Optional[List[int]] = None,
    include_genz: bool = True,
    save_path: Optional[Path] = None,
    request_delay: float = 0.5,
    timeout: int = 15,
) -> dict:
    """Crawl the Census FTP and return a timestamped directory inventory.

    Fetches the TIGER (and optionally GENZ) year→layers structure using
    BeautifulSoup and saves it as JSON so callers can use it as a fallback
    when live Census requests are blocked (403) or rate-limited (429).

    Parameters
    ----------
    years:
        Specific years to crawl.  Defaults to 2010 through the current year.
    include_genz:
        Also crawl the Cartographic Boundary File (GENZ) tree.
    save_path:
        Where to save the JSON.  Defaults to
        ``~/.cache/siege_utilities/census_inventory.json``.
    request_delay:
        Seconds to sleep between HTTP requests to avoid hammering the Census
        server.
    timeout:
        Per-request timeout in seconds.

    Returns
    -------
    dict with keys ``updated_at``, ``tiger``, and (optionally) ``genz``.
    ``tiger[year]`` is a sorted list of layer directory names.
    ``genz[year]`` is a sorted list of available CB file name stems.
    """
    import json

    if years is None:
        years = list(range(2010, datetime.now().year + 1))

    def _parse_dir_links(html: bytes) -> List[str]:
        soup = BeautifulSoup(html, "html.parser")
        return sorted(
            href.rstrip("/")
            for a in soup.find_all("a")
            if (href := a.get("href", "")).endswith("/") and href != "../"
        )

    def _get(url: str) -> Optional[bytes]:
        try:
            r = requests.get(url, timeout=timeout)
            if r.status_code == 200:
                return r.content
            log.debug("census inventory crawl: %s → %s", url, r.status_code)
        except Exception as exc:
            log.debug("census inventory crawl: %s → %s", url, exc)
        return None

    inventory: dict = {
        "updated_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "tiger": {},
    }
    if include_genz:
        inventory["genz"] = {}

    for year in years:
        time.sleep(request_delay)
        tiger_url = f"{_TIGER_BASE}TIGER{year}/"
        html = _get(tiger_url)
        if html:
            dirs = _parse_dir_links(html)
            inventory["tiger"][str(year)] = dirs
            log.info("census inventory: TIGER%s → %d dirs", year, len(dirs))
        else:
            log.warning("census inventory: TIGER%s listing unavailable", year)

        if include_genz:
            time.sleep(request_delay)
            genz_url = f"{_TIGER_BASE}GENZ{year}/shp/"
            html = _get(genz_url)
            if html is None:
                # 2013 and earlier store files directly in the year dir, no shp/
                genz_url = f"{_TIGER_BASE}GENZ{year}/"
                html = _get(genz_url)
            if html:
                soup = BeautifulSoup(html, "html.parser")
                stems = sorted(set(
                    re.sub(r"\.(zip|shp|dbf|shx|prj)$", "", a.get("href", ""), flags=re.I)
                    for a in soup.find_all("a")
                    if a.get("href", "").lower().endswith(".zip")
                ))
                inventory["genz"][str(year)] = stems
                log.info("census inventory: GENZ%s → %d files", year, len(stems))

    save_path = Path(save_path or _DEFAULT_INVENTORY_PATH)
    save_path.parent.mkdir(parents=True, exist_ok=True)
    with open(save_path, "w") as fh:
        json.dump(inventory, fh, indent=2)
    log.info("census inventory saved to %s", save_path)
    return inventory


def load_census_inventory(path: Optional[Path] = None) -> Optional[dict]:
    """Load the saved Census inventory from disk.  Returns None if absent."""
    import json
    p = Path(path or _DEFAULT_INVENTORY_PATH)
    if not p.exists():
        return None
    try:
        with open(p) as fh:
            return json.load(fh)
    except Exception as exc:
        log.warning("could not load census inventory from %s: %s", p, exc)
        return None


def _dirs_from_inventory(year: int, inventory: Optional[dict] = None) -> Optional[List[str]]:
    """Return cached TIGER layer dirs for *year* from the on-disk inventory.

    Returns None if the inventory is unavailable or has no entry for the year.
    """
    inv = inventory or load_census_inventory()
    if inv is None:
        return None
    dirs = inv.get("tiger", {}).get(str(year))
    if dirs is not None:
        log.debug("census fallback: using inventory dirs for TIGER%s (%d entries)", year, len(dirs))
    return dirs


def _known_tiger_directories_for_year(year: int) -> List[str]:
    """Static fallback directory list for a TIGER/Line annual release.

    Used when the Census FTP returns 429 (rate-limit) on the top-level
    ``TIGER{year}/`` directory listing.  These subdirectories exist in every
    annual TIGER release from 2010 onward.  The generic ``CD`` directory is
    included because Census uses it for both national pre-2022 files
    (``tl_{year}_us_cd{congress}.zip``) and per-state 2022+ files
    (``tl_{year}_{fips}_cd{congress}.zip``).
    """
    dirs = ["BG", "CD", "COUNTY", "PLACE", "SLDL", "SLDU", "STATE", "TRACT"]
    if year >= 2012:
        dirs.append("ZCTA5")
    if year == 2020:
        dirs += ["TABBLOCK20", "VTD20"]
    elif year == 2010:
        dirs += ["TABBLOCK10", "VTD10"]
    return sorted(dirs)


class CensusDirectoryDiscovery:
    """Discovers available Census TIGER/Line data dynamically."""
    
    def __init__(self, timeout: Optional[int] = None):
        self.base_url = CENSUS_BASE_URL
        self.timeout = timeout or get_service_timeout('census_api')
        self.cache = {}
        self.cache_timeout = CENSUS_CACHE_TIMEOUT
        
    def _parse_year_links(self, content: bytes) -> List[int]:
        """Parse Census directory HTML to extract available years."""
        soup = BeautifulSoup(content, 'html.parser')
        year_patterns = [
            re.compile(r'TIGER(\d{4})'),
            re.compile(r'GENZ(\d{4})'),
            re.compile(r'TGRGDB(\d{2})'),  # TGRGDB13, TGRGDB14, etc.
            re.compile(r'TGRGPKG(\d{2})')  # TGRGPKG24, TGRGPKG25, etc.
        ]

        years = []
        for link in soup.find_all('a'):
            href = link.get('href', '')
            for pattern in year_patterns:
                match = pattern.search(href)
                if match:
                    if 'TGRGDB' in href or 'TGRGPKG' in href:
                        year = 2000 + int(match.group(1))
                    else:
                        year = int(match.group(1))
                    if 1990 <= year <= datetime.now().year + 1:
                        years.append(year)
                    break

        return sorted(list(set(years)))

    def get_available_years(self, force_refresh: bool = False) -> List[int]:
        """Get list of available Census years with retry and exponential backoff."""
        cache_key = "available_years"

        if not force_refresh and cache_key in self.cache:
            cache_time, data = self.cache[cache_key]
            if time.time() - cache_time < self.cache_timeout:
                return data

        last_exception = None
        for attempt in range(CENSUS_RETRY_ATTEMPTS):
            verify_ssl = True
            try:
                log.debug(f"Discovering Census years (attempt {attempt + 1}/{CENSUS_RETRY_ATTEMPTS})")
                response = requests.get(self.base_url, timeout=self.timeout, verify=verify_ssl)
                response.raise_for_status()

                years = self._parse_year_links(response.content)
                self.cache[cache_key] = (time.time(), years)
                return years

            except requests.exceptions.SSLError:
                if verify_ssl:
                    log.warning("SSL verification failed, retrying without verification...")
                    verify_ssl = False
                    try:
                        response = requests.get(self.base_url, timeout=self.timeout, verify=False)
                        response.raise_for_status()
                        years = self._parse_year_links(response.content)
                        self.cache[cache_key] = (time.time(), years)
                        return years
                    except Exception as e:
                        last_exception = e

            except requests.exceptions.Timeout as e:
                last_exception = e
                log.warning(f"Census directory request timed out (attempt {attempt + 1}/{CENSUS_RETRY_ATTEMPTS})")

            except requests.exceptions.RequestException as e:
                last_exception = e
                log.warning(f"Census directory request failed (attempt {attempt + 1}/{CENSUS_RETRY_ATTEMPTS}): {e}")

            except Exception as e:
                last_exception = e
                log.warning(f"Unexpected error during Census discovery (attempt {attempt + 1}/{CENSUS_RETRY_ATTEMPTS}): {e}")

            # Exponential backoff before retry (1s, 2s, 4s, 8s, ...)
            if attempt < CENSUS_RETRY_ATTEMPTS - 1:
                sleep_time = 2 ** attempt
                log.info(f"Retrying in {sleep_time}s...")
                time.sleep(sleep_time)

        log.error(f"Failed to discover available years after {CENSUS_RETRY_ATTEMPTS} attempts: {last_exception}")
        log.info("Using fallback years (2010-present)")
        return list(range(2010, datetime.now().year + 1))
    
    def get_year_directory_contents(
        self, year: int, force_refresh: bool = False, on_error: str = "skip",
    ) -> List[str]:
        """Get contents of a specific TIGER year directory.

        Parameters
        ----------
        year : int
            Census TIGER year.
        force_refresh : bool
            Bypass the in-memory cache.
        on_error : ``"raise"`` | ``"warn"`` | ``"skip"``
            What to do when the network request fails.  ``"skip"`` (default)
            returns an empty list silently — preserving the legacy behaviour.
        """
        from siege_utilities.exceptions import SiegeGeoError, handle_error

        cache_key = f"year_{year}_contents"

        if not force_refresh and cache_key in self.cache:
            cache_time, data = self.cache[cache_key]
            if time.time() - cache_time < self.cache_timeout:
                return data

        try:
            year_url = f"{self.base_url}/TIGER{year}/"
            response = requests.get(year_url, timeout=self.timeout)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')
            directories = []

            for link in soup.find_all('a'):
                href = link.get('href', '')
                if href.endswith('/') and href != '../':
                    directories.append(href.rstrip('/'))

            self.cache[cache_key] = (time.time(), directories)
            return directories

        except requests.exceptions.SSLError:
            log.warning(f"SSL verification failed for year {year}, trying without verification...")
            try:
                # Fallback: try without SSL verification
                year_url = f"{self.base_url}/TIGER{year}/"
                response = requests.get(year_url, timeout=self.timeout, verify=False)
                response.raise_for_status()

                soup = BeautifulSoup(response.content, 'html.parser')
                directories = []

                for link in soup.find_all('a'):
                    href = link.get('href', '')
                    if href.endswith('/') and href != '../':
                        directories.append(href.rstrip('/'))

                self.cache[cache_key] = (time.time(), directories)
                return directories

            except Exception as e:
                return handle_error(
                    SiegeGeoError(f"Failed to get contents for year {year} (SSL bypass): {e}"),
                    on_error=on_error, fallback=[], context=f"TIGER directory listing for {year}",
                )

        except Exception as e:
            # On rate-limit (429), substitute the static known-directory list
            # instead of returning [] (which silently skips every boundary type).
            # Only override "skip" callers — "raise"/"warn" callers still see
            # the error so their error strategy is honoured.
            _status = getattr(getattr(e, "response", None), "status_code", None)
            if on_error == "skip" and isinstance(e, requests.exceptions.HTTPError) and _status in (429, 403):
                # 429 = rate-limited; 403 = directory browsing blocked.
                # In both cases the individual layer files almost certainly
                # exist — use the crawled inventory first, then the static list.
                fallback = _dirs_from_inventory(year) or _known_tiger_directories_for_year(year)
                reason = "rate-limited (429)" if _status == 429 else "directory browsing blocked (403)"
                log.warning(
                    "Census TIGER%s directory listing %s; "
                    "using fallback (%d directories)",
                    year, reason, len(fallback),
                )
                _FALLBACK_CACHE_TTL = 300  # 5-minute TTL so a recovered endpoint is retried soon
                self.cache[cache_key] = (time.time() - self.cache_timeout + _FALLBACK_CACHE_TTL, fallback)
                return fallback
            return handle_error(
                SiegeGeoError(f"Failed to get contents for year {year}: {e}"),
                on_error=on_error, fallback=[], context=f"TIGER directory listing for {year}",
            )
    
    def discover_boundary_types(self, year: int) -> Dict[str, str]:
        """Discover what boundary types are available for a given year."""
        directories = self.get_year_directory_contents(year)
        
        # Comprehensive mapping of directory names to boundary types
        # This handles variations in naming conventions across different years
        boundary_mapping = {
            # Core geographic boundaries
            'STATE': 'state',
            'COUNTY': 'county', 
            'TRACT': 'tract',
            'BG': 'block_group',
            'TABBLOCK': 'block',
            'TABBLOCK20': 'tabblock20',  # 2020+ naming
            'TABBLOCK10': 'tabblock10',  # 2010 naming
            'PLACE': 'place',
            'ZCTA5': 'zcta',
            'ZCTA': 'zcta',    # Alternative naming
            'ZCTA520': 'zcta', # 2020+ directory name (Census renamed from ZCTA5)
            
            # Legislative boundaries
            'SLDU': 'sldu',  # State Legislative District Upper
            'SLDL': 'sldl',  # State Legislative District Lower
            'CD': 'cd',      # Congressional District
            'CD108': 'cd108', # 108th Congress
            'CD109': 'cd109', # 109th Congress
            'CD110': 'cd110', # 110th Congress
            'CD111': 'cd111', # 111th Congress
            'CD112': 'cd112', # 112th Congress
            'CD113': 'cd113', # 113th Congress
            'CD114': 'cd114', # 114th Congress
            'CD115': 'cd115', # 115th Congress
            'CD116': 'cd116', # 116th Congress
            'CD118': 'cd118', # 118th Congress
            'CD119': 'cd119', # 119th Congress
            
            # Special purpose boundaries
            'CBSA': 'cbsa',  # Core Based Statistical Area
            'CSA': 'csa',    # Combined Statistical Area
            'METDIV': 'metdiv',  # Metropolitan Division
            'MICRO': 'micro',    # Micropolitan Statistical Area
            'NECTA': 'necta',    # New England City and Town Area
            'NECTADIV': 'nectadiv',  # NECTA Division
            'CNECTA': 'cnecta',  # Combined NECTA
            
            # Tribal boundaries
            'AIANNH': 'aiannh',  # American Indian/Alaska Native/Native Hawaiian Areas
            'AITSCE': 'aitsce',  # American Indian Tribal Subdivisions
            'TTRACT': 'ttract',  # Tribal Census Tracts
            'TBG': 'tbg',        # Tribal Block Groups
            
            # School districts
            'ELSD': 'elsd',  # Elementary School District
            'SCSD': 'scsd',  # Secondary School District
            'UNSD': 'unsd',  # Unified School District
            
            # Transportation and infrastructure
            'ADDRFEAT': 'address_features',
            'LINEARWATER': 'linear_water',
            'AREAWATER': 'area_water',
            'ROADS': 'roads',
            'RAILS': 'rails',
            'EDGES': 'edges',
            
            # Special areas
            'ANRC': 'anrc',  # Alaska Native Regional Corporation
            'CONCITY': 'concity',  # Consolidated City
            'SUBMCD': 'submcd',    # Subminor Civil Division
            'COUSUB': 'cousub',    # County Subdivision
            
            # Voting districts
            'VTD': 'vtd',    # Voting District
            'VTD20': 'vtd20', # 2020 Voting District
            
            # Urban areas
            'UAC': 'uac',    # Urban Area
            'UAC20': 'uac20', # 2020 Urban Area
        }
        
        available_types = {}
        for directory in directories:
            if directory in boundary_mapping:
                available_types[boundary_mapping[directory]] = directory
            # Also check for variations and aliases
            elif directory.replace('_', '').replace('-', '') in boundary_mapping:
                clean_dir = directory.replace('_', '').replace('-', '')
                available_types[boundary_mapping[clean_dir]] = directory
        
        return available_types
    
    def get_year_specific_url_patterns(self, year: int) -> Dict[str, Any]:
        """Get year-specific URL patterns and directory structures."""
        patterns = {
            # Base patterns that work across most years
            'base_url': f"{self.base_url}/TIGER{year}",
            'filename_patterns': {
                # National files (no state FIPS needed)
                'national': 'tl_{year}_us_{boundary_type}.zip',
                # State-specific files (state FIPS required)
                'state': 'tl_{year}_{state_fips}_{boundary_type}.zip',
                # Congressional districts with number
                'congress': 'tl_{year}_us_cd{congress_num}.zip',
                # Per-state congressional districts (2022+, Census dropped the national file)
                'congress_state': 'tl_{year}_{state_fips}_cd{congress_num}.zip'
            },
            'directory_mappings': {}
        }
        
        # Year-specific adjustments
        if year >= 2020:
            # 2020 and later have some different patterns
            patterns['directory_mappings'].update({
                'tabblock': 'TABBLOCK20',
                'vtd': 'VTD20',
                'uac': 'UAC20'
            })
        elif year >= 2010:
            patterns['directory_mappings'].update({
                'tabblock': 'TABBLOCK10',
                'vtd': 'VTD10',
                'uac': 'UAC10'
            })
        
        return patterns
    
    # ------------------------------------------------------------------
    # TIGER PL (redistricting) VTD helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _is_vtd_pl_boundary(boundary_type: str, year: int) -> bool:
        """Return True when *boundary_type* must come from a TIGER PL release.

        VTD data is only published in the decennial PL 94-171 product for
        census years (2020, 2010).  It does not appear in the standard annual
        TIGER release for those years. Vintage-specific suffixes must match
        the requested year: ``'vtd20'`` pairs only with 2020, ``'vtd10'`` only
        with 2010. The unsuffixed ``'vtd'`` works for either.
        """
        if year == 2020:
            return boundary_type in ('vtd', 'vtd20')
        if year == 2010:
            return boundary_type in ('vtd', 'vtd10')
        return False

    @staticmethod
    def _construct_vtd_pl_url(year: int, state_fips: str) -> str:
        """Return the TIGER PL download URL for a state's VTD shapefile.

        Raises:
            BoundaryInputError: if *state_fips* has no PL state name mapping
                (i.e. the territory does not publish VTD data).
            BoundaryDiscoveryError: if *year* is not a supported decennial year.
        """
        if year == 2020:
            suffix = 'vtd20'
            pl_dir = 'TIGER2020PL'
        elif year == 2010:
            # 2010 VTDs are published as county-level files under
            # TIGER2010/VTD/2010/ (e.g. tl_2010_48001_vtd10.zip), not as a
            # state-level ZIP under TIGER2010PL/STATE/. The state-level path
            # does not exist on Census and would 404 at download time.
            # Until county-level enumeration is implemented, fail fast.
            raise BoundaryDiscoveryError(
                "2010 VTD boundaries are published per-county under "
                "TIGER2010/VTD/2010/ (e.g. tl_2010_<state_fips><county_fips>_vtd10.zip), "
                "not as a single state-level ZIP. County-level enumeration is not "
                "yet supported by this routing; fetch the required counties directly.",
                context={"year": 2010, "boundary_type": "vtd", "state_fips": state_fips},
            )
        else:
            raise BoundaryDiscoveryError(
                f"VTD PL boundaries are only available for decennial year 2020. "
                f"Requested year: {year}.",
                context={"year": year, "boundary_type": "vtd"},
            )

        state_name = _VTD_PL_STATE_NAMES.get(state_fips)
        if not state_name:
            raise BoundaryInputError(
                f"State FIPS {state_fips!r} does not publish VTD data in "
                f"{pl_dir}.  Check _VTD_PL_STATE_NAMES for supported states.",
                context={"year": year, "boundary_type": "vtd", "state_fips": state_fips},
            )

        url = (
            f"{TIGER_PL_BASE_URL}/{pl_dir}/STATE/"
            f"{state_fips}_{state_name}/{state_fips}/"
            f"tl_{year}_{state_fips}_{suffix}.zip"
        )
        log.info("VTD PL URL: %s", url)
        return url

    def construct_download_url(self, year: int, boundary_type: str, state_fips: Optional[str] = None,
                              congress_number: Optional[int] = None) -> str:
        """Construct download URL using FIPS validation and year-specific patterns.

        Raises:
            BoundaryInputError: If state_fips is invalid.
            BoundaryDiscoveryError: If boundary_type is not available or URL cannot be constructed.
        """
        ctx = {"year": year, "boundary_type": boundary_type, "state_fips": state_fips}
        try:
            # Validate state_fips using centralized FIPS data
            if state_fips:
                if state_fips not in FIPS_TO_STATE:
                    raise BoundaryInputError(
                        f"Invalid state FIPS code: {state_fips}. "
                        f"Valid codes: {list(FIPS_TO_STATE.keys())[:10]}...",
                        context=ctx,
                    )

                state_info = get_fips_info(state_fips)
                log.info(f"Constructing URL for {state_info['name']} ({state_info['abbreviation']})")

            # VTD data lives in the decennial PL 94-171 redistricting product,
            # NOT in the standard annual TIGER release.  Route before doing
            # directory discovery so we never try to find VTD20/ on tiger.
            if self._is_vtd_pl_boundary(boundary_type, year):
                if not state_fips:
                    raise BoundaryInputError(
                        "VTD boundaries require a state_fips code.",
                        context=ctx,
                    )
                return self._construct_vtd_pl_url(year, state_fips)

            # Get year-specific patterns
            patterns = self.get_year_specific_url_patterns(year)

            # Get available boundary types for this year
            available_types = self.discover_boundary_types(year)

            if boundary_type not in available_types:
                available_list = list(available_types.keys())[:20]
                raise BoundaryDiscoveryError(
                    f"Boundary type '{boundary_type}' not available for year {year}. "
                    f"Available: {available_list}",
                    context={**ctx, "available_types": available_list},
                )

            directory = available_types[boundary_type]
            base_url = f"{patterns['base_url']}/{directory}"

            # Determine which filename pattern to use
            filename = self._construct_filename_with_fips_validation(
                year, boundary_type, state_fips, congress_number, patterns
            )

            if not filename:
                raise BoundaryDiscoveryError(
                    f"Could not construct filename for {boundary_type} year={year} "
                    f"state_fips={state_fips} congress={congress_number}",
                    context=ctx,
                )

            final_url = f"{base_url}/{filename}"
            log.info(f"Constructed URL: {final_url}")

            return final_url

        except (BoundaryInputError, BoundaryDiscoveryError, BoundaryConfigurationError):
            raise
        except Exception as e:
            raise BoundaryDiscoveryError(
                f"Failed to construct URL for {boundary_type} in year {year}: {e}",
                context={**ctx, "original_error": str(e)},
            ) from e
    
    def _construct_filename_with_fips_validation(self, year: int, boundary_type: str, 
                                               state_fips: Optional[str], congress_number: Optional[int],
                                               patterns: Dict[str, Any]) -> Optional[str]:
        """Construct filename using FIPS validation and boundary type rules."""
        
        # Define which boundary types require state FIPS (canonical names)
        state_required_types = {
            'tabblock', 'tabblock10', 'tabblock20', 'tract', 'block_group', 'block',
            'sldu', 'sldl', 'vtd', 'vtd10', 'vtd20', 'cousub', 'submcd'
        }
        
        # Define national-only types (never use state FIPS in URL)
        # Note: county is national-only but we filter results post-download
        national_only_types = {
            'state', 'county', 'cbsa', 'csa', 'metdiv', 'micro', 'necta',
            'nectadiv', 'cnecta', 'aiannh', 'aitsce', 'ttract', 'tbg',
            'elsd', 'scsd', 'unsd', 'uac', 'uac10', 'uac20'
        }

        # Define flexible types (can be national or state-specific)
        flexible_types = {'place', 'zcta', 'anrc', 'concity'}
        # Census uses short abbreviations in filenames that differ from the canonical type name.
        _FILENAME_ABBREVS = {'block_group': 'bg'}

        # Handle congressional districts specially
        if boundary_type.startswith('cd'):
            if len(boundary_type) > 2:
                # Specific congress number in boundary type (cd118, cd119, etc.)
                congress_num = boundary_type[2:]
            elif congress_number:
                # Congress number provided separately — zero-pad to 3 digits
                congress_num = f"{congress_number:03d}"
            else:
                max_known = max(YEAR_TO_CONGRESS.keys())
                congress_num = str(YEAR_TO_CONGRESS[max_known])
                log.warning(
                    "Year %d not in YEAR_TO_CONGRESS; falling back to %d (congress %s). "
                    "Add the year to YEAR_TO_CONGRESS if this is incorrect.",
                    year, max_known, congress_num,
                )
            # Census dropped the national CD file after 2021; 2022+ only publishes 56 per-state files.
            if year >= 2022 and not state_fips:
                raise BoundaryConfigurationError(
                    f"Congressional district national file is unavailable for {year}+. "
                    f"Provide state_fips to download the per-state file.",
                    context={"boundary_type": boundary_type, "year": year},
                )
            if state_fips and year >= 2022:
                return patterns['filename_patterns']['congress_state'].format(
                    year=year, state_fips=state_fips, congress_num=congress_num
                )
            return patterns['filename_patterns']['congress'].format(
                year=year, congress_num=congress_num
            )

        # Handle state-required types
        elif boundary_type in state_required_types:
            if not state_fips:
                sample_fips = {
                    fips: f"{STATE_NAMES[abbrev]} ({abbrev})"
                    for fips, abbrev in list(FIPS_TO_STATE.items())[:5]
                }
                raise BoundaryConfigurationError(
                    f"State FIPS code required for boundary type '{boundary_type}'. "
                    f"Example FIPS codes: {sample_fips}",
                    context={
                        "boundary_type": boundary_type,
                        "year": year,
                        "requires": "state_fips",
                    },
                )
            filename_part = _FILENAME_ABBREVS.get(boundary_type, boundary_type)
            return patterns['filename_patterns']['state'].format(
                year=year, state_fips=state_fips, boundary_type=filename_part
            )

        # Handle ZCTA: filename abbreviation and directory are year-dependent.
        # 2020+: ZCTA520 directory + zcta520 abbreviation.
        # pre-2020: ZCTA5 directory + zcta510 abbreviation.
        # ZCTA files are always national (no per-state variant exists).
        elif boundary_type == 'zcta':
            zcta_abbrev = 'zcta520' if year >= 2020 else 'zcta510'
            return patterns['filename_patterns']['national'].format(
                year=year, boundary_type=zcta_abbrev
            )

        # Handle national-only types
        elif boundary_type in national_only_types:
            return patterns['filename_patterns']['national'].format(
                year=year, boundary_type=boundary_type
            )

        # Handle flexible types
        elif boundary_type in flexible_types:
            if state_fips:
                # User provided state FIPS, use state-specific version
                state_info = get_fips_info(state_fips)
                log.info(f"Using state-specific {boundary_type} for {state_info['name']}")
                return patterns['filename_patterns']['state'].format(
                    year=year, state_fips=state_fips, boundary_type=boundary_type
                )
            else:
                # No state FIPS provided, use national version
                log.info(f"Using national {boundary_type} file")
                return patterns['filename_patterns']['national'].format(
                    year=year, boundary_type=boundary_type
                )
        
        # Default pattern for unknown types
        else:
            log.warning(f"Unknown boundary type: {boundary_type}, using default pattern")
            if state_fips:
                return patterns['filename_patterns']['state'].format(
                    year=year, state_fips=state_fips, boundary_type=boundary_type
                )
            else:
                return patterns['filename_patterns']['national'].format(
                    year=year, boundary_type=boundary_type
                )
    
    def validate_download_url(self, url: str) -> bool:
        """Check if a download URL is actually accessible.

        Uses GET with stream=True instead of HEAD because CDNs like Cloudflare
        often block or throttle HEAD requests from non-browser User-Agents.

        Raises:
            BoundaryUrlValidationError: If the URL is not accessible.
        """
        headers = {'User-Agent': 'siege_utilities/1.0 (Census data client)'}
        ctx: Dict[str, Any] = {"url": url}
        try:
            response = requests.get(url, timeout=self.timeout, stream=True, headers=headers)
            response.close()
            if response.status_code == 200:
                return True
            if response.status_code == 429:
                log.warning(
                    "Census rate-limited (429) URL validation for %s; "
                    "assuming URL is valid and proceeding with download",
                    url,
                )
                return True
            ctx["http_status"] = response.status_code
            raise BoundaryUrlValidationError(
                f"URL returned HTTP {response.status_code}: {url}",
                context=ctx,
            )
        except BoundaryUrlValidationError:
            raise
        except requests.exceptions.SSLError as ssl_err:
            log.debug(f"SSL verification failed for {url}, trying without verification...")
            ctx["ssl_error"] = str(ssl_err)
            try:
                response = requests.get(url, timeout=self.timeout, stream=True,
                                        headers=headers, verify=False)
                response.close()
                if response.status_code == 200:
                    return True
                ctx["http_status"] = response.status_code
                raise BoundaryUrlValidationError(
                    f"URL returned HTTP {response.status_code} (SSL bypass): {url}",
                    context=ctx,
                )
            except BoundaryUrlValidationError:
                raise
            except Exception as e:
                ctx["fallback_error"] = str(e)
                raise BoundaryUrlValidationError(
                    f"URL validation failed for {url} (with SSL bypass): {e}",
                    context=ctx,
                ) from e
        except requests.exceptions.Timeout as e:
            ctx["timeout_seconds"] = self.timeout
            raise BoundaryUrlValidationError(
                f"URL validation timed out after {self.timeout}s: {url}",
                context=ctx,
            ) from e
        except Exception as e:
            ctx["error_type"] = type(e).__name__
            raise BoundaryUrlValidationError(
                f"URL validation failed for {url}: {e}",
                context=ctx,
            ) from e
    
    def get_optimal_year(self, requested_year: int, boundary_type: str) -> int:
        """Find the best available year for a requested boundary type."""
        available_years = self.get_available_years()
        
        if requested_year in available_years:
            return requested_year
        
        # Find closest available year
        available_years.sort()
        closest_year = min(available_years, key=lambda y: abs(y - requested_year))
        
        log.info(f"Requested year {requested_year} not available for {boundary_type}. "
                f"Using closest available year: {closest_year}")
        
        return closest_year


class SpatialDataSource:
    """Base class for spatial data sources."""
    
    def __init__(self, name: str, base_url: str, api_key: Optional[str] = None):
        """
        Initialize spatial data source.
        
        Args:
            name: Name of the data source
            base_url: Base URL for the data source
            api_key: API key if required
        """
        self.name = name
        self.base_url = base_url
        self.api_key = api_key
        
        # Get user configuration for API keys and preferences
        try:
            self.user_config = get_user_config()
        except Exception as e:
            log.warning(f"Failed to load user config: {e}")
            self.user_config = {}
    
    def download_data(self, **kwargs) -> Optional[GeoDataFrame]:
        """Download data from the source."""
        raise NotImplementedError("Subclasses must implement download_data")


class CensusDataSource(SpatialDataSource):
    """Census TIGER/Line boundary data source with dynamic year discovery.

    Supports all standard TIGER/Line boundary types:

    **National-scope** (no state_fips required):
        ``nation``, ``state``, ``county``, ``place``, ``zcta``, ``cd``

    **State-scope** (state_fips required):
        ``tract``, ``block_group``, ``block``, ``tabblock20``, ``sldu``, ``sldl``

    GEOID formats by boundary type:

    =============  ======  =================================
    Boundary       Digits  Components
    =============  ======  =================================
    state          2       SS
    county         5       SS + CCC
    tract          11      SS + CCC + TTTTTT
    block_group    12      SS + CCC + TTTTTT + G
    tabblock20     15      SS + CCC + TTTTTT + BBBB
    cd             4       SS + DD
    sldu           5       SS + DDD
    sldl           5       SS + DDD
    =============  ======  =================================
    """
    
    def __init__(self, api_key: Optional[str] = None, timeout: Optional[int] = None):
        super().__init__("Census Bureau", CENSUS_BASE_URL, api_key)
        
        # Initialize discovery service with configurable timeout
        census_timeout = timeout or get_service_timeout('census_api')
        self.discovery = CensusDirectoryDiscovery(timeout=census_timeout)
        
        # Get available years dynamically
        self.available_years = self.discovery.get_available_years()
        
        # Geographic levels that require state FIPS
        self.state_required_levels = ['tract', 'block_group', 'block', 'tabblock20', 'sldu', 'sldl']
        
        # Geographic levels that don't require state FIPS
        self.national_levels = ['nation', 'state', 'county', 'place', 'zcta', 'cd']

        log.info(f"Initialized Census data source with {len(self.available_years)} available years")

    def get_available_years(self, force_refresh: bool = False) -> List[int]:
        """Get list of available Census years.

        Args:
            force_refresh: If True, re-discover years from Census server

        Returns:
            List of available years
        """
        if force_refresh:
            self.available_years = self.discovery.get_available_years(force_refresh=True)
        return self.available_years

    def get_year_directory_contents(self, year: int) -> List[str]:
        """Get directory contents for a specific year."""
        return self.discovery.get_year_directory_contents(year)

    def discover_boundary_types(self, year: int) -> List[str]:
        """Discover available boundary types for a year."""
        return self.discovery.discover_boundary_types(year)

    def get_geographic_boundaries(self,
                                year: int = DEFAULT_CENSUS_YEAR,
                                geographic_level: str = 'county',
                                state_fips: Optional[str] = None,
                                county_fips: Optional[str] = None,
                                congress_number: Optional[int] = None) -> Optional[GeoDataFrame]:
        """
        Download geographic boundaries from Census TIGER/Line files with dynamic discovery.

        This method preserves the legacy ``Optional[GeoDataFrame]`` return type.
        For structured diagnostics, use :meth:`fetch_geographic_boundaries` instead.

        Args:
            year: Census year (will find closest available if not available)
            geographic_level: Geographic level (state, county, tract, etc.)
            state_fips: State FIPS code for filtering (required for some levels)
            county_fips: County FIPS code for filtering
            congress_number: Congress number for congressional districts

        Returns:
            GeoDataFrame with boundaries or None if failed
        """
        _warnings_mod.warn(
            "get_geographic_boundaries() returns None on failure with no diagnostics. "
            "Use fetch_geographic_boundaries() for structured error reporting.",
            DeprecationWarning,
            stacklevel=2,
        )
        result = self.fetch_geographic_boundaries(
            year=year,
            geographic_level=geographic_level,
            state_fips=state_fips,
            county_fips=county_fips,
            congress_number=congress_number,
        )
        if result.success:
            return result.geodataframe
        log.error(f"Boundary retrieval failed at stage '{result.error_stage}': {result.message}")
        return None

    def fetch_geographic_boundaries(self,
                                    year: int = DEFAULT_CENSUS_YEAR,
                                    geographic_level: str = 'county',
                                    state_fips: Optional[str] = None,
                                    county_fips: Optional[str] = None,
                                    congress_number: Optional[int] = None) -> BoundaryFetchResult:
        """
        Download geographic boundaries with structured diagnostics.

        Returns a :class:`BoundaryFetchResult` that carries either the
        GeoDataFrame on success or a machine-readable error code, stage, and
        context dict on failure.

        Args:
            year: Census year (will find closest available if not available)
            geographic_level: Geographic level (state, county, tract, etc.)
            state_fips: State FIPS code for filtering (required for some levels)
            county_fips: County FIPS code for filtering
            congress_number: Congress number for congressional districts

        Returns:
            BoundaryFetchResult with .success, .geodataframe, .error_stage, etc.
        """
        base_ctx: Dict[str, Any] = {
            "year": year,
            "geographic_level": geographic_level,
            "state_fips": state_fips,
            "county_fips": county_fips,
            "congress_number": congress_number,
        }
        try:
            # --- Stage: input_validation ---
            normalized_fips = None
            if state_fips:
                try:
                    normalized_fips = normalize_state_identifier(state_fips)
                except ValueError as e:
                    return BoundaryFetchResult.fail(
                        error_code="INVALID_STATE_IDENTIFIER",
                        error_stage="input_validation",
                        message=f"Invalid state identifier: '{state_fips}' - {e}. "
                                "Valid examples: FIPS ('06'), abbreviation ('CA'), or name ('California')",
                        context=base_ctx,
                    )

                state_info = get_fips_info(normalized_fips)
                log.info(
                    f"Normalized '{state_fips}' to FIPS {normalized_fips}: "
                    f"{state_info['name']} ({state_info['abbreviation']})"
                )
                state_fips = normalized_fips
                base_ctx["normalized_fips"] = normalized_fips

            try:
                self._validate_census_parameters(year, geographic_level, state_fips)
            except ValueError as e:
                return BoundaryFetchResult.fail(
                    error_code="INVALID_PARAMETERS",
                    error_stage="input_validation",
                    message=str(e),
                    context=base_ctx,
                )

            # --- Stage: discovery ---
            optimal_year = self.discovery.get_optimal_year(year, geographic_level)
            base_ctx["optimal_year"] = optimal_year

            try:
                url = self.discovery.construct_download_url(
                    optimal_year, geographic_level, state_fips, congress_number
                )
            except BoundaryRetrievalError as e:
                return BoundaryFetchResult.fail(
                    error_code="URL_CONSTRUCTION_FAILED",
                    error_stage=e.stage,
                    message=str(e),
                    context={**base_ctx, **e.context},
                )

            base_ctx["download_url"] = url

            # --- Stage: url_validation ---
            try:
                self.discovery.validate_download_url(url)
            except BoundaryUrlValidationError as e:
                return BoundaryFetchResult.fail(
                    error_code="URL_NOT_ACCESSIBLE",
                    error_stage="url_validation",
                    message=str(e),
                    context={**base_ctx, **e.context},
                )

            log.info(f"Downloading {geographic_level} boundaries for year {optimal_year}")

            # --- Stages: download + parse ---
            try:
                gdf = self._download_and_process_tiger(url, geographic_level)
            except BoundaryRetrievalError as e:
                return BoundaryFetchResult.fail(
                    error_code=e.context.get("error_code", "DOWNLOAD_OR_PARSE_FAILED"),
                    error_stage=e.stage,
                    message=str(e),
                    context={**base_ctx, **e.context},
                )

            if gdf is None:
                return BoundaryFetchResult.fail(
                    error_code="NO_DATA_RETURNED",
                    error_stage="parse",
                    message=f"_download_and_process_tiger returned None for {url}",
                    context=base_ctx,
                )

            # Post-download filtering for national-only boundary types
            # These types are only available as nationwide files from Census,
            # so we download the full national file and filter by state FIPS
            national_only_types = {
                'state', 'county', 'cbsa', 'csa', 'metdiv', 'micro',
                'necta', 'nectadiv', 'cnecta', 'aiannh', 'uac', 'uac10', 'uac20',
            }
            if normalized_fips and geographic_level in national_only_types:
                fips_col = None
                for col in ['statefp', 'STATEFP', 'statefp20', 'STATEFP20',
                            'statefp10', 'STATEFP10']:
                    if col in gdf.columns:
                        fips_col = col
                        break

                if fips_col:
                    original_count = len(gdf)
                    gdf = gdf[gdf[fips_col] == normalized_fips].copy()
                    log.info(
                        f"Filtered {geographic_level} from {original_count} to "
                        f"{len(gdf)} features for state {normalized_fips}"
                    )
                    base_ctx["filtered_from"] = original_count
                    base_ctx["filtered_to"] = len(gdf)
                else:
                    log.warning(
                        f"No state FIPS column found in {geographic_level} data "
                        f"— cannot filter by state"
                    )

            return BoundaryFetchResult.ok(
                gdf,
                message=f"Retrieved {len(gdf)} {geographic_level} features for year {optimal_year}",
                context=base_ctx,
            )

        except BoundaryRetrievalError as e:
            return BoundaryFetchResult.fail(
                error_code="RETRIEVAL_ERROR",
                error_stage=e.stage,
                message=str(e),
                context={**base_ctx, **e.context},
            )
        except Exception as e:
            return BoundaryFetchResult.fail(
                error_code="UNEXPECTED_ERROR",
                error_stage="unknown",
                message=f"Unexpected error: {type(e).__name__}: {e}",
                context={**base_ctx, "original_error": str(e)},
            )
    
    def get_available_boundary_types(self, year: int) -> Dict[str, str]:
        """Get available boundary types for a specific year."""
        return self.discovery.discover_boundary_types(year)
    
    def refresh_discovery_cache(self):
        """Refresh the discovery cache to get latest available data."""
        self.discovery.cache.clear()
        self.available_years = self.discovery.get_available_years(force_refresh=True)
        log.info("Discovery cache refreshed")
    
    def get_available_state_fips(self) -> Dict[str, str]:
        """Get mapping of state FIPS codes to state names."""
        # Use centralized FIPS data
        return {fips: STATE_NAMES[abbrev] for fips, abbrev in FIPS_TO_STATE.items()}
    
    # DEPRECATED: Old FIPS data method removed - use centralized constants instead
    
    def get_state_abbreviations(self) -> Dict[str, str]:
        """Get mapping of state FIPS codes to state abbreviations."""
        # Use centralized FIPS data
        return FIPS_TO_STATE.copy()
    
    def normalize_state_identifier(self, state_input) -> Optional[str]:
        """Convert any state identifier (FIPS, abbreviation, name) to FIPS code."""
        # DEPRECATED: Use centralized normalize_state_identifier function instead
        try:
            return normalize_state_identifier(state_input)
        except ValueError:
            return None
    
    def get_comprehensive_state_info(self) -> Dict[str, Dict[str, str]]:
        """Get comprehensive state information including FIPS, name, and abbreviation."""
        fips_to_name = self.get_available_state_fips()
        fips_to_abbr = self.get_state_abbreviations()
        
        comprehensive = {}
        for fips, name in fips_to_name.items():
            comprehensive[fips] = {
                'name': name,
                'abbreviation': fips_to_abbr.get(fips, ''),
                'fips': fips
            }
        
        return comprehensive
    
    def get_state_by_abbreviation(self, abbreviation: str) -> Optional[Dict[str, str]]:
        """Get state information by abbreviation."""
        if not abbreviation or len(abbreviation) != 2:
            return None
        
        fips_to_abbr = self.get_state_abbreviations()
        fips_to_name = self.get_available_state_fips()
        
        # Find FIPS code by abbreviation
        for fips, abbr in fips_to_abbr.items():
            if abbr.upper() == abbreviation.upper():
                return {
                    'fips': fips,
                    'name': fips_to_name[fips],
                    'abbreviation': abbr
                }
        
        return None
    
    def get_state_by_name(self, name: str) -> Optional[Dict[str, str]]:
        """Get state information by name (case-insensitive partial match)."""
        if not name:
            return None
        
        fips_to_name = self.get_available_state_fips()
        fips_to_abbr = self.get_state_abbreviations()
        
        # Find FIPS code by name (case-insensitive partial match)
        for fips, state_name in fips_to_name.items():
            if name.lower() in state_name.lower():
                return {
                    'fips': fips,
                    'name': state_name,
                    'abbreviation': fips_to_abbr.get(fips, '')
                }
        
        return None
    
    def validate_state_fips(self, state_fips: str) -> bool:
        """Validate if a state FIPS code is valid."""
        valid_fips = self.get_available_state_fips()
        return state_fips in valid_fips
    
    def get_state_name(self, state_fips: str) -> Optional[str]:
        """Get state name from FIPS code."""
        valid_fips = self.get_available_state_fips()
        return valid_fips.get(state_fips)
    
    def get_state_abbreviation(self, state_fips: str) -> Optional[str]:
        """Get state abbreviation from FIPS code."""
        valid_abbr = self.get_state_abbreviations()
        return valid_abbr.get(state_fips)
    
    def _validate_census_parameters(self, year: int, geographic_level: str, 
                                  state_fips: Optional[str]) -> None:
        """Validate Census API parameters."""
        if year < 1990 or year > datetime.now().year + 1:
            raise ValueError(f"Year {year} is outside valid range (1990-{datetime.now().year + 1})")
        
        if geographic_level in self.state_required_levels and not state_fips:
            raise ValueError(f"State FIPS required for {geographic_level}-level data")
        
        if state_fips and not self.validate_state_fips(state_fips):
            raise ValueError(f"Invalid state FIPS code: {state_fips}. Use get_available_state_fips() to see valid codes.")
        
        # Validate geographic level exists in our known types
        valid_levels = set(self.discovery.discover_boundary_types(year).keys())
        if geographic_level not in valid_levels:
            available = list(valid_levels)[:10]  # Show first 10
            raise ValueError(f"Invalid geographic level: {geographic_level}. Available for year {year}: {available}...")
    
    def _construct_tiger_url(self, year: int, geographic_level: str, 
                            state_fips: Optional[str]) -> Optional[str]:
        """Construct TIGER/Line download URL using discovery service."""
        return self.discovery.construct_download_url(year, geographic_level, state_fips)
    
    def _download_and_process_tiger(self, url: str, geographic_level: str) -> GeoDataFrame:
        """Download and process TIGER/Line shapefile using existing library functions.

        Raises:
            BoundaryDownloadError: If the file cannot be downloaded or is not a valid zip.
            BoundaryParseError: If the shapefile cannot be read by GeoPandas.
        """
        ctx: Dict[str, Any] = {"url": url, "geographic_level": geographic_level}
        zip_filename = None
        unzip_dir = None

        try:
            log.info(f"Downloading TIGER/Line data from: {url}")

            # Get user's download directory
            download_dir = get_download_directory()
            ensure_path_exists(download_dir)

            # Generate local path using existing function
            zip_filename = generate_local_path_from_url(url, download_dir)
            if not zip_filename:
                raise BoundaryDownloadError(
                    "Failed to generate local path for download",
                    context={**ctx, "error_code": "LOCAL_PATH_FAILED"},
                )

            ctx["local_path"] = str(zip_filename)

            # Download file using existing function with SSL fallback
            download_success = False
            try:
                download_success = download_file(url, zip_filename)
            except Exception as ssl_error:
                if "SSL" in str(ssl_error) or "certificate" in str(ssl_error).lower():
                    log.warning(f"SSL verification failed, retrying without verification: {ssl_error}")
                    download_success = download_file(url, zip_filename, verify_ssl=False)
                    if download_success:
                        log.info("Successfully downloaded without SSL verification")

            if not download_success:
                raise BoundaryDownloadError(
                    f"Failed to download TIGER/Line data from {url}",
                    context={**ctx, "error_code": "DOWNLOAD_FAILED"},
                )

            # Validate downloaded file is actually a zip (not an HTML challenge page)
            import zipfile
            zip_path = Path(zip_filename)
            if not zipfile.is_zipfile(zip_path):
                file_size = zip_path.stat().st_size if zip_path.exists() else 0
                log.warning(
                    f"Downloaded file is not a valid zip: {zip_path} "
                    f"({file_size} bytes) — removing and retrying"
                )
                zip_path.unlink(missing_ok=True)
                # Retry once — the first attempt may have been an anti-bot challenge
                download_success = download_file(url, zip_filename)
                if not download_success or not zipfile.is_zipfile(zip_path):
                    zip_path.unlink(missing_ok=True)
                    raise BoundaryDownloadError(
                        f"Downloaded file is not a valid zip after retry: {url}",
                        context={
                            **ctx,
                            "error_code": "INVALID_ZIP",
                            "file_size_bytes": file_size,
                        },
                    )
                log.info("Retry succeeded — valid zip file downloaded")

            # Unzip using existing function
            unzip_dir = unzip_file_to_directory(Path(zip_filename))
            if not unzip_dir:
                raise BoundaryDownloadError(
                    f"Failed to unzip TIGER/Line data from {zip_filename}",
                    context={**ctx, "error_code": "UNZIP_FAILED"},
                )

            # Find the shapefile
            shapefile_path = None
            for file_path in unzip_dir.rglob("*.shp"):
                shapefile_path = file_path
                break

            if not shapefile_path:
                raise BoundaryParseError(
                    f"No shapefile (.shp) found in extracted archive from {url}",
                    context={
                        **ctx,
                        "error_code": "NO_SHAPEFILE",
                        "extracted_files": [str(f.name) for f in unzip_dir.rglob("*") if f.is_file()][:20],
                    },
                )

            # Read with GeoPandas
            try:
                gdf = gpd.read_file(shapefile_path)
            except Exception as read_err:
                raise BoundaryParseError(
                    f"GeoPandas failed to read shapefile {shapefile_path}: {read_err}",
                    context={
                        **ctx,
                        "error_code": "GEOPANDAS_READ_FAILED",
                        "shapefile": str(shapefile_path),
                        "original_error": str(read_err),
                    },
                ) from read_err

            # Standardize columns
            gdf = self._standardize_census_columns(gdf, geographic_level)

            # Cleanup temporary files
            self._cleanup_temp_files(zip_filename, unzip_dir)

            log.info(f"Successfully processed {geographic_level} boundaries: {len(gdf)} features")
            return gdf

        except (BoundaryDownloadError, BoundaryParseError):
            # Cleanup on structured failure
            if zip_filename and unzip_dir:
                try:
                    self._cleanup_temp_files(zip_filename, unzip_dir)
                except Exception:
                    pass
            raise
        except Exception as e:
            # Cleanup on unexpected failure
            if zip_filename and unzip_dir:
                try:
                    self._cleanup_temp_files(zip_filename, unzip_dir)
                except Exception:
                    pass
            raise BoundaryDownloadError(
                f"Unexpected error downloading/processing TIGER data: {e}",
                context={**ctx, "error_code": "UNEXPECTED_DOWNLOAD_ERROR", "original_error": str(e)},
            ) from e
    
    def _standardize_census_columns(self, gdf: GeoDataFrame, geographic_level: str) -> GeoDataFrame:
        """Standardize Census column names and types."""
        # Convert column names to lowercase
        gdf.columns = [col.lower() for col in gdf.columns]
        
        # Ensure geometry column is properly named
        if 'geometry' not in gdf.columns and gdf.geometry.name:
            gdf = gdf.rename(columns={gdf.geometry.name: 'geometry'})
        
        # Add metadata columns
        gdf['census_year'] = gdf.get('year', None)
        gdf['geographic_level'] = geographic_level
        
        return gdf
    
    def _cleanup_temp_files(self, zip_filename: str, unzip_dir: Path) -> None:
        """Clean up temporary files after processing."""
        try:
            if os.path.exists(zip_filename):
                os.remove(zip_filename)
            if unzip_dir.exists():
                import shutil
                shutil.rmtree(unzip_dir)
        except Exception as e:
            log.warning(f"Failed to cleanup temporary files: {e}")


class GovernmentDataSource(SpatialDataSource):
    """Government data portal spatial data source."""
    
    def __init__(self, portal_url: str, api_key: Optional[str] = None):
        """
        Initialize government data source.
        
        Args:
            portal_url: Base URL for the government data portal
            api_key: API key if required
        """
        super().__init__(
            name="Government Data Portal",
            base_url=portal_url,
            api_key=api_key
        )
    
    def download_dataset(self, dataset_id: str, format_type: str = 'geojson') -> Optional[GeoDataFrame]:
        """
        Download a dataset from the government data portal.
        
        Args:
            dataset_id: Unique identifier for the dataset
            format_type: Preferred format (geojson, shapefile, kml)
            
        Returns:
            GeoDataFrame with spatial data or None if failed
        """
        try:
            # Construct download URL
            download_url = f"{self.base_url}/api/3/action/package_show?id={dataset_id}"
            
            # Get dataset metadata
            metadata = self._get_dataset_metadata(download_url)
            if not metadata:
                return None
            
            # Find best format
            resource_url = self._find_best_format(metadata, format_type)
            if not resource_url:
                return None
            
            # Download and process
            return self._download_and_process_dataset(resource_url, format_type)
            
        except SpatialDataError:
            raise
        except Exception as e:
            raise SpatialDataError(
                f"Failed to download dataset {dataset_id}: {e}"
            ) from e
    
    def _get_dataset_metadata(self, url: str) -> Optional[Dict[str, Any]]:
        """Get dataset metadata from the portal."""
        try:
            import requests
            
            response = requests.get(url, timeout=get_service_timeout('census_download'))
            if response.ok:
                data = response.json()
                return data.get('result', {})
            else:
                log.error(f"Failed to get metadata: HTTP {response.status_code}")
                return None
                
        except Exception as e:
            raise SpatialDataError(
                f"Error getting dataset metadata from {url}: {e}"
            ) from e
    
    def _find_best_format(self, metadata: Dict[str, Any], preferred_format: str) -> Optional[str]:
        """Find the best available format for download."""
        try:
            resources = metadata.get('resources', [])
            
            # Look for preferred format first
            for resource in resources:
                if resource.get('format', '').lower() == preferred_format.lower():
                    return resource.get('url')
            
            # Fall back to any available format
            for resource in resources:
                if resource.get('url'):
                    return resource.get('url')
            
            return None
            
        except Exception as e:
            raise SpatialDataError(
                f"Error finding format in dataset metadata: {e}"
            ) from e
    
    def _download_and_process_dataset(self, url: str, format_type: str) -> Optional[GeoDataFrame]:
        """Download and process the dataset."""
        try:
            # Get user's download directory
            download_dir = get_download_directory()
            ensure_path_exists(download_dir)
            
            # Generate local path
            local_filename = generate_local_path_from_url(url, download_dir)
            if not local_filename:
                return None
            
            # Download file
            download_success = download_file(url, local_filename)
            if not download_success:
                return None
            
            # Process based on format
            if format_type.lower() == 'geojson':
                gdf = gpd.read_file(local_filename)
            elif format_type.lower() == 'shapefile':
                # Handle zip files
                if str(local_filename).endswith('.zip'):
                    unzip_dir = unzip_file_to_directory(Path(local_filename))
                    if unzip_dir:
                        shp_files = list(unzip_dir.glob("*.shp"))
                        if shp_files:
                            gdf = gpd.read_file(shp_files[0])
                        else:
                            log.error("No shapefile found in zip")
                            return None
                    else:
                        return None
                else:
                    gdf = gpd.read_file(local_filename)
            else:
                log.error(f"Unsupported format: {format_type}")
                return None
            
            # Clean up
            try:
                os.remove(local_filename)
            except Exception:
                pass
            
            return gdf
            
        except Exception as e:
            raise SpatialDataError(
                f"Failed to process dataset from {url}: {e}"
            ) from e

class OpenStreetMapDataSource(SpatialDataSource):
    """OpenStreetMap data source using Overpass API."""
    
    def __init__(self):
        """Initialize OpenStreetMap data source."""
        super().__init__(
            name="OpenStreetMap",
            base_url="https://overpass-api.de/api/interpreter"
        )
    
    def download_osm_data(self, query: str, bbox: Optional[List[float]] = None) -> Optional[GeoDataFrame]:
        """
        Download data from OpenStreetMap using Overpass QL.
        
        Args:
            query: Overpass QL query string
            bbox: Bounding box [min_lat, min_lon, max_lat, max_lon]
            
        Returns:
            GeoDataFrame with OSM data or None if failed
        """
        try:
            # Construct Overpass query
            if bbox:
                bbox_str = f"[bbox:{bbox[1]},{bbox[0]},{bbox[3]},{bbox[2]}]"
                full_query = f"{query}{bbox_str};out geom;"
            else:
                full_query = f"{query};out geom;"
            
            # Make request
            import requests
            
            response = requests.get(
                self.base_url,
                params={'data': full_query},
                timeout=get_service_timeout('census_download')
            )
            
            if not response.ok:
                log.error(f"Overpass API error: HTTP {response.status_code}")
                return None
            
            # Parse response
            gdf = gpd.read_file(response.content, driver='GeoJSON')
            
            log.info(f"Downloaded {len(gdf)} features from OpenStreetMap")
            return gdf
            
        except Exception as e:
            raise SpatialDataError(
                f"Failed to download OSM data: {e}"
            ) from e

# Convenience functions for backward compatibility
def get_census_data(api_key: Optional[str] = None) -> CensusDataSource:
    """Get Census data source instance."""
    return CensusDataSource(api_key)

def get_census_boundaries(year: int = DEFAULT_CENSUS_YEAR, geographic_level: str = 'county',
                         state_fips: Optional[str] = None, state_identifier: Optional[str] = None) -> Optional[GeoDataFrame]:
    """
    Convenience function to get Census boundaries.

    .. deprecated::
        Use :func:`fetch_geographic_boundaries` (via CensusDataSource) for
        structured diagnostics via :class:`BoundaryFetchResult`.

    Args:
        year: Census year
        geographic_level: Geographic level (county, tract, etc.)
        state_fips: State FIPS code (e.g., '06' for California)
        state_identifier: State identifier - accepts FIPS code, abbreviation, or name
                         (e.g., '06', 'CA', 'California' all work)

    Note:
        Provide either state_fips OR state_identifier, not both.
        If both are provided, state_identifier takes precedence.

    Returns:
        GeoDataFrame with Census boundaries (filtered by state if specified)
    """
    warnings.warn(
        "get_census_boundaries() is deprecated. Use CensusDataSource().fetch_geographic_boundaries() "
        "for structured error reporting via BoundaryFetchResult.",
        DeprecationWarning,
        stacklevel=2,
    )
    source = CensusDataSource()

    # National-only boundary types (downloaded as national file, filtered post-download)
    national_only_types = {'state', 'county', 'cbsa', 'csa', 'metdiv', 'micro', 'necta',
                          'nectadiv', 'cnecta', 'aiannh', 'uac', 'uac10', 'uac20'}

    # Handle both parameter names for backward compatibility
    state_param = state_identifier or state_fips
    normalized_fips = None

    # If state_identifier is provided, normalize it to FIPS
    if state_param:
        try:
            # First normalize the input format (trim, uppercase, pad FIPS)
            normalized_input = normalize_state_input(state_param)
            # Then convert to FIPS code
            normalized_fips = normalize_state_identifier(normalized_input)
        except ValueError as e:
            log.error(f"Invalid state identifier: '{state_param}' - {e}")
            return None

    # Download boundaries
    # For national-only types, don't pass state_fips to the download function
    if geographic_level in national_only_types:
        gdf = source.get_geographic_boundaries(year, geographic_level, None)
    else:
        gdf = source.get_geographic_boundaries(year, geographic_level, normalized_fips)

    # Post-download filtering for national-only types when state is specified
    if gdf is not None and normalized_fips and geographic_level in national_only_types:
        # Filter by state FIPS column (statefp or STATEFP)
        fips_col = None
        for col in ['statefp', 'STATEFP', 'statefp20', 'STATEFP20', 'statefp10', 'STATEFP10']:
            if col in gdf.columns:
                fips_col = col
                break

        if fips_col:
            original_count = len(gdf)
            gdf = gdf[gdf[fips_col] == normalized_fips].copy()
            log.info(f"Filtered {geographic_level} from {original_count} to {len(gdf)} features for state {normalized_fips}")
        else:
            log.warning(f"No state FIPS column found in {geographic_level} data - cannot filter by state")

    return gdf

def download_osm_data(
    query: str,
    bbox: Optional[List[float]] = None,
    *,
    crs: str | None = None,
) -> Optional[GeoDataFrame]:
    """Convenience function to download OSM data.

    Args:
        query: OSM query string.
        bbox: Optional bounding box ``[west, south, east, north]``.
        crs: Output CRS. Defaults to :func:`~siege_utilities.geo.crs.get_default_crs`.
    """
    source = OpenStreetMapDataSource()
    gdf = source.download_osm_data(query, bbox)
    return reproject_if_needed(gdf, crs)

# Standalone convenience functions
def get_available_years(force_refresh: bool = False) -> List[int]:
    """Get available Census years."""
    return census_source.get_available_years(force_refresh)

def get_year_directory_contents(year: int) -> List[str]:
    """Get directory contents for a specific year."""
    return census_source.get_year_directory_contents(year)

def discover_boundary_types(year: int) -> List[str]:
    """Discover available boundary types for a year."""
    return census_source.discover_boundary_types(year)

def construct_download_url(year: int, geographic_level: str, state_fips: Optional[str] = None) -> str:
    """Construct download URL for Census data."""
    return census_source.construct_download_url(year, geographic_level, state_fips)

def validate_download_url(url: str) -> bool:
    """Validate a download URL."""
    return census_source.validate_download_url(url)

def get_optimal_year(geographic_level: str, preferred_year: Optional[int] = None) -> int:
    """Get optimal year for geographic level.

    Args:
        geographic_level: Geographic level (county, tract, etc.)
        preferred_year: Preferred year (defaults to current year if None)

    Returns:
        Best available year for the requested boundary type
    """
    from datetime import datetime
    year = preferred_year if preferred_year is not None else datetime.now().year
    return census_source.get_optimal_year(year, geographic_level)

def download_data(
    year: int,
    geographic_level: str,
    state_fips: Optional[str] = None,
    *,
    crs: str | None = None,
) -> Optional[GeoDataFrame]:
    """Download Census data.

    This is a convenience wrapper around get_geographic_boundaries().

    Args:
        year: Census year
        geographic_level: Geographic level (state, county, tract, etc.)
        state_fips: State FIPS code (required for tract, block_group, etc.)
        crs: Output CRS. Defaults to :func:`~siege_utilities.geo.crs.get_default_crs`.

    Returns:
        GeoDataFrame with boundaries in *crs*, or None if failed.
    """
    gdf = census_source.get_geographic_boundaries(year, geographic_level, state_fips)
    return reproject_if_needed(gdf, crs)

def get_geographic_boundaries(
    year: int = DEFAULT_CENSUS_YEAR,
    geographic_level: str = 'county',
    state_fips: Optional[str] = None,
    state_identifier: Optional[str] = None,
    *,
    crs: str | None = None,
) -> Optional[GeoDataFrame]:
    """Get geographic boundaries (legacy, returns None on failure).

    .. deprecated::
        Use :func:`fetch_geographic_boundaries` for structured diagnostics.

    Args:
        crs: Output CRS. Defaults to :func:`~siege_utilities.geo.crs.get_default_crs`.
    """
    gdf = census_source.get_geographic_boundaries(year, geographic_level, state_fips, state_identifier)
    return reproject_if_needed(gdf, crs)


def fetch_geographic_boundaries(
    year: int = DEFAULT_CENSUS_YEAR,
    geographic_level: str = 'county',
    state_fips: Optional[str] = None,
    congress_number: Optional[int] = None,
    *,
    crs: str | None = None,
) -> BoundaryFetchResult:
    """Get geographic boundaries with structured diagnostics.

    Returns a :class:`BoundaryFetchResult` instead of ``Optional[GeoDataFrame]``.

    Args:
        year: Census year
        geographic_level: Geographic level (state, county, tract, etc.)
        state_fips: State FIPS code (required for tract, block_group, etc.)
        congress_number: Congress number for congressional districts
        crs: Output CRS. Defaults to :func:`~siege_utilities.geo.crs.get_default_crs`.

    Returns:
        BoundaryFetchResult with .success, .geodataframe in *crs*, .error_stage, etc.
    """
    result = census_source.fetch_geographic_boundaries(
        year=year,
        geographic_level=geographic_level,
        state_fips=state_fips,
        congress_number=congress_number,
    )
    if result.success and result.geodataframe is not None:
        result.geodataframe = reproject_if_needed(result.geodataframe, crs)
    return result


def get_available_boundary_types(year: int) -> List[str]:
    """Get available boundary types for a year."""
    return census_source.get_available_boundary_types(year)

def refresh_discovery_cache() -> None:
    """Refresh the discovery cache."""
    return census_source.refresh_discovery_cache()

def get_unified_fips_data() -> Dict[str, Dict[str, Any]]:
    """Get unified FIPS data with state names and abbreviations."""
    return census_source.get_comprehensive_state_info()

def normalize_state_identifier_standalone(identifier: str) -> str:
    """Normalize state identifier - standalone function."""
    return census_source.normalize_state_identifier(identifier)

def normalize_state_input(raw_input: str) -> str:
    """
    Normalize state input to handle formatting and trivial errors.
    
    Args:
        raw_input: Raw state input (name, abbreviation, or FIPS)
    
    Returns:
        Normalized input (uppercase, trimmed, FIPS padded)
    
    Examples:
        normalize_state_input("  ca  ") -> "CA"
        normalize_state_input("CAlifornia") -> "CALIFORNIA" 
        normalize_state_input("6") -> "06"
    """
    if not raw_input:
        return raw_input
    
    # Trim whitespace and convert to uppercase
    normalized = raw_input.strip().upper()
    
    # Handle numeric FIPS codes (6 -> 06)
    if normalized.isdigit():
        return normalized.zfill(2)
    
    return normalized

def normalize_state_name(name: str) -> str:
    """
    Normalize state name input (e.g., "CAlifornia" -> "CALIFORNIA").
    
    Args:
        name: State name input
    
    Returns:
        Normalized state name in uppercase
    """
    return normalize_state_input(name)

def normalize_state_abbreviation(abbrev: str) -> str:
    """
    Normalize state abbreviation input (e.g., " ca " -> "CA").
    
    Args:
        abbrev: State abbreviation input
    
    Returns:
        Normalized state abbreviation in uppercase
    """
    return normalize_state_input(abbrev)

def normalize_fips_code(fips: Union[str, int]) -> str:
    """
    Normalize FIPS code input (e.g., 6 -> "06", "6" -> "06").
    
    Args:
        fips: FIPS code as string or integer
    
    Returns:
        Normalized FIPS code as 2-digit string
    """
    if isinstance(fips, int):
        fips = str(fips)
    
    normalized = str(fips).strip()
    if normalized.isdigit():
        return normalized.zfill(2)
    
    return normalized.upper()

def get_available_state_fips() -> List[str]:
    """Get available state FIPS codes."""
    return census_source.get_available_state_fips()

def get_state_abbreviations() -> List[str]:
    """Get state abbreviations."""
    return census_source.get_state_abbreviations()

def get_comprehensive_state_info() -> Dict[str, Dict[str, Any]]:
    """Get comprehensive state information."""
    return census_source.get_comprehensive_state_info()

def get_state_by_abbreviation(abbreviation: str) -> Optional[Dict[str, Any]]:
    """Get state info by abbreviation."""
    return census_source.get_state_by_abbreviation(abbreviation)

def get_state_by_name(name: str) -> Optional[Dict[str, Any]]:
    """Get state info by name."""
    return census_source.get_state_by_name(name)

def validate_state_fips(fips: str) -> bool:
    """Validate state FIPS code."""
    return census_source.validate_state_fips(fips)

def get_state_name(fips: str) -> Optional[str]:
    """Get state name from FIPS code."""
    return census_source.get_state_name(fips)

def get_state_abbreviation(fips: str) -> Optional[str]:
    """Get state abbreviation from FIPS code."""
    return census_source.get_state_abbreviation(fips)

def download_dataset(
    year: int,
    geographic_level: str,
    state_fips: Optional[str] = None,
    *,
    crs: str | None = None,
) -> Optional[GeoDataFrame]:
    """Download Census dataset.

    Args:
        year: Census year.
        geographic_level: Geographic level.
        state_fips: State FIPS code.
        crs: Output CRS. Defaults to :func:`~siege_utilities.geo.crs.get_default_crs`.
    """
    gdf = census_source.download_dataset(year, geographic_level, state_fips)
    return reproject_if_needed(gdf, crs)

# Global instances for easy access
census_source = CensusDataSource()  # Uses centralized Census timeout settings
government_source = GovernmentDataSource("https://data.gov")
osm_source = OpenStreetMapDataSource()

__all__ = [
    # Classes
    'SpatialDataSource',
    'CensusDataSource',
    'GovernmentDataSource',
    'OpenStreetMapDataSource',
    'CensusDirectoryDiscovery',
    # Census functions
    'get_census_data',
    'get_census_boundaries',
    'get_available_years',
    'get_year_directory_contents',
    'discover_boundary_types',
    'download_data',
    'get_geographic_boundaries',
    # State normalization
    'normalize_state_identifier',
    'normalize_state_input',
    'normalize_state_name',
    'normalize_state_abbreviation',
    'normalize_fips_code',
    'get_state_by_abbreviation',
    'get_state_by_name',
    # OSM
    'download_osm_data',
    # Global instances
    'census_source',
    'government_source',
    'osm_source'
]

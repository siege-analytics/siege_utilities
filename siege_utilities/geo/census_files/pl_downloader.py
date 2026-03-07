"""
PL 94-171 Redistricting Data File Downloader.

This module downloads and processes PL 94-171 redistricting data files
from the Census Bureau. Unlike the Census API, these files provide
block-level data essential for redistricting.

PL 94-171 File Structure:
- Files are distributed as pipe-delimited text files
- Each state has separate files for geographic header and data segments
- Data is organized by summary level (state, county, tract, block group, block)

Example usage:
    from siege_utilities.geo.census_files import get_pl_data, get_pl_blocks

    # Get all PL data for California at tract level
    df = get_pl_data(state='CA', geography='tract', year=2020)

    # Get block-level data for LA County
    blocks = get_pl_blocks(state='CA', county='037', year=2020)
"""

import logging
import zipfile
from datetime import datetime, timedelta
from io import StringIO
from pathlib import Path
from typing import Dict, List, Optional, Union

import pandas as pd
import requests

from ...config import (
    STATE_FIPS_CODES,
    FIPS_TO_STATE,
    normalize_state_identifier,
)

log = logging.getLogger(__name__)


# =============================================================================
# CONSTANTS
# =============================================================================

# PL 94-171 Base URLs
PL_2020_BASE_URL = "https://www2.census.gov/programs-surveys/decennial/2020/data/01-Redistricting_File--PL_94-171"
PL_2010_BASE_URL = "https://www2.census.gov/census_2010/01-Redistricting_File--PL_94-171"

# Cache settings
PL_CACHE_TIMEOUT_DAYS = 30
DEFAULT_CACHE_DIR = Path.home() / '.siege_utilities' / 'cache' / 'pl_files'

# Request timeout
PL_REQUEST_TIMEOUT = 300  # 5 minutes - files can be large

# Summary Level Codes
SUMMARY_LEVELS = {
    'nation': '010',
    'state': '040',
    'county': '050',
    'county_subdivision': '060',
    'place': '160',
    'tract': '140',
    'block_group': '150',
    'block': '750',
}

# PL File Types
PL_FILE_TYPES = {
    'geo': 'Geographic Header File',
    'pl1': 'File 1 - Race',
    'pl2': 'File 2 - Hispanic/Latino',
    'pl3': 'File 3 - Race 18+',
    'pl4': 'File 4 - Hispanic 18+',
}

# PL Table Definitions
PL_TABLES = {
    'P1': {
        'name': 'Race',
        'file': 'pl1',
        'columns': {
            'P1_001N': 'Total',
            'P1_002N': 'One Race',
            'P1_003N': 'White alone',
            'P1_004N': 'Black or African American alone',
            'P1_005N': 'American Indian and Alaska Native alone',
            'P1_006N': 'Asian alone',
            'P1_007N': 'Native Hawaiian and Other Pacific Islander alone',
            'P1_008N': 'Some Other Race alone',
            'P1_009N': 'Two or More Races',
            'P1_010N': 'Two Races including Some Other Race',
            'P1_011N': 'Two Races excluding Some Other Race, and three or more',
        }
    },
    'P2': {
        'name': 'Hispanic or Latino, and Not Hispanic or Latino by Race',
        'file': 'pl1',
        'columns': {
            'P2_001N': 'Total',
            'P2_002N': 'Hispanic or Latino',
            'P2_003N': 'Not Hispanic or Latino',
            'P2_004N': 'Not Hispanic: One Race',
            'P2_005N': 'Not Hispanic: White alone',
            'P2_006N': 'Not Hispanic: Black or African American alone',
            'P2_007N': 'Not Hispanic: American Indian and Alaska Native alone',
            'P2_008N': 'Not Hispanic: Asian alone',
            'P2_009N': 'Not Hispanic: Native Hawaiian and Other Pacific Islander alone',
            'P2_010N': 'Not Hispanic: Some Other Race alone',
            'P2_011N': 'Not Hispanic: Two or More Races',
        }
    },
    'P3': {
        'name': 'Race for the Population 18 Years and Over',
        'file': 'pl2',
        'columns': {
            'P3_001N': 'Total 18+',
            'P3_002N': 'One Race',
            'P3_003N': 'White alone',
            'P3_004N': 'Black or African American alone',
            'P3_005N': 'American Indian and Alaska Native alone',
            'P3_006N': 'Asian alone',
            'P3_007N': 'Native Hawaiian and Other Pacific Islander alone',
            'P3_008N': 'Some Other Race alone',
            'P3_009N': 'Two or More Races',
        }
    },
    'P4': {
        'name': 'Hispanic or Latino, and Not Hispanic by Race for 18+',
        'file': 'pl2',
        'columns': {
            'P4_001N': 'Total 18+',
            'P4_002N': 'Hispanic or Latino',
            'P4_003N': 'Not Hispanic or Latino',
            'P4_004N': 'Not Hispanic: One Race',
            'P4_005N': 'Not Hispanic: White alone',
            'P4_006N': 'Not Hispanic: Black or African American alone',
            'P4_007N': 'Not Hispanic: American Indian and Alaska Native alone',
            'P4_008N': 'Not Hispanic: Asian alone',
            'P4_009N': 'Not Hispanic: Native Hawaiian and Other Pacific Islander alone',
            'P4_010N': 'Not Hispanic: Some Other Race alone',
            'P4_011N': 'Not Hispanic: Two or More Races',
        }
    },
    'P5': {
        'name': 'Group Quarters Population by Major Group Quarters Type',
        'file': 'pl3',
        'columns': {
            'P5_001N': 'Total GQ Population',
            'P5_002N': 'Institutionalized',
            'P5_003N': 'Correctional facilities for adults',
            'P5_004N': 'Juvenile facilities',
            'P5_005N': 'Nursing facilities',
            'P5_006N': 'Other institutional',
            'P5_007N': 'Noninstitutionalized',
            'P5_008N': 'College/University housing',
            'P5_009N': 'Military quarters',
            'P5_010N': 'Other noninstitutional',
        }
    },
    'H1': {
        'name': 'Housing Occupancy',
        'file': 'pl1',
        'columns': {
            'H1_001N': 'Total Housing Units',
            'H1_002N': 'Occupied',
            'H1_003N': 'Vacant',
        }
    },
}

# 2020 PL File column specifications (simplified - actual specs are more complex)
# These are the key columns we need from the geographic header file
GEO_COLUMNS_2020 = [
    'FILEID', 'STUSAB', 'SUMLEV', 'GEOVAR', 'GEOCOMP', 'CHAESSION', 'CIFSN',
    'LOGRECNO', 'GEOID', 'GEOCODE', 'REGION', 'DIVISION', 'STATE', 'STATENS',
    'COUNTY', 'COUNTYCC', 'COUNTYNS', 'COUSUB', 'COUSUBCC', 'COUSUBNS',
    'SUBMCD', 'SUBMCDCC', 'SUBMCDNS', 'ESTATE', 'ESTATECC', 'ESTATENS',
    'CONCIT', 'CONCITCC', 'CONCITNS', 'PLACE', 'PLACECC', 'PLACENS',
    'TRACT', 'BLKGRP', 'BLOCK', 'AIESSION', 'AESSION'
]


# =============================================================================
# PL FILE DOWNLOADER
# =============================================================================

class PLFileDownloader:
    """
    Downloader for PL 94-171 redistricting data files.

    This class handles downloading, caching, and parsing PL files
    from the Census Bureau.
    """

    def __init__(
        self,
        cache_dir: Optional[Union[str, Path]] = None,
        timeout: int = PL_REQUEST_TIMEOUT
    ):
        """
        Initialize the PL file downloader.

        Args:
            cache_dir: Directory for caching files
            timeout: Request timeout in seconds
        """
        self.cache_dir = Path(cache_dir) if cache_dir else DEFAULT_CACHE_DIR
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.timeout = timeout

        log.info(f"Initialized PLFileDownloader (cache: {self.cache_dir})")

    def get_data(
        self,
        state: str,
        year: int = 2020,
        geography: str = 'tract',
        county: Optional[str] = None,
        tables: Optional[List[str]] = None
    ) -> pd.DataFrame:
        """
        Get PL 94-171 data for a state.

        Args:
            state: State name, abbreviation, or FIPS code
            year: Census year (2010 or 2020)
            geography: Geographic level ('state', 'county', 'tract', 'block_group', 'block')
            county: Optional county FIPS code to filter to
            tables: List of tables to include (e.g., ['P1', 'P2', 'H1']).
                   If None, includes all tables.

        Returns:
            DataFrame with PL data at specified geography level
        """
        # Normalize state
        state_fips = normalize_state_identifier(state)
        state_abbr = FIPS_TO_STATE.get(state_fips, state.upper())

        log.info(f"Getting PL {year} data for {state_abbr} at {geography} level")

        # Get summary level code
        geo_lower = geography.lower().replace(' ', '_').replace('-', '_')
        if geo_lower == 'blockgroup':
            geo_lower = 'block_group'

        if geo_lower not in SUMMARY_LEVELS:
            raise ValueError(
                f"Unknown geography level: '{geography}'. "
                f"Valid options: {list(SUMMARY_LEVELS.keys())}"
            )

        sumlev = SUMMARY_LEVELS[geo_lower]

        # Download and parse files
        geo_df = self._get_geographic_file(state_abbr, year)
        data_df = self._get_data_files(state_abbr, year, tables)

        # Merge geographic and data
        merged = geo_df.merge(data_df, on='LOGRECNO', how='inner')

        # Filter to requested summary level
        merged = merged[merged['SUMLEV'] == sumlev].copy()

        # Filter to county if specified
        if county:
            county = str(county).zfill(3)
            merged = merged[merged['COUNTY'] == county].copy()

        # Construct proper GEOID
        merged = self._construct_geoid(merged, geo_lower)

        log.info(f"Retrieved {len(merged)} {geography} records")
        return merged

    def _get_geographic_file(self, state_abbr: str, year: int) -> pd.DataFrame:
        """Download and parse the geographic header file."""
        cache_file = self.cache_dir / f"geo_{state_abbr}_{year}.parquet"

        if self._is_cache_valid(cache_file):
            log.debug(f"Loading geo file from cache: {cache_file.name}")
            return pd.read_parquet(cache_file)

        # Download
        url = self._build_geo_url(state_abbr, year)
        log.info(f"Downloading geographic file: {url}")

        df = self._download_and_parse_geo(url, year)

        # Cache
        df.to_parquet(cache_file, index=False)
        return df

    def _get_data_files(
        self,
        state_abbr: str,
        year: int,
        tables: Optional[List[str]] = None
    ) -> pd.DataFrame:
        """Download and parse data segment files."""
        if tables is None:
            tables = list(PL_TABLES.keys())

        # Determine which file segments we need
        files_needed = set()
        for table in tables:
            if table in PL_TABLES:
                files_needed.add(PL_TABLES[table]['file'])

        all_data = None

        for file_type in files_needed:
            cache_file = self.cache_dir / f"data_{file_type}_{state_abbr}_{year}.parquet"

            if self._is_cache_valid(cache_file):
                log.debug(f"Loading {file_type} from cache")
                df = pd.read_parquet(cache_file)
            else:
                url = self._build_data_url(state_abbr, year, file_type)
                log.info(f"Downloading {file_type}: {url}")
                df = self._download_and_parse_data(url, year, file_type)
                df.to_parquet(cache_file, index=False)

            if all_data is None:
                all_data = df
            else:
                # Merge on LOGRECNO
                all_data = all_data.merge(df, on='LOGRECNO', how='outer')

        return all_data

    def _build_geo_url(self, state_abbr: str, year: int) -> str:
        """Build URL for geographic header file."""
        if year == 2020:
            # 2020 format: state_name/ca2020.pl.zip (for California)
            state_lower = state_abbr.lower()
            state_name = self._get_state_name_for_url(state_abbr)
            return f"{PL_2020_BASE_URL}/{state_name}/{state_lower}2020.pl.zip"
        elif year == 2010:
            state_name = self._get_state_name_for_url(state_abbr)
            state_lower = state_abbr.lower()
            return f"{PL_2010_BASE_URL}/{state_name}/{state_lower}2010.pl.zip"
        else:
            raise ValueError(f"PL files only available for 2010 and 2020, not {year}")

    def _build_data_url(self, state_abbr: str, year: int, file_type: str) -> str:
        """Build URL for data segment file."""
        # Data files are included in the same zip as geo
        return self._build_geo_url(state_abbr, year)

    def _get_state_name_for_url(self, state_abbr: str) -> str:
        """Get state name formatted for Census URL."""
        # Map abbreviation to full name with underscores
        state_names = {
            'AL': 'Alabama', 'AK': 'Alaska', 'AZ': 'Arizona', 'AR': 'Arkansas',
            'CA': 'California', 'CO': 'Colorado', 'CT': 'Connecticut', 'DE': 'Delaware',
            'DC': 'District_of_Columbia', 'FL': 'Florida', 'GA': 'Georgia', 'HI': 'Hawaii',
            'ID': 'Idaho', 'IL': 'Illinois', 'IN': 'Indiana', 'IA': 'Iowa',
            'KS': 'Kansas', 'KY': 'Kentucky', 'LA': 'Louisiana', 'ME': 'Maine',
            'MD': 'Maryland', 'MA': 'Massachusetts', 'MI': 'Michigan', 'MN': 'Minnesota',
            'MS': 'Mississippi', 'MO': 'Missouri', 'MT': 'Montana', 'NE': 'Nebraska',
            'NV': 'Nevada', 'NH': 'New_Hampshire', 'NJ': 'New_Jersey', 'NM': 'New_Mexico',
            'NY': 'New_York', 'NC': 'North_Carolina', 'ND': 'North_Dakota', 'OH': 'Ohio',
            'OK': 'Oklahoma', 'OR': 'Oregon', 'PA': 'Pennsylvania', 'RI': 'Rhode_Island',
            'SC': 'South_Carolina', 'SD': 'South_Dakota', 'TN': 'Tennessee', 'TX': 'Texas',
            'UT': 'Utah', 'VT': 'Vermont', 'VA': 'Virginia', 'WA': 'Washington',
            'WV': 'West_Virginia', 'WI': 'Wisconsin', 'WY': 'Wyoming',
            'PR': 'Puerto_Rico',
        }
        return state_names.get(state_abbr.upper(), state_abbr)

    def _download_and_parse_geo(self, url: str, year: int) -> pd.DataFrame:
        """Download and parse geographic header file."""
        # Download zip file
        response = requests.get(url, timeout=self.timeout)
        response.raise_for_status()

        # Extract geo file from zip
        import io
        with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
            # Find the geo file (ends with 'geo2020.pl' or similar)
            geo_filename = None
            for name in zf.namelist():
                if 'geo' in name.lower() and name.endswith('.pl'):
                    geo_filename = name
                    break

            if geo_filename is None:
                # Try alternate naming
                for name in zf.namelist():
                    if name.endswith('geo.pl') or 'geo20' in name.lower():
                        geo_filename = name
                        break

            if geo_filename is None:
                raise ValueError(f"Could not find geographic file in {url}")

            with zf.open(geo_filename) as f:
                content = f.read().decode('latin-1')

        # Parse fixed-width geo file (2020 format)
        # The geo file is pipe-delimited in 2020
        df = pd.read_csv(
            StringIO(content),
            sep='|',
            dtype=str,
            header=None,
            low_memory=False
        )

        # Assign column names (subset of important columns)
        # Full geo file has many columns; we extract key ones
        if len(df.columns) >= 10:
            df.columns = list(range(len(df.columns)))
            # Key column positions for 2020:
            # 1=STUSAB, 2=SUMLEV, 4=LOGRECNO, 7=GEOID (varies)
            df = df.rename(columns={
                0: 'FILEID',
                1: 'STUSAB',
                2: 'SUMLEV',
                3: 'GEOVAR',
                4: 'GEOCOMP',
                5: 'CHAESSION',
                6: 'CIFSN',
                7: 'LOGRECNO',
            })

            # Extract GEOID components based on position
            if len(df.columns) > 20:
                df['STATE'] = df.iloc[:, 11] if len(df.columns) > 11 else ''
                df['COUNTY'] = df.iloc[:, 14] if len(df.columns) > 14 else ''
                df['TRACT'] = df.iloc[:, 32] if len(df.columns) > 32 else ''
                df['BLKGRP'] = df.iloc[:, 33] if len(df.columns) > 33 else ''
                df['BLOCK'] = df.iloc[:, 34] if len(df.columns) > 34 else ''

        return df

    def _download_and_parse_data(
        self,
        url: str,
        year: int,
        file_type: str
    ) -> pd.DataFrame:
        """Download and parse data segment file."""
        # Data files are in the same zip
        response = requests.get(url, timeout=self.timeout)
        response.raise_for_status()

        import io
        with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
            # Find the data file
            file_num = {'pl1': '1', 'pl2': '2', 'pl3': '3', 'pl4': '4'}.get(file_type, '1')
            data_filename = None

            for name in zf.namelist():
                # Look for files like ca000012020.pl (segment 1) or ca000022020.pl (segment 2)
                if f'0000{file_num}' in name and name.endswith('.pl'):
                    data_filename = name
                    break

            if data_filename is None:
                log.warning(f"Data file {file_type} not found, returning empty DataFrame")
                return pd.DataFrame({'LOGRECNO': []})

            with zf.open(data_filename) as f:
                content = f.read().decode('latin-1')

        # Parse pipe-delimited data file
        df = pd.read_csv(
            StringIO(content),
            sep='|',
            dtype=str,
            header=None,
            low_memory=False
        )

        # Assign column names based on file type
        df = self._assign_data_columns(df, file_type, year)

        return df

    def _assign_data_columns(
        self,
        df: pd.DataFrame,
        file_type: str,
        year: int
    ) -> pd.DataFrame:
        """Assign column names to data segment."""
        # Column positions vary by file segment
        # File 1 (pl1): P1 (race) and P2 (Hispanic) tables
        # File 2 (pl2): P3 (race 18+) and P4 (Hispanic 18+) tables
        # File 3 (pl3): P5 (group quarters) and H1 (housing) tables

        if file_type == 'pl1':
            # File 1 has: FILEID, STUSAB, CHAESSION, CIFSN, LOGRECNO, then data
            base_cols = ['FILEID', 'STUSAB', 'CHAESSION', 'CIFSN', 'LOGRECNO']
            # P1 has 71 cells, P2 has 73 cells, H1 has 3 cells
            p1_cols = [f'P1_{str(i).zfill(3)}N' for i in range(1, 72)]
            p2_cols = [f'P2_{str(i).zfill(3)}N' for i in range(1, 74)]
            h1_cols = ['H1_001N', 'H1_002N', 'H1_003N']
            all_cols = base_cols + p1_cols + p2_cols + h1_cols

        elif file_type == 'pl2':
            base_cols = ['FILEID', 'STUSAB', 'CHAESSION', 'CIFSN', 'LOGRECNO']
            p3_cols = [f'P3_{str(i).zfill(3)}N' for i in range(1, 72)]
            p4_cols = [f'P4_{str(i).zfill(3)}N' for i in range(1, 74)]
            all_cols = base_cols + p3_cols + p4_cols

        elif file_type == 'pl3':
            base_cols = ['FILEID', 'STUSAB', 'CHAESSION', 'CIFSN', 'LOGRECNO']
            p5_cols = [f'P5_{str(i).zfill(3)}N' for i in range(1, 11)]
            all_cols = base_cols + p5_cols

        else:
            return df

        # Only assign if we have enough columns
        if len(df.columns) >= len(all_cols):
            df.columns = all_cols[:len(df.columns)]
        else:
            # Partial assignment
            df.columns = all_cols[:len(df.columns)]

        return df

    def _construct_geoid(self, df: pd.DataFrame, geography: str) -> pd.DataFrame:
        """Construct proper GEOID column."""
        df = df.copy()

        if geography == 'state':
            df['GEOID'] = df['STATE'].str.zfill(2)
        elif geography == 'county':
            df['GEOID'] = df['STATE'].str.zfill(2) + df['COUNTY'].str.zfill(3)
        elif geography == 'tract':
            df['GEOID'] = (
                df['STATE'].str.zfill(2) +
                df['COUNTY'].str.zfill(3) +
                df['TRACT'].str.zfill(6)
            )
        elif geography == 'block_group':
            df['GEOID'] = (
                df['STATE'].str.zfill(2) +
                df['COUNTY'].str.zfill(3) +
                df['TRACT'].str.zfill(6) +
                df['BLKGRP'].str.zfill(1)
            )
        elif geography == 'block':
            df['GEOID'] = (
                df['STATE'].str.zfill(2) +
                df['COUNTY'].str.zfill(3) +
                df['TRACT'].str.zfill(6) +
                df['BLOCK'].str.zfill(4)
            )

        return df

    def _is_cache_valid(self, cache_file: Path) -> bool:
        """Check if cache file exists and is not expired."""
        if not cache_file.exists():
            return False

        file_mtime = datetime.fromtimestamp(cache_file.stat().st_mtime)
        age = datetime.now() - file_mtime

        if age > timedelta(days=PL_CACHE_TIMEOUT_DAYS):
            return False

        return True

    def clear_cache(self) -> int:
        """Clear all cached PL files."""
        deleted = 0
        for f in self.cache_dir.glob('*.parquet'):
            f.unlink()
            deleted += 1
        log.info(f"Cleared {deleted} cached PL files")
        return deleted


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

_default_downloader: Optional[PLFileDownloader] = None


def _get_downloader() -> PLFileDownloader:
    """Get or create default downloader."""
    global _default_downloader
    if _default_downloader is None:
        _default_downloader = PLFileDownloader()
    return _default_downloader


def get_pl_data(
    state: str,
    year: int = 2020,
    geography: str = 'tract',
    county: Optional[str] = None,
    tables: Optional[List[str]] = None
) -> pd.DataFrame:
    """
    Get PL 94-171 redistricting data.

    Args:
        state: State name, abbreviation, or FIPS code
        year: Census year (2010 or 2020)
        geography: Geographic level
        county: Optional county FIPS filter
        tables: Tables to include (default: all)

    Returns:
        DataFrame with PL data

    Example:
        # Get California tract data
        df = get_pl_data(state='CA', geography='tract')

        # Get LA County block data
        df = get_pl_data(state='CA', geography='block', county='037')
    """
    return _get_downloader().get_data(
        state=state,
        year=year,
        geography=geography,
        county=county,
        tables=tables
    )


def get_pl_blocks(
    state: str,
    county: Optional[str] = None,
    year: int = 2020,
    tables: Optional[List[str]] = None
) -> pd.DataFrame:
    """
    Get block-level PL 94-171 data.

    This is the primary function for redistricting analysis as it
    provides the finest geographic detail available.

    Args:
        state: State identifier
        county: Optional county FIPS to filter
        year: Census year
        tables: Tables to include

    Returns:
        DataFrame with block-level PL data
    """
    return get_pl_data(
        state=state,
        year=year,
        geography='block',
        county=county,
        tables=tables
    )


def get_pl_tracts(
    state: str,
    county: Optional[str] = None,
    year: int = 2020,
    tables: Optional[List[str]] = None
) -> pd.DataFrame:
    """
    Get tract-level PL 94-171 data.

    Args:
        state: State identifier
        county: Optional county FIPS filter
        year: Census year
        tables: Tables to include

    Returns:
        DataFrame with tract-level PL data
    """
    return get_pl_data(
        state=state,
        year=year,
        geography='tract',
        county=county,
        tables=tables
    )


def download_pl_file(
    state: str,
    year: int = 2020,
    output_dir: Optional[Union[str, Path]] = None
) -> Path:
    """
    Download raw PL 94-171 zip file.

    Args:
        state: State identifier
        year: Census year
        output_dir: Directory to save file

    Returns:
        Path to downloaded file
    """
    downloader = _get_downloader()
    state_fips = normalize_state_identifier(state)
    state_abbr = FIPS_TO_STATE.get(state_fips, state.upper())

    url = downloader._build_geo_url(state_abbr, year)

    output_dir = Path(output_dir) if output_dir else downloader.cache_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / f"{state_abbr.lower()}{year}.pl.zip"

    log.info(f"Downloading {url} to {output_file}")
    response = requests.get(url, timeout=PL_REQUEST_TIMEOUT)
    response.raise_for_status()

    output_file.write_bytes(response.content)
    log.info(f"Downloaded {output_file.stat().st_size / 1024 / 1024:.1f} MB")

    return output_file


def list_available_pl_files(year: int = 2020) -> List[Dict]:
    """
    List available PL 94-171 files.

    Args:
        year: Census year

    Returns:
        List of available states with file info
    """
    available = []
    for abbr in sorted(STATE_FIPS_CODES.keys()):
        fips = STATE_FIPS_CODES[abbr]
        available.append({
            'state_abbr': abbr,
            'state_fips': fips,
            'year': year,
            'tables': list(PL_TABLES.keys()),
        })
    return available

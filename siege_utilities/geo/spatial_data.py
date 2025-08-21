"""
Modern spatial data sources for siege_utilities.
Provides clean, type-safe access to Census, Government, and OpenStreetMap data.
"""

import logging
import pandas as pd
import geopandas as gpd
from pathlib import Path
from typing import Dict, Any, Optional, List, Union
import json
import tempfile
import os
from urllib.parse import urljoin, urlparse
import time
from datetime import datetime, timedelta
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

# Get logger for this module
log = logging.getLogger(__name__)

# Type aliases
FilePath = Union[str, Path]
GeoDataFrame = gpd.GeoDataFrame


class CensusDirectoryDiscovery:
    """Discovers available Census TIGER/Line data dynamically."""
    
    def __init__(self, timeout: int = 30):
        self.base_url = "https://www2.census.gov/geo/tiger"
        self.timeout = timeout
        self.cache = {}
        self.cache_timeout = 3600  # 1 hour
        
    def get_available_years(self, force_refresh: bool = False) -> List[int]:
        """Get list of available Census years."""
        cache_key = "available_years"
        
        if not force_refresh and cache_key in self.cache:
            cache_time, data = self.cache[cache_key]
            if time.time() - cache_time < self.cache_timeout:
                return data
        
        try:
            # Try with SSL verification first (increased timeout)
            response = requests.get(self.base_url, timeout=30)
            response.raise_for_status()
            
            # Parse HTML to find TIGER and GENZ year directories
            soup = BeautifulSoup(response.content, 'html.parser')
            # Handle both TIGER and GENZ patterns, plus other variations
            year_patterns = [
                re.compile(r'TIGER(\d{4})'),
                re.compile(r'GENZ(\d{4})'),
                re.compile(r'TGRGDB(\d{2})'),  # TGRGDB13, TGRGDB14, etc.
                re.compile(r'TGRGPKG(\d{2})')  # TGRGPKG24, TGRGPKG25, etc.
            ]
            
            years = []
            for link in soup.find_all('a'):
                href = link.get('href', '')
                
                # Try each pattern
                for pattern in year_patterns:
                    match = pattern.search(href)
                    if match:
                        if 'TGRGDB' in href or 'TGRGPKG' in href:
                            # Convert 2-digit years to 4-digit (assume 20xx)
                            year = 2000 + int(match.group(1))
                        else:
                            year = int(match.group(1))
                        
                        if 1990 <= year <= datetime.now().year + 1:
                            years.append(year)
                        break
            
            # Remove duplicates and sort
            years = sorted(list(set(years)))
            self.cache[cache_key] = (time.time(), years)
            return years
            
        except requests.exceptions.SSLError:
            log.warning("SSL verification failed, trying without verification...")
            try:
                # Fallback: try without SSL verification (increased timeout)
                response = requests.get(self.base_url, timeout=30, verify=False)
                response.raise_for_status()
                
                # Parse HTML to find TIGER and GENZ year directories
                soup = BeautifulSoup(response.content, 'html.parser')
                year_patterns = [
                    re.compile(r'TIGER(\d{4})'),
                    re.compile(r'GENZ(\d{4})'),
                    re.compile(r'TGRGDB(\d{2})'),
                    re.compile(r'TGRGPKG(\d{2})')
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
                
                years = sorted(list(set(years)))
                self.cache[cache_key] = (time.time(), years)
                return years
                
            except Exception as e:
                log.error(f"Failed to discover available years (with SSL bypass): {e}")
                log.info("Using fallback years (2010-present)")
                # Fallback to known years
                return list(range(2010, datetime.now().year + 1))
                
        except Exception as e:
            log.error(f"Failed to discover available years: {e}")
            log.info("Using fallback years (2010-present)")
            # Fallback to known years
            return list(range(2010, datetime.now().year + 1))
    
    def get_year_directory_contents(self, year: int, force_refresh: bool = False) -> List[str]:
        """Get contents of a specific TIGER year directory."""
        cache_key = f"year_{year}_contents"
        
        if not force_refresh and cache_key in self.cache:
            cache_time, data = self.cache[cache_key]
            if time.time() - cache_time < self.cache_timeout:
                return data
        
        try:
            year_url = f"{self.base_url}/TIGER{year}/"
            response = requests.get(year_url, timeout=30)
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
                response = requests.get(year_url, timeout=30, verify=False)
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
                log.error(f"Failed to get contents for year {year} (with SSL bypass): {e}")
                return []
                
        except Exception as e:
            log.error(f"Failed to get contents for year {year}: {e}")
            return []
    
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
            'ZCTA': 'zcta',  # Alternative naming
            
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
            'CD117': 'cd117', # 117th Congress
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
    
    def construct_download_url(self, year: int, boundary_type: str, state_fips: Optional[str] = None, 
                              congress_number: Optional[int] = None) -> Optional[str]:
        """Construct download URL based on discovered directory structure."""
        try:
            # Get available boundary types for this year
            available_types = self.discover_boundary_types(year)
            
            if boundary_type not in available_types:
                log.warning(f"Boundary type '{boundary_type}' not available for year {year}")
                return None
            
            directory = available_types[boundary_type]
            base_url = f"{self.base_url}/TIGER{year}/{directory}"
            
            # Construct filename based on boundary type and parameters
            if boundary_type in ['state', 'county']:
                filename = f"tl_{year}_us_{boundary_type}.zip"
            elif boundary_type.startswith('cd') and len(boundary_type) > 2:
                # Handle specific congress numbers (cd108, cd109, etc.)
                congress_num = boundary_type[2:]
                filename = f"tl_{year}_us_cd{congress_num}.zip"
            elif boundary_type == 'cd' and congress_number:
                filename = f"tl_{year}_us_cd{congress_number}.zip"
            elif boundary_type in ['tabblock20', 'tabblock10']:
                if not state_fips:
                    log.error(f"State FIPS required for {boundary_type}")
                    return None
                filename = f"tl_{year}_{state_fips}_{boundary_type}.zip"
            elif boundary_type in ['sldu', 'sldl']:
                if not state_fips:
                    log.error(f"State FIPS required for {boundary_type}")
                    return None
                filename = f"tl_{year}_{state_fips}_{boundary_type}.zip"
            elif boundary_type in ['tract', 'block_group', 'block']:
                if not state_fips:
                    log.error(f"State FIPS required for {boundary_type}")
                    return None
                filename = f"tl_{year}_{state_fips}_{boundary_type}.zip"
            elif boundary_type in ['cbsa', 'csa', 'metdiv', 'micro', 'necta', 'nectadiv', 'cnecta']:
                # Metropolitan and statistical areas are national
                filename = f"tl_{year}_us_{boundary_type}.zip"
            elif boundary_type in ['aiannh', 'aitsce', 'ttract', 'tbg']:
                # Tribal boundaries are national
                filename = f"tl_{year}_us_{boundary_type}.zip"
            elif boundary_type in ['elsd', 'scsd', 'unsd']:
                # School districts are national
                filename = f"tl_{year}_us_{boundary_type}.zip"
            elif boundary_type in ['uac', 'uac20']:
                # Urban areas are national
                filename = f"tl_{year}_us_{boundary_type}.zip"
            elif boundary_type in ['vtd', 'vtd20']:
                # Voting districts are national
                filename = f"tl_{year}_us_{boundary_type}.zip"
            elif boundary_type in ['place', 'zcta', 'anrc', 'concity', 'submcd', 'cousub']:
                # These can be either national or state-specific
                if state_fips:
                    filename = f"tl_{year}_{state_fips}_{boundary_type}.zip"
                else:
                    filename = f"tl_{year}_us_{boundary_type}.zip"
            else:
                # Generic pattern for other types
                if state_fips:
                    filename = f"tl_{year}_{state_fips}_{boundary_type}.zip"
                else:
                    filename = f"tl_{year}_us_{boundary_type}.zip"
            
            return f"{base_url}/{filename}"
            
        except Exception as e:
            log.error(f"Failed to construct URL for {boundary_type} in year {year}: {e}")
            return None
    
    def validate_download_url(self, url: str) -> bool:
        """Check if a download URL is actually accessible."""
        try:
            response = requests.head(url, timeout=30)
            return response.status_code == 200
        except requests.exceptions.SSLError:
            log.debug(f"SSL verification failed for {url}, trying without verification...")
            try:
                response = requests.head(url, timeout=30, verify=False)
                return response.status_code == 200
            except Exception as e:
                log.debug(f"URL validation failed for {url} (with SSL bypass): {e}")
                return False
        except Exception as e:
            log.debug(f"URL validation failed for {url}: {e}")
            return False
    
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
    """Enhanced Census data source with dynamic discovery."""
    
    def __init__(self, api_key: Optional[str] = None, timeout: int = 30):
        super().__init__("Census Bureau", "https://www2.census.gov/geo/tiger", api_key)
        
        # Initialize discovery service with configurable timeout
        self.discovery = CensusDirectoryDiscovery(timeout=timeout)
        
        # Get available years dynamically
        self.available_years = self.discovery.get_available_years()
        
        # Geographic levels that require state FIPS
        self.state_required_levels = ['tract', 'block_group', 'block', 'tabblock20', 'sldu', 'sldl']
        
        # Geographic levels that don't require state FIPS
        self.national_levels = ['nation', 'state', 'county', 'place', 'zcta', 'cd']
        
        log.info(f"Initialized Census data source with {len(self.available_years)} available years")
    
    def get_geographic_boundaries(self, 
                                year: int = 2020,
                                geographic_level: str = 'county',
                                state_fips: Optional[str] = None,
                                county_fips: Optional[str] = None,
                                congress_number: Optional[int] = None) -> Optional[GeoDataFrame]:
        """
        Download geographic boundaries from Census TIGER/Line files with dynamic discovery.
        
        Args:
            year: Census year (will find closest available if not available)
            geographic_level: Geographic level (state, county, tract, etc.)
            state_fips: State FIPS code for filtering (required for some levels)
            county_fips: County FIPS code for filtering
            congress_number: Congress number for congressional districts
            
        Returns:
            GeoDataFrame with boundaries or None if failed
        """
        try:
            # Validate parameters
            self._validate_census_parameters(year, geographic_level, state_fips)
            
            # Find optimal year (closest available to requested)
            optimal_year = self.discovery.get_optimal_year(year, geographic_level)
            
            # Construct URL using discovery service
            url = self.discovery.construct_download_url(
                optimal_year, geographic_level, state_fips, congress_number
            )
            
            if not url:
                log.error(f"Failed to construct URL for {geographic_level} in year {optimal_year}")
                return None
            
            # Validate URL before attempting download
            if not self.discovery.validate_download_url(url):
                log.error(f"Download URL not accessible: {url}")
                return None
            
            log.info(f"Downloading {geographic_level} boundaries for year {optimal_year}")
            
            # Download and process using existing library functions
            return self._download_and_process_tiger(url, geographic_level)
            
        except ValueError as e:
            log.error(f"Invalid parameters: {e}")
            return None
        except Exception as e:
            log.error(f"Failed to download Census boundaries: {e}")
            return None
    
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
        return {
            '01': 'Alabama', '02': 'Alaska', '04': 'Arizona', '05': 'Arkansas',
            '06': 'California', '08': 'Colorado', '09': 'Connecticut', '10': 'Delaware',
            '11': 'District of Columbia', '12': 'Florida', '13': 'Georgia', '15': 'Hawaii',
            '16': 'Idaho', '17': 'Illinois', '18': 'Indiana', '19': 'Iowa',
            '20': 'Kansas', '21': 'Kentucky', '22': 'Louisiana', '23': 'Maine',
            '24': 'Maryland', '25': 'Massachusetts', '26': 'Michigan', '27': 'Minnesota',
            '28': 'Mississippi', '29': 'Missouri', '30': 'Montana', '31': 'Nebraska',
            '32': 'Nevada', '33': 'New Hampshire', '34': 'New Jersey', '35': 'New Mexico',
            '36': 'New York', '37': 'North Carolina', '38': 'North Dakota', '39': 'Ohio',
            '40': 'Oklahoma', '41': 'Oregon', '42': 'Pennsylvania', '44': 'Rhode Island',
            '45': 'South Carolina', '46': 'South Dakota', '47': 'Tennessee', '48': 'Texas',
            '49': 'Utah', '50': 'Vermont', '51': 'Virginia', '53': 'Washington',
            '54': 'West Virginia', '55': 'Wisconsin', '56': 'Wyoming',
            '60': 'American Samoa', '66': 'Guam', '69': 'Northern Mariana Islands',
            '72': 'Puerto Rico', '74': 'U.S. Minor Outlying Islands', '78': 'U.S. Virgin Islands'
        }
    
    def get_state_abbreviations(self) -> Dict[str, str]:
        """Get mapping of state FIPS codes to state abbreviations."""
        return {
            '01': 'AL', '02': 'AK', '04': 'AZ', '05': 'AR',
            '06': 'CA', '08': 'CO', '09': 'CT', '10': 'DE',
            '11': 'DC', '12': 'FL', '13': 'GA', '15': 'HI',
            '16': 'ID', '17': 'IL', '18': 'IN', '19': 'IA',
            '20': 'KS', '21': 'KY', '22': 'LA', '23': 'ME',
            '24': 'MD', '25': 'MA', '26': 'MI', '27': 'MN',
            '28': 'MS', '29': 'MO', '30': 'MT', '31': 'NE',
            '32': 'NV', '33': 'NH', '34': 'NJ', '35': 'NM',
            '36': 'NY', '37': 'NC', '38': 'ND', '39': 'OH',
            '40': 'OK', '41': 'OR', '42': 'PA', '44': 'RI',
            '45': 'SC', '46': 'SD', '47': 'TN', '48': 'TX',
            '49': 'UT', '50': 'VT', '51': 'VA', '53': 'WA',
            '54': 'WV', '55': 'WI', '56': 'WY',
            '60': 'AS', '66': 'GU', '69': 'MP',
            '72': 'PR', '74': 'UM', '78': 'VI'
        }
    
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
    
    def _download_and_process_tiger(self, url: str, geographic_level: str) -> Optional[GeoDataFrame]:
        """Download and process TIGER/Line shapefile using existing library functions."""
        try:
            log.info(f"Downloading TIGER/Line data from: {url}")
            
            # Get user's download directory
            download_dir = get_download_directory()
            ensure_path_exists(download_dir)
            
            # Generate local path using existing function
            zip_filename = generate_local_path_from_url(url, download_dir)
            if not zip_filename:
                log.error("Failed to generate local path for download")
                return None
            
            # Download file using existing function with SSL fallback
            try:
                download_success = download_file(url, zip_filename)
            except Exception as ssl_error:
                if "SSL" in str(ssl_error) or "certificate" in str(ssl_error).lower():
                    log.warning(f"SSL verification failed, retrying without verification: {ssl_error}")
                    # Retry without SSL verification using the download_file function
                    download_success = download_file(url, zip_filename, verify_ssl=False)
                    if download_success:
                        log.info("Successfully downloaded without SSL verification")
                    else:
                        log.error("Download failed even without SSL verification")
                else:
                    download_success = False
            
            if not download_success:
                log.error("Failed to download TIGER/Line data")
                return None
            
            # Unzip using existing function
            unzip_dir = unzip_file_to_directory(Path(zip_filename))
            if not unzip_dir:
                log.error("Failed to unzip TIGER/Line data")
                return None
            
            # Find the shapefile
            shapefile_path = None
            for file_path in unzip_dir.rglob("*.shp"):
                shapefile_path = file_path
                break
            
            if not shapefile_path:
                log.error("No shapefile found in downloaded data")
                return None
            
            # Read with GeoPandas
            gdf = gpd.read_file(shapefile_path)
            
            # Standardize columns
            gdf = self._standardize_census_columns(gdf, geographic_level)
            
            # Cleanup temporary files
            self._cleanup_temp_files(zip_filename, unzip_dir)
            
            log.info(f"Successfully processed {geographic_level} boundaries: {len(gdf)} features")
            return gdf
            
        except Exception as e:
            log.error(f"Failed to download and process TIGER/Line data: {e}")
            # Cleanup on failure
            try:
                self._cleanup_temp_files(zip_filename, unzip_dir)
            except:
                pass
            return None
    
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
            
        except Exception as e:
            log.error(f"Failed to download dataset {dataset_id}: {e}")
            return None
    
    def _get_dataset_metadata(self, url: str) -> Optional[Dict[str, Any]]:
        """Get dataset metadata from the portal."""
        try:
            import requests
            
            response = requests.get(url, timeout=30)
            if response.ok:
                data = response.json()
                return data.get('result', {})
            else:
                log.error(f"Failed to get metadata: HTTP {response.status_code}")
                return None
                
        except Exception as e:
            log.error(f"Error getting dataset metadata: {e}")
            return None
    
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
            log.error(f"Error finding format: {e}")
            return None
    
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
            log.error(f"Failed to process dataset: {e}")
            return None

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
                timeout=60
            )
            
            if not response.ok:
                log.error(f"Overpass API error: HTTP {response.status_code}")
                return None
            
            # Parse response
            gdf = gpd.read_file(response.content, driver='GeoJSON')
            
            log.info(f"Downloaded {len(gdf)} features from OpenStreetMap")
            return gdf
            
        except Exception as e:
            log.error(f"Failed to download OSM data: {e}")
            return None

# Convenience functions for backward compatibility
def get_census_data(api_key: Optional[str] = None) -> CensusDataSource:
    """Get Census data source instance."""
    return CensusDataSource(api_key)

def get_census_boundaries(year: int = 2020, geographic_level: str = 'county',
                         state_fips: Optional[str] = None) -> Optional[GeoDataFrame]:
    """Convenience function to get Census boundaries."""
    source = CensusDataSource()
    return source.get_geographic_boundaries(year, geographic_level, state_fips)

def download_osm_data(query: str, bbox: Optional[List[float]] = None) -> Optional[GeoDataFrame]:
    """Convenience function to download OSM data."""
    source = OpenStreetMapDataSource()
    return source.download_osm_data(query, bbox)

# Global instances for easy access
census_source = CensusDataSource(timeout=45)  # Longer timeout for better reliability
government_source = GovernmentDataSource("https://data.gov")
osm_source = OpenStreetMapDataSource()

__all__ = [
    'SpatialDataSource',
    'CensusDataSource', 
    'GovernmentDataSource',
    'OpenStreetMapDataSource',
    'CensusDirectoryDiscovery',
    'get_census_data',
    'get_census_boundaries',
    'download_osm_data',
    'census_source',
    'government_source',
    'osm_source'
]

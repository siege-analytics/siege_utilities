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

# Import existing library functions
from ..files.remote import download_file, generate_local_path_from_url
from ..files.paths import unzip_file_to_directory, ensure_path_exists
from ..config.user_config import get_user_config, get_download_directory

# Get logger for this module
log = logging.getLogger(__name__)

# Type aliases
FilePath = Union[str, Path]
GeoDataFrame = gpd.GeoDataFrame

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
            self.user_config = None
    
    def download_data(self, **kwargs) -> Optional[GeoDataFrame]:
        """
        Download spatial data from the source.
        
        Args:
            **kwargs: Source-specific parameters
            
        Returns:
            GeoDataFrame with spatial data or None if failed
        """
        raise NotImplementedError("Subclasses must implement download_data")

class CensusDataSource(SpatialDataSource):
    """Census Bureau spatial data source using existing library functions."""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Census data source.
        
        Args:
            api_key: Census API key (optional but recommended)
        """
        super().__init__(
            name="Census Bureau",
            base_url="https://api.census.gov/data",
            api_key=api_key
        )
        
        # Census geographic levels with FIPS codes
        self.geographic_levels = {
            'nation': '010',
            'state': '040',
            'county': '050',
            'tract': '140',
            'block_group': '150',
            'block': '750',
            'place': '160',
            'zcta': '860'
        }
        
        # Available years for TIGER/Line files
        self.available_years = list(range(2010, datetime.now().year + 1))
        
        # TIGER/Line file structure
        self.tiger_file_structure = {
            'nation': 'ADDRFEAT/tl_{year}_us_addrfeat.zip',
            'state': 'STATE/tl_{year}_us_state.zip',
            'county': 'COUNTY/tl_{year}_us_county.zip',
            'tract': 'TRACT/tl_{year}_{state_fips}_tract.zip',
            'block_group': 'BG/tl_{year}_{state_fips}_bg.zip',
            'block': 'TABBLOCK/tl_{year}_{state_fips}_tabblock.zip',
            'place': 'PLACE/tl_{year}_us_place.zip',
            'zcta': 'ZCTA5/tl_{year}_us_zcta510.zip'
        }
    
    def get_geographic_boundaries(self, 
                                year: int = 2020,
                                geographic_level: str = 'county',
                                state_fips: Optional[str] = None,
                                county_fips: Optional[str] = None) -> Optional[GeoDataFrame]:
        """
        Download geographic boundaries from Census TIGER/Line files.
        
        Args:
            year: Census year (2010-2023)
            geographic_level: Geographic level (nation, state, county, tract, etc.)
            state_fips: State FIPS code for filtering (required for tract/block levels)
            county_fips: County FIPS code for filtering
            
        Returns:
            GeoDataFrame with boundaries or None if failed
            
        Raises:
            ValueError: If invalid parameters are provided
        """
        try:
            # Validate parameters
            self._validate_census_parameters(year, geographic_level, state_fips)
            
            # Construct TIGER/Line URL
            url = self._construct_tiger_url(year, geographic_level, state_fips)
            if not url:
                return None
            
            # Download and process using existing library functions
            return self._download_and_process_tiger(url, geographic_level)
            
        except ValueError as e:
            log.error(f"Invalid parameters: {e}")
            return None
        except Exception as e:
            log.error(f"Failed to download Census boundaries: {e}")
            return None
    
    def _validate_census_parameters(self, year: int, geographic_level: str, 
                                  state_fips: Optional[str]) -> None:
        """Validate Census API parameters."""
        if year not in self.available_years:
            raise ValueError(f"Year {year} not available. Available years: {self.available_years}")
        
        if geographic_level not in self.geographic_levels:
            raise ValueError(f"Invalid geographic level: {geographic_level}")
        
        # Check if state FIPS is required
        if geographic_level in ['tract', 'block_group', 'block'] and not state_fips:
            raise ValueError(f"State FIPS required for {geographic_level}-level data")
    
    def _construct_tiger_url(self, year: int, geographic_level: str, 
                            state_fips: Optional[str]) -> Optional[str]:
        """Construct TIGER/Line download URL."""
        try:
            base_url = f"https://www2.census.gov/geo/tiger/TIGER{year}"
            
            if geographic_level in ['tract', 'block_group', 'block']:
                # These levels require state FIPS
                template = self.tiger_file_structure[geographic_level]
                return f"{base_url}/{template.format(year=year, state_fips=state_fips)}"
            else:
                # Nation, state, county, place, zcta levels
                template = self.tiger_file_structure[geographic_level]
                return f"{base_url}/{template.format(year=year)}"
                
        except KeyError:
            log.error(f"Unsupported geographic level: {geographic_level}")
            return None
    
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
            
            # Download file using existing function
            download_success = download_file(url, zip_filename)
            if not download_success:
                log.error("Failed to download TIGER/Line data")
                return None
            
            # Unzip using existing function
            unzip_dir = unzip_file_to_directory(Path(zip_filename))
            if not unzip_dir:
                log.error("Failed to unzip TIGER/Line data")
                return None
            
            # Find shapefile
            shp_files = list(Path(unzip_dir).glob("*.shp"))
            if not shp_files:
                log.error("No shapefile found in downloaded data")
                return None
            
            # Read shapefile
            log.info(f"Reading shapefile: {shp_files[0]}")
            gdf = gpd.read_file(shp_files[0])
            
            # Standardize column names
            gdf = self._standardize_census_columns(gdf, geographic_level)
            
            # Clean up temporary files
            self._cleanup_temp_files(zip_filename, unzip_dir)
            
            log.info(f"Successfully processed {len(gdf)} features from {geographic_level} data")
            return gdf
                
        except Exception as e:
            log.error(f"Failed to process TIGER/Line data: {e}")
            return None
    
    def _standardize_census_columns(self, gdf: GeoDataFrame, geographic_level: str) -> GeoDataFrame:
        """Standardize column names for consistency across geographic levels."""
        try:
            # Create a copy to avoid modifying the original
            standardized = gdf.copy()
            
            # Common column mappings
            column_mappings = {
                'GEOID': 'geoid',
                'NAME': 'name',
                'ALAND': 'aland',
                'AWATER': 'awater',
                'INTPTLAT': 'latitude',
                'INTPTLON': 'longitude'
            }
            
            # Apply mappings
            for old_name, new_name in column_mappings.items():
                if old_name in standardized.columns:
                    standardized = standardized.rename(columns={old_name: new_name})
            
            # Add metadata
            standardized.attrs['source'] = 'Census Bureau TIGER/Line'
            standardized.attrs['geographic_level'] = geographic_level
            standardized.attrs['processed_at'] = datetime.now().isoformat()
            
            return standardized
            
        except Exception as e:
            log.warning(f"Failed to standardize columns: {e}")
            return gdf
    
    def _cleanup_temp_files(self, zip_filename: str, unzip_dir: Path) -> None:
        """Clean up temporary downloaded and extracted files."""
        try:
            # Remove zip file
            if os.path.exists(zip_filename):
                os.remove(zip_filename)
                log.debug(f"Removed temporary zip file: {zip_filename}")
            
            # Remove extracted directory
            if unzip_dir.exists():
                import shutil
                shutil.rmtree(unzip_dir)
                log.debug(f"Removed temporary directory: {unzip_dir}")
                
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
census_source = CensusDataSource()
government_source = GovernmentDataSource("https://data.gov")
osm_source = OpenStreetMapDataSource()

__all__ = [
    'SpatialDataSource',
    'CensusDataSource', 
    'GovernmentDataSource',
    'OpenStreetMapDataSource',
    'get_census_data',
    'get_census_boundaries',
    'download_osm_data',
    'census_source',
    'government_source',
    'osm_source'
]

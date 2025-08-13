"""
Spatial data sources and download functions for siege_utilities.
Provides access to Census, government, and other spatial data sources.
"""

import logging
import requests
import pandas as pd
import geopandas as gpd
from pathlib import Path
from typing import Dict, Any, Optional, List, Union
import json
import zipfile
import tempfile
import os
from urllib.parse import urljoin, urlparse
import time
from datetime import datetime, timedelta

log = logging.getLogger(__name__)

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
        self.session = requests.Session()
        
        if api_key:
            self.session.headers.update({'Authorization': f'Bearer {api_key}'})
    
    def download_data(self, **kwargs) -> Optional[gpd.GeoDataFrame]:
        """
        Download spatial data from the source.
        
        Args:
            **kwargs: Source-specific parameters
            
        Returns:
            GeoDataFrame with spatial data or None if failed
        """
        raise NotImplementedError("Subclasses must implement download_data")

class CensusDataSource(SpatialDataSource):
    """Census Bureau spatial data source."""
    
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
        
        # Census geographic levels
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
        
        # Available years
        self.available_years = list(range(2010, datetime.now().year + 1))
    
    def get_geographic_boundaries(self, 
                                year: int = 2020,
                                geographic_level: str = 'county',
                                state_fips: Optional[str] = None,
                                county_fips: Optional[str] = None) -> Optional[gpd.GeoDataFrame]:
        """
        Download geographic boundaries from Census TIGER/Line files.
        
        Args:
            year: Census year (2010-2023)
            geographic_level: Geographic level (nation, state, county, tract, etc.)
            state_fips: State FIPS code for filtering
            county_fips: County FIPS code for filtering
            
        Returns:
            GeoDataFrame with boundaries
        """
        try:
            # Validate year
            if year not in self.available_years:
                log.error(f"Year {year} not available. Available years: {self.available_years}")
                return None
            
            # Validate geographic level
            if geographic_level not in self.geographic_levels:
                log.error(f"Invalid geographic level: {geographic_level}")
                return None
            
            # Construct TIGER/Line URL
            tiger_url = f"https://www2.census.gov/geo/tiger/TIGER{year}"
            
            if geographic_level == 'nation':
                url = f"{tiger_url}/ADDRFEAT/tl_{year}_us_addrfeat.zip"
            elif geographic_level == 'state':
                url = f"{tiger_url}/STATE/tl_{year}_us_state.zip"
            elif geographic_level == 'county':
                url = f"{tiger_url}/COUNTY/tl_{year}_us_county.zip"
            elif geographic_level == 'tract':
                if not state_fips:
                    log.error("State FIPS required for tract-level data")
                    return None
                url = f"{tiger_url}/TRACT/tl_{year}_{state_fips}_tract.zip"
            elif geographic_level == 'block_group':
                if not state_fips:
                    log.error("State FIPS required for block group-level data")
                    return None
                url = f"{tiger_url}/BG/tl_{year}_{state_fips}_bg.zip"
            elif geographic_level == 'place':
                url = f"{tiger_url}/PLACE/tl_{year}_us_place.zip"
            elif geographic_level == 'zcta':
                url = f"{tiger_url}/ZCTA5/tl_{year}_us_zcta510.zip"
            else:
                log.error(f"Unsupported geographic level: {geographic_level}")
                return None
            
            # Download and process
            return self._download_and_process_tiger(url, geographic_level)
            
        except Exception as e:
            log.error(f"Failed to download Census boundaries: {e}")
            return None
    
    def _download_and_process_tiger(self, url: str, geographic_level: str) -> Optional[gpd.GeoDataFrame]:
        """Download and process TIGER/Line shapefile."""
        try:
            # Download zip file
            response = self.session.get(url)
            response.raise_for_status()
            
            # Create temporary directory
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                zip_path = temp_path / "data.zip"
                
                # Save zip file
                with open(zip_path, 'wb') as f:
                    f.write(response.content)
                
                # Extract zip file
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(temp_path)
                
                # Find shapefile
                shp_files = list(temp_path.glob("*.shp"))
                if not shp_files:
                    log.error("No shapefile found in downloaded data")
                    return None
                
                # Read shapefile
                gdf = gpd.read_file(shp_files[0])
                
                # Standardize column names
                gdf = self._standardize_census_columns(gdf, geographic_level)
                
                return gdf
                
        except Exception as e:
            log.error(f"Failed to process TIGER/Line data: {e}")
            return None
    
    def _standardize_census_columns(self, gdf: gpd.GeoDataFrame, geographic_level: str) -> gpd.GeoDataFrame:
        """Standardize Census column names."""
        # Common column mappings
        column_mappings = {
            'GEOID': 'geoid',
            'NAME': 'name',
            'ALAND': 'land_area',
            'AWATER': 'water_area',
            'STATEFP': 'state_fips',
            'COUNTYFP': 'county_fips',
            'TRACTCE': 'tract_code',
            'BLKGRPCE': 'block_group_code',
            'PLACEFP': 'place_fips',
            'ZCTA5CE10': 'zcta_code'
        }
        
        # Rename columns
        for old_name, new_name in column_mappings.items():
            if old_name in gdf.columns:
                gdf = gdf.rename(columns={old_name: new_name})
        
        # Add metadata
        gdf.attrs['source'] = 'Census Bureau TIGER/Line'
        gdf.attrs['geographic_level'] = geographic_level
        gdf.attrs['download_date'] = datetime.now().isoformat()
        
        return gdf
    
    def get_census_data(self, 
                        year: int = 2020,
                        dataset: str = 'acs/acs5',
                        variables: List[str] = None,
                        geographic_level: str = 'county',
                        state_fips: Optional[str] = None,
                        county_fips: Optional[str] = None) -> Optional[pd.DataFrame]:
        """
        Download Census demographic data.
        
        Args:
            year: Census year
            dataset: Dataset name (e.g., 'acs/acs5', 'dec/pl')
            variables: List of variable codes to download
            geographic_level: Geographic level
            state_fips: State FIPS code
            county_fips: County FIPS code
            
        Returns:
            DataFrame with Census data
        """
        try:
            if not self.api_key:
                log.warning("No API key provided. Census API has rate limits without key.")
            
            # Default variables if none specified
            if not variables:
                variables = ['B01003_001E']  # Total population
            
            # Construct API URL
            url = f"{self.base_url}/{year}/{dataset}"
            
            # Geographic parameters
            params = {
                'get': ','.join(variables),
                'for': geographic_level,
                'key': self.api_key
            }
            
            if state_fips:
                params['in'] = f'state:{state_fips}'
            if county_fips:
                params['in'] = f'state:{state_fips}&county:{county_fips}'
            
            # Make request
            response = self.session.get(url, params=params)
            response.raise_for_status()
            
            # Parse response
            data = response.json()
            if not data:
                log.error("No data returned from Census API")
                return None
            
            # Convert to DataFrame
            df = pd.DataFrame(data[1:], columns=data[0])
            
            # Standardize column names
            df = self._standardize_census_data_columns(df, variables)
            
            return df
            
        except Exception as e:
            log.error(f"Failed to download Census data: {e}")
            return None
    
    def _standardize_census_data_columns(self, df: pd.DataFrame, variables: List[str]) -> pd.DataFrame:
        """Standardize Census data column names."""
        # Variable name mappings
        variable_names = {
            'B01003_001E': 'total_population',
            'B19013_001E': 'median_household_income',
            'B25077_001E': 'median_home_value',
            'B08303_001E': 'commute_time',
            'B15003_001E': 'educational_attainment'
        }
        
        # Rename variable columns
        for var in variables:
            if var in df.columns and var in variable_names:
                df = df.rename(columns={var: variable_names[var]})
        
        # Standardize geographic columns
        geographic_mappings = {
            'state': 'state_fips',
            'county': 'county_fips',
            'tract': 'tract_code',
            'block group': 'block_group_code',
            'place': 'place_fips',
            'zcta': 'zcta_code'
        }
        
        for old_name, new_name in geographic_mappings.items():
            if old_name in df.columns:
                df = df.rename(columns={old_name: new_name})
        
        return df

class GovernmentDataSource(SpatialDataSource):
    """Government spatial data sources."""
    
    def __init__(self):
        """Initialize government data source."""
        super().__init__(
            name="Government Sources",
            base_url="https://data.gov"
        )
        
        # Government data catalogs
        self.data_catalogs = {
            'data_gov': 'https://catalog.data.gov/dataset',
            'usgs': 'https://www.usgs.gov/programs/national-geospatial-program/national-map',
            'noaa': 'https://www.ngdc.noaa.gov/',
            'epa': 'https://www.epa.gov/environmental-geospatial-data'
        }
    
    def search_datasets(self, 
                       query: str,
                       source: str = 'data_gov',
                       category: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Search for government datasets.
        
        Args:
            query: Search query
            source: Data source to search
            category: Category filter
            
        Returns:
            List of dataset information
        """
        try:
            # This is a simplified search - in practice, you'd use the actual APIs
            log.info(f"Searching {source} for: {query}")
            
            # Placeholder for actual search implementation
            return []
            
        except Exception as e:
            log.error(f"Failed to search datasets: {e}")
            return []
    
    def download_dataset(self, dataset_url: str) -> Optional[gpd.GeoDataFrame]:
        """
        Download a government dataset.
        
        Args:
            dataset_url: URL to the dataset
            
        Returns:
            GeoDataFrame with spatial data
        """
        try:
            # Download dataset based on URL type
            if dataset_url.endswith('.zip'):
                return self._download_zip_dataset(dataset_url)
            elif dataset_url.endswith('.shp'):
                return self._download_shapefile(dataset_url)
            elif dataset_url.endswith('.geojson'):
                return self._download_geojson(dataset_url)
            else:
                log.warning(f"Unsupported file format: {dataset_url}")
                return None
                
        except Exception as e:
            log.error(f"Failed to download dataset: {e}")
            return None
    
    def _download_zip_dataset(self, url: str) -> Optional[gpd.GeoDataFrame]:
        """Download and extract zip dataset."""
        try:
            response = self.session.get(url)
            response.raise_for_status()
            
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                zip_path = temp_path / "dataset.zip"
                
                with open(zip_path, 'wb') as f:
                    f.write(response.content)
                
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(temp_path)
                
                # Find spatial files
                shp_files = list(temp_path.glob("*.shp"))
                geojson_files = list(temp_path.glob("*.geojson"))
                
                if shp_files:
                    return gpd.read_file(shp_files[0])
                elif geojson_files:
                    return gpd.read_file(geojson_files[0])
                else:
                    log.error("No spatial files found in zip")
                    return None
                    
        except Exception as e:
            log.error(f"Failed to download zip dataset: {e}")
            return None
    
    def _download_shapefile(self, url: str) -> Optional[gpd.GeoDataFrame]:
        """Download shapefile directly."""
        try:
            return gpd.read_file(url)
        except Exception as e:
            log.error(f"Failed to download shapefile: {e}")
            return None
    
    def _download_geojson(self, url: str) -> Optional[gpd.GeoDataFrame]:
        """Download GeoJSON directly."""
        try:
            return gpd.read_file(url)
        except Exception as e:
            log.error(f"Failed to download GeoJSON: {e}")
            return None

class OpenStreetMapDataSource(SpatialDataSource):
    """OpenStreetMap data source."""
    
    def __init__(self):
        """Initialize OpenStreetMap data source."""
        super().__init__(
            name="OpenStreetMap",
            base_url="https://overpass-api.de/api"
        )
    
    def download_osm_data(self, 
                          query: str,
                          bbox: Optional[List[float]] = None) -> Optional[gpd.GeoDataFrame]:
        """
        Download data from OpenStreetMap using Overpass API.
        
        Args:
            query: Overpass QL query
            bbox: Bounding box [min_lon, min_lat, max_lon, max_lat]
            
        Returns:
            GeoDataFrame with OSM data
        """
        try:
            # Construct Overpass query
            if bbox:
                bbox_str = f"({bbox[1]},{bbox[0]},{bbox[3]},{bbox[2]})"
                full_query = f"[out:json][timeout:25];{query}{bbox_str};out geom;"
            else:
                full_query = f"[out:json][timeout:25];{query};out geom;"
            
            # Make request
            response = self.session.post(
                f"{self.base_url}/interpreter",
                data={'data': full_query}
            )
            response.raise_for_status()
            
            # Parse response
            data = response.json()
            
            # Convert to GeoDataFrame
            return self._osm_to_geodataframe(data)
            
        except Exception as e:
            log.error(f"Failed to download OSM data: {e}")
            return None
    
    def _osm_to_geodataframe(self, osm_data: Dict[str, Any]) -> Optional[gpd.GeoDataFrame]:
        """Convert OSM data to GeoDataFrame."""
        try:
            features = []
            
            for element in osm_data.get('elements', []):
                if element['type'] == 'way' and 'geometry' in element:
                    # Create polygon/linestring from way
                    coords = [(point['lon'], point['lat']) for point in element['geometry']]
                    
                    from shapely.geometry import LineString, Polygon
                    
                    if len(coords) > 3 and coords[0] == coords[-1]:
                        # Closed way - create polygon
                        geom = Polygon(coords)
                    else:
                        # Open way - create linestring
                        geom = LineString(coords)
                    
                    feature = {
                        'geometry': geom,
                        'id': element['id'],
                        'type': element['type'],
                        'tags': element.get('tags', {})
                    }
                    features.append(feature)
            
            if not features:
                log.warning("No features found in OSM data")
                return None
            
            # Create GeoDataFrame
            gdf = gpd.GeoDataFrame(features)
            gdf.set_crs(epsg=4326, inplace=True)
            
            return gdf
            
        except Exception as e:
            log.error(f"Failed to convert OSM data: {e}")
            return None

# Global instances
census_source = CensusDataSource()
government_source = GovernmentDataSource()
osm_source = OpenStreetMapDataSource()

def get_census_data(year: int = 2020,
                   dataset: str = 'acs/acs5',
                   variables: List[str] = None,
                   geographic_level: str = 'county',
                   state_fips: Optional[str] = None,
                   county_fips: Optional[str] = None) -> Optional[pd.DataFrame]:
    """Get Census data."""
    return census_source.get_census_data(
        year=year,
        dataset=dataset,
        variables=variables,
        geographic_level=geographic_level,
        state_fips=state_fips,
        county_fips=county_fips
    )

def get_census_boundaries(year: int = 2020,
                         geographic_level: str = 'county',
                         state_fips: Optional[str] = None,
                         county_fips: Optional[str] = None) -> Optional[gpd.GeoDataFrame]:
    """Get Census geographic boundaries."""
    return census_source.get_geographic_boundaries(
        year=year,
        geographic_level=geographic_level,
        state_fips=state_fips,
        county_fips=county_fips
    )

def download_osm_data(query: str, bbox: Optional[List[float]] = None) -> Optional[gpd.GeoDataFrame]:
    """Download OpenStreetMap data."""
    return osm_source.download_osm_data(query=query, bbox=bbox)

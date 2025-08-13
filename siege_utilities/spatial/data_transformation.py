"""
Spatial data transformation and database integration for siege_utilities.
Provides functions to transform spatial data formats and integrate with PostGIS and DuckDB.
"""

import logging
import pandas as pd
import geopandas as gpd
from pathlib import Path
from typing import Dict, Any, Optional, List, Union, Tuple
import json
import tempfile
import os
from shapely.geometry import shape, mapping
from shapely.wkt import loads, dumps
import psycopg2
from psycopg2.extras import RealDictCursor
import duckdb
import sqlite3
from sqlalchemy import create_engine, text
import fiona
import pyproj
from pyproj import CRS, Transformer

log = logging.getLogger(__name__)

class SpatialDataTransformer:
    """Handles spatial data format transformations and conversions."""
    
    def __init__(self):
        """Initialize the spatial data transformer."""
        self.supported_formats = {
            'input': ['shp', 'geojson', 'gpkg', 'kml', 'gml', 'wkt', 'wkb'],
            'output': ['shp', 'geojson', 'gpkg', 'kml', 'gml', 'wkt', 'wkb', 'postgis', 'duckdb']
        }
    
    def convert_format(self, 
                      input_data: Union[str, Path, gpd.GeoDataFrame],
                      output_format: str,
                      output_path: Optional[str] = None,
                      **kwargs) -> Union[gpd.GeoDataFrame, str, bool]:
        """
        Convert spatial data between different formats.
        
        Args:
            input_data: Input data (file path or GeoDataFrame)
            output_format: Desired output format
            output_path: Output file path (optional)
            **kwargs: Format-specific options
            
        Returns:
            Converted data or file path
        """
        try:
            # Load input data
            if isinstance(input_data, (str, Path)):
                gdf = gpd.read_file(input_data)
            elif isinstance(input_data, gpd.GeoDataFrame):
                gdf = input_data.copy()
            else:
                raise ValueError("Input data must be file path or GeoDataFrame")
            
            # Validate output format
            if output_format not in self.supported_formats['output']:
                raise ValueError(f"Unsupported output format: {output_format}")
            
            # Convert based on format
            if output_format in ['shp', 'geojson', 'gpkg', 'kml', 'gml']:
                return self._convert_to_file_format(gdf, output_format, output_path, **kwargs)
            elif output_format == 'wkt':
                return self._convert_to_wkt(gdf, **kwargs)
            elif output_format == 'wkb':
                return self._convert_to_wkb(gdf, **kwargs)
            elif output_format == 'postgis':
                return self._convert_to_postgis(gdf, **kwargs)
            elif output_format == 'duckdb':
                return self._convert_to_duckdb(gdf, **kwargs)
            else:
                raise ValueError(f"Unsupported output format: {output_format}")
                
        except Exception as e:
            log.error(f"Failed to convert spatial data: {e}")
            return None
    
    def _convert_to_file_format(self, 
                               gdf: gpd.GeoDataFrame,
                               format_type: str,
                               output_path: Optional[str],
                               **kwargs) -> str:
        """Convert to file-based format."""
        if not output_path:
            # Generate output path
            output_path = f"converted_data.{format_type}"
        
        try:
            if format_type == 'shp':
                gdf.to_file(output_path, driver='ESRI Shapefile', **kwargs)
            elif format_type == 'geojson':
                gdf.to_file(output_path, driver='GeoJSON', **kwargs)
            elif format_type == 'gpkg':
                gdf.to_file(output_path, driver='GPKG', **kwargs)
            elif format_type == 'kml':
                gdf.to_file(output_path, driver='KML', **kwargs)
            elif format_type == 'gml':
                gdf.to_file(output_path, driver='GML', **kwargs)
            
            log.info(f"Successfully converted to {format_type}: {output_path}")
            return output_path
            
        except Exception as e:
            log.error(f"Failed to convert to {format_type}: {e}")
            return None
    
    def _convert_to_wkt(self, gdf: gpd.GeoDataFrame, **kwargs) -> pd.DataFrame:
        """Convert geometries to WKT format."""
        try:
            # Convert to WKT
            wkt_df = gdf.copy()
            wkt_df['geometry_wkt'] = wkt_df.geometry.apply(lambda geom: dumps(geom))
            
            # Drop geometry column
            wkt_df = wkt_df.drop(columns=['geometry'])
            
            return wkt_df
            
        except Exception as e:
            log.error(f"Failed to convert to WKT: {e}")
            return None
    
    def _convert_to_wkb(self, gdf: gpd.GeoDataFrame, **kwargs) -> pd.DataFrame:
        """Convert geometries to WKB format."""
        try:
            # Convert to WKB
            wkb_df = gdf.copy()
            wkb_df['geometry_wkb'] = wkb_df.geometry.apply(lambda geom: geom.wkb)
            
            # Drop geometry column
            wkb_df = wkb_df.drop(columns=['geometry'])
            
            return wkb_df
            
        except Exception as e:
            log.error(f"Failed to convert to WKB: {e}")
            return None
    
    def _convert_to_postgis(self, gdf: gpd.GeoDataFrame, **kwargs) -> bool:
        """Convert to PostGIS format and upload to database."""
        try:
            # Get database connection parameters
            connection_string = kwargs.get('connection_string')
            table_name = kwargs.get('table_name', 'spatial_data')
            schema = kwargs.get('schema', 'public')
            
            if not connection_string:
                raise ValueError("PostGIS connection string required")
            
            # Create SQLAlchemy engine
            engine = create_engine(connection_string)
            
            # Upload to PostGIS
            gdf.to_postgis(
                name=table_name,
                con=engine,
                schema=schema,
                if_exists=kwargs.get('if_exists', 'replace'),
                index=kwargs.get('index', False)
            )
            
            log.info(f"Successfully uploaded to PostGIS table: {schema}.{table_name}")
            return True
            
        except Exception as e:
            log.error(f"Failed to convert to PostGIS: {e}")
            return False
    
    def _convert_to_duckdb(self, gdf: gpd.GeoDataFrame, **kwargs) -> bool:
        """Convert to DuckDB format and save to database."""
        try:
            # Get database parameters
            db_path = kwargs.get('db_path', ':memory:')
            table_name = kwargs.get('table_name', 'spatial_data')
            
            # Connect to DuckDB
            con = duckdb.connect(db_path)
            
            # Convert to pandas DataFrame with WKT geometries
            df = gdf.copy()
            df['geometry_wkt'] = df.geometry.apply(lambda geom: dumps(geom))
            df = df.drop(columns=['geometry'])
            
            # Upload to DuckDB
            con.execute(f"CREATE TABLE IF NOT EXISTS {table_name} AS SELECT * FROM df")
            
            log.info(f"Successfully uploaded to DuckDB table: {table_name}")
            return True
            
        except Exception as e:
            log.error(f"Failed to convert to DuckDB: {e}")
            return False
    
    def transform_crs(self, 
                     gdf: gpd.GeoDataFrame,
                     target_crs: Union[str, int, CRS],
                     **kwargs) -> gpd.GeoDataFrame:
        """
        Transform coordinate reference system.
        
        Args:
            gdf: Input GeoDataFrame
            target_crs: Target CRS (EPSG code, WKT, or CRS object)
            **kwargs: Additional transformation options
            
        Returns:
            Transformed GeoDataFrame
        """
        try:
            # Create target CRS object
            if isinstance(target_crs, (int, str)):
                target_crs = CRS.from_user_input(target_crs)
            
            # Transform
            transformed_gdf = gdf.to_crs(target_crs)
            
            log.info(f"Successfully transformed CRS to: {target_crs}")
            return transformed_gdf
            
        except Exception as e:
            log.error(f"Failed to transform CRS: {e}")
            return gdf
    
    def simplify_geometries(self, 
                           gdf: gpd.GeoDataFrame,
                           tolerance: float,
                           preserve_topology: bool = True,
                           **kwargs) -> gpd.GeoDataFrame:
        """
        Simplify geometries using Douglas-Peucker algorithm.
        
        Args:
            gdf: Input GeoDataFrame
            tolerance: Simplification tolerance
            preserve_topology: Whether to preserve topology
            **kwargs: Additional simplification options
            
        Returns:
            Simplified GeoDataFrame
        """
        try:
            simplified_gdf = gdf.copy()
            simplified_gdf['geometry'] = simplified_gdf.geometry.simplify(
                tolerance=tolerance,
                preserve_topology=preserve_topology
            )
            
            log.info(f"Successfully simplified geometries with tolerance: {tolerance}")
            return simplified_gdf
            
        except Exception as e:
            log.error(f"Failed to simplify geometries: {e}")
            return gdf
    
    def buffer_geometries(self, 
                         gdf: gpd.GeoDataFrame,
                         distance: float,
                         **kwargs) -> gpd.GeoDataFrame:
        """
        Create buffers around geometries.
        
        Args:
            gdf: Input GeoDataFrame
            distance: Buffer distance
            **kwargs: Additional buffer options
            
        Returns:
            Buffered GeoDataFrame
        """
        try:
            buffered_gdf = gdf.copy()
            buffered_gdf['geometry'] = buffered_gdf.geometry.buffer(distance)
            
            log.info(f"Successfully created buffers with distance: {distance}")
            return buffered_gdf
            
        except Exception as e:
            log.error(f"Failed to create buffers: {e}")
            return gdf

class PostGISConnector:
    """Handles PostGIS database connections and operations."""
    
    def __init__(self, connection_string: str):
        """
        Initialize PostGIS connector.
        
        Args:
            connection_string: PostgreSQL connection string
        """
        self.connection_string = connection_string
        self.engine = None
    
    def connect(self):
        """Establish database connection."""
        try:
            self.engine = create_engine(self.connection_string)
            log.info("Successfully connected to PostGIS")
            return True
        except Exception as e:
            log.error(f"Failed to connect to PostGIS: {e}")
            return False
    
    def upload_spatial_data(self, 
                           gdf: gpd.GeoDataFrame,
                           table_name: str,
                           schema: str = 'public',
                           if_exists: str = 'replace',
                           **kwargs) -> bool:
        """
        Upload spatial data to PostGIS.
        
        Args:
            gdf: GeoDataFrame to upload
            table_name: Target table name
            schema: Target schema
            if_exists: What to do if table exists
            **kwargs: Additional upload options
            
        Returns:
            True if successful
        """
        try:
            if not self.engine:
                if not self.connect():
                    return False
            
            # Upload to PostGIS
            gdf.to_postgis(
                name=table_name,
                con=self.engine,
                schema=schema,
                if_exists=if_exists,
                index=kwargs.get('index', False)
            )
            
            log.info(f"Successfully uploaded to PostGIS: {schema}.{table_name}")
            return True
            
        except Exception as e:
            log.error(f"Failed to upload to PostGIS: {e}")
            return False
    
    def download_spatial_data(self, 
                             table_name: str,
                             schema: str = 'public',
                             where_clause: Optional[str] = None,
                             **kwargs) -> Optional[gpd.GeoDataFrame]:
        """
        Download spatial data from PostGIS.
        
        Args:
            table_name: Source table name
            schema: Source schema
            where_clause: SQL WHERE clause
            **kwargs: Additional query options
            
        Returns:
            GeoDataFrame with spatial data
        """
        try:
            if not self.engine:
                if not self.connect():
                    return None
            
            # Construct query
            query = f"SELECT * FROM {schema}.{table_name}"
            if where_clause:
                query += f" WHERE {where_clause}"
            
            # Execute query
            gdf = gpd.read_postgis(query, self.engine, geom_col='geometry')
            
            log.info(f"Successfully downloaded from PostGIS: {schema}.{table_name}")
            return gdf
            
        except Exception as e:
            log.error(f"Failed to download from PostGIS: {e}")
            return None
    
    def execute_spatial_query(self, 
                             query: str,
                             **kwargs) -> Optional[gpd.GeoDataFrame]:
        """
        Execute custom spatial SQL query.
        
        Args:
            query: SQL query to execute
            **kwargs: Additional query options
            
        Returns:
            Query results as GeoDataFrame
        """
        try:
            if not self.engine:
                if not self.connect():
                    return None
            
            # Execute query
            gdf = gpd.read_postgis(query, self.engine, geom_col='geometry')
            
            log.info("Successfully executed spatial query")
            return gdf
            
        except Exception as e:
            log.error(f"Failed to execute spatial query: {e}")
            return None

class DuckDBConnector:
    """Handles DuckDB database connections and operations."""
    
    def __init__(self, db_path: str = ':memory:'):
        """
        Initialize DuckDB connector.
        
        Args:
            db_path: Path to DuckDB database file
        """
        self.db_path = db_path
        self.connection = None
    
    def connect(self):
        """Establish database connection."""
        try:
            self.connection = duckdb.connect(self.db_path)
            log.info("Successfully connected to DuckDB")
            return True
        except Exception as e:
            log.error(f"Failed to connect to DuckDB: {e}")
            return False
    
    def upload_spatial_data(self, 
                           gdf: gpd.GeoDataFrame,
                           table_name: str,
                           if_exists: str = 'replace',
                           **kwargs) -> bool:
        """
        Upload spatial data to DuckDB.
        
        Args:
            gdf: GeoDataFrame to upload
            table_name: Target table name
            if_exists: What to do if table exists
            **kwargs: Additional upload options
            
        Returns:
            True if successful
        """
        try:
            if not self.connection:
                if not self.connect():
                    return False
            
            # Convert to pandas DataFrame with WKT geometries
            df = gdf.copy()
            df['geometry_wkt'] = df.geometry.apply(lambda geom: dumps(geom))
            df = df.drop(columns=['geometry'])
            
            # Handle table replacement
            if if_exists == 'replace':
                self.connection.execute(f"DROP TABLE IF EXISTS {table_name}")
            
            # Upload to DuckDB
            self.connection.execute(f"CREATE TABLE {table_name} AS SELECT * FROM df")
            
            log.info(f"Successfully uploaded to DuckDB: {table_name}")
            return True
            
        except Exception as e:
            log.error(f"Failed to upload to DuckDB: {e}")
            return False
    
    def download_spatial_data(self, 
                             table_name: str,
                             where_clause: Optional[str] = None,
                             **kwargs) -> Optional[gpd.GeoDataFrame]:
        """
        Download spatial data from DuckDB.
        
        Args:
            table_name: Source table name
            where_clause: SQL WHERE clause
            **kwargs: Additional query options
            
        Returns:
            GeoDataFrame with spatial data
        """
        try:
            if not self.connection:
                if not self.connect():
                    return None
            
            # Construct query
            query = f"SELECT * FROM {table_name}"
            if where_clause:
                query += f" WHERE {where_clause}"
            
            # Execute query
            df = self.connection.execute(query).df()
            
            # Convert WKT back to geometries
            if 'geometry_wkt' in df.columns:
                df['geometry'] = df['geometry_wkt'].apply(loads)
                df = df.drop(columns=['geometry_wkt'])
            
            # Create GeoDataFrame
            gdf = gpd.GeoDataFrame(df, geometry='geometry')
            
            log.info(f"Successfully downloaded from DuckDB: {table_name}")
            return gdf
            
        except Exception as e:
            log.error(f"Failed to download from DuckDB: {e}")
            return None
    
    def execute_spatial_query(self, 
                             query: str,
                             **kwargs) -> Optional[gpd.GeoDataFrame]:
        """
        Execute custom SQL query.
        
        Args:
            query: SQL query to execute
            **kwargs: Additional query options
            
        Returns:
            Query results as GeoDataFrame
        """
        try:
            if not self.connection:
                if not self.connect():
                    return None
            
            # Execute query
            df = self.connection.execute(query).df()
            
            # Convert WKT back to geometries if present
            if 'geometry_wkt' in df.columns:
                df['geometry'] = df['geometry_wkt'].apply(loads)
                df = df.drop(columns=['geometry_wkt'])
            
            # Create GeoDataFrame
            gdf = gpd.GeoDataFrame(df, geometry='geometry')
            
            log.info("Successfully executed DuckDB query")
            return gdf
            
        except Exception as e:
            log.error(f"Failed to execute DuckDB query: {e}")
            return None

# Global instances
spatial_transformer = SpatialDataTransformer()

def convert_spatial_format(input_data: Union[str, Path, gpd.GeoDataFrame],
                          output_format: str,
                          output_path: Optional[str] = None,
                          **kwargs) -> Union[gpd.GeoDataFrame, str, bool]:
    """Convert spatial data between formats."""
    return spatial_transformer.convert_format(
        input_data=input_data,
        output_format=output_format,
        output_path=output_path,
        **kwargs
    )

def transform_spatial_crs(gdf: gpd.GeoDataFrame,
                         target_crs: Union[str, int, CRS],
                         **kwargs) -> gpd.GeoDataFrame:
    """Transform coordinate reference system."""
    return spatial_transformer.transform_crs(gdf, target_crs, **kwargs)

def simplify_spatial_geometries(gdf: gpd.GeoDataFrame,
                               tolerance: float,
                               preserve_topology: bool = True,
                               **kwargs) -> gpd.GeoDataFrame:
    """Simplify spatial geometries."""
    return spatial_transformer.simplify_geometries(
        gdf, tolerance, preserve_topology, **kwargs
    )

def buffer_spatial_geometries(gdf: gpd.GeoDataFrame,
                             distance: float,
                             **kwargs) -> gpd.GeoDataFrame:
    """Create buffers around spatial geometries."""
    return spatial_transformer.buffer_geometries(gdf, distance, **kwargs)

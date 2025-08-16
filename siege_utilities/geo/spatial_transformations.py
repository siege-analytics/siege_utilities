"""
Spatial data transformation utilities for siege_utilities.
Provides format conversion and transformation capabilities using the core geospatial stack.
DuckDB support is included but optional for enhanced performance on large datasets.
"""

import logging
import pandas as pd
import geopandas as gpd
from pathlib import Path
from typing import Dict, Any, Optional, List, Union
import json
import tempfile
import os
import shutil

# Import existing library functions
from ..files.remote import download_file, generate_local_path_from_url
from ..files.paths import unzip_file_to_directory, ensure_path_exists
from ..config.user_config import get_user_config, get_download_directory

# Get logger for this module
log = logging.getLogger(__name__)

# Type aliases
FilePath = Union[str, Path]
GeoDataFrame = gpd.GeoDataFrame

# Try to import DuckDB (optional)
try:
    import duckdb
    DUCKDB_AVAILABLE = True
    log.info("DuckDB available for enhanced spatial operations")
except ImportError:
    DUCKDB_AVAILABLE = False
    log.info("DuckDB not available - using standard geospatial stack")


class SpatialDataTransformer:
    """Transform spatial data between different formats and coordinate systems."""
    
    def __init__(self):
        """Initialize the spatial data transformer."""
        try:
            self.user_config = get_user_config()
        except Exception as e:
            log.warning(f"Failed to load user config: {e}")
            self.user_config = {}
        
        # Supported output formats (using core geospatial stack + optional DuckDB)
        self.supported_formats = {
            'output': ['shp', 'geojson', 'gpkg', 'kml', 'gml', 'wkt', 'wkb', 'postgis']
        }
        
        # Add DuckDB if available
        if DUCKDB_AVAILABLE:
            self.supported_formats['output'].append('duckdb')
    
    def convert_format(self, gdf: GeoDataFrame, output_format: str, **kwargs) -> bool:
        """
        Convert GeoDataFrame to different format.
        
        Args:
            gdf: Input GeoDataFrame
            output_format: Desired output format
            **kwargs: Additional format-specific parameters
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if output_format == 'shp':
                return self._convert_to_shapefile(gdf, **kwargs)
            elif output_format == 'geojson':
                return self._convert_to_geojson(gdf, **kwargs)
            elif output_format == 'gpkg':
                return self._convert_to_geopackage(gdf, **kwargs)
            elif output_format == 'kml':
                return self._convert_to_kml(gdf, **kwargs)
            elif output_format == 'gml':
                return self._convert_to_gml(gdf, **kwargs)
            elif output_format == 'wkt':
                return self._convert_to_wkt(gdf, **kwargs)
            elif output_format == 'wkb':
                return self._convert_to_wkb(gdf, **kwargs)
            elif output_format == 'postgis':
                return self._convert_to_postgis(gdf, **kwargs)
            elif output_format == 'duckdb':
                if DUCKDB_AVAILABLE:
                    return self._convert_to_duckdb(gdf, **kwargs)
                else:
                    log.error("DuckDB not available. Install with: pip install duckdb")
                    return False
            else:
                log.error(f"Unsupported output format: {output_format}")
                return False
                
        except Exception as e:
            log.error(f"Format conversion failed: {e}")
            return False
    
    def _convert_to_shapefile(self, gdf: GeoDataFrame, **kwargs) -> bool:
        """Convert to ESRI Shapefile format."""
        try:
            output_path = kwargs.get('output_path', 'output.shp')
            gdf.to_file(output_path, driver='ESRI Shapefile')
            log.info(f"Successfully converted to Shapefile: {output_path}")
            return True
        except Exception as e:
            log.error(f"Failed to convert to Shapefile: {e}")
            return False
    
    def _convert_to_geojson(self, gdf: GeoDataFrame, **kwargs) -> bool:
        """Convert to GeoJSON format."""
        try:
            output_path = kwargs.get('output_path', 'output.geojson')
            gdf.to_file(output_path, driver='GeoJSON')
            log.info(f"Successfully converted to GeoJSON: {output_path}")
            return True
        except Exception as e:
            log.error(f"Failed to convert to GeoJSON: {e}")
            return False
    
    def _convert_to_geopackage(self, gdf: GeoDataFrame, **kwargs) -> bool:
        """Convert to GeoPackage format."""
        try:
            output_path = kwargs.get('output_path', 'output.gpkg')
            gdf.to_file(output_path, driver='GPKG')
            log.info(f"Successfully converted to GeoPackage: {output_path}")
            return True
        except Exception as e:
            log.error(f"Failed to convert to GeoPackage: {e}")
            return False
    
    def _convert_to_kml(self, gdf: GeoDataFrame, **kwargs) -> bool:
        """Convert to KML format."""
        try:
            output_path = kwargs.get('output_path', 'output.kml')
            gdf.to_file(output_path, driver='KML')
            log.info(f"Successfully converted to KML: {output_path}")
            return True
        except Exception as e:
            log.error(f"Failed to convert to KML: {e}")
            return False
    
    def _convert_to_gml(self, gdf: GeoDataFrame, **kwargs) -> bool:
        """Convert to GML format."""
        try:
            output_path = kwargs.get('output_path', 'output.gml')
            gdf.to_file(output_path, driver='GML')
            log.info(f"Successfully converted to GML: {output_path}")
            return True
        except Exception as e:
            log.error(f"Failed to convert to GML: {e}")
            return False
    
    def _convert_to_wkt(self, gdf: GeoDataFrame, **kwargs) -> bool:
        """Convert to WKT (Well-Known Text) format."""
        try:
            output_path = kwargs.get('output_path', 'output.wkt')
            
            # Convert geometries to WKT strings
            wkt_data = gdf.copy()
            wkt_data['geometry'] = wkt_data.geometry.astype(str)
            
            # Save as CSV with WKT geometries
            wkt_data.to_csv(output_path, index=False)
            log.info(f"Successfully converted to WKT: {output_path}")
            return True
        except Exception as e:
            log.error(f"Failed to convert to WKT: {e}")
            return False
    
    def _convert_to_wkb(self, gdf: GeoDataFrame, **kwargs) -> bool:
        """Convert to WKB (Well-Known Binary) format."""
        try:
            output_path = kwargs.get('output_path', 'output.wkb')
            
            # Convert geometries to WKB bytes
            wkb_data = gdf.copy()
            wkb_data['geometry'] = wkb_data.geometry.apply(lambda geom: geom.wkb)
            
            # Save as pickle (WKB is binary data)
            wkb_data.to_pickle(output_path)
            log.info(f"Successfully converted to WKB: {output_path}")
            return True
        except Exception as e:
            log.error(f"Failed to convert to WKB: {e}")
            return False
    
    def _convert_to_postgis(self, gdf: GeoDataFrame, **kwargs) -> bool:
        """Convert to PostGIS format (upload to PostgreSQL database)."""
        try:
            # This would require psycopg2 and database connection
            # For now, just save as SQL file that can be imported
            output_path = kwargs.get('output_path', 'output.sql')
            
            # Generate SQL INSERT statements
            sql_statements = []
            for idx, row in gdf.iterrows():
                geom_wkt = row.geometry.wkt
                # Basic SQL generation - in practice you'd want more sophisticated handling
                sql = f"INSERT INTO spatial_table (geom) VALUES (ST_GeomFromText('{geom_wkt}'));"
                sql_statements.append(sql)
            
            with open(output_path, 'w') as f:
                f.write('\n'.join(sql_statements))
            
            log.info(f"Successfully generated PostGIS SQL: {output_path}")
            return True
        except Exception as e:
            log.error(f"Failed to convert to PostGIS: {e}")
            return False
    
    def _convert_to_duckdb(self, gdf: GeoDataFrame, **kwargs) -> bool:
        """Convert to DuckDB format and save to database."""
        if not DUCKDB_AVAILABLE:
            log.error("DuckDB not available")
            return False
            
        try:
            # Get database parameters from user config or kwargs
            db_path = kwargs.get('db_path') or self.user_config.get_database_connection('duckdb') or ':memory:'
            table_name = kwargs.get('table_name', 'spatial_data')
            
            # Connect to DuckDB
            con = duckdb.connect(db_path)
            
            # Convert to pandas DataFrame with WKT geometries
            df = gdf.copy()
            df['geometry_wkt'] = df.geometry.apply(lambda geom: geom.wkt)
            df = df.drop(columns=['geometry'])
            
            # Upload to DuckDB
            con.execute(f"CREATE TABLE IF NOT EXISTS {table_name} AS SELECT * FROM df")
            
            log.info(f"Successfully uploaded to DuckDB table: {table_name}")
            return True
            
        except Exception as e:
            log.error(f"Failed to convert to DuckDB: {e}")
            return False


class PostGISConnector:
    """Handles PostGIS database connections and operations."""
    
    def __init__(self, connection_string: Optional[str] = None):
        """
        Initialize PostGIS connector.
        
        Args:
            connection_string: PostgreSQL connection string
        """
        self.connection_string = connection_string or self.user_config.get_database_connection('postgresql')
        
        try:
            import psycopg2
            self.psycopg2 = psycopg2
            self.connection = psycopg2.connect(self.connection_string)
            log.info("Successfully connected to PostGIS")
        except ImportError:
            log.error("psycopg2 not available. Install with: pip install psycopg2-binary")
            self.psycopg2 = None
            self.connection = None
        except Exception as e:
            log.error(f"Failed to connect to PostGIS: {e}")
            self.connection = None
    
    def upload_spatial_data(self, gdf: GeoDataFrame, table_name: str, **kwargs) -> bool:
        """
        Upload spatial data to PostGIS.
        
        Args:
            gdf: GeoDataFrame to upload
            table_name: Target table name
            **kwargs: Additional parameters
            
        Returns:
            True if successful, False otherwise
        """
        if not self.connection:
            log.error("No PostGIS connection available")
            return False
        
        try:
            # Create table if it doesn't exist
            self._create_spatial_table(table_name, gdf)
            
            # Upload data
            cursor = self.connection.cursor()
            
            for idx, row in gdf.iterrows():
                geom_wkt = row.geometry.wkt
                # Basic upload - in practice you'd want more sophisticated handling
                cursor.execute(
                    f"INSERT INTO {table_name} (geom) VALUES (ST_GeomFromText(%s))",
                    (geom_wkt,)
                )
            
            self.connection.commit()
            log.info(f"Successfully uploaded to PostGIS table: {table_name}")
            return True
            
        except Exception as e:
            log.error(f"Failed to upload to PostGIS: {e}")
            return False
    
    def download_spatial_data(self, table_name: str, **kwargs) -> Optional[GeoDataFrame]:
        """
        Download spatial data from PostGIS.
        
        Args:
            table_name: Source table name
            **kwargs: Additional parameters
            
        Returns:
            GeoDataFrame with spatial data or None if failed
        """
        if not self.connection:
            log.error("No PostGIS connection available")
            return None
        
        try:
            cursor = self.connection.cursor()
            cursor.execute(f"SELECT ST_AsText(geom) as geometry FROM {table_name}")
            
            rows = cursor.fetchall()
            geometries = []
            
            for row in rows:
                from shapely import wkt
                geom = wkt.loads(row[0])
                geometries.append(geom)
            
            # Create GeoDataFrame
            gdf = gpd.GeoDataFrame(geometry=geometries)
            log.info(f"Successfully downloaded from PostGIS: {table_name}")
            return gdf
            
        except Exception as e:
            log.error(f"Failed to download from PostGIS: {e}")
            return None
    
    def execute_spatial_query(self, query: str, **kwargs) -> Optional[GeoDataFrame]:
        """
        Execute a spatial SQL query.
        
        Args:
            query: SQL query string
            **kwargs: Additional parameters
            
        Returns:
            Query results as GeoDataFrame or None if failed
        """
        if not self.connection:
            log.error("No PostGIS connection available")
            return None
        
        try:
            cursor = self.connection.cursor()
            cursor.execute(query)
            
            # Process results based on query type
            if query.strip().upper().startswith('SELECT'):
                rows = cursor.fetchall()
                # Convert to GeoDataFrame (simplified)
                gdf = gpd.GeoDataFrame(rows)
                log.info("Successfully executed PostGIS query")
                return gdf
            else:
                self.connection.commit()
                log.info("Successfully executed PostGIS query")
                return gpd.GeoDataFrame()
                
        except Exception as e:
            log.error(f"Failed to execute PostGIS query: {e}")
            return None
    
    def _create_spatial_table(self, table_name: str, gdf: GeoDataFrame):
        """Create a spatial table in PostGIS."""
        cursor = self.connection.cursor()
        
        # Basic table creation - in practice you'd want more sophisticated handling
        create_sql = f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            id SERIAL PRIMARY KEY,
            geom GEOMETRY(POLYGON, 4326)
        );
        """
        
        cursor.execute(create_sql)
        self.connection.commit()


class DuckDBConnector:
    """Handles DuckDB database connections and operations (optional)."""
    
    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize DuckDB connector.
        
        Args:
            db_path: Path to DuckDB database file (optional, uses user config if not provided)
        """
        if not DUCKDB_AVAILABLE:
            raise ImportError("DuckDB not available. Install with: pip install duckdb")
        
        try:
            self.user_config = get_user_config()
        except Exception as e:
            log.warning(f"Failed to load user config: {e}")
            self.user_config = {}
        
        self.db_path = db_path or self.user_config.get_database_connection('duckdb') or ':memory:'
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
    
    def upload_spatial_data(self, gdf: GeoDataFrame, table_name: str, **kwargs) -> bool:
        """
        Upload spatial data to DuckDB.
        
        Args:
            gdf: GeoDataFrame to upload
            table_name: Target table name
            **kwargs: Additional parameters
            
        Returns:
            True if successful, False otherwise
        """
        if not self.connection:
            if not self.connect():
                return False
        
        try:
            # Convert to pandas DataFrame with WKT geometries
            df = gdf.copy()
            df['geometry_wkt'] = df.geometry.apply(lambda geom: geom.wkt)
            df = df.drop(columns=['geometry'])
            
            # Handle table replacement
            if_exists = kwargs.get('if_exists', 'replace')
            if if_exists == 'replace':
                self.connection.execute(f"DROP TABLE IF EXISTS {table_name}")
            
            # Upload to DuckDB
            self.connection.execute(f"CREATE TABLE {table_name} AS SELECT * FROM df")
            
            log.info(f"Successfully uploaded to DuckDB: {table_name}")
            return True
            
        except Exception as e:
            log.error(f"Failed to upload to DuckDB: {e}")
            return False
    
    def download_spatial_data(self, table_name: str, **kwargs) -> Optional[GeoDataFrame]:
        """
        Download spatial data from DuckDB.
        
        Args:
            table_name: Source table name
            **kwargs: Additional parameters
            
        Returns:
            GeoDataFrame with spatial data or None if failed
        """
        if not self.connection:
            if not self.connect():
                return None
        
        try:
            # Construct query
            query = f"SELECT * FROM {table_name}"
            where_clause = kwargs.get('where_clause')
            if where_clause:
                query += f" WHERE {where_clause}"
            
            # Execute query
            df = self.connection.execute(query).df()
            
            # Convert WKT back to geometries
            if 'geometry_wkt' in df.columns:
                from shapely import wkt
                df['geometry'] = df['geometry_wkt'].apply(wkt.loads)
                df = df.drop(columns=['geometry_wkt'])
            
            # Create GeoDataFrame
            gdf = gpd.GeoDataFrame(df, geometry='geometry')
            
            log.info(f"Successfully downloaded from DuckDB: {table_name}")
            return gdf
            
        except Exception as e:
            log.error(f"Failed to download from DuckDB: {e}")
            return None
    
    def execute_spatial_query(self, query: str, **kwargs) -> Optional[GeoDataFrame]:
        """
        Execute a spatial SQL query.
        
        Args:
            query: SQL query string
            **kwargs: Additional parameters
            
        Returns:
            Query results as GeoDataFrame or None if failed
        """
        if not self.connection:
            if not self.connect():
                return None
        
        try:
            # Execute query
            df = self.connection.execute(query).df()
            
            # Convert WKT back to geometries if present
            if 'geometry_wkt' in df.columns:
                from shapely import wkt
                df['geometry'] = df['geometry_wkt'].apply(wkt.loads)
                df = df.drop(columns=['geometry_wkt'])
            
            # Create GeoDataFrame
            gdf = gpd.GeoDataFrame(df, geometry='geometry')
            
            log.info("Successfully executed DuckDB query")
            return gdf
            
        except Exception as e:
            log.error(f"Failed to execute DuckDB query: {e}")
            return None


# Convenience functions
def convert_spatial_format(gdf: GeoDataFrame, output_format: str, **kwargs) -> bool:
    """Convert spatial data to different format."""
    transformer = SpatialDataTransformer()
    return transformer.convert_format(gdf, output_format, **kwargs)


def upload_to_postgis(gdf: GeoDataFrame, table_name: str, connection_string: Optional[str] = None, **kwargs) -> bool:
    """Upload spatial data to PostGIS."""
    connector = PostGISConnector(connection_string)
    return connector.upload_spatial_data(gdf, table_name, **kwargs)


def download_from_postgis(table_name: str, connection_string: Optional[str] = None, **kwargs) -> Optional[GeoDataFrame]:
    """Download spatial data from PostGIS."""
    connector = PostGISConnector(connection_string)
    return connector.download_spatial_data(table_name, **kwargs)


def execute_postgis_query(query: str, connection_string: Optional[str] = None, **kwargs) -> Optional[GeoDataFrame]:
    """Execute a spatial SQL query on PostGIS."""
    connector = PostGISConnector(connection_string)
    return connector.execute_spatial_query(query, **kwargs)


def upload_to_duckdb(gdf: GeoDataFrame, table_name: str, db_path: Optional[str] = None, **kwargs) -> bool:
    """Upload spatial data to DuckDB (optional)."""
    if not DUCKDB_AVAILABLE:
        log.error("DuckDB not available. Install with: pip install duckdb")
        return False
    
    connector = DuckDBConnector(db_path)
    return connector.upload_spatial_data(gdf, table_name, **kwargs)


def download_from_duckdb(table_name: str, db_path: Optional[str] = None, **kwargs) -> Optional[GeoDataFrame]:
    """Download spatial data from DuckDB (optional)."""
    if not DUCKDB_AVAILABLE:
        log.error("DuckDB not available. Install with: pip install duckdb")
        return None
    
    connector = DuckDBConnector(db_path)
    return connector.download_spatial_data(table_name, **kwargs)


def execute_duckdb_query(query: str, db_path: Optional[str] = None, **kwargs) -> Optional[GeoDataFrame]:
    """Execute a spatial SQL query on DuckDB (optional)."""
    if not DUCKDB_AVAILABLE:
        log.error("DuckDB not available. Install with: pip install duckdb")
        return None
    
    connector = DuckDBConnector(db_path)
    return connector.execute_spatial_query(query, **kwargs)


__all__ = [
    'SpatialDataTransformer',
    'PostGISConnector',
    'DuckDBConnector',
    'convert_spatial_format',
    'upload_to_postgis',
    'download_from_postgis',
    'execute_postgis_query',
    'upload_to_duckdb',
    'download_from_duckdb',
    'execute_duckdb_query',
    'DUCKDB_AVAILABLE'
]

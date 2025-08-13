"""
Spatial data utilities for siege_utilities.
Provides spatial data sources, transformations, and database integration.
"""

from .data_sources import (
    CensusDataSource,
    GovernmentDataSource,
    OpenStreetMapDataSource,
    census_source,
    government_source,
    osm_source,
    get_census_data,
    get_census_boundaries,
    download_osm_data
)

from .data_transformation import (
    SpatialDataTransformer,
    PostGISConnector,
    DuckDBConnector,
    spatial_transformer,
    convert_spatial_format,
    transform_spatial_crs,
    simplify_spatial_geometries,
    buffer_spatial_geometries
)

__all__ = [
    # Data sources
    'CensusDataSource',
    'GovernmentDataSource', 
    'OpenStreetMapDataSource',
    'census_source',
    'government_source',
    'osm_source',
    'get_census_data',
    'get_census_boundaries',
    'download_osm_data',
    
    # Data transformation
    'SpatialDataTransformer',
    'PostGISConnector',
    'DuckDBConnector',
    'spatial_transformer',
    'convert_spatial_format',
    'transform_spatial_crs',
    'simplify_spatial_geometries',
    'buffer_spatial_geometries'
]

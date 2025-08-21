"""
Geographic utilities for spatial data analysis, Census data access, and mapping.

This package provides comprehensive tools for working with geographic data,
including enhanced Census utilities, intelligent data selection, and spatial analysis.
"""

from .spatial_data import (
    CensusDirectoryDiscovery,
    CensusDataSource,
    SpatialDataSource,
    GovernmentDataSource,
    OpenStreetMapDataSource
)

from .census_dataset_mapper import (
    CensusDatasetMapper,
    SurveyType,
    GeographyLevel,
    DataReliability,
    CensusDataset,
    DatasetRelationship,
    get_census_dataset_mapper,
    get_best_dataset_for_analysis,
    compare_census_datasets
)

from .census_data_selector import (
    CensusDataSelector,
    get_census_data_selector,
    select_census_datasets,
    get_analysis_approach
)

from .spatial_transformations import (
    SpatialDataTransformer,
    DUCKDB_AVAILABLE
)

from .geocoding import (
    concatenate_addresses,
    use_nominatim_geocoder,
    NominatimGeoClassifier
)

__all__ = [
    # Core spatial data classes
    'CensusDirectoryDiscovery',
    'CensusDataSource', 
    'SpatialDataSource',
    'GovernmentDataSource',
    'OpenStreetMapDataSource',
    
    # Census dataset mapping and intelligence
    'CensusDatasetMapper',
    'SurveyType',
    'GeographyLevel', 
    'DataReliability',
    'CensusDataset',
    'DatasetRelationship',
    'get_census_dataset_mapper',
    'get_best_dataset_for_analysis',
    'compare_census_datasets',
    
    # Intelligent data selection
    'CensusDataSelector',
    'get_census_data_selector',
    'select_census_datasets',
    'get_analysis_approach',
    
    # Spatial transformations
    'SpatialDataTransformer',
    'DUCKDB_AVAILABLE',
    
    # Geocoding
    'concatenate_addresses',
    'use_nominatim_geocoder',
    'NominatimGeoClassifier'
]

# Package metadata
__version__ = "2.0.0"
__author__ = "Siege Analytics"
__description__ = "Enhanced geographic utilities with intelligent Census data selection"

# Convenience function for quick access to Census intelligence
def get_census_intelligence():
    """
    Get a comprehensive Census intelligence system.
    
    Returns:
        tuple: (CensusDatasetMapper, CensusDataSelector) for full Census data intelligence
    """
    from .census_dataset_mapper import get_census_dataset_mapper
    from .census_data_selector import get_census_data_selector
    
    return get_census_dataset_mapper(), get_census_data_selector()

# Quick access to common Census data selection
def quick_census_selection(analysis_type: str, geography_level: str):
    """
    Quick access to Census data selection recommendations.
    
    Args:
        analysis_type: Type of analysis (e.g., "demographics", "housing", "business")
        geography_level: Required geography level (e.g., "tract", "county", "state")
    
    Returns:
        dict: Dataset recommendations and analysis approach
    """
    from .census_data_selector import select_census_datasets, get_analysis_approach
    
    recommendations = select_census_datasets(analysis_type, geography_level)
    approach = get_analysis_approach(analysis_type, geography_level)
    
    return {
        "recommendations": recommendations,
        "analysis_approach": approach
    }
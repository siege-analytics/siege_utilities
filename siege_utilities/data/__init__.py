"""
Sample Data Module for Siege Utilities

This module provides built-in sample datasets for testing, learning, and demonstration purposes.
Combines real Census data with synthetic personal data using Faker for realistic datasets.
"""

from .sample_data import (
    # Core sample data functions
    load_sample_data,
    list_available_datasets,
    get_dataset_info,
    
    # Census-based sample data
    get_census_boundaries,
    get_census_data,
    join_boundaries_and_data,
    create_sample_dataset,
    
    # Synthetic data generation
    generate_synthetic_population,
    generate_synthetic_businesses,
    generate_synthetic_housing,
    
    # Dataset categories
    SAMPLE_DATASETS,
    CENSUS_SAMPLES,
    SYNTHETIC_SAMPLES
)

__all__ = [
    # Core functions
    'load_sample_data',
    'list_available_datasets', 
    'get_dataset_info',
    
    # Census samples
    'get_census_boundaries',
    'get_census_data',
    'join_boundaries_and_data',
    'create_sample_dataset',
    
    # Synthetic generation
    'generate_synthetic_population',
    'generate_synthetic_businesses',
    'generate_synthetic_housing',
    
    # Dataset info
    'SAMPLE_DATASETS',
    'CENSUS_SAMPLES',
    'SYNTHETIC_SAMPLES'
]

# Package metadata
__version__ = "1.0.0"
__description__ = "Sample datasets and synthetic data generation for testing and learning"

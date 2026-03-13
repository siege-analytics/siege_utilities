"""
Data Module for Siege Utilities

This module provides:
- Built-in sample datasets for testing, learning, and demonstration purposes.
- Engine-agnostic DataFrame operations (pandas, DuckDB, Spark, PostGIS).
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
    HOUSING_LOCALE_PRESETS,

    # Dataset categories
    SAMPLE_DATASETS,
    CENSUS_SAMPLES,
    SYNTHETIC_SAMPLES
)

from .redistricting_data_hub import (
    RDHClient,
    RDHDataset,
    RDHDataFormat,
    RDHDatasetType,
    RDH_BASE_URL,
    US_STATES,
    polsby_popper,
    reock,
    convex_hull_ratio,
    schwartzberg,
    compute_compactness,
    compare_plans,
    demographic_profile,
)

from .dataframe_engine import (
    Engine,
    PANDAS,
    DUCKDB,
    SPARK,
    POSTGIS,
    DataFrameEngine,
    PandasEngine,
    DuckDBEngine,
    SparkEngine,
    PostGISEngine,
    get_engine,
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
    'HOUSING_LOCALE_PRESETS',

    # Dataset info
    'SAMPLE_DATASETS',
    'CENSUS_SAMPLES',
    'SYNTHETIC_SAMPLES',

    # Redistricting Data Hub
    'RDHClient',
    'RDHDataset',
    'RDHDataFormat',
    'RDHDatasetType',
    'RDH_BASE_URL',
    'US_STATES',
    'polsby_popper',
    'reock',
    'convex_hull_ratio',
    'schwartzberg',
    'compute_compactness',
    'compare_plans',
    'demographic_profile',

    # Engine-agnostic DataFrame operations
    'Engine',
    'PANDAS',
    'DUCKDB',
    'SPARK',
    'POSTGIS',
    'DataFrameEngine',
    'PandasEngine',
    'DuckDBEngine',
    'SparkEngine',
    'PostGISEngine',
    'get_engine',
]

# Package metadata
__version__ = "1.0.0"
__description__ = "Sample datasets and synthetic data generation for testing and learning"

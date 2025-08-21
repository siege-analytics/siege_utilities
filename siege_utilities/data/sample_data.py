"""
Sample Data Generation and Management

This module provides built-in sample datasets for testing, learning, and demonstration purposes.
Combines real Census data with synthetic personal data using Faker for realistic datasets.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Union, Any, Tuple
import warnings
import os
from pathlib import Path

# Try to import optional dependencies
try:
    from faker import Faker
    from faker.providers import address, person, company, internet
    FAKER_AVAILABLE = True
except ImportError:
    FAKER_AVAILABLE = False
    warnings.warn("Faker not available. Install with: pip install Faker")

try:
    import geopandas as gpd
    from shapely.geometry import Point, Polygon
    GEOPANDAS_AVAILABLE = True
except ImportError:
    GEOPANDAS_AVAILABLE = False
    warnings.warn("GeoPandas not available. Install with: pip install geopandas")

# Import existing Census utilities
try:
    from ..geo import get_census_data_selector, select_census_datasets
    from ..geo.spatial_data import CensusDataSource
    CENSUS_AVAILABLE = True
except ImportError:
    CENSUS_AVAILABLE = False
    warnings.warn("Census utilities not available")

# Initialize Faker instances for different locales
if FAKER_AVAILABLE:
    faker_en = Faker(['en_US'])
    faker_es = Faker(['es_ES'])  # Hispanic names
    faker_zh = Faker(['zh_CN'])  # Asian names
    faker_hi = Faker(['hi_IN'])  # Indian names
    faker_ar = Faker(['ar_SA'])  # Arabic names

# Dataset definitions
SAMPLE_DATASETS = {
    "census_tract_sample": {
        "description": "Sample Census tract with real boundaries and synthetic population",
        "size": "~1-5 MB",
        "type": "geospatial",
        "variables": ["demographics", "housing", "income", "geometry"],
        "source": "census_synthetic"
    },
    "census_county_sample": {
        "description": "Sample county with multiple tracts and synthetic businesses",
        "size": "~5-15 MB", 
        "type": "geospatial",
        "variables": ["demographics", "businesses", "geometry"],
        "source": "census_synthetic"
    },
    "metropolitan_sample": {
        "description": "Metropolitan area with multiple counties and comprehensive data",
        "size": "~20-50 MB",
        "type": "geospatial",
        "variables": ["demographics", "businesses", "housing", "transportation"],
        "source": "census_synthetic"
    },
    "synthetic_population": {
        "description": "Synthetic population matching Census standards and demographic patterns",
        "size": "~1-10 MB",
        "type": "tabular",
        "variables": ["names", "age_groups", "race", "hispanic_origin", "sex", "income_brackets", "education_attainment"],
        "source": "synthetic"
    },
    "synthetic_businesses": {
        "description": "Synthetic business data with realistic industry patterns",
        "size": "~1-5 MB",
        "type": "tabular", 
        "variables": ["names", "industries", "sizes", "locations", "revenue"],
        "source": "synthetic"
    },
    "synthetic_housing": {
        "description": "Synthetic housing data with realistic property patterns",
        "size": "~1-5 MB",
        "type": "tabular",
        "variables": ["addresses", "values", "types", "features", "coordinates"],
        "source": "synthetic"
    }
}

CENSUS_SAMPLES = ["census_tract_sample", "census_county_sample", "metropolitan_sample"]
SYNTHETIC_SAMPLES = ["synthetic_population", "synthetic_businesses", "synthetic_housing"]

def list_available_datasets() -> Dict[str, Dict[str, Any]]:
    """
    List all available sample datasets with descriptions and metadata.
    
    Returns:
        Dictionary of available datasets with metadata
    """
    return SAMPLE_DATASETS.copy()

def get_dataset_info(dataset_name: str) -> Optional[Dict[str, Any]]:
    """
    Get detailed information about a specific dataset.
    
    Args:
        dataset_name: Name of the dataset
        
    Returns:
        Dataset information dictionary or None if not found
    """
    return SAMPLE_DATASETS.get(dataset_name)

def load_sample_data(dataset_name: str, **kwargs) -> Union[pd.DataFrame, gpd.GeoDataFrame, None]:
    """
    Load a sample dataset by name.
    
    Args:
        dataset_name: Name of the dataset to load
        **kwargs: Additional arguments for dataset generation
        
    Returns:
        DataFrame or GeoDataFrame with sample data
        
    Raises:
        ValueError: If dataset name is not recognized
        ImportError: If required dependencies are not available
    """
    if dataset_name not in SAMPLE_DATASETS:
        raise ValueError(f"Unknown dataset: {dataset_name}. Available: {list(SAMPLE_DATASETS.keys())}")
    
    if dataset_name in CENSUS_SAMPLES:
        if not CENSUS_AVAILABLE:
            raise ImportError("Census utilities required for this dataset. Install with: pip install siege-utilities[geo]")
        if not GEOPANDAS_AVAILABLE:
            raise ImportError("GeoPandas required for geospatial datasets. Install with: pip install geopandas")
    
    if dataset_name in SYNTHETIC_SAMPLES:
        if not FAKER_AVAILABLE:
            raise ImportError("Faker required for synthetic datasets. Install with: pip install Faker")
    
    # Route to appropriate generator
    if dataset_name == "census_tract_sample":
        return create_sample_dataset(**kwargs)
    elif dataset_name == "census_county_sample":
        return get_census_county_sample(**kwargs)
    elif dataset_name == "metropolitan_sample":
        return get_metropolitan_sample(**kwargs)
    elif dataset_name == "synthetic_population":
        return generate_synthetic_population(**kwargs)
    elif dataset_name == "synthetic_businesses":
        return generate_synthetic_businesses(**kwargs)
    elif dataset_name == "synthetic_housing":
        return generate_synthetic_housing(**kwargs)
    else:
        raise ValueError(f"Dataset generator not implemented: {dataset_name}")

def get_census_boundaries(year: int = 2020,
                         geographic_level: str = 'tract',
                         state_fips: Optional[str] = None,
                         county_fips: Optional[str] = None) -> Optional[gpd.GeoDataFrame]:
    """
    Download Census geographic boundaries.
    
    Args:
        year: Census year (default: 2020)
        geographic_level: Geographic level (state, county, tract, etc.)
        state_fips: State FIPS code for filtering
        county_fips: County FIPS code for filtering (if applicable)
        
    Returns:
        GeoDataFrame with boundaries or None if failed
    """
    if not CENSUS_AVAILABLE:
        raise ImportError("Census utilities required. Install with: pip install siege-utilities[geo]")
    
    try:
        from siege_utilities.geo.spatial_data import census_source
        
        print(f"🗺️ Downloading {geographic_level} boundaries for year {year}")
        
        # Download boundaries
        boundaries = census_source.get_geographic_boundaries(
            year=year,
            geographic_level=geographic_level,
            state_fips=state_fips
        )
        
        if boundaries is None or len(boundaries) == 0:
            print("❌ No boundaries returned from Census source")
            return None
        
        print(f"✅ Downloaded {len(boundaries)} {geographic_level} boundaries")
        print(f"📋 Available columns: {list(boundaries.columns)}")
        
        # Filter by county if specified
        if county_fips and geographic_level in ['tract', 'block_group']:
            county_cols = boundaries.columns[boundaries.columns.str.lower() == 'countyfp']
            if len(county_cols) > 0:
                county_col = county_cols[0]
                boundaries = boundaries[boundaries[county_col] == county_fips]
                print(f"📊 Filtered to {len(boundaries)} boundaries in county {county_fips}")
            else:
                print("⚠️ No county column found, skipping county filter")
        
        return boundaries
        
    except Exception as e:
        print(f"❌ Error downloading boundaries: {e}")
        return None


def get_census_data(year: int = 2020,
                   data_type: str = 'demographics',
                   geographic_level: str = 'tract',
                   state_fips: Optional[str] = None,
                   county_fips: Optional[str] = None) -> Optional[pd.DataFrame]:
    """
    Get Census demographic/attribute data.
    
    Args:
        year: Census year (default: 2020)
        data_type: Type of data (demographics, housing, income, etc.)
        geographic_level: Geographic level for data
        state_fips: State FIPS code for filtering
        county_fips: County FIPS code for filtering
        
    Returns:
        DataFrame with Census data or None if failed
    """
    if not CENSUS_AVAILABLE:
        raise ImportError("Census utilities required. Install with: pip install siege-utilities[geo]")
    
    try:
        print(f"📊 Getting {data_type} data for {geographic_level} level, year {year}")
        
        # This would integrate with existing Census data functions
        # For now, return a placeholder
        print("⚠️ Census data retrieval not yet implemented")
        print("   This function will integrate with existing Census data utilities")
        return None
        
    except Exception as e:
        print(f"❌ Error getting Census data: {e}")
        return None


def join_boundaries_and_data(boundaries: gpd.GeoDataFrame,
                           data: pd.DataFrame,
                           boundary_id_col: str = 'geoid',
                           data_id_col: str = 'geoid') -> Optional[gpd.GeoDataFrame]:
    """
    Join geographic boundaries with attribute data.
    
    Args:
        boundaries: GeoDataFrame with geographic boundaries
        data: DataFrame with attribute data
        boundary_id_col: Column name for boundary identifiers
        data_id_col: Column name for data identifiers
        
    Returns:
        GeoDataFrame with joined data or None if failed
    """
    try:
        print(f"🔗 Joining boundaries ({len(boundaries)} records) with data ({len(data)} records)")
        print(f"   Boundary ID column: {boundary_id_col}")
        print(f"   Data ID column: {data_id_col}")
        
        # Check if ID columns exist
        if boundary_id_col not in boundaries.columns:
            print(f"❌ Boundary ID column '{boundary_id_col}' not found")
            print(f"   Available columns: {list(boundaries.columns)}")
            return None
            
        if data_id_col not in data.columns:
            print(f"❌ Data ID column '{data_id_col}' not found")
            print(f"   Available columns: {list(data.columns)}")
            return None
        
        # Perform the join
        result = boundaries.merge(
            data,
            left_on=boundary_id_col,
            right_on=data_id_col,
            how='inner'
        )
        
        if len(result) == 0:
            print("❌ Join resulted in 0 records")
            return None
        
        print(f"✅ Successfully joined data: {len(result)} records")
        return result
        
    except Exception as e:
        print(f"❌ Error joining boundaries and data: {e}")
        return None


def create_sample_dataset(year: int = 2020,
                         geographic_level: str = 'tract',
                         state_fips: str = '06',
                         county_fips: str = '037',
                         include_geometry: bool = True) -> Optional[Union[pd.DataFrame, gpd.GeoDataFrame]]:
    """
    Create a real-world sample dataset by combining boundaries and data.
    
    Args:
        year: Census year
        geographic_level: Geographic level
        state_fips: State FIPS code
        county_fips: County FIPS code
        include_geometry: Whether to include geographic boundaries
        
    Returns:
        Combined dataset or None if failed
    """
    print(f"🚀 Creating sample dataset: {geographic_level} level, year {year}, state {state_fips}")
    
    # Step 1: Get boundaries
    boundaries = get_census_boundaries(year, geographic_level, state_fips, county_fips)
    if boundaries is None:
        return None
    
    # Step 2: Get data (when implemented)
    data = get_census_data(year, 'demographics', geographic_level, state_fips, county_fips)
    if data is None:
        print("⚠️ No Census data available, returning boundaries only")
        return boundaries if include_geometry else boundaries.drop(columns=['geometry'])
    
    # Step 3: Join boundaries and data
    result = join_boundaries_and_data(boundaries, data)
    if result is None:
        print("⚠️ Join failed, returning boundaries only")
        return boundaries if include_geometry else boundaries.drop(columns=['geometry'])
    
    return result

# Old helper functions removed - replaced with cleaner, focused functions above


def get_census_county_sample(state_fips: str = "06", 
                            county_fips: str = "037",
                            tract_count: int = 5,
                            population_per_tract: int = 500) -> Union[pd.DataFrame, gpd.GeoDataFrame]:
    """
    Generate a sample county dataset with multiple tracts and synthetic data.
    
    Args:
        state_fips: State FIPS code (default: CA)
        county_fips: County FIPS code (default: Los Angeles)
        tract_count: Number of tracts to include
        population_per_tract: Population per tract
        
    Returns:
        DataFrame or GeoDataFrame with county data
    """
    if not CENSUS_AVAILABLE:
        raise ImportError("Census utilities required. Install with: pip install siege-utilities[geo]")
    
    # Generate multiple tracts using the new function
    all_tracts = []
    for i in range(tract_count):
        tract_fips = f"{200100 + i:06d}"
        tract_data = create_sample_dataset(
            year=2020,
            geographic_level='tract',
            state_fips=state_fips,
            county_fips=county_fips,
            include_geometry=False
        )
        if tract_data is not None:
            tract_data['tract_fips'] = tract_fips
            all_tracts.append(tract_data)
    
    if not all_tracts:
        print("❌ No tract data generated")
        return None
    
    # Combine all tracts
    county_data = pd.concat(all_tracts, ignore_index=True)
    county_data['county_fips'] = county_fips
    county_data['state_fips'] = state_fips
    
    return county_data

def get_metropolitan_sample(cbsa_code: str = "31080",
                           county_count: int = 3,
                           population_per_county: int = 2000) -> Union[pd.DataFrame, gpd.GeoDataFrame]:
    """
    Generate a metropolitan area sample with multiple counties.
    
    Args:
        cbsa_code: CBSA code (default: Los Angeles metro)
        county_count: Number of counties to include
        population_per_county: Population per county
        
    Returns:
        DataFrame or GeoDataFrame with metro data
    """
    if not CENSUS_AVAILABLE:
        raise ImportError("Census utilities required. Install with: pip install siege-utilities[geo]")
    
    # Sample counties for the metro area
    sample_counties = ["037", "059", "065"]  # LA, Orange, Riverside
    
    all_counties = []
    for county_fips in sample_counties[:county_count]:
        county_data = get_census_county_sample(
            state_fips="06",
            county_fips=county_fips,
            tract_count=3,
            population_per_tract=population_per_county // 3
        )
        county_data['cbsa_code'] = cbsa_code
        all_counties.append(county_data)
    
    metro_data = pd.concat(all_counties, ignore_index=True)
    return metro_data

def generate_synthetic_population(demographics: Optional[Dict] = None,
                                 size: int = 1000,
                                 geography_level: str = "tract",
                                 tract_info: Optional[Dict] = None,
                                 include_names: bool = True,
                                 include_addresses: bool = True,
                                 include_income: bool = True,
                                 include_education: bool = True) -> pd.DataFrame:
    """
    Generate synthetic population data matching real demographic patterns.
    
    Args:
        demographics: Dictionary of demographic percentages
        size: Number of people to generate
        geography_level: Geographic level (tract, county, etc.)
        tract_info: Additional tract information
        include_names: Whether to include synthetic names
        include_addresses: Whether to include synthetic addresses
        include_income: Whether to include synthetic income
        include_education: Whether to include synthetic education
        
    Returns:
        DataFrame with synthetic population data
    """
    if not FAKER_AVAILABLE:
        raise ImportError("Faker required. Install with: pip install Faker")
    
    # Default demographics if none provided (using Census standards)
    if demographics is None:
        demographics = {
            "Hispanic or Latino": 0.35,
            "White alone, not Hispanic or Latino": 0.30,
            "Asian alone, not Hispanic or Latino": 0.25,
            "Black or African American alone, not Hispanic or Latino": 0.10
        }
    
    # Generate population based on demographics
    population_data = []
    
    for ethnicity, percentage in demographics.items():
        ethnic_count = int(size * percentage)
        if ethnic_count == 0:
            continue
            
        for _ in range(ethnic_count):
            person = _generate_synthetic_person(
                ethnicity=ethnicity,
                include_names=include_names,
                include_addresses=include_addresses,
                include_income=include_income,
                include_education=include_education
            )
            population_data.append(person)
    
            # Add tract/county information if provided
            if tract_info:
                for person in population_data:
                    person.update({
                        'state_fips': tract_info.get('state_fips'),
                        'county_fips': tract_info.get('county_fips'),
                        'tract_fips': tract_info.get('tract_fips'),
                        'geography_level': geography_level
                    })
            
            # Add category columns for visualization compatibility
            for person in population_data:
                # Map income brackets to categories
                income = person.get('income_bracket', '')
                if 'Less than $25,000' in str(income) or 'Less than $10,000' in str(income) or '$10,000 to $24,999' in str(income):
                    person['income_category'] = 'Low'
                elif '$25,000 to $49,999' in str(income) or '$50,000 to $74,999' in str(income):
                    person['income_category'] = 'Medium'
                else:
                    person['income_category'] = 'High'
                
                # Map education to categories
                education = person.get('education_attainment', '')
                if 'Less than 9th grade' in str(education) or '9th to 12th grade' in str(education) or 'High school graduate' in str(education):
                    person['education_category'] = 'Low'
                elif 'Some college' in str(education) or "Associate's degree" in str(education):
                    person['education_category'] = 'Medium'
                else:
                    person['education_category'] = 'High'
    
    return pd.DataFrame(population_data)

def generate_synthetic_businesses(business_count: int = 500,
                                 industry_distribution: Optional[Dict] = None,
                                 include_locations: bool = True) -> pd.DataFrame:
    """
    Generate synthetic business data with realistic industry patterns.
    
    Args:
        business_count: Number of businesses to generate
        industry_distribution: Dictionary of industry percentages
        include_locations: Whether to include synthetic addresses
        
    Returns:
        DataFrame with synthetic business data
    """
    if not FAKER_AVAILABLE:
        raise ImportError("Faker required. Install with: pip install Faker")
    
    # Default industry distribution
    if industry_distribution is None:
        industry_distribution = {
            "retail": 0.25,
            "healthcare": 0.20,
            "professional_services": 0.15,
            "manufacturing": 0.10,
            "food_services": 0.10,
            "construction": 0.08,
            "technology": 0.07,
            "other": 0.05
        }
    
    businesses = []
    
    for industry, percentage in industry_distribution.items():
        industry_count = int(business_count * percentage)
        if industry_count == 0:
            continue
            
        for _ in range(industry_count):
            business = _generate_synthetic_business(
                industry=industry,
                include_locations=include_locations
            )
            businesses.append(business)
    
    return pd.DataFrame(businesses)

def generate_synthetic_housing(housing_count: int = 300,
                              property_types: Optional[Dict] = None,
                              include_coordinates: bool = True) -> pd.DataFrame:
    """
    Generate synthetic housing data with realistic property patterns.
    
    Args:
        housing_count: Number of housing units to generate
        property_types: Dictionary of property type percentages
        include_coordinates: Whether to include synthetic coordinates
        
    Returns:
        DataFrame with synthetic housing data
    """
    if not FAKER_AVAILABLE:
        raise ImportError("Faker required. Install with: pip install Faker")
    
    # Default property type distribution
    if property_types is None:
        property_types = {
            "single_family": 0.60,
            "apartment": 0.25,
            "condo": 0.10,
            "townhouse": 0.05
        }
    
    housing_units = []
    
    for prop_type, percentage in property_types.items():
        type_count = int(housing_count * percentage)
        if type_count == 0:
            continue
            
        for _ in range(type_count):
            housing = _generate_synthetic_housing_unit(
                property_type=prop_type,
                include_coordinates=include_coordinates
            )
            housing_units.append(housing)
    
    return pd.DataFrame(housing_units)

# Helper functions for synthetic data generation
def _generate_synthetic_person(ethnicity: str,
                              include_names: bool = True,
                              include_addresses: bool = True,
                              include_income: bool = True,
                              include_education: bool = True) -> Dict[str, Any]:
    """Generate a single synthetic person using Census standards."""
    person = {}
    
    if include_names:
        if "Hispanic" in ethnicity:
            person['name'] = faker_es.name()
        elif "Asian" in ethnicity:
            person['name'] = faker_zh.name()
        elif "Black or African American" in ethnicity:
            person['name'] = faker_en.name()  # Could add African-American specific names
        else:
            person['name'] = faker_en.name()
    
    # Age groups using Census standards (18+ for working population)
    age_groups = [
        "18 to 24 years", "25 to 34 years", "35 to 44 years", 
        "45 to 54 years", "55 to 64 years", "65 to 74 years", "75 years and over"
    ]
    age_weights = [0.15, 0.20, 0.20, 0.18, 0.15, 0.08, 0.04]
    person['age_group'] = np.random.choice(age_groups, p=age_weights)
    
    # Race and Hispanic Origin (Census standard)
    person['race'] = ethnicity
    person['hispanic_origin'] = "Hispanic or Latino" if "Hispanic" in ethnicity else "Not Hispanic or Latino"
    
    # Sex (Census standard)
    person['sex'] = np.random.choice(['Male', 'Female'])
    
    if include_addresses:
        person['address'] = faker_en.address()
    
    if include_income:
        # Income brackets using Census standards
        income_brackets = [
            "Less than $10,000", "$10,000 to $14,999", "$15,000 to $19,999",
            "$20,000 to $24,999", "$25,000 to $29,999", "$30,000 to $34,999",
            "$35,000 to $39,999", "$40,000 to $44,999", "$45,000 to $49,999",
            "$50,000 to $59,999", "$60,000 to $74,999", "$75,000 to $99,999",
            "$100,000 to $124,999", "$125,000 to $149,999", "$150,000 to $199,999",
            "$200,000 or more"
        ]
        
        # Adjust weights based on ethnicity (simplified)
        if "Hispanic" in ethnicity:
            income_weights = [0.15, 0.12, 0.10, 0.10, 0.08, 0.08, 0.07, 0.06, 0.05, 0.08, 0.06, 0.03, 0.01, 0.01, 0.00, 0.00]
        elif "Asian" in ethnicity:
            income_weights = [0.05, 0.03, 0.03, 0.04, 0.05, 0.06, 0.07, 0.08, 0.08, 0.12, 0.15, 0.12, 0.08, 0.04, 0.02, 0.01]
        elif "Black or African American" in ethnicity:
            income_weights = [0.12, 0.10, 0.09, 0.09, 0.08, 0.08, 0.07, 0.07, 0.06, 0.10, 0.08, 0.06, 0.03, 0.02, 0.01, 0.00]
        else:  # White
            income_weights = [0.08, 0.06, 0.05, 0.06, 0.06, 0.07, 0.07, 0.07, 0.07, 0.10, 0.12, 0.10, 0.07, 0.04, 0.02, 0.01]
        
        person['income_bracket'] = np.random.choice(income_brackets, p=income_weights)
    
    if include_education:
        # Education levels using Census standards
        education_levels = [
            "Less than 9th grade", "9th to 12th grade, no diploma", 
            "High school graduate (includes equivalency)", "Some college, no degree",
            "Associate's degree", "Bachelor's degree", "Graduate or professional degree"
        ]
        education_weights = [0.08, 0.12, 0.25, 0.20, 0.10, 0.18, 0.07]
        person['education_attainment'] = np.random.choice(education_levels, p=education_weights)
    
    return person

def _generate_synthetic_business(industry: str, include_locations: bool = True) -> Dict[str, Any]:
    """Generate a single synthetic business."""
    business = {
        'name': faker_en.company(),
        'industry': industry,
        'size': np.random.choice(['small', 'medium', 'large'], p=[0.7, 0.2, 0.1]),
        'revenue': np.random.randint(100000, 10000000),
        'employees': np.random.randint(1, 500)
    }
    
    if include_locations:
        business['address'] = faker_en.address()
    
    return business

def _generate_synthetic_housing_unit(property_type: str, include_coordinates: bool = True) -> Dict[str, Any]:
    """Generate a single synthetic housing unit."""
    housing = {
        'address': faker_en.address(),
        'property_type': property_type,
        'bedrooms': np.random.randint(1, 6),
        'bathrooms': np.random.randint(1, 4),
        'square_feet': np.random.randint(800, 4000),
        'year_built': np.random.randint(1950, 2024),
        'value': np.random.randint(200000, 2000000)
    }
    
    if include_coordinates:
        # Generate coordinates in a reasonable range (e.g., Los Angeles area)
        housing['latitude'] = np.random.uniform(33.5, 34.5)
        housing['longitude'] = np.random.uniform(-118.5, -117.5)
    
    return housing

def _generate_synthetic_tract_info(state_fips: str, county_fips: str, tract_fips: str) -> Dict[str, Any]:
    """Generate synthetic tract information using Census standards."""
    return {
        'state_fips': state_fips,
        'county_fips': county_fips,
        'tract_fips': tract_fips,
        'demographics': {
            'Hispanic or Latino': 0.35,
            'White alone, not Hispanic or Latino': 0.30,
            'Asian alone, not Hispanic or Latino': 0.25,
            'Black or African American alone, not Hispanic or Latino': 0.10
        },
        'total_population': 4500,
        'median_income_bracket': '$50,000 to $59,999',
        'housing_units': 1800,
        'median_age_group': '35 to 44 years'
    }

# Synthetic data generation removed from library - will be implemented separately if needed

def _create_tract_geodataframe(population_data: pd.DataFrame, tract_info: Dict) -> gpd.GeoDataFrame:
    """Create a GeoDataFrame with tract boundaries."""
    if not GEOPANDAS_AVAILABLE:
        return population_data
    
    # Create simple tract boundary (rectangle around population points)
    if 'latitude' in population_data.columns and 'longitude' in population_data.columns:
        min_lat, max_lat = population_data['latitude'].min(), population_data['latitude'].max()
        min_lon, max_lon = population_data['longitude'].min(), population_data['longitude'].max()
        
        # Expand boundaries slightly
        lat_buffer = (max_lat - min_lat) * 0.1
        lon_buffer = (max_lon - min_lon) * 0.1
        
        tract_boundary = Polygon([
            (min_lon - lon_buffer, min_lat - lat_buffer),
            (max_lon + lon_buffer, min_lat - lat_buffer),
            (max_lon + lon_buffer, max_lat + lat_buffer),
            (min_lon - lon_buffer, max_lat + lat_buffer)
        ])
        
        # Add tract boundary to population data
        population_data['tract_geometry'] = tract_boundary
        
        return gpd.GeoDataFrame(population_data, geometry='tract_geometry')
    else:
        return population_data

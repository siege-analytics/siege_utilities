#!/usr/bin/env python
# coding: utf-8

# # Census Data + Bivariate Choropleth Recipe
# 
# This notebook demonstrates the complete workflow for:
# 
# 1. **Census Boundary Download** with intelligent FIPS handling
# 2. **Thematic Data Integration** using Census APIs
# 3. **Dataset Recommendation System** for optimal data selection
# 4. **Bivariate Choropleth Mapping** with true 2D color schemes
# 
# ## Prerequisites
# 
# Install required dependencies:
# ```bash
# pip install pandas geopandas matplotlib requests folium
# ```

# In[ ]:


# Import siege utilities
import siege_utilities as su

# Check available Census functions
info = su.get_package_info()
census_functions = [f for f in info['categories'].get('geo', []) if 'census' in f.lower()]
print(f"Available Census functions: {len(census_functions)}")
for func in census_functions[:10]:
    print(f"  - {func}")
if len(census_functions) > 10:
    print(f"  ... and {len(census_functions) - 10} more")


# ## Step 1: FIPS Data Structure
# 
# The unified FIPS data structure handles state identification intelligently:

# In[ ]:


# Demonstrate FIPS data structure (requires pandas)
try:
    # Get unified FIPS data
    fips_data = su.get_unified_fips_data()
    
    # Show examples
    for fips, info in list(fips_data.items())[:5]:
        print(f"FIPS {fips}: {info['name']} ({info['abbreviation']})")
        
    # Test state identifier normalization
    examples = ['CA', 'california', '6', 'Texas', 'NY']
    for example in examples:
        normalized = su.normalize_state_identifier(example)
        print(f"'{example}' -> {normalized}")
        
except ImportError as e:
    print(f"FIPS functions require pandas: {e}")
    print("Install with: pip install pandas")


# ## Step 2: Intelligent Census Dataset Selection
# 
# The dataset recommendation system helps choose optimal Census data:

# In[ ]:


# Demonstrate dataset selection system
try:
    # Get dataset selector
    selector = su.get_census_data_selector()
    
    # Get recommendations for demographic analysis
    recommendations = su.select_census_datasets(
        analysis_type='demographics',
        geography_level='county',
        time_period='recent'
    )

    print("Primary recommendation:")
    primary = recommendations['primary_recommendation']
    print(f"  - {primary['dataset']}: Score {primary['suitability_score']}")
    print(f"    Breakdown: {primary['score_breakdown']}")
    print(f"    Rationale: {primary['rationale']}")

    print("\nAlternatives:")
    for alt in recommendations['alternatives']:
        print(f"  - {alt['dataset']}: Score {alt['suitability_score']}")
        print(f"    Breakdown: {alt['score_breakdown']}")
        print(f"    Rationale: {alt['rationale']}")
        
except ImportError as e:
    print(f"Dataset selection requires pandas: {e}")
except Exception as e:
    print(f"Dataset selection example: {e}")


# ## Step 3: Boundary Download with Year-Specific URLs
# 
# The system handles Census Bureau's changing URL patterns:

# In[ ]:


# Demonstrate boundary download (requires geopandas)
try:
    # Download county boundaries for California
    boundaries = su.get_census_boundaries(
        year=2020,
        geographic_level='county',
        state_fips='06'  # California FIPS code
    )
    
    print(f"✅ Downloaded {len(boundaries)} county boundaries")
    print(f"📋 Available columns: {list(boundaries.columns)}")
    
except ImportError as e:
    print(f"Boundary download requires geopandas: {e}")
    print("Install with: pip install geopandas")


# ## Step 4: Thematic Data Integration
# 
# Combine Census boundaries with thematic data from APIs:

# In[ ]:


# Simulate thematic data (in practice, get from Census API)
import pandas as pd
import numpy as np

try:
    # Create sample thematic data
    np.random.seed(42)
    sample_data = pd.DataFrame({
        'GEOID': [f'06{str(i).zfill(3)}' for i in range(1, 59)],  # CA counties
        'population_density': np.random.lognormal(5, 1, 58),
        'median_income': np.random.normal(70000, 20000, 58)
    })
    
    print("Sample thematic data:")
    print(sample_data.head())
    
except Exception as e:
    print(f"Error creating sample data: {e}")


# ## Step 5: True Bivariate Choropleth Mapping
# 
# Create professional bivariate maps with proper 2D color schemes:

# In[ ]:


# Create bivariate choropleth map
try:
    # This function now uses true 2D color matrix
    bivariate_map = su.create_bivariate_choropleth(
        data=sample_data,
        geodata=boundaries,  # From step 3
        location_column='GEOID',
        value_column1='population_density',
        value_column2='median_income',
        title='Population Density vs Median Income',
        color_scheme='default'
    )
    
    print("Bivariate choropleth created successfully!")
    print("Features:")
    print("  - True 2D color matrix (not fake 1D colormap)")
    print("  - Quantile-based classification for both variables")
    print("  - Professional 3x3 legend grid")
    print("  - Proper bivariate color scheme")
    
except ImportError as e:
    print(f"Bivariate mapping requires matplotlib + geopandas: {e}")
    print("Install with: pip install matplotlib geopandas")


# ## Step 6: Dataset Relationship Mapping
# 
# Understand which Census datasets work well together:

# In[ ]:


# Explore dataset relationships
try:
    # Get dataset mapper
    mapper = su.get_census_dataset_mapper()
    
    # Find the best dataset for a specific analysis
    best_dataset = su.get_best_dataset_for_analysis(
        analysis_type='economic',
        geography_level='tract',
        time_sensitivity='current'
    )
    
    print(f"Best dataset for economic analysis: {best_dataset}")
    
    # Compare two datasets
    comparison = su.compare_census_datasets('acs_5yr', 'decennial')
    print(f"Dataset comparison: {comparison}")
    
except ImportError as e:
    print(f"Dataset mapping requires pandas: {e}")
except Exception as e:
    print(f"Dataset mapping example: {e}")


# ## Summary: Complete Workflow
# 
# This recipe demonstrates the complete Census + bivariate mapping workflow:
# 
# ### 1. Intelligent FIPS Handling
# - Unified data structure with FIPS, name, and abbreviation
# - Smart state identifier normalization
# - Integrated FIPS validation in URL construction
# 
# ### 2. Dataset Intelligence
# - Automatic dataset recommendations
# - Compatibility analysis between datasets
# - Analysis-type specific guidance
# 
# ### 3. Robust Boundary Download
# - Year-specific URL pattern handling
# - Dynamic Census directory discovery
# - Graceful handling of URL changes
# 
# ### 4. Professional Bivariate Mapping
# - True 2D color matrix (not fake 1D)
# - Proper quantile classification
# - 3x3 bivariate legend grid
# 
# ### Key Improvements Made
# 
# 1. **Fixed URL Construction**: Now handles Census Bureau's changing directory structures
# 2. **Unified FIPS Structure**: Single source of truth for state/territory identification
# 3. **True Bivariate Colors**: Replaced fake 1D colormap with proper 2D matrix
# 4. **Intelligent Dataset Selection**: Automated recommendations based on analysis needs
# 
# The result is a professional-grade system for Census data analysis and visualization.

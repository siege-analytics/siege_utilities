# Recipe Test Script
import sys
import os
sys.path.append('.')

# Code block 1
from siege_utilities.geo.census_data_selector import select_census_datasets

# Get recommendations for demographic analysis at tract level
recommendations = select_census_datasets(
    analysis_type="demographics",
    geography_level="tract",
    variables=["population", "income", "education"]
)

print(recommendations)

# Code block 2
from siege_utilities.geo.census_data_selector import get_analysis_approach

# Get comprehensive analysis approach
approach = get_analysis_approach(
    analysis_type="housing",
    geography_level="county",
    time_constraints="comprehensive"
)

print(approach)

# Code block 3
# Use the recommended API endpoint
api_endpoint = recommendations["primary_recommendation"]["api_endpoint"]

# Download data using the enhanced Census utilities
from siege_utilities.geo.spatial_data import census_source

# The system automatically handles the right dataset selection
data = census_source.get_demographic_data(
    year=2020,
    geographic_level="tract",
    state_fips="06",  # California
    variables=["B01003_001E", "B19013_001E"]  # Population, Median Income
)

# Code block 4
recommendations = select_census_datasets(
    analysis_type="demographics",
    geography_level="tract",
    variables=["income", "education", "population"]
)

# Code block 5
recommendations = select_census_datasets(
    analysis_type="business",
    geography_level="county",
    variables=["business_count", "employment", "industry"]
)

# Code block 6
recommendations = select_census_datasets(
    analysis_type="demographics",
    geography_level="cbsa",
    time_period="2023"
)

# Code block 7
# ❌ Wrong - 1-year ACS for tract-level analysis
data = census_source.get_demographic_data(
    year=2020,
    geographic_level="tract",
    survey_type="acs1"  # May not be available
)

# ✅ Right - 5-year ACS for tract-level analysis
data = census_source.get_demographic_data(
    year=2020,
    geographic_level="tract",
    survey_type="acs5"  # Always available
)

# Code block 8
# ❌ Wrong - Comparing different survey types directly
decennial_pop = decennial_data["total_population"]
acs_pop = acs_data["total_population"]
difference = decennial_pop - acs_pop  # Apples vs. oranges!

# ✅ Right - Understand the differences
# Decennial: Official count as of April 1, 2020
# ACS 5-year: Average over 2016-2020
# Population Estimates: Current estimate for 2023

# Code block 9
# ✅ Right - Include margins of error in analysis
from siege_utilities.geo.census_data_selector import get_analysis_approach

approach = get_analysis_approach("demographics", "tract")
print(approach["methodology_notes"])
# Output: "Check margins of error for small geographies"

# Code block 10
# ❌ Wrong - Using outdated data
data = census_source.get_demographic_data(year=2010)  # 13+ years old!

# ✅ Right - Let the system recommend current data
recommendations = select_census_datasets(
    analysis_type="demographics",
    geography_level="county",
    time_period="2023"
)

# Code block 11
from siege_utilities.geo.census_data_selector import select_census_datasets

# Get recommendations for comprehensive analysis
demographics = select_census_datasets("demographics", "tract")
housing = select_census_datasets("housing", "tract")
business = select_census_datasets("business", "county")

# Combine insights from multiple sources
comprehensive_analysis = {
    "demographics": demographics["primary_recommendation"],
    "housing": housing["primary_recommendation"],
    "business": business["primary_recommendation"],
    "integration_notes": [
        "Use ACS 5-year for tract-level demographics and housing",
        "Use Economic Census for county-level business data",
        "Spatially join business data to demographic areas"
    ]
}

# Code block 12
# ✅ Right - Consistent ACS 5-year estimates for trends
years = [2010, 2015, 2020]
trend_data = []

for year in years:
    data = census_source.get_demographic_data(
        year=year,
        geographic_level="tract",
        survey_type="acs5"
    )
    trend_data.append(data)

# Analyze trends over time
trend_analysis = analyze_trends(trend_data)

# Code block 13
from siege_utilities.geo.census_data_selector import get_analysis_approach

approach = get_analysis_approach("demographics", "tract")
print("Quality Checks:")
for check in approach["quality_checks"]:
    print(f"  - {check}")

print("\nReporting Considerations:")
for consideration in approach["reporting_considerations"]:
    print(f"  - {consideration}")

# Code block 14
   from siege_utilities.geo.census_data_selector import select_census_datasets
   
   recommendations = select_census_datasets("demographics", "tract")

# Code block 15
   primary_dataset = recommendations["primary_recommendation"]
   print(f"Use {primary_dataset['dataset']} for your analysis")

# Code block 16
   from siege_utilities.geo.spatial_data import census_source
   
   data = census_source.get_demographic_data(
       year=2020,
       geographic_level="tract",
       state_fips="06"
   )


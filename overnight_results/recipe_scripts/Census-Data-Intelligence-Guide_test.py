#!/usr/bin/env python3
# Test script extracted from recipe: Census-Data-Intelligence-Guide.md
# Generated: 2025-09-11T02:20:10.672777

import sys
import os
import traceback

# Add current directory to path
sys.path.append('.')

# Add error handling wrapper
def safe_execute():
    try:
        print("Testing recipe code blocks...")
        
        # Code block 1
        print('Executing code block 1...')
        from siege_utilities.geo.census_data_selector import select_census_datasets
        
        # Get recommendations for demographic analysis at tract level
        recommendations = select_census_datasets(
            analysis_type="demographics",
            geography_level="tract",
            variables=["population", "income", "education"]
        )
        
        print(recommendations)

        # Code block 2
        print('Executing code block 2...')
        from siege_utilities.geo.census_data_selector import get_analysis_approach
        
        # Get comprehensive analysis approach
        approach = get_analysis_approach(
            analysis_type="housing",
            geography_level="county",
            time_constraints="comprehensive"
        )
        
        print(approach)

        # Code block 3
        print('Executing code block 3...')
        # Use the recommended API endpoint
        api_endpoint = recommendations["primary_recommendation"]["api_endpoint"]
        
        # Download geographic boundaries using the enhanced Census utilities
        from siege_utilities.geo.spatial_data import census_source
        
        # The system automatically handles the right dataset selection for boundaries
        boundaries = census_source.get_geographic_boundaries(
            year=2020,
            geographic_level="tract",
            state_fips="06"  # California
        )
        
        print(f"Downloaded {len(boundaries)} census tracts for California")
        print(f"Boundary data columns: {list(boundaries.columns)}")
        print(f"Sample tract GEOID: {boundaries['geoid'].iloc[0] if len(boundaries) > 0 else 'No data'}")

        # Code block 4
        print('Executing code block 4...')
        recommendations = select_census_datasets(
            analysis_type="demographics",
            geography_level="tract",
            variables=["income", "education", "population"]
        )

        # Code block 5
        print('Executing code block 5...')
        recommendations = select_census_datasets(
            analysis_type="business",
            geography_level="county",
            variables=["business_count", "employment", "industry"]
        )

        # Code block 6
        print('Executing code block 6...')
        recommendations = select_census_datasets(
            analysis_type="demographics",
            geography_level="cbsa",
            time_period="2023"
        )

        # Code block 7
        print('Executing code block 7...')
        # Demonstrate boundary type discovery for different geographic levels
        available_boundaries = census_source.get_available_boundary_types(2020)
        print(f"Available boundary types for 2020: {list(available_boundaries.keys())}")
        
        # Test different geographic levels
        test_levels = ['state', 'county', 'tract']
        for level in test_levels:
            if level in available_boundaries:
                print(f"✅ {level.upper()} boundaries available")
            else:
                print(f"❌ {level.upper()} boundaries not available")

        # Code block 8
        print('Executing code block 8...')
        # ✅ Right - Understand the differences between survey types
        print("Survey type differences:")
        print("- Decennial: Official count as of April 1, 2020")
        print("- ACS 5-year: Average over 2016-2020")
        print("- Population Estimates: Current estimate for 2023")
        print("- Never compare different survey types directly!")

        # Code block 9
        print('Executing code block 9...')
        # ✅ Right - Include margins of error in analysis
        from siege_utilities.geo.census_data_selector import get_analysis_approach
        
        approach = get_analysis_approach("demographics", "tract")
        print(approach["methodology_notes"])
        # Output: "Check margins of error for small geographies"

        # Code block 10
        print('Executing code block 10...')
        # ❌ Wrong - Using outdated data (2010 is 13+ years old!)
        print("❌ Don't use outdated data - 2010 Census is 13+ years old!")
        
        # ✅ Right - Let the system recommend current data
        recommendations = select_census_datasets(
            analysis_type="demographics",
            geography_level="county",
            time_period="2023"
        )

        # Code block 11
        print('Executing code block 11...')
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
        print('Executing code block 12...')
        # ✅ Right - Consistent ACS 5-year estimates for trends
        years = [2010, 2015, 2020]
        trend_data = []
        
        for year in years:
            # Test boundary availability for different years
            boundaries = census_source.get_geographic_boundaries(
                year=year,
                geographic_level="tract",
                state_fips="06"  # California
            )
            if boundaries is not None:
                trend_data.append(f"Year {year}: {len(boundaries)} tracts available")
            else:
                trend_data.append(f"Year {year}: No data available")
        
        # Analyze trends over time
        print("Trend analysis results:")
        for result in trend_data:
            print(f"  - {result}")

        # Code block 13
        print('Executing code block 13...')
        from siege_utilities.geo.census_data_selector import get_analysis_approach
        
        approach = get_analysis_approach("demographics", "tract")
        print("Quality Checks:")
        for check in approach["quality_checks"]:
            print(f"  - {check}")
        
        print("\nReporting Considerations:")
        for consideration in approach["reporting_considerations"]:
            print(f"  - {consideration}")

        return True, "All code blocks executed successfully"
    except Exception as e:
        return False, f"Error: {e}\nTraceback: {traceback.format_exc()}"

if __name__ == "__main__":
    success, message = safe_execute()
    if success:
        print("✅ Recipe code executed successfully")
    else:
        print(f"❌ Recipe code failed: {message}")

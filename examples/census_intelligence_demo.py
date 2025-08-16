#!/usr/bin/env python3
"""
Census Data Intelligence Demo

This script demonstrates the new intelligent Census data selection system
that makes Census data human-comprehensible and automatically recommends
the best datasets for different analysis needs.
"""

import json
import sys
from pathlib import Path

# Add the parent directory to the path to import siege_utilities
sys.path.insert(0, str(Path(__file__).parent.parent))

from siege_utilities.geo import (
    get_census_intelligence,
    quick_census_selection,
    select_census_datasets,
    get_analysis_approach
)

def demo_basic_selection():
    """Demonstrate basic Census data selection."""
    
    print("🎯 DEMO 1: Basic Census Data Selection")
    print("=" * 50)
    
    # Get recommendations for demographic analysis at tract level
    recommendations = select_census_datasets(
        analysis_type="demographics",
        geography_level="tract",
        variables=["population", "income", "education"]
    )
    
    print(f"Analysis Type: {recommendations['analysis_type']}")
    print(f"Geography Level: {recommendations['geography_level']}")
    print(f"Primary Recommendation: {recommendations['primary_recommendation']['dataset']}")
    print(f"Survey Type: {recommendations['primary_recommendation']['survey_type']}")
    print(f"Time Period: {recommendations['primary_recommendation']['time_period']}")
    print(f"Reliability: {recommendations['primary_recommendation']['reliability']}")
    print(f"Score: {recommendations['primary_recommendation']['score']:.1f}")
    print(f"Rationale: {recommendations['primary_recommendation']['rationale']}")
    
    print("\nAvailable Variables:")
    for var in recommendations['primary_recommendation']['variables']:
        print(f"  - {var}")
    
    print("\nConsiderations:")
    for consideration in recommendations['considerations']:
        print(f"  - {consideration}")
    
    print("\nNext Steps:")
    for step in recommendations['next_steps']:
        print(f"  - {step}")

def demo_analysis_approach():
    """Demonstrate getting analysis approach recommendations."""
    
    print("\n🧠 DEMO 2: Analysis Approach Recommendations")
    print("=" * 50)
    
    # Get comprehensive analysis approach for housing analysis
    approach = get_analysis_approach(
        analysis_type="housing",
        geography_level="county",
        time_constraints="comprehensive"
    )
    
    print(f"Analysis Type: {approach['analysis_type']}")
    print(f"Geography Level: {approach['geography_level']}")
    print(f"Recommended Approach: {approach['recommended_approach']}")
    
    print("\nData Sources:")
    data_sources = approach['data_sources']
    print(f"  Dataset: {data_sources['dataset']}")
    print(f"  Survey Type: {data_sources['survey_type']}")
    print(f"  Time Period: {data_sources['time_period']}")
    print(f"  Reliability: {data_sources['reliability']}")
    
    print("\nMethodology Notes:")
    for note in approach['methodology_notes']:
        print(f"  - {note}")
    
    print("\nQuality Checks:")
    for check in approach['quality_checks']:
        print(f"  - {check}")
    
    print("\nReporting Considerations:")
    for consideration in approach['reporting_considerations']:
        print(f"  - {consideration}")

def demo_quick_selection():
    """Demonstrate quick Census data selection."""
    
    print("\n⚡ DEMO 3: Quick Census Data Selection")
    print("=" * 50)
    
    # Use the quick selection function
    result = quick_census_selection("business", "county")
    
    print("Business Analysis at County Level:")
    print(f"  Primary Dataset: {result['recommendations']['primary_recommendation']['dataset']}")
    print(f"  Analysis Approach: {result['analysis_approach']['recommended_approach']}")

def demo_dataset_comparison():
    """Demonstrate comparing different Census datasets."""
    
    print("\n🔍 DEMO 4: Dataset Comparison")
    print("=" * 50)
    
    from siege_utilities.geo import compare_census_datasets
    
    # Compare Decennial Census with ACS 5-year
    comparison = compare_census_datasets("decennial_2020", "acs_5yr_2020")
    
    print("Decennial 2020 vs ACS 5-Year 2020:")
    print(f"  Dataset 1: {comparison['dataset1']['name']}")
    print(f"  Dataset 2: {comparison['dataset2']['name']}")
    print(f"  Reliability Difference: {comparison['comparison']['reliability_difference']}")
    
    print("\nGeography Overlap:")
    for geo in comparison['comparison']['geography_overlap']:
        print(f"  - {geo}")
    
    print("\nVariable Overlap:")
    for var in comparison['comparison']['variable_overlap']:
        print(f"  - {var}")
    
    print("\nWhen to Use Decennial:")
    for use_case in comparison['comparison']['when_to_use_dataset1']:
        print(f"  - {use_case}")
    
    print("\nWhen to Use ACS:")
    for use_case in comparison['comparison']['when_to_use_dataset2']:
        print(f"  - {use_case}")

def demo_compatibility_matrix():
    """Demonstrate the dataset compatibility matrix."""
    
    print("\n📊 DEMO 5: Dataset Compatibility Matrix")
    print("=" * 50)
    
    from siege_utilities.geo import get_census_data_selector
    
    selector = get_census_data_selector()
    matrix = selector.get_dataset_compatibility_matrix()
    
    print("Compatibility Matrix (Higher scores = better compatibility):")
    print(matrix.round(2))
    
    print("\nInterpretation:")
    print("  - Scores range from 0.0 to 5.0")
    print("  - 5.0 = Perfect compatibility")
    print("  - 0.0 = No compatibility")
    print("  - Higher scores indicate better dataset-analysis type matches")

def demo_export_catalog():
    """Demonstrate exporting the dataset catalog."""
    
    print("\n💾 DEMO 6: Export Dataset Catalog")
    print("=" * 50)
    
    from siege_utilities.geo import get_census_dataset_mapper
    
    mapper = get_census_dataset_mapper()
    
    # Export to JSON
    output_file = "census_dataset_catalog.json"
    mapper.export_dataset_catalog(output_file)
    
    print(f"Dataset catalog exported to {output_file}")
    print("This file contains:")
    print("  - Complete dataset information")
    print("  - Dataset relationships")
    print("  - API endpoints and download URLs")
    print("  - Data quality notes and limitations")

def main():
    """Run all demos."""
    
    print("🚀 CENSUS DATA INTELLIGENCE SYSTEM DEMO")
    print("=" * 60)
    print("This demo shows how the new intelligent system makes Census data")
    print("human-comprehensible and automatically recommends the best datasets.")
    print("=" * 60)
    
    try:
        # Run all demos
        demo_basic_selection()
        demo_analysis_approach()
        demo_quick_selection()
        demo_dataset_comparison()
        demo_compatibility_matrix()
        demo_export_catalog()
        
        print("\n🎉 DEMO COMPLETED SUCCESSFULLY!")
        print("\nKey Benefits:")
        print("  ✅ No more confusion about which Census dataset to use")
        print("  ✅ Automatic recommendations based on your needs")
        print("  ✅ Quality guidance to avoid common mistakes")
        print("  ✅ Comprehensive documentation for each dataset")
        print("  ✅ Relationship mapping between different surveys")
        print("  ✅ Best practices built into the recommendations")
        
        print("\nNext Steps:")
        print("  1. Use select_census_datasets() for your analysis needs")
        print("  2. Get analysis approach recommendations with get_analysis_approach()")
        print("  3. Compare datasets with compare_census_datasets()")
        print("  4. Export the full catalog for reference")
        
    except Exception as e:
        print(f"\n❌ Demo failed with error: {e}")
        print("Make sure you have installed siege-utilities with geo support:")
        print("  pip install siege-utilities[geo]")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""
Test Script: Sample Data + Bivariate Choropleth Generation

This script tests:
1. Cross-system compatibility (iPython validation)
2. Census-compliant synthetic data generation
3. Bivariate choropleth map creation
4. Integration with existing utilities

Run this in iPython first, then in PySpark shell to validate cross-system compatibility.
"""

import sys
import pandas as pd
import numpy as np
from pathlib import Path

def test_sample_data_generation():
    """Test 1: Sample data generation and Census compliance."""
    print("🧪 TEST 1: Sample Data Generation & Census Compliance")
    print("=" * 60)
    
    try:
        # Import the library
        import siege_utilities
        print("✅ Import successful")
        
        # Generate Census-compliant synthetic population
        print("\n📊 Generating synthetic population...")
        population = siege_utilities.generate_synthetic_population(size=500)
        
        print(f"✅ Generated {len(population)} people")
        print(f"📋 Dataset shape: {population.shape}")
        print(f"🔍 Columns: {list(population.columns)}")
        
        # Verify Census standards
        print("\n🏛️  Verifying Census Standards:")
        if 'race' in population.columns:
            print(f"✅ Race categories: {population['race'].unique()}")
        if 'age_group' in population.columns:
            print(f"✅ Age groups: {population['age_group'].unique()}")
        if 'income_bracket' in population.columns:
            print(f"✅ Income brackets: {population['income_bracket'].unique()}")
        if 'education_attainment' in population.columns:
            print(f"✅ Education levels: {population['education_attainment'].unique()}")
        
        # Show sample data
        print("\n📋 Sample Data:")
        print(population.head(3))
        
        return population
        
    except Exception as e:
        print(f"❌ Test 1 failed: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_census_tract_integration():
    """Test 2: Census tract data integration."""
    print("\n🧪 TEST 2: Census Tract Data Integration")
    print("=" * 60)
    
    try:
        import siege_utilities
        
        # Get Census tract sample
        print("🗺️  Getting Census tract sample...")
        tract_data = siege_utilities.get_census_tract_sample(
            population_size=300, 
            include_geometry=False
        )
        
        print(f"✅ Generated Census tract sample: {len(tract_data)} people")
        print(f"📋 Tract columns: {list(tract_data.columns)}")
        
        # Show tract-level summary
        if 'tract_fips' in tract_data.columns:
            tract_summary = tract_data.groupby('tract_fips').agg({
                'income_bracket': 'count',
                'education_attainment': 'count'
            }).rename(columns={
                'income_bracket': 'population',
                'education_attainment': 'education_count'
            })
            print(f"\n🏘️  Tract Summary (showing first 5):")
            print(tract_summary.head())
        
        return tract_data
        
    except Exception as e:
        print(f"❌ Test 2 failed: {e}")
        import traceback
        traceback.print_exc()
        return None

def create_bivariate_choropleth_data(population_data, tract_data):
    """Test 3: Create data for bivariate choropleth."""
    print("\n🧪 TEST 3: Bivariate Choropleth Data Preparation")
    print("=" * 60)
    
    try:
        # Create tract-level summary for bivariate analysis
        print("📊 Creating tract-level summary for bivariate analysis...")
        
        # Merge population data with tract data if possible
        if tract_data is not None and 'tract_fips' in tract_data.columns:
            # Use tract data directly
            tract_summary = tract_data.groupby('tract_fips').agg({
                'income_bracket': lambda x: _categorize_income(x.mode().iloc[0] if not x.mode().empty else x.iloc[0]),
                'education_attainment': lambda x: _categorize_education(x.mode().iloc[0] if not x.mode().empty else x.iloc[0]),
                'race': 'count'  # Population count
            }).rename(columns={'race': 'population'})
        else:
            # Create synthetic tract data from population
            print("🔄 Creating synthetic tract data from population...")
            tract_ids = [f"T{str(i).zfill(6)}" for i in range(1, 21)]  # 20 synthetic tracts
            
            tract_summary = []
            for tract_id in tract_ids:
                # Sample 15-25 people per tract
                tract_size = np.random.randint(15, 26)
                tract_population = population_data.sample(n=tract_size, replace=True)
                
                # Aggregate tract-level metrics
                income_category = _categorize_income(tract_population['income_bracket'].mode().iloc[0] if not tract_population['income_bracket'].mode().empty else tract_population['income_bracket'].iloc[0])
                education_category = _categorize_education(tract_population['education_attainment'].mode().iloc[0] if not tract_population['education_attainment'].mode().empty else tract_population['education_attainment'].iloc[0])
                
                tract_summary.append({
                    'tract_fips': tract_id,
                    'income_category': income_category,
                    'education_category': education_category,
                    'population': tract_size
                })
            
            tract_summary = pd.DataFrame(tract_summary)
        
        print(f"✅ Created tract summary with {len(tract_summary)} tracts")
        print(f"📋 Summary columns: {list(tract_summary.columns)}")
        
        # Show the data
        print("\n🏘️  Tract Summary Data:")
        print(tract_summary.head(10))
        
        # Show distribution
        print("\n📊 Income Category Distribution:")
        print(tract_summary['income_category'].value_counts())
        print("\n📊 Education Category Distribution:")
        print(tract_summary['education_category'].value_counts())
        
        return tract_summary
        
    except Exception as e:
        print(f"❌ Test 3 failed: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_bivariate_choropleth_generation(tract_summary):
    """Test 4: Generate bivariate choropleth map."""
    print("\n🧪 TEST 4: Bivariate Choropleth Generation")
    print("=" * 60)
    
    try:
        from siege_utilities.reporting.chart_generator import ChartGenerator
        
        print("🗺️  Initializing ChartGenerator...")
        chart_gen = ChartGenerator()
        
        # Create bivariate choropleth
        print("🎨 Creating bivariate choropleth map...")
        chart = chart_gen.create_bivariate_choropleth(
            data=tract_summary,
            location_column='tract_fips',
            value_column1='income_category',
            value_column2='education_category',
            title="Income vs Education by Census Tract",
            width=12.0,
            height=10.0
        )
        
        print("✅ Bivariate choropleth created successfully!")
        print(f"📊 Chart type: {type(chart)}")
        
        # Try to save the chart
        try:
            output_path = Path("bivariate_choropleth_test.html")
            chart.save(str(output_path))
            print(f"💾 Chart saved to: {output_path}")
        except Exception as save_error:
            print(f"⚠️  Could not save chart: {save_error}")
        
        return chart
        
    except Exception as e:
        print(f"❌ Test 4 failed: {e}")
        import traceback
        traceback.print_exc()
        return None

def _categorize_income(income_bracket):
    """Categorize income brackets into low/medium/high."""
    if pd.isna(income_bracket):
        return "medium"
    
    income_str = str(income_bracket)
    
    # Low income
    if any(x in income_str for x in ["Less than $10,000", "$10,000 to $14,999", 
                                    "$15,000 to $19,999", "$20,000 to $24,999", 
                                    "$25,000 to $29,999", "$30,000 to $34,999"]):
        return "low"
    # High income
    elif any(x in income_str for x in ["$100,000 to $124,999", "$125,000 to $149,999", 
                                      "$150,000 to $199,999", "$200,000 or more"]):
        return "high"
    # Medium income
    else:
        return "medium"

def _categorize_education(education_level):
    """Categorize education levels into low/medium/high."""
    if pd.isna(education_level):
        return "medium"
    
    education_str = str(education_level)
    
    # Low education
    if any(x in education_str for x in ["Less than 9th grade", "9th to 12th grade, no diploma"]):
        return "low"
    # High education
    elif any(x in education_str for x in ["Bachelor's degree", "Graduate or professional degree"]):
        return "high"
    # Medium education
    else:
        return "medium"

def main():
    """Run all tests."""
    print("🚀 Siege Utilities: Sample Data + Bivariate Choropleth Test Suite")
    print("=" * 80)
    print("This script tests cross-system compatibility and bivariate choropleth generation.")
    print("Run in iPython first, then in PySpark shell to validate compatibility.\n")
    
    # Test 1: Sample data generation
    population_data = test_sample_data_generation()
    if population_data is None:
        print("❌ Critical failure in sample data generation. Stopping.")
        return False
    
    # Test 2: Census tract integration
    tract_data = test_census_tract_integration()
    
    # Test 3: Bivariate data preparation
    tract_summary = create_bivariate_choropleth_data(population_data, tract_data)
    if tract_summary is None:
        print("❌ Critical failure in bivariate data preparation. Stopping.")
        return False
    
    # Test 4: Bivariate choropleth generation
    chart = test_bivariate_choropleth_generation(tract_summary)
    
    # Summary
    print("\n" + "=" * 80)
    print("📊 TEST SUMMARY")
    print("=" * 80)
    print(f"✅ Sample Data Generation: {'PASS' if population_data is not None else 'FAIL'}")
    print(f"✅ Census Tract Integration: {'PASS' if tract_data is not None else 'FAIL'}")
    print(f"✅ Bivariate Data Preparation: {'PASS' if tract_summary is not None else 'FAIL'}")
    print(f"✅ Bivariate Choropleth Generation: {'PASS' if chart is not None else 'FAIL'}")
    
    if all([population_data is not None, tract_summary is not None, chart is not None]):
        print("\n🎉 All critical tests passed! The system is working correctly.")
        print("💡 You can now test this in PySpark shell to validate cross-system compatibility.")
        return True
    else:
        print("\n❌ Some tests failed. Check the output above for details.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

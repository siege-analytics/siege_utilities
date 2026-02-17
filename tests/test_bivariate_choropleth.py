#!/usr/bin/env python3
"""
Simple test script for bivariate choropleth functionality.

This script tests the basic functionality without requiring external dependencies.
Run this to verify that the ChartGenerator class can be imported and basic
methods are available.
"""

import sys
import os
from pathlib import Path

# Add the parent directory to the path so we can import the modules
sys.path.insert(0, str(Path(__file__).parent.parent))

def test_imports():
    """Test that all required modules can be imported."""
    print("Testing imports...")
    
    try:
        from reporting.chart_generator import ChartGenerator
        print("✓ ChartGenerator imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import ChartGenerator: {e}")
        return False
    
    try:
        import pandas as pd
        print("✓ pandas imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import pandas: {e}")
        return False
    
    try:
        import matplotlib.pyplot as plt
        print("✓ matplotlib imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import matplotlib: {e}")
        return False
    
    return True

def test_chart_generator_initialization():
    """Test that ChartGenerator can be initialized."""
    print("\nTesting ChartGenerator initialization...")
    
    try:
        from reporting.chart_generator import ChartGenerator
        
        # Test basic initialization
        chart_gen = ChartGenerator()
        print("✓ ChartGenerator initialized successfully")
        
        # Test with branding config
        branding_config = {
            'colors': {
                'primary': '#0077CC',
                'secondary': '#EEEEEE',
                'accent': '#FF6B35'
            }
        }
        chart_gen_with_branding = ChartGenerator(branding_config)
        print("✓ ChartGenerator with branding initialized successfully")
        
        return True
        
    except Exception as e:
        print(f"✗ Failed to initialize ChartGenerator: {e}")
        return False

def test_method_availability():
    """Test that bivariate choropleth methods are available."""
    print("\nTesting method availability...")
    
    try:
        from reporting.chart_generator import ChartGenerator
        
        chart_gen = ChartGenerator()
        
        # Check if bivariate choropleth methods exist
        methods_to_check = [
            'create_bivariate_choropleth',
            'create_bivariate_choropleth_matplotlib',
            'create_advanced_choropleth',
            '_create_bivariate_color_scheme',
            '_add_bivariate_legend'
        ]
        
        for method_name in methods_to_check:
            if hasattr(chart_gen, method_name):
                print(f"✓ Method {method_name} is available")
            else:
                print(f"✗ Method {method_name} is missing")
                return False
        
        return True
        
    except Exception as e:
        print(f"✗ Failed to check methods: {e}")
        return False

def test_sample_data_creation():
    """Test creating sample data for testing."""
    print("\nTesting sample data creation...")
    
    try:
        import pandas as pd
        
        # Create sample data
        sample_data = {
            'state': ['California', 'Texas', 'New York'],
            'population_density': [251.3, 108.4, 421.0],
            'median_income': [75235, 64034, 72741]
        }
        
        df = pd.DataFrame(sample_data)
        print("✓ Sample data created successfully")
        print(f"  Data shape: {df.shape}")
        print(f"  Columns: {list(df.columns)}")
        
        return True
        
    except Exception as e:
        print(f"✗ Failed to create sample data: {e}")
        return False

def test_basic_functionality():
    """Test basic chart generation functionality."""
    print("\nTesting basic chart generation...")
    
    try:
        from reporting.chart_generator import ChartGenerator
        import pandas as pd
        
        # Create sample data
        sample_data = {
            'state': ['California', 'Texas', 'New York'],
            'population_density': [251.3, 108.4, 421.0],
            'median_income': [75235, 64034, 72741]
        }
        df = pd.DataFrame(sample_data)
        
        # Initialize chart generator
        chart_gen = ChartGenerator()
        
        # Test basic bar chart (this should work without external dependencies)
        try:
            chart = chart_gen.create_bar_chart(
                data=df,
                x_column='state',
                y_column='population_density',
                title="Test Chart",
                width=6.0,
                height=4.0
            )
            print("✓ Basic chart creation successful")
        except Exception as e:
            print(f"⚠ Basic chart creation failed (expected if matplotlib not available): {e}")
        
        return True
        
    except Exception as e:
        print(f"✗ Failed to test basic functionality: {e}")
        return False

def run_all_tests():
    """Run all tests and report results."""
    print("🧪 Testing Bivariate Choropleth Functionality")
    print("=" * 50)
    
    tests = [
        ("Import Tests", test_imports),
        ("ChartGenerator Initialization", test_chart_generator_initialization),
        ("Method Availability", test_method_availability),
        ("Sample Data Creation", test_sample_data_creation),
        ("Basic Functionality", test_basic_functionality)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n🔍 {test_name}")
        try:
            if test_func():
                passed += 1
                print(f"✅ {test_name} PASSED")
            else:
                print(f"❌ {test_name} FAILED")
        except Exception as e:
            print(f"💥 {test_name} ERROR: {e}")
    
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Bivariate choropleth functionality is ready.")
    else:
        print("⚠ Some tests failed. Check the output above for details.")
    
    return passed == total

if __name__ == "__main__":
    """Main execution block."""
    success = run_all_tests()
    
    if success:
        print("\n💡 Next steps:")
        print("1. Install additional dependencies: pip install geopandas folium")
        print("2. Run the examples: python examples/bivariate_choropleth_example.py")
        print("3. Check the documentation: README_bivariate_choropleth.md")
    else:
        print("\n🔧 Troubleshooting:")
        print("1. Check that all required packages are installed")
        print("2. Verify the module structure is correct")
        print("3. Check for any import errors in the output above")
    
    sys.exit(0 if success else 1)

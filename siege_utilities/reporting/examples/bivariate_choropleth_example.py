"""
Bivariate Choropleth Map Examples for siege_utilities ChartGenerator

This module demonstrates how to create bivariate choropleth maps using the enhanced
ChartGenerator class. Bivariate choropleth maps show the relationship between two
variables across geographic regions using a two-dimensional color scheme.

Examples include:
1. Basic bivariate choropleth using Folium
2. Advanced bivariate choropleth using matplotlib and geopandas
3. Custom color schemes and legends
4. Integration with the reporting system

Based on the approach from: https://github.com/mikhailsirenko/bivariate-choropleth
"""

import pandas as pd
import geopandas as gpd
from pathlib import Path
import logging

# Import the ChartGenerator
from ..chart_generator import ChartGenerator

# Setup logging
logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

def create_sample_data():
    """
    Create sample data for bivariate choropleth examples.
    
    Returns:
        pandas.DataFrame: Sample data with location and two value columns
    """
    # Sample data - population density and median income by state
    sample_data = {
        'state': ['California', 'Texas', 'New York', 'Florida', 'Illinois', 
                  'Pennsylvania', 'Ohio', 'Georgia', 'Michigan', 'North Carolina'],
        'population_density': [251.3, 108.4, 421.0, 384.3, 231.1, 
                              285.3, 287.7, 175.1, 174.8, 200.6],
        'median_income': [75235, 64034, 72741, 59227, 69234, 
                          63240, 58642, 61820, 59234, 57216]
    }
    
    return pd.DataFrame(sample_data)

def create_sample_geodata():
    """
    Create sample geographic data for examples.
    In practice, you would load real GeoJSON files.
    
    Returns:
        geopandas.GeoDataFrame: Sample geographic data
    """
    # This is a simplified example - in practice you'd load real GeoJSON
    # For demonstration, we'll create a simple GeoDataFrame
    from shapely.geometry import Point
    
    # Create simple point geometries for demonstration
    sample_geodata = {
        'state': ['California', 'Texas', 'New York', 'Florida', 'Illinois'],
        'geometry': [
            Point(-119.4179, 36.7783),  # California
            Point(-99.9018, 31.9686),    # Texas
            Point(-74.2179, 43.2994),    # New York
            Point(-81.5158, 27.6648),    # Florida
            Point(-88.9861, 40.3495)     # Illinois
        ]
    }
    
    return gpd.GeoDataFrame(sample_geodata, crs="EPSG:4326")

def example_basic_bivariate_choropleth():
    """
    Example 1: Basic bivariate choropleth using Folium.
    
    This example shows how to create a simple bivariate choropleth map
    using the Folium-based method.
    """
    print("=== Example 1: Basic Bivariate Choropleth (Folium) ===")
    
    # Initialize chart generator
    chart_gen = ChartGenerator()
    
    # Create sample data
    data = create_sample_data()
    
    try:
        # Create bivariate choropleth
        chart = chart_gen.create_bivariate_choropleth(
            data=data,
            location_column='state',
            value_column1='population_density',
            value_column2='median_income',
            title="Population Density vs Median Income by State",
            width=10.0,
            height=8.0
        )
        
        print("✓ Basic bivariate choropleth created successfully")
        print(f"Chart type: {type(chart)}")
        print(f"Chart dimensions: {chart.drawWidth} x {chart.drawHeight}")
        
        return chart
        
    except Exception as e:
        print(f"✗ Error creating basic bivariate choropleth: {e}")
        return None

def example_advanced_bivariate_choropleth():
    """
    Example 2: Advanced bivariate choropleth using matplotlib and geopandas.
    
    This example demonstrates the more sophisticated approach using matplotlib
    for better control over styling and legends.
    """
    print("\n=== Example 2: Advanced Bivariate Choropleth (Matplotlib) ===")
    
    # Initialize chart generator
    chart_gen = ChartGenerator()
    
    # Create sample data
    data = create_sample_data()
    geodata = create_sample_geodata()
    
    try:
        # Create advanced bivariate choropleth
        chart = chart_gen.create_bivariate_choropleth_matplotlib(
            data=data,
            geodata=geodata,
            location_column='state',
            value_column1='population_density',
            value_column2='median_income',
            title="Advanced Bivariate Choropleth: Population Density vs Income",
            width=12.0,
            height=10.0,
            color_scheme='custom'
        )
        
        print("✓ Advanced bivariate choropleth created successfully")
        print(f"Chart type: {type(chart)}")
        print(f"Chart dimensions: {chart.drawWidth} x {chart.drawHeight}")
        
        return chart
        
    except Exception as e:
        print(f"✗ Error creating advanced bivariate choropleth: {e}")
        return None

def example_custom_chart_configuration():
    """
    Example 3: Using custom chart configuration for bivariate choropleth.
    
    This example shows how to use the custom chart configuration
    system with bivariate choropleth maps.
    """
    print("\n=== Example 3: Custom Chart Configuration ===")
    
    # Initialize chart generator
    chart_gen = ChartGenerator()
    
    # Create sample data
    data = create_sample_data()
    
    # Custom chart configuration
    chart_config = {
        'type': 'bivariate_choropleth',
        'title': 'Custom Bivariate Choropleth Configuration',
        'data': data,
        'location_column': 'state',
        'value_columns': ['population_density', 'median_income']
    }
    
    try:
        # Create chart using custom configuration
        chart = chart_gen.create_custom_chart(
            chart_config=chart_config,
            width=10.0,
            height=8.0
        )
        
        print("✓ Custom chart configuration bivariate choropleth created successfully")
        print(f"Chart type: {type(chart)}")
        print(f"Chart dimensions: {chart.drawWidth} x {chart.drawHeight}")
        
        return chart
        
    except Exception as e:
        print(f"✗ Error creating custom chart configuration: {e}")
        return None

def example_dataframe_integration():
    """
    Example 4: Integration with DataFrame-based chart generation.
    
    This example shows how to use the DataFrame integration methods
    with bivariate choropleth maps.
    """
    print("\n=== Example 4: DataFrame Integration ===")
    
    # Initialize chart generator
    chart_gen = ChartGenerator()
    
    # Create sample data
    data = create_sample_data()
    
    try:
        # Create bivariate choropleth using DataFrame method
        chart = chart_gen.generate_chart_from_dataframe(
            df=data,
            chart_type='bivariate_choropleth',
            x_column='state',
            y_columns=['population_density', 'median_income'],
            title="DataFrame Integration Example",
            width=10.0,
            height=8.0
        )
        
        print("✓ DataFrame integration bivariate choropleth created successfully")
        print(f"Chart type: {type(chart)}")
        print(f"Chart dimensions: {chart.drawWidth} x {chart.drawHeight}")
        
        return chart
        
    except Exception as e:
        print(f"✗ Error creating DataFrame integration chart: {e}")
        return None

def example_advanced_choropleth():
    """
    Example 5: Advanced choropleth with classification options.
    
    This example demonstrates the advanced choropleth functionality
    with different classification methods.
    """
    print("\n=== Example 5: Advanced Choropleth with Classification ===")
    
    # Initialize chart generator
    chart_gen = ChartGenerator()
    
    # Create sample data
    data = create_sample_data()
    geodata = create_sample_geodata()
    
    try:
        # Create advanced choropleth with quantile classification
        chart = chart_gen.create_advanced_choropleth(
            data=data,
            geodata=geodata,
            location_column='state',
            value_column='population_density',
            title="Advanced Choropleth: Population Density (Quantile Classification)",
            width=12.0,
            height=10.0,
            classification='quantiles',
            bins=5,
            color_scheme='YlOrRd'
        )
        
        print("✓ Advanced choropleth with classification created successfully")
        print(f"Chart type: {type(chart)}")
        print(f"Chart dimensions: {chart.drawWidth} x {chart.drawHeight}")
        
        return chart
        
    except Exception as e:
        print(f"✗ Error creating advanced choropleth: {e}")
        return None

def run_all_examples():
    """
    Run all bivariate choropleth examples and return results.
    
    Returns:
        list: List of successfully created charts
    """
    print("🚀 Running Bivariate Choropleth Examples")
    print("=" * 50)
    
    charts = []
    
    # Run all examples
    examples = [
        example_basic_bivariate_choropleth,
        example_advanced_bivariate_choropleth,
        example_custom_chart_configuration,
        example_dataframe_integration,
        example_advanced_choropleth
    ]
    
    for example_func in examples:
        try:
            chart = example_func()
            if chart:
                charts.append(chart)
        except Exception as e:
            print(f"✗ Example {example_func.__name__} failed: {e}")
    
    print(f"\n📊 Summary: {len(charts)} out of {len(examples)} examples completed successfully")
    
    return charts

def create_report_with_bivariate_maps():
    """
    Example 6: Create a complete report section with bivariate choropleth maps.
    
    This example shows how to integrate bivariate choropleth maps
    into the complete reporting system.
    """
    print("\n=== Example 6: Report Integration ===")
    
    # Initialize chart generator
    chart_gen = ChartGenerator()
    
    # Create sample data
    data = create_sample_data()
    
    try:
        # Create multiple charts for the report
        charts = []
        
        # Chart 1: Basic bivariate choropleth
        chart1 = chart_gen.create_bivariate_choropleth(
            data=data,
            location_column='state',
            value_column1='population_density',
            value_column2='median_income',
            title="Population Density vs Median Income",
            width=8.0,
            height=6.0
        )
        charts.append(chart1)
        
        # Chart 2: Scatter plot for comparison
        chart2 = chart_gen.create_scatter_plot(
            data=data,
            x_column='population_density',
            y_column='median_income',
            title="Population Density vs Median Income (Scatter)",
            width=8.0,
            height=6.0
        )
        charts.append(chart2)
        
        # Create report section
        report_section = chart_gen.create_chart_section(
            title="Geographic Analysis: Population and Income Patterns",
            charts=charts,
            description="This section analyzes the relationship between population density and median income across different states using bivariate choropleth maps and supporting visualizations."
        )
        
        print("✓ Report section with bivariate maps created successfully")
        print(f"Number of charts in section: {len(charts)}")
        print(f"Report section length: {len(report_section)} elements")
        
        return report_section
        
    except Exception as e:
        print(f"✗ Error creating report section: {e}")
        return None

if __name__ == "__main__":
    """
    Main execution block for running examples.
    """
    print("🎯 Bivariate Choropleth Map Examples for siege_utilities")
    print("Based on: https://github.com/mikhailsirenko/bivariate-choropleth")
    print()
    
    # Run all examples
    charts = run_all_examples()
    
    # Create report integration example
    report_section = create_report_with_bivariate_maps()
    
    print("\n🎉 Examples completed!")
    print(f"Total charts created: {len(charts)}")
    print(f"Report section created: {'Yes' if report_section else 'No'}")
    
    # Print usage tips
    print("\n💡 Usage Tips:")
    print("1. Install required dependencies: pip install geopandas folium matplotlib")
    print("2. Use GeoJSON files for real geographic data")
    print("3. Experiment with different color schemes and classification methods")
    print("4. Combine with other chart types for comprehensive analysis")
    print("5. Integrate with the full reporting system for professional reports")

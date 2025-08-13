#!/usr/bin/env python3
"""
Comprehensive Mapping and Reporting Example

This example demonstrates the full range of mapping capabilities and comprehensive
reporting features in siege_utilities, including:

1. Multiple map types (choropleth, marker, 3D, heatmap, cluster, flow)
2. Comprehensive PDF reports with tables, charts, text, and appendices
3. PowerPoint presentations with various slide types
4. Integration of multiple data sources
5. Professional document structure with TOC and page organization

Requirements:
- siege_utilities with enhanced mapping capabilities
- Required dependencies installed
- Sample data files (or will create synthetic data)
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
import geopandas as gpd
from shapely.geometry import Point

# Import siege_utilities components
from siege_utilities.reporting.chart_generator import ChartGenerator
from siege_utilities.reporting.report_generator import ReportGenerator
from siege_utilities.reporting.powerpoint_generator import PowerPointGenerator
from siege_utilities.reporting.client_branding import ClientBrandingManager

def create_sample_geographic_data():
    """Create sample geographic data for demonstration."""
    
    # Sample US cities with coordinates and metrics
    cities_data = {
        'city': ['New York', 'Los Angeles', 'Chicago', 'Houston', 'Phoenix', 'Philadelphia', 
                'San Antonio', 'San Diego', 'Dallas', 'San Jose', 'Austin', 'Jacksonville',
                'Fort Worth', 'Columbus', 'Charlotte', 'San Francisco', 'Indianapolis', 
                'Seattle', 'Denver', 'Boston'],
        'latitude': [40.7128, 34.0522, 41.8781, 29.7604, 33.4484, 39.9526, 29.4241, 
                    32.7157, 32.7767, 37.3382, 30.2672, 30.3322, 32.7555, 39.9612, 
                    35.2271, 37.7749, 39.7684, 47.6062, 39.7392, 42.3601],
        'longitude': [-74.0060, -118.2437, -87.6298, -95.3698, -112.0740, -75.1652, 
                      -98.4936, -117.1611, -96.7970, -121.8863, -97.7431, -81.6557, 
                      -97.3308, -82.9988, -80.8431, -122.4194, -86.1581, -122.3321, 
                      -104.9903, -71.0589],
        'population': [8336817, 3979576, 2693976, 2320268, 1680992, 1603797, 1547253, 
                       1423851, 1343573, 1030119, 978908, 949611, 918915, 898553, 885708, 
                       873965, 876384, 744955, 727211, 694583],
        'median_income': [67212, 65000, 58000, 52000, 56000, 45000, 50000, 79000, 52000, 
                          117000, 75000, 52000, 58000, 52000, 62000, 112000, 47000, 93000, 
                          68000, 71000],
        'crime_rate': [2.8, 2.9, 3.2, 2.5, 2.1, 3.5, 2.3, 1.8, 2.7, 1.9, 2.1, 2.4, 
                       2.6, 2.8, 2.3, 1.7, 3.1, 1.9, 2.2, 2.0],
        'elevation': [33, 285, 594, 80, 1132, 39, 650, 430, 430, 82, 489, 16, 653, 902, 
                      751, 52, 715, 520, 5289, 141]
    }
    
    return pd.DataFrame(cities_data)

def create_sample_regional_data():
    """Create sample regional data for choropleth maps."""
    
    # Sample US regions with aggregated metrics
    regional_data = {
        'region': ['Northeast', 'Southeast', 'Midwest', 'Southwest', 'West Coast', 'Mountain West'],
        'population': [56116484, 85848333, 68028804, 40123456, 52345678, 23456789],
        'gdp_growth': [2.1, 3.2, 1.8, 4.1, 3.8, 2.9],
        'unemployment': [4.2, 3.8, 4.5, 3.2, 3.9, 3.1],
        'median_income': [72000, 58000, 62000, 54000, 85000, 65000],
        'education_level': [85.2, 78.9, 82.1, 76.5, 88.7, 81.3]
    }
    
    return pd.DataFrame(regional_data)

def create_sample_flow_data():
    """Create sample flow data for flow maps."""
    
    # Sample migration/flow data between cities
    flow_data = {
        'origin_city': ['New York', 'Los Angeles', 'Chicago', 'Houston', 'Phoenix'],
        'origin_lat': [40.7128, 34.0522, 41.8781, 29.7604, 33.4484],
        'origin_lon': [-74.0060, -118.2437, -87.6298, -95.3698, -112.0740],
        'dest_city': ['Los Angeles', 'New York', 'Houston', 'Phoenix', 'San Diego'],
        'dest_lat': [34.0522, 40.7128, 29.7604, 33.4484, 32.7157],
        'dest_lon': [-118.2437, -74.0060, -95.3698, -112.0740, -117.1611],
        'flow_volume': [15000, 12000, 8000, 6000, 4000]
    }
    
    return pd.DataFrame(flow_data)

def demonstrate_comprehensive_mapping():
    """Demonstrate all mapping capabilities."""
    
    print("🚀 Creating comprehensive mapping demonstration...")
    
    # Initialize chart generator
    chart_gen = ChartGenerator()
    
    # Create sample data
    cities_df = create_sample_geographic_data()
    regional_df = create_sample_regional_data()
    flow_df = create_sample_flow_data()
    
    print("📊 Generated sample data:")
    print(f"   - Cities: {len(cities_df)} locations")
    print(f"   - Regions: {len(regional_df)} regions")
    print(f"   - Flows: {len(flow_df)} connections")
    
    # 1. Bivariate Choropleth Map
    print("\n🗺️  Creating bivariate choropleth map...")
    bivariate_map = chart_gen.create_bivariate_choropleth_matplotlib(
        data=regional_df,
        geodata=None,  # Will use simple location-based approach
        location_column='region',
        value_column1='population',
        value_column2='median_income',
        title="Population vs Median Income by Region",
        width=12.0,
        height=10.0
    )
    
    # 2. Marker Map
    print("📍 Creating marker map...")
    marker_map = chart_gen.create_marker_map(
        data=cities_df,
        latitude_column='latitude',
        longitude_column='longitude',
        value_column='population',
        label_column='city',
        title="US Cities Population Map",
        width=12.0,
        height=10.0
    )
    
    # 3. 3D Map
    print("🏔️  Creating 3D elevation map...")
    elevation_map = chart_gen.create_3d_map(
        data=cities_df,
        latitude_column='latitude',
        longitude_column='longitude',
        elevation_column='elevation',
        title="City Elevation 3D Visualization",
        width=12.0,
        height=10.0
    )
    
    # 4. Heatmap
    print("🔥 Creating population heatmap...")
    heatmap = chart_gen.create_heatmap_map(
        data=cities_df,
        latitude_column='latitude',
        longitude_column='longitude',
        value_column='population',
        title="Population Density Heatmap",
        width=12.0,
        height=10.0
    )
    
    # 5. Cluster Map
    print("🔗 Creating cluster map...")
    cluster_map = chart_gen.create_cluster_map(
        data=cities_df,
        latitude_column='latitude',
        longitude_column='longitude',
        cluster_column='region',
        label_column='city',
        title="City Clusters by Region",
        width=12.0,
        height=10.0
    )
    
    # 6. Flow Map
    print("🌊 Creating flow map...")
    flow_map = chart_gen.create_flow_map(
        data=flow_df,
        origin_lat_column='origin_lat',
        origin_lon_column='origin_lon',
        dest_lat_column='dest_lat',
        dest_lon_column='dest_lon',
        flow_value_column='flow_volume',
        title="Migration Flows Between Cities",
        width=14.0,
        height=10.0
    )
    
    # 7. Advanced Choropleth
    print("🎨 Creating advanced choropleth...")
    advanced_choropleth = chart_gen.create_advanced_choropleth(
        data=regional_df,
        geodata=None,
        location_column='region',
        value_column='gdp_growth',
        title="GDP Growth by Region (Natural Breaks)",
        width=12.0,
        height=10.0,
        classification='natural_breaks',
        bins=5,
        color_scheme='RdYlGn'
    )
    
    print("\n✅ All map types created successfully!")
    
    return {
        'bivariate_map': bivariate_map,
        'marker_map': marker_map,
        'elevation_map': elevation_map,
        'heatmap': heatmap,
        'cluster_map': cluster_map,
        'flow_map': flow_map,
        'advanced_choropleth': advanced_choropleth
    }

def create_comprehensive_pdf_report(maps_dict):
    """Create a comprehensive PDF report with all map types."""
    
    print("\n📄 Creating comprehensive PDF report...")
    
    # Initialize report generator
    report_gen = ReportGenerator()
    
    # Create comprehensive report structure
    report_content = report_gen.create_comprehensive_report(
        title="Comprehensive Geographic Analysis Report",
        author="Siege Analytics Team",
        client="Geographic Research Institute",
        report_type="geographic_analysis",
        sections=[],
        appendices=[],
        table_of_contents=True,
        page_numbers=True,
        header_footer=True
    )
    
    # Add executive summary
    report_content = report_gen.add_text_section(
        report_content,
        "Executive Summary",
        """This comprehensive geographic analysis examines multiple aspects of spatial data across the United States, 
        including population distribution, economic indicators, migration patterns, and environmental factors. 
        The analysis reveals significant regional variations and provides actionable insights for strategic planning.""",
        level=1,
        page_break_after=True
    )
    
    # Add methodology section
    report_content = report_gen.add_text_section(
        report_content,
        "Methodology",
        """Data was collected from multiple sources including census data, economic indicators, and geographic databases. 
        Analysis was performed using advanced spatial analysis techniques including bivariate choropleth mapping, 
        3D visualization, and flow analysis. All maps were generated using the enhanced siege_utilities mapping system.""",
        level=1
    )
    
    # Add bivariate choropleth section
    report_content = report_gen.add_map_section(
        report_content,
        "Regional Population and Income Analysis",
        [maps_dict['bivariate_map']],
        map_type="bivariate_choropleth",
        description="This bivariate choropleth map shows the relationship between population size and median income across US regions.",
        level=1,
        page_break_after=True
    )
    
    # Add marker map section
    report_content = report_gen.add_map_section(
        report_content,
        "City Population Distribution",
        [maps_dict['marker_map']],
        map_type="marker",
        description="Marker map showing population distribution across major US cities with interactive popups.",
        level=1
    )
    
    # Add 3D elevation section
    report_content = report_gen.add_map_section(
        report_content,
        "3D Elevation Analysis",
        [maps_dict['elevation_map']],
        map_type="3d",
        description="Three-dimensional visualization of city elevations across the United States.",
        level=1,
        page_break_after=True
    )
    
    # Add heatmap section
    report_content = report_gen.add_map_section(
        report_content,
        "Population Density Heatmap",
        [maps_dict['heatmap']],
        map_type="heatmap",
        description="Heatmap visualization of population density across major metropolitan areas.",
        level=1
    )
    
    # Add cluster analysis section
    report_content = report_gen.add_map_section(
        report_content,
        "Regional City Clusters",
        [maps_dict['cluster_map']],
        map_type="cluster",
        description="Cluster analysis showing geographic grouping of cities by region.",
        level=1,
        page_break_after=True
    )
    
    # Add flow analysis section
    report_content = report_gen.add_map_section(
        report_content,
        "Migration Flow Patterns",
        [maps_dict['flow_map']],
        map_type="flow",
        description="Flow map showing migration patterns and connections between major cities.",
        level=1
    )
    
    # Add insights section
    report_content = report_gen.add_text_section(
        report_content,
        "Key Insights",
        """• Population density shows strong correlation with economic indicators
        • Regional clustering reveals distinct geographic patterns
        • Migration flows indicate economic opportunity patterns
        • Elevation variations impact urban development
        • Income disparities exist across geographic regions""",
        level=1,
        page_break_after=True
    )
    
    # Add recommendations section
    report_content = report_gen.add_text_section(
        report_content,
        "Strategic Recommendations",
        """• Focus economic development in high-potential regions
        • Develop infrastructure in emerging population centers
        • Address income inequality through targeted programs
        • Plan for climate adaptation in low-elevation areas
        • Strengthen regional economic partnerships""",
        level=1
    )
    
    # Add data appendix
    cities_df = create_sample_geographic_data()
    report_content = report_gen.add_appendix(
        report_content,
        "Raw Data Tables",
        cities_df,
        appendix_type="data"
    )
    
    # Generate PDF report
    output_path = "comprehensive_geographic_report.pdf"
    success = report_gen.generate_pdf_report(report_content, output_path)
    
    if success:
        print(f"✅ PDF report generated successfully: {output_path}")
    else:
        print("❌ Error generating PDF report")
    
    return success

def create_comprehensive_powerpoint(maps_dict):
    """Create a comprehensive PowerPoint presentation."""
    
    print("\n📊 Creating comprehensive PowerPoint presentation...")
    
    # Initialize PowerPoint generator
    ppt_gen = PowerPointGenerator()
    
    # Create comprehensive presentation structure
    presentation_content = ppt_gen.create_comprehensive_presentation(
        title="Geographic Analysis Presentation",
        author="Siege Analytics Team",
        client="Geographic Research Institute",
        presentation_type="geographic_analysis",
        sections=[],
        include_toc=True,
        include_agenda=True
    )
    
    # Add overview slide
    presentation_content = ppt_gen.add_text_slide(
        presentation_content,
        "Analysis Overview",
        """• Comprehensive geographic analysis of US regions
        • Multiple visualization types and mapping techniques
        • Population, economic, and environmental factors
        • Strategic insights and recommendations
        • Interactive and static map outputs""",
        level=1
    )
    
    # Add bivariate choropleth slide
    presentation_content = ppt_gen.add_map_slide(
        presentation_content,
        "Regional Population vs Income",
        [maps_dict['bivariate_map']],
        map_type="bivariate_choropleth",
        description="Bivariate analysis showing population and income relationships",
        level=1
    )
    
    # Add marker map slide
    presentation_content = ppt_gen.add_map_slide(
        presentation_content,
        "City Population Distribution",
        [maps_dict['marker_map']],
        map_type="marker",
        description="Interactive marker map with population data",
        level=1
    )
    
    # Add 3D elevation slide
    presentation_content = ppt_gen.add_map_slide(
        presentation_content,
        "3D Elevation Visualization",
        [maps_dict['elevation_map']],
        map_type="3d",
        description="Three-dimensional elevation analysis",
        level=1
    )
    
    # Add comparison slide
    presentation_content = ppt_gen.add_comparison_slide(
        presentation_content,
        "Map Type Comparison",
        {
            'left_title': 'Static Maps',
            'left_content': ['Choropleth', '3D Visualization', 'Advanced Classification'],
            'right_title': 'Interactive Maps',
            'right_content': ['Marker Maps', 'Heatmaps', 'Flow Maps', 'Cluster Maps']
        },
        level=1
    )
    
    # Add insights slide
    presentation_content = ppt_gen.add_text_slide(
        presentation_content,
        "Key Findings",
        """• Strong regional clustering patterns
        • Population-economic correlations
        • Migration flow insights
        • Environmental factor impacts
        • Strategic opportunity identification""",
        level=1
    )
    
    # Add summary slide
    presentation_content = ppt_gen.add_summary_slide(
        presentation_content,
        "Summary & Next Steps",
        [
            "Comprehensive geographic analysis completed",
            "Multiple visualization types demonstrated",
            "Strategic insights identified",
            "Recommendations developed",
            "Ready for implementation planning"
        ],
        level=1
    )
    
    # Generate PowerPoint
    output_path = "comprehensive_geographic_presentation.pptx"
    success = ppt_gen.generate_powerpoint_presentation(presentation_content, output_path)
    
    if success:
        print(f"✅ PowerPoint presentation generated successfully: {output_path}")
    else:
        print("❌ Error generating PowerPoint presentation")
    
    return success

def main():
    """Main demonstration function."""
    
    print("=" * 80)
    print("🗺️  COMPREHENSIVE MAPPING & REPORTING DEMONSTRATION")
    print("=" * 80)
    print("This example demonstrates the full range of mapping and reporting capabilities")
    print("in siege_utilities, including multiple map types and comprehensive document generation.")
    print()
    
    try:
        # Step 1: Create all map types
        maps_dict = demonstrate_comprehensive_mapping()
        
        # Step 2: Generate comprehensive PDF report
        pdf_success = create_comprehensive_pdf_report(maps_dict)
        
        # Step 3: Generate comprehensive PowerPoint presentation
        ppt_success = create_comprehensive_powerpoint(maps_dict)
        
        # Summary
        print("\n" + "=" * 80)
        print("📋 DEMONSTRATION SUMMARY")
        print("=" * 80)
        print(f"✅ Maps Created: {len(maps_dict)} different map types")
        print(f"✅ PDF Report: {'Generated' if pdf_success else 'Failed'}")
        print(f"✅ PowerPoint: {'Generated' if ppt_success else 'Failed'}")
        print()
        print("🎯 Key Capabilities Demonstrated:")
        print("   • Multiple map types (choropleth, marker, 3D, heatmap, cluster, flow)")
        print("   • Comprehensive PDF reports with TOC, sections, and appendices")
        print("   • PowerPoint presentations with various slide types")
        print("   • Professional document structure and organization")
        print("   • Integration of multiple data sources and visualization types")
        print()
        print("💡 Next Steps:")
        print("   1. Review generated documents")
        print("   2. Customize for your specific use case")
        print("   3. Integrate with your data sources")
        print("   4. Apply client branding and customization")
        print("   5. Deploy in production reporting workflows")
        
    except Exception as e:
        print(f"\n❌ Error during demonstration: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Enhanced Features Demo for Siege Utilities

This script demonstrates the new enhanced features:
1. User Configuration Management
2. Extensible Page Templates
3. Extensible Chart Types
4. Spatial Data Sources (Census, Government, OSM)
5. Spatial Data Transformation and Database Integration
6. Default Download Directory Management
"""

import logging
import sys
from pathlib import Path
import pandas as pd
import geopandas as gpd

# Add the parent directory to the path to import siege_utilities
sys.path.append(str(Path(__file__).parent.parent.parent))

from siege_utilities import (
    # User configuration
    get_user_config, get_download_directory,
    
    # Spatial data sources
    get_census_data, get_census_boundaries, download_osm_data,
    
    # Spatial transformations
    convert_spatial_format, transform_spatial_crs,
    simplify_spatial_geometries, buffer_spatial_geometries,
    
    # Page templates and chart types
    get_template_manager, get_chart_registry
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def demo_user_configuration():
    """Demonstrate user configuration management."""
    print("\n" + "="*60)
    print("🚀 USER CONFIGURATION DEMO")
    print("="*60)
    
    # Get user configuration
    user_config = get_user_config()
    
    # Display current profile
    profile = user_config.get_user_profile()
    print(f"Current user: {profile.full_name} ({profile.username})")
    print(f"Email: {profile.email}")
    print(f"GitHub: {profile.github_login}")
    print(f"Organization: {profile.organization}")
    print(f"Default download directory: {profile.preferred_download_directory}")
    print(f"Default output format: {profile.default_output_format}")
    
    # Update some preferences
    user_config.update_user_profile(
        default_output_format='pdf',
        preferred_map_style='satellite',
        default_color_scheme='viridis'
    )
    
    print("\n✅ Updated user preferences!")
    
    # Get download directory (uses user's default)
    download_dir = get_download_directory()
    print(f"Using download directory: {download_dir}")
    
    # Get download directory with specific path
    specific_dir = get_download_directory("/tmp/siege_demo")
    print(f"Using specific directory: {specific_dir}")

def demo_page_templates():
    """Demonstrate extensible page templates."""
    print("\n" + "="*60)
    print("📄 PAGE TEMPLATES DEMO")
    print("="*60)
    
    # Get template manager
    template_manager = get_template_manager()
    
    # List available templates
    pdf_templates = template_manager.list_templates('pdf')
    ppt_templates = template_manager.list_templates('powerpoint')
    
    print(f"Available PDF templates: {pdf_templates}")
    print(f"Available PowerPoint templates: {ppt_templates}")
    
    # Get template details
    title_template = template_manager.get_template('pdf_title')
    if title_template:
        print(f"\nTitle template properties:")
        print(f"  - Page dimensions: {title_template.page_width}\" x {title_template.page_height}\"")
        print(f"  - Margins: {title_template.margins}")
        print(f"  - Custom elements: {title_template.custom_elements}")
    
    # Create custom template
    custom_template = template_manager.get_template('pdf_title')
    if custom_template:
        template_manager.modify_template('pdf_title', 
                                      page_width=11.0,
                                      page_height=8.5,
                                      custom_elements={'logo_position': 'top_left'})
        print("\n✅ Modified title template!")

def demo_chart_types():
    """Demonstrate extensible chart types."""
    print("\n" + "="*60)
    print("📊 CHART TYPES DEMO")
    print("="*60)
    
    # Get chart registry
    chart_registry = get_chart_registry()
    
    # List available chart types
    geographic_charts = chart_registry.list_chart_types('geographic')
    statistical_charts = chart_registry.list_chart_types('statistical')
    
    print(f"Available geographic charts: {geographic_charts}")
    print(f"Available statistical charts: {statistical_charts}")
    
    # Get chart help
    bivariate_help = chart_registry.get_chart_help('bivariate_choropleth')
    if bivariate_help:
        print(f"\nBivariate choropleth chart:")
        print(f"  - Description: {bivariate_help['description']}")
        print(f"  - Required parameters: {bivariate_help['required_parameters']}")
        print(f"  - Optional parameters: {bivariate_help['optional_parameters']}")
        print(f"  - Supports interactive: {bivariate_help['supports_interactive']}")
        print(f"  - Supports 3D: {bivariate_help['supports_3d']}")

def demo_spatial_data_sources():
    """Demonstrate spatial data sources."""
    print("\n" + "="*60)
    print("🗺️ SPATIAL DATA SOURCES DEMO")
    print("="*60)
    
    # Get download directory
    download_dir = get_download_directory()
    
    try:
        # Download Census county boundaries
        print("Downloading Census county boundaries...")
        counties = get_census_boundaries(
            year=2020,
            geographic_level='county'
        )
        
        if counties is not None:
            print(f"✅ Downloaded {len(counties)} counties")
            print(f"Columns: {list(counties.columns)}")
            print(f"CRS: {counties.crs}")
            
            # Save to user's download directory
            output_path = download_dir / "census_counties_2020.gpkg"
            counties.to_file(output_path, driver='GPKG')
            print(f"✅ Saved to: {output_path}")
        else:
            print("❌ Failed to download Census data")
    
    except Exception as e:
        print(f"❌ Census data download failed: {e}")
    
    try:
        # Download Census demographic data
        print("\nDownloading Census demographic data...")
        demo_data = get_census_data(
            year=2020,
            dataset='acs/acs5',
            variables=['B01003_001E', 'B19013_001E'],  # Population and income
            geographic_level='county'
        )
        
        if demo_data is not None:
            print(f"✅ Downloaded {len(demo_data)} records")
            print(f"Columns: {list(demo_data.columns)}")
            
            # Save to user's download directory
            output_path = download_dir / "census_demographics_2020.csv"
            demo_data.to_csv(output_path, index=False)
            print(f"✅ Saved to: {output_path}")
        else:
            print("❌ Failed to download Census demographics")
    
    except Exception as e:
        print(f"❌ Census demographics download failed: {e}")

def demo_spatial_transformations():
    """Demonstrate spatial data transformations."""
    print("\n" + "="*60)
    print("🔄 SPATIAL TRANSFORMATIONS DEMO")
    print("="*60)
    
    # Get download directory
    download_dir = get_download_directory()
    
    try:
        # Load sample data (if available)
        counties_path = download_dir / "census_counties_2020.gpkg"
        if counties_path.exists():
            counties = gpd.read_file(counties_path)
            print(f"✅ Loaded {len(counties)} counties for transformation")
            
            # Transform CRS
            print("Transforming CRS to Web Mercator...")
            counties_web_mercator = transform_spatial_crs(counties, 'EPSG:3857')
            print(f"✅ Transformed CRS to: {counties_web_mercator.crs}")
            
            # Simplify geometries
            print("Simplifying geometries...")
            counties_simplified = simplify_spatial_geometries(counties, tolerance=1000)
            print(f"✅ Simplified geometries with tolerance 1000m")
            
            # Create buffers
            print("Creating buffers...")
            counties_buffered = buffer_spatial_geometries(counties, distance=5000)
            print(f"✅ Created 5km buffers around counties")
            
            # Convert formats
            print("Converting to different formats...")
            
            # To GeoJSON
            geojson_path = download_dir / "counties_simplified.geojson"
            convert_spatial_format(counties_simplified, 'geojson', str(geojson_path))
            print(f"✅ Converted to GeoJSON: {geojson_path}")
            
            # To Shapefile
            shp_path = download_dir / "counties_buffered.shp"
            convert_spatial_format(counties_buffered, 'shp', str(shp_path))
            print(f"✅ Converted to Shapefile: {shp_path}")
            
        else:
            print("⚠️ No Census data available for transformation demo")
    
    except Exception as e:
        print(f"❌ Spatial transformation failed: {e}")

def demo_database_integration():
    """Demonstrate database integration."""
    print("\n" + "="*60)
    print("🗄️ DATABASE INTEGRATION DEMO")
    print("="*60)
    
    # Get download directory
    download_dir = get_download_directory()
    
    try:
        # Load sample data
        counties_path = download_dir / "census_counties_2020.gpkg"
        if counties_path.exists():
            counties = gpd.read_file(counties_path)
            print(f"✅ Loaded {len(counties)} counties for database demo")
            
            # Convert to DuckDB (in-memory)
            print("Converting to DuckDB format...")
            success = convert_spatial_format(
                counties,
                'duckdb',
                table_name='counties_demo',
                db_path=':memory:'
            )
            
            if success:
                print("✅ Successfully converted to DuckDB format")
            else:
                print("❌ Failed to convert to DuckDB")
            
            # Convert to WKT format
            print("Converting to WKT format...")
            counties_wkt = convert_spatial_format(counties, 'wkt')
            
            if counties_wkt is not None:
                print(f"✅ Converted to WKT format with {len(counties_wkt)} rows")
                
                # Save WKT data
                wkt_path = download_dir / "counties_wkt.csv"
                counties_wkt.to_csv(wkt_path, index=False)
                print(f"✅ Saved WKT data to: {wkt_path}")
            else:
                print("❌ Failed to convert to WKT")
                
        else:
            print("⚠️ No Census data available for database demo")
    
    except Exception as e:
        print(f"❌ Database integration failed: {e}")

def main():
    """Run all demos."""
    print("🌟 SIEGE UTILITIES - ENHANCED FEATURES DEMO")
    print("="*60)
    
    try:
        # Run all demos
        demo_user_configuration()
        demo_page_templates()
        demo_chart_types()
        demo_spatial_data_sources()
        demo_spatial_transformations()
        demo_database_integration()
        
        print("\n" + "="*60)
        print("🎉 ALL DEMOS COMPLETED SUCCESSFULLY!")
        print("="*60)
        
        # Show final download directory contents
        download_dir = get_download_directory()
        print(f"\n📁 Files created in download directory: {download_dir}")
        
        if download_dir.exists():
            files = list(download_dir.glob("*"))
            for file in files:
                if file.is_file():
                    size_mb = file.stat().st_size / (1024 * 1024)
                    print(f"  - {file.name} ({size_mb:.2f} MB)")
        
    except Exception as e:
        print(f"\n❌ Demo failed with error: {e}")
        logger.exception("Demo execution failed")
        return 1
    
    return 0

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)

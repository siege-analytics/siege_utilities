#!/usr/bin/env python3
"""
Enhanced Features Demo for Siege Utilities

This script demonstrates key library features:
1. User Configuration Management
2. Page Templates and Chart Types
3. Spatial Data Sources (Census boundaries and demographics)
4. Spatial Data Transformation and Format Conversion
5. Default Download Directory Management

Prerequisites:
    pip install siege_utilities[geo,reporting]
"""

import logging
import sys
from pathlib import Path
from typing import Optional

import geopandas as gpd
import pandas as pd

from siege_utilities import get_user_config, get_download_directory
from siege_utilities.geo import (
    get_census_boundaries,
    get_census_data,
    download_osm_data,
    SpatialDataTransformer,
)
from siege_utilities.reporting.chart_types import get_chart_registry
from siege_utilities.reporting.templates.page_templates import get_template_manager

__all__ = [
    'demo_user_configuration',
    'demo_page_templates',
    'demo_chart_types',
    'demo_spatial_data_sources',
    'demo_spatial_transformations',
    'main',
]

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def demo_user_configuration():
    """Demonstrate user configuration management."""
    print("\n" + "=" * 60)
    print("USER CONFIGURATION DEMO")
    print("=" * 60)

    user_config = get_user_config()
    profile = user_config.get_user_profile()
    print(f"Current user: {profile.full_name} ({profile.username})")
    print(f"Email: {profile.email}")
    print(f"Organization: {profile.organization}")
    print(f"Default download directory: {profile.preferred_download_directory}")
    print(f"Default output format: {profile.default_output_format}")

    download_dir = get_download_directory()
    print(f"Using download directory: {download_dir}")


def demo_page_templates():
    """Demonstrate extensible page templates."""
    print("\n" + "=" * 60)
    print("PAGE TEMPLATES DEMO")
    print("=" * 60)

    template_manager = get_template_manager()

    pdf_templates = template_manager.list_templates("pdf")
    ppt_templates = template_manager.list_templates("powerpoint")

    print(f"Available PDF templates: {pdf_templates}")
    print(f"Available PowerPoint templates: {ppt_templates}")

    title_template = template_manager.get_template("pdf_title")
    if title_template:
        print(f"\nTitle template properties:")
        print(f"  - Page dimensions: {title_template.page_width}\" x {title_template.page_height}\"")
        print(f"  - Margins: {title_template.margins}")
        print(f"  - Custom elements: {title_template.custom_elements}")


def demo_chart_types():
    """Demonstrate extensible chart types."""
    print("\n" + "=" * 60)
    print("CHART TYPES DEMO")
    print("=" * 60)

    chart_registry = get_chart_registry()

    geographic_charts = chart_registry.list_chart_types("geographic")
    statistical_charts = chart_registry.list_chart_types("statistical")

    print(f"Available geographic charts: {geographic_charts}")
    print(f"Available statistical charts: {statistical_charts}")

    bivariate_help = chart_registry.get_chart_help("bivariate_choropleth")
    if bivariate_help:
        print(f"\nBivariate choropleth chart:")
        print(f"  - Description: {bivariate_help['description']}")
        print(f"  - Required parameters: {bivariate_help['required_parameters']}")
        print(f"  - Supports interactive: {bivariate_help['supports_interactive']}")


def demo_spatial_data_sources():
    """Demonstrate spatial data sources (Census boundaries and demographics)."""
    print("\n" + "=" * 60)
    print("SPATIAL DATA SOURCES DEMO")
    print("=" * 60)

    download_dir = get_download_directory()

    try:
        print("Downloading Census county boundaries...")
        counties: Optional[gpd.GeoDataFrame] = get_census_boundaries(
            year=2020, geographic_level="county"
        )

        if counties is not None:
            print(f"Downloaded {len(counties)} counties")
            print(f"Columns: {list(counties.columns)}")
            print(f"CRS: {counties.crs}")

            output_path = download_dir / "census_counties_2020.gpkg"
            counties.to_file(output_path, driver="GPKG")
            print(f"Saved to: {output_path}")
        else:
            logger.warning(
                "Census boundary download returned None; "
                "check network connectivity and Census API availability"
            )

    except Exception as exc:
        logger.error("Census boundary download failed: %s", exc)


def demo_spatial_transformations():
    """Demonstrate spatial data transformations using GeoPandas and SpatialDataTransformer."""
    print("\n" + "=" * 60)
    print("SPATIAL TRANSFORMATIONS DEMO")
    print("=" * 60)

    download_dir = get_download_directory()
    counties_path = download_dir / "census_counties_2020.gpkg"

    if not counties_path.exists():
        logger.info(
            "Skipping transformation demo: run spatial_data_sources demo first "
            "to download Census county data"
        )
        return

    try:
        counties = gpd.read_file(counties_path)
        print(f"Loaded {len(counties)} counties for transformation")

        # CRS reprojection via GeoPandas
        print("Reprojecting to Web Mercator (EPSG:3857)...")
        counties_mercator = counties.to_crs(epsg=3857)
        print(f"Reprojected CRS: {counties_mercator.crs}")

        # Geometry simplification via GeoPandas
        print("Simplifying geometries (tolerance=1000m in projected CRS)...")
        counties_mercator["geometry"] = counties_mercator.geometry.simplify(
            tolerance=1000
        )
        print(f"Simplified {len(counties_mercator)} geometries")

        # Format conversion via SpatialDataTransformer
        print("Converting simplified data to GeoJSON...")
        geojson_path = download_dir / "counties_simplified.geojson"
        transformer = SpatialDataTransformer()
        transformer.convert_format(
            counties_mercator.to_crs(epsg=4326), "geojson", output_path=str(geojson_path)
        )
        print(f"Saved GeoJSON: {geojson_path}")

    except Exception as exc:
        logger.error("Spatial transformation failed: %s", exc)


def main():
    """Run all demos."""
    print("SIEGE UTILITIES - ENHANCED FEATURES DEMO")
    print("=" * 60)

    try:
        demo_user_configuration()
        demo_page_templates()
        demo_chart_types()
        demo_spatial_data_sources()
        demo_spatial_transformations()

        print("\n" + "=" * 60)
        print("ALL DEMOS COMPLETED SUCCESSFULLY")
        print("=" * 60)

        download_dir = get_download_directory()
        if download_dir.exists():
            print(f"\nFiles created in: {download_dir}")
            for f in sorted(download_dir.glob("*")):
                if f.is_file():
                    size_mb = f.stat().st_size / (1024 * 1024)
                    print(f"  - {f.name} ({size_mb:.2f} MB)")

    except Exception as exc:
        logger.exception("Demo execution failed: %s", exc)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())

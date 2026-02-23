"""
Google Analytics Geographic Analysis with Census Data Integration

This module extends the GA reporting with geographic visualization:
1. Join GA city/region data with Census demographics
2. Create choropleth maps of website traffic by geography
3. Overlay demographic insights on traffic patterns
4. Generate geographic performance reports

Requirements:
- siege_utilities with geo and reporting extras
- Census API key (for demographic data)
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
import logging
import tempfile

# Geographic imports
try:
    import geopandas as gpd
    from shapely.geometry import Point
    GEOPANDAS_AVAILABLE = True
except ImportError:
    GEOPANDAS_AVAILABLE = False

# Plotting imports
try:
    import matplotlib.pyplot as plt
    import matplotlib.colors as mcolors
    from matplotlib.patches import Patch
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False

try:
    import folium
    from folium.plugins import HeatMap, MarkerCluster
    FOLIUM_AVAILABLE = True
except ImportError:
    FOLIUM_AVAILABLE = False

# siege_utilities imports
try:
    from siege_utilities.geo import get_geographic_boundaries, get_census_data_with_geometry
    from siege_utilities.geo.geocoding import use_nominatim_geocoder
    from siege_utilities.geo.census_api_client import CensusAPIClient
    GEO_AVAILABLE = True
except ImportError:
    GEO_AVAILABLE = False

log = logging.getLogger(__name__)


# US State FIPS codes for reference
STATE_FIPS = {
    'Alabama': '01', 'Alaska': '02', 'Arizona': '04', 'Arkansas': '05',
    'California': '06', 'Colorado': '08', 'Connecticut': '09', 'Delaware': '10',
    'Florida': '12', 'Georgia': '13', 'Hawaii': '15', 'Idaho': '16',
    'Illinois': '17', 'Indiana': '18', 'Iowa': '19', 'Kansas': '20',
    'Kentucky': '21', 'Louisiana': '22', 'Maine': '23', 'Maryland': '24',
    'Massachusetts': '25', 'Michigan': '26', 'Minnesota': '27', 'Mississippi': '28',
    'Missouri': '29', 'Montana': '30', 'Nebraska': '31', 'Nevada': '32',
    'New Hampshire': '33', 'New Jersey': '34', 'New Mexico': '35', 'New York': '36',
    'North Carolina': '37', 'North Dakota': '38', 'Ohio': '39', 'Oklahoma': '40',
    'Oregon': '41', 'Pennsylvania': '42', 'Rhode Island': '44', 'South Carolina': '45',
    'South Dakota': '46', 'Tennessee': '47', 'Texas': '48', 'Utah': '49',
    'Vermont': '50', 'Virginia': '51', 'Washington': '53', 'West Virginia': '54',
    'Wisconsin': '55', 'Wyoming': '56', 'District of Columbia': '11'
}

# Major US cities with coordinates
MAJOR_CITIES = {
    'New York': {'lat': 40.7128, 'lon': -74.0060, 'state': 'New York', 'state_fips': '36'},
    'Los Angeles': {'lat': 34.0522, 'lon': -118.2437, 'state': 'California', 'state_fips': '06'},
    'Chicago': {'lat': 41.8781, 'lon': -87.6298, 'state': 'Illinois', 'state_fips': '17'},
    'Houston': {'lat': 29.7604, 'lon': -95.3698, 'state': 'Texas', 'state_fips': '48'},
    'Phoenix': {'lat': 33.4484, 'lon': -112.0740, 'state': 'Arizona', 'state_fips': '04'},
    'Philadelphia': {'lat': 39.9526, 'lon': -75.1652, 'state': 'Pennsylvania', 'state_fips': '42'},
    'San Antonio': {'lat': 29.4241, 'lon': -98.4936, 'state': 'Texas', 'state_fips': '48'},
    'San Diego': {'lat': 32.7157, 'lon': -117.1611, 'state': 'California', 'state_fips': '06'},
    'Dallas': {'lat': 32.7767, 'lon': -96.7970, 'state': 'Texas', 'state_fips': '48'},
    'San Jose': {'lat': 37.3382, 'lon': -121.8863, 'state': 'California', 'state_fips': '06'},
    'Austin': {'lat': 30.2672, 'lon': -97.7431, 'state': 'Texas', 'state_fips': '48'},
    'Jacksonville': {'lat': 30.3322, 'lon': -81.6557, 'state': 'Florida', 'state_fips': '12'},
    'Fort Worth': {'lat': 32.7555, 'lon': -97.3308, 'state': 'Texas', 'state_fips': '48'},
    'Columbus': {'lat': 39.9612, 'lon': -82.9988, 'state': 'Ohio', 'state_fips': '39'},
    'Charlotte': {'lat': 35.2271, 'lon': -80.8431, 'state': 'North Carolina', 'state_fips': '37'},
    'San Francisco': {'lat': 37.7749, 'lon': -122.4194, 'state': 'California', 'state_fips': '06'},
    'Indianapolis': {'lat': 39.7684, 'lon': -86.1581, 'state': 'Indiana', 'state_fips': '18'},
    'Seattle': {'lat': 47.6062, 'lon': -122.3321, 'state': 'Washington', 'state_fips': '53'},
    'Denver': {'lat': 39.7392, 'lon': -104.9903, 'state': 'Colorado', 'state_fips': '08'},
    'Boston': {'lat': 42.3601, 'lon': -71.0589, 'state': 'Massachusetts', 'state_fips': '25'},
    'Miami': {'lat': 25.7617, 'lon': -80.1918, 'state': 'Florida', 'state_fips': '12'},
    'Atlanta': {'lat': 33.7490, 'lon': -84.3880, 'state': 'Georgia', 'state_fips': '13'},
    'Portland': {'lat': 45.5152, 'lon': -122.6784, 'state': 'Oregon', 'state_fips': '41'},
    'Minneapolis': {'lat': 44.9778, 'lon': -93.2650, 'state': 'Minnesota', 'state_fips': '27'},
}


def geocode_ga_cities(ga_city_data: List[Dict[str, Any]]) -> pd.DataFrame:
    """
    Add coordinates to GA city data.

    Uses built-in major cities lookup first, then falls back to geocoding.
    """
    results = []

    for city_data in ga_city_data:
        city_name = city_data.get('city', '')
        region = city_data.get('region', '')

        result = {**city_data}

        # Check built-in lookup first
        if city_name in MAJOR_CITIES:
            info = MAJOR_CITIES[city_name]
            result['latitude'] = info['lat']
            result['longitude'] = info['lon']
            result['state'] = info['state']
            result['state_fips'] = info['state_fips']
            result['geocode_source'] = 'built-in'
        else:
            # Would use geocoding API here
            result['latitude'] = None
            result['longitude'] = None
            result['state'] = region
            result['state_fips'] = STATE_FIPS.get(region, None)
            result['geocode_source'] = 'not_found'

        results.append(result)

    return pd.DataFrame(results)


def aggregate_by_state(ga_city_df: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregate city-level GA data to state level.
    """
    # Filter to rows with valid state FIPS
    valid = ga_city_df[ga_city_df['state_fips'].notna()].copy()

    if valid.empty:
        return pd.DataFrame()

    # Aggregate metrics
    state_data = valid.groupby(['state', 'state_fips']).agg({
        'sessions': 'sum',
        'users': 'sum',
        'pageviews': 'sum' if 'pageviews' in valid.columns else lambda x: 0,
        'bounce_rate': 'mean' if 'bounce_rate' in valid.columns else lambda x: 0,
        'avg_duration': 'mean' if 'avg_duration' in valid.columns else lambda x: 0,
    }).reset_index()

    return state_data


def create_state_choropleth(state_data: pd.DataFrame, value_column: str = 'sessions',
                            title: str = "Website Traffic by State",
                            output_path: Optional[str] = None) -> Optional[str]:
    """
    Create a choropleth map of US states colored by a metric.
    """
    if not GEOPANDAS_AVAILABLE or not MATPLOTLIB_AVAILABLE:
        log.warning("GeoPandas or matplotlib not available for choropleth")
        return None

    try:
        # Load US states shapefile (from Census TIGER/Line)
        if GEO_AVAILABLE:
            states_gdf = get_geographic_boundaries(
                boundary_type='state',
                year=2020,
                state=None  # All states
            )
        else:
            log.warning("siege_utilities geo module not available")
            return None

        if states_gdf is None or states_gdf.empty:
            log.warning("Could not load state boundaries")
            return None

        # Merge with GA data
        merged = states_gdf.merge(
            state_data,
            left_on='STATEFP',
            right_on='state_fips',
            how='left'
        )

        # Create figure
        fig, ax = plt.subplots(1, 1, figsize=(14, 8))

        # Plot states
        merged.plot(
            column=value_column,
            ax=ax,
            legend=True,
            cmap='Blues',
            missing_kwds={'color': 'lightgray', 'label': 'No data'},
            legend_kwds={'label': value_column.replace('_', ' ').title()}
        )

        # Styling
        ax.set_title(title, fontsize=16, fontweight='bold')
        ax.set_axis_off()

        # Crop to continental US
        ax.set_xlim(-130, -65)
        ax.set_ylim(24, 50)

        plt.tight_layout()

        # Save or return path
        if output_path:
            plt.savefig(output_path, dpi=150, bbox_inches='tight')
            plt.close()
            return output_path
        else:
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                plt.savefig(tmp.name, dpi=150, bbox_inches='tight')
                plt.close()
                return tmp.name

    except Exception as e:
        log.error(f"Error creating state choropleth: {e}")
        return None


def create_city_heatmap(ga_city_df: pd.DataFrame, value_column: str = 'sessions',
                        output_path: Optional[str] = None) -> Optional[str]:
    """
    Create an interactive heatmap of traffic intensity by city.
    """
    if not FOLIUM_AVAILABLE:
        log.warning("Folium not available for heatmap")
        return None

    try:
        # Filter to geocoded cities
        valid = ga_city_df[ga_city_df['latitude'].notna()].copy()

        if valid.empty:
            log.warning("No geocoded cities for heatmap")
            return None

        # Create base map centered on US
        center_lat = valid['latitude'].mean()
        center_lon = valid['longitude'].mean()
        m = folium.Map(location=[center_lat, center_lon], zoom_start=4)

        # Prepare heatmap data
        heat_data = []
        for _, row in valid.iterrows():
            weight = row[value_column] / valid[value_column].max()  # Normalize
            heat_data.append([row['latitude'], row['longitude'], weight])

        # Add heatmap layer
        HeatMap(heat_data, radius=25, blur=15).add_to(m)

        # Add markers for top cities
        top_cities = valid.nlargest(10, value_column)
        for _, row in top_cities.iterrows():
            folium.CircleMarker(
                location=[row['latitude'], row['longitude']],
                radius=8,
                popup=f"{row['city']}: {row[value_column]:,} {value_column}",
                color='red',
                fill=True,
                fill_opacity=0.7
            ).add_to(m)

        # Save map
        if output_path:
            m.save(output_path)
            return output_path
        else:
            with tempfile.NamedTemporaryFile(suffix='.html', delete=False) as tmp:
                m.save(tmp.name)
                return tmp.name

    except Exception as e:
        log.error(f"Error creating city heatmap: {e}")
        return None


def create_traffic_demographics_comparison(ga_state_data: pd.DataFrame,
                                            census_year: int = 2022) -> pd.DataFrame:
    """
    Join GA state-level data with Census demographics.

    Returns a DataFrame with both traffic metrics and demographic data.
    """
    if not GEO_AVAILABLE:
        log.warning("siege_utilities geo module not available for Census data")
        return ga_state_data

    try:
        # Fetch state-level demographics
        census_client = CensusAPIClient()

        demographics = census_client.fetch_data(
            year=census_year,
            dataset='acs5',
            geography='state',
            variables=['B01001_001E', 'B19013_001E', 'B15003_022E'],  # Pop, Income, Bachelor's
            state='*'
        )

        if demographics.empty:
            return ga_state_data

        # Rename columns
        demographics = demographics.rename(columns={
            'B01001_001E': 'total_population',
            'B19013_001E': 'median_income',
            'B15003_022E': 'bachelors_degree'
        })

        # Merge with GA data
        merged = ga_state_data.merge(
            demographics[['state', 'total_population', 'median_income', 'bachelors_degree']],
            on='state',
            how='left'
        )

        # Calculate derived metrics
        if 'total_population' in merged.columns and 'users' in merged.columns:
            merged['users_per_capita'] = merged['users'] / merged['total_population'] * 100000

        return merged

    except Exception as e:
        log.error(f"Error fetching Census demographics: {e}")
        return ga_state_data


def create_bivariate_traffic_income_map(merged_data: pd.DataFrame,
                                         output_path: Optional[str] = None) -> Optional[str]:
    """
    Create a bivariate choropleth showing traffic vs income.
    """
    if not GEOPANDAS_AVAILABLE or not MATPLOTLIB_AVAILABLE:
        return None

    try:
        if GEO_AVAILABLE:
            states_gdf = get_geographic_boundaries(
                boundary_type='state',
                year=2020,
                state=None
            )
        else:
            return None

        if states_gdf is None or states_gdf.empty:
            return None

        # Merge data
        gdf = states_gdf.merge(
            merged_data,
            left_on='STATEFP',
            right_on='state_fips',
            how='left'
        )

        # Create quantile bins for both variables
        gdf['traffic_bin'] = pd.qcut(gdf['sessions'].fillna(0), q=3, labels=['Low', 'Medium', 'High'])
        gdf['income_bin'] = pd.qcut(gdf['median_income'].fillna(0), q=3, labels=['Low', 'Medium', 'High'])

        # Create bivariate color matrix
        bivariate_colors = {
            ('Low', 'Low'): '#e8e8e8',
            ('Low', 'Medium'): '#b8d6be',
            ('Low', 'High'): '#73ae80',
            ('Medium', 'Low'): '#b5c0da',
            ('Medium', 'Medium'): '#90b2b3',
            ('Medium', 'High'): '#5a9178',
            ('High', 'Low'): '#6c83b5',
            ('High', 'Medium'): '#567994',
            ('High', 'High'): '#2a5a5b',
        }

        def get_color(row):
            if pd.isna(row['traffic_bin']) or pd.isna(row['income_bin']):
                return '#ffffff'
            return bivariate_colors.get((row['traffic_bin'], row['income_bin']), '#ffffff')

        gdf['color'] = gdf.apply(get_color, axis=1)

        # Create figure
        fig, ax = plt.subplots(1, 1, figsize=(14, 10))

        # Plot with custom colors
        gdf.plot(
            ax=ax,
            color=gdf['color'],
            edgecolor='white',
            linewidth=0.5
        )

        # Title and styling
        ax.set_title('Website Traffic vs. Median Income by State', fontsize=16, fontweight='bold')
        ax.set_axis_off()
        ax.set_xlim(-130, -65)
        ax.set_ylim(24, 50)

        # Add legend
        legend_elements = [
            Patch(facecolor='#73ae80', label='High Income, Low Traffic'),
            Patch(facecolor='#2a5a5b', label='High Income, High Traffic'),
            Patch(facecolor='#e8e8e8', label='Low Income, Low Traffic'),
            Patch(facecolor='#6c83b5', label='Low Income, High Traffic'),
        ]
        ax.legend(handles=legend_elements, loc='lower right', fontsize=9)

        plt.tight_layout()

        if output_path:
            plt.savefig(output_path, dpi=150, bbox_inches='tight')
            plt.close()
            return output_path
        else:
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                plt.savefig(tmp.name, dpi=150, bbox_inches='tight')
                plt.close()
                return tmp.name

    except Exception as e:
        log.error(f"Error creating bivariate map: {e}")
        return None


def generate_geographic_insights(merged_data: pd.DataFrame) -> List[str]:
    """
    Generate insights from the geographic + demographic analysis.
    """
    insights = []

    if merged_data.empty:
        return ["Insufficient geographic data for analysis."]

    # Top performing states
    if 'users' in merged_data.columns:
        top_states = merged_data.nlargest(3, 'users')
        state_list = ', '.join(top_states['state'].tolist())
        insights.append(f"Top traffic states: {state_list}")

    # Per-capita analysis
    if 'users_per_capita' in merged_data.columns:
        high_percap = merged_data.nlargest(3, 'users_per_capita')
        low_percap = merged_data.nsmallest(3, 'users_per_capita')

        insights.append(
            f"Highest per-capita engagement: {', '.join(high_percap['state'].tolist())} "
            f"(avg {high_percap['users_per_capita'].mean():.0f} users per 100k population)"
        )

        insights.append(
            f"Opportunity states (low per-capita): {', '.join(low_percap['state'].tolist())}"
        )

    # Income correlation
    if 'median_income' in merged_data.columns and 'users' in merged_data.columns:
        correlation = merged_data['median_income'].corr(merged_data['users'])
        if correlation > 0.5:
            insights.append(
                f"Strong positive correlation ({correlation:.2f}) between state income and traffic volume."
            )
        elif correlation < -0.3:
            insights.append(
                f"Negative correlation ({correlation:.2f}) suggests opportunity in lower-income states."
            )

    return insights


def main():
    """Demonstrate geographic GA analysis."""
    print("=" * 80)
    print("Google Analytics Geographic Analysis Demo")
    print("=" * 80)

    # Sample GA city-level data
    ga_cities = [
        {'city': 'Los Angeles', 'region': 'California', 'sessions': 15000, 'users': 12000},
        {'city': 'New York', 'region': 'New York', 'sessions': 18000, 'users': 14500},
        {'city': 'Chicago', 'region': 'Illinois', 'sessions': 8500, 'users': 7000},
        {'city': 'Houston', 'region': 'Texas', 'sessions': 6000, 'users': 5000},
        {'city': 'Phoenix', 'region': 'Arizona', 'sessions': 4500, 'users': 3800},
        {'city': 'San Francisco', 'region': 'California', 'sessions': 9000, 'users': 7500},
        {'city': 'Seattle', 'region': 'Washington', 'sessions': 7000, 'users': 5800},
        {'city': 'Denver', 'region': 'Colorado', 'sessions': 5500, 'users': 4500},
        {'city': 'Boston', 'region': 'Massachusetts', 'sessions': 6500, 'users': 5200},
        {'city': 'Atlanta', 'region': 'Georgia', 'sessions': 5000, 'users': 4200},
        {'city': 'Miami', 'region': 'Florida', 'sessions': 7500, 'users': 6000},
        {'city': 'Dallas', 'region': 'Texas', 'sessions': 5500, 'users': 4500},
        {'city': 'Portland', 'region': 'Oregon', 'sessions': 4000, 'users': 3300},
        {'city': 'Minneapolis', 'region': 'Minnesota', 'sessions': 3500, 'users': 2900},
    ]

    print("\n1. Geocoding GA city data...")
    ga_df = geocode_ga_cities(ga_cities)
    print(f"   Geocoded {len(ga_df[ga_df['latitude'].notna()])} of {len(ga_df)} cities")

    print("\n2. Aggregating to state level...")
    state_df = aggregate_by_state(ga_df)
    print(f"   {len(state_df)} states with data")

    print("\n3. Creating state choropleth map...")
    choropleth = create_state_choropleth(state_df, 'sessions', 'Website Sessions by State')
    if choropleth:
        print(f"   Saved: {choropleth}")

    print("\n4. Creating city heatmap...")
    heatmap = create_city_heatmap(ga_df, 'sessions')
    if heatmap:
        print(f"   Saved: {heatmap}")

    print("\n5. Adding Census demographics...")
    merged = create_traffic_demographics_comparison(state_df)
    if 'median_income' in merged.columns:
        print("   Census data merged successfully")

    print("\n6. Generating geographic insights...")
    insights = generate_geographic_insights(merged)
    for insight in insights:
        print(f"   - {insight}")

    print("\nDone!")
    return True


if __name__ == "__main__":
    main()

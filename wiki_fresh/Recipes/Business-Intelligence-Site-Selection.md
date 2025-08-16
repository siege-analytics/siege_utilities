# Business Intelligence and Site Selection System

This recipe demonstrates how to build a comprehensive business intelligence platform that combines Census demographics, business data, and advanced analytics to optimize site selection, market entry strategies, and competitive positioning.

## 🏢 **Overview**

Create a business intelligence system that:
- Analyzes market demographics and business environment
- Identifies optimal locations for new business ventures
- Evaluates competitive landscape and market saturation
- Provides predictive analytics for business performance
- Generates strategic business reports and recommendations

## 🚀 **Prerequisites**

```bash
pip install siege-utilities[geo,analytics,reporting,spatial]
pip install yelp-fusion googlemaps pandas-profiling
pip install plotly dash folium seaborn scikit-learn
pip install networkx community python-louvain
```

## 📊 **Sample Datasets We'll Use**

### **Primary Data Sources**
1. **Census TIGER/Line**: Geographic boundaries and demographics
2. **Yelp Fusion API**: Business listings, ratings, categories
3. **Google Maps API**: Places, distance calculations, traffic data
4. **OpenStreetMap**: Amenities, transportation networks
5. **Government Data**: Business licenses, economic indicators

### **External Data Integration**
- **Data.world**: Business datasets, market research
- **Snowflake**: Store large business intelligence datasets
- **Facebook Business**: Local business insights and audience data
- **Google Analytics**: Web traffic patterns and consumer behavior

## 🔄 **Complete Workflow**

### **Step 1: Market Analysis and Business Planning**

```python
from siege_utilities.geo.spatial_data import census_source
from siege_utilities.analytics import search_datadotworld_datasets
from siege_utilities.core.logging import setup_logging
import pandas as pd
import geopandas as gpd
import numpy as np
from datetime import datetime

# Setup logging
setup_logging(level='INFO')

# Define target markets and business types
target_markets = {
    'CA': {
        'name': 'California',
        'metros': ['Los Angeles', 'San Francisco', 'San Diego'],
        'fips': '06',
        'business_types': ['restaurant', 'retail', 'healthcare', 'professional_services']
    },
    'TX': {
        'name': 'Texas',
        'metros': ['Houston', 'Dallas', 'Austin'],
        'fips': '48',
        'business_types': ['restaurant', 'retail', 'energy', 'technology']
    },
    'NY': {
        'name': 'New York',
        'metros': ['New York City', 'Buffalo', 'Rochester'],
        'fips': '36',
        'business_types': ['restaurant', 'retail', 'finance', 'media']
    }
}

print("🎯 Target Markets and Business Types:")
for state, info in target_markets.items():
    print(f"  {info['name']}: {', '.join(info['metros'])}")
    print(f"    Business Types: {', '.join(info['business_types'])}")

# Discover available Census data
analysis_year = 2020
print(f"\n📊 Using Census Year: {analysis_year}")

# Get available boundary types for detailed analysis
boundary_types = census_source.get_available_boundary_types(analysis_year)
print(f"Available boundaries: {list(boundary_types.keys())}")

# Define business categories and their demographic requirements
business_demographics = {
    'restaurant': {
        'target_age_groups': ['25-34', '35-44', '45-54'],
        'min_income': 50000,
        'population_density': 'high',
        'competition_threshold': 0.8
    },
    'retail': {
        'target_age_groups': ['18-24', '25-34', '35-44'],
        'min_income': 40000,
        'population_density': 'medium',
        'competition_threshold': 0.7
    },
    'healthcare': {
        'target_age_groups': ['45-54', '55-64', '65+'],
        'min_income': 60000,
        'population_density': 'medium',
        'competition_threshold': 0.6
    },
    'professional_services': {
        'target_age_groups': ['25-34', '35-44', '45-54'],
        'min_income': 70000,
        'population_density': 'medium',
        'competition_threshold': 0.5
    }
}
```

### **Step 2: Download Geographic and Demographic Data**

```python
from siege_utilities.files import ensure_path_exists, get_download_directory
import time

# Create data directory structure
data_dir = get_download_directory() / "business_intelligence" / str(analysis_year)
ensure_path_exists(data_dir)

# Download boundaries and demographics for each target state
market_data = {}
for state_code, state_info in target_markets.items():
    state_fips = state_info['fips']
    state_name = state_info['name']
    
    print(f"\n🏢 Processing {state_name}...")
    
    # Download county boundaries
    counties = census_source.get_geographic_boundaries(
        year=analysis_year,
        geographic_level='county',
        state_fips=state_fips
    )
    
    if counties is not None:
        # Download tract boundaries for neighborhood-level analysis
        tracts = census_source.get_geographic_boundaries(
            year=analysis_year,
            geographic_level='tract',
            state_fips=state_fips
        )
        
        # Download block group boundaries for micro-neighborhood analysis
        block_groups = census_source.get_geographic_boundaries(
            year=analysis_year,
            geographic_level='block_group',
            state_fips=state_fips
        )
        
        # Get comprehensive state demographics
        state_demographics = census_source.get_comprehensive_state_info()
        
        # Get state-specific demographic data
        state_demo_data = census_source.get_state_demographics(
            year=analysis_year,
            state_fips=state_fips
        )
        
        market_data[state_code] = {
            'counties': counties,
            'tracts': tracts,
            'block_groups': block_groups,
            'demographics': state_demo_data,
            'state_info': state_demographics.get(state_fips, {}),
            'name': state_name,
            'fips': state_fips
        }
        
        print(f"✓ {state_name}: {len(counties)} counties, {len(tracts)} tracts, {len(block_groups)} block groups")
        
        # Save geographic data
        counties.to_file(data_dir / f"{state_code}_counties.geojson", driver='GeoJSON')
        tracts.to_file(data_dir / f"{state_code}_tracts.geojson", driver='GeoJSON')
        block_groups.to_file(data_dir / f"{state_code}_block_groups.geojson", driver='GeoJSON')
        
        if state_demo_data is not None:
            state_demo_data.to_csv(data_dir / f"{state_code}_demographics.csv", index=False)
    
    # Rate limiting
    time.sleep(1)
```

### **Step 3: Business Data Collection and Market Research**

```python
import requests
import json
from typing import Dict, List, Optional

class BusinessDataCollector:
    """Collect business and market data from multiple sources."""
    
    def __init__(self, api_keys=None):
        self.api_keys = api_keys or {}
        self.session = requests.Session()
    
    def get_yelp_businesses(self, location, business_type, limit=50):
        """Get Yelp business listings for a specific location and business type."""
        
        # Yelp Fusion API endpoint
        base_url = "https://api.yelp.com/v3/businesses/search"
        
        headers = {
            'Authorization': f'Bearer {self.api_keys.get("yelp", "DEMO_KEY")}',
            'Content-Type': 'application/json'
        }
        
        params = {
            'location': location,
            'term': business_type,
            'limit': limit,
            'sort_by': 'rating'
        }
        
        try:
            response = self.session.get(base_url, headers=headers, params=params)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error getting Yelp data for {location} {business_type}: {e}")
            return None
    
    def get_google_places(self, location, business_type, radius=5000):
        """Get Google Places data for a specific location and business type."""
        
        # Google Places API endpoint
        base_url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
        
        params = {
            'location': location,
            'radius': radius,
            'type': business_type,
            'key': self.api_keys.get("google", "DEMO_KEY")
        }
        
        try:
            response = self.session.get(base_url, params=params)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error getting Google Places data for {location} {business_type}: {e}")
            return None
    
    def get_business_licenses(self, location, business_type):
        """Get business license data from government sources."""
        
        # This would integrate with government APIs for business licenses
        # For now, return mock data structure
        mock_licenses = {
            'total_licenses': np.random.randint(50, 200),
            'active_licenses': np.random.randint(40, 180),
            'new_licenses_last_year': np.random.randint(5, 25),
            'license_types': [business_type, 'general_business', 'specialty']
        }
        
        return mock_licenses
    
    def get_economic_indicators(self, location):
        """Get economic indicators for a location."""
        
        # This would integrate with economic data APIs
        # For now, return mock data structure
        mock_economics = {
            'unemployment_rate': np.random.uniform(3.0, 8.0),
            'gdp_growth': np.random.uniform(1.0, 4.0),
            'consumer_confidence': np.random.uniform(60, 90),
            'retail_sales_growth': np.random.uniform(-2.0, 5.0)
        }
        
        return mock_economics

# Initialize business data collector
business_collector = BusinessDataCollector({
    'yelp': 'YOUR_YELP_API_KEY',
    'google': 'YOUR_GOOGLE_API_KEY'
})

# Collect business data for each market
business_data = {}
for state_code, state_info in market_data.items():
    state_name = state_info['name']
    print(f"\n🏪 Collecting business data for {state_name}...")
    
    state_business_data = {}
    
    for metro in state_info['metros']:
        print(f"  Processing {metro}...")
        
        metro_business_data = {}
        
        for business_type in state_info['business_types']:
            print(f"    Collecting {business_type} data...")
            
            # Get Yelp business data
            yelp_data = business_collector.get_yelp_businesses(metro, business_type)
            if yelp_data:
                metro_business_data[f"{business_type}_yelp"] = yelp_data
            
            # Get Google Places data
            google_data = business_collector.get_google_places(metro, business_type)
            if google_data:
                metro_business_data[f"{business_type}_google"] = google_data
            
            # Get business licenses
            license_data = business_collector.get_business_licenses(metro, business_type)
            if license_data:
                metro_business_data[f"{business_type}_licenses"] = license_data
            
            # Get economic indicators
            economic_data = business_collector.get_economic_indicators(metro)
            if economic_data:
                metro_business_data[f"{business_type}_economics"] = economic_data
        
        state_business_data[metro] = metro_business_data
        
        print(f"    ✓ {metro}: Collected data for {len(metro_business_data)} business types")
    
    business_data[state_code] = state_business_data
    
    # Save business data
    with open(data_dir / f"{state_code}_business_data.json", 'w') as f:
        json.dump(state_business_data, f, indent=2, default=str)
```

### **Step 4: Market Analysis and Competitive Intelligence**

```python
from sklearn.ensemble import RandomForestRegressor, IsolationForest
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
import networkx as nx
import community

class MarketAnalyzer:
    """Analyze business markets and competitive landscape."""
    
    def __init__(self):
        self.scaler = StandardScaler()
        self.clustering_model = KMeans(n_clusters=5, random_state=42)
        self.anomaly_detector = IsolationForest(contamination=0.1, random_state=42)
    
    def analyze_market_opportunities(self, business_data, demographics_data, business_type):
        """Analyze market opportunities for a specific business type."""
        
        # Combine business and demographic data
        combined_data = self._combine_business_demographics(business_data, demographics_data, business_type)
        
        # Calculate market indicators
        market_indicators = self._calculate_market_indicators(combined_data, business_type)
        
        # Analyze competitive landscape
        competitive_analysis = self._analyze_competition(combined_data, business_type)
        
        # Identify market gaps and opportunities
        market_opportunities = self._identify_market_gaps(market_indicators, competitive_analysis)
        
        # Generate market forecasts
        market_forecasts = self._generate_market_forecasts(market_indicators, business_type)
        
        return {
            'market_indicators': market_indicators,
            'competitive_analysis': competitive_analysis,
            'market_opportunities': market_opportunities,
            'market_forecasts': market_forecasts
        }
    
    def _combine_business_demographics(self, business_data, demographics_data, business_type):
        """Combine business data with demographic information."""
        
        combined_data = []
        
        for state_code, state_business in business_data.items():
            for metro, metro_business in state_business.items():
                if f"{business_type}_yelp" in metro_business:
                    # Extract Yelp business data
                    yelp_df = self._extract_yelp_data(metro_business[f"{business_type}_yelp"])
                    if yelp_df is not None:
                        # Add demographic context
                        demographic_context = self._get_demographic_context(
                            metro, demographics_data
                        )
                        if demographic_context is not None:
                            yelp_df = yelp_df.merge(
                                demographic_context,
                                left_index=True,
                                right_index=True,
                                how='left'
                            )
                        combined_data.append(yelp_df)
        
        if combined_data:
            return pd.concat(combined_data, ignore_index=True)
        return pd.DataFrame()
    
    def _extract_yelp_data(self, yelp_data):
        """Extract relevant data from Yelp API response."""
        
        try:
            if 'businesses' in yelp_data:
                businesses = yelp_data['businesses']
                
                extracted_data = []
                for business in businesses:
                    extracted_data.append({
                        'business_id': business.get('id'),
                        'name': business.get('name'),
                        'rating': business.get('rating'),
                        'review_count': business.get('review_count'),
                        'price': business.get('price'),
                        'categories': [cat['title'] for cat in business.get('categories', [])],
                        'latitude': business.get('coordinates', {}).get('latitude'),
                        'longitude': business.get('coordinates', {}).get('longitude'),
                        'address': business.get('location', {}).get('address1'),
                        'city': business.get('location', {}).get('city'),
                        'state': business.get('location', {}).get('state'),
                        'zip_code': business.get('location', {}).get('zip_code'),
                        'phone': business.get('phone'),
                        'distance': business.get('distance')
                    })
                
                return pd.DataFrame(extracted_data)
        
        except Exception as e:
            print(f"Error extracting Yelp data: {e}")
            return None
    
    def _get_demographic_context(self, metro, demographics_data):
        """Get demographic context for a metropolitan area."""
        
        # This would involve spatial joining between business locations and demographic boundaries
        # For now, return a simplified version
        return pd.DataFrame({
            'median_income': [demographics_data.get('median_income', 50000)],
            'population_density': [demographics_data.get('population_density', 1000)],
            'education_rate': [demographics_data.get('education_rate', 25)],
            'median_age': [demographics_data.get('median_age', 35)],
            'household_size': [demographics_data.get('household_size', 2.5)]
        })
    
    def _calculate_market_indicators(self, combined_data, business_type):
        """Calculate key market indicators for business analysis."""
        
        if combined_data.empty:
            return pd.DataFrame()
        
        # Calculate business density
        combined_data['business_density'] = len(combined_data) / 1000  # per 1000 people
        
        # Calculate average rating and review count
        combined_data['avg_rating'] = combined_data['rating'].mean()
        combined_data['avg_review_count'] = combined_data['review_count'].mean()
        
        # Calculate price distribution
        combined_data['price_level'] = combined_data['price'].apply(
            lambda x: len(x) if pd.notna(x) else 1
        )
        
        # Calculate market saturation
        business_demographics = business_demographics.get(business_type, {})
        target_population = combined_data['population_density'].iloc[0] if not combined_data.empty else 1000
        
        combined_data['market_saturation'] = (
            len(combined_data) / (target_population / 1000)
        )
        
        # Calculate demographic fit score
        combined_data['demographic_fit'] = self._calculate_demographic_fit(
            combined_data, business_type
        )
        
        return combined_data
    
    def _calculate_demographic_fit(self, data, business_type):
        """Calculate how well the demographics fit the business type."""
        
        requirements = business_demographics.get(business_type, {})
        
        if data.empty:
            return 0
        
        # Calculate fit based on income, age, and population density
        income_fit = min(data['median_income'].iloc[0] / requirements.get('min_income', 50000), 1.5)
        age_fit = 1.0  # Simplified for now
        density_fit = 1.0  # Simplified for now
        
        # Weighted average
        fit_score = (income_fit * 0.4 + age_fit * 0.3 + density_fit * 0.3)
        
        return min(fit_score, 1.0)
    
    def _analyze_competition(self, combined_data, business_type):
        """Analyze competitive landscape and market structure."""
        
        if combined_data.empty:
            return None
        
        # Create competitive network
        G = nx.Graph()
        
        # Add nodes (businesses)
        for idx, business in combined_data.iterrows():
            G.add_node(business['business_id'], 
                      name=business['name'],
                      rating=business['rating'],
                      price=business['price_level'])
        
        # Add edges based on proximity and similarity
        for i, business1 in combined_data.iterrows():
            for j, business2 in combined_data.iterrows():
                if i < j:
                    # Calculate similarity score
                    rating_diff = abs(business1['rating'] - business2['rating'])
                    price_diff = abs(business1['price_level'] - business2['price_level'])
                    
                    # Add edge if businesses are similar
                    if rating_diff < 1.0 and price_diff < 1:
                        G.add_edge(business1['business_id'], business2['business_id'],
                                  weight=1.0 / (rating_diff + price_diff + 0.1))
        
        # Community detection
        communities = community.best_partition(G)
        
        # Calculate competitive metrics
        competitive_metrics = {
            'total_businesses': len(combined_data),
            'communities': len(set(communities.values())),
            'avg_rating': combined_data['rating'].mean(),
            'avg_price_level': combined_data['price_level'].mean(),
            'market_concentration': self._calculate_herfindahl_index(combined_data),
            'network_density': nx.density(G)
        }
        
        return {
            'network': G,
            'communities': communities,
            'metrics': competitive_metrics
        }
    
    def _calculate_herfindahl_index(self, data):
        """Calculate Herfindahl-Hirschman Index for market concentration."""
        
        if data.empty:
            return 0
        
        # Calculate market shares (simplified)
        total_reviews = data['review_count'].sum()
        if total_reviews == 0:
            return 0
        
        market_shares = (data['review_count'] / total_reviews) ** 2
        return market_shares.sum()
    
    def _identify_market_gaps(self, market_indicators, competitive_analysis):
        """Identify market gaps and opportunities."""
        
        if market_indicators.empty:
            return None
        
        # Identify underserved areas
        underserved_areas = market_indicators[
            market_indicators['market_saturation'] < 0.5
        ].copy()
        
        # Identify high-potential areas
        high_potential_areas = market_indicators[
            (market_indicators['demographic_fit'] > 0.7) &
            (market_indicators['market_saturation'] < 0.8)
        ].copy()
        
        # Calculate opportunity scores
        if not underserved_areas.empty:
            underserved_areas['opportunity_score'] = (
                underserved_areas['demographic_fit'] * 50 +
                (1 - underserved_areas['market_saturation']) * 30 +
                underserved_areas['avg_rating'] * 20
            )
        
        if not high_potential_areas.empty:
            high_potential_areas['opportunity_score'] = (
                high_potential_areas['demographic_fit'] * 40 +
                (1 - high_potential_areas['market_saturation']) * 40 +
                high_potential_areas['avg_rating'] * 20
            )
        
        return {
            'underserved_areas': underserved_areas,
            'high_potential_areas': high_potential_areas
        }
    
    def _generate_market_forecasts(self, market_indicators, business_type):
        """Generate market forecasts for business planning."""
        
        if market_indicators.empty:
            return None
        
        # Prepare features for forecasting
        features = ['business_density', 'market_saturation', 'demographic_fit', 'avg_rating']
        feature_data = market_indicators[features].fillna(0)
        
        # Target variable: business success (simplified)
        target = market_indicators['avg_rating'].fillna(0)
        
        # Train forecasting model
        model = RandomForestRegressor(n_estimators=100, random_state=42)
        model.fit(feature_data, target)
        
        # Feature importance
        feature_importance = pd.DataFrame({
            'feature': features,
            'importance': model.feature_importances_
        }).sort_values('importance', ascending=False)
        
        # Generate market size estimates
        market_size_estimate = self._estimate_market_size(market_indicators, business_type)
        
        return {
            'model': model,
            'feature_importance': feature_importance,
            'market_size_estimate': market_size_estimate
        }
    
    def _estimate_market_size(self, data, business_type):
        """Estimate market size for a business type."""
        
        if data.empty:
            return 0
        
        # Get business requirements
        requirements = business_demographics.get(business_type, {})
        
        # Estimate based on demographics and competition
        population = data['population_density'].iloc[0] if not data.empty else 1000
        income_factor = data['median_income'].iloc[0] / requirements.get('min_income', 50000)
        competition_factor = 1 - data['market_saturation'].iloc[0] if not data.empty else 0.5
        
        # Market size formula (simplified)
        market_size = population * income_factor * competition_factor * 0.01
        
        return max(market_size, 0)

# Initialize market analyzer
market_analyzer = MarketAnalyzer()

# Analyze markets for each business type
market_analysis = {}
for state_code, state_info in market_data.items():
    state_name = state_info['name']
    print(f"\n📊 Analyzing markets in {state_name}...")
    
    state_market_analysis = {}
    
    for business_type in state_info['business_types']:
        print(f"  Analyzing {business_type} market...")
        
        # Get business data for this state
        state_business_data = business_data.get(state_code, {})
        
        # Get demographic data
        state_demographics = state_info.get('demographics')
        
        # Perform market analysis
        analysis_results = market_analyzer.analyze_market_opportunities(
            state_business_data,
            state_demographics,
            business_type
        )
        
        state_market_analysis[business_type] = analysis_results
        print(f"    ✓ Completed {business_type} analysis for {state_name}")
        
        # Save analysis results
        with open(data_dir / f"{state_code}_{business_type}_market_analysis.json", 'w') as f:
            json.dump(analysis_results, f, indent=2, default=str)
    
    market_analysis[state_code] = state_market_analysis
```

### **Step 5: Site Selection and Location Optimization**

```python
class SiteSelector:
    """Optimize site selection based on market analysis."""
    
    def __init__(self):
        self.location_scores = {}
    
    def optimize_site_selection(self, market_analysis, business_type, target_criteria):
        """Optimize site selection for a specific business type."""
        
        # Collect all potential locations
        all_locations = []
        
        for state_code, state_analysis in market_analysis.items():
            if business_type in state_analysis:
                business_analysis = state_analysis[business_type]
                
                # Get market opportunities
                opportunities = business_analysis.get('market_opportunities', {})
                
                if opportunities:
                    underserved = opportunities.get('underserved_areas')
                    high_potential = opportunities.get('high_potential_areas')
                    
                    if underserved is not None and not underserved.empty:
                        all_locations.extend(self._extract_location_data(underserved, 'underserved'))
                    
                    if high_potential is not None and not high_potential.empty:
                        all_locations.extend(self._extract_location_data(high_potential, 'high_potential'))
        
        if not all_locations:
            return pd.DataFrame()
        
        # Convert to DataFrame
        locations_df = pd.DataFrame(all_locations)
        
        # Score locations based on target criteria
        scored_locations = self._score_locations(locations_df, target_criteria)
        
        # Rank locations
        ranked_locations = scored_locations.sort_values('total_score', ascending=False)
        
        return ranked_locations
    
    def _extract_location_data(self, data, category):
        """Extract location data from market analysis results."""
        
        locations = []
        for idx, row in data.iterrows():
            location = {
                'state': row.get('state', 'Unknown'),
                'city': row.get('city', 'Unknown'),
                'category': category,
                'demographic_fit': row.get('demographic_fit', 0),
                'market_saturation': row.get('market_saturation', 0),
                'avg_rating': row.get('avg_rating', 0),
                'opportunity_score': row.get('opportunity_score', 0),
                'median_income': row.get('median_income', 0),
                'population_density': row.get('population_density', 0)
            }
            locations.append(location)
        
        return locations
    
    def _score_locations(self, locations_df, target_criteria):
        """Score locations based on target criteria."""
        
        scored_locations = locations_df.copy()
        
        # Define scoring weights
        weights = {
            'demographic_fit': 0.25,
            'market_opportunity': 0.30,
            'competitive_advantage': 0.20,
            'economic_stability': 0.15,
            'growth_potential': 0.10
        }
        
        # Calculate individual scores
        scored_locations['demographic_fit_score'] = (
            scored_locations['demographic_fit'] * 100
        )
        
        scored_locations['market_opportunity_score'] = (
            (1 - scored_locations['market_saturation']) * 100
        )
        
        scored_locations['competitive_advantage_score'] = (
            (1 - scored_locations['avg_rating'] / 5) * 100  # Lower competition = higher score
        )
        
        scored_locations['economic_stability_score'] = (
            (scored_locations['median_income'] / 100000) * 100
        ).clip(0, 100)
        
        scored_locations['growth_potential_score'] = (
            (scored_locations['population_density'] / 5000) * 100
        ).clip(0, 100)
        
        # Calculate weighted total score
        scored_locations['total_score'] = (
            scored_locations['demographic_fit_score'] * weights['demographic_fit'] +
            scored_locations['market_opportunity_score'] * weights['market_opportunity'] +
            scored_locations['competitive_advantage_score'] * weights['competitive_advantage'] +
            scored_locations['economic_stability_score'] * weights['economic_stability'] +
            scored_locations['growth_potential_score'] * weights['growth_potential']
        )
        
        # Add location recommendations
        scored_locations['recommendation'] = scored_locations['total_score'].apply(
            lambda x: 'Excellent' if x >= 80 else 'Good' if x >= 60 else 'Fair' if x >= 40 else 'Poor'
        )
        
        return scored_locations

# Initialize site selector
site_selector = SiteSelector()

# Define target criteria for site selection
target_criteria = {
    'restaurant': {
        'min_demographic_fit': 0.7,
        'max_market_saturation': 0.8,
        'min_income': 50000,
        'preferred_population_density': 'medium'
    },
    'retail': {
        'min_demographic_fit': 0.6,
        'max_market_saturation': 0.7,
        'min_income': 40000,
        'preferred_population_density': 'medium'
    }
}

# Optimize site selection for each business type
site_recommendations = {}
for business_type in ['restaurant', 'retail']:
    print(f"\n🎯 Optimizing site selection for {business_type}...")
    
    # Get site recommendations
    recommendations = site_selector.optimize_site_selection(
        market_analysis,
        business_type,
        target_criteria.get(business_type, {})
    )
    
    if not recommendations.empty:
        site_recommendations[business_type] = recommendations
        
        print(f"✓ Found {len(recommendations)} potential locations for {business_type}")
        
        # Show top recommendations
        top_recommendations = recommendations.head(5)
        print(f"  Top locations for {business_type}:")
        for idx, rec in top_recommendations.iterrows():
            print(f"    {rec['city']}, {rec['state']}: {rec['recommendation']} (Score: {rec['total_score']:.1f})")
        
        # Save recommendations
        recommendations.to_csv(data_dir / f"{business_type}_site_recommendations.csv", index=False)
    else:
        print(f"✗ No suitable locations found for {business_type}")
```

### **Step 6: Business Intelligence Dashboard**

```python
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import dash
from dash import dcc, html
from dash.dependencies import Input, Output

def create_business_intelligence_dashboard(market_analysis, site_recommendations):
    """Create an interactive dashboard for business intelligence."""
    
    app = dash.Dash(__name__)
    
    # Prepare data for visualization
    all_market_data = []
    all_site_data = []
    
    for state_code, state_analysis in market_analysis.items():
        for business_type, business_analysis in state_analysis.items():
            if 'market_indicators' in business_analysis and not business_analysis['market_indicators'].empty:
                business_analysis['market_indicators']['business_type'] = business_type
                business_analysis['market_indicators']['state'] = state_code
                all_market_data.append(business_analysis['market_indicators'])
    
    for business_type, recommendations in site_recommendations.items():
        if not recommendations.empty:
            recommendations['business_type'] = business_type
            all_site_data.append(recommendations)
    
    if all_market_data:
        combined_market_data = pd.concat(all_market_data, ignore_index=True)
        
        # Create dashboard layout
        app.layout = html.Div([
            html.H1("Business Intelligence Dashboard", 
                    style={'textAlign': 'center', 'color': '#2c3e50'}),
            
            html.Div([
                html.H3("Market Analysis by Business Type"),
                dcc.Graph(
                    id='market-analysis',
                    figure=px.scatter(
                        combined_market_data,
                        x='market_saturation',
                        y='demographic_fit',
                        color='business_type',
                        size='avg_rating',
                        hover_data=['city', 'state', 'business_density'],
                        title="Market Saturation vs. Demographic Fit by Business Type"
                    )
                )
            ]),
            
            html.Div([
                html.H3("Site Selection Recommendations"),
                dcc.Graph(
                    id='site-recommendations',
                    figure=px.scatter(
                        pd.concat(all_site_data, ignore_index=True) if all_site_data else pd.DataFrame(),
                        x='market_opportunity_score',
                        y='demographic_fit_score',
                        color='business_type',
                        size='total_score',
                        hover_data=['city', 'state', 'recommendation'],
                        title="Site Recommendations by Opportunity and Fit"
                    )
                )
            ]),
            
            html.Div([
                html.H3("Competitive Landscape"),
                dcc.Graph(
                    id='competitive-landscape',
                    figure=px.bar(
                        combined_market_data.groupby('business_type')['avg_rating'].mean().reset_index(),
                        x='business_type',
                        y='avg_rating',
                        title="Average Rating by Business Type"
                    )
                )
            ])
        ])
    
    return app

# Create and run dashboard
print("\n📊 Creating business intelligence dashboard...")
business_dashboard = create_business_intelligence_dashboard(market_analysis, site_recommendations)
print("✓ Interactive dashboard created")

# Save dashboard as HTML
try:
    business_dashboard.layout.children[0].children[1].figure.write_html(
        data_dir / "business_intelligence_dashboard.html"
    )
    print("✓ Dashboard saved as HTML")
except Exception as e:
    print(f"Could not save dashboard: {e}")
```

### **Step 7: Generate Strategic Business Reports**

```python
from siege_utilities.reporting.report_generator import ReportGenerator
from siege_utilities.reporting.chart_types import ChartType

def generate_business_strategy_report(market_analysis, site_recommendations, data_dir):
    """Generate a comprehensive business strategy report."""
    
    report_gen = ReportGenerator()
    
    # Calculate summary statistics
    total_locations = sum(
        len(recs) for recs in site_recommendations.values() 
        if recs is not None and not recs.empty
    )
    
    excellent_locations = sum(
        len(recs[recs['recommendation'] == 'Excellent']) 
        for recs in site_recommendations.values() 
        if recs is not None and not recs.empty
    )
    
    # Create report configuration
    report_config = {
        'title': 'Business Intelligence and Site Selection Report',
        'subtitle': f'Strategic Market Analysis - {datetime.now().strftime("%B %Y")}',
        'sections': [
            {
                'title': 'Executive Summary',
                'content': f"""
                This report provides comprehensive business intelligence analysis across multiple markets,
                identifying {total_locations} potential business locations with {excellent_locations} excellent opportunities.
                
                **Key Business Insights:**
                - Market saturation analysis reveals underserved areas
                - Competitive landscape assessment identifies strategic advantages
                - Demographic fit scoring optimizes location selection
                - Site recommendations prioritize growth potential and profitability
                """
            },
            {
                'title': 'Market Analysis Results',
                'content': f"""
                **Markets Analyzed:**
                {chr(10).join([f"- {market_data[code]['name']}" for code in market_data.keys()])}
                
                **Business Types Analyzed:**
                {chr(10).join([f"- {bt}" for bt in set([bt for state in market_analysis.values() for bt in state.keys()])])}
                
                **Total Market Opportunities:**
                {sum(len(analysis.get('market_opportunities', {}).get('underserved_areas', [])) + len(analysis.get('market_opportunities', {}).get('high_potential_areas', [])) for state in market_analysis.values() for analysis in state.values())}
                """
            },
            {
                'title': 'Site Selection Recommendations',
                'content': f"""
                **Location Quality Distribution:**
                - Excellent: {excellent_locations}
                - Good: {sum(len(recs[recs['recommendation'] == 'Good']) for recs in site_recommendations.values() if recs is not None and not recs.empty)}
                - Fair: {sum(len(recs[recs['recommendation'] == 'Fair']) for recs in site_recommendations.values() if recs is not None and not recs.empty)}
                - Poor: {sum(len(recs[recs['recommendation'] == 'Poor']) for recs in site_recommendations.values() if recs is not None and not recs.empty)}
                
                **Top Selection Criteria:**
                - Demographic fit and target market alignment
                - Market saturation and competitive landscape
                - Economic stability and growth potential
                - Location accessibility and visibility
                - Regulatory environment and business climate
                """
            }
        ],
        'charts': [
            {
                'type': ChartType.SCATTER,
                'data': pd.concat([recs for recs in site_recommendations.values() if recs is not None and not recs.empty], ignore_index=True),
                'title': 'Site Selection Recommendations by Score',
                'x_column': 'market_opportunity_score',
                'y_column': 'demographic_fit_score',
                'color_column': 'business_type'
            }
        ]
    }
    
    # Generate report
    report_file = data_dir / "business_intelligence_strategy_report.pdf"
    report_gen.generate_report(report_config, report_file)
    
    print(f"✓ Business strategy report generated: {report_file}")
    return report_file

# Generate the business strategy report
business_report = generate_business_strategy_report(market_analysis, site_recommendations, data_dir)
```

### **Step 8: Data Export and Integration**

```python
from siege_utilities.analytics import upload_to_snowflake
from siege_utilities.files import ensure_path_exists

# Export to multiple formats
export_dir = data_dir / "exports"
ensure_path_exists(export_dir)

# Export market analysis results
for state_code, state_analysis in market_analysis.items():
    for business_type, business_analysis in state_analysis.items():
        if 'market_indicators' in business_analysis and not business_analysis['market_indicators'].empty:
            business_analysis['market_indicators'].to_csv(
                export_dir / f"{state_code}_{business_type}_market_indicators.csv", 
                index=False
            )

# Export site recommendations
for business_type, recommendations in site_recommendations.items():
    if recommendations is not None and not recommendations.empty:
        recommendations.to_csv(
            export_dir / f"{business_type}_site_recommendations.csv", 
            index=False
        )

# Export summary statistics
summary_stats = {
    'total_locations': total_locations,
    'excellent_locations': excellent_locations,
    'market_analysis_summary': {
        state_code: {
            business_type: {
                'total_opportunities': len(analysis.get('market_opportunities', {}).get('underserved_areas', [])) + len(analysis.get('market_opportunities', {}).get('high_potential_areas', [])),
                'competitive_metrics': analysis.get('competitive_analysis', {}).get('metrics', {})
            }
            for business_type, analysis in state_analysis.items()
        }
        for state_code, state_analysis in market_analysis.items()
    }
}

with open(export_dir / "business_intelligence_summary.json", 'w') as f:
    json.dump(summary_stats, f, indent=2, default=str)

print("✓ Business intelligence data exported")

# Optional: Upload to Snowflake
try:
    # Combine all market indicators
    all_market_data = []
    for state_analysis in market_analysis.values():
        for business_analysis in state_analysis.values():
            if 'market_indicators' in business_analysis and not business_analysis['market_indicators'].empty:
                all_market_data.append(business_analysis['market_indicators'])
    
    if all_market_data:
        combined_market_data = pd.concat(all_market_data, ignore_index=True)
        
        # Upload to Snowflake
        success = upload_to_snowflake(
            combined_market_data,
            'business_intelligence_market_analysis',
            overwrite=True
        )
        
        if success:
            print("✓ Business intelligence data uploaded to Snowflake")
        else:
            print("✗ Failed to upload to Snowflake")
            
except Exception as e:
    print(f"Snowflake upload not available: {e}")
```

## 🎉 **Final Results**

After running this complete pipeline, you'll have:

1. **📊 Market Intelligence**: Comprehensive analysis of business markets
2. **🎯 Site Recommendations**: Optimized location selection for businesses
3. **📈 Competitive Analysis**: Market structure and competitive landscape
4. **🗺️ Interactive Dashboard**: Web-based business intelligence tool
5. **📄 Strategic Reports**: Professional PDF reports with recommendations
6. **💾 Data Exports**: Multiple formats for further analysis
7. **☁️ Cloud Integration**: Optional Snowflake storage

## 🔧 **Customization Options**

### **Add More Business Types**
```python
business_types.extend([
    'fitness_center',
    'coffee_shop',
    'dental_clinic',
    'auto_repair'
])
```

### **Enhance Scoring Algorithm**
```python
# Add seasonal factors
scoring_weights['seasonal_demand'] = 0.10

# Add regulatory factors
scoring_weights['regulatory_environment'] = 0.15

# Add accessibility factors
scoring_weights['transportation_access'] = 0.10
```

### **Add Machine Learning Models**
```python
# Business success prediction
success_model = XGBRegressor()
success_model.fit(features, success_metrics)

# Market demand forecasting
demand_model = LSTM()
demand_model.fit(historical_data, demand_patterns)
```

## 🚀 **Next Steps**

1. **Real-time Market Monitoring**: Set up automated market tracking
2. **Performance Validation**: Track actual business performance vs. predictions
3. **Dynamic Pricing**: Implement dynamic pricing based on market conditions
4. **Expansion Planning**: Plan multi-location expansion strategies
5. **Risk Assessment**: Add comprehensive risk analysis models

This recipe demonstrates how to build a professional-grade business intelligence system using the enhanced Census utilities and analytics integration!

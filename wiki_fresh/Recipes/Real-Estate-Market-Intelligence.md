# Real Estate Market Intelligence System

This recipe demonstrates how to build a comprehensive real estate market intelligence platform using Census data, property databases, and advanced analytics to identify investment opportunities and market trends.

## 🏠 **Overview**

Create a real estate market intelligence system that:
- Analyzes property values and market trends by geographic area
- Identifies emerging neighborhoods and investment opportunities
- Combines Census demographics with property data
- Provides predictive analytics for market forecasting
- Generates investment reports and market insights

## 🚀 **Prerequisites**

```bash
pip install siege-utilities[geo,analytics,reporting,spatial]
pip install zillow-python realtor-python pandas-profiling
pip install plotly dash folium seaborn scikit-learn
```

## 📊 **Sample Datasets We'll Use**

### **Primary Data Sources**
1. **Census TIGER/Line**: Neighborhood boundaries and demographics
2. **Zillow API**: Property values, rental rates, market trends
3. **Realtor.com API**: Property listings, sales data, market statistics
4. **OpenStreetMap**: Amenities, transportation, points of interest
5. **Government Data**: Building permits, zoning information

### **External Data Integration**
- **Data.world**: Historical property data, market indices
- **Snowflake**: Store large property datasets
- **Facebook Business**: Local business density and activity
- **Google Analytics**: Web traffic patterns for neighborhoods

## 🔄 **Complete Workflow**

### **Step 1: Market Area Definition and Planning**

```python
from siege_utilities.geo.spatial_data import census_source
from siege_utilities.analytics import search_datadotworld_datasets
from siege_utilities.core.logging import setup_logging
import pandas as pd
import geopandas as gpd
import numpy as np

# Setup logging
setup_logging(level='INFO')

# Define target markets (major metropolitan areas)
target_metros = {
    'CA': {
        'name': 'California',
        'metros': ['Los Angeles', 'San Francisco', 'San Diego'],
        'fips': '06'
    },
    'TX': {
        'name': 'Texas', 
        'metros': ['Houston', 'Dallas', 'Austin'],
        'fips': '48'
    },
    'NY': {
        'name': 'New York',
        'metros': ['New York City', 'Buffalo', 'Rochester'],
        'fips': '36'
    }
}

print("🎯 Target Markets:")
for state, info in target_metros.items():
    print(f"  {info['name']}: {', '.join(info['metros'])}")

# Discover available Census data
analysis_year = 2020
print(f"\n📊 Using Census Year: {analysis_year}")

# Get available boundary types for detailed analysis
boundary_types = census_source.get_available_boundary_types(analysis_year)
print(f"Available boundaries: {list(boundary_types.keys())}")
```

### **Step 2: Download Geographic and Demographic Data**

```python
from siege_utilities.files import ensure_path_exists, get_download_directory
import time

# Create data directory structure
data_dir = get_download_directory() / "real_estate_intelligence" / str(analysis_year)
ensure_path_exists(data_dir)

# Download boundaries and demographics for each target state
market_data = {}
for state_code, state_info in target_metros.items():
    state_fips = state_info['fips']
    state_name = state_info['name']
    
    print(f"\n🏠 Processing {state_name}...")
    
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
        
        # Get state demographics
        state_demographics = census_source.get_state_demographics(
            year=analysis_year,
            state_fips=state_fips
        )
        
        market_data[state_code] = {
            'counties': counties,
            'tracts': tracts,
            'block_groups': block_groups,
            'demographics': state_demographics,
            'name': state_name,
            'fips': state_fips
        }
        
        print(f"✓ {state_name}: {len(counties)} counties, {len(tracts)} tracts, {len(block_groups)} block groups")
        
        # Save geographic data
        counties.to_file(data_dir / f"{state_code}_counties.geojson", driver='GeoJSON')
        tracts.to_file(data_dir / f"{state_code}_tracts.geojson", driver='GeoJSON')
        block_groups.to_file(data_dir / f"{state_code}_block_groups.geojson", driver='GeoJSON')
        
        if state_demographics is not None:
            state_demographics.to_csv(data_dir / f"{state_code}_demographics.csv", index=False)
    
    # Rate limiting
    time.sleep(1)
```

### **Step 3: Property Data Collection and Integration**

```python
import requests
from datetime import datetime, timedelta
import json

class PropertyDataCollector:
    """Collect property data from multiple sources."""
    
    def __init__(self, api_keys=None):
        self.api_keys = api_keys or {}
        self.session = requests.Session()
    
    def get_zillow_data(self, location, property_type='all'):
        """Get Zillow data for a specific location."""
        
        # Zillow API endpoint (you'll need to register for API access)
        base_url = "https://api.bridgedataoutput.com/api/v2/zestimates"
        
        headers = {
            'Authorization': f'Bearer {self.api_keys.get("zillow", "DEMO_KEY")}',
            'Content-Type': 'application/json'
        }
        
        params = {
            'access_token': self.api_keys.get("zillow", "DEMO_KEY"),
            'location': location,
            'property_type': property_type
        }
        
        try:
            response = self.session.get(base_url, headers=headers, params=params)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error getting Zillow data for {location}: {e}")
            return None
    
    def get_realtor_data(self, location, property_type='all'):
        """Get Realtor.com data for a specific location."""
        
        # Realtor.com API endpoint
        base_url = "https://realtor.p.rapidapi.com/properties/v3/list"
        
        headers = {
            'X-RapidAPI-Key': self.api_keys.get("realtor", "DEMO_KEY"),
            'X-RapidAPI-Host': 'realtor.p.rapidapi.com'
        }
        
        params = {
            'location': location,
            'property_type': property_type,
            'limit': 100
        }
        
        try:
            response = self.session.get(base_url, headers=headers, params=params)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error getting Realtor data for {location}: {e}")
            return None
    
    def get_historical_data(self, location, years_back=5):
        """Get historical property data from data.world."""
        
        from siege_utilities.analytics import search_datadotworld_datasets, load_datadotworld_dataset
        
        # Search for historical property datasets
        datasets = search_datadotworld_datasets(
            query=f"property values {location} historical",
            limit=5
        )
        
        historical_data = []
        for dataset in datasets:
            try:
                df = load_datadotworld_dataset(dataset['id'])
                if df is not None:
                    historical_data.append({
                        'dataset_id': dataset['id'],
                        'title': dataset['title'],
                        'data': df
                    })
            except Exception as e:
                print(f"Failed to load dataset {dataset['id']}: {e}")
        
        return historical_data

# Initialize property data collector
property_collector = PropertyDataCollector({
    'zillow': 'YOUR_ZILLOW_API_KEY',
    'realtor': 'YOUR_REALTOR_API_KEY'
})

# Collect property data for each market
property_data = {}
for state_code, state_info in market_data.items():
    state_name = state_info['name']
    print(f"\n🏘️ Collecting property data for {state_name}...")
    
    state_property_data = {}
    
    for metro in state_info['metros']:
        print(f"  Processing {metro}...")
        
        # Get Zillow data
        zillow_data = property_collector.get_zillow_data(metro)
        if zillow_data:
            state_property_data[f"{metro}_zillow"] = zillow_data
        
        # Get Realtor data
        realtor_data = property_collector.get_realtor_data(metro)
        if realtor_data:
            state_property_data[f"{metro}_realtor"] = realtor_data
        
        # Get historical data
        historical_data = property_collector.get_historical_data(metro)
        if historical_data:
            state_property_data[f"{metro}_historical"] = historical_data
        
        print(f"    ✓ {metro}: Zillow({zillow_data is not None}), Realtor({realtor_data is not None}), Historical({len(historical_data) if historical_data else 0})")
    
    property_data[state_code] = state_property_data
    
    # Save property data
    with open(data_dir / f"{state_code}_property_data.json", 'w') as f:
        json.dump(state_property_data, f, indent=2, default=str)
```

### **Step 4: Market Analysis and Trend Identification**

```python
from sklearn.ensemble import RandomForestRegressor, IsolationForest
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
import pandas as pd
import numpy as np

class MarketAnalyzer:
    """Analyze real estate market trends and identify opportunities."""
    
    def __init__(self):
        self.scaler = StandardScaler()
        self.clustering_model = KMeans(n_clusters=6, random_state=42)
        self.anomaly_detector = IsolationForest(contamination=0.1, random_state=42)
    
    def analyze_market_trends(self, property_data, demographics_data):
        """Analyze market trends and identify patterns."""
        
        # Combine property and demographic data
        combined_data = self._combine_data_sources(property_data, demographics_data)
        
        # Calculate market indicators
        market_indicators = self._calculate_market_indicators(combined_data)
        
        # Identify market segments
        market_segments = self._identify_market_segments(market_indicators)
        
        # Detect anomalies and opportunities
        opportunities = self._detect_opportunities(market_indicators)
        
        # Generate market forecasts
        forecasts = self._generate_forecasts(market_indicators)
        
        return {
            'market_indicators': market_indicators,
            'market_segments': market_segments,
            'opportunities': opportunities,
            'forecasts': forecasts
        }
    
    def _combine_data_sources(self, property_data, demographics_data):
        """Combine property and demographic data sources."""
        
        combined_data = []
        
        for state_code, state_property in property_data.items():
            for metro, metro_data in state_property.items():
                if 'zillow' in metro:
                    # Extract Zillow data
                    zillow_df = self._extract_zillow_data(metro_data)
                    if zillow_df is not None:
                        # Add demographic context
                        demographic_context = self._get_demographic_context(
                            metro, demographics_data
                        )
                        if demographic_context is not None:
                            zillow_df = zillow_df.merge(
                                demographic_context, 
                                left_index=True, 
                                right_index=True, 
                                how='left'
                            )
                        combined_data.append(zillow_df)
        
        if combined_data:
            return pd.concat(combined_data, ignore_index=True)
        return pd.DataFrame()
    
    def _extract_zillow_data(self, zillow_data):
        """Extract relevant data from Zillow API response."""
        
        try:
            # This is a simplified extraction - adjust based on actual API response
            if 'properties' in zillow_data:
                properties = zillow_data['properties']
                
                extracted_data = []
                for prop in properties:
                    extracted_data.append({
                        'zpid': prop.get('zpid'),
                        'address': prop.get('address', {}).get('streetAddress'),
                        'city': prop.get('address', {}).get('city'),
                        'state': prop.get('address', {}).get('state'),
                        'zipcode': prop.get('address', {}).get('zipcode'),
                        'price': prop.get('price'),
                        'bedrooms': prop.get('bedrooms'),
                        'bathrooms': prop.get('bathrooms'),
                        'sqft': prop.get('sqft'),
                        'lot_size': prop.get('lotSize'),
                        'year_built': prop.get('yearBuilt'),
                        'zestimate': prop.get('zestimate'),
                        'rent_zestimate': prop.get('rentZestimate')
                    })
                
                return pd.DataFrame(extracted_data)
        
        except Exception as e:
            print(f"Error extracting Zillow data: {e}")
            return None
    
    def _get_demographic_context(self, metro, demographics_data):
        """Get demographic context for a metropolitan area."""
        
        # This would involve spatial joining between property locations and demographic boundaries
        # For now, return a simplified version
        return pd.DataFrame({
            'median_income': [demographics_data.get('median_income', 50000)],
            'population_density': [demographics_data.get('population_density', 1000)],
            'education_rate': [demographics_data.get('education_rate', 25)],
            'median_age': [demographics_data.get('median_age', 35)]
        })
    
    def _calculate_market_indicators(self, combined_data):
        """Calculate key market indicators."""
        
        if combined_data.empty:
            return pd.DataFrame()
        
        # Calculate price per square foot
        combined_data['price_per_sqft'] = (
            combined_data['price'] / combined_data['sqft']
        )
        
        # Calculate price to rent ratio
        combined_data['price_to_rent_ratio'] = (
            combined_data['price'] / (combined_data['rent_zestimate'] * 12)
        )
        
        # Calculate market efficiency (price vs. zestimate)
        combined_data['market_efficiency'] = (
            combined_data['price'] / combined_data['zestimate']
        )
        
        # Calculate property age
        current_year = datetime.now().year
        combined_data['property_age'] = current_year - combined_data['year_built']
        
        # Calculate lot efficiency
        combined_data['lot_efficiency'] = (
            combined_data['sqft'] / combined_data['lot_size']
        )
        
        return combined_data
    
    def _identify_market_segments(self, market_indicators):
        """Identify distinct market segments using clustering."""
        
        if market_indicators.empty:
            return None
        
        # Prepare features for clustering
        features = ['price_per_sqft', 'price_to_rent_ratio', 'market_efficiency', 'property_age']
        feature_data = market_indicators[features].fillna(0)
        
        # Scale features
        scaled_features = self.scaler.fit_transform(feature_data)
        
        # Perform clustering
        clusters = self.clustering_model.fit_predict(scaled_features)
        market_indicators['market_segment'] = clusters
        
        # Analyze segments
        segment_analysis = market_indicators.groupby('market_segment')[features].agg(['mean', 'std', 'count'])
        
        return {
            'segmented_data': market_indicators,
            'segment_analysis': segment_analysis
        }
    
    def _detect_opportunities(self, market_indicators):
        """Detect investment opportunities using anomaly detection."""
        
        if market_indicators.empty:
            return None
        
        # Prepare features for anomaly detection
        features = ['price_per_sqft', 'price_to_rent_ratio', 'market_efficiency']
        feature_data = market_indicators[features].fillna(0)
        
        # Detect anomalies
        anomalies = self.anomaly_detector.fit_predict(feature_data)
        market_indicators['is_anomaly'] = anomalies == -1
        
        # Identify opportunities (properties that are undervalued)
        opportunities = market_indicators[
            (market_indicators['is_anomaly']) & 
            (market_indicators['market_efficiency'] < 0.9)  # Price below zestimate
        ].copy()
        
        # Rank opportunities by potential
        opportunities['opportunity_score'] = (
            (1 - opportunities['market_efficiency']) * 100 +  # Higher discount = higher score
            (opportunities['price_to_rent_ratio'] < 15).astype(int) * 20 +  # Good rental yield
            (opportunities['property_age'] < 20).astype(int) * 10  # Newer properties
        )
        
        opportunities = opportunities.sort_values('opportunity_score', ascending=False)
        
        return opportunities
    
    def _generate_forecasts(self, market_indicators):
        """Generate market forecasts using machine learning."""
        
        if market_indicators.empty:
            return None
        
        # Prepare features for forecasting
        features = ['price_per_sqft', 'price_to_rent_ratio', 'median_income', 'population_density']
        feature_data = market_indicators[features].fillna(0)
        
        # Target variable: price
        target = market_indicators['price'].fillna(0)
        
        # Train forecasting model
        model = RandomForestRegressor(n_estimators=100, random_state=42)
        model.fit(feature_data, target)
        
        # Feature importance
        feature_importance = pd.DataFrame({
            'feature': features,
            'importance': model.feature_importances_
        }).sort_values('importance', ascending=False)
        
        # Generate predictions for new scenarios
        # This is a simplified example - in practice, you'd use more sophisticated forecasting
        base_scenario = feature_data.mean().values.reshape(1, -1)
        
        # Optimistic scenario (higher income, lower density)
        optimistic_scenario = base_scenario.copy()
        optimistic_scenario[0, 2] *= 1.2  # 20% higher income
        optimistic_scenario[0, 3] *= 0.8  # 20% lower density
        
        # Pessimistic scenario (lower income, higher density)
        pessimistic_scenario = base_scenario.copy()
        pessimistic_scenario[0, 2] *= 0.8  # 20% lower income
        pessimistic_scenario[0, 3] *= 1.2  # 20% higher density
        
        scenarios = {
            'base': model.predict(base_scenario)[0],
            'optimistic': model.predict(optimistic_scenario)[0],
            'pessimistic': model.predict(pessimistic_scenario)[0]
        }
        
        return {
            'model': model,
            'feature_importance': feature_importance,
            'scenarios': scenarios
        }

# Initialize market analyzer
market_analyzer = MarketAnalyzer()

# Analyze markets
print("\n📊 Analyzing real estate markets...")
market_analysis = {}
for state_code, state_info in market_data.items():
    state_name = state_info['name']
    print(f"  Analyzing {state_name}...")
    
    # Get property data for this state
    state_property_data = property_data.get(state_code, {})
    
    # Get demographic data
    state_demographics = state_info.get('demographics')
    
    # Perform market analysis
    analysis_results = market_analyzer.analyze_market_trends(
        state_property_data, 
        state_demographics
    )
    
    market_analysis[state_code] = analysis_results
    print(f"    ✓ Completed analysis for {state_name}")
    
    # Save analysis results
    with open(data_dir / f"{state_code}_market_analysis.json", 'w') as f:
        json.dump(analysis_results, f, indent=2, default=str)
```

### **Step 5: Investment Opportunity Scoring and Ranking**

```python
class InvestmentScorer:
    """Score and rank investment opportunities."""
    
    def __init__(self):
        self.scoring_weights = {
            'price_discount': 0.25,      # How much below market value
            'rental_yield': 0.20,        # Rental income potential
            'appreciation_potential': 0.20,  # Growth potential
            'market_stability': 0.15,    # Market volatility
            'location_score': 0.20       # Neighborhood quality
        }
    
    def score_opportunities(self, opportunities, market_indicators, demographics_data):
        """Score investment opportunities based on multiple factors."""
        
        if opportunities.empty:
            return pd.DataFrame()
        
        scored_opportunities = opportunities.copy()
        
        # Calculate individual scores
        scored_opportunities['price_discount_score'] = (
            (1 - scored_opportunities['market_efficiency']) * 100
        )
        
        scored_opportunities['rental_yield_score'] = (
            (1 / scored_opportunities['price_to_rent_ratio']) * 1000
        ).clip(0, 100)
        
        scored_opportunities['appreciation_potential_score'] = (
            (scored_opportunities['median_income'] / 50000) * 50 +  # Higher income = higher potential
            (scored_opportunities['education_rate'] / 25) * 50      # Higher education = higher potential
        ).clip(0, 100)
        
        scored_opportunities['market_stability_score'] = (
            (1 - scored_opportunities['price_per_sqft'].std() / scored_opportunities['price_per_sqft'].mean()) * 100
        ).clip(0, 100)
        
        # Location score based on demographics and amenities
        scored_opportunities['location_score'] = (
            (scored_opportunities['median_income'] / 50000) * 30 +
            (scored_opportunities['education_rate'] / 25) * 30 +
            (scored_opportunities['population_density'] < 2000).astype(int) * 40  # Prefer lower density
        ).clip(0, 100)
        
        # Calculate weighted total score
        scored_opportunities['total_score'] = (
            scored_opportunities['price_discount_score'] * self.scoring_weights['price_discount'] +
            scored_opportunities['rental_yield_score'] * self.scoring_weights['rental_yield'] +
            scored_opportunities['appreciation_potential_score'] * self.scoring_weights['appreciation_potential'] +
            scored_opportunities['market_stability_score'] * self.scoring_weights['market_stability'] +
            scored_opportunities['location_score'] * self.scoring_weights['location_score']
        )
        
        # Rank opportunities
        scored_opportunities = scored_opportunities.sort_values('total_score', ascending=False)
        
        # Add investment recommendations
        scored_opportunities['recommendation'] = scored_opportunities['total_score'].apply(
            lambda x: 'Strong Buy' if x >= 80 else 'Buy' if x >= 60 else 'Hold' if x >= 40 else 'Avoid'
        )
        
        return scored_opportunities

# Score investment opportunities
print("\n🎯 Scoring investment opportunities...")
investment_scorer = InvestmentScorer()

scored_opportunities = {}
for state_code, state_info in market_data.items():
    state_name = state_info['name']
    print(f"  Scoring opportunities in {state_name}...")
    
    # Get opportunities from market analysis
    state_opportunities = market_analysis[state_code]['opportunities']
    
    if state_opportunities is not None and not state_opportunities.empty:
        # Score opportunities
        scored = investment_scorer.score_opportunities(
            state_opportunities,
            market_analysis[state_code]['market_indicators'],
            state_info['demographics']
        )
        
        scored_opportunities[state_code] = scored
        
        print(f"    ✓ Scored {len(scored)} opportunities in {state_name}")
        
        # Save scored opportunities
        scored.to_csv(data_dir / f"{state_code}_scored_opportunities.csv", index=False)
        
        # Show top opportunities
        top_opportunities = scored.head(5)
        print(f"    Top opportunities in {state_name}:")
        for idx, opp in top_opportunities.iterrows():
            print(f"      {opp['address']}: {opp['recommendation']} (Score: {opp['total_score']:.1f})")
```

### **Step 6: Interactive Market Dashboard**

```python
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import folium

def create_market_dashboard(market_analysis, scored_opportunities):
    """Create an interactive dashboard for real estate market analysis."""
    
    app = dash.Dash(__name__)
    
    # Prepare data for visualization
    all_market_data = []
    all_opportunities = []
    
    for state_code, analysis in market_analysis.items():
        if 'market_indicators' in analysis and not analysis['market_indicators'].empty:
            all_market_data.append(analysis['market_indicators'])
        
        if state_code in scored_opportunities and not scored_opportunities[state_code].empty:
            all_opportunities.append(scored_opportunities[state_code])
    
    if all_market_data:
        combined_market_data = pd.concat(all_market_data, ignore_index=True)
        
        # Create dashboard layout
        app.layout = html.Div([
            html.H1("Real Estate Market Intelligence Dashboard", 
                    style={'textAlign': 'center', 'color': '#2c3e50'}),
            
            html.Div([
                html.H3("Market Segments Analysis"),
                dcc.Graph(
                    id='market-segments',
                    figure=px.scatter(
                        combined_market_data,
                        x='price_per_sqft',
                        y='price_to_rent_ratio',
                        color='market_segment',
                        size='price',
                        hover_data=['address', 'city', 'state'],
                        title="Market Segments by Price and Rental Yield"
                    )
                )
            ]),
            
            html.Div([
                html.H3("Investment Opportunities"),
                dcc.Graph(
                    id='opportunities-map',
                    figure=px.scatter(
                        pd.concat(all_opportunities, ignore_index=True) if all_opportunities else pd.DataFrame(),
                        x='price',
                        y='total_score',
                        color='recommendation',
                        size='opportunity_score',
                        hover_data=['address', 'city', 'state', 'total_score'],
                        title="Investment Opportunities by Price and Score"
                    )
                )
            ]),
            
            html.Div([
                html.H3("Market Trends"),
                dcc.Graph(
                    id='market-trends',
                    figure=px.line(
                        combined_market_data.groupby('market_segment')['price_per_sqft'].mean().reset_index(),
                        x='market_segment',
                        y='price_per_sqft',
                        title="Average Price per Square Foot by Market Segment"
                    )
                )
            ])
        ])
    
    return app

# Create and run dashboard
print("\n📊 Creating market intelligence dashboard...")
market_dashboard = create_market_dashboard(market_analysis, scored_opportunities)
print("✓ Interactive dashboard created")

# Save dashboard as HTML
try:
    market_dashboard.layout.children[0].children[1].figure.write_html(
        data_dir / "market_intelligence_dashboard.html"
    )
    print("✓ Dashboard saved as HTML")
except Exception as e:
    print(f"Could not save dashboard: {e}")
```

### **Step 7: Generate Investment Reports**

```python
from siege_utilities.reporting.report_generator import ReportGenerator
from siege_utilities.reporting.chart_types import ChartType

def generate_investment_report(market_analysis, scored_opportunities, data_dir):
    """Generate a comprehensive investment report."""
    
    report_gen = ReportGenerator()
    
    # Calculate summary statistics
    total_opportunities = sum(
        len(opps) for opps in scored_opportunities.values() 
        if opps is not None and not opps.empty
    )
    
    strong_buy_count = sum(
        len(opps[opps['recommendation'] == 'Strong Buy']) 
        for opps in scored_opportunities.values() 
        if opps is not None and not opps.empty
    )
    
    # Create report configuration
    report_config = {
        'title': 'Real Estate Market Intelligence Report',
        'subtitle': f'Investment Opportunities Analysis - {datetime.now().strftime("%B %Y")}',
        'sections': [
            {
                'title': 'Executive Summary',
                'content': f"""
                This report provides comprehensive analysis of real estate markets across multiple states,
                identifying {total_opportunities} investment opportunities with {strong_buy_count} strong buy recommendations.
                
                **Key Market Insights:**
                - Market segmentation reveals distinct property categories
                - Anomaly detection identifies undervalued properties
                - Investment scoring ranks opportunities by potential return
                - Geographic analysis shows regional market variations
                """
            },
            {
                'title': 'Market Analysis Results',
                'content': f"""
                **States Analyzed:**
                {chr(10).join([f"- {market_data[code]['name']}" for code in market_data.keys()])}
                
                **Total Properties Analyzed:**
                {sum(len(analysis['market_indicators']) for analysis in market_analysis.values() if 'market_indicators' in analysis)}
                
                **Market Segments Identified:**
                {len(set([seg for analysis in market_analysis.values() if 'segmented_data' in analysis and analysis['segmented_data'] is not None for seg in analysis['segmented_data']['market_segment']]))}
                """
            },
            {
                'title': 'Investment Recommendations',
                'content': f"""
                **Opportunity Distribution:**
                - Strong Buy: {strong_buy_count}
                - Buy: {sum(len(opps[opps['recommendation'] == 'Buy']) for opps in scored_opportunities.values() if opps is not None and not opps.empty)}
                - Hold: {sum(len(opps[opps['recommendation'] == 'Hold']) for opps in scored_opportunities.values() if opps is not None and not opps.empty)}
                - Avoid: {sum(len(opps[opps['recommendation'] == 'Avoid']) for opps in scored_opportunities.values() if opps is not None and not opps.empty)}
                
                **Top Investment Criteria:**
                - Price discount to market value
                - Rental yield potential
                - Appreciation potential based on demographics
                - Market stability and volatility
                - Location quality and amenities
                """
            }
        ],
        'charts': [
            {
                'type': ChartType.SCATTER,
                'data': pd.concat([opps for opps in scored_opportunities.values() if opps is not None and not opps.empty], ignore_index=True),
                'title': 'Investment Opportunities by Score and Price',
                'x_column': 'price',
                'y_column': 'total_score',
                'color_column': 'recommendation'
            }
        ]
    }
    
    # Generate report
    report_file = data_dir / "real_estate_investment_report.pdf"
    report_gen.generate_report(report_config, report_file)
    
    print(f"✓ Investment report generated: {report_file}")
    return report_file

# Generate the investment report
investment_report = generate_investment_report(market_analysis, scored_opportunities, data_dir)
```

### **Step 8: Data Export and Integration**

```python
from siege_utilities.analytics import upload_to_snowflake
from siege_utilities.files import ensure_path_exists

# Export to multiple formats
export_dir = data_dir / "exports"
ensure_path_exists(export_dir)

# Export market analysis results
for state_code, analysis in market_analysis.items():
    if 'market_indicators' in analysis and not analysis['market_indicators'].empty:
        analysis['market_indicators'].to_csv(
            export_dir / f"{state_code}_market_indicators.csv", 
            index=False
        )
    
    if 'segmented_data' in analysis and analysis['segmented_data'] is not None:
        analysis['segmented_data'].to_csv(
            export_dir / f"{state_code}_market_segments.csv", 
            index=False
        )

# Export scored opportunities
for state_code, opportunities in scored_opportunities.items():
    if opportunities is not None and not opportunities.empty:
        opportunities.to_csv(
            export_dir / f"{state_code}_scored_opportunities.csv", 
            index=False
        )

# Export summary statistics
summary_stats = {
    'total_opportunities': total_opportunities,
    'strong_buy_count': strong_buy_count,
    'market_analysis_summary': {
        state_code: {
            'total_properties': len(analysis.get('market_indicators', [])),
            'market_segments': len(analysis.get('segmented_data', {}).get('market_segment', []).unique()) if analysis.get('segmented_data') is not None else 0,
            'opportunities_found': len(analysis.get('opportunities', [])) if analysis.get('opportunities') is not None else 0
        }
        for state_code, analysis in market_analysis.items()
    }
}

with open(export_dir / "market_analysis_summary.json", 'w') as f:
    json.dump(summary_stats, f, indent=2, default=str)

print("✓ Market analysis data exported")

# Optional: Upload to Snowflake
try:
    # Combine all market indicators
    all_market_data = []
    for analysis in market_analysis.values():
        if 'market_indicators' in analysis and not analysis['market_indicators'].empty:
            all_market_data.append(analysis['market_indicators'])
    
    if all_market_data:
        combined_market_data = pd.concat(all_market_data, ignore_index=True)
        
        # Upload to Snowflake
        success = upload_to_snowflake(
            combined_market_data,
            'real_estate_market_analysis',
            overwrite=True
        )
        
        if success:
            print("✓ Market analysis data uploaded to Snowflake")
        else:
            print("✗ Failed to upload to Snowflake")
            
except Exception as e:
    print(f"Snowflake upload not available: {e}")
```

## 🎉 **Final Results**

After running this complete pipeline, you'll have:

1. **📊 Market Intelligence**: Comprehensive analysis of real estate markets
2. **🎯 Investment Opportunities**: Scored and ranked property investments
3. **📈 Market Trends**: Segmentation and forecasting analysis
4. **🗺️ Interactive Dashboard**: Web-based market visualization tool
5. **📄 Investment Reports**: Professional PDF reports with recommendations
6. **💾 Data Exports**: Multiple formats for further analysis
7. **☁️ Cloud Integration**: Optional Snowflake storage

## 🔧 **Customization Options**

### **Add More Data Sources**
```python
# Add Redfin API
redfin_data = redfin_api.get_property_data(location)

# Add MLS data
mls_data = mls_api.get_listings(location)

# Add building permit data
permit_data = government_api.get_building_permits(location)
```

### **Enhance Scoring Algorithm**
```python
# Add macroeconomic factors
scoring_weights['interest_rate_impact'] = 0.10
scoring_weights['economic_growth'] = 0.15

# Add seasonal adjustments
seasonal_factors = self._calculate_seasonal_factors(property_data)
```

### **Add Machine Learning Models**
```python
# Price prediction model
price_model = XGBRegressor()
price_model.fit(features, prices)

# Market timing model
timing_model = RandomForestClassifier()
timing_model.fit(features, market_direction)
```

## 🚀 **Next Steps**

1. **Real-time Updates**: Set up automated data collection
2. **Portfolio Tracking**: Monitor actual investment performance
3. **Risk Management**: Add risk assessment models
4. **Market Alerts**: Set up notification systems
5. **Mobile App**: Create mobile investment dashboard

This recipe demonstrates how to build a professional-grade real estate market intelligence system using the enhanced Census utilities and analytics integration!

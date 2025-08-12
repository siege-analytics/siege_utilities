# External Data Integration for Geographic Reporting

## Problem Statement

You need to create geographic reports using data from multiple external sources such as Google Analytics, Facebook Business, databases, and custom APIs. The data needs to be processed, cleaned, and integrated with geographic boundaries to create comprehensive spatial analysis reports.

## Solution

Use siege_utilities' built-in connectors and data processing capabilities to integrate external data sources with the geographic reporting system, creating unified datasets for bivariate choropleth maps and comprehensive analysis.

## Prerequisites

- siege_utilities with analytics connectors
- Required API credentials and access
- Geographic boundary files (GeoJSON, Shapefiles)
- Database connection details (if applicable)

## Step-by-Step Implementation

### 1. Google Analytics Integration

```python
from siege_utilities.analytics.google_analytics import GoogleAnalyticsConnector
from siege_utilities.reporting.chart_generator import ChartGenerator
import pandas as pd

# Initialize Google Analytics connector
ga_connector = GoogleAnalyticsConnector(
    credentials_path='path/to/credentials.json',
    property_id='your_property_id'
)

# Retrieve geographic data from Google Analytics
ga_data = ga_connector.batch_retrieve_ga_data(
    metrics=['sessions', 'bounce_rate', 'avg_session_duration'],
    dimensions=['country', 'region'],
    date_range=['2023-01-01', '2023-12-31']
)

# Process and clean the data
ga_df = pd.DataFrame(ga_data)
ga_df['country'] = ga_df['country'].str.strip()
ga_df['region'] = ga_df['region'].str.strip()

# Aggregate data by geographic region
geographic_metrics = ga_df.groupby(['country', 'region']).agg({
    'sessions': 'sum',
    'bounce_rate': 'mean',
    'avg_session_duration': 'mean'
}).reset_index()

# Create bivariate choropleth for engagement vs. performance
chart_gen = ChartGenerator()
engagement_chart = chart_gen.create_bivariate_choropleth_matplotlib(
    data=geographic_metrics,
    geodata='path/to/world_regions.geojson',
    location_column='region',
    value_column1='sessions',
    value_column2='avg_session_duration',
    title="Website Engagement by Geographic Region",
    width=12.0,
    height=10.0
)
```

### 2. Facebook Business Integration

```python
from siege_utilities.analytics.facebook_business import FacebookBusinessConnector

# Initialize Facebook Business connector
fb_connector = FacebookBusinessConnector(
    access_token='your_access_token',
    app_id='your_app_id',
    app_secret='your_app_secret'
)

# Retrieve geographic advertising data
fb_data = fb_connector.batch_retrieve_facebook_data(
    metrics=['impressions', 'clicks', 'spend'],
    breakdowns=['country', 'region'],
    date_range=['2023-01-01', '2023-12-31']
)

# Process Facebook data
fb_df = pd.DataFrame(fb_data)
fb_df['ctr'] = (fb_df['clicks'] / fb_df['impressions']) * 100
fb_df['cpc'] = fb_df['spend'] / fb_df['clicks']

# Create bivariate choropleth for advertising performance
ad_performance_chart = chart_gen.create_bivariate_choropleth_matplotlib(
    data=fb_df,
    geodata='path/to/world_regions.geojson',
    location_column='region',
    value_column1='ctr',
    value_column2='cpc',
    title="Facebook Ad Performance by Region",
    width=12.0,
    height=10.0
)
```

### 3. Database Integration

```python
from siege_utilities.config.databases import DatabaseConnector
import sqlalchemy as sa

# Initialize database connector
db_connector = DatabaseConnector(
    connection_string='postgresql://user:password@localhost/dbname'
)

# Query customer data with geographic information
customer_query = """
SELECT 
    state,
    COUNT(*) as customer_count,
    AVG(annual_revenue) as avg_revenue,
    AVG(customer_satisfaction_score) as avg_satisfaction
FROM customers 
WHERE signup_date >= '2023-01-01'
GROUP BY state
"""

customer_data = db_connector.execute_query(customer_query)
customer_df = pd.DataFrame(customer_data)

# Create bivariate choropleth for customer metrics
customer_chart = chart_gen.create_bivariate_choropleth_matplotlib(
    data=customer_df,
    geodata='path/to/us_states.geojson',
    location_column='state',
    value_column1='customer_count',
    value_column2='avg_revenue',
    title="Customer Distribution and Revenue by State",
    width=12.0,
    height=10.0
)
```

### 4. Custom API Integration

```python
import requests
import json

def fetch_custom_api_data(api_endpoint, api_key):
    """Fetch data from custom API with geographic information."""
    headers = {'Authorization': f'Bearer {api_key}'}
    
    response = requests.get(api_endpoint, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"API request failed: {response.status_code}")

# Fetch data from custom API
custom_data = fetch_custom_api_data(
    'https://api.example.com/geographic-metrics',
    'your_api_key'
)

# Process custom API data
custom_df = pd.DataFrame(custom_data)
custom_df['location'] = custom_df['location'].str.title()

# Create visualization for custom data
custom_chart = chart_gen.create_bivariate_choropleth(
    data=custom_df,
    location_column='location',
    value_column1='metric1',
    value_column2='metric2',
    title="Custom API Metrics by Location",
    width=10.0,
    height=8.0
)
```

### 5. Data Integration and Unified Reporting

```python
from siege_utilities.reporting.report_generator import ReportGenerator

# Combine data from multiple sources
combined_data = {
    'google_analytics': geographic_metrics,
    'facebook_business': fb_df,
    'database': customer_df,
    'custom_api': custom_df
}

# Create unified geographic analysis
def create_unified_geographic_report(combined_data, chart_gen):
    """Create comprehensive report from multiple data sources."""
    
    charts = []
    insights = []
    
    # Google Analytics insights
    if 'google_analytics' in combined_data:
        ga_data = combined_data['google_analytics']
        ga_chart = chart_gen.create_bivariate_choropleth_matplotlib(
            data=ga_data,
            geodata='path/to/world_regions.geojson',
            location_column='region',
            value_column1='sessions',
            value_column2='avg_session_duration',
            title="Website Performance by Region"
        )
        charts.append(ga_chart)
        
        # Add insights
        top_regions = ga_data.nlargest(5, 'sessions')
        insights.append(f"Top performing regions: {', '.join(top_regions['region'].tolist())}")
    
    # Facebook Business insights
    if 'facebook_business' in combined_data:
        fb_data = combined_data['facebook_business']
        fb_chart = chart_gen.create_bivariate_choropleth_matplotlib(
            data=fb_data,
            geodata='path/to/world_regions.geojson',
            location_column='region',
            value_column1='ctr',
            value_column2='cpc',
            title="Advertising Performance by Region"
        )
        charts.append(fb_chart)
        
        # Add insights
        best_ctr_region = fb_data.loc[fb_data['ctr'].idxmax(), 'region']
        insights.append(f"Best click-through rate in: {best_ctr_region}")
    
    # Database insights
    if 'database' in combined_data:
        db_data = combined_data['database']
        db_chart = chart_gen.create_bivariate_choropleth_matplotlib(
            data=db_data,
            geodata='path/to/us_states.geojson',
            location_column='state',
            value_column1='customer_count',
            value_column2='avg_revenue',
            title="Customer Metrics by State"
        )
        charts.append(db_chart)
        
        # Add insights
        highest_revenue_state = db_data.loc[db_data['avg_revenue'].idxmax(), 'state']
        insights.append(f"Highest average revenue in: {highest_revenue_state}")
    
    return charts, insights

# Generate unified report
charts, insights = create_unified_geographic_report(combined_data, chart_gen)

# Create comprehensive report
report_gen = ReportGenerator()
unified_report = report_gen.create_analytics_report(
    title="Multi-Source Geographic Analysis",
    charts=charts,
    data_summary="Comprehensive analysis combining data from Google Analytics, Facebook Business, internal databases, and custom APIs.",
    insights=insights,
    recommendations=[
        "Focus marketing efforts on high-performing regions identified in Google Analytics",
        "Optimize Facebook ad targeting based on geographic performance patterns",
        "Develop customer acquisition strategies for high-revenue states",
        "Establish regional partnerships in underperforming areas"
    ]
)

# Generate report in multiple formats
report_gen.generate_pdf_report(unified_report, "unified_geographic_analysis.pdf")
report_gen.generate_powerpoint_report(unified_report, "unified_geographic_analysis.pptx")
```

### 6. Automated Data Pipeline

```python
import schedule
import time
from datetime import datetime, timedelta

def automated_data_collection():
    """Automated data collection and report generation."""
    
    try:
        # Collect data from all sources
        data_sources = {
            'google_analytics': collect_ga_data(),
            'facebook_business': collect_fb_data(),
            'database': collect_database_data(),
            'custom_api': collect_custom_api_data()
        }
        
        # Generate report
        charts, insights = create_unified_geographic_report(data_sources, chart_gen)
        
        # Create and save report
        report = report_gen.create_analytics_report(
            title=f"Automated Geographic Analysis - {datetime.now().strftime('%Y-%m-%d')}",
            charts=charts,
            insights=insights
        )
        
        # Save with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_gen.generate_pdf_report(report, f"automated_analysis_{timestamp}.pdf")
        
        print(f"Automated report generated successfully: {timestamp}")
        
    except Exception as e:
        print(f"Automated data collection failed: {e}")

# Schedule automated collection (daily at 9 AM)
schedule.every().day.at("09:00").do(automated_data_collection)

# Run scheduler
while True:
    schedule.run_pending()
    time.sleep(60)
```

## Advanced Integration Features

### 1. Real-time Data Streaming

```python
import asyncio
import aiohttp
from websockets import connect

async def stream_real_time_data():
    """Stream real-time data for live geographic dashboards."""
    
    async with connect('wss://your-websocket-endpoint') as websocket:
        async for message in websocket:
            data = json.loads(message)
            
            # Process real-time data
            if data.get('type') == 'geographic_update':
                # Update charts in real-time
                updated_chart = chart_gen.create_bivariate_choropleth(
                    data=data['metrics'],
                    location_column='region',
                    value_column1='metric1',
                    value_column2='metric2',
                    title="Real-time Geographic Metrics"
                )
                
                # Update dashboard or report
                update_live_dashboard(updated_chart)

# Run real-time streaming
asyncio.run(stream_real_time_data())
```

### 2. Data Quality Monitoring

```python
def monitor_data_quality(data_sources):
    """Monitor data quality across all sources."""
    
    quality_report = {}
    
    for source_name, data in data_sources.items():
        quality_metrics = {
            'row_count': len(data),
            'missing_values': data.isnull().sum().sum(),
            'duplicates': data.duplicated().sum(),
            'data_types': data.dtypes.to_dict()
        }
        
        quality_report[source_name] = quality_metrics
    
    return quality_report

# Monitor data quality
quality_report = monitor_data_quality(combined_data)
print("Data Quality Report:")
for source, metrics in quality_report.items():
    print(f"\n{source}:")
    for metric, value in metrics.items():
        print(f"  {metric}: {value}")
```

## Expected Output

- **Unified datasets** combining multiple external sources
- **Comprehensive geographic reports** with multi-source insights
- **Automated data pipelines** for regular reporting
- **Real-time dashboards** with live data updates
- **Data quality monitoring** and validation
- **Professional reports** in multiple formats (PDF, PowerPoint)

## Best Practices

1. **Data Validation**: Always validate external data before processing
2. **Error Handling**: Implement robust error handling for API failures
3. **Rate Limiting**: Respect API rate limits and implement appropriate delays
4. **Data Caching**: Cache frequently accessed data to improve performance
5. **Security**: Secure API credentials and database connections
6. **Monitoring**: Implement comprehensive logging and monitoring

## Troubleshooting

- **API Failures**: Implement retry logic and fallback data sources
- **Data Mismatches**: Validate geographic identifiers across all sources
- **Performance Issues**: Use data sampling and aggregation for large datasets
- **Authentication Errors**: Regularly rotate API keys and monitor access

This external data integration approach enables comprehensive geographic reporting by combining multiple data sources into unified, actionable insights while maintaining data quality and system reliability.

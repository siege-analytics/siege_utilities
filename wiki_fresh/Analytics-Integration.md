# Analytics Integration - Multi-Platform Data Collection

## Problem

You need to collect analytics data from multiple platforms (Google Analytics, Facebook Business, etc.) and consolidate them into a unified dataset for analysis, but managing different APIs, authentication, and data formats is complex and time-consuming.

## Solution

Use Siege Utilities' analytics modules to create a unified data collection pipeline that handles multiple platforms, manages authentication, and standardizes data formats for consistent analysis.

## Quick Start

```python
import siege_utilities
import pandas as pd
from datetime import datetime, timedelta

# Initialize logging
siege_utilities.log_info("Multi-platform analytics collection initialized")

# Run the complete pipeline
results = run_multi_platform_collection()
```

## Complete Implementation

### 1. Google Analytics Integration

#### Setup Google Analytics API
```python
import siege_utilities
from siege_utilities.analytics.google_analytics import GoogleAnalytics

# Initialize Google Analytics client
ga_client = GoogleAnalytics(
    view_id='123456789',
    credentials_path='path/to/credentials.json'
)

# Test connection
if ga_client.test_connection():
    print("✅ Google Analytics connection successful")
else:
    print("❌ Google Analytics connection failed")
```

#### Collect Google Analytics Data
```python
# Define date range
start_date = datetime.now() - timedelta(days=30)
end_date = datetime.now()

# Collect pageview data
pageview_data = ga_client.get_pageviews(
    start_date=start_date,
    end_date=end_date,
    metrics=['pageviews', 'uniquePageviews', 'avgTimeOnPage'],
    dimensions=['pagePath', 'pageTitle', 'date']
)

# Collect user behavior data
behavior_data = ga_client.get_user_behavior(
    start_date=start_date,
    end_date=end_date,
    metrics=['sessions', 'users', 'newUsers', 'bounceRate']
)

# Collect e-commerce data (if applicable)
ecommerce_data = ga_client.get_ecommerce_data(
    start_date=start_date,
    end_date=end_date,
    metrics=['transactions', 'revenue', 'itemsPerTransaction']
)

print(f"✅ Collected {len(pageview_data)} pageview records")
print(f"✅ Collected {len(behavior_data)} behavior records")
print(f"✅ Collected {len(ecommerce_data)} e-commerce records")
```

### 2. Facebook Business Integration

#### Setup Facebook Business API
```python
from siege_utilities.analytics.facebook_business import FacebookBusiness

# Initialize Facebook Business client
fb_client = FacebookBusiness(
    access_token='your_access_token',
    ad_account_id='act_123456789'
)

# Test connection
if fb_client.test_connection():
    print("✅ Facebook Business connection successful")
else:
    print("❌ Facebook Business connection failed")
```

#### Collect Facebook Advertising Data
```python
# Collect ad performance data
ad_performance = fb_client.get_ad_performance(
    start_date=start_date,
    end_date=end_date,
    fields=['campaign_name', 'adset_name', 'impressions', 'clicks', 'spend', 'cpm', 'ctr']
)

# Collect audience insights
audience_insights = fb_client.get_audience_insights(
    target_audience='your_target_audience',
    fields=['age', 'gender', 'location', 'interests']
)

# Collect conversion data
conversion_data = fb_client.get_conversions(
    start_date=start_date,
    end_date=end_date,
    conversion_types=['purchase', 'lead', 'add_to_cart']
)

print(f"✅ Collected {len(ad_performance)} ad performance records")
print(f"✅ Collected {len(audience_insights)} audience insight records")
print(f"✅ Collected {len(conversion_data)} conversion records")
```

### 3. Data Standardization and Consolidation

#### Create Unified Data Schema
```python
import pandas as pd
from datetime import datetime

def standardize_google_analytics_data(ga_data):
    """Standardize Google Analytics data format."""
    if ga_data is None or ga_data.empty:
        return pd.DataFrame()
    
    # Standardize column names
    ga_data.columns = ga_data.columns.str.lower().str.replace(' ', '_')
    
    # Add source identifier
    ga_data['data_source'] = 'google_analytics'
    ga_data['collection_timestamp'] = datetime.now()
    
    # Standardize date format
    if 'date' in ga_data.columns:
        ga_data['date'] = pd.to_datetime(ga_data['date'])
    
    return ga_data

def standardize_facebook_data(fb_data):
    """Standardize Facebook Business data format."""
    if fb_data is None or fb_data.empty:
        return pd.DataFrame()
    
    # Standardize column names
    fb_data.columns = fb_data.columns.str.lower().str.replace(' ', '_')
    
    # Add source identifier
    fb_data['data_source'] = 'facebook_business'
    fb_data['collection_timestamp'] = datetime.now()
    
    return fb_data
```

#### Consolidate All Data Sources
```python
def consolidate_analytics_data(ga_data, fb_data):
    """Consolidate data from multiple sources."""
    consolidated_data = []
    
    # Process Google Analytics data
    if not ga_data.empty:
        ga_standardized = standardize_google_analytics_data(ga_data)
        consolidated_data.append(ga_standardized)
    
    # Process Facebook Business data
    if not fb_data.empty:
        fb_standardized = standardize_facebook_data(fb_data)
        consolidated_data.append(fb_standardized)
    
    # Combine all data
    if consolidated_data:
        final_data = pd.concat(consolidated_data, ignore_index=True)
        print(f"✅ Consolidated {len(final_data)} total records")
        return final_data
    else:
        print("⚠️ No data to consolidate")
        return pd.DataFrame()
```

### 4. Complete Multi-Platform Pipeline

#### Main Collection Function
```python
def run_multi_platform_collection():
    """Run complete multi-platform analytics collection."""
    print("🚀 Starting multi-platform analytics collection...")
    
    try:
        # Initialize clients
        ga_client = GoogleAnalytics(
            view_id='123456789',
            credentials_path='path/to/credentials.json'
        )
        
        fb_client = FacebookBusiness(
            access_token='your_access_token',
            ad_account_id='act_123456789'
        )
        
        # Define collection period
        start_date = datetime.now() - timedelta(days=30)
        end_date = datetime.now()
        
        print(f"📅 Collecting data from {start_date.date()} to {end_date.date()}")
        
        # Collect Google Analytics data
        print("📊 Collecting Google Analytics data...")
        ga_pageviews = ga_client.get_pageviews(
            start_date=start_date,
            end_date=end_date,
            metrics=['pageviews', 'uniquePageviews', 'avgTimeOnPage'],
            dimensions=['pagePath', 'pageTitle', 'date']
        )
        
        ga_behavior = ga_client.get_user_behavior(
            start_date=start_date,
            end_date=end_date,
            metrics=['sessions', 'users', 'newUsers', 'bounceRate']
        )
        
        # Collect Facebook Business data
        print("📘 Collecting Facebook Business data...")
        fb_ads = fb_client.get_ad_performance(
            start_date=start_date,
            end_date=end_date,
            fields=['campaign_name', 'adset_name', 'impressions', 'clicks', 'spend', 'cpm', 'ctr']
        )
        
        fb_conversions = fb_client.get_conversions(
            start_date=start_date,
            end_date=end_date,
            conversion_types=['purchase', 'lead', 'add_to_cart']
        )
        
        # Consolidate data
        print("🔗 Consolidating data...")
        all_data = consolidate_analytics_data(
            pd.concat([ga_pageviews, ga_behavior], ignore_index=True),
            pd.concat([fb_ads, fb_conversions], ignore_index=True)
        )
        
        # Save consolidated data
        if not all_data.empty:
            output_path = f"analytics_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            all_data.to_csv(output_path, index=False)
            print(f"💾 Data saved to {output_path}")
        
        return all_data
        
    except Exception as e:
        print(f"❌ Error during collection: {e}")
        siege_utilities.log_error(f"Analytics collection failed: {e}")
        return pd.DataFrame()
```

### 5. Advanced Features

#### Automated Scheduling
```python
import schedule
import time

def schedule_analytics_collection():
    """Schedule daily analytics collection."""
    
    # Collect data daily at 2 AM
    schedule.every().day.at("02:00").do(run_multi_platform_collection)
    
    # Collect data every Monday at 9 AM for weekly reports
    schedule.every().monday.at("09:00").do(run_weekly_analytics_report)
    
    print("📅 Analytics collection scheduled")
    
    while True:
        schedule.run_pending()
        time.sleep(60)

def run_weekly_analytics_report():
    """Generate weekly analytics report."""
    print("📊 Generating weekly analytics report...")
    
    # Collect data for the past week
    end_date = datetime.now()
    start_date = end_date - timedelta(days=7)
    
    # Run collection and generate report
    data = run_multi_platform_collection()
    
    if not data.empty:
        # Generate insights
        insights = generate_analytics_insights(data)
        
        # Create report
        create_analytics_report(data, insights, "Weekly Analytics Report")
        
        print("✅ Weekly report generated")
```

#### Data Quality Validation
```python
def validate_analytics_data(data):
    """Validate collected analytics data quality."""
    validation_results = {
        'total_records': len(data),
        'missing_values': data.isnull().sum().to_dict(),
        'duplicate_records': data.duplicated().sum(),
        'date_range': {
            'start': data['date'].min() if 'date' in data.columns else None,
            'end': data['date'].max() if 'date' in data.columns else None
        }
    }
    
    # Check for data quality issues
    issues = []
    
    if validation_results['total_records'] == 0:
        issues.append("No data collected")
    
    if validation_results['duplicate_records'] > 0:
        issues.append(f"Found {validation_results['duplicate_records']} duplicate records")
    
    # Check for missing critical fields
    critical_fields = ['data_source', 'collection_timestamp']
    for field in critical_fields:
        if field in data.columns and data[field].isnull().sum() > 0:
            issues.append(f"Missing values in critical field: {field}")
    
    validation_results['issues'] = issues
    validation_results['is_valid'] = len(issues) == 0
    
    return validation_results
```

## Expected Output

```
🚀 Starting multi-platform analytics collection...
📅 Collecting data from 2024-08-13 to 2024-08-13
📊 Collecting Google Analytics data...
✅ Collected 1,247 pageview records
✅ Collected 89 behavior records
📘 Collecting Facebook Business data...
✅ Collected 156 ad performance records
✅ Collected 23 conversion records
🔗 Consolidating data...
✅ Consolidated 1,515 total records
💾 Data saved to analytics_data_20240813_143022.csv
📅 Analytics collection scheduled
```

## Configuration Options

### Google Analytics Configuration
```yaml
google_analytics:
  view_id: "123456789"
  credentials_path: "path/to/credentials.json"
  metrics:
    - "pageviews"
    - "uniquePageviews"
    - "sessions"
    - "users"
  dimensions:
    - "pagePath"
    - "pageTitle"
    - "date"
    - "source"
```

### Facebook Business Configuration
```yaml
facebook_business:
  access_token: "your_access_token"
  ad_account_id: "act_123456789"
  fields:
    - "campaign_name"
    - "adset_name"
    - "impressions"
    - "clicks"
    - "spend"
  conversion_types:
    - "purchase"
    - "lead"
    - "add_to_cart"
```

## Troubleshooting

### Common Issues

1. **Authentication Errors**
   - Verify API credentials and permissions
   - Check token expiration dates
   - Ensure proper scopes are granted

2. **Rate Limiting**
   - Implement exponential backoff
   - Respect API rate limits
   - Use batch processing for large datasets

3. **Data Quality Issues**
   - Validate data before processing
   - Handle missing values appropriately
   - Check for data format inconsistencies

### Error Handling
```python
def handle_api_errors(func):
    """Decorator for handling API errors gracefully."""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            siege_utilities.log_error(f"API error in {func.__name__}: {e}")
            return None
    return wrapper
```

## Next Steps

After successful analytics integration:

- **Data Analysis**: Use consolidated data for insights
- **Reporting**: Generate automated reports and dashboards
- **Optimization**: Implement data quality monitoring
- **Expansion**: Add more data sources (Twitter, LinkedIn, etc.)

## Related Recipes

- **[Comprehensive Reporting](Comprehensive-Reporting)** - Generate reports from collected data
- **[Batch Processing](Batch-Processing)** - Process large analytics datasets
- **[Basic Setup](Basic-Setup)** - Configure Siege Utilities for analytics
- **[Client Management](Examples/Client-Management)** - Set up client-specific analytics

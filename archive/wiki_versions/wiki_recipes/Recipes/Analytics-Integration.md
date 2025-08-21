# 📊 Analytics Integration - Multi-Platform Data Collection

<div align="center">

![Analytics](https://img.shields.io/badge/Analytics-Multi_Platform-blue)
![Integration](https://img.shields.io/badge/Integration-Google_GA%2BFacebook-orange)
![Data](https://img.shields.io/badge/Data-Collection-green)

**Unified analytics data collection from multiple platforms** 🚀

</div>

---

## 🎯 **Problem**

You need to collect analytics data from multiple platforms (Google Analytics, Facebook Business, etc.) and consolidate them into a unified dataset for analysis, but managing different APIs, authentication, and data formats is complex and time-consuming.

## 💡 **Solution**

Use Siege Utilities' analytics modules to create a unified data collection pipeline that handles multiple platforms, manages authentication, and standardizes data formats for consistent analysis.

## 🚀 **Quick Start**

```python
import siege_utilities
import pandas as pd
from datetime import datetime, timedelta

# Initialize logging
siege_utilities.log_info("Multi-platform analytics collection initialized")

# Run the complete pipeline
results = run_multi_platform_collection()
```

## 📋 **Complete Implementation**

### **1. Setup and Configuration**

```python
import siege_utilities
import pandas as pd
from datetime import datetime, timedelta
import json

# Initialize logging
siege_utilities.log_info("Multi-platform analytics collection initialized")

# Configuration for multiple platforms
ANALYTICS_CONFIG = {
    'google_analytics': {
        'view_id': '123456789',
        'credentials_file': 'ga_credentials.json',
        'start_date': '2024-01-01',
        'end_date': '2024-01-31'
    },
    'facebook_business': {
        'access_token': 'your_fb_access_token',
        'ad_account_id': 'act_123456789',
        'start_date': '2024-01-01',
        'end_date': '2024-01-31'
    }
}
```

### **2. Google Analytics Data Collection**

```python
def collect_google_analytics_data(config):
    """Collect data from Google Analytics"""
    
    try:
        siege_utilities.log_info("Starting Google Analytics data collection")
        
        # Collect basic metrics
        ga_data = siege_utilities.get_analytics_data(
            view_id=config['view_id'],
            start_date=config['start_date'],
            end_date=config['end_date'],
            metrics=['sessions', 'users', 'pageviews', 'bounceRate'],
            dimensions=['date', 'pagePath', 'source']
        )
        
        # Collect user behavior data
        user_behavior = siege_utilities.get_user_metrics(
            view_id=config['view_id'],
            start_date=config['start_date'],
            end_date=config['end_date']
        )
        
        # Collect page performance data
        page_performance = siege_utilities.get_page_views(
            view_id=config['view_id'],
            start_date=config['start_date'],
            end_date=config['end_date'],
            max_results=100
        )
        
        siege_utilities.log_info(f"Google Analytics: Collected {len(ga_data)} data points")
        
        return {
            'basic_metrics': ga_data,
            'user_behavior': user_behavior,
            'page_performance': page_performance,
            'platform': 'google_analytics',
            'collection_timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        siege_utilities.log_error(f"Google Analytics collection failed: {e}")
        return None
```

### **3. Facebook Business Data Collection**

```python
def collect_facebook_business_data(config):
    """Collect data from Facebook Business API"""
    
    try:
        siege_utilities.log_info("Starting Facebook Business data collection")
        
        # Get ad accounts
        ad_accounts = siege_utilities.get_ad_accounts(config['access_token'])
        
        # Collect campaign data
        campaigns = siege_utilities.get_campaigns(
            config['access_token'], 
            config['ad_account_id']
        )
        
        # Collect ad performance data
        ad_insights = siege_utilities.get_insights(
            config['access_token'],
            [campaign['id'] for campaign in campaigns],
            fields=['impressions', 'clicks', 'spend', 'ctr', 'cpc', 'reach']
        )
        
        # Collect ad set data
        ad_sets = siege_utilities.get_ad_sets(
            config['access_token'],
            config['ad_account_id']
        )
        
        siege_utilities.log_info(f"Facebook Business: Collected data for {len(campaigns)} campaigns")
        
        return {
            'ad_accounts': ad_accounts,
            'campaigns': campaigns,
            'ad_insights': ad_insights,
            'ad_sets': ad_sets,
            'platform': 'facebook_business',
            'collection_timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        siege_utilities.log_error(f"Facebook Business collection failed: {e}")
        return None
```

### **4. Data Standardization and Consolidation**

```python
def standardize_analytics_data(ga_data, fb_data):
    """Standardize data from multiple platforms into consistent format"""
    
    standardized_data = {
        'platform_summary': [],
        'unified_metrics': [],
        'cross_platform_insights': {}
    }
    
    # Standardize Google Analytics data
    if ga_data:
        ga_summary = {
            'platform': 'Google Analytics',
            'total_sessions': sum(item.get('sessions', 0) for item in ga_data['basic_metrics']),
            'total_users': sum(item.get('users', 0) for item in ga_data['basic_metrics']),
            'total_pageviews': sum(item.get('pageviews', 0) for item in ga_data['basic_metrics']),
            'avg_bounce_rate': sum(item.get('bounceRate', 0) for item in ga_data['basic_metrics']) / len(ga_data['basic_metrics']),
            'data_points': len(ga_data['basic_metrics'])
        }
        standardized_data['platform_summary'].append(ga_summary)
        
        # Convert to unified format
        for item in ga_data['basic_metrics']:
            unified_item = {
                'date': item.get('date'),
                'platform': 'Google Analytics',
                'metric_type': 'web_analytics',
                'sessions': item.get('sessions', 0),
                'users': item.get('users', 0),
                'pageviews': item.get('pageviews', 0),
                'bounce_rate': item.get('bounceRate', 0),
                'source': item.get('source', 'direct')
            }
            standardized_data['unified_metrics'].append(unified_item)
    
    # Standardize Facebook Business data
    if fb_data:
        fb_summary = {
            'platform': 'Facebook Business',
            'total_campaigns': len(fb_data['campaigns']),
            'total_impressions': sum(item.get('impressions', 0) for item in fb_data['ad_insights']),
            'total_clicks': sum(item.get('clicks', 0) for item in fb_data['ad_insights']),
            'total_spend': sum(item.get('spend', 0) for item in fb_data['ad_insights']),
            'avg_ctr': sum(item.get('ctr', 0) for item in fb_data['ad_insights']) / len(fb_data['ad_insights']),
            'data_points': len(fb_data['ad_insights'])
        }
        standardized_data['platform_summary'].append(fb_summary)
        
        # Convert to unified format
        for item in fb_data['ad_insights']:
            unified_item = {
                'date': datetime.now().strftime('%Y-%m-%d'),
                'platform': 'Facebook Business',
                'metric_type': 'ad_performance',
                'impressions': item.get('impressions', 0),
                'clicks': item.get('clicks', 0),
                'spend': item.get('spend', 0),
                'ctr': item.get('ctr', 0),
                'cpc': item.get('cpc', 0),
                'reach': item.get('reach', 0)
            }
            standardized_data['unified_metrics'].append(unified_item)
    
    # Generate cross-platform insights
    if ga_data and fb_data:
        standardized_data['cross_platform_insights'] = {
            'total_platforms': 2,
            'total_data_points': len(standardized_data['unified_metrics']),
            'collection_timestamp': datetime.now().isoformat(),
            'data_freshness': 'real-time'
        }
    
    return standardized_data
```

### **5. Data Export and Storage**

```python
def export_analytics_data(standardized_data, output_dir):
    """Export standardized data to various formats"""
    
    siege_utilities.ensure_path_exists(output_dir)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Export to JSON
    json_file = f"{output_dir}/analytics_data_{timestamp}.json"
    with open(json_file, 'w') as f:
        json.dump(standardized_data, f, indent=2, default=str)
    
    # Export to CSV
    if standardized_data['unified_metrics']:
        df = pd.DataFrame(standardized_data['unified_metrics'])
        csv_file = f"{output_dir}/unified_metrics_{timestamp}.csv"
        df.to_csv(csv_file, index=False)
    
    # Export platform summary
    if standardized_data['platform_summary']:
        summary_df = pd.DataFrame(standardized_data['platform_summary'])
        summary_file = f"{output_dir}/platform_summary_{timestamp}.csv"
        summary_df.to_csv(summary_file, index=False)
    
    siege_utilities.log_info(f"Data exported to {output_dir}")
    
    return {
        'json_file': json_file,
        'csv_file': csv_file if standardized_data['unified_metrics'] else None,
        'summary_file': summary_file if standardized_data['platform_summary'] else None
    }
```

### **6. Complete Multi-Platform Collection Pipeline**

```python
def run_multi_platform_collection():
    """Run complete multi-platform analytics collection"""
    
    siege_utilities.log_info("Starting multi-platform analytics collection pipeline")
    
    # Step 1: Collect data from each platform
    ga_data = collect_google_analytics_data(ANALYTICS_CONFIG['google_analytics'])
    fb_data = collect_facebook_business_data(ANALYTICS_CONFIG['facebook_business'])
    
    # Step 2: Standardize and consolidate data
    standardized_data = standardize_analytics_data(ga_data, fb_data)
    
    # Step 3: Export data
    output_dir = 'analytics_exports'
    export_files = export_analytics_data(standardized_data, output_dir)
    
    # Step 4: Generate summary report
    total_platforms = len(standardized_data['platform_summary'])
    total_metrics = len(standardized_data['unified_metrics'])
    
    siege_utilities.log_info(f"Collection complete: {total_platforms} platforms, {total_metrics} metrics")
    
    # Print summary
    print("\n" + "="*50)
    print("MULTI-PLATFORM ANALYTICS COLLECTION SUMMARY")
    print("="*50)
    
    for platform in standardized_data['platform_summary']:
        print(f"\n{platform['platform']}:")
        for key, value in platform.items():
            if key != 'platform':
                print(f"  {key}: {value}")
    
    print(f"\nTotal unified metrics: {total_metrics}")
    print(f"Export files: {list(export_files.values())}")
    
    return standardized_data, export_files

# Run the complete pipeline
if __name__ == "__main__":
    results = run_multi_platform_collection()
```

## 📊 **Expected Output**

```
2024-01-15 10:30:00 - multi_platform_analytics - INFO - Multi-platform analytics collection initialized
2024-01-15 10:30:01 - multi_platform_analytics - INFO - Starting Google Analytics data collection
2024-01-15 10:30:02 - multi_platform_analytics - INFO - Google Analytics: Collected 31 data points
2024-01-15 10:30:03 - multi_platform_analytics - INFO - Starting Facebook Business data collection
2024-01-15 10:30:04 - multi_platform_analytics - INFO - Facebook Business: Collected data for 5 campaigns
2024-01-15 10:30:05 - multi_platform_analytics - INFO - Data exported to analytics_exports
2024-01-15 10:30:05 - multi_platform_analytics - INFO - Collection complete: 2 platforms, 36 metrics

==================================================
MULTI-PLATFORM ANALYTICS COLLECTION SUMMARY
==================================================

Google Analytics:
  total_sessions: 15420
  total_users: 12350
  total_pageviews: 45680
  avg_bounce_rate: 0.42
  data_points: 31

Facebook Business:
  total_campaigns: 5
  total_impressions: 125000
  total_clicks: 2500
  total_spend: 1500.50
  avg_ctr: 0.02
  data_points: 5

Total unified metrics: 36
Export files: ['analytics_exports/analytics_data_20240115_103005.json', 'analytics_exports/unified_metrics_20240115_103005.csv', 'analytics_exports/platform_summary_20240115_103005.csv']
```

## ⚠️ **Important Notes**

- **🔐 Authentication**: Store API credentials securely, not in code
- **⏱️ Rate Limiting**: Implement delays between API calls to respect rate limits
- **🛡️ Error Handling**: Always implement comprehensive error handling for API failures
- **🔄 Data Freshness**: Consider implementing incremental data collection for efficiency
- **💾 Storage**: Choose appropriate storage format based on your analysis needs
- **📊 Monitoring**: Set up alerts for collection failures or data quality issues

## 🚨 **Troubleshooting**

### **Common Issues**

1. **🔐 Authentication Errors**: Check API credentials and permissions
2. **⏱️ Rate Limiting**: Implement exponential backoff for failed requests
3. **📊 Data Format Changes**: APIs may change data formats - implement validation
4. **🌐 Network Issues**: Implement retry logic for transient failures

### **Performance Tips**

- **⚡ Async Operations**: Use async/await for concurrent API calls
- **💾 Caching**: Implement caching for frequently accessed data
- **🔄 Incremental Collection**: Use incremental collection for large datasets
- **📊 Monitoring**: Monitor API quotas and usage

## 🚀 **Next Steps**

After mastering multi-platform collection:

- **[Custom Analytics Dashboards](Custom-Analytics-Dashboard.md)** - Build interactive dashboards
- **[Data Quality Validation](Data-Quality-Validation.md)** - Implement data validation
- **[Automated Data Pipelines](Automated-Data-Pipelines.md)** - Create scheduled collections
- **[Real-time Monitoring](Real-time-Monitoring.md)** - Set up live data monitoring

## 🔗 **Related Recipes**

- **[Getting Started](Getting-Started.md)** - First steps with Siege Utilities
- **[Client Management](Client-Management.md)** - Manage client profiles and branding
- **[Report Generation](Report-Generation.md)** - Create professional reports from analytics data
- **[Data Export](Data-Export.md)** - Export data in various formats

---

<div align="center">

**Ready to integrate your analytics?** 📊

**[Next: Custom Analytics Dashboard](Custom-Analytics-Dashboard.md)** → **[Data Quality Validation](Data-Quality-Validation.md)**

</div>

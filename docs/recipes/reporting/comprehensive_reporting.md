# Comprehensive Reporting System

## Problem
You need to generate professional PDF reports and PowerPoint presentations from various data sources including Google Analytics, databases, and custom datasets. The reports should include client branding, charts, tables, and insights.

## Solution
Use the `siege_utilities.reporting` module to create comprehensive reports with:
- **BaseReportTemplate**: Foundation for PDF generation with branding
- **ChartGenerator**: Create charts using QuickChart.io
- **ClientBrandingManager**: Manage client-specific branding configurations
- **ReportGenerator**: Orchestrate complete report creation
- **AnalyticsReportGenerator**: Specialized for analytics data
- **PowerPointGenerator**: Create PowerPoint presentations

## Code Example

### 1. Basic Report Generation

```python
from siege_utilities.reporting import ReportGenerator

# Create a report generator for a client
report_gen = ReportGenerator('Siege Analytics')

# Sample analytics data
report_data = {
    'executive_summary': 'Q1 2024 showed strong performance with 15,000 users and 22,000 sessions.',
    'metrics': {
        'Total Users': {'value': '15,000', 'change': '+12.5%', 'status': 'excellent'},
        'Total Sessions': {'value': '22,000', 'change': '+15.2%', 'status': 'excellent'},
        'Bounce Rate': {'value': '45.2%', 'change': '-5.1%', 'status': 'good'}
    },
    'charts': [
        {
            'type': 'line',
            'title': 'Daily User Traffic',
            'data': {
                'labels': ['Mon', 'Tue', 'Wed', 'Thu', 'Fri'],
                'datasets': [{'label': 'Users', 'data': [500, 520, 480, 550, 600]}]
            }
        }
    ],
    'tables': [
        {
            'title': 'Top Pages',
            'headers': ['Page', 'Views', 'Bounce Rate'],
            'data': [
                ['/home', '5,000', '40%'],
                ['/products', '3,500', '35%']
            ]
        }
    ],
    'insights': [
        'User engagement increased by 12.5%',
        'Bounce rate decreased by 5.1%',
        'Pages per session increased by 12.0%'
    ]
}

# Generate PDF report
report_path = report_gen.create_analytics_report(
    report_data, 
    "Q1 2024 Performance Report"
)
print(f"Report generated: {report_path}")
```

### 2. Google Analytics Report

```python
from siege_utilities.reporting import AnalyticsReportGenerator

# Create analytics report generator
analytics_gen = AnalyticsReportGenerator('Siege Analytics')

# Google Analytics data
ga_data = {
    'total_users': 15000,
    'total_sessions': 22000,
    'avg_session_duration': 180.5,
    'bounce_rate': 45.2,
    'executive_summary': 'Strong performance with positive engagement trends.',
    'daily_traffic': {
        'dates': ['2024-01-01', '2024-01-02', '2024-01-03'],
        'users': [500, 520, 480]
    },
    'top_pages': [
        {'page': '/home', 'views': 5000, 'bounce_rate': 40},
        {'page': '/products', 'views': 3500, 'bounce_rate': 35}
    ]
}

# Generate Google Analytics report
report_path = analytics_gen.create_google_analytics_report(
    ga_data, 
    "Q1 2024 - January 2024"
)
```

### 3. PowerPoint Presentation

```python
from siege_utilities.reporting import PowerPointGenerator

# Create PowerPoint generator
ppt_gen = PowerPointGenerator('Siege Analytics')

# Generate PowerPoint from the same data
ppt_path = ppt_gen.create_analytics_presentation(
    report_data,
    "Q1 2024 Performance Review"
)
print(f"Presentation generated: {ppt_path}")
```

### 4. Custom Report Configuration

```python
# Create a custom report with specific sections
custom_config = {
    'title': 'Marketing Campaign Report',
    'subtitle': 'Q1 2024 Campaign Analysis',
    'page_size': 'letter',
    'sections': [
        {
            'type': 'text',
            'title': 'Campaign Overview',
            'content': 'Digital marketing campaign focused on brand awareness.'
        },
        {
            'type': 'chart',
            'title': 'Performance Metrics',
            'chart_config': {
                'type': 'bar',
                'data': {
                    'labels': ['Week 1', 'Week 2', 'Week 3', 'Week 4'],
                    'datasets': [
                        {'label': 'Impressions', 'data': [10000, 12000, 11000, 13000]},
                        {'label': 'Clicks', 'data': [500, 600, 550, 700]}
                    ]
                }
            },
            'caption': 'Weekly campaign performance'
        },
        {
            'type': 'table',
            'title': 'Results Summary',
            'headers': ['Metric', 'Target', 'Actual', 'Performance'],
            'data': [
                ['Impressions', '100,000', '115,000', '115%'],
                ['Clicks', '5,000', '5,800', '116%']
            ]
        }
    ]
}

# Generate custom report
custom_report_path = report_gen.create_custom_report(custom_config)
```

### 5. DataFrame Report

```python
import pandas as pd
import numpy as np

# Create sample DataFrame
df = pd.DataFrame({
    'Date': pd.date_range('2024-01-01', periods=30, freq='D'),
    'Users': np.random.randint(800, 1200, 30),
    'Sessions': np.random.randint(1200, 1800, 30),
    'Revenue': np.random.uniform(1000, 5000, 30)
})

# Generate report from DataFrame
df_report_path = analytics_gen.create_custom_analytics_report(
    'dataframe',
    df,
    {'title': 'Monthly Performance Analysis'}
)
```

### 6. Client Branding Management

```python
from siege_utilities.reporting import ClientBrandingManager

# Create branding manager
branding_manager = ClientBrandingManager()

# List available clients
clients = branding_manager.list_clients()
print(f"Available clients: {clients}")

# Get client branding
siege_branding = branding_manager.get_client_branding('siege_analytics')
print(f"Branding loaded: {bool(siege_branding)}")

# Create new client branding
new_client_config = {
    'name': 'Acme Corp',
    'colors': {
        'primary': '#FF6B35',
        'text_color': '#333333'
    },
    'fonts': {
        'default_font': 'Helvetica'
    }
}

# Create branding for new client
config_path = branding_manager.create_client_branding('Acme Corp', new_client_config)
```

### 7. Chart Generation

```python
from siege_utilities.reporting import ChartGenerator

# Create chart generator with branding
chart_gen = ChartGenerator(siege_branding)

# Create various chart types
labels = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun']
datasets = [
    {'label': 'Users', 'data': [1000, 1200, 1100, 1400, 1300, 1600]},
    {'label': 'Sessions', 'data': [1500, 1800, 1600, 2000, 1900, 2400]}
]

# Bar chart
bar_chart = chart_gen.create_bar_chart(labels, datasets, "Monthly Performance")

# Line chart
line_chart = chart_gen.create_line_chart(labels, datasets, "Trend Analysis")

# Pie chart
pie_chart = chart_gen.create_pie_chart(labels, [1000, 1200, 1100, 1400, 1300, 1600], "User Distribution")

# Dashboard with multiple charts
dashboard_charts = chart_gen.create_dashboard_chart([
    {'type': 'bar', 'labels': labels, 'datasets': datasets},
    {'type': 'line', 'labels': labels, 'datasets': datasets}
], layout="2x1")
```

## Expected Output

The system will generate:
- **PDF Reports**: Professional reports with client branding, charts, tables, and insights
- **PowerPoint Presentations**: Slide decks with the same content in presentation format
- **Charts**: Visualizations using QuickChart.io for web-based chart generation
- **Branded Content**: Consistent styling based on client configurations

## Notes

### Dependencies
- **ReportLab**: For PDF generation (included in base template)
- **python-pptx**: For PowerPoint generation (optional, install with `pip install python-pptx`)
- **PIL/Pillow**: For image processing (optional, for logo handling)
- **pandas**: For DataFrame processing (optional, for data analysis)

### File Structure
```
reports/                          # Generated PDF reports
├── siege_analytics_analytics_report_20241201_143022.pdf
├── siege_analytics_performance_report_20241201_143045.pdf
└── siege_analytics_custom_report_20241201_143100.pdf

presentations/                    # Generated PowerPoint files
├── siege_analytics_analytics_presentation_20241201_143022.pptx
└── siege_analytics_dataframe_presentation_20241201_143045.pptx

~/.siege_utilities/branding/     # Client branding configurations
├── siege_analytics/
│   └── siege_analytics_branding.yaml
└── acme_corp/
    └── acme_corp_branding.yaml
```

### Branding Configuration
Branding files use YAML format:
```yaml
name: "Client Name"
colors:
  primary: "#0077CC"
  text_color: "#333333"
fonts:
  default_font: "Helvetica"
logo:
  image_url: "https://example.com/logo.png"
  width: 1.5
  height: 0.6
```

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure all required packages are installed
   ```bash
   pip install reportlab python-pptx pillow pandas
   ```

2. **Chart Generation Fails**: Check internet connection for QuickChart.io
   - Charts are generated using web service
   - Offline fallback creates placeholder charts

3. **Branding Not Applied**: Verify branding configuration file exists
   - Check file paths and YAML syntax
   - Use `ClientBrandingManager.validate_branding_config()` to validate

4. **PowerPoint Generation Fails**: Install python-pptx package
   ```bash
   pip install python-pptx
   ```

### Performance Tips

- **Batch Processing**: Generate multiple reports in sequence
- **Chart Caching**: Charts are cached locally for reuse
- **Memory Management**: Large datasets are processed efficiently
- **Parallel Generation**: Use multiple instances for concurrent report generation

### Advanced Features

- **Custom Templates**: Extend BaseReportTemplate for specialized reports
- **Data Connectors**: Integrate with databases, APIs, and file systems
- **Automated Scheduling**: Set up recurring report generation
- **Email Distribution**: Automatically send reports to stakeholders
- **Version Control**: Track report versions and changes

## Related Functions

- `siege_utilities.analytics.google_analytics`: Google Analytics data retrieval
- `siege_utilities.analytics.facebook_business`: Facebook Business data
- `siege_utilities.distributed.spark_utils`: Spark DataFrame processing
- `siege_utilities.files.operations`: File handling and management

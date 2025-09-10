# 📊 Comprehensive Reporting System - PDF & PowerPoint Generation

<div align="center">

![Reporting](https://img.shields.io/badge/Reporting-PDF_%26_PowerPoint-blue)
![Branding](https://img.shields.io/badge/Branding-Client_Customization-green)
![Analytics](https://img.shields.io/badge/Analytics-Data_Visualization-orange)

**Generate professional reports with client branding, charts, tables, and insights** 🚀

</div>

---

## 🎯 **Problem**

You need to generate professional PDF reports and PowerPoint presentations from various data sources including Google Analytics, databases, and custom datasets. The reports should include client branding, charts, tables, and insights.

## 💡 **Solution**

Use the `siege_utilities.reporting` module to create comprehensive reports with:
- **BaseReportTemplate**: Foundation for PDF generation with branding
- **ChartGenerator**: Create charts using QuickChart.io
- **ClientBrandingManager**: Manage client-specific branding configurations
- **ReportGenerator**: Orchestrate complete report creation
- **AnalyticsReportGenerator**: Specialized for analytics data
- **PowerPointGenerator**: Create PowerPoint presentations

## 🚀 **Quick Start**

```python
from siege_utilities.reporting import ReportGenerator

# Create a report generator for a client
report_gen = ReportGenerator('Siege Analytics')

# Generate PDF report
report_path = report_gen.create_analytics_report(
    report_data, 
    "Q1 2024 Performance Report"
)
print(f"✅ Report generated: {report_path}")
```

## 📋 **Complete Implementation**

### **1. Basic Report Generation**

```python
from siege_utilities.reporting import ReportGenerator
import pandas as pd

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
print(f"✅ Report generated: {report_path}")
```

### **2. Google Analytics Report**

```python
from siege_utilities.reporting import AnalyticsReportGenerator
import pandas as pd

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
print(f"✅ Google Analytics report generated: {report_path}")
```

### **3. PowerPoint Presentation Generation**

```python
from siege_utilities.reporting import PowerPointGenerator

# Create PowerPoint generator
ppt_gen = PowerPointGenerator('Siege Analytics')

# Presentation data
presentation_data = {
    'title': 'Q1 2024 Performance Review',
    'subtitle': 'Key Metrics and Insights',
    'slides': [
        {
            'type': 'title',
            'title': 'Q1 2024 Performance Review',
            'subtitle': 'Key Metrics and Insights',
            'company': 'Siege Analytics'
        },
        {
            'type': 'executive_summary',
            'title': 'Executive Summary',
            'content': 'Strong Q1 performance with significant improvements in user engagement and conversion rates.',
            'key_metrics': [
                '15,000 total users (+12.5%)',
                '22,000 total sessions (+15.2%)',
                '45.2% bounce rate (-5.1%)'
            ]
        },
        {
            'type': 'chart',
            'title': 'Daily User Traffic',
            'chart_type': 'line',
            'data': {
                'labels': ['Mon', 'Tue', 'Wed', 'Thu', 'Fri'],
                'datasets': [{'label': 'Users', 'data': [500, 520, 480, 550, 600]}]
            }
        },
        {
            'type': 'table',
            'title': 'Top Performing Pages',
            'headers': ['Page', 'Views', 'Bounce Rate', 'Conversion'],
            'data': [
                ['/home', '5,000', '40%', '2.1%'],
                ['/products', '3,500', '35%', '3.2%'],
                ['/about', '2,800', '30%', '1.8%']
            ]
        },
        {
            'type': 'insights',
            'title': 'Key Insights',
            'insights': [
                'User engagement increased by 12.5%',
                'Bounce rate decreased by 5.1%',
                'Pages per session increased by 12.0%',
                'Mobile traffic grew by 18.3%'
            ]
        }
    ]
}

# Generate PowerPoint presentation
presentation_path = ppt_gen.create_presentation(presentation_data)
print(f"✅ PowerPoint presentation generated: {presentation_path}")
```

### **4. Advanced Report with Custom Branding**

```python
from siege_utilities.reporting import ReportGenerator, ClientBrandingManager
from siege_utilities.config.clients import create_client_profile

# Create client profile with custom branding
client_profile = create_client_profile(
    "Acme Corporation",
    "ACME001",
    {"primary_contact": "John Smith", "email": "john@acme.com"},
    brand_colors=["#0066CC", "#FF6600"],
    logo_path="/assets/logos/acme_logo.png"
)

# Create branded report generator
branded_gen = ReportGenerator('Acme Corporation', client_profile)

# Advanced report data with multiple sections
advanced_report_data = {
    'title': 'Acme Corporation - Q1 2024 Analytics Report',
    'executive_summary': {
        'overview': 'Q1 2024 demonstrated exceptional growth across all key metrics.',
        'highlights': [
            'User base expanded by 15,000 new users',
            'Revenue increased by 22.3%',
            'Customer satisfaction score: 4.8/5.0'
        ]
    },
    'performance_metrics': {
        'user_growth': {'current': 15000, 'previous': 13000, 'change': '+15.4%'},
        'revenue_growth': {'current': 125000, 'previous': 102000, 'change': '+22.3%'},
        'engagement_rate': {'current': 68.5, 'previous': 62.1, 'change': '+10.3%'}
    },
    'detailed_analysis': {
        'traffic_sources': [
            {'source': 'Organic Search', 'users': 8500, 'percentage': 56.7},
            {'source': 'Direct', 'users': 4200, 'percentage': 28.0},
            {'source': 'Social Media', 'users': 1800, 'percentage': 12.0},
            {'source': 'Referral', 'users': 500, 'percentage': 3.3}
        ],
        'geographic_distribution': [
            {'region': 'North America', 'users': 9000, 'percentage': 60.0},
            {'region': 'Europe', 'users': 4500, 'percentage': 30.0},
            {'region': 'Asia Pacific', 'users': 1500, 'percentage': 10.0}
        ]
    },
    'recommendations': [
        'Increase investment in organic search optimization',
        'Expand social media presence in European markets',
        'Develop mobile-first content strategy',
        'Implement A/B testing for conversion optimization'
    ]
}

# Generate comprehensive branded report
report_path = branded_gen.create_comprehensive_report(
    advanced_report_data,
    "Q1 2024 Comprehensive Analytics Report"
)
print(f"✅ Branded report generated: {report_path}")
```

### **5. Automated Report Generation Pipeline**

```python
from siege_utilities.reporting import ReportGenerator, AnalyticsReportGenerator
from siege_utilities.analytics.google_analytics import GoogleAnalytics
import schedule
import time
from datetime import datetime, timedelta

class AutomatedReportingPipeline:
    """Automated reporting pipeline for regular report generation"""
    
    def __init__(self, client_name, client_profile=None):
        self.client_name = client_name
        self.client_profile = client_profile
        self.report_gen = ReportGenerator(client_name, client_profile)
        self.analytics_gen = AnalyticsReportGenerator(client_name, client_profile)
        
    def collect_analytics_data(self, start_date, end_date):
        """Collect analytics data for the specified period"""
        try:
            # Initialize Google Analytics
            ga = GoogleAnalytics()
            
            # Collect data
            data = {
                'period': f"{start_date} to {end_date}",
                'total_users': ga.get_total_users(start_date, end_date),
                'total_sessions': ga.get_total_sessions(start_date, end_date),
                'avg_session_duration': ga.get_avg_session_duration(start_date, end_date),
                'bounce_rate': ga.get_bounce_rate(start_date, end_date),
                'daily_traffic': ga.get_daily_traffic(start_date, end_date),
                'top_pages': ga.get_top_pages(start_date, end_date, limit=10),
                'traffic_sources': ga.get_traffic_sources(start_date, end_date),
                'conversion_data': ga.get_conversion_data(start_date, end_date)
            }
            
            return data
            
        except Exception as e:
            print(f"❌ Error collecting analytics data: {e}")
            return None
    
    def generate_weekly_report(self):
        """Generate weekly report"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)
        
        print(f"📊 Generating weekly report for {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
        
        # Collect data
        data = self.collect_analytics_data(start_date, end_date)
        if not data:
            return
        
        # Generate report
        report_title = f"Weekly Report - {end_date.strftime('%Y-%m-%d')}"
        report_path = self.report_gen.create_analytics_report(data, report_title)
        
        print(f"✅ Weekly report generated: {report_path}")
    
    def generate_monthly_report(self):
        """Generate monthly report"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        
        print(f"📊 Generating monthly report for {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
        
        # Collect data
        data = self.collect_analytics_data(start_date, end_date)
        if not data:
            return
        
        # Generate comprehensive report
        report_title = f"Monthly Report - {end_date.strftime('%B %Y')}"
        report_path = self.report_gen.create_comprehensive_report(data, report_title)
        
        print(f"✅ Monthly report generated: {report_path}")
    
    def schedule_reports(self):
        """Schedule automated report generation"""
        # Schedule weekly reports (every Monday at 9 AM)
        schedule.every().monday.at("09:00").do(self.generate_weekly_report)
        
        # Schedule monthly reports (first day of month at 9 AM)
        schedule.every().month.at("09:00").do(self.generate_monthly_report)
        
        print("📅 Reports scheduled:")
        print("   📊 Weekly reports: Every Monday at 9:00 AM")
        print("   📊 Monthly reports: First day of month at 9:00 AM")
        
        # Keep the scheduler running
        while True:
            schedule.run_pending()
            time.sleep(60)

# Usage example
if __name__ == "__main__":
    # Create automated reporting pipeline
    pipeline = AutomatedReportingPipeline("Siege Analytics")
    
    # Generate immediate reports
    pipeline.generate_weekly_report()
    pipeline.generate_monthly_report()
    
    # Schedule automated reports
    pipeline.schedule_reports()
```

### **6. Report Customization and Templates**

```python
from siege_utilities.reporting import BaseReportTemplate, ChartGenerator
import json

class CustomReportTemplate(BaseReportTemplate):
    """Custom report template with specific styling and layout"""
    
    def __init__(self, client_name, branding_config=None):
        super().__init__(client_name, branding_config)
        self.chart_generator = ChartGenerator(branding_config)
    
    def create_custom_section(self, title, content, section_type="text"):
        """Create a custom section with specific formatting"""
        
        if section_type == "text":
            return self._create_text_section(title, content)
        elif section_type == "chart":
            return self._create_chart_section(title, content)
        elif section_type == "table":
            return self._create_table_section(title, content)
        elif section_type == "metrics":
            return self._create_metrics_section(title, content)
        else:
            return self._create_generic_section(title, content)
    
    def _create_metrics_section(self, title, metrics_data):
        """Create a metrics section with key performance indicators"""
        
        section = {
            'type': 'metrics',
            'title': title,
            'metrics': []
        }
        
        for metric_name, metric_data in metrics_data.items():
            metric = {
                'name': metric_name,
                'value': metric_data.get('value', 'N/A'),
                'change': metric_data.get('change', ''),
                'status': metric_data.get('status', 'neutral'),
                'description': metric_data.get('description', '')
            }
            section['metrics'].append(metric)
        
        return section
    
    def _create_chart_section(self, title, chart_data):
        """Create a chart section with custom styling"""
        
        # Generate chart using ChartGenerator
        chart_url = self.chart_generator.create_chart(
            chart_type=chart_data.get('type', 'line'),
            data=chart_data.get('data', {}),
            options=chart_data.get('options', {})
        )
        
        section = {
            'type': 'chart',
            'title': title,
            'chart_url': chart_url,
            'description': chart_data.get('description', ''),
            'insights': chart_data.get('insights', [])
        }
        
        return section

# Usage example
custom_template = CustomReportTemplate("Acme Corporation")

# Create custom metrics section
metrics_data = {
    'User Growth': {
        'value': '15,000',
        'change': '+12.5%',
        'status': 'positive',
        'description': 'Total users this quarter'
    },
    'Revenue': {
        'value': '$125,000',
        'change': '+22.3%',
        'status': 'excellent',
        'description': 'Total revenue generated'
    }
}

metrics_section = custom_template.create_custom_section(
    "Key Performance Indicators",
    metrics_data,
    "metrics"
)

print(f"✅ Custom metrics section created: {metrics_section}")
```

## 📊 **Expected Output**

### **PDF Report Structure**
```
📄 Acme Corporation - Q1 2024 Analytics Report
├── 🏢 Title Page (with logo and branding)
├── 📋 Table of Contents
├── 📊 Executive Summary
│   ├── Overview
│   └── Key Highlights
├── 📈 Performance Metrics
│   ├── User Growth: 15,000 (+15.4%)
│   ├── Revenue: $125,000 (+22.3%)
│   └── Engagement: 68.5% (+10.3%)
├── 🗺️ Detailed Analysis
│   ├── Traffic Sources Chart
│   └── Geographic Distribution
├── 💡 Key Insights
├── 🎯 Recommendations
└── 📚 Appendices
```

### **PowerPoint Presentation Structure**
```
🎯 Q1 2024 Performance Review
├── 🏢 Title Slide
├── 📋 Executive Summary
├── 📊 Daily User Traffic Chart
├── 📋 Top Performing Pages Table
├── 💡 Key Insights
└── 🚀 Next Steps
```

## 🔧 **Configuration Options**

### **Client Branding Configuration**
```yaml
# client_branding.yaml
client_name: "Acme Corporation"
brand_colors:
  primary: "#0066CC"
  secondary: "#FF6600"
  accent: "#00CC66"
logo_path: "/assets/logos/acme_logo.png"
font_family: "Arial"
header_style: "modern"
footer_style: "professional"
```

### **Report Template Configuration**
```yaml
# report_template.yaml
sections:
  - title: "Executive Summary"
    type: "summary"
    required: true
  - title: "Performance Metrics"
    type: "metrics"
    required: true
  - title: "Detailed Analysis"
    type: "analysis"
    required: false
  - title: "Recommendations"
    type: "recommendations"
    required: true

styling:
  page_size: "A4"
  margins: "1 inch"
  header_height: "0.5 inch"
  footer_height: "0.5 inch"
```

## 🚨 **Troubleshooting**

### **Common Issues**

1. **📊 Chart Generation Failed**: Check QuickChart.io API access and data format
2. **🎨 Branding Not Applied**: Verify client profile and branding configuration
3. **📄 PDF Generation Error**: Check file permissions and ReportLab installation
4. **📊 Data Format Issues**: Ensure data follows expected schema

### **Performance Tips**

- **⚡ Batch Processing**: Generate multiple reports in batch
- **💾 Caching**: Cache frequently used charts and templates
- **🔄 Incremental Updates**: Only regenerate changed sections
- **📊 Data Optimization**: Pre-process data before report generation

### **Best Practices**

- **📋 Templates**: Use consistent templates for similar reports
- **🎨 Branding**: Maintain consistent client branding across all materials
- **📊 Data Validation**: Validate data before report generation
- **📁 Organization**: Organize reports with clear naming conventions
- **🔄 Automation**: Automate regular report generation

## 🚀 **Next Steps**

After mastering comprehensive reporting:

- **[Client Management](Examples/Client-Management.md)** - Set up client profiles and branding
- **[Analytics Integration](Recipes/Analytics-Integration.md)** - Connect data sources
- **[Automation Guide](Recipes/Automation-Guide.md)** - Automate report workflows
- **[Performance Optimization](Recipes/Performance-Optimization.md)** - Optimize report generation

## 🔗 **Related Recipes**

- **[Basic Setup](Recipes/Basic-Setup.md)** - Install and configure Siege Utilities
- **[Client Management](Examples/Client-Management.md)** - Manage client profiles
- **[Analytics Integration](Recipes/Analytics-Integration.md)** - Connect data sources
- **[Batch Processing](Recipes/Batch-Processing.md)** - Process multiple reports

---

<div align="center">

**Ready to create professional reports?** 📊

**[Next: Analytics Integration](Recipes/Analytics-Integration.md)** → **[Client Management](Examples/Client-Management.md)**

</div>

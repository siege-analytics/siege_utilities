# Comprehensive Reporting System - PDF & PowerPoint Generation

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

## Quick Start

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

## Complete Implementation

### 1. Basic Report Generation

#### Setup Report Generator
```python
import siege_utilities
from siege_utilities.reporting import ReportGenerator
from siege_utilities.reporting.client_branding import ClientBrandingManager
from pathlib import Path

# Initialize logging
siege_utilities.log_info("Starting comprehensive reporting system")

# Setup client branding
branding_manager = ClientBrandingManager()
branding_config = branding_manager.get_client_branding('Acme Corporation')

# Initialize report generator
report_gen = ReportGenerator(
    client_name='Acme Corporation',
    branding_config=branding_config,
    output_directory='reports'
)

print(f"✅ Report generator initialized for {branding_config['client_name']}")
print(f"🎨 Branding colors: {branding_config['primary_color']}, {branding_config['secondary_color']}")
```

#### Create Simple PDF Report
```python
def create_basic_report():
    """Create a basic PDF report with minimal content."""
    
    try:
        # Sample data for the report
        report_data = {
            'title': 'Monthly Performance Summary',
            'period': 'January 2024',
            'metrics': {
                'total_revenue': 125000,
                'total_customers': 1250,
                'conversion_rate': 0.045,
                'avg_order_value': 100.00
            },
            'summary': 'Strong performance in January with revenue growth of 15% over December.'
        }
        
        # Create basic report
        report_path = report_gen.create_basic_report(
            title=report_data['title'],
            content={
                'period': report_data['period'],
                'summary': report_data['summary'],
                'metrics': report_data['metrics']
            },
            include_toc=True,
            include_page_numbers=True
        )
        
        print(f"✅ Basic report created: {report_path}")
        return report_path
        
    except Exception as e:
        print(f"❌ Error creating basic report: {e}")
        siege_utilities.log_error(f"Basic report creation failed: {e}")
        return None

# Create basic report
basic_report_path = create_basic_report()
```

### 2. Google Analytics Report Generation

#### Analytics Data Integration
```python
def create_analytics_report():
    """Create a comprehensive analytics report with Google Analytics data."""
    
    try:
        # Sample Google Analytics data
        analytics_data = {
            'pageviews': 45000,
            'unique_visitors': 12500,
            'bounce_rate': 0.42,
            'avg_session_duration': 180,
            'top_pages': [
                {'page': '/home', 'views': 8500, 'bounce_rate': 0.38},
                {'page': '/products', 'views': 7200, 'bounce_rate': 0.35},
                {'page': '/about', 'views': 6800, 'bounce_rate': 0.45},
                {'page': '/contact', 'views': 5200, 'bounce_rate': 0.28}
            ],
            'traffic_sources': [
                {'source': 'Organic Search', 'sessions': 18000, 'conversion_rate': 0.052},
                {'source': 'Direct', 'sessions': 12000, 'conversion_rate': 0.048},
                {'source': 'Social Media', 'sessions': 8000, 'conversion_rate': 0.038},
                {'source': 'Referral', 'sessions': 7000, 'conversion_rate': 0.042}
            ]
        }
        
        # Create charts for the report
        charts = []
        
        # Page performance chart
        from siege_utilities.reporting.chart_generator import ChartGenerator
        chart_gen = ChartGenerator(branding_config)
        
        page_chart = chart_gen.create_bar_chart(
            data=analytics_data['top_pages'],
            x_column='page',
            y_column='views',
            title='Top Performing Pages',
            color_scheme='brand'
        )
        charts.append(page_chart)
        
        # Traffic source chart
        traffic_chart = chart_gen.create_pie_chart(
            data=analytics_data['traffic_sources'],
            values_column='sessions',
            labels_column='source',
            title='Traffic Sources Distribution'
        )
        charts.append(traffic_chart)
        
        # Create comprehensive analytics report
        report_path = report_gen.create_analytics_report(
            title="Q1 2024 Website Analytics Report",
            charts=charts,
            data_summary=f"Comprehensive analysis of website performance for {analytics_data['unique_visitors']:,} unique visitors",
            insights=[
                "Homepage shows strong engagement with low bounce rate",
                "Product pages drive significant traffic and conversions",
                "Organic search remains the primary traffic source",
                "Social media shows potential for growth optimization"
            ],
            recommendations=[
                "Optimize product page content for better conversion rates",
                "Increase social media marketing efforts",
                "Improve about page content to reduce bounce rate",
                "Implement A/B testing for contact page optimization"
            ],
            additional_sections={
                'executive_summary': True,
                'methodology': True,
                'appendix': True,
                'contact_info': True
            }
        )
        
        print(f"✅ Analytics report created: {report_path}")
        return report_path
        
    except Exception as e:
        print(f"❌ Error creating analytics report: {e}")
        siege_utilities.log_error(f"Analytics report creation failed: {e}")
        return None

# Create analytics report
analytics_report_path = create_analytics_report()
```

### 3. PowerPoint Generation

#### Create Professional Presentations
```python
from siege_utilities.reporting import PowerPointGenerator

def create_powerpoint_presentation():
    """Create a comprehensive PowerPoint presentation."""
    
    try:
        # Initialize PowerPoint generator
        ppt_gen = PowerPointGenerator(
            client_name='Acme Corporation',
            branding_config=branding_config,
            template_path='templates/presentation_template.pptx'
        )
        
        # Create presentation structure
        presentation_structure = {
            'title_slide': {
                'title': 'Q1 2024 Performance Review',
                'subtitle': 'Acme Corporation',
                'date': 'February 2024',
                'presenter': 'Marketing Team'
            },
            'agenda': [
                'Executive Summary',
                'Key Performance Metrics',
                'Market Analysis',
                'Strategic Recommendations',
                'Next Steps'
            ],
            'content_slides': [
                {
                    'type': 'metrics_overview',
                    'title': 'Key Performance Metrics',
                    'content': {
                        'revenue': '$125,000',
                        'customers': '1,250',
                        'growth_rate': '15%',
                        'conversion_rate': '4.5%'
                    }
                },
                {
                    'type': 'chart_slide',
                    'title': 'Revenue Trend Analysis',
                    'chart_data': analytics_data['top_pages'],
                    'chart_type': 'line'
                },
                {
                    'type': 'comparison',
                    'title': 'Q4 vs Q1 Performance',
                    'content': {
                        'q4_revenue': '$108,000',
                        'q1_revenue': '$125,000',
                        'q4_customers': '1080',
                        'q1_customers': '1250'
                    }
                }
            ],
            'conclusion': {
                'title': 'Strategic Recommendations',
                'points': [
                    'Focus on high-converting traffic sources',
                    'Optimize product page performance',
                    'Expand social media presence',
                    'Implement conversion rate optimization'
                ]
            }
        }
        
        # Generate PowerPoint presentation
        ppt_path = ppt_gen.create_presentation(
            structure=presentation_structure,
            include_speaker_notes=True,
            include_branding=True,
            output_format='pptx'
        )
        
        print(f"✅ PowerPoint presentation created: {ppt_path}")
        return ppt_path
        
    except Exception as e:
        print(f"❌ Error creating PowerPoint: {e}")
        siege_utilities.log_error(f"PowerPoint creation failed: {e}")
        return None

# Create PowerPoint presentation
powerpoint_path = create_powerpoint_presentation()
```

### 4. Advanced Reports with Custom Branding

#### Custom Branding Integration
```python
def create_custom_branded_report():
    """Create a report with custom branding and styling."""
    
    try:
        # Custom branding configuration
        custom_branding = {
            'client_name': 'TechStart Inc.',
            'primary_color': '#2E86AB',
            'secondary_color': '#A23B72',
            'accent_color': '#F18F01',
            'logo_path': 'assets/techstart_logo.png',
            'font_family': 'Arial',
            'header_style': 'modern',
            'footer_text': 'TechStart Inc. - Confidential Report'
        }
        
        # Create custom report generator
        custom_report_gen = ReportGenerator(
            client_name=custom_branding['client_name'],
            branding_config=custom_branding,
            template_config={
                'page_size': 'A4',
                'margins': {'top': 1, 'bottom': 1, 'left': 1, 'right': 1},
                'header_height': 0.5,
                'footer_height': 0.5,
                'include_page_numbers': True,
                'include_watermark': False
            }
        )
        
        # Sample data for custom report
        custom_data = {
            'title': 'Technology Market Analysis Report',
            'sections': [
                {
                    'title': 'Market Overview',
                    'content': 'Analysis of current technology market trends and opportunities.',
                    'charts': [],
                    'tables': []
                },
                {
                    'title': 'Competitive Analysis',
                    'content': 'Detailed comparison of key competitors in the market.',
                    'charts': [],
                    'tables': []
                },
                {
                    'title': 'Growth Projections',
                    'content': 'Forecasted market growth and revenue projections.',
                    'charts': [],
                    'tables': []
                }
            ]
        }
        
        # Create custom branded report
        custom_report_path = custom_report_gen.create_custom_report(
            title=custom_data['title'],
            sections=custom_data['sections'],
            branding_config=custom_branding,
            include_executive_summary=True,
            include_table_of_contents=True,
            include_appendix=True
        )
        
        print(f"✅ Custom branded report created: {custom_report_path}")
        return custom_report_path
        
    except Exception as e:
        print(f"❌ Error creating custom report: {e}")
        siege_utilities.log_error(f"Custom report creation failed: {e}")
        return None

# Create custom branded report
custom_report_path = create_custom_branded_report()
```

### 5. Automated Report Pipeline

#### Scheduled Report Generation
```python
import schedule
import time
from datetime import datetime, timedelta

def create_automated_report_pipeline():
    """Create an automated pipeline for regular report generation."""
    
    try:
        # Define report schedule
        report_schedule = {
            'daily': {
                'time': '09:00',
                'type': 'daily_summary',
                'recipients': ['team@acme.com']
            },
            'weekly': {
                'time': 'Monday 10:00',
                'type': 'weekly_analysis',
                'recipients': ['management@acme.com', 'team@acme.com']
            },
            'monthly': {
                'time': '1st 14:00',
                'type': 'monthly_comprehensive',
                'recipients': ['stakeholders@acme.com', 'management@acme.com']
            }
        }
        
        def generate_daily_report():
            """Generate daily performance summary."""
            print(f"📊 Generating daily report for {datetime.now().strftime('%Y-%m-%d')}")
            
            # Get daily data
            daily_data = get_daily_analytics_data()
            
            # Create daily report
            daily_report = report_gen.create_daily_summary(
                data=daily_data,
                date=datetime.now().date(),
                include_charts=True,
                include_comparisons=True
            )
            
            # Send report
            send_report_via_email(daily_report, report_schedule['daily']['recipients'])
            print("✅ Daily report generated and sent")
        
        def generate_weekly_report():
            """Generate weekly comprehensive analysis."""
            print(f"📊 Generating weekly report for week of {datetime.now().strftime('%Y-%m-%d')}")
            
            # Get weekly data
            weekly_data = get_weekly_analytics_data()
            
            # Create weekly report
            weekly_report = report_gen.create_weekly_analysis(
                data=weekly_data,
                week_start=datetime.now().date() - timedelta(days=7),
                include_trends=True,
                include_forecasts=True
            )
            
            # Send report
            send_report_via_email(weekly_report, report_schedule['weekly']['recipients'])
            print("✅ Weekly report generated and sent")
        
        def generate_monthly_report():
            """Generate monthly comprehensive report."""
            print(f"📊 Generating monthly report for {datetime.now().strftime('%B %Y')}")
            
            # Get monthly data
            monthly_data = get_monthly_analytics_data()
            
            # Create monthly report
            monthly_report = report_gen.create_monthly_comprehensive(
                data=monthly_data,
                month=datetime.now().month,
                year=datetime.now().year,
                include_executive_summary=True,
                include_strategic_recommendations=True
            )
            
            # Send report
            send_report_via_email(monthly_report, report_schedule['monthly']['recipients'])
            print("✅ Monthly report generated and sent")
        
        # Schedule reports
        schedule.every().day.at(report_schedule['daily']['time']).do(generate_daily_report)
        schedule.every().monday.at(report_schedule['weekly']['time'].split()[1]).do(generate_weekly_report)
        schedule.every().month.at(report_schedule['monthly']['time'].split()[1]).do(generate_monthly_report)
        
        print("📅 Report pipeline scheduled successfully")
        print(f"  Daily: {report_schedule['daily']['time']}")
        print(f"  Weekly: {report_schedule['weekly']['time']}")
        print(f"  Monthly: {report_schedule['monthly']['time']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error setting up automated pipeline: {e}")
        return False

def get_daily_analytics_data():
    """Get daily analytics data for reports."""
    # This would typically connect to your analytics platform
    return {
        'date': datetime.now().date(),
        'pageviews': 1500,
        'unique_visitors': 450,
        'conversions': 12,
        'revenue': 2500
    }

def get_weekly_analytics_data():
    """Get weekly analytics data for reports."""
    return {
        'week_start': datetime.now().date() - timedelta(days=7),
        'total_pageviews': 10500,
        'total_visitors': 3150,
        'total_conversions': 84,
        'total_revenue': 17500
    }

def get_monthly_analytics_data():
    """Get monthly analytics data for reports."""
    return {
        'month': datetime.now().month,
        'year': datetime.now().year,
        'total_pageviews': 45000,
        'total_visitors': 12500,
        'total_conversions': 360,
        'total_revenue': 75000
    }

def send_report_via_email(report_path, recipients):
    """Send report via email to recipients."""
    try:
        # This would integrate with your email system
        print(f"📧 Sending report to: {', '.join(recipients)}")
        # email_service.send_report(report_path, recipients)
        print("✅ Report sent successfully")
    except Exception as e:
        print(f"❌ Error sending report: {e}")

# Setup automated pipeline
pipeline_success = create_automated_report_pipeline()
```

### 6. Customization and Templates

#### Advanced Template Configuration
```python
def create_custom_report_template():
    """Create a custom report template with advanced styling."""
    
    try:
        # Custom template configuration
        template_config = {
            'page_layout': {
                'size': 'A4',
                'orientation': 'portrait',
                'margins': {'top': 0.75, 'bottom': 0.75, 'left': 0.75, 'right': 0.75},
                'header_height': 0.5,
                'footer_height': 0.5
            },
            'styling': {
                'font_family': 'Helvetica',
                'title_font_size': 18,
                'heading_font_size': 14,
                'body_font_size': 11,
                'line_spacing': 1.2,
                'paragraph_spacing': 0.2
            },
            'sections': {
                'title_page': {
                    'include_logo': True,
                    'include_date': True,
                    'include_author': True,
                    'background_color': '#f8f9fa'
                },
                'table_of_contents': {
                    'include_page_numbers': True,
                    'max_depth': 3,
                    'style': 'modern'
                },
                'content_pages': {
                    'include_headers': True,
                    'include_footers': True,
                    'page_numbers': 'bottom_center',
                    'watermark': None
                }
            },
            'branding': {
                'primary_color': '#2E86AB',
                'secondary_color': '#A23B72',
                'accent_color': '#F18F01',
                'header_background': '#2E86AB',
                'header_text_color': '#ffffff',
                'footer_background': '#f8f9fa',
                'footer_text_color': '#6c757d'
            }
        }
        
        # Create template
        template_path = report_gen.create_custom_template(
            template_config=template_config,
            save_template=True,
            template_name='modern_business_template'
        )
        
        print(f"✅ Custom template created: {template_path}")
        return template_path
        
    except Exception as e:
        print(f"❌ Error creating custom template: {e}")
        return None

# Create custom template
template_path = create_custom_report_template()
```

## Expected Output

```
✅ Report generator initialized for Acme Corporation
🎨 Branding colors: #2E86AB, #A23B72

✅ Basic report created: reports/basic_report_20240813.pdf
✅ Analytics report created: reports/analytics_report_20240813.pdf
✅ PowerPoint presentation created: presentations/q1_performance_20240813.pptx
✅ Custom branded report created: reports/custom_report_20240813.pdf

📅 Report pipeline scheduled successfully
  Daily: 09:00
  Weekly: Monday 10:00
  Monthly: 1st 14:00

✅ Custom template created: templates/modern_business_template.yaml
```

## Configuration Options

### Report Configuration
```yaml
reporting:
  default_format: PDF
  output_directory: "reports"
  include_branding: true
  include_page_numbers: true
  include_table_of_contents: true
  template_directory: "templates"
  branding_directory: "branding"
  email_notifications: true
  storage_retention_days: 365
```

### PowerPoint Configuration
```yaml
powerpoint:
  default_template: "business_template.pptx"
  include_speaker_notes: true
  include_branding: true
  slide_transitions: true
  animation_effects: false
  output_format: "pptx"
  quality: "high"
```

## Troubleshooting

### Common Issues

1. **Template Loading Errors**
   - Verify template file paths
   - Check template format compatibility
   - Ensure template files are not corrupted

2. **Branding Integration Issues**
   - Verify logo file paths and formats
   - Check color code validity
   - Ensure branding configuration is complete

3. **Chart Generation Problems**
   - Verify data format and structure
   - Check chart generator dependencies
   - Ensure data columns match expected names

### Performance Tips

```python
# For large reports, use streaming generation
def generate_large_report(data, chunk_size=1000):
    """Generate large reports efficiently using streaming."""
    
    report_sections = []
    
    for i in range(0, len(data), chunk_size):
        chunk = data.iloc[i:i+chunk_size]
        
        # Process chunk
        section = process_report_section(chunk)
        report_sections.append(section)
        
        # Clear memory
        del chunk
    
    # Combine sections
    return combine_report_sections(report_sections)
```

## Next Steps

After mastering comprehensive reporting:

- **Advanced Analytics**: Integrate with more data sources
- **Custom Templates**: Create industry-specific templates
- **Automation**: Set up fully automated reporting pipelines
- **Integration**: Connect with business intelligence tools

## Related Recipes

- **[Analytics Integration](Analytics-Integration)** - Connect data sources for reports
- **[Bivariate Choropleth Maps](Bivariate-Choropleth-Maps)** - Add geographic visualizations
- **[Client Management](Examples/Client-Management)** - Apply client branding to reports
- **[Basic Setup](Basic-Setup)** - Configure Siege Utilities for reporting

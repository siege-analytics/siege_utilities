#!/usr/bin/env python3
"""
Test script for the new siege_utilities reporting system.
Demonstrates PDF and PowerPoint generation with various data sources.
"""

import sys
import os
from pathlib import Path
import pandas as pd
from datetime import datetime, timedelta
import numpy as np

# Add the current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

def test_basic_reporting():
    """Test basic reporting functionality."""
    print("🧪 Testing Basic Reporting System...")
    
    try:
        from siege_utilities.reporting import (
            BaseReportTemplate, ReportGenerator, ChartGenerator, 
            ClientBrandingManager, AnalyticsReportGenerator, PowerPointGenerator
        )
        print("✅ All reporting modules imported successfully")
        
        # Test client branding manager
        print("\n📋 Testing Client Branding Manager...")
        branding_manager = ClientBrandingManager()
        
        # List available clients
        clients = branding_manager.list_clients()
        print(f"Available clients: {clients}")
        
        # Get Siege Analytics branding
        siege_branding = branding_manager.get_client_branding('siege_analytics')
        print(f"Siege Analytics branding loaded: {bool(siege_branding)}")
        
        # Test chart generator
        print("\n📊 Testing Chart Generator...")
        chart_gen = ChartGenerator(siege_branding)
        
        # Create sample data
        labels = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun']
        datasets = [
            {'label': 'Users', 'data': [1000, 1200, 1100, 1400, 1300, 1600]},
            {'label': 'Sessions', 'data': [1500, 1800, 1600, 2000, 1900, 2400]}
        ]
        
        # Create charts
        bar_chart = chart_gen.create_bar_chart(labels, datasets, "Monthly Performance")
        line_chart = chart_gen.create_line_chart(labels, datasets, "Trend Analysis")
        pie_chart = chart_gen.create_pie_chart(labels, [1000, 1200, 1100, 1400, 1300, 1600], "User Distribution")
        
        print(f"✅ Created {bar_chart}, {line_chart}, {pie_chart}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error in basic reporting test: {e}")
        return False

def test_analytics_reports():
    """Test analytics report generation."""
    print("\n📈 Testing Analytics Report Generation...")
    
    try:
        from siege_utilities.reporting import AnalyticsReportGenerator
        
        # Create sample Google Analytics data
        ga_data = {
            'total_users': 15000,
            'total_sessions': 22000,
            'avg_session_duration': 180.5,
            'bounce_rate': 45.2,
            'avg_pages_per_session': 3.8,
            'users_change': 12.5,
            'sessions_change': 15.2,
            'duration_change': 8.3,
            'bounce_change': -5.1,
            'pages_change': 12.0,
            'executive_summary': 'Strong performance with 15,000 users and 22,000 sessions. Engagement metrics show positive trends.',
            'daily_traffic': {
                'dates': ['2024-01-01', '2024-01-02', '2024-01-03', '2024-01-04', '2024-01-05'],
                'users': [500, 520, 480, 550, 600]
            },
            'top_pages': [
                {'page': '/home', 'views': 5000, 'unique_views': 4500, 'avg_time': 120, 'bounce_rate': 40},
                {'page': '/products', 'views': 3500, 'unique_views': 3200, 'avg_time': 180, 'bounce_rate': 35},
                {'page': '/about', 'views': 2000, 'unique_views': 1900, 'avg_time': 90, 'bounce_rate': 50}
            ],
            'traffic_sources': [
                {'source': 'Organic Search', 'sessions': 12000, 'users': 10000, 'bounce_rate': 42, 'avg_session_duration': 200},
                {'source': 'Direct', 'sessions': 6000, 'users': 5000, 'bounce_rate': 48, 'avg_session_duration': 150},
                {'source': 'Social', 'sessions': 4000, 'users': 3000, 'bounce_rate': 55, 'avg_session_duration': 120}
            ]
        }
        
        # Create analytics report generator
        analytics_gen = AnalyticsReportGenerator('Siege Analytics')
        
        # Generate Google Analytics report
        report_path = analytics_gen.create_google_analytics_report(
            ga_data, 
            "Q1 2024 - January 2024",
            "Q1 2024 Website Performance Report"
        )
        
        print(f"✅ Generated Google Analytics report: {report_path}")
        
        # Test custom analytics report with DataFrame
        print("\n📊 Testing DataFrame Report Generation...")
        
        # Create sample DataFrame
        df = pd.DataFrame({
            'Date': pd.date_range('2024-01-01', periods=30, freq='D'),
            'Users': np.random.randint(800, 1200, 30),
            'Sessions': np.random.randint(1200, 1800, 30),
            'Revenue': np.random.uniform(1000, 5000, 30),
            'Conversion_Rate': np.random.uniform(2.0, 5.0, 30)
        })
        
        # Generate DataFrame report
        df_report_path = analytics_gen.create_custom_analytics_report(
            'dataframe',
            df,
            {'title': 'Monthly Performance Data Analysis'}
        )
        
        print(f"✅ Generated DataFrame report: {df_report_path}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error in analytics reports test: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_powerpoint_generation():
    """Test PowerPoint presentation generation."""
    print("\n📊 Testing PowerPoint Generation...")
    
    try:
        from siege_utilities.reporting import PowerPointGenerator
        
        # Create PowerPoint generator
        ppt_gen = PowerPointGenerator('Siege Analytics')
        
        # Create sample report data
        report_data = {
            'executive_summary': 'This presentation provides an overview of our Q1 2024 performance metrics and key insights.',
            'metrics': {
                'Total Users': {'value': '15,000', 'change': '+12.5%', 'status': 'excellent'},
                'Total Sessions': {'value': '22,000', 'change': '+15.2%', 'status': 'excellent'},
                'Avg Session Duration': {'value': '3.0 min', 'change': '+8.3%', 'status': 'good'},
                'Bounce Rate': {'value': '45.2%', 'change': '-5.1%', 'status': 'good'},
                'Pages per Session': {'value': '3.8', 'change': '+12.0%', 'status': 'excellent'}
            },
            'charts': [
                {
                    'type': 'line',
                    'title': 'Daily User Traffic',
                    'data': {
                        'labels': ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
                        'datasets': [{'label': 'Users', 'data': [500, 520, 480, 550, 600, 580, 520]}]
                    }
                }
            ],
            'tables': [
                {
                    'title': 'Top Performing Pages',
                    'headers': ['Page', 'Views', 'Unique Views', 'Avg Time', 'Bounce Rate'],
                    'data': [
                        ['/home', '5,000', '4,500', '2.0 min', '40%'],
                        ['/products', '3,500', '3,200', '3.0 min', '35%'],
                        ['/about', '2,000', '1,900', '1.5 min', '50%']
                    ]
                }
            ],
            'insights': [
                'User engagement increased by 12.5% compared to previous quarter',
                'Bounce rate decreased by 5.1%, indicating improved content quality',
                'Pages per session increased by 12.0%, showing better user journey',
                'Direct traffic shows highest engagement with 3.0 min average session duration'
            ]
        }
        
        # Generate PowerPoint presentation
        ppt_path = ppt_gen.create_analytics_presentation(
            report_data,
            "Q1 2024 Performance Review"
        )
        
        print(f"✅ Generated PowerPoint presentation: {ppt_path}")
        
        # Test DataFrame presentation
        print("\n📊 Testing DataFrame PowerPoint Generation...")
        
        # Create sample DataFrame
        df = pd.DataFrame({
            'Metric': ['Users', 'Sessions', 'Revenue', 'Conversion Rate'],
            'Q1 2024': [15000, 22000, 45000, 3.2],
            'Q4 2023': [13333, 19111, 40000, 2.9],
            'Change %': [12.5, 15.2, 12.5, 10.3]
        })
        
        # Generate DataFrame presentation
        df_ppt_path = ppt_gen.create_presentation_from_dataframe(
            df,
            "Q1 2024 vs Q4 2023 Performance Comparison"
        )
        
        print(f"✅ Generated DataFrame PowerPoint: {df_ppt_path}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error in PowerPoint generation test: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_custom_reports():
    """Test custom report generation."""
    print("\n🎨 Testing Custom Report Generation...")
    
    try:
        from siege_utilities.reporting import ReportGenerator
        
        # Create report generator
        report_gen = ReportGenerator('Siege Analytics')
        
        # Create custom report configuration
        custom_config = {
            'title': 'Custom Marketing Campaign Report',
            'subtitle': 'Q1 2024 Campaign Performance Analysis',
            'page_size': 'letter',
            'sections': [
                {
                    'type': 'text',
                    'title': 'Campaign Overview',
                    'content': 'This campaign focused on increasing brand awareness and driving user engagement through targeted digital marketing efforts.'
                },
                {
                    'type': 'chart',
                    'title': 'Campaign Performance Metrics',
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
                    'caption': 'Weekly campaign performance showing impressions and clicks'
                },
                {
                    'type': 'table',
                    'title': 'Campaign Results Summary',
                    'headers': ['Metric', 'Target', 'Actual', 'Performance'],
                    'data': [
                        ['Impressions', '100,000', '115,000', '115%'],
                        ['Clicks', '5,000', '5,800', '116%'],
                        ['CTR', '5.0%', '5.0%', '100%'],
                        ['Conversions', '250', '290', '116%']
                    ]
                }
            ]
        }
        
        # Generate custom report
        custom_report_path = report_gen.create_custom_report(custom_config)
        
        print(f"✅ Generated custom report: {custom_report_path}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error in custom report test: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_performance_reports():
    """Test performance report generation."""
    print("\n⚡ Testing Performance Report Generation...")
    
    try:
        from siege_utilities.reporting import ReportGenerator
        
        # Create report generator
        report_gen = ReportGenerator('Siege Analytics')
        
        # Create performance data
        performance_data = {
            'overview': 'Q1 2024 showed strong performance across all key metrics with significant improvements in user engagement and conversion rates.',
            'users': {
                'current': 15000,
                'target': 14000,
                'performance': '107%'
            },
            'sessions': {
                'current': 22000,
                'target': 20000,
                'performance': '110%'
            },
            'revenue': {
                'current': 45000,
                'target': 40000,
                'performance': '112.5%'
            },
            'conversion_rate': {
                'current': 3.2,
                'target': 3.0,
                'performance': '107%'
            },
            'trends': {
                'User Growth': {
                    'labels': ['Jan', 'Feb', 'Mar'],
                    'data': [10000, 12500, 15000]
                },
                'Revenue Growth': {
                    'labels': ['Jan', 'Feb', 'Mar'],
                    'data': [30000, 37500, 45000]
                }
            },
            'recommendations': [
                'Continue optimizing landing pages to maintain high conversion rates',
                'Scale successful campaigns based on Q1 performance data',
                'Focus on user retention strategies to maximize lifetime value',
                'Invest in content marketing to support organic growth'
            ]
        }
        
        # Define metrics to include
        metrics = ['users', 'sessions', 'revenue', 'conversion_rate']
        
        # Generate performance report
        perf_report_path = report_gen.create_performance_report(
            performance_data,
            metrics,
            "Q1 2024 Performance Metrics Report"
        )
        
        print(f"✅ Generated performance report: {perf_report_path}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error in performance report test: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all reporting system tests."""
    print("🚀 Testing Siege Utilities Reporting System")
    print("=" * 50)
    
    # Track test results
    test_results = []
    
    # Run tests
    test_results.append(("Basic Reporting", test_basic_reporting()))
    test_results.append(("Analytics Reports", test_analytics_reports()))
    test_results.append(("PowerPoint Generation", test_powerpoint_generation()))
    test_results.append(("Custom Reports", test_custom_reports()))
    test_results.append(("Performance Reports", test_performance_reports()))
    
    # Print results summary
    print("\n" + "=" * 50)
    print("📊 TEST RESULTS SUMMARY")
    print("=" * 50)
    
    passed = 0
    total = len(test_results)
    
    for test_name, result in test_results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Reporting system is working correctly.")
        return 0
    else:
        print("⚠️  Some tests failed. Check the output above for details.")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)

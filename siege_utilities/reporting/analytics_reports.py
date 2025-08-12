"""
Analytics reports module for siege_utilities reporting system.
Integrates with Google Analytics, databases, and other data sources.
"""

import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
from datetime import datetime, timedelta
import pandas as pd

from .report_generator import ReportGenerator
from .chart_generator import ChartGenerator

log = logging.getLogger(__name__)

class AnalyticsReportGenerator:
    """
    Generates analytics reports from various data sources.
    Integrates with Google Analytics, databases, and Spark dataframes.
    """

    def __init__(self, client_name: str, output_dir: Optional[Path] = None):
        """
        Initialize the analytics report generator.
        
        Args:
            client_name: Name of the client for branding
            output_dir: Directory for output reports
        """
        self.client_name = client_name
        self.output_dir = output_dir or Path.cwd() / "reports"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize components
        self.report_generator = ReportGenerator(client_name, output_dir)
        self.chart_generator = ChartGenerator()

    def create_google_analytics_report(self, ga_data: Dict[str, Any], 
                                     date_range: str = "",
                                     report_title: str = "") -> Path:
        """
        Create a Google Analytics report.
        
        Args:
            ga_data: Google Analytics data dictionary
            date_range: Date range for the report
            report_title: Custom title for the report
            
        Returns:
            Path to the generated PDF report
        """
        try:
            # Prepare report data
            report_data = self._prepare_ga_report_data(ga_data, date_range)
            
            # Generate report
            report_path = self.report_generator.create_analytics_report(
                report_data, report_title
            )
            
            log.info(f"Google Analytics report created: {report_path}")
            return report_path
            
        except Exception as e:
            log.error(f"Error creating Google Analytics report: {e}")
            raise

    def create_website_performance_report(self, performance_data: Dict[str, Any],
                                        metrics: List[str],
                                        report_title: str = "") -> Path:
        """
        Create a website performance report.
        
        Args:
            performance_data: Website performance data
            metrics: List of performance metrics to include
            report_title: Custom title for the report
            
        Returns:
            Path to the generated PDF report
        """
        try:
            # Generate report
            report_path = self.report_generator.create_performance_report(
                performance_data, metrics, report_title
            )
            
            log.info(f"Website performance report created: {report_path}")
            return report_path
            
        except Exception as e:
            log.error(f"Error creating website performance report: {e}")
            raise

    def create_custom_analytics_report(self, data_source: str,
                                     data: Union[pd.DataFrame, Dict[str, Any]],
                                     report_config: Dict[str, Any]) -> Path:
        """
        Create a custom analytics report from various data sources.
        
        Args:
            data_source: Type of data source ('dataframe', 'dict', 'json', 'csv')
            data: The actual data
            report_config: Report configuration
            
        Returns:
            Path to the generated PDF report
        """
        try:
            # Process data based on source type
            if data_source == 'dataframe':
                processed_data = self._process_dataframe_data(data, report_config)
            elif data_source == 'dict':
                processed_data = self._process_dict_data(data, report_config)
            elif data_source == 'json':
                processed_data = self._process_json_data(data, report_config)
            elif data_source == 'csv':
                processed_data = self._process_csv_data(data, report_config)
            else:
                raise ValueError(f"Unsupported data source: {data_source}")
            
            # Generate custom report
            report_path = self.report_generator.create_custom_report(processed_data)
            
            log.info(f"Custom analytics report created: {report_path}")
            return report_path
            
        except Exception as e:
            log.error(f"Error creating custom analytics report: {e}")
            raise

    def create_monthly_analytics_report(self, monthly_data: Dict[str, Any],
                                      year: int,
                                      month: int) -> Path:
        """
        Create a monthly analytics report.
        
        Args:
            monthly_data: Monthly analytics data
            year: Year for the report
            month: Month for the report
            
        Returns:
            Path to the generated PDF report
        """
        try:
            # Prepare monthly report data
            report_data = self._prepare_monthly_report_data(monthly_data, year, month)
            
            # Generate report
            report_path = self.report_generator.create_analytics_report(
                report_data, f"Monthly Analytics Report - {year}-{month:02d}"
            )
            
            log.info(f"Monthly analytics report created: {report_path}")
            return report_path
            
        except Exception as e:
            log.error(f"Error creating monthly analytics report: {e}")
            raise

    def create_quarterly_analytics_report(self, quarterly_data: Dict[str, Any],
                                        year: int,
                                        quarter: int) -> Path:
        """
        Create a quarterly analytics report.
        
        Args:
            quarterly_data: Quarterly analytics data
            year: Year for the report
            quarter: Quarter for the report (1-4)
            
        Returns:
            Path to the generated PDF report
        """
        try:
            # Prepare quarterly report data
            report_data = self._prepare_quarterly_report_data(quarterly_data, year, quarter)
            
            # Generate report
            report_path = self.report_generator.create_analytics_report(
                report_data, f"Q{quarter} {year} Analytics Report"
            )
            
            log.info(f"Quarterly analytics report created: {report_path}")
            return report_path
            
        except Exception as e:
            log.error(f"Error creating quarterly analytics report: {e}")
            raise

    def create_campaign_performance_report(self, campaign_data: Dict[str, Any],
                                         campaign_name: str,
                                         date_range: str = "") -> Path:
        """
        Create a campaign performance report.
        
        Args:
            campaign_data: Campaign performance data
            campaign_name: Name of the campaign
            date_range: Date range for the campaign
            
        Returns:
            Path to the generated PDF report
        """
        try:
            # Prepare campaign report data
            report_data = self._prepare_campaign_report_data(campaign_data, campaign_name, date_range)
            
            # Generate report
            report_path = self.report_generator.create_analytics_report(
                report_data, f"Campaign Performance: {campaign_name}"
            )
            
            log.info(f"Campaign performance report created: {report_path}")
            return report_path
            
        except Exception as e:
            log.error(f"Error creating campaign performance report: {e}")
            raise

    def _prepare_ga_report_data(self, ga_data: Dict[str, Any], 
                               date_range: str) -> Dict[str, Any]:
        """Prepare Google Analytics data for reporting."""
        report_data = {
            'executive_summary': self._generate_ga_executive_summary(ga_data, date_range),
            'metrics': self._extract_ga_metrics(ga_data),
            'charts': self._create_ga_charts(ga_data),
            'tables': self._create_ga_tables(ga_data),
            'insights': self._generate_ga_insights(ga_data)
        }
        
        return report_data

    def _prepare_monthly_report_data(self, monthly_data: Dict[str, Any],
                                   year: int, month: int) -> Dict[str, Any]:
        """Prepare monthly report data."""
        month_name = datetime(year, month, 1).strftime('%B')
        
        report_data = {
            'executive_summary': f"Monthly analytics report for {month_name} {year} showing key performance indicators and trends.",
            'metrics': self._extract_monthly_metrics(monthly_data),
            'charts': self._create_monthly_charts(monthly_data, year, month),
            'tables': self._create_monthly_tables(monthly_data),
            'insights': self._generate_monthly_insights(monthly_data)
        }
        
        return report_data

    def _prepare_quarterly_report_data(self, quarterly_data: Dict[str, Any],
                                     year: int, quarter: int) -> Dict[str, Any]:
        """Prepare quarterly report data."""
        quarter_names = ['Q1 (Jan-Mar)', 'Q2 (Apr-Jun)', 'Q3 (Jul-Sep)', 'Q4 (Oct-Dec)']
        quarter_name = quarter_names[quarter - 1]
        
        report_data = {
            'executive_summary': f"Quarterly analytics report for {quarter_name} {year} showing performance trends and key insights.",
            'metrics': self._extract_quarterly_metrics(quarterly_data),
            'charts': self._create_quarterly_charts(quarterly_data, year, quarter),
            'tables': self._create_quarterly_tables(quarterly_data),
            'insights': self._generate_quarterly_insights(quarterly_data)
        }
        
        return report_data

    def _prepare_campaign_report_data(self, campaign_data: Dict[str, Any],
                                    campaign_name: str,
                                    date_range: str) -> Dict[str, Any]:
        """Prepare campaign report data."""
        report_data = {
            'executive_summary': f"Campaign performance report for '{campaign_name}' covering {date_range}.",
            'metrics': self._extract_campaign_metrics(campaign_data),
            'charts': self._create_campaign_charts(campaign_data),
            'tables': self._create_campaign_tables(campaign_data),
            'insights': self._generate_campaign_insights(campaign_data)
        }
        
        return report_data

    def _generate_ga_executive_summary(self, ga_data: Dict[str, Any], 
                                     date_range: str) -> str:
        """Generate executive summary for Google Analytics data."""
        try:
            # Extract key metrics
            total_users = ga_data.get('total_users', 0)
            total_sessions = ga_data.get('total_sessions', 0)
            avg_session_duration = ga_data.get('avg_session_duration', 0)
            bounce_rate = ga_data.get('bounce_rate', 0)
            
            summary = f"""
            This report provides a comprehensive analysis of website performance for {date_range}. 
            Key highlights include {total_users:,} total users with {total_sessions:,} sessions. 
            The average session duration was {avg_session_duration:.1f} seconds, and the bounce rate was {bounce_rate:.1f}%.
            """
            
            return summary.strip()
            
        except Exception as e:
            log.error(f"Error generating GA executive summary: {e}")
            return "Executive summary could not be generated due to data processing errors."

    def _extract_ga_metrics(self, ga_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract key metrics from Google Analytics data."""
        metrics = {}
        
        # User metrics
        if 'total_users' in ga_data:
            metrics['Total Users'] = {
                'value': f"{ga_data['total_users']:,}",
                'change': ga_data.get('users_change', 'N/A'),
                'status': self._get_metric_status(ga_data.get('users_change', 0))
            }
        
        # Session metrics
        if 'total_sessions' in ga_data:
            metrics['Total Sessions'] = {
                'value': f"{ga_data['total_sessions']:,}",
                'change': ga_data.get('sessions_change', 'N/A'),
                'status': self._get_metric_status(ga_data.get('sessions_change', 0))
            }
        
        # Engagement metrics
        if 'avg_session_duration' in ga_data:
            metrics['Avg Session Duration'] = {
                'value': f"{ga_data['avg_session_duration']:.1f}s",
                'change': ga_data.get('duration_change', 'N/A'),
                'status': self._get_metric_status(ga_data.get('duration_change', 0))
            }
        
        if 'bounce_rate' in ga_data:
            metrics['Bounce Rate'] = {
                'value': f"{ga_data['bounce_rate']:.1f}%",
                'change': ga_data.get('bounce_change', 'N/A'),
                'status': self._get_metric_status(-ga_data.get('bounce_change', 0))  # Lower is better
            }
        
        # Page metrics
        if 'avg_pages_per_session' in ga_data:
            metrics['Pages per Session'] = {
                'value': f"{ga_data['avg_pages_per_session']:.1f}",
                'change': ga_data.get('pages_change', 'N/A'),
                'status': self._get_metric_status(ga_data.get('pages_change', 0))
            }
        
        return metrics

    def _create_ga_charts(self, ga_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create charts for Google Analytics data."""
        charts = []
        
        # Traffic over time
        if 'daily_traffic' in ga_data:
            daily_data = ga_data['daily_traffic']
            charts.append({
                'type': 'line',
                'title': 'Daily Website Traffic',
                'data': {
                    'labels': daily_data.get('dates', []),
                    'datasets': [{
                        'label': 'Users',
                        'data': daily_data.get('users', [])
                    }]
                }
            })
        
        # Page performance
        if 'top_pages' in ga_data:
            top_pages = ga_data['top_pages']
            charts.append({
                'type': 'bar',
                'title': 'Top Performing Pages',
                'data': {
                    'labels': [page.get('page', 'Unknown') for page in top_pages[:10]],
                    'datasets': [{
                        'label': 'Page Views',
                        'data': [page.get('views', 0) for page in top_pages[:10]]
                    }]
                }
            })
        
        # Traffic sources
        if 'traffic_sources' in ga_data:
            sources = ga_data['traffic_sources']
            charts.append({
                'type': 'pie',
                'title': 'Traffic Sources',
                'data': {
                    'labels': [source.get('source', 'Unknown') for source in sources],
                    'data': [source.get('sessions', 0) for source in sources]
                }
            })
        
        return charts

    def _create_ga_tables(self, ga_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create tables for Google Analytics data."""
        tables = []
        
        # Top pages table
        if 'top_pages' in ga_data:
            top_pages = ga_data['top_pages']
            table_data = []
            for page in top_pages[:20]:  # Top 20 pages
                table_data.append([
                    page.get('page', 'Unknown'),
                    f"{page.get('views', 0):,}",
                    f"{page.get('unique_views', 0):,}",
                    f"{page.get('avg_time', 0):.1f}s",
                    f"{page.get('bounce_rate', 0):.1f}%"
                ])
            
            tables.append({
                'title': 'Top Pages by Page Views',
                'headers': ['Page', 'Page Views', 'Unique Views', 'Avg Time', 'Bounce Rate'],
                'data': table_data
            })
        
        # Traffic sources table
        if 'traffic_sources' in ga_data:
            sources = ga_data['traffic_sources']
            table_data = []
            for source in sources:
                table_data.append([
                    source.get('source', 'Unknown'),
                    f"{source.get('sessions', 0):,}",
                    f"{source.get('users', 0):,}",
                    f"{source.get('bounce_rate', 0):.1f}%",
                    f"{source.get('avg_session_duration', 0):.1f}s"
                ])
            
            tables.append({
                'title': 'Traffic Sources Performance',
                'headers': ['Source', 'Sessions', 'Users', 'Bounce Rate', 'Avg Duration'],
                'data': table_data
            })
        
        return tables

    def _generate_ga_insights(self, ga_data: Dict[str, Any]) -> List[str]:
        """Generate insights from Google Analytics data."""
        insights = []
        
        # Traffic insights
        if 'total_users' in ga_data and 'total_sessions' in ga_data:
            users = ga_data['total_users']
            sessions = ga_data['total_sessions']
            if sessions > users:
                insights.append(f"High engagement: {sessions/users:.1f} sessions per user on average")
            elif sessions < users:
                insights.append(f"Low engagement: Only {sessions/users:.1f} sessions per user on average")
        
        # Bounce rate insights
        if 'bounce_rate' in ga_data:
            bounce_rate = ga_data['bounce_rate']
            if bounce_rate < 30:
                insights.append(f"Excellent bounce rate of {bounce_rate:.1f}% indicates strong user engagement")
            elif bounce_rate > 70:
                insights.append(f"High bounce rate of {bounce_rate:.1f}% suggests need for content optimization")
        
        # Page performance insights
        if 'top_pages' in ga_data:
            top_pages = ga_data['top_pages']
            if top_pages:
                best_page = top_pages[0]
                insights.append(f"'{best_page.get('page', 'Unknown')}' is the top performing page with {best_page.get('views', 0):,} views")
        
        # Traffic source insights
        if 'traffic_sources' in ga_data:
            sources = ga_data['traffic_sources']
            if sources:
                top_source = sources[0]
                insights.append(f"'{top_source.get('source', 'Unknown')}' is the primary traffic source, contributing {top_source.get('sessions', 0):,} sessions")
        
        return insights

    def _extract_monthly_metrics(self, monthly_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract metrics for monthly reports."""
        metrics = {}
        
        # Basic metrics
        for key, value in monthly_data.items():
            if isinstance(value, (int, float)):
                if 'change' in key.lower():
                    metrics[key.replace('_', ' ').title()] = {
                        'value': f"{value:+.1f}%",
                        'change': 'N/A',
                        'status': self._get_metric_status(value)
                    }
                else:
                    metrics[key.replace('_', ' ').title()] = {
                        'value': f"{value:,}",
                        'change': 'N/A',
                        'status': 'stable'
                    }
        
        return metrics

    def _create_monthly_charts(self, monthly_data: Dict[str, Any],
                             year: int, month: int) -> List[Dict[str, Any]]:
        """Create charts for monthly reports."""
        charts = []
        
        # Monthly trend chart
        if 'daily_data' in monthly_data:
            daily_data = monthly_data['daily_data']
            charts.append({
                'type': 'line',
                'title': f'Daily Performance - {datetime(year, month, 1).strftime("%B %Y")}',
                'data': {
                    'labels': daily_data.get('dates', []),
                    'datasets': [{
                        'label': 'Daily Metric',
                        'data': daily_data.get('values', [])
                    }]
                }
            })
        
        return charts

    def _create_monthly_tables(self, monthly_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create tables for monthly reports."""
        tables = []
        
        # Summary table
        if 'summary' in monthly_data:
            summary = monthly_data['summary']
            table_data = []
            for key, value in summary.items():
                if isinstance(value, (int, float)):
                    table_data.append([key.replace('_', ' ').title(), f"{value:,}"])
            
            tables.append({
                'title': 'Monthly Summary',
                'headers': ['Metric', 'Value'],
                'data': table_data
            })
        
        return tables

    def _generate_monthly_insights(self, monthly_data: Dict[str, Any]) -> List[str]:
        """Generate insights for monthly reports."""
        insights = []
        
        # Performance insights
        if 'performance_score' in monthly_data:
            score = monthly_data['performance_score']
            if score > 80:
                insights.append(f"Excellent monthly performance score of {score}/100")
            elif score < 50:
                insights.append(f"Monthly performance score of {score}/100 indicates need for improvement")
        
        # Growth insights
        if 'growth_rate' in monthly_data:
            growth = monthly_data['growth_rate']
            if growth > 0:
                insights.append(f"Positive growth of {growth:.1f}% this month")
            else:
                insights.append(f"Decline of {abs(growth):.1f}% this month requires attention")
        
        return insights

    def _extract_quarterly_metrics(self, quarterly_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract metrics for quarterly reports."""
        metrics = {}
        
        # Basic metrics
        for key, value in quarterly_data.items():
            if isinstance(value, (int, float)):
                if 'change' in key.lower():
                    metrics[key.replace('_', ' ').title()] = {
                        'value': f"{value:+.1f}%",
                        'change': 'N/A',
                        'status': self._get_metric_status(value)
                    }
                else:
                    metrics[key.replace('_', ' ').title()] = {
                        'value': f"{value:,}",
                        'change': 'N/A',
                        'status': 'stable'
                    }
        
        return metrics

    def _create_quarterly_charts(self, quarterly_data: Dict[str, Any],
                               year: int, quarter: int) -> List[Dict[str, Any]]:
        """Create charts for quarterly reports."""
        charts = []
        
        # Quarterly trend chart
        if 'monthly_data' in quarterly_data:
            monthly_data = quarterly_data['monthly_data']
            charts.append({
                'type': 'line',
                'title': f'Q{quarter} {year} Monthly Trends',
                'data': {
                    'labels': monthly_data.get('months', []),
                    'datasets': [{
                        'label': 'Monthly Metric',
                        'data': monthly_data.get('values', [])
                    }]
                }
            })
        
        return charts

    def _create_quarterly_tables(self, quarterly_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create tables for quarterly reports."""
        tables = []
        
        # Summary table
        if 'summary' in quarterly_data:
            summary = quarterly_data['summary']
            table_data = []
            for key, value in summary.items():
                if isinstance(value, (int, float)):
                    table_data.append([key.replace('_', ' ').title(), f"{value:,}"])
            
            tables.append({
                'title': 'Quarterly Summary',
                'headers': ['Metric', 'Value'],
                'data': table_data
            })
        
        return tables

    def _generate_quarterly_insights(self, quarterly_data: Dict[str, Any]) -> List[str]:
        """Generate insights for quarterly reports."""
        insights = []
        
        # Performance insights
        if 'performance_score' in quarterly_data:
            score = quarterly_data['performance_score']
            if score > 80:
                insights.append(f"Strong quarterly performance score of {score}/100")
            elif score < 50:
                insights.append(f"Quarterly performance score of {score}/100 needs improvement")
        
        # Growth insights
        if 'growth_rate' in quarterly_data:
            growth = quarterly_data['growth_rate']
            if growth > 0:
                insights.append(f"Quarterly growth of {growth:.1f}% shows positive momentum")
            else:
                insights.append(f"Quarterly decline of {abs(growth):.1f}% requires strategic review")
        
        return insights

    def _extract_campaign_metrics(self, campaign_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract metrics for campaign reports."""
        metrics = {}
        
        # Basic campaign metrics
        if 'impressions' in campaign_data:
            metrics['Impressions'] = {
                'value': f"{campaign_data['impressions']:,}",
                'change': campaign_data.get('impressions_change', 'N/A'),
                'status': self._get_metric_status(campaign_data.get('impressions_change', 0))
            }
        
        if 'clicks' in campaign_data:
            metrics['Clicks'] = {
                'value': f"{campaign_data['clicks']:,}",
                'change': campaign_data.get('clicks_change', 'N/A'),
                'status': self._get_metric_status(campaign_data.get('clicks_change', 0))
            }
        
        if 'ctr' in campaign_data:
            metrics['Click-Through Rate'] = {
                'value': f"{campaign_data['ctr']:.2f}%",
                'change': campaign_data.get('ctr_change', 'N/A'),
                'status': self._get_metric_status(campaign_data.get('ctr_change', 0))
            }
        
        if 'conversions' in campaign_data:
            metrics['Conversions'] = {
                'value': f"{campaign_data['conversions']:,}",
                'change': campaign_data.get('conversions_change', 'N/A'),
                'status': self._get_metric_status(campaign_data.get('conversions_change', 0))
            }
        
        return metrics

    def _create_campaign_charts(self, campaign_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create charts for campaign reports."""
        charts = []
        
        # Performance over time
        if 'daily_performance' in campaign_data:
            daily_data = campaign_data['daily_performance']
            charts.append({
                'type': 'line',
                'title': 'Campaign Performance Over Time',
                'data': {
                    'labels': daily_data.get('dates', []),
                    'datasets': [{
                        'label': 'Impressions',
                        'data': daily_data.get('impressions', [])
                    }, {
                        'label': 'Clicks',
                        'data': daily_data.get('clicks', [])
                    }]
                }
            })
        
        return charts

    def _create_campaign_tables(self, campaign_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create tables for campaign reports."""
        tables = []
        
        # Performance summary
        if 'performance_summary' in campaign_data:
            summary = campaign_data['performance_summary']
            table_data = []
            for key, value in summary.items():
                if isinstance(value, (int, float)):
                    table_data.append([key.replace('_', ' ').title(), f"{value:,}"])
            
            tables.append({
                'title': 'Campaign Performance Summary',
                'headers': ['Metric', 'Value'],
                'data': table_data
            })
        
        return tables

    def _generate_campaign_insights(self, campaign_data: Dict[str, Any]) -> List[str]:
        """Generate insights for campaign reports."""
        insights = []
        
        # CTR insights
        if 'ctr' in campaign_data:
            ctr = campaign_data['ctr']
            if ctr > 2.0:
                insights.append(f"Excellent click-through rate of {ctr:.2f}%")
            elif ctr < 0.5:
                insights.append(f"Low click-through rate of {ctr:.2f}% suggests need for creative optimization")
        
        # Conversion insights
        if 'conversions' in campaign_data and 'clicks' in campaign_data:
            conversions = campaign_data['conversions']
            clicks = campaign_data['clicks']
            if clicks > 0:
                conv_rate = (conversions / clicks) * 100
                if conv_rate > 5.0:
                    insights.append(f"Strong conversion rate of {conv_rate:.1f}%")
                elif conv_rate < 1.0:
                    insights.append(f"Low conversion rate of {conv_rate:.1f}% indicates need for landing page optimization")
        
        return insights

    def _process_dataframe_data(self, df: pd.DataFrame, 
                               report_config: Dict[str, Any]) -> Dict[str, Any]:
        """Process pandas DataFrame data for reporting."""
        try:
            # Extract basic statistics
            numeric_cols = df.select_dtypes(include=['number']).columns
            summary_stats = df[numeric_cols].describe()
            
            # Create charts
            charts = []
            for col in numeric_cols[:5]:  # Limit to 5 columns
                if df[col].nunique() > 1:
                    charts.append({
                        'type': 'bar',
                        'title': f'{col} Distribution',
                        'data': {
                            'labels': df[col].value_counts().head(10).index.astype(str).tolist(),
                            'datasets': [{
                                'label': col,
                                'data': df[col].value_counts().head(10).values.tolist()
                            }]
                        }
                    })
            
            # Create tables
            tables = []
            if not df.empty:
                # Sample data table
                sample_data = df.head(20).values.tolist()
                tables.append({
                    'title': 'Sample Data',
                    'headers': df.columns.tolist(),
                    'data': sample_data
                })
                
                # Summary statistics table
                summary_data = []
                for col in numeric_cols:
                    summary_data.append([
                        col,
                        f"{df[col].mean():.2f}",
                        f"{df[col].std():.2f}",
                        f"{df[col].min():.2f}",
                        f"{df[col].max():.2f}"
                    ])
                
                tables.append({
                    'title': 'Summary Statistics',
                    'headers': ['Column', 'Mean', 'Std', 'Min', 'Max'],
                    'data': summary_data
                })
            
            return {
                'title': report_config.get('title', 'DataFrame Analysis Report'),
                'subtitle': f"Generated from {len(df)} rows and {len(df.columns)} columns",
                'sections': [
                    {
                        'type': 'text',
                        'title': 'Data Overview',
                        'content': f"This report analyzes a dataset with {len(df)} rows and {len(df.columns)} columns. The data includes {len(numeric_cols)} numeric columns suitable for statistical analysis."
                    },
                    {
                        'type': 'chart',
                        'title': 'Data Distribution Charts',
                        'chart_config': charts[0] if charts else {},
                        'caption': 'Distribution of key numeric variables'
                    },
                    {
                        'type': 'table',
                        'title': 'Summary Statistics',
                        'headers': ['Column', 'Mean', 'Std', 'Min', 'Max'],
                        'data': summary_data if 'summary_data' in locals() else []
                    }
                ]
            }
            
        except Exception as e:
            log.error(f"Error processing DataFrame data: {e}")
            return {
                'title': 'DataFrame Analysis Report',
                'subtitle': 'Error processing data',
                'sections': [{
                    'type': 'text',
                    'title': 'Error',
                    'content': f'Error processing DataFrame: {str(e)}'
                }]
            }

    def _process_dict_data(self, data: Dict[str, Any], 
                          report_config: Dict[str, Any]) -> Dict[str, Any]:
        """Process dictionary data for reporting."""
        try:
            sections = []
            
            # Process each key-value pair
            for key, value in data.items():
                if isinstance(value, (int, float)):
                    sections.append({
                        'type': 'text',
                        'title': key.replace('_', ' ').title(),
                        'content': f"Value: {value:,}" if isinstance(value, int) else f"Value: {value:.2f}"
                    })
                elif isinstance(value, list) and len(value) > 0:
                    if isinstance(value[0], (int, float)):
                        # Create chart for numeric list
                        sections.append({
                            'type': 'chart',
                            'title': f'{key.replace("_", " ").title()} Chart',
                            'chart_config': {
                                'type': 'bar',
                                'data': {
                                    'labels': [f'Item {i+1}' for i in range(len(value))],
                                    'datasets': [{'label': key, 'data': value}]
                                }
                            },
                            'caption': f'Chart showing {key} values'
                        })
                    else:
                        # Create table for list of other types
                        sections.append({
                            'type': 'table',
                            'title': f'{key.replace("_", " ").title()} Data',
                            'headers': ['Index', 'Value'],
                            'data': [[i, str(v)] for i, v in enumerate(value)]
                        })
                elif isinstance(value, dict):
                    # Recursively process nested dictionaries
                    nested_sections = self._process_dict_data(value, {})
                    sections.extend(nested_sections.get('sections', []))
            
            return {
                'title': report_config.get('title', 'Dictionary Analysis Report'),
                'subtitle': f"Generated from dictionary with {len(data)} keys",
                'sections': sections
            }
            
        except Exception as e:
            log.error(f"Error processing dictionary data: {e}")
            return {
                'title': 'Dictionary Analysis Report',
                'subtitle': 'Error processing data',
                'sections': [{
                    'type': 'text',
                    'title': 'Error',
                    'content': f'Error processing dictionary: {str(e)}'
                }]
            }

    def _process_json_data(self, json_data: str, 
                          report_config: Dict[str, Any]) -> Dict[str, Any]:
        """Process JSON data for reporting."""
        try:
            import json
            data = json.loads(json_data)
            return self._process_dict_data(data, report_config)
        except Exception as e:
            log.error(f"Error processing JSON data: {e}")
            return {
                'title': 'JSON Analysis Report',
                'subtitle': 'Error processing data',
                'sections': [{
                    'type': 'text',
                    'title': 'Error',
                    'content': f'Error processing JSON: {str(e)}'
                }]
            }

    def _process_csv_data(self, csv_path: str, 
                         report_config: Dict[str, Any]) -> Dict[str, Any]:
        """Process CSV data for reporting."""
        try:
            df = pd.read_csv(csv_path)
            return self._process_dataframe_data(df, report_config)
        except Exception as e:
            log.error(f"Error processing CSV data: {e}")
            return {
                'title': 'CSV Analysis Report',
                'subtitle': 'Error processing data',
                'sections': [{
                    'type': 'text',
                    'title': 'Error',
                    'content': f'Error processing CSV: {str(e)}'
                }]
            }

    def _get_metric_status(self, change_value: float) -> str:
        """Get status for a metric based on change value."""
        if change_value > 5:
            return 'excellent'
        elif change_value > 0:
            return 'good'
        elif change_value > -5:
            return 'stable'
        else:
            return 'needs_attention'

"""
Enhanced Google Analytics Report Example

This example demonstrates a comprehensive GA4 report with:
1. KPI Dashboard with metric cards
2. Period-over-period comparison
3. Traffic source analysis
4. Geographic visualization
5. Page performance tables
6. Funnel visualization
7. Insights and recommendations

Requirements:
- siege_utilities with reporting extras
- Google Analytics credentials (service account or OAuth)
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
import logging
import io
import tempfile

# ReportLab imports
try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter, landscape
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
        PageBreak, Image as RLImage, KeepTogether, Flowable
    )
    from reportlab.graphics.shapes import Drawing, Rect, String, Line
    from reportlab.graphics.charts.lineplots import LinePlot
    from reportlab.graphics.charts.barcharts import VerticalBarChart
    from reportlab.graphics.charts.piecharts import Pie
    from reportlab.graphics.widgets.markers import makeMarker
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

# Matplotlib for additional charts
try:
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False

# siege_utilities imports
from siege_utilities.reporting.chart_generator import ChartGenerator
from siege_utilities.reporting.report_generator import ReportGenerator

log = logging.getLogger(__name__)


class KPICard(Flowable):
    """A custom flowable for displaying KPI metrics in a card format."""

    def __init__(self, title: str, value: str, change: float = None,
                 change_label: str = "vs prior period", width: float = 2*inch,
                 height: float = 1.2*inch, primary_color: tuple = (0.2, 0.4, 0.8)):
        Flowable.__init__(self)
        self.title = title
        self.value = value
        self.change = change
        self.change_label = change_label
        self.width = width
        self.height = height
        self.primary_color = primary_color

    def draw(self):
        """Draw the KPI card."""
        # Background
        self.canv.setFillColorRGB(0.97, 0.97, 0.97)
        self.canv.roundRect(0, 0, self.width, self.height, 5, fill=1, stroke=0)

        # Top accent bar
        self.canv.setFillColorRGB(*self.primary_color)
        self.canv.rect(0, self.height - 4, self.width, 4, fill=1, stroke=0)

        # Title
        self.canv.setFillColorRGB(0.4, 0.4, 0.4)
        self.canv.setFont("Helvetica", 9)
        self.canv.drawString(10, self.height - 20, self.title)

        # Value
        self.canv.setFillColorRGB(0.1, 0.1, 0.1)
        self.canv.setFont("Helvetica-Bold", 20)
        self.canv.drawString(10, self.height - 50, self.value)

        # Change indicator
        if self.change is not None:
            if self.change >= 0:
                self.canv.setFillColorRGB(0.2, 0.7, 0.3)
                arrow = "\u25B2"  # Up arrow
                change_text = f"{arrow} {self.change:+.1f}%"
            else:
                self.canv.setFillColorRGB(0.8, 0.2, 0.2)
                arrow = "\u25BC"  # Down arrow
                change_text = f"{arrow} {abs(self.change):.1f}%"

            self.canv.setFont("Helvetica", 10)
            self.canv.drawString(10, self.height - 70, change_text)

            self.canv.setFillColorRGB(0.5, 0.5, 0.5)
            self.canv.setFont("Helvetica", 8)
            self.canv.drawString(10, self.height - 85, self.change_label)


class SparklineChart(Flowable):
    """A compact sparkline chart for inline trends."""

    def __init__(self, data: List[float], width: float = 1.5*inch,
                 height: float = 0.4*inch, color: tuple = (0.2, 0.4, 0.8)):
        Flowable.__init__(self)
        self.data = data
        self.width = width
        self.height = height
        self.color = color

    def draw(self):
        """Draw the sparkline."""
        if not self.data or len(self.data) < 2:
            return

        # Normalize data to fit
        min_val = min(self.data)
        max_val = max(self.data)
        range_val = max_val - min_val if max_val != min_val else 1

        normalized = [(v - min_val) / range_val for v in self.data]

        # Calculate points
        x_step = self.width / (len(self.data) - 1)
        points = [(i * x_step, v * self.height * 0.8 + self.height * 0.1)
                  for i, v in enumerate(normalized)]

        # Draw line
        self.canv.setStrokeColorRGB(*self.color)
        self.canv.setLineWidth(1.5)

        path = self.canv.beginPath()
        path.moveTo(points[0][0], points[0][1])
        for x, y in points[1:]:
            path.lineTo(x, y)
        self.canv.drawPath(path, stroke=1, fill=0)

        # Draw end point
        self.canv.setFillColorRGB(*self.color)
        self.canv.circle(points[-1][0], points[-1][1], 2, fill=1)


def create_heatmapped_table_style(table_data: List[List], value_column_index: int,
                                   base_style: Optional[List] = None,
                                   color_scheme: str = 'blue') -> TableStyle:
    """
    Create a TableStyle with heatmap coloring based on scalar values in a column.

    Salvaged from Masai-Interactive/google_analytics_reports StructuredGAReportGenerator.

    Args:
        table_data: Table data including header row
        value_column_index: Index of column with numeric values for heatmapping
        base_style: Base style commands (list of tuples). If None, uses professional defaults.
        color_scheme: Color gradient scheme ('blue', 'green', 'red', 'purple')

    Returns:
        TableStyle with heatmap row coloring applied
    """
    if base_style is None:
        base_style = [
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c3e50')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#bdc3c7')),
        ]

    # Extract numeric values from data rows (skip header)
    values = []
    for row in table_data[1:]:
        try:
            val_str = str(row[value_column_index]).replace(',', '').replace('%', '').replace('+', '')
            values.append(float(val_str))
        except (ValueError, IndexError):
            values.append(0)

    if not values:
        return TableStyle(base_style)

    min_val = min(values)
    max_val = max(values)
    val_range = max_val - min_val if max_val != min_val else 1

    style_commands = list(base_style)

    schemes = {
        'blue': lambda i: (235 - int(i * 80), 245 - int(i * 40), 255 - int(i * 30)),
        'green': lambda i: (235 - int(i * 80), 250 - int(i * 20), 235 - int(i * 80)),
        'red': lambda i: (255 - int(i * 30), 235 - int(i * 80), 235 - int(i * 80)),
        'purple': lambda i: (245 - int(i * 40), 235 - int(i * 80), 255 - int(i * 20)),
    }
    color_fn = schemes.get(color_scheme, schemes['blue'])

    for i, value in enumerate(values):
        intensity = (value - min_val) / val_range
        r, g, b = color_fn(intensity)
        r, g, b = max(0, min(255, r)), max(0, min(255, g)), max(0, min(255, b))
        heat_color = colors.HexColor(f"#{r:02x}{g:02x}{b:02x}")
        style_commands.append(('BACKGROUND', (0, i + 1), (-1, i + 1), heat_color))

    return TableStyle(style_commands)


def generate_sample_ga_data(start_date: datetime, end_date: datetime) -> Dict[str, Any]:
    """
    Generate sample Google Analytics data for demonstration.
    In production, this would fetch from the GA4 API.
    """
    days = (end_date - start_date).days + 1
    dates = [start_date + timedelta(days=i) for i in range(days)]

    # Generate realistic daily traffic patterns
    np.random.seed(42)
    base_users = 1500
    weekly_pattern = [1.0, 0.95, 0.9, 0.85, 1.1, 0.7, 0.6]  # Mon-Sun

    daily_users = []
    daily_sessions = []
    daily_pageviews = []
    daily_bounce_rate = []
    daily_avg_duration = []

    for i, date in enumerate(dates):
        weekday = date.weekday()
        trend = 1 + 0.001 * i  # Slight upward trend
        seasonal = weekly_pattern[weekday]
        noise = np.random.normal(1, 0.1)

        users = int(base_users * trend * seasonal * noise)
        sessions = int(users * np.random.uniform(1.1, 1.4))
        pageviews = int(sessions * np.random.uniform(2.5, 4.0))
        bounce = np.random.uniform(35, 55)
        duration = np.random.uniform(90, 180)

        daily_users.append(users)
        daily_sessions.append(sessions)
        daily_pageviews.append(pageviews)
        daily_bounce_rate.append(bounce)
        daily_avg_duration.append(duration)

    # Calculate totals and changes
    total_users = sum(daily_users)
    total_sessions = sum(daily_sessions)
    total_pageviews = sum(daily_pageviews)
    avg_bounce_rate = np.mean(daily_bounce_rate)
    avg_session_duration = np.mean(daily_avg_duration)

    # Traffic sources
    traffic_sources = [
        {'source': 'organic', 'medium': 'search', 'sessions': int(total_sessions * 0.45),
         'users': int(total_users * 0.42), 'bounce_rate': 42.3, 'avg_duration': 145.2},
        {'source': 'direct', 'medium': '(none)', 'sessions': int(total_sessions * 0.25),
         'users': int(total_users * 0.28), 'bounce_rate': 38.7, 'avg_duration': 168.5},
        {'source': 'google', 'medium': 'cpc', 'sessions': int(total_sessions * 0.15),
         'users': int(total_users * 0.14), 'bounce_rate': 52.1, 'avg_duration': 98.3},
        {'source': 'social', 'medium': 'referral', 'sessions': int(total_sessions * 0.10),
         'users': int(total_users * 0.11), 'bounce_rate': 58.4, 'avg_duration': 72.1},
        {'source': 'email', 'medium': 'newsletter', 'sessions': int(total_sessions * 0.05),
         'users': int(total_users * 0.05), 'bounce_rate': 35.2, 'avg_duration': 192.7},
    ]

    # Top pages
    top_pages = [
        {'page': '/', 'pageviews': int(total_pageviews * 0.25), 'unique_views': int(total_pageviews * 0.22),
         'avg_time': 45.3, 'bounce_rate': 35.2, 'exit_rate': 28.4},
        {'page': '/products', 'pageviews': int(total_pageviews * 0.18), 'unique_views': int(total_pageviews * 0.15),
         'avg_time': 92.1, 'bounce_rate': 42.1, 'exit_rate': 35.7},
        {'page': '/about', 'pageviews': int(total_pageviews * 0.12), 'unique_views': int(total_pageviews * 0.10),
         'avg_time': 68.4, 'bounce_rate': 48.3, 'exit_rate': 42.1},
        {'page': '/contact', 'pageviews': int(total_pageviews * 0.08), 'unique_views': int(total_pageviews * 0.07),
         'avg_time': 120.5, 'bounce_rate': 25.1, 'exit_rate': 55.2},
        {'page': '/blog/post-1', 'pageviews': int(total_pageviews * 0.06), 'unique_views': int(total_pageviews * 0.05),
         'avg_time': 185.2, 'bounce_rate': 62.3, 'exit_rate': 58.4},
    ]

    # Geographic data (top regions)
    geo_data = [
        {'country': 'United States', 'region': 'California', 'city': 'Los Angeles',
         'sessions': int(total_sessions * 0.15), 'users': int(total_users * 0.14)},
        {'country': 'United States', 'region': 'New York', 'city': 'New York',
         'sessions': int(total_sessions * 0.12), 'users': int(total_users * 0.11)},
        {'country': 'United States', 'region': 'Texas', 'city': 'Houston',
         'sessions': int(total_sessions * 0.08), 'users': int(total_users * 0.08)},
        {'country': 'United States', 'region': 'Illinois', 'city': 'Chicago',
         'sessions': int(total_sessions * 0.06), 'users': int(total_users * 0.06)},
        {'country': 'United States', 'region': 'Florida', 'city': 'Miami',
         'sessions': int(total_sessions * 0.05), 'users': int(total_users * 0.05)},
    ]

    # Device categories
    devices = [
        {'device': 'desktop', 'sessions': int(total_sessions * 0.52), 'bounce_rate': 38.2},
        {'device': 'mobile', 'sessions': int(total_sessions * 0.42), 'bounce_rate': 52.4},
        {'device': 'tablet', 'sessions': int(total_sessions * 0.06), 'bounce_rate': 44.1},
    ]

    # Prior period comparison (assume 10% growth)
    prior_users = int(total_users / 1.10)
    prior_sessions = int(total_sessions / 1.08)
    prior_bounce = avg_bounce_rate + 3.2
    prior_duration = avg_session_duration * 0.92

    # Best/worst day analysis
    best_day_idx = daily_sessions.index(max(daily_sessions))
    worst_day_idx = daily_sessions.index(min(daily_sessions))

    # Weekly aggregation
    daily_df = pd.DataFrame({
        'date': dates,
        'sessions': daily_sessions,
        'users': daily_users,
    })
    daily_df['week'] = daily_df['date'].apply(lambda d: d.isocalendar()[1])
    weekly_agg = daily_df.groupby('week').agg({'sessions': 'sum', 'users': 'sum'}).reset_index()
    best_week_idx = weekly_agg['sessions'].idxmax()
    worst_week_idx = weekly_agg['sessions'].idxmin()

    # Longitudinal sample data (simulated multi-year)
    current_year = end_date.year
    longitudinal_data = {}
    for offset in [2, 1, 0]:
        year = current_year - offset
        # Simulate growth: ~15% annually
        year_factor = (1.0 + 0.15) ** (2 - offset)
        year_sessions = int(total_sessions * 12 * year_factor)  # Annualize
        year_users = int(total_users * 12 * year_factor)
        longitudinal_data[str(year)] = {
            'sessions': year_sessions,
            'users': year_users,
            'pageviews': int(year_sessions * 3.2),
        }

    return {
        'date_range': {
            'start': start_date.strftime('%Y-%m-%d'),
            'end': end_date.strftime('%Y-%m-%d'),
        },
        'daily_data': {
            'dates': [d.strftime('%Y-%m-%d') for d in dates],
            'users': daily_users,
            'sessions': daily_sessions,
            'pageviews': daily_pageviews,
            'bounce_rate': daily_bounce_rate,
            'avg_duration': daily_avg_duration,
        },
        'totals': {
            'users': total_users,
            'sessions': total_sessions,
            'pageviews': total_pageviews,
            'avg_bounce_rate': avg_bounce_rate,
            'avg_session_duration': avg_session_duration,
            'pages_per_session': total_pageviews / total_sessions,
        },
        'prior_period': {
            'users': prior_users,
            'sessions': prior_sessions,
            'avg_bounce_rate': prior_bounce,
            'avg_session_duration': prior_duration,
        },
        'changes': {
            'users': ((total_users - prior_users) / prior_users) * 100,
            'sessions': ((total_sessions - prior_sessions) / prior_sessions) * 100,
            'bounce_rate': avg_bounce_rate - prior_bounce,
            'duration': ((avg_session_duration - prior_duration) / prior_duration) * 100,
        },
        'traffic_sources': traffic_sources,
        'top_pages': top_pages,
        'geo_data': geo_data,
        'devices': devices,
        'best_day': {
            'date': dates[best_day_idx].strftime('%Y-%m-%d'),
            'sessions': daily_sessions[best_day_idx],
            'users': daily_users[best_day_idx],
        },
        'worst_day': {
            'date': dates[worst_day_idx].strftime('%Y-%m-%d'),
            'sessions': daily_sessions[worst_day_idx],
            'users': daily_users[worst_day_idx],
        },
        'best_week': {
            'week': int(weekly_agg.loc[best_week_idx, 'week']),
            'sessions': int(weekly_agg.loc[best_week_idx, 'sessions']),
        },
        'worst_week': {
            'week': int(weekly_agg.loc[worst_week_idx, 'week']),
            'sessions': int(weekly_agg.loc[worst_week_idx, 'sessions']),
        },
        'weekly_data': weekly_agg.to_dict('records'),
        'longitudinal': longitudinal_data,
    }


def fetch_real_ga4_data(property_id: str, start_date: str, end_date: str,
                        credential_item_name: str = "Google Analytics Service Account - Multi-Client Reporter",
                        vault: Optional[str] = None,
                        account: Optional[str] = None,
                        ) -> Optional[Dict[str, Any]]:
    """
    Fetch real GA4 data using GoogleAnalyticsConnector with 1Password credentials.

    Tries service account auth first, then falls back to OAuth2 credentials.
    Returns the same dict structure as generate_sample_ga_data() so notebook code
    works identically with either data source.

    Salvaged from Masai-Interactive/google_analytics_reports.

    Args:
        property_id: GA4 property ID (e.g., '366963525')
        start_date: Start date string 'YYYY-MM-DD'
        end_date: End date string 'YYYY-MM-DD'
        credential_item_name: 1Password item name for service account
        vault: 1Password vault name (e.g., 'Private')
        account: 1Password account shorthand or UUID

    Returns:
        GA data dict matching generate_sample_ga_data() structure, or None if unavailable
    """
    try:
        from siege_utilities.analytics import GoogleAnalyticsConnector
        from siege_utilities.config import get_google_service_account_from_1password
    except ImportError:
        log.warning("GoogleAnalyticsConnector not available — install google-analytics-data")
        return None

    try:
        connector = None

        # Strategy 1: Try service account credentials from 1Password
        service_account_data = get_google_service_account_from_1password(
            vault=vault, account=account,
        )
        if service_account_data:
            connector = GoogleAnalyticsConnector(
                auth_method="service_account",
                service_account_data=service_account_data,
            )

        # Strategy 2: Try OAuth2 credentials from 1Password
        if connector is None:
            log.info("No service account found — trying OAuth2 credentials")
            try:
                from siege_utilities.config import get_google_oauth_from_1password
            except ImportError:
                log.warning("get_google_oauth_from_1password not available")
                return None

            oauth_creds = get_google_oauth_from_1password(vault=vault, account=account)
            if not oauth_creds:
                log.warning("No GA credentials found in 1Password (service account or OAuth2)")
                return None

            connector = GoogleAnalyticsConnector(
                client_id=oauth_creds['client_id'],
                client_secret=oauth_creds['client_secret'],
                redirect_uri=oauth_creds.get('redirect_uri', 'http://localhost'),
            )
            token_path = Path.home() / '.siege_utilities' / 'ga_token.json'
            token_path.parent.mkdir(parents=True, exist_ok=True)
            if not connector.authenticate(token_file=str(token_path)):
                log.warning("OAuth2 authentication failed")
                return None

        # Fetch daily metrics
        daily_df = connector.get_ga4_data(
            property_id=property_id,
            start_date=start_date,
            end_date=end_date,
            metrics=["sessions", "totalUsers", "screenPageViews", "bounceRate", "averageSessionDuration"],
            dimensions=["date"]
        )

        if daily_df is None or daily_df.empty:
            log.warning("No daily data returned from GA4")
            return None

        # Fetch traffic sources
        sources_df = connector.get_ga4_data(
            property_id=property_id,
            start_date=start_date,
            end_date=end_date,
            metrics=["sessions", "totalUsers", "bounceRate", "averageSessionDuration"],
            dimensions=["sessionDefaultChannelGrouping"]
        )

        # Fetch device categories
        device_df = connector.get_ga4_data(
            property_id=property_id,
            start_date=start_date,
            end_date=end_date,
            metrics=["sessions", "bounceRate"],
            dimensions=["deviceCategory"]
        )

        # Fetch geographic data
        geo_df = connector.get_ga4_data(
            property_id=property_id,
            start_date=start_date,
            end_date=end_date,
            metrics=["sessions", "totalUsers"],
            dimensions=["city", "region", "country"]
        )

        # Fetch top pages
        pages_df = connector.get_ga4_data(
            property_id=property_id,
            start_date=start_date,
            end_date=end_date,
            metrics=["screenPageViews", "bounceRate", "averageSessionDuration"],
            dimensions=["pagePath"]
        )

        # Convert daily data
        daily_df['date'] = pd.to_datetime(daily_df['date'])
        daily_df = daily_df.sort_values('date')
        dates = daily_df['date'].tolist()
        daily_sessions = daily_df['sessions'].astype(int).tolist()
        daily_users = daily_df['totalUsers'].astype(int).tolist()
        daily_pageviews = daily_df['screenPageViews'].astype(int).tolist()
        daily_bounce = daily_df['bounceRate'].astype(float).tolist()
        daily_duration = daily_df['averageSessionDuration'].astype(float).tolist()

        total_sessions = sum(daily_sessions)
        total_users = sum(daily_users)
        total_pageviews = sum(daily_pageviews)
        avg_bounce = float(np.mean(daily_bounce)) if daily_bounce else 0.0
        avg_duration = float(np.mean(daily_duration)) if daily_duration else 0.0

        # Traffic sources
        traffic_sources = []
        if sources_df is not None and not sources_df.empty:
            for _, row in sources_df.nlargest(5, 'sessions').iterrows():
                traffic_sources.append({
                    'source': row.get('sessionDefaultChannelGrouping', 'unknown'),
                    'medium': 'channel',
                    'sessions': int(row['sessions']),
                    'users': int(row.get('totalUsers', 0)),
                    'bounce_rate': float(row.get('bounceRate', 0)),
                    'avg_duration': float(row.get('averageSessionDuration', 0)),
                })

        # Devices
        devices = []
        if device_df is not None and not device_df.empty:
            for _, row in device_df.iterrows():
                devices.append({
                    'device': row.get('deviceCategory', 'unknown'),
                    'sessions': int(row['sessions']),
                    'bounce_rate': float(row.get('bounceRate', 0)),
                })

        # Geographic data (top 5 cities)
        geo_data = []
        if geo_df is not None and not geo_df.empty:
            for _, row in geo_df.nlargest(5, 'sessions').iterrows():
                geo_data.append({
                    'country': row.get('country', 'Unknown'),
                    'region': row.get('region', 'Unknown'),
                    'city': row.get('city', 'Unknown'),
                    'sessions': int(row['sessions']),
                    'users': int(row.get('totalUsers', 0)),
                })

        # Top pages
        top_pages = []
        if pages_df is not None and not pages_df.empty:
            for _, row in pages_df.nlargest(5, 'screenPageViews').iterrows():
                top_pages.append({
                    'page': row.get('pagePath', '/'),
                    'pageviews': int(row['screenPageViews']),
                    'unique_views': int(row['screenPageViews'] * 0.85),
                    'avg_time': float(row.get('averageSessionDuration', 0)),
                    'bounce_rate': float(row.get('bounceRate', 0)),
                    'exit_rate': float(row.get('bounceRate', 0)) * 0.8,
                })

        # Best/worst day
        best_day_idx = daily_sessions.index(max(daily_sessions))
        worst_day_idx = daily_sessions.index(min(daily_sessions))

        # Weekly aggregation
        daily_df_agg = pd.DataFrame({'date': dates, 'sessions': daily_sessions, 'users': daily_users})
        daily_df_agg['week'] = daily_df_agg['date'].apply(lambda d: d.isocalendar()[1])
        weekly_agg = daily_df_agg.groupby('week').agg({'sessions': 'sum', 'users': 'sum'}).reset_index()
        best_week_idx = weekly_agg['sessions'].idxmax()
        worst_week_idx = weekly_agg['sessions'].idxmin()

        # Prior period comparison (fetch prior period data)
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        end_dt = datetime.strptime(end_date, '%Y-%m-%d')
        period_days = (end_dt - start_dt).days
        prior_start = (start_dt - timedelta(days=period_days)).strftime('%Y-%m-%d')
        prior_end = (start_dt - timedelta(days=1)).strftime('%Y-%m-%d')

        prior_df = connector.get_ga4_data(
            property_id=property_id,
            start_date=prior_start,
            end_date=prior_end,
            metrics=["sessions", "totalUsers", "bounceRate", "averageSessionDuration"],
            dimensions=["date"]
        )

        prior_sessions = int(prior_df['sessions'].sum()) if prior_df is not None else int(total_sessions / 1.08)
        prior_users = int(prior_df['totalUsers'].sum()) if prior_df is not None else int(total_users / 1.10)
        prior_bounce = float(prior_df['bounceRate'].mean()) if prior_df is not None else avg_bounce + 3.2
        prior_duration = float(prior_df['averageSessionDuration'].mean()) if prior_df is not None else avg_duration * 0.92

        # Longitudinal data (fetch yearly totals)
        current_year = end_dt.year
        longitudinal_data = {}
        for offset in [2, 1, 0]:
            year = current_year - offset
            year_start = f"{year}-01-01"
            year_end = end_date if offset == 0 else f"{year}-12-31"
            try:
                year_df = connector.get_ga4_data(
                    property_id=property_id,
                    start_date=year_start,
                    end_date=year_end,
                    metrics=["sessions", "totalUsers", "screenPageViews"],
                    dimensions=["year"]
                )
                if year_df is not None and not year_df.empty:
                    longitudinal_data[str(year)] = {
                        'sessions': int(year_df['sessions'].sum()),
                        'users': int(year_df['totalUsers'].sum()),
                        'pageviews': int(year_df['screenPageViews'].sum()),
                    }
            except Exception:
                log.debug(f"Could not fetch longitudinal data for {year}")

        result = {
            'date_range': {'start': start_date, 'end': end_date},
            'daily_data': {
                'dates': [d.strftime('%Y-%m-%d') for d in dates],
                'users': daily_users,
                'sessions': daily_sessions,
                'pageviews': daily_pageviews,
                'bounce_rate': daily_bounce,
                'avg_duration': daily_duration,
            },
            'totals': {
                'users': total_users,
                'sessions': total_sessions,
                'pageviews': total_pageviews,
                'avg_bounce_rate': avg_bounce,
                'avg_session_duration': avg_duration,
                'pages_per_session': total_pageviews / total_sessions if total_sessions else 0,
            },
            'prior_period': {
                'users': prior_users,
                'sessions': prior_sessions,
                'avg_bounce_rate': prior_bounce,
                'avg_session_duration': prior_duration,
            },
            'changes': {
                'users': ((total_users - prior_users) / prior_users * 100) if prior_users else 0,
                'sessions': ((total_sessions - prior_sessions) / prior_sessions * 100) if prior_sessions else 0,
                'bounce_rate': avg_bounce - prior_bounce,
                'duration': ((avg_duration - prior_duration) / prior_duration * 100) if prior_duration else 0,
            },
            'traffic_sources': traffic_sources,
            'top_pages': top_pages,
            'geo_data': geo_data,
            'devices': devices,
            'best_day': {
                'date': dates[best_day_idx].strftime('%Y-%m-%d'),
                'sessions': daily_sessions[best_day_idx],
                'users': daily_users[best_day_idx],
            },
            'worst_day': {
                'date': dates[worst_day_idx].strftime('%Y-%m-%d'),
                'sessions': daily_sessions[worst_day_idx],
                'users': daily_users[worst_day_idx],
            },
            'best_week': {
                'week': int(weekly_agg.loc[best_week_idx, 'week']),
                'sessions': int(weekly_agg.loc[best_week_idx, 'sessions']),
            },
            'worst_week': {
                'week': int(weekly_agg.loc[worst_week_idx, 'week']),
                'sessions': int(weekly_agg.loc[worst_week_idx, 'sessions']),
            },
            'weekly_data': weekly_agg.to_dict('records'),
            'longitudinal': longitudinal_data,
            'data_source': 'ga4_api',
        }

        log.info(f"Fetched real GA4 data: {total_sessions:,} sessions, {total_users:,} users")
        return result

    except Exception as e:
        log.warning(f"Could not fetch real GA4 data: {e}")
        return None


def create_kpi_dashboard(ga_data: Dict[str, Any]) -> List[Flowable]:
    """Create a row of KPI cards for the dashboard section."""
    if not REPORTLAB_AVAILABLE:
        return []

    totals = ga_data['totals']
    changes = ga_data['changes']

    kpis = [
        KPICard(
            title="Total Users",
            value=f"{totals['users']:,}",
            change=changes['users'],
            primary_color=(0.2, 0.5, 0.8)
        ),
        KPICard(
            title="Sessions",
            value=f"{totals['sessions']:,}",
            change=changes['sessions'],
            primary_color=(0.3, 0.6, 0.4)
        ),
        KPICard(
            title="Bounce Rate",
            value=f"{totals['avg_bounce_rate']:.1f}%",
            change=-changes['bounce_rate'],  # Negative is good for bounce rate
            primary_color=(0.8, 0.4, 0.2)
        ),
        KPICard(
            title="Avg. Session Duration",
            value=f"{totals['avg_session_duration']:.0f}s",
            change=changes['duration'],
            primary_color=(0.6, 0.3, 0.7)
        ),
    ]

    # Create a table to hold KPI cards side by side
    kpi_table = Table([[kpi for kpi in kpis]], colWidths=[2.2*inch]*4)
    kpi_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))

    return [kpi_table, Spacer(1, 24)]


def create_traffic_trend_chart(ga_data: Dict[str, Any], width: float = 7*inch,
                                height: float = 3*inch) -> Optional[str]:
    """Create a line chart showing traffic trends over time."""
    if not MATPLOTLIB_AVAILABLE:
        return None

    daily = ga_data['daily_data']
    dates = [datetime.strptime(d, '%Y-%m-%d') for d in daily['dates']]

    fig, ax = plt.subplots(figsize=(width/72, height/72), dpi=100)

    # Plot users and sessions
    ax.plot(dates, daily['users'], color='#3366cc', linewidth=2, label='Users')
    ax.plot(dates, daily['sessions'], color='#dc3912', linewidth=2, label='Sessions', alpha=0.7)

    # Formatting
    ax.set_xlabel('Date', fontsize=10)
    ax.set_ylabel('Count', fontsize=10)
    ax.set_title('Daily Users & Sessions', fontsize=12, fontweight='bold')
    ax.legend(loc='upper left', fontsize=9)
    ax.grid(True, alpha=0.3)

    # Format x-axis dates
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %d'))
    ax.xaxis.set_major_locator(mdates.WeekdayLocator(interval=1))
    plt.xticks(rotation=45, ha='right')

    plt.tight_layout()

    # Save to temporary file
    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
        plt.savefig(tmp.name, dpi=150, bbox_inches='tight')
        plt.close()
        return tmp.name


def create_traffic_sources_chart(ga_data: Dict[str, Any], width: float = 6*inch,
                                  height: float = 4*inch) -> Optional[str]:
    """Create a pie chart of traffic sources."""
    if not MATPLOTLIB_AVAILABLE:
        return None

    sources = ga_data['traffic_sources']
    labels = [s['source'] for s in sources]
    values = [s['sessions'] for s in sources]
    colors = ['#3366cc', '#dc3912', '#ff9900', '#109618', '#990099']

    fig, ax = plt.subplots(figsize=(width/72, height/72), dpi=100)

    wedges, texts, autotexts = ax.pie(
        values, labels=labels, autopct='%1.1f%%',
        colors=colors, startangle=90,
        textprops={'fontsize': 9}
    )

    ax.set_title('Traffic Sources', fontsize=12, fontweight='bold')

    plt.tight_layout()

    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
        plt.savefig(tmp.name, dpi=150, bbox_inches='tight')
        plt.close()
        return tmp.name


def create_device_breakdown_chart(ga_data: Dict[str, Any], width: float = 5*inch,
                                   height: float = 3.5*inch) -> Optional[str]:
    """Create a horizontal bar chart for device breakdown."""
    if not MATPLOTLIB_AVAILABLE:
        return None

    devices = ga_data['devices']
    labels = [d['device'].title() for d in devices]
    values = [d['sessions'] for d in devices]

    fig, ax = plt.subplots(figsize=(width/72, height/72), dpi=100)

    bars = ax.barh(labels, values, color=['#3366cc', '#dc3912', '#ff9900'])
    ax.set_xlabel('Sessions', fontsize=9)
    ax.set_title('Sessions by Device', fontsize=11, fontweight='bold')

    # Add value labels
    for bar, val in zip(bars, values):
        ax.text(val + max(values)*0.02, bar.get_y() + bar.get_height()/2,
                f'{val:,}', va='center', fontsize=8)

    plt.tight_layout()

    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
        plt.savefig(tmp.name, dpi=150, bbox_inches='tight')
        plt.close()
        return tmp.name


def create_top_pages_table(ga_data: Dict[str, Any]) -> List[List[str]]:
    """Create table data for top pages."""
    pages = ga_data['top_pages']

    headers = ['Page', 'Pageviews', 'Unique Views', 'Avg. Time', 'Bounce Rate', 'Exit Rate']
    rows = []

    for page in pages:
        rows.append([
            page['page'][:40],  # Truncate long paths
            f"{page['pageviews']:,}",
            f"{page['unique_views']:,}",
            f"{page['avg_time']:.1f}s",
            f"{page['bounce_rate']:.1f}%",
            f"{page['exit_rate']:.1f}%",
        ])

    return [headers] + rows


def create_traffic_sources_table(ga_data: Dict[str, Any]) -> List[List[str]]:
    """Create table data for traffic sources."""
    sources = ga_data['traffic_sources']

    headers = ['Source', 'Medium', 'Sessions', 'Users', 'Bounce Rate', 'Avg. Duration']
    rows = []

    for src in sources:
        rows.append([
            src['source'],
            src['medium'],
            f"{src['sessions']:,}",
            f"{src['users']:,}",
            f"{src['bounce_rate']:.1f}%",
            f"{src['avg_duration']:.1f}s",
        ])

    return [headers] + rows


def create_geo_table(ga_data: Dict[str, Any]) -> List[List[str]]:
    """Create table data for geographic breakdown."""
    geo = ga_data['geo_data']

    headers = ['City', 'Region', 'Sessions', 'Users']
    rows = []

    for loc in geo:
        rows.append([
            loc['city'],
            loc['region'],
            f"{loc['sessions']:,}",
            f"{loc['users']:,}",
        ])

    return [headers] + rows


def generate_insights(ga_data: Dict[str, Any]) -> List[str]:
    """Generate automated insights from the data."""
    insights = []

    changes = ga_data['changes']
    totals = ga_data['totals']
    sources = ga_data['traffic_sources']
    devices = ga_data['devices']

    # User growth insight
    if changes['users'] > 0:
        insights.append(f"User traffic increased by {changes['users']:.1f}% compared to the prior period, "
                       f"indicating positive growth momentum.")
    else:
        insights.append(f"User traffic decreased by {abs(changes['users']):.1f}% compared to the prior period. "
                       f"Consider reviewing marketing efforts and content strategy.")

    # Bounce rate insight
    if totals['avg_bounce_rate'] < 40:
        insights.append(f"The bounce rate of {totals['avg_bounce_rate']:.1f}% is excellent, "
                       f"indicating strong user engagement with your content.")
    elif totals['avg_bounce_rate'] > 60:
        insights.append(f"The bounce rate of {totals['avg_bounce_rate']:.1f}% is higher than optimal. "
                       f"Consider improving page load times and content relevance.")

    # Traffic source insight
    top_source = max(sources, key=lambda x: x['sessions'])
    insights.append(f"'{top_source['source'].title()}' is the primary traffic driver, "
                   f"contributing {top_source['sessions']:,} sessions ({top_source['sessions']/totals['sessions']*100:.1f}% of total).")

    # Device insight
    mobile = next((d for d in devices if d['device'] == 'mobile'), None)
    if mobile:
        mobile_pct = mobile['sessions'] / totals['sessions'] * 100
        if mobile_pct > 50:
            insights.append(f"Mobile traffic accounts for {mobile_pct:.1f}% of sessions. "
                           f"Ensure your site provides an excellent mobile experience.")

    # Session duration insight
    if totals['avg_session_duration'] > 120:
        insights.append(f"Average session duration of {totals['avg_session_duration']:.0f} seconds "
                       f"indicates users are engaging deeply with your content.")

    return insights


def generate_recommendations(ga_data: Dict[str, Any]) -> List[str]:
    """Generate actionable recommendations from the data."""
    recommendations = []

    totals = ga_data['totals']
    sources = ga_data['traffic_sources']
    pages = ga_data['top_pages']
    devices = ga_data['devices']

    # Bounce rate recommendations
    if totals['avg_bounce_rate'] > 50:
        recommendations.append("Reduce bounce rate by improving page load speed, "
                              "adding compelling above-the-fold content, and ensuring clear CTAs.")

    # Traffic source recommendations
    organic = next((s for s in sources if s['source'] == 'organic'), None)
    if organic and organic['sessions'] / totals['sessions'] < 0.40:
        recommendations.append("Invest in SEO to increase organic traffic share. "
                              "Focus on keyword research and content optimization.")

    # Mobile optimization
    mobile = next((d for d in devices if d['device'] == 'mobile'), None)
    if mobile and mobile['bounce_rate'] > 50:
        recommendations.append(f"Mobile bounce rate ({mobile['bounce_rate']:.1f}%) is high. "
                              f"Prioritize mobile UX improvements and page speed optimization.")

    # Content recommendations
    if pages:
        high_bounce_pages = [p for p in pages if p['bounce_rate'] > 55]
        if high_bounce_pages:
            recommendations.append(f"Review content on pages with high bounce rates "
                                  f"(e.g., {high_bounce_pages[0]['page']}). "
                                  f"Consider adding related content links and clearer navigation.")

    # Engagement recommendations
    if totals['pages_per_session'] < 2.5:
        recommendations.append("Increase pages per session by improving internal linking, "
                              "adding related content sections, and implementing content recommendations.")

    return recommendations


def generate_ga_report_pdf(ga_data: Dict[str, Any], output_path: str,
                           client_name: str = "Demo Client",
                           report_title: str = "Google Analytics Performance Report",
                           branding_key: Optional[str] = None,
                           prepared_by: str = "Siege Analytics") -> bool:
    """
    Generate a comprehensive Google Analytics PDF report with professional styling.

    Produces a multi-section report including executive summary, KPI dashboard,
    traffic trends, source analysis, geographic data, longitudinal YoY comparison,
    best/worst day analysis, and actionable recommendations.

    Args:
        ga_data: Google Analytics data dictionary (from generate_sample_ga_data or fetch_real_ga4_data)
        output_path: Output PDF file path
        client_name: Client name for branding
        report_title: Report title
        branding_key: Optional ClientBrandingManager template key (e.g., 'hillcrest', 'siege_analytics')
        prepared_by: Name of report preparer

    Returns:
        True if successful
    """
    if not REPORTLAB_AVAILABLE:
        log.error("ReportLab not available - cannot generate PDF")
        return False

    try:
        # Load branding colors
        primary_color = '#1E3A5F'
        secondary_color = '#2E7D32'
        if branding_key:
            try:
                from siege_utilities.reporting.client_branding import ClientBrandingManager
                mgr = ClientBrandingManager()
                branding = mgr.get_client_branding(branding_key)
                if branding:
                    primary_color = branding.get('colors', {}).get('primary', primary_color)
                    secondary_color = branding.get('colors', {}).get('secondary', secondary_color)
                    client_name = branding.get('name', client_name)
                    prepared_by = branding.get('footer', {}).get('left_text', f"Prepared by: {prepared_by}").replace('Prepared by: ', '')
            except Exception as e:
                log.debug(f"Could not load branding '{branding_key}': {e}")

        date_range = ga_data['date_range']
        totals = ga_data['totals']
        changes = ga_data['changes']

        # Header/footer callback
        def _header_footer(canvas_obj, doc_obj):
            canvas_obj.saveState()
            canvas_obj.setFont('Helvetica-Bold', 8)
            canvas_obj.setFillColor(colors.HexColor(primary_color))
            canvas_obj.drawString(0.75*inch, letter[1] - 0.4*inch, report_title)
            canvas_obj.setFont('Helvetica', 7)
            canvas_obj.setFillColor(colors.HexColor('#666666'))
            canvas_obj.drawString(0.75*inch, letter[1] - 0.52*inch, f"{client_name}  |  {date_range['start']} to {date_range['end']}")
            # Footer
            canvas_obj.setFont('Helvetica', 7)
            canvas_obj.drawString(0.75*inch, 0.4*inch, f"Page {doc_obj.page}")
            canvas_obj.drawRightString(letter[0] - 0.75*inch, 0.4*inch, prepared_by)
            canvas_obj.restoreState()

        # Create document with room for header/footer
        doc = SimpleDocTemplate(
            output_path,
            pagesize=letter,
            rightMargin=0.75*inch,
            leftMargin=0.75*inch,
            topMargin=0.85*inch,
            bottomMargin=0.7*inch
        )

        styles = getSampleStyleSheet()

        # Branding-aware styles
        title_style = ParagraphStyle(
            'CustomTitle', parent=styles['Title'],
            fontSize=28, spaceAfter=8, alignment=TA_CENTER,
            textColor=colors.HexColor(primary_color), fontName='Helvetica-Bold'
        )
        subtitle_style = ParagraphStyle(
            'CustomSubtitle', parent=styles['Normal'],
            fontSize=14, alignment=TA_CENTER, textColor=colors.HexColor('#666666'),
            spaceAfter=20
        )
        heading_style = ParagraphStyle(
            'CustomHeading', parent=styles['Heading1'],
            fontSize=16, spaceBefore=20, spaceAfter=10,
            textColor=colors.HexColor(primary_color)
        )
        subheading_style = ParagraphStyle(
            'CustomSubheading', parent=styles['Heading2'],
            fontSize=13, spaceBefore=15, spaceAfter=8,
            textColor=colors.HexColor('#34495e')
        )
        body_style = ParagraphStyle(
            'CustomBody', parent=styles['Normal'],
            fontSize=10, leading=14, spaceBefore=6, spaceAfter=6
        )
        bullet_style = ParagraphStyle(
            'CustomBullet', parent=styles['Normal'],
            fontSize=10, leading=14, leftIndent=20, bulletIndent=10,
            spaceBefore=3, spaceAfter=3
        )
        details_style = ParagraphStyle(
            'Details', parent=styles['Normal'],
            fontSize=11, spaceAfter=6, alignment=TA_LEFT
        )

        # Standard table styles
        primary_table_style = [
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor(primary_color)),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#F8F9FA')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E9ECEF')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#F8F9FA'), colors.white]),
        ]

        green_table_style = list(primary_table_style)
        green_table_style[0] = ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor(secondary_color))

        story = []

        # ── TITLE PAGE ──
        story.append(Spacer(1, 1.5*inch))
        story.append(Paragraph(client_name, title_style))
        story.append(Paragraph("Comprehensive Website Performance Analysis", subtitle_style))
        story.append(Spacer(1, 0.3*inch))
        story.append(Paragraph(report_title, ParagraphStyle(
            'ReportTitle', parent=styles['Heading1'],
            fontSize=20, alignment=TA_CENTER, fontName='Helvetica-Bold'
        )))
        story.append(Spacer(1, 0.5*inch))
        story.append(Paragraph(f"<b>Report Date:</b> {datetime.now().strftime('%B %d, %Y')}", details_style))
        story.append(Paragraph(f"<b>Period Covered:</b> {date_range['start']} to {date_range['end']}", details_style))
        story.append(Paragraph(f"<b>Prepared By:</b> {prepared_by}", details_style))
        data_source = ga_data.get('data_source', 'sample')
        story.append(Paragraph(f"<b>Data Source:</b> {'GA4 API (Live)' if data_source == 'ga4_api' else 'Sample Data'}", details_style))
        story.append(PageBreak())

        # ── TABLE OF CONTENTS ──
        story.append(Paragraph("Table of Contents", heading_style))
        story.append(Spacer(1, 12))
        toc_items = [
            "1. Executive Summary",
            "2. Key Performance Indicators",
            "3. Traffic Trends",
            "4. Traffic Sources Analysis",
            "5. Device Analysis",
            "6. Top Pages Performance",
            "7. Geographic Distribution",
        ]
        if ga_data.get('longitudinal'):
            toc_items.append("8. Year-over-Year Analysis")
        if ga_data.get('best_day'):
            toc_items.append(f"{len(toc_items) + 1}. Performance Highlights")
        toc_items.append(f"{len(toc_items) + 1}. Key Insights")
        toc_items.append(f"{len(toc_items) + 1}. Recommendations")
        for item in toc_items:
            story.append(Paragraph(item, ParagraphStyle(
                'TOC', parent=styles['Normal'], fontSize=12, spaceBefore=4, spaceAfter=4,
                leftIndent=20
            )))
        story.append(PageBreak())

        # ── 1. EXECUTIVE SUMMARY ──
        story.append(Paragraph("1. Executive Summary", heading_style))
        summary_text = (
            f"This report provides a comprehensive analysis of website performance for the period "
            f"{date_range['start']} to {date_range['end']}. During this period, the website received "
            f"<b>{totals['users']:,}</b> unique users and <b>{totals['sessions']:,}</b> sessions, "
            f"representing a <b>{changes['users']:+.1f}%</b> change in users compared to the prior period."
        )
        story.append(Paragraph(summary_text, body_style))
        story.append(Spacer(1, 8))
        summary_text2 = (
            f"Key performance indicators show an average bounce rate of <b>{totals['avg_bounce_rate']:.1f}%</b> "
            f"and average session duration of <b>{totals['avg_session_duration']:.0f} seconds</b>. "
            f"Users viewed an average of <b>{totals['pages_per_session']:.1f} pages</b> per session."
        )
        story.append(Paragraph(summary_text2, body_style))
        story.append(Spacer(1, 15))

        # Key Performance Highlights table
        avg_daily = totals['sessions'] / max(1, len(ga_data['daily_data']['sessions']))
        kph_data = [
            ["Metric", "Value", "Details"],
            ["Total Sessions", f"{totals['sessions']:,}", f"Average: {avg_daily:.0f} per day"],
            ["Total Users", f"{totals['users']:,}", "Unique visitors"],
            ["Total Pageviews", f"{totals['pageviews']:,}", f"{totals['pages_per_session']:.1f} pages/session"],
            ["Avg Bounce Rate", f"{totals['avg_bounce_rate']:.1f}%", f"{changes['bounce_rate']:+.1f}% vs prior"],
            ["Avg Session Duration", f"{totals['avg_session_duration']:.0f}s", f"{changes['duration']:+.1f}% vs prior"],
        ]
        if ga_data.get('best_day'):
            kph_data.append(["Best Day", f"{ga_data['best_day']['sessions']:,} sessions", ga_data['best_day']['date']])
        if ga_data.get('worst_day'):
            kph_data.append(["Lowest Day", f"{ga_data['worst_day']['sessions']:,} sessions", ga_data['worst_day']['date']])

        kph_table = Table(kph_data, colWidths=[2*inch, 1.5*inch, 2.8*inch])
        kph_table.setStyle(TableStyle(primary_table_style))
        story.append(kph_table)
        story.append(Spacer(1, 20))

        # ── 2. KPI DASHBOARD ──
        story.append(Paragraph("2. Key Performance Indicators", heading_style))
        story.extend(create_kpi_dashboard(ga_data))
        story.append(PageBreak())

        # ── 3. TRAFFIC TRENDS ──
        story.append(Paragraph("3. Traffic Trends", heading_style))
        trend_chart = create_traffic_trend_chart(ga_data)
        if trend_chart:
            story.append(RLImage(trend_chart, width=7*inch, height=3*inch))
            story.append(Spacer(1, 12))
        else:
            story.append(Paragraph("Traffic trend chart unavailable (matplotlib not installed).", body_style))
        story.append(PageBreak())

        # ── 4. TRAFFIC SOURCES ──
        story.append(Paragraph("4. Traffic Sources Analysis", heading_style))
        source_chart = create_traffic_sources_chart(ga_data)
        if source_chart:
            story.append(RLImage(source_chart, width=6*inch, height=4*inch))
            story.append(Spacer(1, 12))

        source_table_data = create_traffic_sources_table(ga_data)
        # Heatmap the sessions column (index 2)
        source_table = Table(source_table_data, colWidths=[1.2*inch, 1*inch, 1*inch, 1*inch, 1*inch, 1.2*inch])
        source_table.setStyle(create_heatmapped_table_style(
            source_table_data, value_column_index=2,
            base_style=primary_table_style, color_scheme='blue'
        ))
        story.append(source_table)
        story.append(Spacer(1, 20))

        # ── 5. DEVICE ANALYSIS ──
        story.append(Paragraph("5. Device Analysis", heading_style))
        device_chart = create_device_breakdown_chart(ga_data)
        if device_chart:
            story.append(RLImage(device_chart, width=5*inch, height=3.5*inch))
        else:
            story.append(Paragraph("Device analysis chart unavailable (matplotlib not installed).", body_style))
        story.append(PageBreak())

        # ── 6. TOP PAGES ──
        story.append(Paragraph("6. Top Pages Performance", heading_style))
        pages_table_data = create_top_pages_table(ga_data)
        pages_table = Table(pages_table_data, colWidths=[2.2*inch, 0.9*inch, 0.9*inch, 0.8*inch, 0.9*inch, 0.8*inch])
        pages_table.setStyle(create_heatmapped_table_style(
            pages_table_data, value_column_index=1,
            base_style=[
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor(primary_color)),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (0, -1), 'LEFT'),
                ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 9),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#bdc3c7')),
            ],
            color_scheme='blue'
        ))
        story.append(pages_table)
        story.append(Spacer(1, 20))

        # ── 7. GEOGRAPHIC DISTRIBUTION ──
        story.append(Paragraph("7. Geographic Distribution", heading_style))
        story.append(Paragraph("Top locations by session volume:", body_style))
        geo_table_data = create_geo_table(ga_data)
        geo_table = Table(geo_table_data, colWidths=[1.8*inch, 1.5*inch, 1.2*inch, 1.2*inch])
        geo_table.setStyle(create_heatmapped_table_style(
            geo_table_data, value_column_index=2,
            base_style=green_table_style, color_scheme='green'
        ))
        story.append(geo_table)
        story.append(PageBreak())

        # ── 8. YEAR-OVER-YEAR ANALYSIS (if available) ──
        longitudinal = ga_data.get('longitudinal', {})
        if longitudinal:
            story.append(Paragraph("8. Year-over-Year Analysis", heading_style))
            story.append(Paragraph(
                "Longitudinal comparison of website performance across years.",
                body_style
            ))
            story.append(Spacer(1, 10))

            yoy_header = ["Year", "Sessions", "Users", "Pageviews", "Growth Rate"]
            yoy_rows = []
            years_sorted = sorted(longitudinal.keys())
            prev_sessions = None
            for year in years_sorted:
                year_data = longitudinal[year]
                sessions = year_data['sessions']
                growth = "Baseline"
                if prev_sessions and prev_sessions > 0:
                    rate = ((sessions - prev_sessions) / prev_sessions) * 100
                    growth = f"{rate:+.1f}%"
                yoy_rows.append([
                    year if year == years_sorted[-1] else year,
                    f"{sessions:,}",
                    f"{year_data['users']:,}",
                    f"{year_data['pageviews']:,}",
                    growth,
                ])
                prev_sessions = sessions

            yoy_table_data = [yoy_header] + yoy_rows
            yoy_table = Table(yoy_table_data, colWidths=[1.2*inch, 1.4*inch, 1.4*inch, 1.4*inch, 1.2*inch])
            yoy_table.setStyle(create_heatmapped_table_style(
                yoy_table_data, value_column_index=1,
                base_style=green_table_style, color_scheme='green'
            ))
            story.append(yoy_table)
            story.append(Spacer(1, 20))

        # ── PERFORMANCE HIGHLIGHTS (best/worst) ──
        best_day = ga_data.get('best_day')
        worst_day = ga_data.get('worst_day')
        best_week = ga_data.get('best_week')
        worst_week = ga_data.get('worst_week')
        if best_day or best_week:
            section_num = 9 if longitudinal else 8
            story.append(Paragraph(f"{section_num}. Performance Highlights", heading_style))

            highlights = [["Metric", "Value", "Details"]]
            if best_day:
                highlights.append(["Best Day", f"{best_day['sessions']:,} sessions", best_day['date']])
            if worst_day:
                highlights.append(["Lowest Day", f"{worst_day['sessions']:,} sessions", worst_day['date']])
            if best_week:
                highlights.append(["Best Week", f"{best_week['sessions']:,} sessions", f"Week {best_week['week']}"])
            if worst_week:
                highlights.append(["Lowest Week", f"{worst_week['sessions']:,} sessions", f"Week {worst_week['week']}"])

            hl_table = Table(highlights, colWidths=[2*inch, 2*inch, 2.3*inch])
            hl_table.setStyle(TableStyle(primary_table_style))
            story.append(hl_table)
            story.append(Spacer(1, 20))
            story.append(PageBreak())

        if not (best_day or best_week):
            story.append(PageBreak())

        # ── INSIGHTS ──
        insights_num = (10 if longitudinal and (best_day or best_week) else
                       9 if longitudinal or (best_day or best_week) else 8)
        story.append(Paragraph(f"{insights_num}. Key Insights", heading_style))
        insights = generate_insights(ga_data)
        for insight in insights:
            story.append(Paragraph(f"-- {insight}", bullet_style))
        story.append(Spacer(1, 20))

        # ── RECOMMENDATIONS ──
        story.append(Paragraph(f"{insights_num + 1}. Recommendations", heading_style))
        recommendations = generate_recommendations(ga_data)
        for i, rec in enumerate(recommendations, 1):
            story.append(Paragraph(f"<b>{i}.</b> {rec}", bullet_style))
        story.append(Spacer(1, 30))

        # Build with header/footer
        doc.build(story, onFirstPage=lambda c, d: None, onLaterPages=_header_footer)

        log.info(f"Google Analytics report generated: {output_path}")
        return True

    except Exception as e:
        log.error(f"Error generating GA report: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main demonstration function."""
    print("=" * 80)
    print("Enhanced Google Analytics Report Generator")
    print("=" * 80)

    # Generate sample data for last 30 days
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)

    print(f"\nGenerating sample data for {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}...")
    ga_data = generate_sample_ga_data(start_date, end_date)

    print(f"  Total Users: {ga_data['totals']['users']:,}")
    print(f"  Total Sessions: {ga_data['totals']['sessions']:,}")
    print(f"  Avg Bounce Rate: {ga_data['totals']['avg_bounce_rate']:.1f}%")

    # Generate PDF report
    output_path = "ga_performance_report.pdf"
    print(f"\nGenerating PDF report: {output_path}...")

    success = generate_ga_report_pdf(
        ga_data=ga_data,
        output_path=output_path,
        client_name="Demo Company",
        report_title="Website Analytics Report"
    )

    if success:
        print(f"\n Report generated successfully: {output_path}")
        print("\nReport includes:")
        print("  - Executive Summary")
        print("  - KPI Dashboard with metric cards")
        print("  - Traffic Trends chart")
        print("  - Traffic Sources analysis")
        print("  - Device breakdown")
        print("  - Top Pages performance table")
        print("  - Geographic distribution")
        print("  - Automated Insights")
        print("  - Actionable Recommendations")
    else:
        print("\n Report generation failed. Check logs for details.")

    return success


if __name__ == "__main__":
    main()

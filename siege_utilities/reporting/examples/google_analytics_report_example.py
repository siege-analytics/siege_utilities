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
    }


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


def create_traffic_sources_chart(ga_data: Dict[str, Any], width: float = 4*inch,
                                  height: float = 3*inch) -> Optional[str]:
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


def create_device_breakdown_chart(ga_data: Dict[str, Any], width: float = 3*inch,
                                   height: float = 2.5*inch) -> Optional[str]:
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
                           report_title: str = "Google Analytics Performance Report") -> bool:
    """
    Generate a comprehensive Google Analytics PDF report.

    Args:
        ga_data: Google Analytics data dictionary
        output_path: Output PDF file path
        client_name: Client name for branding
        report_title: Report title

    Returns:
        True if successful
    """
    if not REPORTLAB_AVAILABLE:
        log.error("ReportLab not available - cannot generate PDF")
        return False

    try:
        # Create document
        doc = SimpleDocTemplate(
            output_path,
            pagesize=letter,
            rightMargin=0.75*inch,
            leftMargin=0.75*inch,
            topMargin=0.75*inch,
            bottomMargin=0.75*inch
        )

        styles = getSampleStyleSheet()

        # Custom styles
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Title'],
            fontSize=24,
            spaceAfter=30,
            alignment=TA_CENTER
        )

        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading1'],
            fontSize=16,
            spaceBefore=20,
            spaceAfter=10,
            textColor=colors.HexColor('#2c3e50')
        )

        subheading_style = ParagraphStyle(
            'CustomSubheading',
            parent=styles['Heading2'],
            fontSize=13,
            spaceBefore=15,
            spaceAfter=8,
            textColor=colors.HexColor('#34495e')
        )

        body_style = ParagraphStyle(
            'CustomBody',
            parent=styles['Normal'],
            fontSize=10,
            leading=14,
            spaceBefore=6,
            spaceAfter=6
        )

        bullet_style = ParagraphStyle(
            'CustomBullet',
            parent=styles['Normal'],
            fontSize=10,
            leading=14,
            leftIndent=20,
            bulletIndent=10,
            spaceBefore=3,
            spaceAfter=3
        )

        story = []

        # Title page
        story.append(Spacer(1, 2*inch))
        story.append(Paragraph(report_title, title_style))
        story.append(Paragraph(f"Prepared for: {client_name}",
                              ParagraphStyle('Subtitle', parent=styles['Normal'],
                                           fontSize=14, alignment=TA_CENTER)))
        story.append(Spacer(1, 12))

        date_range = ga_data['date_range']
        story.append(Paragraph(
            f"Reporting Period: {date_range['start']} to {date_range['end']}",
            ParagraphStyle('DateRange', parent=styles['Normal'],
                          fontSize=12, alignment=TA_CENTER, textColor=colors.grey)
        ))
        story.append(Spacer(1, 12))
        story.append(Paragraph(
            f"Generated: {datetime.now().strftime('%B %d, %Y')}",
            ParagraphStyle('Generated', parent=styles['Normal'],
                          fontSize=10, alignment=TA_CENTER, textColor=colors.grey)
        ))
        story.append(PageBreak())

        # Executive Summary
        story.append(Paragraph("Executive Summary", heading_style))

        totals = ga_data['totals']
        changes = ga_data['changes']
        summary_text = f"""
        This report provides a comprehensive analysis of website performance for the period
        {date_range['start']} to {date_range['end']}. During this period, the website received
        <b>{totals['users']:,}</b> unique users and <b>{totals['sessions']:,}</b> sessions,
        representing a <b>{changes['users']:+.1f}%</b> change in users compared to the prior period.

        Key performance indicators show an average bounce rate of <b>{totals['avg_bounce_rate']:.1f}%</b>
        and average session duration of <b>{totals['avg_session_duration']:.0f} seconds</b>.
        Users viewed an average of <b>{totals['pages_per_session']:.1f} pages</b> per session.
        """
        story.append(Paragraph(summary_text.strip(), body_style))
        story.append(Spacer(1, 20))

        # KPI Dashboard
        story.append(Paragraph("Key Performance Indicators", heading_style))
        story.extend(create_kpi_dashboard(ga_data))
        story.append(Spacer(1, 20))

        # Traffic Trends
        story.append(Paragraph("Traffic Trends", heading_style))
        trend_chart = create_traffic_trend_chart(ga_data)
        if trend_chart:
            story.append(RLImage(trend_chart, width=7*inch, height=3*inch))
            story.append(Spacer(1, 12))

        story.append(PageBreak())

        # Traffic Sources Section
        story.append(Paragraph("Traffic Sources Analysis", heading_style))

        # Side by side: pie chart and table
        source_chart = create_traffic_sources_chart(ga_data)
        source_table_data = create_traffic_sources_table(ga_data)

        if source_chart:
            story.append(RLImage(source_chart, width=4*inch, height=3*inch))
            story.append(Spacer(1, 12))

        story.append(Paragraph("Traffic Sources Breakdown", subheading_style))
        source_table = Table(source_table_data, colWidths=[1.2*inch, 1*inch, 1*inch, 1*inch, 1*inch, 1.2*inch])
        source_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c3e50')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#ecf0f1')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#bdc3c7')),
        ]))
        story.append(source_table)
        story.append(Spacer(1, 20))

        # Device Breakdown
        story.append(Paragraph("Device Analysis", subheading_style))
        device_chart = create_device_breakdown_chart(ga_data)
        if device_chart:
            story.append(RLImage(device_chart, width=3.5*inch, height=2.5*inch))

        story.append(PageBreak())

        # Top Pages Section
        story.append(Paragraph("Top Pages Performance", heading_style))
        pages_table_data = create_top_pages_table(ga_data)
        pages_table = Table(pages_table_data, colWidths=[2.2*inch, 0.9*inch, 0.9*inch, 0.8*inch, 0.9*inch, 0.8*inch])
        pages_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c3e50')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#bdc3c7')),
        ]))
        story.append(pages_table)
        story.append(Spacer(1, 20))

        # Geographic Distribution
        story.append(Paragraph("Geographic Distribution", heading_style))
        story.append(Paragraph("Top locations by session volume:", body_style))
        geo_table_data = create_geo_table(ga_data)
        geo_table = Table(geo_table_data, colWidths=[1.8*inch, 1.5*inch, 1.2*inch, 1.2*inch])
        geo_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#27ae60')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#bdc3c7')),
        ]))
        story.append(geo_table)

        story.append(PageBreak())

        # Insights Section
        story.append(Paragraph("Key Insights", heading_style))
        insights = generate_insights(ga_data)
        for i, insight in enumerate(insights, 1):
            story.append(Paragraph(f"\u2022 {insight}", bullet_style))
        story.append(Spacer(1, 20))

        # Recommendations Section
        story.append(Paragraph("Recommendations", heading_style))
        recommendations = generate_recommendations(ga_data)
        for i, rec in enumerate(recommendations, 1):
            story.append(Paragraph(f"<b>{i}.</b> {rec}", bullet_style))
        story.append(Spacer(1, 20))

        # Footer
        story.append(Spacer(1, 30))
        story.append(Paragraph(
            "<i>This report was generated using siege_utilities analytics reporting system.</i>",
            ParagraphStyle('Footer', parent=styles['Normal'],
                          fontSize=8, alignment=TA_CENTER, textColor=colors.grey)
        ))

        # Build document
        doc.build(story)

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

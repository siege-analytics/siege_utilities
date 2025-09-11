"""
Reporting utilities for siege_utilities package.
Comprehensive PDF and PowerPoint report generation with client branding.
"""

from .base_template import BaseReportTemplate
from .report_generator import ReportGenerator
from .chart_generator import ChartGenerator, create_bar_chart, create_line_chart, create_scatter_plot
from .client_branding import ClientBrandingManager
from .analytics_reports import AnalyticsReportGenerator
from .powerpoint_generator import PowerPointGenerator

# Professional page templates from GA project
from .title_page_template import TitlePageTemplate, create_title_page
from .table_of_contents_template import (
    TableOfContentsTemplate, 
    create_table_of_contents,
    generate_sections_from_report_structure
)
from .content_page_template import ContentPageTemplate, create_content_page

__all__ = [
    # Base Template
    'BaseReportTemplate',
    
    # Report Generation
    'ReportGenerator',
    'ChartGenerator',
    
    # Chart Functions
    'create_bar_chart',
    'create_line_chart',
    'create_scatter_plot',
    
    # Branding and Customization
    'ClientBrandingManager',
    
    # Specialized Reports
    'AnalyticsReportGenerator',
    'PowerPointGenerator',
    
    # Professional Page Templates
    'TitlePageTemplate',
    'create_title_page',
    'TableOfContentsTemplate',
    'create_table_of_contents',
    'generate_sections_from_report_structure',
    'ContentPageTemplate',
    'create_content_page'
]

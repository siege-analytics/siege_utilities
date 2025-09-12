"""
Reporting utilities for siege_utilities package.
Comprehensive PDF and PowerPoint report generation with client branding.
"""

from pathlib import Path
from .base_template import BaseReportTemplate
from .report_generator import ReportGenerator
from .chart_generator import ChartGenerator, create_bar_chart, create_line_chart, create_scatter_plot, create_pie_chart, create_heatmap
from .client_branding import ClientBrandingManager
from .analytics_reports import AnalyticsReportGenerator
from .powerpoint_generator import PowerPointGenerator

# Profile-integrated reporting functions
def get_report_output_directory(client_code: str = None) -> Path:
    """
    Get the appropriate output directory for reports based on profile system.
    
    Args:
        client_code: Client code for client-specific directory
        
    Returns:
        Path to the report output directory
    """
    from pathlib import Path
    try:
        from ..config.enhanced_config import get_download_directory
        base_dir = get_download_directory(client_code)
        return base_dir / "reports"
    except ImportError:
        # Fallback to default
        return Path.cwd() / "reports"

def create_report_generator(client_name: str, client_code: str = None) -> ReportGenerator:
    """
    Create a ReportGenerator with profile-based output directory.
    
    Args:
        client_name: Name of the client
        client_code: Client code for profile-based directory
        
    Returns:
        Configured ReportGenerator instance
    """
    output_dir = get_report_output_directory(client_code)
    return ReportGenerator(client_name, output_dir)

def create_powerpoint_generator(client_name: str, client_code: str = None) -> PowerPointGenerator:
    """
    Create a PowerPointGenerator with profile-based output directory.
    
    Args:
        client_name: Name of the client
        client_code: Client code for profile-based directory
        
    Returns:
        Configured PowerPointGenerator instance
    """
    from pathlib import Path
    try:
        from ..config.enhanced_config import get_download_directory
        base_dir = get_download_directory(client_code)
        output_dir = base_dir / "presentations"
    except ImportError:
        # Fallback to default
        output_dir = Path.cwd() / "presentations"
    
    return PowerPointGenerator(client_name, output_dir)

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
    'create_pie_chart',
    'create_heatmap',
    
    # Branding and Customization
    'ClientBrandingManager',
    
    # Specialized Reports
    'AnalyticsReportGenerator',
    'PowerPointGenerator',
    
    # Profile-integrated functions
    'get_report_output_directory',
    'create_report_generator',
    'create_powerpoint_generator',
    
    # Professional Page Templates
    'TitlePageTemplate',
    'create_title_page',
    'TableOfContentsTemplate',
    'create_table_of_contents',
    'generate_sections_from_report_structure',
    'ContentPageTemplate',
    'create_content_page'
]

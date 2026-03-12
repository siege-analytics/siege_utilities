"""
Reporting utilities — lazy-loaded.

Comprehensive PDF and PowerPoint report generation with client branding.
All submodules load on first attribute access via PEP 562 __getattr__.
"""

import importlib
import logging
import sys
from pathlib import Path

log = logging.getLogger(__name__)

_LAZY_IMPORTS = {}


def _register(names, module):
    for name in names:
        _LAZY_IMPORTS[name] = module


_register(['BaseReportTemplate'], '.templates.base_template')
_register(['ReportGenerator'], '.report_generator')
_register([
    'ChartGenerator', 'create_bar_chart', 'create_line_chart',
    'create_scatter_plot', 'create_pie_chart', 'create_heatmap',
    'create_choropleth_map', 'create_bivariate_choropleth',
    'create_marker_map', 'create_flow_map', 'create_convergence_diagram',
    'create_dashboard',
    'create_dataframe_summary_charts', 'generate_chart_from_dataframe',
], '.chart_generator')
_register(['ClientBrandingManager'], '.client_branding')
_register(['AnalyticsReportGenerator'], '.analytics.analytics_reports')
_register(['PowerPointGenerator'], '.powerpoint_generator')
_register(['decode_rl_image', 'show_rl_image', 'save_rl_image'], '.image_utils')
_register(['ChartTypeRegistry'], '.chart_types')
_register(['PollingAnalyzer'], '.analytics.polling_analyzer')

# IDML (InDesign) export
_register(['IDMLExporter', 'export_report_idml', 'SIMPLEIDML_AVAILABLE'], '.idml_export')

# 3D map rendering (pydeck / deck.gl)
_register([
    'ThreeDMapRenderer', 'PYDECK_AVAILABLE',
    'create_3d_hexbin', 'create_3d_columns',
], '.map_3d')

# Professional page templates
_register(['TitlePageTemplate', 'create_title_page'], '.templates.title_page_template')
_register([
    'TableOfContentsTemplate', 'create_table_of_contents',
    'generate_sections_from_report_structure',
], '.templates.table_of_contents_template')
_register(['ContentPageTemplate', 'create_content_page'], '.templates.content_page_template')

__all__ = [
    'BaseReportTemplate', 'ReportGenerator', 'ChartGenerator',
    'create_bar_chart', 'create_line_chart', 'create_scatter_plot',
    'create_pie_chart', 'create_heatmap',
    'create_convergence_diagram',
    'ClientBrandingManager', 'AnalyticsReportGenerator', 'PowerPointGenerator',
    'get_report_output_directory', 'create_report_generator', 'create_powerpoint_generator',
    'export_branding_config', 'import_branding_config', 'export_chart_type_config',
    'decode_rl_image', 'show_rl_image', 'save_rl_image',
    'TitlePageTemplate', 'create_title_page',
    'TableOfContentsTemplate', 'create_table_of_contents',
    'generate_sections_from_report_structure',
    'ContentPageTemplate', 'create_content_page',
    'ThreeDMapRenderer', 'PYDECK_AVAILABLE',
    'create_3d_hexbin', 'create_3d_columns',
    'IDMLExporter', 'export_report_idml', 'SIMPLEIDML_AVAILABLE',
]


def __getattr__(name):
    if name in _LAZY_IMPORTS:
        mod = importlib.import_module(_LAZY_IMPORTS[name], __package__)
        val = getattr(mod, name)
        setattr(sys.modules[__name__], name, val)
        return val
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__():
    return sorted(set(list(globals().keys()) + list(_LAZY_IMPORTS.keys())))


# Profile-integrated reporting functions (defined here, use lazy internal imports)

def get_report_output_directory(client_code: str = None) -> Path:
    """Get the appropriate output directory for reports based on profile system."""
    try:
        from ..config.enhanced_config import get_download_directory
        import os
        username = os.environ.get('SIEGE_USERNAME', os.environ.get('USER', 'default'))
        base_dir = get_download_directory(username)
        if client_code:
            return base_dir / client_code / "reports"
        return base_dir / "reports"
    except ImportError:
        return Path.cwd() / "reports"


def create_report_generator(client_name: str, client_code: str = None):
    """Create a ReportGenerator with profile-based output directory."""
    from .report_generator import ReportGenerator as _RG
    output_dir = get_report_output_directory(client_code)
    return _RG(client_name, output_dir)


def create_powerpoint_generator(client_name: str, client_code: str = None):
    """Create a PowerPointGenerator with profile-based output directory."""
    from .powerpoint_generator import PowerPointGenerator as _PG
    try:
        from ..config.enhanced_config import get_download_directory
        import os
        username = os.environ.get('SIEGE_USERNAME', os.environ.get('USER', 'default'))
        base_dir = get_download_directory(username)
        if client_code:
            output_dir = base_dir / client_code / "presentations"
        else:
            output_dir = base_dir / "presentations"
    except ImportError:
        output_dir = Path.cwd() / "presentations"
    return _PG(client_name, output_dir)


def export_branding_config(client_name: str, export_path: str) -> bool:
    """Export client branding configuration to a file."""
    try:
        from .client_branding import ClientBrandingManager as _CBM
        branding_manager = _CBM()
        return branding_manager.export_branding_config(client_name, Path(export_path))
    except Exception as e:
        log.error(f"Failed to export branding config: {e}")
        return False


def import_branding_config(import_path: str, client_name: str = None) -> bool:
    """Import client branding configuration from a file."""
    try:
        from .client_branding import ClientBrandingManager as _CBM
        branding_manager = _CBM()
        return branding_manager.import_branding_config(Path(import_path), client_name)
    except Exception as e:
        log.error(f"Failed to import branding config: {e}")
        return False


def export_chart_type_config(chart_type_name: str, output_path: str) -> bool:
    """Export chart type configuration to a file."""
    try:
        from .chart_types import ChartTypeRegistry as _CTR
        chart_registry = _CTR()
        chart_registry.export_chart_type_config(chart_type_name, output_path)
        return True
    except Exception as e:
        log.error(f"Failed to export chart type config: {e}")
        return False

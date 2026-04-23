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
_register(['AnalyticsReportGenerator'], '.analytics_reports')
_register(['PowerPointGenerator'], '.powerpoint_generator')
_register(['decode_rl_image', 'show_rl_image', 'save_rl_image'], '.image_utils')
_register(['ChartTypeRegistry'], '.chart_types')
_register(['PollingAnalyzer'], '.analytics.polling_analyzer')
_register(['Argument', 'TableType'], '.pages.page_models')

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


class ReportingConfigError(RuntimeError):
    """Raised when a reporting configuration export / import cannot complete."""


def export_branding_config(client_name: str, export_path: str) -> bool:
    """Export client branding configuration to a file.

    Parameters
    ----------
    client_name : str
        Name of the client whose branding should be exported.
    export_path : str
        Destination path for the export.

    Returns
    -------
    bool
        True on success. (Never returns False — failures raise.)

    Raises
    ------
    ReportingConfigError
        On any failure — OS error writing the file, missing client, etc.
    """
    try:
        from .client_branding import ClientBrandingManager as _CBM
        branding_manager = _CBM()
        return branding_manager.export_branding_config(client_name, Path(export_path))
    except (OSError, ValueError, KeyError) as e:
        log.error(
            "export_branding_config failed (client=%s, path=%s): %s",
            client_name, export_path, e,
        )
        raise ReportingConfigError(
            f"failed to export branding for client={client_name!r} to {export_path!r}"
        ) from e


def import_branding_config(import_path: str, client_name: str = None) -> bool:
    """Import client branding configuration from a file.

    Parameters
    ----------
    import_path : str
        Source file to read branding from.
    client_name : str, optional
        Client to associate with the imported branding. When omitted, the
        implementation picks a name from the file.

    Returns
    -------
    bool
        True on success.

    Raises
    ------
    ReportingConfigError
        On any failure — file missing, parse error, client collision.
    """
    try:
        from .client_branding import ClientBrandingManager as _CBM
        branding_manager = _CBM()
        return branding_manager.import_branding_config(Path(import_path), client_name)
    except (OSError, ValueError, KeyError) as e:
        log.error(
            "import_branding_config failed (path=%s, client=%s): %s",
            import_path, client_name, e,
        )
        raise ReportingConfigError(
            f"failed to import branding from {import_path!r} (client={client_name!r})"
        ) from e


def export_chart_type_config(chart_type_name: str, output_path: str) -> bool:
    """Export chart type configuration to a file.

    Parameters
    ----------
    chart_type_name : str
        Name of the chart type (must exist in the registry).
    output_path : str
        Destination file path.

    Returns
    -------
    bool
        True on success.

    Raises
    ------
    ReportingConfigError
        On any failure — unknown chart type, OS error writing.
    """
    try:
        from .chart_types import ChartTypeRegistry as _CTR
        chart_registry = _CTR()
        chart_registry.export_chart_type_config(chart_type_name, output_path)
        return True
    except (OSError, ValueError, KeyError) as e:
        log.error(
            "export_chart_type_config failed (chart_type=%s, path=%s): %s",
            chart_type_name, output_path, e,
        )
        raise ReportingConfigError(
            f"failed to export chart type {chart_type_name!r} to {output_path!r}"
        ) from e

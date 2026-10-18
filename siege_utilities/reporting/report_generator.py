"""
Main report generator for siege_utilities reporting system.
Orchestrates the creation of comprehensive reports with charts, tables, and branding.
"""

import logging
import os
import uuid
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
import pandas as pd

# Try to import PIL Image, fall back to Any if not available
try:
    from PIL import Image
    ImageType = Image.Image
except ImportError:
    ImageType = Any

# ReportLab imports for PDF generation
try:
    from reportlab.platypus import Paragraph, Spacer, Table, TableStyle, PageBreak
    from reportlab.platypus import Image as RLImage
    from reportlab.platypus.tableofcontents import TableOfContents
    from reportlab.lib import colors
    from reportlab.lib.units import inch
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False
    Paragraph = None
    Spacer = None
    Table = None
    TableStyle = None
    PageBreak = None
    RLImage = None
    TableOfContents = None
    colors = None
    inch = None

from ._markup import _escape_paragraph
from .templates.base_template import BaseReportTemplate
from .chart_generator import ChartGenerator
from .client_branding import ClientBrandingManager, ClientBrandingNotFoundError

log = logging.getLogger(__name__)

__all__ = [
    "ReportGenerator",
]


class ReportGenerator:
    """
    Main report generator that creates comprehensive reports.
    Integrates templates, charts, and data sources.
    """

    def __init__(self, client_name: str, output_dir: Optional[Path] = None):
        """
        Initialize the report generator.
        
        Args:
            client_name: Name of the client for branding
            output_dir: Directory for output reports
        """
        self.client_name = client_name
        self.output_dir = output_dir or Path.cwd() / "reports"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.branding_manager = ClientBrandingManager()
        try:
            self.branding_config = self.branding_manager.get_client_branding(client_name)
        except ClientBrandingNotFoundError:
            log.warning(f"No branding configuration found for {client_name}, using defaults")
            self.branding_config = {}
        
        self.chart_generator = ChartGenerator(
            self.branding_config, output_dir=self.output_dir,
            max_chart_width=6.0, max_chart_height=8.5,
        )

    def create_analytics_report(self, title: str, charts: List[ImageType], 
                               data_summary: str = "", insights: List[str] = None,
                               recommendations: List[str] = None, 
                               executive_summary: str = None,
                               methodology: str = None) -> Dict[str, Any]:
        """
        Create a comprehensive analytics report with multiple sections.
        
        Args:
            title: Report title
            charts: List of chart images
            data_summary: Summary of the data analyzed
            insights: List of key insights
            recommendations: List of actionable recommendations
            executive_summary: Executive summary text
            methodology: Methodology description
            
        Returns:
            Dictionary containing report content structure
        """
        insights = insights or []
        recommendations = recommendations or []
        
        report_content = {
            'title': title,
            'type': 'analytics_report',
            'sections': [],
            'metadata': {
                'created_date': datetime.now().isoformat(),
                'total_charts': len(charts),
                'total_insights': len(insights),
                'total_recommendations': len(recommendations)
            }
        }
        
        # Add executive summary if provided
        if executive_summary:
            report_content['sections'].append({
                'type': 'executive_summary',
                'title': 'Executive Summary',
                'content': executive_summary,
                'level': 1
            })
        
        # Add methodology if provided
        if methodology:
            report_content['sections'].append({
                'type': 'methodology',
                'title': 'Methodology',
                'content': methodology,
                'level': 1
            })
        
        # Add data summary
        if data_summary:
            report_content['sections'].append({
                'type': 'data_summary',
                'title': 'Data Summary',
                'content': data_summary,
                'level': 1
            })
        
        # Add insights section
        if insights:
            report_content['sections'].append({
                'type': 'insights',
                'title': 'Key Insights',
                'content': insights,
                'level': 1
            })
        
        # Add recommendations section
        if recommendations:
            report_content['sections'].append({
                'type': 'recommendations',
                'title': 'Recommendations',
                'content': recommendations,
                'level': 1
            })
        
        # Add charts section
        if charts:
            report_content['sections'].append({
                'type': 'charts',
                'title': 'Data Visualizations',
                'content': charts,
                'level': 1
            })
        
        return report_content

    def create_comprehensive_report(self, title: str, author: str = None,
                                  client: str = None, report_type: str = "analysis",
                                  sections: List[Dict] = None,
                                  appendices: List[Dict] = None,
                                  table_of_contents: bool = True,
                                  page_numbers: bool = True,
                                  header_footer: bool = True) -> Dict[str, Any]:
        """
        Create a comprehensive report with full document structure.
        
        Args:
            title: Report title
            author: Report author
            client: Client name
            report_type: Type of report
            sections: List of report sections
            appendices: List of appendices
            table_of_contents: Include table of contents
            page_numbers: Include page numbers
            header_footer: Include headers and footers
            
        Returns:
            Dictionary containing complete report structure
        """
        sections = sections or []
        appendices = appendices or []
        
        report_structure = {
            'title': title,
            'type': 'comprehensive_report',
            'metadata': {
                'author': author or 'Siege Analytics',
                'client': client,
                'report_type': report_type,
                'created_date': datetime.now().isoformat(),
                'version': '1.0'
            },
            'document_structure': {
                'table_of_contents': table_of_contents,
                'page_numbers': page_numbers,
                'header_footer': header_footer
            },
            'sections': [
                {
                    'type': 'title_page',
                    'title': title,
                    'subtitle': f"{report_type.title()} Report",
                    'author': author or 'Siege Analytics',
                    'client': client,
                    'date': datetime.now().strftime('%B %d, %Y'),
                    'level': 0
                }
            ]
        }
        
        # Add table of contents if requested
        if table_of_contents:
            report_structure['sections'].append({
                'type': 'table_of_contents',
                'title': 'Table of Contents',
                'level': 0
            })
        
        # Add main sections
        for section in sections:
            section['level'] = section.get('level', 1)
            report_structure['sections'].append(section)
        
        # Add appendices if provided
        if appendices:
            report_structure['sections'].append({
                'type': 'appendix_header',
                'title': 'Appendices',
                'level': 0
            })
            
            for i, appendix in enumerate(appendices, 1):
                appendix['level'] = appendix.get('level', 1)
                appendix['appendix_number'] = i
                report_structure['sections'].append(appendix)
        
        return report_structure

    def add_section(self, report_content: Dict[str, Any], section_type: str,
                    title: str, content: Any, level: int = 1,
                    page_break_before: bool = False,
                    page_break_after: bool = False) -> Dict[str, Any]:
        """
        Add a new section to an existing report.
        
        Args:
            report_content: Existing report content
            section_type: Type of section
            title: Section title
            content: Section content
            level: Section level (0=main, 1=section, 2=subsection)
            page_break_before: Add page break before section
            page_break_after: Add page break after section
            
        Returns:
            Updated report content
        """
        new_section = {
            'type': section_type,
            'title': title,
            'content': content,
            'level': level,
            'page_break_before': page_break_before,
            'page_break_after': page_break_after
        }
        
        if 'sections' not in report_content:
            report_content['sections'] = []
        
        report_content['sections'].append(new_section)
        return report_content

    def add_table_section(self, report_content: Dict[str, Any], title: str,
                          table_data: Union[List[List], List[Dict[str, Any]], pd.DataFrame],
                          headers: List[str] = None, level: int = 1,
                          table_style: str = "default",
                          sort_by: Optional[Union[int, str]] = None,
                          sort_order: str = "asc") -> Dict[str, Any]:
        """
        Add a table section to the report.

        Args:
            report_content: Existing report content
            title: Section title
            table_data: Table data (rows, record dictionaries or DataFrame)
            headers: Column headers
            level: Section level
            table_style: Table styling
            sort_by: Column index or header name to sort by.
                None preserves existing order.
            sort_order: ``'asc'`` or ``'desc'``.

        Returns:
            Updated report content
        """
        from siege_utilities.reporting.table_utils import sort_table_data

        # Record dictionaries are used by the reporting notebook and need
        # column-aligned values, rather than iteration over dictionary keys.
        if isinstance(table_data, list) and table_data and isinstance(table_data[0], dict):
            if not all(isinstance(row, dict) for row in table_data):
                raise ValueError("Table section records must all be dictionaries")
            table_data = pd.DataFrame(table_data, columns=headers)

        # Convert DataFrame to list format if needed
        if hasattr(table_data, 'to_dict'):
            if headers is None:
                headers = table_data.columns.tolist()
            table_data = [headers] + table_data.values.tolist()
        elif headers and table_data:
            table_data = [headers] + table_data

        if sort_by is not None:
            table_data = sort_table_data(
                table_data, sort_by=sort_by, sort_order=sort_order
            )

        content = {
            'data': table_data,
            'headers': headers,
            'style': table_style
        }

        return self.add_section(report_content, 'table', title, content, level)

    def add_text_section(self, report_content: Dict[str, Any], title: str,
                         text_content: str, level: int = 1,
                         text_style: str = "body") -> Dict[str, Any]:
        """
        Add a text section to the report.
        
        Args:
            report_content: Existing report content
            title: Section title
            text_content: Text content
            level: Section level
            text_style: Text styling
            
        Returns:
            Updated report content
        """
        return self.add_section(report_content, 'text', title, text_content, level)

    def add_chart_section(self, report_content: Dict[str, Any], title: str,
                          charts: List[ImageType], description: str = "",
                          level: int = 1, layout: str = "vertical") -> Dict[str, Any]:
        """
        Add a chart section to the report.
        
        Args:
            report_content: Existing report content
            title: Section title
            charts: List of chart images
            description: Section description
            level: Section level
            layout: Chart layout ('vertical', 'horizontal', 'grid')
            
        Returns:
            Updated report content
        """
        content = {
            'charts': charts,
            'description': description,
            'layout': layout
        }

        return self.add_section(report_content, 'charts', title, content, level)

    def add_map_section(self, report_content: Dict[str, Any], title: str,
                        maps: List[ImageType], map_type: str = "choropleth",
                        description: str = "", level: int = 1) -> Dict[str, Any]:
        """
        Add a map section to the report.
        
        Args:
            report_content: Existing report content
            title: Section title
            maps: List of map images
            map_type: Type of maps
            description: Section description
            level: Section level
            
        Returns:
            Updated report content
        """
        content = {
            'maps': maps,
            'map_type': map_type,
            'description': description
        }

        return self.add_section(report_content, 'maps', title, content, level)

    def add_appendix(self, report_content: Dict[str, Any], title: str,
                     content: Any, appendix_type: str = "data",
                     level: int = 1) -> Dict[str, Any]:
        """
        Add an appendix to the report.
        
        Args:
            report_content: Existing report content
            title: Appendix title
            content: Appendix content
            appendix_type: Type of appendix
            level: Section level
            
        Returns:
            Updated report content
        """
        return self.add_section(report_content, 'appendix', title, content, level)

    def _get_template(self, output_path: str, template_config: Optional[str] = None) -> 'BaseReportTemplate':
        """
        Create a report template for PDF generation.

        Args:
            output_path: Output PDF file path
            template_config: Optional path to template configuration file

        Returns:
            BaseReportTemplate instance
        """
        from .templates.base_template import BaseReportTemplate

        config_path = Path(template_config) if template_config else None
        return BaseReportTemplate(
            output_filename=output_path,
            branding_config_path=config_path
        )

    def generate_pdf_report(self, report_content: Dict[str, Any],
                           output_path: str, template_config: str = None) -> None:
        """
        Generate a comprehensive PDF report with full document structure.

        Args:
            report_content: Report content structure
            output_path: Output PDF file path
            template_config: Template configuration file path

        Raises:
            OSError: If the output directory cannot be created or is not writable,
                or if the final rename fails.
        """
        final = Path(output_path)
        parent = final.parent if str(final.parent) else Path(".")
        parent.mkdir(parents=True, exist_ok=True)
        if not os.access(parent, os.W_OK):
            raise OSError(
                f"generate_pdf_report: output directory {parent} is not writable"
            )

        tmp_path = parent / f".{final.name}.{uuid.uuid4().hex[:8]}.part"

        try:
            template = self._get_template(str(tmp_path), template_config)

            story = []

            metadata = report_content.get('metadata', {})
            sections = report_content.get('sections', [])
            title = metadata.get('title') or report_content.get('title')
            if title and not any(section.get('type') == 'title_page' for section in sections):
                title_flowables = template.add_title_page(
                    title=title,
                    subtitle=metadata.get('subtitle', ''),
                    author=metadata.get('author', ''),
                    date=metadata.get('date', ''),
                    client=metadata.get('client', '')
                )
                story.extend(title_flowables)

            for section in sections:
                section_story = self._build_section_content(section, template)
                story.extend(section_story)

                if section.get('page_break_after', False):
                    story.append(PageBreak())

            if not any(hasattr(flowable, '_toc_entry') for flowable in story):
                for index, flowable in enumerate(story):
                    if isinstance(flowable, TableOfContents):
                        log.warning("Table of contents has no titled report sections")
                        story[index] = Paragraph("No sections.", template.styles['Normal'])

            template.build_document(story)

            try:
                os.replace(tmp_path, final)
            except OSError as exc:
                try:
                    if tmp_path.exists():
                        tmp_path.unlink()
                except OSError:
                    pass
                raise OSError(
                    f"generate_pdf_report: built {tmp_path} but could not "
                    f"rename to {final}: {exc}"
                ) from exc

        except BaseException:
            try:
                if tmp_path.exists():
                    tmp_path.unlink()
            except OSError:
                pass
            raise

        log.info(f"PDF report generated successfully: {output_path}")

    def _process_chart_list(self, charts: List[Any], width: float = 6,
                             height: float = 4) -> List:
        """
        Process a list of charts in various formats into ReportLab Image objects.

        Supported formats:
        - File path (str or Path)
        - matplotlib Figure object
        - PIL Image object
        - BytesIO object containing image data
        - ReportLab Flowable (passed through)

        Args:
            charts: List of chart objects in various formats
            width: Image width in inches
            height: Image height in inches

        Returns:
            List of ReportLab Image flowables
        """
        if not REPORTLAB_AVAILABLE:
            raise ImportError(
                "ReportLab is required to process charts. "
                "Install with: pip install reportlab"
            )

        import io

        result = []

        for chart in charts:
            try:
                # Handle ReportLab flowables (pass through)
                if hasattr(chart, 'drawOn'):
                    result.append(chart)
                    continue

                # Handle file paths
                if isinstance(chart, (str, Path)):
                    chart_path = Path(chart)
                    if chart_path.exists():
                        img = RLImage(str(chart_path), width=width*inch, height=height*inch)
                        result.append(img)
                    else:
                        log.warning("Chart image does not exist: %s", chart_path)
                    continue

                # Handle matplotlib Figure
                if hasattr(chart, 'savefig'):
                    # Always close the figure and the buffer, even on
                    # savefig() exceptions — long-running pipelines that
                    # raise mid-render were leaking the entire figure
                    # graph until interpreter exit.
                    buf = io.BytesIO()
                    try:
                        chart.savefig(buf, format='png', dpi=150, bbox_inches='tight')
                        buf.seek(0)
                        img = RLImage(buf, width=width*inch, height=height*inch)
                        result.append(img)
                    finally:
                        try:
                            import matplotlib.pyplot as plt
                            plt.close(chart)
                        except (ValueError, TypeError, AttributeError) as exc:
                            log.debug("Could not close matplotlib figure: %s", exc)
                        # The BytesIO is now referenced by the RLImage —
                        # ReportLab keeps a handle for the build pass and
                        # closes it itself. Nothing to do here.
                    continue

                # Handle PIL Image
                if hasattr(chart, 'save') and hasattr(chart, 'mode'):
                    # PIL Image
                    buf = io.BytesIO()
                    chart.save(buf, format='PNG')
                    buf.seek(0)
                    img = RLImage(buf, width=width*inch, height=height*inch)
                    result.append(img)
                    continue

                # Handle BytesIO
                if isinstance(chart, io.BytesIO):
                    chart.seek(0)
                    img = RLImage(chart, width=width*inch, height=height*inch)
                    result.append(img)
                    continue

                # Handle dict with image_path
                if isinstance(chart, dict):
                    image_path = chart.get('image_path') or chart.get('path')
                    if image_path and Path(image_path).exists():
                        chart_width = chart.get('width', width)
                        chart_height = chart.get('height', height)
                        img = RLImage(str(image_path), width=chart_width*inch,
                                     height=chart_height*inch)
                        result.append(img)
                    else:
                        log.warning("Chart has no existing image path: %r", chart)
                    continue

                log.warning(f"Unknown chart type: {type(chart)}")

            except (ValueError, TypeError, KeyError, IndexError, AttributeError, OSError) as e:
                log.error(f"Error processing chart: {e}")

        return result

    def _build_section_content(self, section: Dict[str, Any],
                              template) -> List:
        """
        Build ReportLab content for a section.

        Args:
            section: Section dictionary
            template: Report template (BaseReportTemplate with styles)

        Returns:
            List of ReportLab flowables
        """
        if not REPORTLAB_AVAILABLE:
            raise ImportError(
                "ReportLab is required to build report sections. "
                "Install with: pip install reportlab"
            )

        story = []
        section_type = section.get('type', 'text')
        styles = template.styles
        content = section.get('content')
        text_types = {'text', 'executive_summary', 'methodology', 'data_summary', 'appendix'}
        supported_types = text_types | {
            'insights', 'recommendations', 'title_page', 'table_of_contents',
            'appendix_header', 'table', 'chart', 'charts', 'map', 'maps',
        }
        if section_type not in supported_types:
            raise ValueError(f"Unknown report section type: {section_type!r}")

        def invalid_content(expected):
            raise ValueError(f"Invalid content for {section_type!r} section: expected {expected}")

        # Add page break if requested
        if section.get('page_break_before', False) or section_type == 'appendix_header':
            story.append(PageBreak())

        if section_type == 'title_page':
            fields = ('title', 'subtitle', 'author', 'client', 'date')
            if content is not None or any(
                section.get(field) is not None and not isinstance(section[field], str)
                for field in fields
            ):
                invalid_content('title, subtitle, author, client and date strings on the section')
            if not (section.get('title') or '').strip():
                invalid_content('a nonempty title')
            story.extend(template.add_title_page(**{field: section.get(field) or '' for field in fields}))
            return story

        # Add section title
        title = section.get('title', '')
        level = section.get('level', 1)
        if title:
            heading_style = styles.get(f'Heading{level}', styles['Heading1'])
            heading = Paragraph(_escape_paragraph(title), heading_style)
            if section_type != 'table_of_contents':
                heading._toc_entry = (max(0, level - 1), _escape_paragraph(title))
            story.append(heading)
            story.append(Spacer(1, 12))

        # Handle different section types
        if section_type in text_types:
            text = content.get('text') if isinstance(content, dict) else content
            if not isinstance(text, str):
                invalid_content('a string or a mapping with a text string')
            if not text.strip():
                log.warning("Empty content for %s section %r", section_type, title)
            if text:
                # Split on newlines and create separate paragraphs to preserve formatting
                for line in text.split('\n'):
                    stripped = line.strip()
                    if not stripped:
                        story.append(Spacer(1, 6))
                    elif stripped.startswith('- ') or stripped.startswith('* '):
                        # Bullet point — escape user text before concatenating
                        # the literal ``&bull;`` entity. ReportLab's mini-HTML
                        # parser treats ``<`` and ``&`` as markup; raw user
                        # text containing ``<3`` or ``Q&A`` would otherwise
                        # raise a parse error mid-render.
                        bullet_text = _escape_paragraph(stripped[2:])
                        story.append(Paragraph(f'&bull; {bullet_text}', styles['Normal']))
                    else:
                        story.append(Paragraph(_escape_paragraph(stripped), styles['Normal']))
            story.append(Spacer(1, 12))

        elif section_type in {'insights', 'recommendations'}:
            if not isinstance(content, list) or not all(isinstance(item, str) and item.strip() for item in content):
                invalid_content('a list of nonempty strings')
            if not content:
                log.warning("Empty content for %s section %r", section_type, title)
            for item in content:
                story.append(Paragraph(_escape_paragraph(item), styles['Bullet'], bulletText='\u2022'))
            story.append(Spacer(1, 12))

        elif section_type == 'table_of_contents':
            if content is not None:
                invalid_content('automatically generated entries, without explicit content')
            story.extend([TableOfContents(), PageBreak()])

        elif section_type == 'appendix_header':
            if content is not None:
                invalid_content('an appendix divider without content')
            if not title:
                invalid_content('an appendix divider title')

        elif section_type == 'table':
            if not isinstance(content, dict):
                invalid_content('a mapping with table data')
            table_data = content.get('data')
            headers = content.get('headers')
            if headers is not None and not isinstance(headers, list):
                invalid_content('a list of column headers')

            if isinstance(table_data, pd.DataFrame):
                headers = headers or table_data.columns.tolist()
                table_data = [headers] + table_data.values.tolist()
            else:
                if not isinstance(table_data, list) or not all(isinstance(row, (list, tuple)) for row in table_data):
                    invalid_content('a list of rows or a DataFrame')
                if headers and table_data and table_data[0] != headers:
                    # add_table_section already prepends headers.
                    table_data = [headers] + table_data

            if table_data:
                table = Table(table_data, repeatRows=1 if headers else 0)
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 10),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                    ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
                    ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                    ('FONTSIZE', (0, 1), (-1, -1), 9),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ]))
                story.append(table)
                story.append(Spacer(1, 12))
            else:
                log.warning("Empty content for table section %r", title)

        elif section_type in {'chart', 'charts', 'map', 'maps'}:
            key = 'maps' if section_type in {'map', 'maps'} else 'charts'
            description = ''
            if key == 'charts' and isinstance(content, list):
                charts = content
            elif isinstance(content, dict):
                charts = content.get(key, [])
                description = content.get('description', '')
                if not isinstance(charts, list):
                    invalid_content(f'a list under {key!r}')
                if key == 'charts' and content.get('image_path'):
                    charts = [content['image_path']] + charts
            else:
                invalid_content('a chart list or an image mapping' if key == 'charts' else 'a maps mapping')
            if not isinstance(description, str):
                invalid_content('a string description')

            if description:
                story.append(Paragraph(_escape_paragraph(description), styles['Normal']))
                story.append(Spacer(1, 8))

            chart_images = self._process_chart_list(charts)
            if not chart_images:
                log.warning("No renderable images for %s section %r", section_type, title)
            for chart_img in chart_images:
                story.append(chart_img)
                story.append(Spacer(1, 12))

        return story

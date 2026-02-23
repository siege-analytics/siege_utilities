"""
Main report generator for siege_utilities reporting system.
Orchestrates the creation of comprehensive reports with charts, tables, and branding.
"""

import logging
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
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib import colors
    from reportlab.lib.units import inch
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False
    PageBreak = None  # Define for type hints

from .templates.base_template import BaseReportTemplate
from .chart_generator import ChartGenerator
from .client_branding import ClientBrandingManager

log = logging.getLogger(__name__)

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
        
        # Initialize components
        self.branding_manager = ClientBrandingManager()
        self.branding_config = self.branding_manager.get_client_branding(client_name)
        
        if not self.branding_config:
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
                          table_data: Union[List[List], pd.DataFrame],
                          headers: List[str] = None, level: int = 1,
                          table_style: str = "default") -> Dict[str, Any]:
        """
        Add a table section to the report.
        
        Args:
            report_content: Existing report content
            title: Section title
            table_data: Table data (list of lists or DataFrame)
            headers: Column headers
            level: Section level
            table_style: Table styling
            
        Returns:
            Updated report content
        """
        # Convert DataFrame to list format if needed
        if hasattr(table_data, 'to_dict'):
            if headers is None:
                headers = table_data.columns.tolist()
            table_data = [headers] + table_data.values.tolist()
        elif headers and table_data:
            table_data = [headers] + table_data
        
        table_section = {
            'type': 'table',
            'title': title,
            'content': {
                'data': table_data,
                'headers': headers,
                'style': table_style
            },
            'level': level
        }
        
        return self.add_section(report_content, 'table', title, table_section, level)

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
        text_section = {
            'type': 'text',
            'title': title,
            'content': {
                'text': text_content,
                'style': text_style
            },
            'level': level
        }
        
        return self.add_section(report_content, 'text', title, text_section, level)

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
        chart_section = {
            'type': 'charts',
            'title': title,
            'content': {
                'charts': charts,
                'description': description,
                'layout': layout
            },
            'level': level
        }
        
        return self.add_section(report_content, 'charts', title, chart_section, level)

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
        map_section = {
            'type': 'maps',
            'title': title,
            'content': {
                'maps': maps,
                'map_type': map_type,
                'description': description
            },
            'level': level
        }
        
        return self.add_section(report_content, 'maps', title, map_section, level)

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
        appendix_section = {
            'type': 'appendix',
            'title': title,
            'content': content,
            'appendix_type': appendix_type,
            'level': level
        }
        
        return self.add_section(report_content, 'appendix', title, appendix_section, level)

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
                           output_path: str, template_config: str = None) -> bool:
        """
        Generate a comprehensive PDF report with full document structure.
        
        Args:
            report_content: Report content structure
            output_path: Output PDF file path
            template_config: Template configuration file path
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Initialize template with output path
            template = self._get_template(output_path, template_config)

            # Build document content
            story = []

            # Add title page if metadata present
            metadata = report_content.get('metadata', {})
            if metadata.get('title'):
                title_flowables = template.add_title_page(
                    title=metadata.get('title', 'Report'),
                    subtitle=metadata.get('subtitle', ''),
                    author=metadata.get('author', ''),
                    date=metadata.get('date', '')
                )
                story.extend(title_flowables)

            # Process each section
            for section in report_content.get('sections', []):
                section_story = self._build_section_content(section, template)
                story.extend(section_story)

                # Add page breaks if requested
                if section.get('page_break_after', False):
                    story.append(PageBreak())

            # Build PDF using the template's build_document method
            template.build_document(story)

            log.info(f"PDF report generated successfully: {output_path}")
            return True

        except Exception as e:
            log.error(f"Error generating PDF report: {e}")
            return False

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
            return []

        import io
        import tempfile

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
                    continue

                # Handle matplotlib Figure
                if hasattr(chart, 'savefig'):
                    # matplotlib Figure
                    buf = io.BytesIO()
                    chart.savefig(buf, format='png', dpi=150, bbox_inches='tight')
                    buf.seek(0)
                    img = RLImage(buf, width=width*inch, height=height*inch)
                    result.append(img)
                    # Close the figure to free memory
                    try:
                        import matplotlib.pyplot as plt
                        plt.close(chart)
                    except:
                        pass
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
                    continue

                log.warning(f"Unknown chart type: {type(chart)}")

            except Exception as e:
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
            log.error("ReportLab not available - cannot build section content")
            return []

        story = []
        section_type = section.get('type', 'text')
        styles = template.styles

        # Add page break if requested
        if section.get('page_break_before', False):
            story.append(PageBreak())

        # Add section title
        title = section.get('title', '')
        level = section.get('level', 1)
        if title:
            heading_style = styles.get(f'Heading{level}', styles['Heading1'])
            story.append(Paragraph(title, heading_style))
            story.append(Spacer(1, 12))

        # Handle different section types
        if section_type == 'text':
            content = section.get('content', '')
            if isinstance(content, str):
                story.append(Paragraph(content, styles['Normal']))
            story.append(Spacer(1, 12))

        elif section_type == 'table':
            table_data = section.get('content', {}).get('data', [])
            headers = section.get('content', {}).get('headers')

            if isinstance(table_data, pd.DataFrame):
                headers = headers or table_data.columns.tolist()
                table_data = [headers] + table_data.values.tolist()
            elif headers:
                table_data = [headers] + table_data

            if table_data:
                table = Table(table_data)
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

        elif section_type == 'chart' or section_type == 'charts':
            content = section.get('content', {})
            charts = content.get('charts', [])
            image_path = content.get('image_path')
            description = content.get('description', '')
            layout = content.get('layout', 'vertical')

            # Add description if provided
            if description:
                story.append(Paragraph(description, styles['Normal']))
                story.append(Spacer(1, 8))

            # Handle single image path (legacy support)
            if image_path and Path(image_path).exists():
                img = RLImage(str(image_path), width=6*inch, height=4*inch)
                story.append(img)
                story.append(Spacer(1, 12))

            # Handle list of charts (new enhanced support)
            if charts:
                chart_images = self._process_chart_list(charts)
                for chart_img in chart_images:
                    story.append(chart_img)
                    story.append(Spacer(1, 12))

        elif section_type == 'maps' or section_type == 'map':
            content = section.get('content', {})
            maps = content.get('maps', [])
            description = content.get('description', '')

            if description:
                story.append(Paragraph(description, styles['Normal']))
                story.append(Spacer(1, 8))

            if maps:
                map_images = self._process_chart_list(maps)
                for map_img in map_images:
                    story.append(map_img)
                    story.append(Spacer(1, 12))

        else:
            # Default: treat as text
            content = section.get('content', '')
            if isinstance(content, str):
                story.append(Paragraph(content, styles['Normal']))
            elif isinstance(content, dict) and 'text' in content:
                story.append(Paragraph(content['text'], styles['Normal']))
            story.append(Spacer(1, 12))

        return story

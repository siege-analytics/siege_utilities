"""
Main report generator for siege_utilities reporting system.
Orchestrates the creation of comprehensive reports with charts, tables, and branding.
"""

import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
import pandas as pd

from .base_template import BaseReportTemplate
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
        
        self.chart_generator = ChartGenerator(self.branding_config)

    def create_analytics_report(self, title: str, charts: List[Image], 
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
                          charts: List[Image], description: str = "",
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
                        maps: List[Image], map_type: str = "choropleth",
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
            # Initialize template
            template = self._get_template(template_config)
            
            # Create PDF document
            doc = template.create_document(report_content)
            
            # Build document content
            story = []
            
            # Process each section
            for section in report_content.get('sections', []):
                section_story = self._build_section_content(section, template)
                story.extend(section_story)
                
                # Add page breaks if requested
                if section.get('page_break_after', False):
                    story.append(PageBreak())
            
            # Build PDF
            doc.build(story)
            
            log.info(f"PDF report generated successfully: {output_path}")
            return True
            
        except Exception as e:
            log.error(f"Error generating PDF report: {e}")
            return False

    def _build_section_content(self, section: Dict[str, Any], 
                              template) -> List:
        """
        Build ReportLab content for a section.
        
        Args:
            section: Section dictionary
            template: Report template
            
        Returns:
            List of ReportLab flowables
        """
        story = []
        section_type = section.get('type', 'text')
        
        # Add page break if requested
        if section.get('page_break_before', False):
            story.append(PageBreak())
        
        # Handle different section types
        if section_type == 'title_page':
            story.extend(template.create_title_page(section))
        elif section_type == 'table_of_contents':
            story.extend(template.create_table_of_contents(section))
        elif section_type == 'table':
            story.extend(template.create_table_section(section))
        elif section_type == 'charts':
            story.extend(template.create_chart_section(section))
        elif section_type == 'maps':
            story.extend(template.create_map_section(section))
        elif section_type == 'text':
            story.extend(template.create_text_section(section))
        elif section_type == 'appendix':
            story.extend(template.create_appendix_section(section))
        else:
            # Default text section
            story.extend(template.create_text_section(section))
        
        return story

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

    def create_analytics_report(self, report_data: Dict[str, Any], 
                              report_title: str = "", 
                              include_charts: bool = True,
                              include_tables: bool = True) -> Path:
        """
        Create a comprehensive analytics report.
        
        Args:
            report_data: Dictionary containing report data
            report_title: Title of the report
            include_charts: Whether to include charts
            include_tables: Whether to include data tables
            
        Returns:
            Path to the generated PDF report
        """
        try:
            # Generate filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{self.client_name.lower().replace(' ', '_')}_analytics_report_{timestamp}.pdf"
            output_path = self.output_dir / filename
            
            # Create report template
            template = BaseReportTemplate(
                output_filename=str(output_path),
                branding_config_path=None,  # We'll pass config directly
                page_size="letter"
            )
            
            # Override branding config
            template.branding_config = self.branding_config
            
            # Generate report content
            story = self._generate_analytics_content(report_data, report_title, 
                                                  include_charts, include_tables)
            
            # Build document
            template.build_document(story)
            
            log.info(f"Analytics report created successfully: {output_path}")
            return output_path
            
        except Exception as e:
            log.error(f"Error creating analytics report: {e}")
            raise

    def create_performance_report(self, performance_data: Dict[str, Any],
                                metrics: List[str],
                                report_title: str = "") -> Path:
        """
        Create a performance metrics report.
        
        Args:
            performance_data: Dictionary containing performance metrics
            metrics: List of metrics to include
            report_title: Title of the report
            
        Returns:
            Path to the generated PDF report
        """
        try:
            # Generate filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{self.client_name.lower().replace(' ', '_')}_performance_report_{timestamp}.pdf"
            output_path = self.output_dir / filename
            
            # Create report template
            template = BaseReportTemplate(
                output_filename=str(output_path),
                branding_config_path=None,
                page_size="letter"
            )
            
            # Override branding config
            template.branding_config = self.branding_config
            
            # Generate performance report content
            story = self._generate_performance_content(performance_data, metrics, report_title)
            
            # Build document
            template.build_document(story)
            
            log.info(f"Performance report created successfully: {output_path}")
            return output_path
            
        except Exception as e:
            log.error(f"Error creating performance report: {e}")
            raise

    def create_custom_report(self, report_config: Dict[str, Any]) -> Path:
        """
        Create a custom report based on configuration.
        
        Args:
            report_config: Complete report configuration
            
        Returns:
            Path to the generated PDF report
        """
        try:
            # Generate filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_type = report_config.get('type', 'custom')
            filename = f"{self.client_name.lower().replace(' ', '_')}_{report_type}_report_{timestamp}.pdf"
            output_path = self.output_dir / filename
            
            # Create report template
            template = BaseReportTemplate(
                output_filename=str(output_path),
                branding_config_path=None,
                page_size=report_config.get('page_size', 'letter')
            )
            
            # Override branding config
            template.branding_config = self.branding_config
            
            # Generate custom report content
            story = self._generate_custom_content(report_config)
            
            # Build document
            template.build_document(story)
            
            log.info(f"Custom report created successfully: {output_path}")
            return output_path
            
        except Exception as e:
            log.error(f"Error creating custom report: {e}")
            raise

    def _generate_analytics_content(self, report_data: Dict[str, Any], 
                                  report_title: str, 
                                  include_charts: bool,
                                  include_tables: bool) -> List:
        """Generate content for analytics report."""
        story = []
        
        # Title page
        title = report_title or f"{self.client_name} Analytics Report"
        subtitle = f"Generated on {datetime.now().strftime('%B %d, %Y')}"
        story.extend(self._create_title_page(title, subtitle))
        
        # Executive Summary
        story.extend(self._create_executive_summary(report_data))
        
        # Key Metrics
        if 'metrics' in report_data:
            story.extend(self._create_metrics_section(report_data['metrics']))
        
        # Charts and Visualizations
        if include_charts and 'charts' in report_data:
            story.extend(self._create_charts_section(report_data['charts']))
        
        # Data Tables
        if include_tables and 'tables' in report_data:
            story.extend(self._create_tables_section(report_data['tables']))
        
        # Insights and Recommendations
        if 'insights' in report_data:
            story.extend(self._create_insights_section(report_data['insights']))
        
        return story

    def _generate_performance_content(self, performance_data: Dict[str, Any],
                                    metrics: List[str],
                                    report_title: str) -> List:
        """Generate content for performance report."""
        story = []
        
        # Title page
        title = report_title or f"{self.client_name} Performance Report"
        subtitle = f"Performance Metrics - {datetime.now().strftime('%B %d, %Y')}"
        story.extend(self._create_title_page(title, subtitle))
        
        # Performance Overview
        story.extend(self._create_performance_overview(performance_data))
        
        # Metrics Breakdown
        story.extend(self._create_metrics_breakdown(performance_data, metrics))
        
        # Performance Trends
        if 'trends' in performance_data:
            story.extend(self._create_trends_section(performance_data['trends']))
        
        # Recommendations
        if 'recommendations' in performance_data:
            story.extend(self._create_recommendations_section(performance_data['recommendations']))
        
        return story

    def _generate_custom_content(self, report_config: Dict[str, Any]) -> List:
        """Generate content for custom report."""
        story = []
        
        # Title page
        title = report_config.get('title', f"{self.client_name} Report")
        subtitle = report_config.get('subtitle', f"Generated on {datetime.now().strftime('%B %d, %Y')}")
        story.extend(self._create_title_page(title, subtitle))
        
        # Custom sections
        sections = report_config.get('sections', [])
        for section in sections:
            section_type = section.get('type', 'text')
            
            if section_type == 'text':
                story.extend(self._create_text_section(section))
            elif section_type == 'chart':
                story.extend(self._create_custom_chart_section(section))
            elif section_type == 'table':
                story.extend(self._create_custom_table_section(section))
            elif section_type == 'image':
                story.extend(self._create_image_section(section))
        
        return story

    def _create_title_page(self, title: str, subtitle: str = "") -> List:
        """Create a title page for the report."""
        from reportlab.platypus import Paragraph, Spacer, PageBreak
        from reportlab.lib.units import inch
        
        story = []
        
        # Main title
        story.append(Paragraph(title, self.chart_generator.styles['h1']))
        story.append(Spacer(1, 0.3 * inch))
        
        # Subtitle
        if subtitle:
            story.append(Paragraph(subtitle, self.chart_generator.styles['h2']))
            story.append(Spacer(1, 0.2 * inch))
        
        # Client info
        story.append(Paragraph(f"Client: {self.client_name}", self.chart_generator.styles['BodyText']))
        story.append(Spacer(1, 0.1 * inch))
        
        # Generated date
        story.append(Paragraph(f"Generated: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}", 
                             self.chart_generator.styles['BodyText']))
        story.append(Spacer(1, 0.3 * inch))
        
        # Page break
        story.append(PageBreak())
        
        return story

    def _create_executive_summary(self, report_data: Dict[str, Any]) -> List:
        """Create executive summary section."""
        from reportlab.platypus import Paragraph, Spacer
        from reportlab.lib.units import inch
        
        story = []
        
        story.append(Paragraph("Executive Summary", self.chart_generator.styles['h1']))
        story.append(Spacer(1, 0.2 * inch))
        
        summary = report_data.get('executive_summary', 'No executive summary provided.')
        story.append(Paragraph(summary, self.chart_generator.styles['BodyText']))
        story.append(Spacer(1, 0.3 * inch))
        
        return story

    def _create_metrics_section(self, metrics: Dict[str, Any]) -> List:
        """Create metrics section with key performance indicators."""
        from reportlab.platypus import Paragraph, Spacer, Table, TableStyle
        from reportlab.lib.units import inch
        from reportlab.lib import colors
        
        story = []
        
        story.append(Paragraph("Key Performance Indicators", self.chart_generator.styles['h2']))
        story.append(Spacer(1, 0.2 * inch))
        
        # Create metrics table
        if isinstance(metrics, dict):
            table_data = [["Metric", "Value", "Change", "Status"]]
            
            for metric_name, metric_data in metrics.items():
                if isinstance(metric_data, dict):
                    value = metric_data.get('value', 'N/A')
                    change = metric_data.get('change', 'N/A')
                    status = metric_data.get('status', 'N/A')
                else:
                    value = str(metric_data)
                    change = 'N/A'
                    status = 'N/A'
                
                table_data.append([metric_name, str(value), str(change), str(status)])
            
            # Create table
            table = Table(table_data, colWidths=[2*inch, 1.5*inch, 1.5*inch, 1*inch])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            
            story.append(table)
            story.append(Spacer(1, 0.3 * inch))
        
        return story

    def _create_charts_section(self, charts: List[Dict[str, Any]]) -> List:
        """Create charts section with visualizations."""
        from reportlab.platypus import Paragraph, Spacer, PageBreak
        from reportlab.lib.units import inch
        
        story = []
        
        story.append(Paragraph("Data Visualizations", self.chart_generator.styles['h2']))
        story.append(Spacer(1, 0.2 * inch))
        
        for i, chart_config in enumerate(charts):
            try:
                chart_type = chart_config.get('type', 'bar')
                title = chart_config.get('title', f'Chart {i+1}')
                data = chart_config.get('data', {})
                
                if chart_type == 'bar':
                    chart = self.chart_generator.create_bar_chart(
                        data.get('labels', []),
                        data.get('datasets', []),
                        title
                    )
                elif chart_type == 'line':
                    chart = self.chart_generator.create_line_chart(
                        data.get('labels', []),
                        data.get('datasets', []),
                        title
                    )
                elif chart_type == 'pie':
                    chart = self.chart_generator.create_pie_chart(
                        data.get('labels', []),
                        data.get('data', []),
                        title
                    )
                else:
                    continue
                
                # Add chart with caption
                story.extend(self.chart_generator.create_chart_with_caption(
                    chart, f"Figure {i+1}: {title}"
                ))
                
                # Add page break for large charts
                if i > 0 and i % 2 == 0:
                    story.append(PageBreak())
                    
            except Exception as e:
                log.error(f"Error creating chart {i+1}: {e}")
                continue
        
        return story

    def _create_tables_section(self, tables: List[Dict[str, Any]]) -> List:
        """Create tables section with data tables."""
        from reportlab.platypus import Paragraph, Spacer, Table, TableStyle, PageBreak
        from reportlab.lib.units import inch
        from reportlab.lib import colors
        
        story = []
        
        story.append(Paragraph("Data Tables", self.chart_generator.styles['h2']))
        story.append(Spacer(1, 0.2 * inch))
        
        for i, table_config in enumerate(tables):
            try:
                title = table_config.get('title', f'Table {i+1}')
                data = table_config.get('data', [])
                headers = table_config.get('headers', [])
                
                if not data:
                    continue
                
                # Add table title
                story.append(Paragraph(title, self.chart_generator.styles['h3']))
                story.append(Spacer(1, 0.1 * inch))
                
                # Prepare table data
                if headers:
                    table_data = [headers]
                    table_data.extend(data)
                else:
                    table_data = data
                
                # Calculate column widths
                num_cols = len(table_data[0]) if table_data else 1
                col_width = 6.0 / num_cols  # 6 inches total width
                col_widths = [col_width * inch] * num_cols
                
                # Create table
                table = Table(table_data, colWidths=col_widths)
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 10),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('PADDING', (0, 0), (-1, -1), 6)
                ]))
                
                story.append(table)
                story.append(Spacer(1, 0.3 * inch))
                
                # Add page break for large tables
                if i > 0 and i % 3 == 0:
                    story.append(PageBreak())
                    
            except Exception as e:
                log.error(f"Error creating table {i+1}: {e}")
                continue
        
        return story

    def _create_insights_section(self, insights: List[str]) -> List:
        """Create insights and recommendations section."""
        from reportlab.platypus import Paragraph, Spacer
        from reportlab.lib.units import inch
        
        story = []
        
        story.append(Paragraph("Key Insights & Recommendations", self.chart_generator.styles['h2']))
        story.append(Spacer(1, 0.2 * inch))
        
        for i, insight in enumerate(insights, 1):
            story.append(Paragraph(f"• {insight}", self.chart_generator.styles['BodyText']))
            story.append(Spacer(1, 0.1 * inch))
        
        story.append(Spacer(1, 0.3 * inch))
        
        return story

    def _create_performance_overview(self, performance_data: Dict[str, Any]) -> List:
        """Create performance overview section."""
        from reportlab.platypus import Paragraph, Spacer
        from reportlab.lib.units import inch
        
        story = []
        
        story.append(Paragraph("Performance Overview", self.chart_generator.styles['h2']))
        story.append(Spacer(1, 0.2 * inch))
        
        overview = performance_data.get('overview', 'No performance overview provided.')
        story.append(Paragraph(overview, self.chart_generator.styles['BodyText']))
        story.append(Spacer(1, 0.3 * inch))
        
        return story

    def _create_metrics_breakdown(self, performance_data: Dict[str, Any], 
                                 metrics: List[str]) -> List:
        """Create metrics breakdown section."""
        from reportlab.platypus import Paragraph, Spacer, Table, TableStyle
        from reportlab.lib.units import inch
        from reportlab.lib import colors
        
        story = []
        
        story.append(Paragraph("Metrics Breakdown", self.chart_generator.styles['h2']))
        story.append(Spacer(1, 0.2 * inch))
        
        # Create metrics table
        table_data = [["Metric", "Current Value", "Target", "Performance"]]
        
        for metric in metrics:
            if metric in performance_data:
                metric_data = performance_data[metric]
                current = metric_data.get('current', 'N/A')
                target = metric_data.get('target', 'N/A')
                performance = metric_data.get('performance', 'N/A')
                
                table_data.append([metric, str(current), str(target), str(performance)])
        
        # Create table
        table = Table(table_data, colWidths=[2*inch, 1.5*inch, 1.5*inch, 1*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(table)
        story.append(Spacer(1, 0.3 * inch))
        
        return story

    def _create_trends_section(self, trends: Dict[str, Any]) -> List:
        """Create trends section with performance trends."""
        from reportlab.platypus import Paragraph, Spacer
        from reportlab.lib.units import inch
        
        story = []
        
        story.append(Paragraph("Performance Trends", self.chart_generator.styles['h2']))
        story.append(Spacer(1, 0.2 * inch))
        
        # Create trend charts
        for trend_name, trend_data in trends.items():
            try:
                if 'labels' in trend_data and 'data' in trend_data:
                    chart = self.chart_generator.create_line_chart(
                        trend_data['labels'],
                        [{'label': trend_name, 'data': trend_data['data']}],
                        f"{trend_name} Trend"
                    )
                    
                    story.extend(self.chart_generator.create_chart_with_caption(
                        chart, f"Trend: {trend_name}"
                    ))
                    
            except Exception as e:
                log.error(f"Error creating trend chart for {trend_name}: {e}")
                continue
        
        return story

    def _create_recommendations_section(self, recommendations: List[str]) -> List:
        """Create recommendations section."""
        from reportlab.platypus import Paragraph, Spacer
        from reportlab.lib.units import inch
        
        story = []
        
        story.append(Paragraph("Recommendations", self.chart_generator.styles['h2']))
        story.append(Spacer(1, 0.2 * inch))
        
        for i, recommendation in enumerate(recommendations, 1):
            story.append(Paragraph(f"{i}. {recommendation}", self.chart_generator.styles['BodyText']))
            story.append(Spacer(1, 0.1 * inch))
        
        story.append(Spacer(1, 0.3 * inch))
        
        return story

    def _create_text_section(self, section: Dict[str, Any]) -> List:
        """Create a text section."""
        from reportlab.platypus import Paragraph, Spacer
        from reportlab.lib.units import inch
        
        story = []
        
        title = section.get('title', '')
        content = section.get('content', '')
        
        if title:
            story.append(Paragraph(title, self.chart_generator.styles['h3']))
            story.append(Spacer(1, 0.1 * inch))
        
        if content:
            story.append(Paragraph(content, self.chart_generator.styles['BodyText']))
            story.append(Spacer(1, 0.2 * inch))
        
        return story

    def _create_custom_chart_section(self, section: Dict[str, Any]) -> List:
        """Create a custom chart section."""
        try:
            chart_config = section.get('chart_config', {})
            title = section.get('title', '')
            caption = section.get('caption', '')
            
            chart = self.chart_generator.create_custom_chart(chart_config)
            
            story = []
            if title:
                story.append(Paragraph(title, self.chart_generator.styles['h3']))
                story.append(Spacer(1, 0.1 * inch))
            
            story.extend(self.chart_generator.create_chart_with_caption(chart, caption))
            
            return story
            
        except Exception as e:
            log.error(f"Error creating custom chart section: {e}")
            return []

    def _create_custom_table_section(self, section: Dict[str, Any]) -> List:
        """Create a custom table section."""
        from reportlab.platypus import Paragraph, Spacer, Table, TableStyle
        from reportlab.lib.units import inch
        from reportlab.lib import colors
        
        try:
            title = section.get('title', '')
            data = section.get('data', [])
            headers = section.get('headers', [])
            
            story = []
            
            if title:
                story.append(Paragraph(title, self.chart_generator.styles['h3']))
                story.append(Spacer(1, 0.1 * inch))
            
            if data:
                # Prepare table data
                if headers:
                    table_data = [headers]
                    table_data.extend(data)
                else:
                    table_data = data
                
                # Calculate column widths
                num_cols = len(table_data[0]) if table_data else 1
                col_width = 6.0 / num_cols
                col_widths = [col_width * inch] * num_cols
                
                # Create table
                table = Table(table_data, colWidths=col_widths)
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 10),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('PADDING', (0, 0), (-1, -1), 6)
                ]))
                
                story.append(table)
                story.append(Spacer(1, 0.3 * inch))
            
            return story
            
        except Exception as e:
            log.error(f"Error creating custom table section: {e}")
            return []

    def _create_image_section(self, section: Dict[str, Any]) -> List:
        """Create an image section."""
        from reportlab.platypus import Paragraph, Spacer, Image
        from reportlab.lib.units import inch
        
        try:
            title = section.get('title', '')
            image_path = section.get('image_path', '')
            caption = section.get('caption', '')
            width = section.get('width', 6.0)
            height = section.get('height', 4.0)
            
            story = []
            
            if title:
                story.append(Paragraph(title, self.chart_generator.styles['h3']))
                story.append(Spacer(1, 0.1 * inch))
            
            if image_path and Path(image_path).exists():
                img = Image(image_path, width=width*inch, height=height*inch)
                story.append(img)
                
                if caption:
                    story.append(Paragraph(caption, self.chart_generator.styles['Caption']))
                
                story.append(Spacer(1, 0.2 * inch))
            
            return story
            
        except Exception as e:
            log.error(f"Error creating image section: {e}")
            return []

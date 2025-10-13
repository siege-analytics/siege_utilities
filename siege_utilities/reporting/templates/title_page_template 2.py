#!/usr/bin/env python3
"""
Professional Title Page Template for siege_utilities
Creates beautiful, branded title pages with proper typography and layout
Adapted from working GA project implementation
"""

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.units import inch, mm
from reportlab.lib.colors import Color, HexColor
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from datetime import datetime
from pathlib import Path
import yaml
from typing import Dict, Any, Optional

try:
    from ..core.logging import log_info, log_warning, log_error
except ImportError:
    def log_info(message): print(f"INFO: {message}")
    def log_warning(message): print(f"WARNING: {message}")
    def log_error(message): print(f"ERROR: {message}")


class TitlePageTemplate:
    """Professional title page generator for siege utilities reports"""
    
    def __init__(self, canvas_obj: canvas.Canvas, page_size: tuple = letter):
        self.canvas = canvas_obj
        self.page_size = page_size
        self.width, self.height = page_size
        
        # Load brand configuration (if available)
        self.brand_config = self._load_brand_config()
        self.colors = self._setup_colors()
        
        # Page margins and layout
        self.margin_left = 72  # 1 inch
        self.margin_right = 72
        self.margin_top = 90
        self.margin_bottom = 72
        
        # Content area
        self.content_width = self.width - self.margin_left - self.margin_right
        self.content_height = self.height - self.margin_top - self.margin_bottom
        
    def _load_brand_config(self) -> Dict[str, Any]:
        """Load brand configuration from client branding system"""
        try:
            # Try to use siege utilities client branding
            from .client_branding import ClientBrandingManager
            branding_manager = ClientBrandingManager()
            # For now, return default - could be enhanced to load specific client
            return self._default_brand_config()
        except Exception as e:
            log_warning(f"Could not load brand config: {e}")
            return self._default_brand_config()
    
    def _default_brand_config(self) -> Dict[str, Any]:
        """Default brand configuration for siege utilities"""
        return {
            'client_name': 'Siege Analytics',
            'brand_colors': {
                'primary': '#2E5B8C',      # Professional blue
                'secondary': '#4A90E2',    # Lighter blue
                'accent': '#E74C3C',       # Red accent
                'text': '#2C3E50',         # Dark gray
                'light_gray': '#7F8C8D',   # Medium gray
                'background': '#FFFFFF'     # White
            },
            'fonts': {
                'primary': 'Helvetica',
                'heading': 'Helvetica-Bold',
                'title_size': 24,
                'subtitle_size': 16,
                'body_size': 11
            },
            'logo': {
                'text': 'SIEGE ANALYTICS',
                'width': 2.0,
                'height': 0.8
            }
        }
    
    def _setup_colors(self) -> Dict[str, Color]:
        """Setup color palette from brand config"""
        brand_colors = self.brand_config.get('brand_colors', {})
        return {
            'primary': HexColor(brand_colors.get('primary', '#2E5B8C')),
            'secondary': HexColor(brand_colors.get('secondary', '#4A90E2')),
            'accent': HexColor(brand_colors.get('accent', '#E74C3C')),
            'text': HexColor(brand_colors.get('text', '#2C3E50')),
            'light_gray': HexColor(brand_colors.get('light_gray', '#7F8C8D')),
            'background': HexColor(brand_colors.get('background', '#FFFFFF'))
        }
    
    def create_title_page(self, 
                         title: str,
                         subtitle: str = "",
                         report_period: str = "",
                         prepared_by: str = "",
                         client_name: str = "",
                         additional_info: Dict[str, str] = None) -> None:
        """
        Create a professional title page.
        
        Args:
            title: Main report title
            subtitle: Report subtitle
            report_period: Date range or period
            prepared_by: Who prepared the report
            client_name: Client name (overrides brand config)
            additional_info: Additional information to display
        """
        additional_info = additional_info or {}
        
        # Use provided client name or default from brand config
        if not client_name:
            client_name = self.brand_config.get('client_name', 'Siege Analytics')
        
        # Clear the page
        self.canvas.setFillColor(self.colors['background'])
        self.canvas.rect(0, 0, self.width, self.height, fill=1)
        
        # Header section with logo/branding
        self._draw_header(client_name)
        
        # Main title section
        self._draw_title_section(title, subtitle)
        
        # Report details section
        self._draw_details_section(report_period, prepared_by, additional_info)
        
        # Footer
        self._draw_footer()
        
        # Finish the page
        self.canvas.showPage()
        log_info(f"Created title page: {title}")
    
    def _draw_header(self, client_name: str) -> None:
        """Draw the header section with logo/branding"""
        # Header background
        self.canvas.setFillColor(self.colors['primary'])
        header_height = 80
        self.canvas.rect(0, self.height - header_height, self.width, header_height, fill=1)
        
        # Logo/Brand text
        self.canvas.setFillColor(self.colors['background'])
        self.canvas.setFont('Helvetica-Bold', 18)
        
        logo_text = self.brand_config.get('logo', {}).get('text', client_name.upper())
        logo_x = self.margin_left
        logo_y = self.height - 50
        
        self.canvas.drawString(logo_x, logo_y, logo_text)
        
        # Tagline or additional branding
        self.canvas.setFont('Helvetica', 10)
        tagline = "Professional Analytics & Reporting"
        self.canvas.drawString(logo_x, logo_y - 20, tagline)
    
    def _draw_title_section(self, title: str, subtitle: str) -> None:
        """Draw the main title section"""
        # Title
        self.canvas.setFillColor(self.colors['text'])
        title_font_size = self.brand_config.get('fonts', {}).get('title_size', 24)
        self.canvas.setFont('Helvetica-Bold', title_font_size)
        
        # Center the title
        title_width = self.canvas.stringWidth(title, 'Helvetica-Bold', title_font_size)
        title_x = (self.width - title_width) / 2
        title_y = self.height - 200
        
        self.canvas.drawString(title_x, title_y, title)
        
        # Subtitle
        if subtitle:
            subtitle_font_size = self.brand_config.get('fonts', {}).get('subtitle_size', 16)
            self.canvas.setFont('Helvetica', subtitle_font_size)
            self.canvas.setFillColor(self.colors['secondary'])
            
            subtitle_width = self.canvas.stringWidth(subtitle, 'Helvetica', subtitle_font_size)
            subtitle_x = (self.width - subtitle_width) / 2
            subtitle_y = title_y - 40
            
            self.canvas.drawString(subtitle_x, subtitle_y, subtitle)
        
        # Decorative line
        line_y = title_y - 80
        line_margin = 100
        self.canvas.setStrokeColor(self.colors['accent'])
        self.canvas.setLineWidth(2)
        self.canvas.line(line_margin, line_y, self.width - line_margin, line_y)
    
    def _draw_details_section(self, report_period: str, prepared_by: str, 
                            additional_info: Dict[str, str]) -> None:
        """Draw the report details section"""
        self.canvas.setFillColor(self.colors['text'])
        self.canvas.setFont('Helvetica', 12)
        
        details_y = self.height - 350
        line_height = 25
        
        # Report period
        if report_period:
            self.canvas.drawString(self.margin_left, details_y, f"Report Period: {report_period}")
            details_y -= line_height
        
        # Prepared by
        if prepared_by:
            self.canvas.drawString(self.margin_left, details_y, f"Prepared by: {prepared_by}")
            details_y -= line_height
        
        # Generation date
        generation_date = datetime.now().strftime("%B %d, %Y")
        self.canvas.drawString(self.margin_left, details_y, f"Generated: {generation_date}")
        details_y -= line_height
        
        # Additional information
        for key, value in additional_info.items():
            if value:
                self.canvas.drawString(self.margin_left, details_y, f"{key}: {value}")
                details_y -= line_height
    
    def _draw_footer(self) -> None:
        """Draw the footer section"""
        # Footer background
        footer_height = 40
        self.canvas.setFillColor(self.colors['light_gray'])
        self.canvas.rect(0, 0, self.width, footer_height, fill=1)
        
        # Footer text
        self.canvas.setFillColor(self.colors['background'])
        self.canvas.setFont('Helvetica', 9)
        
        footer_text = "Confidential - Prepared for internal use"
        footer_x = self.margin_left
        footer_y = 15
        
        self.canvas.drawString(footer_x, footer_y, footer_text)
        
        # Page indicator
        page_text = "Page 1"
        page_width = self.canvas.stringWidth(page_text, 'Helvetica', 9)
        page_x = self.width - self.margin_right - page_width
        
        self.canvas.drawString(page_x, footer_y, page_text)


def create_title_page(canvas_obj: canvas.Canvas, 
                     title: str,
                     subtitle: str = "",
                     report_period: str = "",
                     prepared_by: str = "",
                     client_name: str = "",
                     additional_info: Dict[str, str] = None,
                     page_size: tuple = letter) -> None:
    """
    Convenience function to create a title page.
    
    Args:
        canvas_obj: ReportLab canvas object
        title: Main report title
        subtitle: Report subtitle
        report_period: Date range or period
        prepared_by: Who prepared the report
        client_name: Client name
        additional_info: Additional information to display
        page_size: Page size tuple (default: letter)
    """
    template = TitlePageTemplate(canvas_obj, page_size)
    template.create_title_page(
        title=title,
        subtitle=subtitle,
        report_period=report_period,
        prepared_by=prepared_by,
        client_name=client_name,
        additional_info=additional_info
    )


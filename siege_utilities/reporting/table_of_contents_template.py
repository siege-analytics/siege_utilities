#!/usr/bin/env python3
"""
Professional Table of Contents Template for siege_utilities
Creates clean, organized TOCs with proper typography and page numbering
Adapted from working GA project implementation
"""

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.colors import HexColor
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import Paragraph, Table, TableStyle
from reportlab.lib.units import inch
from datetime import datetime
from pathlib import Path
import yaml
from typing import List, Dict, Any, Tuple

try:
    from ..core.logging import log_info, log_warning, log_error
except ImportError:
    def log_info(message): print(f"INFO: {message}")
    def log_warning(message): print(f"WARNING: {message}")
    def log_error(message): print(f"ERROR: {message}")


class TableOfContentsTemplate:
    """Professional table of contents generator for siege utilities reports"""
    
    def __init__(self, canvas_obj: canvas.Canvas, page_size: tuple = letter):
        self.canvas = canvas_obj
        self.page_size = page_size
        self.width, self.height = page_size
        
        # Load brand configuration
        self.brand_config = self._load_brand_config()
        self.colors = self._setup_colors()
        
        # Page margins
        self.margin_left = 72
        self.margin_right = 72
        self.margin_top = 90
        self.margin_bottom = 72
        
        # Content area
        self.content_width = self.width - self.margin_left - self.margin_right
        self.content_height = self.height - self.margin_top - self.margin_bottom
    
    def _load_brand_config(self) -> Dict[str, Any]:
        """Load brand configuration from client branding system"""
        try:
            from .client_branding import ClientBrandingManager
            branding_manager = ClientBrandingManager()
            return self._default_brand_config()
        except Exception as e:
            log_warning(f"Could not load brand config: {e}")
            return self._default_brand_config()
    
    def _default_brand_config(self) -> Dict[str, Any]:
        """Default brand configuration for siege utilities"""
        return {
            'client_name': 'Siege Analytics',
            'brand_colors': {
                'primary': '#2E5B8C',
                'secondary': '#4A90E2',
                'accent': '#E74C3C',
                'text': '#2C3E50',
                'light_gray': '#7F8C8D',
                'background': '#FFFFFF'
            },
            'fonts': {
                'primary': 'Helvetica',
                'heading': 'Helvetica-Bold',
                'title_size': 20,
                'section_size': 14,
                'body_size': 11
            }
        }
    
    def _setup_colors(self) -> Dict[str, Any]:
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
    
    def create_table_of_contents(self, 
                                sections: List[Dict[str, Any]],
                                title: str = "Table of Contents",
                                page_number: int = 2) -> None:
        """
        Create a professional table of contents page.
        
        Args:
            sections: List of section dictionaries with 'title', 'page', and optional 'subsections'
            title: TOC title (default: "Table of Contents")
            page_number: Current page number
        
        Section format:
            {
                'title': 'Executive Summary',
                'page': 3,
                'subsections': [  # Optional
                    {'title': 'Key Findings', 'page': 3},
                    {'title': 'Recommendations', 'page': 4}
                ]
            }
        """
        # Clear the page
        self.canvas.setFillColor(self.colors['background'])
        self.canvas.rect(0, 0, self.width, self.height, fill=1)
        
        # Header
        self._draw_header()
        
        # Title
        self._draw_title(title)
        
        # TOC entries
        self._draw_toc_entries(sections)
        
        # Footer
        self._draw_footer(page_number)
        
        # Finish the page
        self.canvas.showPage()
        log_info(f"Created table of contents with {len(sections)} sections")
    
    def _draw_header(self) -> None:
        """Draw the header section"""
        # Header background
        self.canvas.setFillColor(self.colors['primary'])
        header_height = 60
        self.canvas.rect(0, self.height - header_height, self.width, header_height, fill=1)
        
        # Header text
        self.canvas.setFillColor(self.colors['background'])
        self.canvas.setFont('Helvetica-Bold', 14)
        
        brand_name = self.brand_config.get('client_name', 'Siege Analytics')
        header_text = f"{brand_name} Report"
        
        self.canvas.drawString(self.margin_left, self.height - 40, header_text)
    
    def _draw_title(self, title: str) -> None:
        """Draw the TOC title"""
        self.canvas.setFillColor(self.colors['text'])
        title_font_size = self.brand_config.get('fonts', {}).get('title_size', 20)
        self.canvas.setFont('Helvetica-Bold', title_font_size)
        
        # Center the title
        title_width = self.canvas.stringWidth(title, 'Helvetica-Bold', title_font_size)
        title_x = (self.width - title_width) / 2
        title_y = self.height - 140
        
        self.canvas.drawString(title_x, title_y, title)
        
        # Decorative line
        line_y = title_y - 20
        line_margin = 100
        self.canvas.setStrokeColor(self.colors['accent'])
        self.canvas.setLineWidth(1)
        self.canvas.line(line_margin, line_y, self.width - line_margin, line_y)
    
    def _draw_toc_entries(self, sections: List[Dict[str, Any]]) -> None:
        """Draw the table of contents entries"""
        start_y = self.height - 200
        current_y = start_y
        line_height = 25
        indent_width = 20
        
        self.canvas.setFont('Helvetica', 12)
        
        for section in sections:
            # Main section
            section_title = section.get('title', '')
            section_page = section.get('page', '')
            
            if section_title and section_page:
                # Draw section title
                self.canvas.setFillColor(self.colors['text'])
                self.canvas.drawString(self.margin_left, current_y, section_title)
                
                # Draw dotted line
                title_width = self.canvas.stringWidth(section_title, 'Helvetica', 12)
                page_text = str(section_page)
                page_width = self.canvas.stringWidth(page_text, 'Helvetica', 12)
                
                dots_start = self.margin_left + title_width + 10
                dots_end = self.width - self.margin_right - page_width - 10
                
                self._draw_dotted_line(dots_start, dots_end, current_y + 3)
                
                # Draw page number
                self.canvas.drawString(self.width - self.margin_right - page_width, 
                                     current_y, page_text)
                
                current_y -= line_height
            
            # Subsections
            subsections = section.get('subsections', [])
            for subsection in subsections:
                subsection_title = subsection.get('title', '')
                subsection_page = subsection.get('page', '')
                
                if subsection_title and subsection_page:
                    # Indented subsection
                    self.canvas.setFillColor(self.colors['light_gray'])
                    self.canvas.setFont('Helvetica', 10)
                    
                    subsection_x = self.margin_left + indent_width
                    self.canvas.drawString(subsection_x, current_y, f"• {subsection_title}")
                    
                    # Page number for subsection
                    page_text = str(subsection_page)
                    page_width = self.canvas.stringWidth(page_text, 'Helvetica', 10)
                    self.canvas.drawString(self.width - self.margin_right - page_width, 
                                         current_y, page_text)
                    
                    current_y -= (line_height * 0.8)  # Smaller spacing for subsections
                    
                    # Reset font for next main section
                    self.canvas.setFont('Helvetica', 12)
    
    def _draw_dotted_line(self, start_x: float, end_x: float, y: float) -> None:
        """Draw a dotted line for TOC entries"""
        if end_x <= start_x:
            return
            
        self.canvas.setStrokeColor(self.colors['light_gray'])
        self.canvas.setLineWidth(0.5)
        
        # Create dotted pattern
        dot_spacing = 4
        current_x = start_x
        
        while current_x < end_x:
            self.canvas.circle(current_x, y, 0.5, fill=1)
            current_x += dot_spacing
    
    def _draw_footer(self, page_number: int) -> None:
        """Draw the footer section"""
        # Footer background
        footer_height = 40
        self.canvas.setFillColor(self.colors['light_gray'])
        self.canvas.rect(0, 0, self.width, footer_height, fill=1)
        
        # Footer text
        self.canvas.setFillColor(self.colors['background'])
        self.canvas.setFont('Helvetica', 9)
        
        footer_text = "Table of Contents"
        footer_x = self.margin_left
        footer_y = 15
        
        self.canvas.drawString(footer_x, footer_y, footer_text)
        
        # Page number
        page_text = f"Page {page_number}"
        page_width = self.canvas.stringWidth(page_text, 'Helvetica', 9)
        page_x = self.width - self.margin_right - page_width
        
        self.canvas.drawString(page_x, footer_y, page_text)


def create_table_of_contents(canvas_obj: canvas.Canvas,
                           sections: List[Dict[str, Any]],
                           title: str = "Table of Contents",
                           page_number: int = 2,
                           page_size: tuple = letter) -> None:
    """
    Convenience function to create a table of contents page.
    
    Args:
        canvas_obj: ReportLab canvas object
        sections: List of section dictionaries with 'title', 'page', and optional 'subsections'
        title: TOC title
        page_number: Current page number
        page_size: Page size tuple
    """
    template = TableOfContentsTemplate(canvas_obj, page_size)
    template.create_table_of_contents(
        sections=sections,
        title=title,
        page_number=page_number
    )


def generate_sections_from_report_structure(report_structure: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Generate TOC sections from a report structure dictionary.
    
    Args:
        report_structure: Dictionary defining report structure
        
    Returns:
        List of section dictionaries for TOC
    """
    sections = []
    current_page = 3  # Start after title and TOC
    
    for section_key, section_info in report_structure.items():
        if isinstance(section_info, dict):
            section_title = section_info.get('title', section_key.replace('_', ' ').title())
            
            # Main section
            section_entry = {
                'title': section_title,
                'page': current_page
            }
            
            # Check for subsections
            subsections = section_info.get('subsections', {})
            if subsections:
                section_entry['subsections'] = []
                for sub_key, sub_info in subsections.items():
                    if isinstance(sub_info, dict):
                        sub_title = sub_info.get('title', sub_key.replace('_', ' ').title())
                        section_entry['subsections'].append({
                            'title': sub_title,
                            'page': current_page
                        })
                    current_page += 1
            else:
                current_page += 1
            
            sections.append(section_entry)
    
    return sections


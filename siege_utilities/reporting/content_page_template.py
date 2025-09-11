#!/usr/bin/env python3
"""
Professional Content Page Template for siege_utilities
Creates structured content pages with headers, footers, and proper layout
Adapted from working GA project implementation
"""

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.colors import HexColor
from reportlab.lib.units import inch
from reportlab.platypus import Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from datetime import datetime
from pathlib import Path
import yaml
from typing import Dict, Any, Optional, List, Union

try:
    from ..core.logging import log_info, log_warning, log_error
except ImportError:
    def log_info(message): print(f"INFO: {message}")
    def log_warning(message): print(f"WARNING: {message}")
    def log_error(message): print(f"ERROR: {message}")


class ContentPageTemplate:
    """Professional content page generator for siege utilities reports"""
    
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
        
        # Header and footer heights
        self.header_height = 50
        self.footer_height = 40
        
        # Available content area (excluding header/footer)
        self.available_content_height = self.content_height - self.header_height - self.footer_height
        
        # Current Y position for content
        self.current_y = self.height - self.margin_top - self.header_height - 20
    
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
                'title_size': 18,
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
    
    def start_page(self, 
                   page_title: str,
                   page_number: int,
                   section_name: str = "") -> None:
        """
        Start a new content page with header and setup.
        
        Args:
            page_title: Title for this page
            page_number: Current page number
            section_name: Optional section name for header
        """
        # Clear the page
        self.canvas.setFillColor(self.colors['background'])
        self.canvas.rect(0, 0, self.width, self.height, fill=1)
        
        # Draw header
        self._draw_header(page_title, section_name)
        
        # Store page info for footer
        self.page_number = page_number
        self.page_title = page_title
        
        # Reset current Y position
        self.current_y = self.height - self.margin_top - self.header_height - 20
        
        log_info(f"Started content page: {page_title} (Page {page_number})")
    
    def add_section_title(self, title: str, font_size: int = 16) -> None:
        """Add a section title to the page"""
        if self.current_y < (self.margin_bottom + self.footer_height + 50):
            log_warning("Not enough space for section title, consider new page")
            return
        
        self.canvas.setFillColor(self.colors['primary'])
        self.canvas.setFont('Helvetica-Bold', font_size)
        
        self.canvas.drawString(self.margin_left, self.current_y, title)
        
        # Add underline
        title_width = self.canvas.stringWidth(title, 'Helvetica-Bold', font_size)
        self.canvas.setStrokeColor(self.colors['accent'])
        self.canvas.setLineWidth(2)
        self.canvas.line(self.margin_left, self.current_y - 5, 
                        self.margin_left + title_width, self.current_y - 5)
        
        self.current_y -= 35
    
    def add_paragraph(self, text: str, font_size: int = 11, 
                     text_color: str = None, line_spacing: float = 1.2) -> None:
        """Add a paragraph of text to the page"""
        if not text:
            return
        
        color = HexColor(text_color) if text_color else self.colors['text']
        self.canvas.setFillColor(color)
        self.canvas.setFont('Helvetica', font_size)
        
        # Simple text wrapping
        words = text.split()
        lines = []
        current_line = ""
        
        for word in words:
            test_line = f"{current_line} {word}".strip()
            if self.canvas.stringWidth(test_line, 'Helvetica', font_size) <= self.content_width:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line)
                current_line = word
        
        if current_line:
            lines.append(current_line)
        
        # Draw lines
        line_height = font_size * line_spacing
        for line in lines:
            if self.current_y < (self.margin_bottom + self.footer_height + line_height):
                log_warning("Not enough space for paragraph, consider new page")
                break
            
            self.canvas.drawString(self.margin_left, self.current_y, line)
            self.current_y -= line_height
        
        # Add spacing after paragraph
        self.current_y -= 10
    
    def add_table(self, data: List[List[str]], 
                  headers: List[str] = None,
                  table_title: str = "") -> None:
        """Add a table to the page"""
        if not data:
            return
        
        if table_title:
            self.add_section_title(table_title, 14)
        
        # Prepare table data
        table_data = []
        if headers:
            table_data.append(headers)
        table_data.extend(data)
        
        # Calculate column widths
        num_cols = len(table_data[0]) if table_data else 0
        if num_cols == 0:
            return
        
        col_width = self.content_width / num_cols
        table_width = self.content_width
        
        # Estimate table height
        row_height = 20
        table_height = len(table_data) * row_height
        
        if self.current_y - table_height < (self.margin_bottom + self.footer_height):
            log_warning("Not enough space for table, consider new page")
            return
        
        # Draw table manually (simple version)
        start_y = self.current_y
        
        # Table border
        self.canvas.setStrokeColor(self.colors['text'])
        self.canvas.setLineWidth(1)
        self.canvas.rect(self.margin_left, start_y - table_height, 
                        table_width, table_height)
        
        # Draw rows
        for i, row in enumerate(table_data):
            row_y = start_y - (i * row_height)
            
            # Header row styling
            if i == 0 and headers:
                self.canvas.setFillColor(self.colors['primary'])
                self.canvas.rect(self.margin_left, row_y - row_height, 
                               table_width, row_height, fill=1)
                self.canvas.setFillColor(self.colors['background'])
                self.canvas.setFont('Helvetica-Bold', 10)
            else:
                self.canvas.setFillColor(self.colors['text'])
                self.canvas.setFont('Helvetica', 10)
            
            # Draw cells
            for j, cell in enumerate(row):
                cell_x = self.margin_left + (j * col_width) + 5
                cell_y = row_y - 15
                
                # Truncate text if too long
                max_width = col_width - 10
                while self.canvas.stringWidth(str(cell), self.canvas._fontname, 10) > max_width and len(str(cell)) > 3:
                    cell = str(cell)[:-4] + "..."
                
                self.canvas.drawString(cell_x, cell_y, str(cell))
            
            # Row separator
            if i < len(table_data) - 1:
                self.canvas.setStrokeColor(self.colors['light_gray'])
                self.canvas.line(self.margin_left, row_y - row_height, 
                               self.margin_left + table_width, row_y - row_height)
        
        # Column separators
        self.canvas.setStrokeColor(self.colors['light_gray'])
        for j in range(1, num_cols):
            col_x = self.margin_left + (j * col_width)
            self.canvas.line(col_x, start_y, col_x, start_y - table_height)
        
        self.current_y = start_y - table_height - 20
    
    def add_bullet_list(self, items: List[str], bullet_char: str = "•") -> None:
        """Add a bullet list to the page"""
        self.canvas.setFillColor(self.colors['text'])
        self.canvas.setFont('Helvetica', 11)
        
        line_height = 16
        indent = 20
        
        for item in items:
            if self.current_y < (self.margin_bottom + self.footer_height + line_height):
                log_warning("Not enough space for bullet item, consider new page")
                break
            
            # Draw bullet
            self.canvas.drawString(self.margin_left, self.current_y, bullet_char)
            
            # Draw text (simple, no wrapping for now)
            self.canvas.drawString(self.margin_left + indent, self.current_y, item)
            
            self.current_y -= line_height
        
        # Add spacing after list
        self.current_y -= 10
    
    def add_spacing(self, points: float = 20) -> None:
        """Add vertical spacing"""
        self.current_y -= points
    
    def get_remaining_space(self) -> float:
        """Get remaining space on current page"""
        return self.current_y - (self.margin_bottom + self.footer_height)
    
    def finish_page(self) -> None:
        """Finish the current page by drawing footer"""
        self._draw_footer()
        self.canvas.showPage()
    
    def _draw_header(self, page_title: str, section_name: str = "") -> None:
        """Draw the page header"""
        # Header background
        self.canvas.setFillColor(self.colors['primary'])
        self.canvas.rect(0, self.height - self.margin_top, 
                        self.width, self.header_height, fill=1)
        
        # Header text
        self.canvas.setFillColor(self.colors['background'])
        self.canvas.setFont('Helvetica-Bold', 12)
        
        # Left side - section name or brand
        left_text = section_name or self.brand_config.get('client_name', 'Siege Analytics')
        self.canvas.drawString(self.margin_left, self.height - self.margin_top + 20, left_text)
        
        # Right side - page title
        if page_title:
            title_width = self.canvas.stringWidth(page_title, 'Helvetica-Bold', 12)
            title_x = self.width - self.margin_right - title_width
            self.canvas.drawString(title_x, self.height - self.margin_top + 20, page_title)
    
    def _draw_footer(self) -> None:
        """Draw the page footer"""
        # Footer background
        self.canvas.setFillColor(self.colors['light_gray'])
        self.canvas.rect(0, 0, self.width, self.footer_height, fill=1)
        
        # Footer text
        self.canvas.setFillColor(self.colors['background'])
        self.canvas.setFont('Helvetica', 9)
        
        # Left side - generation info
        footer_text = f"Generated: {datetime.now().strftime('%B %d, %Y')}"
        self.canvas.drawString(self.margin_left, 15, footer_text)
        
        # Right side - page number
        page_text = f"Page {self.page_number}"
        page_width = self.canvas.stringWidth(page_text, 'Helvetica', 9)
        page_x = self.width - self.margin_right - page_width
        self.canvas.drawString(page_x, 15, page_text)


def create_content_page(canvas_obj: canvas.Canvas,
                       page_title: str,
                       page_number: int,
                       content_sections: List[Dict[str, Any]],
                       section_name: str = "",
                       page_size: tuple = letter) -> None:
    """
    Convenience function to create a complete content page.
    
    Args:
        canvas_obj: ReportLab canvas object
        page_title: Title for this page
        page_number: Current page number
        content_sections: List of content sections to add
        section_name: Optional section name for header
        page_size: Page size tuple
    
    Content sections format:
        [
            {'type': 'title', 'text': 'Section Title'},
            {'type': 'paragraph', 'text': 'Paragraph text...'},
            {'type': 'table', 'data': [[...]], 'headers': [...], 'title': 'Table Title'},
            {'type': 'bullets', 'items': ['Item 1', 'Item 2']},
            {'type': 'spacing', 'points': 20}
        ]
    """
    template = ContentPageTemplate(canvas_obj, page_size)
    template.start_page(page_title, page_number, section_name)
    
    for section in content_sections:
        section_type = section.get('type', '')
        
        if section_type == 'title':
            template.add_section_title(section.get('text', ''))
        elif section_type == 'paragraph':
            template.add_paragraph(section.get('text', ''))
        elif section_type == 'table':
            template.add_table(
                data=section.get('data', []),
                headers=section.get('headers'),
                table_title=section.get('title', '')
            )
        elif section_type == 'bullets':
            template.add_bullet_list(section.get('items', []))
        elif section_type == 'spacing':
            template.add_spacing(section.get('points', 20))
    
    template.finish_page()


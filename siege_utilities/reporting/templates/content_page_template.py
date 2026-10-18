#!/usr/bin/env python3
"""
Professional Content Page Template for siege_utilities
Creates structured content pages with headers, footers, and proper layout
Adapted from working GA project implementation
"""

from __future__ import annotations

try:
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.colors import HexColor
    from reportlab.lib.units import inch
    from reportlab.platypus import Table, TableStyle, Paragraph
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False
    canvas = None
    letter = None
    HexColor = None
    inch = None
    Table = TableStyle = Paragraph = None
    getSampleStyleSheet = ParagraphStyle = None
from datetime import datetime
from typing import Dict, Any, List

from siege_utilities.core.logging import log_info, log_warning
from .._markup import _escape_paragraph

__all__ = [
    'ContentPageTemplate',
    'create_content_page',
]


class ContentPageTemplate:
    """Professional content page generator for siege utilities reports"""
    
    def __init__(self, canvas_obj: "canvas.Canvas", page_size: tuple = letter):
        if not REPORTLAB_AVAILABLE:
            raise ImportError(
                "reportlab is required for PDF content pages but is not installed. "
                "Install it with: pip install reportlab"
            )
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
        
        # Current Y position and continuation-page context.
        self.current_y = self.height - self.margin_top - self.header_height - 20
        self.page_number = self.canvas.getPageNumber()
        self.page_title = ""
        self.section_name = ""
    
    def _load_brand_config(self) -> Dict[str, Any]:
        """Load brand configuration from client branding system"""
        try:
            from .client_branding import ClientBrandingManager  # noqa: F401
            return self._default_brand_config()
        except ImportError as e:
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
        self.section_name = section_name
        
        # Reset current Y position
        self.current_y = self.height - self.margin_top - self.header_height - 20
        
        log_info(f"Started content page: {page_title} (Page {page_number})")
    
    def add_section_title(self, title: str, font_size: int = 16) -> None:
        """Add a section title to the page"""
        if self.current_y < (self.margin_bottom + self.footer_height + 50):
            self._continue_page()
        
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
    
    def _continue_page(self) -> None:
        """Finish the current page and repeat its header on the next page."""
        self.finish_page()
        self.start_page(self.page_title, self.page_number + 1, self.section_name)

    def _add_flowable(self, flowable, spacing: float) -> None:
        """Draw all fragments, or raise if a fragment cannot fit an empty page."""
        pending = [flowable]
        page_top = self.height - self.margin_top - self.header_height - 20
        while pending:
            current = pending.pop(0)
            available = max(0, self.get_remaining_space())
            width, height = current.wrapOn(self.canvas, self.content_width, available)
            if width > self.content_width + 1e-6:
                raise ValueError("Content cannot fit within the page width")
            if height <= available:
                current.drawOn(self.canvas, self.margin_left, self.current_y - height)
                self.current_y -= height
                continue

            fragments = current.splitOn(self.canvas, self.content_width, available)
            if len(fragments) >= 2:
                pending[0:0] = fragments
                continue
            if self.current_y >= page_top:
                raise ValueError("Content cannot fit on an empty page")
            self._continue_page()
            pending.insert(0, current)
        self.current_y -= spacing

    def add_paragraph(self, text: str, font_size: int = 11,
                     text_color: str = None, line_spacing: float = 1.2) -> None:
        """Add plain text, continuing onto subsequent pages when necessary."""
        if not text:
            return
        if font_size <= 0 or line_spacing <= 0:
            raise ValueError("Paragraph font size and line spacing must be positive")
        style = ParagraphStyle(
            'ContentBody', fontName='Helvetica', fontSize=font_size,
            leading=font_size * line_spacing,
            textColor=HexColor(text_color) if text_color else self.colors['text'],
        )
        self._add_flowable(Paragraph(_escape_paragraph(text), style), spacing=10)

    def add_table(self, data: List[List[str]],
                  headers: List[str] = None,
                  table_title: str = "",
                  sort_by=None,
                  sort_order: str = "asc") -> None:
        """Add a table to the page.

        Args:
            data: Row data (list of lists).
            headers: Column headers.
            table_title: Optional title above the table.
            sort_by: Column index (int) or header name (str) to sort by.
                None preserves existing order.
            sort_order: ``'asc'`` or ``'desc'``.
        """
        if not data:
            return

        if table_title:
            self.add_section_title(table_title, 14)

        # Prepare table data
        table_data = []
        if headers:
            table_data.append(headers)
        table_data.extend(data)

        if sort_by is not None:
            from siege_utilities.reporting.table_utils import sort_table_data
            table_data = sort_table_data(
                table_data, sort_by=sort_by, sort_order=sort_order,
                has_header=bool(headers),
            )
        
        num_cols = len(table_data[0])
        if not num_cols or any(len(row) != num_cols for row in table_data):
            raise ValueError("Table rows must have the same nonzero number of columns")
        body_style = ParagraphStyle(
            'ContentCell', fontName='Helvetica', fontSize=10, leading=12,
            textColor=self.colors['text'],
        )
        header_style = ParagraphStyle(
            'ContentHeader', parent=body_style, fontName='Helvetica-Bold',
            textColor=self.colors['background'],
        )
        rows = [
            [Paragraph(_escape_paragraph(str(cell)), header_style if headers and i == 0 else body_style)
             for cell in row]
            for i, row in enumerate(table_data)
        ]
        table = Table(rows, colWidths=[self.content_width / num_cols] * num_cols,
                      repeatRows=1 if headers else 0)
        commands = [
            ('GRID', (0, 0), (-1, -1), 0.5, self.colors['light_gray']),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]
        if headers:
            commands.append(('BACKGROUND', (0, 0), (-1, 0), self.colors['primary']))
        table.setStyle(TableStyle(commands))
        self._add_flowable(table, spacing=20)

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


def create_content_page(canvas_obj: "canvas.Canvas",
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


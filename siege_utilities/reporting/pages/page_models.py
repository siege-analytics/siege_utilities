"""
Page Models - OOP hierarchy for report pages
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Table type taxonomy
# ---------------------------------------------------------------------------

class TableType(Enum):
    SINGLE_RESPONSE   = "single_response"    # percents sum to 100%; one answer per respondent
    MULTIPLE_RESPONSE = "multiple_response"  # percents sum to >100%; base note required
    CROSS_TAB         = "cross_tab"          # two-dimension table with sig-test markers
    LONGITUDINAL      = "longitudinal"       # time periods as columns, delta column
    RANKING           = "ranking"            # ordered list with value + share columns
    MEAN_SCALE        = "mean_scale"         # average scores with confidence intervals
    BANNER            = "banner"             # multi-column cross-tab (OSCAR-style)


# ---------------------------------------------------------------------------
# Argument — atomic report unit
# ---------------------------------------------------------------------------

@dataclass
class Argument:
    """Atomic report unit: headline → narrative → table → visualization(s).

    layout is auto-resolved in __post_init__:
      - map_figure present  → "full_width"  (stacked: title / table / figure)
      - map_figure absent   → "side_by_side" (title top, table left, figure right)
    """

    headline: str
    narrative: str
    table: Any                              # pandas DataFrame or Chain
    table_type: TableType
    chart: Optional[Any] = None            # matplotlib Figure
    map_figure: Optional[Any] = None       # ChoroplethFigure; triggers full-width layout
    layout: str = "auto"                   # "auto" | "side_by_side" | "full_width"
    base_note: Optional[str] = None        # e.g. "n=342; multiple responses permitted"
    source_note: Optional[str] = None
    tags: List[str] = field(default_factory=list)

    def __post_init__(self):
        if self.layout == "auto":
            self.layout = "full_width" if self.map_figure is not None else "side_by_side"


# ---------------------------------------------------------------------------
# Base page
# ---------------------------------------------------------------------------

class Page(ABC):
    """Abstract base class for all report pages"""

    def __init__(self, primary_color, secondary_color, accent_color):
        self.primary_color = primary_color
        self.secondary_color = secondary_color
        self.accent_color = accent_color
        self.story = []

    @abstractmethod
    def build(self):
        """Build the page content"""

    def add_spacer(self, height):
        """Add spacing to the page"""
        from reportlab.platypus import Spacer
        self.story.append(Spacer(1, height))

    def add_paragraph(self, text, style):
        """Add a paragraph to the page"""
        from reportlab.platypus import Paragraph
        self.story.append(Paragraph(text, style))

    def add_page_break(self):
        """Add a page break"""
        from reportlab.platypus import PageBreak
        self.story.append(PageBreak())

    def get_content(self):
        """Get the complete page content"""
        return self.story


# ---------------------------------------------------------------------------
# TitlePage
# ---------------------------------------------------------------------------

class TitlePage(Page):
    """Title page implementation"""

    def __init__(self, primary_color, secondary_color, accent_color,
                 client_name, client_url, prepared_by,
                 report_type: str = "ANALYTICS REPORT",
                 tagline: str = "",
                 phone: Optional[str] = None):
        super().__init__(primary_color, secondary_color, accent_color)
        self.client_name = client_name
        self.client_url = client_url
        self.prepared_by = prepared_by
        self.report_type = report_type
        self.tagline = tagline
        self.phone = phone

        # Title page specific spacing
        self.BLUE_BAR_TO_TITLE = 1.2
        self.TITLE_TO_TAGLINE = 0.8
        self.TAGLINE_TO_DETAILS = 1.6
        self.DETAILS_INTERNAL = 0.4

    def create_blue_bar_style(self):
        """Create the blue header bar style"""
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib import colors
        styles = getSampleStyleSheet()
        return ParagraphStyle(
            'BlueBar',
            parent=styles['Normal'],
            fontSize=14,
            textColor=colors.white,
            alignment=1,
            spaceAfter=0,
            spaceBefore=0,
            fontName='Helvetica-Bold',
            backColor=colors.HexColor(self.primary_color),
            borderPadding=16,
            borderWidth=0,
            borderRadius=0
        )

    def create_title_style(self):
        """Create the main title style"""
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib import colors
        styles = getSampleStyleSheet()
        return ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=36,
            textColor=colors.HexColor(self.primary_color),
            alignment=1,
            spaceAfter=0.3,
            fontName='Helvetica-Bold',
            leading=50,
            leftIndent=0,
            rightIndent=0,
            wordWrap='LTR'
        )

    def create_tagline_style(self):
        """Create the tagline style"""
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib import colors
        styles = getSampleStyleSheet()
        return ParagraphStyle(
            'Tagline',
            parent=styles['Normal'],
            fontSize=14,
            textColor=colors.HexColor('#666666'),
            alignment=1,
            spaceAfter=0,
            fontName='Helvetica'
        )

    def create_details_style(self):
        """Create the details style"""
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib import colors
        styles = getSampleStyleSheet()
        return ParagraphStyle(
            'Details',
            parent=styles['Normal'],
            fontSize=12,
            textColor=colors.black,
            alignment=0,
            spaceAfter=int(0.3 * 72),
            fontName='Helvetica'
        )

    def build(self, start_date, end_date):
        """Build the complete title page"""
        from datetime import datetime

        # Blue header bar
        blue_bar_style = self.create_blue_bar_style()
        self.add_paragraph(self.report_type, blue_bar_style)
        self.add_spacer(self.BLUE_BAR_TO_TITLE)

        # Main title
        title_style = self.create_title_style()
        client_name_fixed = self.client_name.replace(" & ", "&nbsp;& ")
        self.add_paragraph(client_name_fixed, title_style)
        self.add_spacer(self.TITLE_TO_TAGLINE)

        # Tagline (omitted if empty)
        if self.tagline:
            tagline_style = self.create_tagline_style()
            self.add_paragraph(self.tagline, tagline_style)
        self.add_spacer(self.TAGLINE_TO_DETAILS)

        # Report details
        details_style = self.create_details_style()
        self.add_paragraph("<b>Report Date:</b><br/>" + datetime.now().strftime('%B %d, %Y'), details_style)
        self.add_spacer(self.DETAILS_INTERNAL)
        self.add_paragraph(f"<b>Period Covered:</b><br/>{start_date} to {end_date}", details_style)
        self.add_spacer(self.DETAILS_INTERNAL)
        if self.phone:
            self.add_paragraph(
                f'<b>Phone:</b><br/><a href="tel:{self.phone}">{self.phone}</a>',
                details_style,
            )
            self.add_spacer(self.DETAILS_INTERNAL)
        self.add_paragraph(f'<b>Website:</b><br/><a href="{self.client_url}">{self.client_url}</a>', details_style)
        self.add_spacer(self.DETAILS_INTERNAL)
        self.add_paragraph(f"<b>Prepared By:</b><br/>{self.prepared_by}", details_style)
        self.add_page_break()

        return self.get_content()


# ---------------------------------------------------------------------------
# TableOfContentsPage
# ---------------------------------------------------------------------------

class TableOfContentsPage(Page):
    """Table of contents page implementation"""

    def __init__(self, primary_color, secondary_color, accent_color):
        super().__init__(primary_color, secondary_color, accent_color)
        self.HEADER_SPACING = 0.6
        self.SECTION_SPACING = 0.4
        self.ITEM_SPACING = 0.2

    def create_header_style(self):
        """Create the TOC header style"""
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib import colors
        styles = getSampleStyleSheet()
        return ParagraphStyle(
            'TOCHeader',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor(self.primary_color),
            alignment=1,
            spaceAfter=self.HEADER_SPACING,
            fontName='Helvetica-Bold'
        )

    def create_section_style(self):
        """Create the TOC section style"""
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib import colors
        styles = getSampleStyleSheet()
        return ParagraphStyle(
            'TOCSection',
            parent=styles['Heading2'],
            fontSize=16,
            textColor=colors.HexColor(self.secondary_color),
            alignment=0,
            spaceAfter=self.SECTION_SPACING,
            fontName='Helvetica-Bold'
        )

    def create_item_style(self):
        """Create the TOC item style"""
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib import colors
        styles = getSampleStyleSheet()
        return ParagraphStyle(
            'TOCItem',
            parent=styles['Normal'],
            fontSize=12,
            textColor=colors.black,
            alignment=0,
            spaceAfter=self.ITEM_SPACING,
            fontName='Helvetica',
            leftIndent=20,
        )

    def build(self, toc_data: List[Dict]):
        """Build the table of contents page.

        Args:
            toc_data: list of dicts with keys 'section', 'title', and optional 'page_num'
        """
        header_style = self.create_header_style()
        section_style = self.create_section_style()
        item_style = self.create_item_style()

        self.add_paragraph("Table of Contents", header_style)
        self.add_spacer(self.HEADER_SPACING)

        # Group entries by section while preserving first-appearance order of
        # both sections and of titles within each section. This keeps the
        # output stable even when toc_data interleaves sections
        # (e.g. ``[A, B, A]`` still produces one A block and one B block).
        grouped: Dict[str, list] = {}
        section_order: list = []
        for entry in toc_data:
            section = entry.get("section", "")
            if section not in grouped:
                grouped[section] = []
                section_order.append(section)
            grouped[section].append(entry)

        for section in section_order:
            self.add_spacer(self.SECTION_SPACING)
            self.add_paragraph(section, section_style)
            for entry in grouped[section]:
                title = entry.get("title", "")
                page_num = entry.get("page_num")
                label = f"{title}{'  ·  ' + str(page_num) if page_num else ''}"
                self.add_paragraph(label, item_style)

        self.add_page_break()
        return self.get_content()


# ---------------------------------------------------------------------------
# ContentPage
# ---------------------------------------------------------------------------

class ContentPage(Page):
    """Base class for content pages (sections, charts, tables)"""

    def __init__(self, primary_color, secondary_color, accent_color):
        super().__init__(primary_color, secondary_color, accent_color)
        self.SECTION_HEADER_SPACING = 0.6
        self.HEADER_TO_CONTENT_SPACING = 0.5
        self.ELEMENT_SPACING = 0.4

    def create_section_header_style(self):
        """Create section header style"""
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib import colors
        styles = getSampleStyleSheet()
        return ParagraphStyle(
            'SectionHeader',
            parent=styles['Heading1'],
            fontSize=20,
            textColor=colors.HexColor(self.primary_color),
            alignment=0,
            spaceAfter=self.SECTION_HEADER_SPACING,
            fontName='Helvetica-Bold'
        )

    def create_subsection_header_style(self):
        """Create subsection header style"""
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib import colors
        styles = getSampleStyleSheet()
        return ParagraphStyle(
            'SubsectionHeader',
            parent=styles['Heading2'],
            fontSize=16,
            textColor=colors.HexColor(self.secondary_color),
            alignment=0,
            spaceAfter=self.HEADER_TO_CONTENT_SPACING,
            fontName='Helvetica-Bold'
        )

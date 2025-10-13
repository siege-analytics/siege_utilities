"""
Page Models - OOP hierarchy for report pages
"""
from abc import ABC, abstractmethod
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib import colors
from reportlab.platypus import Spacer, Paragraph, PageBreak
from reportlab.lib.styles import getSampleStyleSheet

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
        pass
    
    def add_spacer(self, height):
        """Add spacing to the page"""
        self.story.append(Spacer(1, height))
    
    def add_paragraph(self, text, style):
        """Add a paragraph to the page"""
        self.story.append(Paragraph(text, style))
    
    def add_page_break(self):
        """Add a page break"""
        self.story.append(PageBreak())
    
    def get_content(self):
        """Get the complete page content"""
        return self.story

class TitlePage(Page):
    """Title page implementation"""
    
    def __init__(self, primary_color, secondary_color, accent_color, 
                 client_name, client_url, prepared_by):
        super().__init__(primary_color, secondary_color, accent_color)
        self.client_name = client_name
        self.client_url = client_url
        self.prepared_by = prepared_by
        
        # Title page specific spacing
        self.BLUE_BAR_TO_TITLE = 1.2
        self.TITLE_TO_TAGLINE = 0.8
        self.TAGLINE_TO_DETAILS = 1.6
        self.DETAILS_INTERNAL = 0.4
    
    def create_blue_bar_style(self):
        """Create the blue header bar style"""
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
        self.add_paragraph("GOOGLE ANALYTICS REPORT", blue_bar_style)
        self.add_spacer(self.BLUE_BAR_TO_TITLE)
        
        # Main title
        title_style = self.create_title_style()
        client_name_fixed = self.client_name.replace(" & ", "&nbsp;& ")
        self.add_paragraph(client_name_fixed, title_style)
        self.add_spacer(self.TITLE_TO_TAGLINE)
        
        # Tagline
        tagline_style = self.create_tagline_style()
        self.add_paragraph("Promoting wellness and well-being for over 200 years", tagline_style)
        self.add_spacer(self.TAGLINE_TO_DETAILS)
        
        # Report details
        details_style = self.create_details_style()
        self.add_paragraph("<b>Report Date:</b><br/>" + datetime.now().strftime('%B %d, %Y'), details_style)
        self.add_spacer(self.DETAILS_INTERNAL)
        self.add_paragraph(f"<b>Period Covered:</b><br/>{start_date} to {end_date}", details_style)
        self.add_spacer(self.DETAILS_INTERNAL)
        self.add_paragraph(f"<b>Phone:</b><br/><a href=\"tel:+12022326100\">(202) 232-6100</a>", details_style)
        self.add_spacer(self.DETAILS_INTERNAL)
        self.add_paragraph(f"<b>Website:</b><br/><a href=\"{self.client_url}\">{self.client_url}</a>", details_style)
        self.add_spacer(self.DETAILS_INTERNAL)
        self.add_paragraph(f"<b>Prepared By:</b><br/><a href=\"https://masaiinteractive.com\">Masai Interactive</a> / <a href=\"https://siegeanalytics.com\">Siege Analytics</a>", details_style)
        self.add_page_break()
        
        return self.get_content()

class TableOfContentsPage(Page):
    """Table of contents page implementation"""
    
    def __init__(self, primary_color, secondary_color, accent_color):
        super().__init__(primary_color, secondary_color, accent_color)
        self.HEADER_SPACING = 0.6
        self.SECTION_SPACING = 0.4
        self.ITEM_SPACING = 0.2
    
    def create_header_style(self):
        """Create the TOC header style"""
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
    
    def build(self, toc_data):
        """Build the table of contents page"""
        # Implementation for TOC page
        pass

class ContentPage(Page):
    """Base class for content pages (sections, charts, tables)"""
    
    def __init__(self, primary_color, secondary_color, accent_color):
        super().__init__(primary_color, secondary_color, accent_color)
        self.SECTION_HEADER_SPACING = 0.6
        self.HEADER_TO_CONTENT_SPACING = 0.5
        self.ELEMENT_SPACING = 0.4
    
    def create_section_header_style(self):
        """Create section header style"""
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

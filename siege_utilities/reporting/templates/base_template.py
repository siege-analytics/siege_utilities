"""
Base ReportLab template for siege_utilities reporting system.
Enhanced version of the existing template with additional features.
"""

import logging
import yaml
from pathlib import Path
import requests
from hashlib import md5
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, PageBreak
from reportlab.lib.units import inch, cm, mm, pica
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus.flowables import Flowable
from reportlab.platypus import PageTemplate, Frame
from reportlab.lib.colors import HexColor
from typing import Dict, Any, Optional, List

# Import PIL for image dimension auto-calculation
try:
    from PIL import Image as PILImage
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    PILImage = None

log = logging.getLogger(__name__)

class BaseReportTemplate:
    """
    A base class for generating PDF reports using ReportLab.
    Enhanced version with additional features and better error handling.
    """

    def __init__(self, output_filename: str, branding_config_path: Optional[Path] = None, 
                 page_size: str = "letter", margins: Optional[Dict[str, float]] = None):
        """
        Initialize the base report template.
        
        Args:
            output_filename: Name of the output PDF file
            branding_config_path: Path to branding configuration YAML file
            page_size: Page size ('letter' or 'A4')
            margins: Custom margins in inches (top, bottom, left, right)
        """
        self.output_filename = output_filename
        self.branding_config_path = branding_config_path
        self.page_size = self._get_page_size(page_size)
        
        # Set up document with default margins
        default_margins = margins or {"top": 1.0, "bottom": 1.0, "left": 1.0, "right": 1.0}
        
        self.doc = SimpleDocTemplate(
            output_filename,
            pagesize=self.page_size,
            rightMargin=default_margins["right"] * inch,
            leftMargin=default_margins["left"] * inch,
            topMargin=default_margins["top"] * inch,
            bottomMargin=default_margins["bottom"] * inch
        )
        
        self.styles = getSampleStyleSheet()
        self.branding_config = self._load_config() if branding_config_path else {}
        self._register_fonts()
        self._add_custom_styles()
        self._doc_setup()
        self._create_cache_dir()

    def _get_page_size(self, page_size: str):
        """Get the ReportLab page size object."""
        page_sizes = {
            "letter": letter,
            "A4": A4,
            "a4": A4
        }
        return page_sizes.get(page_size.lower(), letter)

    def _load_config(self) -> dict:
        """Loads the branding configuration from a YAML file."""
        try:
            with open(self.branding_config_path, 'r') as f:
                config = yaml.safe_load(f)
            log.info(f"Configuration loaded successfully from {self.branding_config_path}")
            return config
        except FileNotFoundError:
            log.error(f"Branding config file not found: {self.branding_config_path}")
            return {}
        except yaml.YAMLError as e:
            log.error(f"Error parsing branding config YAML: {e}")
            return {}

    def _register_fonts(self):
        """Registers fonts specified in branding config or uses defaults."""
        # Default font registration
        try:
            # Try to register Liberation fonts if available
            font_paths = {
                "Liberation-Serif": {
                    "normal": "/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf",
                    "bold": "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf",
                    "italic": "/usr/share/fonts/truetype/liberation/LiberationSerif-Italic.ttf",
                    "bold_italic": "/usr/share/fonts/truetype/liberation/LiberationSerif-BoldItalic.ttf",
                }
            }
            
            registered_families = set()
            for font_family, font_paths_dict in font_paths.items():
                try:
                    # Check if font files exist
                    if Path(font_paths_dict["normal"]).exists():
                        pdfmetrics.registerFont(TTFont(font_family, font_paths_dict["normal"]))
                        log.info(f"Successfully registered font: {font_family} (Normal)")
                        
                        if 'bold' in font_paths_dict and Path(font_paths_dict["bold"]).exists():
                            pdfmetrics.registerFont(TTFont(f"{font_family}-Bold", font_paths_dict["bold"]))
                            log.info(f"Successfully registered font: {font_family}-Bold")
                        
                        if 'italic' in font_paths_dict and Path(font_paths_dict["italic"]).exists():
                            pdfmetrics.registerFont(TTFont(f"{font_family}-Italic", font_paths_dict["italic"]))
                            log.info(f"Successfully registered font: {font_family}-Italic")
                        
                        if 'bold_italic' in font_paths_dict and Path(font_paths_dict["bold_italic"]).exists():
                            pdfmetrics.registerFont(TTFont(f"{font_family}-BoldItalic", font_paths_dict["bold_italic"]))
                            log.info(f"Successfully registered font: {font_family}-BoldItalic")

                        pdfmetrics.registerFontFamily(
                            font_family,
                            normal=font_family,
                            bold=f"{font_family}-Bold" if 'bold' in font_paths_dict else font_family,
                            italic=f"{font_family}-Italic" if 'italic' in font_paths_dict else font_family,
                            boldItalic=f"{font_family}-BoldItalic" if 'bold_italic' in font_paths_dict else font_family,
                        )
                        log.info(f"Font family '{font_family}' processed.")
                        registered_families.add(font_family)
                except Exception as e:
                    log.error(f"Failed to register font family '{font_family}': {e}")

            # Set default styles to use registered fonts
            if "Liberation-Serif" in registered_families:
                self.styles['Normal'].fontName = "Liberation-Serif"
                self.styles['h1'].fontName = "Liberation-Serif-Bold"
                self.styles['h2'].fontName = "Liberation-Serif-Bold"
                self.styles['h3'].fontName = "Liberation-Serif-Bold"
                self.styles['BodyText'].fontName = "Liberation-Serif"
                log.info("Default styles updated to use Liberation-Serif fonts.")
            else:
                log.warning("Liberation-Serif not fully registered. Defaulting to standard ReportLab fonts.")
                
        except Exception as e:
            log.error(f"Error in font registration: {e}")

    def _add_custom_styles(self):
        """Adds or updates custom paragraph styles based on branding config."""
        if not self.branding_config:
            return
            
        colors = self.branding_config.get('colors', {})
        fonts = self.branding_config.get('fonts', {})

        default_text_color = HexColor(colors.get('text_color', '#000000'))

        # Update existing styles from branding config
        for style_name in ['h1', 'h2', 'h3', 'BodyText']:
            if style_name in self.styles:
                style = self.styles[style_name]
                style.textColor = default_text_color
                
                # Apply font from branding, ensuring it's registered
                font_family = fonts.get('default_font', 'Helvetica')
                if style_name in ['h1', 'h2', 'h3']:
                    style.fontName = f"{font_family}-Bold" if pdfmetrics.getFont(f"{font_family}-Bold") else font_family
                else:
                    style.fontName = font_family

                if style_name in fonts and 'font_size' in fonts[style_name]:
                    style.fontSize = fonts[style_name]['font_size']
                if style_name in fonts and 'leading' in fonts[style_name]:
                    style.leading = fonts[style_name]['leading']
                log.debug(f"Updating existing style: {style_name}")

        # Add new custom styles
        self.styles.add(ParagraphStyle(name='Caption',
                                       parent=self.styles['Normal'],
                                       fontSize=9,
                                       leading=10,
                                       alignment=TA_CENTER,
                                       textColor=default_text_color))

        self.styles.add(ParagraphStyle(name='Link',
                                       parent=self.styles['BodyText'],
                                       textColor=HexColor('#0000FF'),
                                       underline=1))

        # Header/Footer specific style
        self.styles.add(ParagraphStyle(name='HeaderFooter',
                                       parent=self.styles['Normal'],
                                       fontSize=9,
                                       textColor=HexColor(colors.get('header_footer_text_color', '#444444'))))

        log.info("Custom styles added/updated in stylesheet.")

    def _doc_setup(self):
        """Sets up document margins from branding config."""
        if not self.branding_config:
            return
            
        margins = self.branding_config.get('page_margins', {})
        self.doc.leftMargin = margins.get('left', 1) * inch
        self.doc.rightMargin = margins.get('right', 1) * inch
        self.doc.topMargin = margins.get('top', 1) * inch
        self.doc.bottomMargin = margins.get('bottom', 1) * inch
        log.info("Document margins set.")

    def _create_cache_dir(self):
        """Ensures the image cache directory exists."""
        cache_dir = Path.home() / ".siege_utilities" / "image_cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_dir = cache_dir
        log.info(f"Image cache directory ensured: {cache_dir}")

    def _get_image_data_for_reportlab(self, image_source: str):
        """
        Handles image loading for ReportLab. Supports local paths and URLs,
        with caching for URLs. Returns the path to the image data.
        """
        if image_source.startswith(('http://', 'https://')):
            image_hash = md5(image_source.encode('utf-8')).hexdigest()
            
            # Determine file extension based on content type
            ext = '.png'  # Default
            if 'jpg' in image_source.lower() or 'jpeg' in image_source.lower():
                ext = '.jpg'
            elif 'gif' in image_source.lower():
                ext = '.gif'

            cached_path = self.cache_dir / f"{image_hash}{ext}"

            if cached_path.exists():
                log.debug(f"Image found in cache: {cached_path}")
                return str(cached_path)

            log.info(f"Downloading image from URL: {image_source}")
            try:
                response = requests.get(image_source, stream=True, timeout=30)
                response.raise_for_status()

                # More robust extension determination from content type
                content_type = response.headers.get('Content-Type', '').lower()
                if 'image/jpeg' in content_type:
                    cached_path = cached_path.with_suffix('.jpg')
                elif 'image/png' in content_type:
                    cached_path = cached_path.with_suffix('.png')
                elif 'image/gif' in content_type:
                    cached_path = cached_path.with_suffix('.gif')

                with open(cached_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                log.info(f"Image cached to: {cached_path}")
                return str(cached_path)
            except requests.exceptions.RequestException as e:
                log.error(f"Error downloading image from {image_source}: {e}")
                return None
        else:
            local_path = Path(image_source)
            if local_path.exists():
                log.debug(f"Using local image file: {local_path}")
                return str(local_path)
            else:
                log.error(f"Local image file not found: {local_path}")
                return None

    def _header_footer_on_page(self, canvas, doc):
        """
        Callback function to draw headers and footers on each page.
        This is called by ReportLab's SimpleDocTemplate.
        """
        if not self.branding_config:
            return
            
        canvas.saveState()
        header_footer_style = self.styles['HeaderFooter']
        page_width, page_height = doc.pagesize

        header_config = self.branding_config.get('header', {})
        footer_config = self.branding_config.get('footer', {})
        main_logo_config = self.branding_config.get('logo', {})
        footer_logo_config = self.branding_config.get('footer_logo', {})

        # --- Header ---
        header_text_left = header_config.get('left_text', '')
        header_text_right = header_config.get('right_text', '')

        # Vertical position for header elements
        header_y_pos = page_height - (doc.topMargin / 2)

        # Draw Main Logo (if configured)
        current_header_x = doc.leftMargin
        if main_logo_config and main_logo_config.get('image_url'):
            logo_path = self._get_image_data_for_reportlab(main_logo_config['image_url'])
            if logo_path and PIL_AVAILABLE:
                try:
                    img_width = main_logo_config.get('width', 1.0) * inch
                    img_height = main_logo_config.get('height', 0) * inch

                    if img_height == 0:  # Auto-calculate height if not specified
                        with PILImage.open(logo_path) as img:
                            original_width, original_height = img.size
                            img_height = (img_width / original_width) * original_height

                    # Draw logo
                    canvas.drawImage(logo_path, current_header_x, header_y_pos - img_height/2,
                                     width=img_width, height=img_height, mask='auto')

                    current_header_x += img_width + 0.1 * inch
                except Exception as e:
                    log.error(f"Error drawing main header logo: {e}")

        # Left Header Text
        if header_text_left:
            P_left = Paragraph(header_text_left, header_footer_style)
            left_text_available_width = (page_width / 2) - current_header_x - 0.1 * inch
            P_left.wrapOn(canvas, left_text_available_width, doc.topMargin)
            P_left.drawOn(canvas, current_header_x, header_y_pos - P_left.height / 2)

        # Right Header Text
        if header_text_right:
            P_right = Paragraph(header_text_right, header_footer_style)
            text_width = P_right.wrapOn(canvas, page_width - doc.leftMargin - doc.rightMargin, doc.topMargin)[0]
            P_right.drawOn(canvas, page_width - doc.rightMargin - text_width, header_y_pos - P_right.height / 2)

        # --- Footer ---
        footer_text_left = footer_config.get('left_text', '')
        footer_text_right = footer_config.get('right_text', '')
        page_number_format = footer_config.get('page_number_format', 'Page %s')

        # Vertical position for footer elements
        footer_y_pos = doc.bottomMargin / 2

        # Draw Footer Logo (if configured)
        current_footer_x = doc.leftMargin
        if footer_logo_config and footer_logo_config.get('image_url'):
            footer_logo_path = self._get_image_data_for_reportlab(footer_logo_config['image_url'])
            if footer_logo_path and PIL_AVAILABLE:
                try:
                    footer_img_width = footer_logo_config.get('width', 0.5) * inch
                    footer_img_height = footer_logo_config.get('height', 0) * inch

                    if footer_img_height == 0:  # Auto-calculate height if not specified
                        with PILImage.open(footer_logo_path) as img:
                            original_width, original_height = img.size
                            footer_img_height = (footer_img_width / original_width) * original_height

                    canvas.drawImage(footer_logo_path, current_footer_x, footer_y_pos - footer_img_height / 2,
                                     width=footer_img_width, height=footer_img_height, mask='auto')
                    current_footer_x += footer_img_width + 0.1 * inch
                except Exception as e:
                    log.error(f"Error drawing footer logo: {e}")

        # Left Footer Text
        if footer_text_left:
            F_left = Paragraph(footer_text_left, header_footer_style)
            footer_left_text_available_width = (page_width / 2) - current_footer_x - 0.1 * inch
            F_left.wrapOn(canvas, footer_left_text_available_width, doc.bottomMargin)
            F_left.drawOn(canvas, current_footer_x, footer_y_pos - F_left.height / 2)

        # Right Footer Text
        if footer_text_right:
            F_right = Paragraph(footer_text_right, header_footer_style)
            text_width_f = F_right.wrapOn(canvas, page_width - doc.leftMargin - doc.rightMargin, doc.bottomMargin)[0]
            F_right.drawOn(canvas, page_width - doc.rightMargin - text_width_f, footer_y_pos - F_right.height / 2)

        # Page Number
        page_number_text = page_number_format % doc.page
        P_page_num = Paragraph(page_number_text, header_footer_style)
        P_page_num.wrapOn(canvas, page_width, doc.bottomMargin)
        page_num_x_pos = page_width - doc.rightMargin - P_page_num.wrapOn(canvas, page_width, doc.bottomMargin)[0]
        P_page_num.drawOn(canvas, page_num_x_pos, footer_y_pos - P_page_num.height / 2 - 0.2 * inch)

        canvas.restoreState()

    def _get_page_templates(self):
        """
        Defines and returns a list of PageTemplate objects.
        This allows for complex page layouts (e.g., headers, footers, multiple frames).
        """
        # Define the main frame for content
        main_frame = Frame(
            self.doc.leftMargin,
            self.doc.bottomMargin,
            self.doc.width,
            self.doc.height,
            id='normal_frame',
            showBoundary=0
        )

        return [
            PageTemplate(
                id='Normal',
                frames=[main_frame],
                onPage=self._header_footer_on_page
            )
        ]

    def build_document(self, story: list):
        """
        Builds the PDF document using the provided story and page templates.
        
        Args:
            story: List of ReportLab flowables to include in the document
        """
        try:
            self.doc.pageTemplates = self._get_page_templates()
            self.doc.build(story)
            log.info(f"Document '{self.output_filename}' built successfully.")
        except Exception as e:
            log.error(f"Error building document '{self.output_filename}': {e}", exc_info=True)
            raise

    def generate_report(self, report_data: dict):
        """
        Abstract method to be implemented by concrete report classes.
        This method should populate the 'story' list with ReportLab flowables.
        
        Args:
            report_data: Dictionary containing data needed for the report
        """
        raise NotImplementedError("Subclasses must implement generate_report method")

    def add_title_page(self, title: str, subtitle: str = "", author: str = "", date: str = ""):
        """
        Add a title page to the report.
        
        Args:
            title: Main title of the report
            subtitle: Subtitle or description
            author: Author of the report
            date: Date of the report
        """
        story = []
        
        # Title
        story.append(Paragraph(title, self.styles['h1']))
        story.append(Spacer(1, 0.3 * inch))
        
        # Subtitle
        if subtitle:
            story.append(Paragraph(subtitle, self.styles['h2']))
            story.append(Spacer(1, 0.2 * inch))
        
        # Author
        if author:
            story.append(Paragraph(f"Prepared by: {author}", self.styles['BodyText']))
            story.append(Spacer(1, 0.1 * inch))
        
        # Date
        if date:
            story.append(Paragraph(f"Date: {date}", self.styles['BodyText']))
            story.append(Spacer(1, 0.3 * inch))
        
        story.append(PageBreak())
        return story

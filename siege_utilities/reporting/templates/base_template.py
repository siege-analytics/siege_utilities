"""
Base ReportLab template for siege_utilities reporting system.
Enhanced version of the existing template with additional features.
"""

import copy
import logging
import yaml
from pathlib import Path
import requests
from hashlib import md5

from siege_utilities.files.operations import atomic_write_path
try:
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_RIGHT
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
    from reportlab.lib.units import inch
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.platypus import PageTemplate, Frame
    from reportlab.lib.colors import HexColor
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False
    getSampleStyleSheet = ParagraphStyle = None
    TA_CENTER = TA_RIGHT = None
    pdfmetrics = None
    TTFont = None
    SimpleDocTemplate = Paragraph = Spacer = PageBreak = None
    inch = None
    letter = A4 = None
    PageTemplate = Frame = None
    HexColor = None
from typing import Dict, Optional

from .._brand_colors import BRANDING_SECTIONS, brand_color, validate_branding_layout
from ..client_branding import BrandingConfigError
from .._markup import _escape_paragraph

# Import PIL for image dimension auto-calculation
try:
    from PIL import Image as PILImage
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    PILImage = None

__all__ = [
    'BaseReportTemplate',
]

log = logging.getLogger(__name__)

class BaseReportTemplate:
    """
    A base class for generating PDF reports using ReportLab.
    Enhanced version with additional features and better error handling.
    """

    def __init__(self, output_filename: str, branding_config_path: Optional[Path] = None,
                 page_size: str = "letter", margins: Optional[Dict[str, float]] = None,
                 branding_config: Optional[dict] = None,
                 fetch_remote_assets: bool = False):
        """
        Initialize the base report template.

        Args:
            output_filename: Name of the output PDF file
            branding_config_path: Path to branding configuration YAML file
            page_size: Page size ('letter' or 'A4')
            margins: Custom margins in inches (top, bottom, left, right)
            branding_config: Branding dictionary (the shape
                ``ClientBrandingManager`` returns), used instead of a YAML
                file. It is copied. Without either, the report is unbranded:
                no header, footer or page numbers.
            fetch_remote_assets: Download ``http(s)`` logo URLs from the
                branding. Off by default, so building a PDF makes no network
                calls: remote logos are left out (logged once per document)
                and local logo paths still work.

        Raises:
            ImportError: If ReportLab is not installed.
            ValueError: If both ``branding_config_path`` and
                ``branding_config`` are given.
            BrandingColorError: If a branding text colour is not a colour.
            BrandingConfigError: If the branding is not a mapping, a layout
                entry has the wrong shape, or the margins leave less than
                72 pt for the page frame either way.
        """
        if not REPORTLAB_AVAILABLE:
            raise ImportError(
                "reportlab is required for PDF report generation but is not installed. "
                "Install it with: pip install reportlab"
            )
        if branding_config_path and branding_config:
            raise ValueError(
                "Pass either branding_config_path or branding_config, not both"
            )
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
        if branding_config_path:
            loaded = self._load_config()
        else:
            loaded = copy.deepcopy(branding_config)
        self.branding_config = self._checked_branding(loaded)
        self.fetch_remote_assets = fetch_remote_assets
        # Images that could not be fetched, so each is tried once per document,
        # and downloaded images by URL (the saved name can differ from the URL).
        self._unavailable_images = set()
        self._fetched_images = {}
        self._remote_skip_logged = False
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
        """Loads the branding configuration from a YAML file.

        Raises:
            FileNotFoundError: If the branding config file does not exist.
            yaml.YAMLError: If the YAML is malformed.
        """
        with open(self.branding_config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        log.info(f"Configuration loaded successfully from {self.branding_config_path}")
        return config

    def _register_fonts(self):
        """Registers fonts specified in branding config or uses defaults."""
        # Default font registration. Candidate locations differ per OS:
        # Linux ships Liberation under /usr/share/fonts/truetype/liberation,
        # macOS under /Library/Fonts (and /System/Library/Fonts since
        # Catalina), Windows under C:\Windows\Fonts. Probe each in turn —
        # the previous hard-coded Linux path silently failed everywhere
        # else and fell through to ReportLab's defaults with no warning.
        try:
            import sys
            _LIBERATION_CANDIDATES = {
                "linux": "/usr/share/fonts/truetype/liberation",
                "darwin": "/Library/Fonts",
                "win32": r"C:\Windows\Fonts",
            }
            base = _LIBERATION_CANDIDATES.get(sys.platform, _LIBERATION_CANDIDATES["linux"])
            font_paths = {
                "Liberation-Serif": {
                    "normal": f"{base}/LiberationSerif-Regular.ttf",
                    "bold": f"{base}/LiberationSerif-Bold.ttf",
                    "italic": f"{base}/LiberationSerif-Italic.ttf",
                    "bold_italic": f"{base}/LiberationSerif-BoldItalic.ttf",
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
                except (OSError, ValueError, KeyError) as e:
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
                
        except (OSError, ValueError, KeyError, AttributeError) as e:
            log.error(f"Error in font registration: {e}")

    @staticmethod
    def _checked_branding(branding) -> dict:
        """Validate the branding and give unset (``None``) sections as empty mappings.

        Raises:
            BrandingConfigError: If the branding or one of its entries has
                the wrong shape.
        """
        if branding is None:
            return {}
        if not isinstance(branding, dict):
            raise BrandingConfigError(f"branding must be a mapping, got {branding!r}")
        validate_branding_layout(branding)
        for name in BRANDING_SECTIONS:
            if name in branding and branding[name] is None:
                branding[name] = {}
        return branding

    @staticmethod
    def _font_registered(font_name: str) -> bool:
        """True if ReportLab can draw *font_name* (a standard or registered font)."""
        return font_name in pdfmetrics.standardFonts or font_name in pdfmetrics.getRegisteredFontNames()

    def _add_custom_styles(self):
        """Adds or updates custom paragraph styles based on branding config."""
        if not self.branding_config:
            return
            
        colors = self.branding_config.get('colors') or {}
        fonts = self.branding_config.get('fonts') or {}

        default_text_color = brand_color(colors.get('text_color', '#000000'), 'text_color')

        # Apply the brand font only if it is registered (e.g. Liberation-Serif
        # is registered only where its files are installed); otherwise
        # ReportLab raises KeyError mid-build.
        font_family = fonts.get('default_font') or 'Helvetica'
        if not self._font_registered(font_family):
            log.warning("Branding font %r is not registered; using Helvetica", font_family)
            font_family = 'Helvetica'
        bold_font = f"{font_family}-Bold"
        heading_font = bold_font if self._font_registered(bold_font) else font_family

        # Update existing styles from branding config
        for style_name in ['h1', 'h2', 'h3', 'BodyText']:
            if style_name in self.styles:
                style = self.styles[style_name]
                style.textColor = default_text_color
                style.fontName = heading_font if style_name in ['h1', 'h2', 'h3'] else font_family

                metrics = fonts.get(style_name) or {}
                if metrics.get('font_size') is not None:
                    style.fontSize = metrics['font_size']
                if metrics.get('leading') is not None:
                    style.leading = metrics['leading']
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
                                       textColor=brand_color(colors.get('header_footer_text_color', '#444444'),
                                                             'header_footer_text_color')))

        log.info("Custom styles added/updated in stylesheet.")

    def _doc_setup(self):
        """Sets up document margins from branding config.

        Raises:
            BrandingConfigError: If the margins leave less than 72 pt for the
                page frame across or down.
        """
        if not self.branding_config:
            return

        margins = self.branding_config.get('page_margins') or {}

        def margin(side):
            value = margins.get(side)
            return (1 if value is None else value) * inch

        self.doc.leftMargin = margin('left')
        self.doc.rightMargin = margin('right')
        self.doc.topMargin = margin('top')
        self.doc.bottomMargin = margin('bottom')
        # SimpleDocTemplate derives width/height from the margins only in
        # _calc(); without it the frame and table fitting use stale sizes.
        self.doc._calc()
        if self.doc.width < inch or self.doc.height < inch:
            raise BrandingConfigError(
                f"branding page_margins {margins!r} leave a {self.doc.width:.0f} x "
                f"{self.doc.height:.0f} pt page frame; at least 72 pt each way is needed"
            )
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
        with caching for URLs. Returns the path to the image data, or None
        (logged) when it cannot be had. URLs are used only when the template
        was created with ``fetch_remote_assets=True``; otherwise they are
        skipped without any network or cache access. A URL that failed is not
        retried for the rest of this document, so a missing logo costs one
        attempt rather than one per page.
        """
        if image_source in self._unavailable_images:
            return None
        if image_source in self._fetched_images:
            return self._fetched_images[image_source]
        is_remote = image_source.startswith(('http://', 'https://'))
        if is_remote and not self.fetch_remote_assets:
            self._unavailable_images.add(image_source)
            if not self._remote_skip_logged:
                self._remote_skip_logged = True
                log.info(
                    "Remote branding images (such as %s) are not downloaded; "
                    "pass fetch_remote_assets=True to include them", image_source,
                )
            return None
        if is_remote:
            # Known bandit B324 finding, suppressed here and tracked in #1754.
            image_hash = md5(image_source.encode('utf-8')).hexdigest()  # nosec B324
            
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
            # Cleared below once the download succeeds.
            self._unavailable_images.add(image_source)
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

                with atomic_write_path(cached_path) as tmp:
                    with open(tmp, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            f.write(chunk)
                log.info(f"Image cached to: {cached_path}")
                self._unavailable_images.discard(image_source)
                # The saved name follows the Content-Type, which can differ
                # from the URL-derived name looked up above; remember it.
                self._fetched_images[image_source] = str(cached_path)
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
                # Logged once per document, not on every page.
                self._unavailable_images.add(image_source)
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
                except (OSError, ValueError, TypeError, AttributeError) as e:
                    log.error(f"Error drawing main header logo: {e}")

        # Left Header Text
        if header_text_left:
            P_left = Paragraph(_escape_paragraph(header_text_left), header_footer_style)
            left_text_available_width = (page_width / 2) - current_header_x - 0.1 * inch
            P_left.wrapOn(canvas, left_text_available_width, doc.topMargin)
            P_left.drawOn(canvas, current_header_x, header_y_pos - P_left.height / 2)

        # Right-aligned text lives in the right half of the page, flush with the
        # right margin. Paragraph.wrapOn() returns the width it was *given*, not
        # the text width, so it cannot be used to compute an x offset (#1998).
        # Instead draw into a fixed-width box with right alignment; long text
        # wraps inside the box rather than spilling onto the left-hand text.
        right_edge = page_width - doc.rightMargin
        right_box_width = max(right_edge - page_width / 2 - 0.1 * inch, 0.5 * inch)
        gap = self._HEADER_FOOTER_GAP

        # Right Header Text: kept inside the top margin, truncated if too long.
        if header_text_right:
            self._draw_right_aligned(canvas, header_text_right, header_footer_style,
                                     right_edge, right_box_width, header_y_pos,
                                     doc.topMargin,
                                     bottom_limit=page_height - doc.topMargin + gap,
                                     top_limit=page_height - gap)

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
                except (OSError, ValueError, TypeError, AttributeError) as e:
                    log.error(f"Error drawing footer logo: {e}")

        # Left Footer Text
        if footer_text_left:
            F_left = Paragraph(_escape_paragraph(footer_text_left), header_footer_style)
            footer_left_text_available_width = (page_width / 2) - current_footer_x - 0.1 * inch
            F_left.wrapOn(canvas, footer_left_text_available_width, doc.bottomMargin)
            F_left.drawOn(canvas, current_footer_x, footer_y_pos - F_left.height / 2)

        # Page Number (bottom-right, just below the footer line), kept on the page.
        page_number_text = page_number_format % doc.page
        page_number_y, page_number_height = self._draw_right_aligned(
            canvas, page_number_text, header_footer_style, right_edge, right_box_width,
            footer_y_pos - 0.2 * inch, doc.bottomMargin,
            bottom_limit=gap, top_limit=doc.bottomMargin - gap)

        # Right Footer Text: stays above the page number and below the body
        # frame. Wrapped text moves up rather than over the page number, and
        # text that still does not fit is truncated.
        if footer_text_right:
            self._draw_right_aligned(canvas, footer_text_right, header_footer_style,
                                     right_edge, right_box_width, footer_y_pos,
                                     doc.bottomMargin,
                                     bottom_limit=page_number_y + page_number_height + gap,
                                     top_limit=doc.bottomMargin - gap)

        canvas.restoreState()

    # Clearance (points) kept between header/footer blocks and between them
    # and the page edge or body frame.
    _HEADER_FOOTER_GAP = 2.0
    _ELLIPSIS = "…"

    @classmethod
    def _draw_right_aligned(cls, canvas, text, style, right_edge, box_width,
                            center_y, max_height, bottom_limit=None, top_limit=None):
        """Draw ``text`` right-aligned so its lines end at ``right_edge``.

        The paragraph is laid out in a ``box_width``-wide box whose right side
        is ``right_edge``, vertically centred on ``center_y``. Lines longer
        than the box wrap inside it. Text whose wrapped height exceeds
        ``max_height`` (or the band between ``bottom_limit`` and
        ``top_limit``, when given) is cut and ends with an ellipsis; at least
        one line is always drawn. When limits are given the block is moved,
        as little as possible, to stay between them.

        Returns:
            ``(y, height)`` of the drawn block's bottom edge and height.
        """
        right_style = ParagraphStyle(name=f"{style.name}-right", parent=style,
                                     alignment=TA_RIGHT)
        if bottom_limit is not None and top_limit is not None:
            max_height = min(max_height, top_limit - bottom_limit)
        paragraph, height = cls._fit_paragraph(canvas, text, right_style,
                                               box_width, max_height)
        y = center_y - height / 2
        if top_limit is not None:
            y = min(y, top_limit - height)
        if bottom_limit is not None:
            y = max(y, bottom_limit)
        paragraph.drawOn(canvas, right_edge - box_width, y)
        return y, height

    @classmethod
    def _fit_paragraph(cls, canvas, text, style, width, max_height):
        """Paragraph for ``text`` no taller than ``max_height`` (one line minimum).

        Too-tall text is replaced by its longest prefix that, followed by an
        ellipsis, still fits.
        """
        def build(candidate):
            paragraph = Paragraph(_escape_paragraph(candidate), style)
            _, height = paragraph.wrapOn(canvas, width, max_height)
            return paragraph, height

        paragraph, height = build(text)
        if height <= max_height or len(text) <= 1:
            return paragraph, height
        lo, hi = 0, len(text) - 1
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if build(text[:mid].rstrip() + cls._ELLIPSIS)[1] <= max_height:
                lo = mid
            else:
                hi = mid - 1
        return build(text[:lo].rstrip() + cls._ELLIPSIS)

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
            # SimpleDocTemplate.build appends its own 'First'/'Later' page
            # templates and switches to 'Later' after page 1, so the header
            # and footer callback must also be given for later pages.
            self.doc.pageTemplates = self._get_page_templates()
            if any(flowable.isIndexing() for flowable in story):
                previous_after_flowable = self.doc.afterFlowable

                def record_toc_entry(flowable):
                    previous_after_flowable(flowable)
                    entry = getattr(flowable, '_toc_entry', None)
                    if entry is not None:
                        level, title = entry
                        self.doc.notify('TOCEntry', (level, title, self.doc.page))

                self.doc.afterFlowable = record_toc_entry
                try:
                    self.doc.multiBuild(story, onLaterPages=self._header_footer_on_page)
                finally:
                    self.doc.afterFlowable = previous_after_flowable
            else:
                self.doc.build(story, onLaterPages=self._header_footer_on_page)
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
        # #1206: abstract/extension-point placeholder; keep tracked until implemented or abstracted.
        raise NotImplementedError("Subclasses must implement generate_report method")

    def add_title_page(self, title: str, subtitle: str = "", author: str = "", date: str = "", client: str = ""):
        """
        Add a title page to the report.
        
        Args:
            title: Main title of the report
            subtitle: Subtitle or description
            author: Author of the report
            date: Date of the report
            client: Client for whom the report was prepared
        """
        story = []
        
        # Title
        story.append(Paragraph(_escape_paragraph(title), self.styles['h1']))
        story.append(Spacer(1, 0.3 * inch))
        
        # Subtitle
        if subtitle:
            story.append(Paragraph(_escape_paragraph(subtitle), self.styles['h2']))
            story.append(Spacer(1, 0.2 * inch))
        
        # Author
        if author:
            story.append(Paragraph(f"Prepared by: {_escape_paragraph(author)}", self.styles['BodyText']))
            story.append(Spacer(1, 0.1 * inch))
        
        # Client
        if client:
            story.append(Paragraph(f"Prepared for: {_escape_paragraph(client)}", self.styles['BodyText']))
            story.append(Spacer(1, 0.1 * inch))

        # Date
        if date:
            story.append(Paragraph(f"Date: {_escape_paragraph(date)}", self.styles['BodyText']))
            story.append(Spacer(1, 0.3 * inch))
        
        story.append(PageBreak())
        return story

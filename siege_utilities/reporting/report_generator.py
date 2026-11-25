"""
Main report generator for siege_utilities reporting system.
Orchestrates the creation of comprehensive reports with charts, tables, and branding.
"""

import copy
import logging
import os
import re
import uuid
from dataclasses import dataclass
from numbers import Number
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
import pandas as pd

# Try to import PIL Image, fall back to Any if not available
try:
    from PIL import Image
    ImageType = Image.Image
except ImportError:
    ImageType = Any

# ReportLab imports for PDF generation
try:
    from reportlab.platypus import Paragraph, Spacer, Table, TableStyle, PageBreak
    from reportlab.platypus import Flowable, XPreformatted
    from reportlab.platypus import Image as RLImage
    from reportlab.platypus.tableofcontents import TableOfContents
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.pdfbase.pdfmetrics import stringWidth
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False
    Flowable = None
    XPreformatted = None
    TA_CENTER = None
    ParagraphStyle = None
    stringWidth = None
    Paragraph = None
    Spacer = None
    Table = None
    TableStyle = None
    PageBreak = None
    RLImage = None
    TableOfContents = None
    colors = None
    inch = None

from ._brand_colors import (
    AA_GRAPHIC_CONTRAST, brand_color, contrast_ratio, readable_text_color,
    validate_brand_colors, validate_branding_layout,
)
from ._markup import _escape_paragraph
from .templates.base_template import BaseReportTemplate
from .chart_generator import ChartGenerator
from .client_branding import ClientBrandingManager, ClientBrandingNotFoundError

log = logging.getLogger(__name__)

__all__ = [
    "ReportGenerator",
    "TableRowTooTallError",
]


class TableRowTooTallError(ValueError):
    """Raised when a report table row is taller than a page and cannot be split.

    Rows of text are split across pages; a row holding an image or several
    flowables taller than a page cannot be. The message names the table
    section, row and column. No PDF is written.
    """

# ReportLab defaults: a Frame pads 6 pt on each side, and so does a table cell.
_FRAME_PADDING = 12
_CELL_PADDING = 12
# Narrowest a shrunk table column may become (12 pt of text plus padding).
_MIN_COLUMN_WIDTH = 24
# Extra width on a word or number floor so float round-off never breaks it.
_WIDTH_SLACK = 1.0
# Formatted numbers, amounts, percentages, dates, phone numbers, ZIP codes.
_NUMERIC_CHARACTERS = frozenset("0123456789.,:/%$€£¥()+-' ")
_MAX_NUMERIC_TOKEN = 40
# Room a repeated header row must leave on a page for body rows.
_MIN_BODY_HEIGHT = 72
# Vertical cell padding: ReportLab's 3 pt top and bottom; the style gives the
# first row 10 pt at the bottom, 7 pt more.
_BODY_ROW_PADDING = 6
_HEADER_EXTRA_PADDING = 7
# Fonts of the table style: row 0 is the header row, as it always has been.
_HEADER_FONT = ('Helvetica-Bold', 10)
_BODY_FONT = ('Helvetica', 9)


@dataclass(frozen=True)
class _TablePalette:
    """Colours of a report table, from the branding config or the defaults."""

    header_background: Any
    header_text: Any
    body_background: Any
    body_text: Any
    grid: Any

    def commands(self) -> List[tuple]:
        """Return the TableStyle commands; unbranded, they are the 4.x style."""
        return [
            ('BACKGROUND', (0, 0), (-1, 0), self.header_background),
            ('TEXTCOLOR', (0, 0), (-1, 0), self.header_text),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), _HEADER_FONT[0]),
            ('FONTSIZE', (0, 0), (-1, 0), _HEADER_FONT[1]),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
            ('BACKGROUND', (0, 1), (-1, -1), self.body_background),
            ('TEXTCOLOR', (0, 1), (-1, -1), self.body_text),
            ('FONTNAME', (0, 1), (-1, -1), _BODY_FONT[0]),
            ('FONTSIZE', (0, 1), (-1, -1), _BODY_FONT[1]),
            ('GRID', (0, 0), (-1, -1), 0.5, self.grid),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]

    def header_commands(self, first_row: int, last_row: int) -> List[tuple]:
        """Header-row look for rows *first_row*..*last_row* (a split first row)."""
        start, stop = (0, first_row), (-1, last_row)
        return [
            ('BACKGROUND', start, stop, self.header_background),
            ('TEXTCOLOR', start, stop, self.header_text),
            ('FONTNAME', start, stop, _HEADER_FONT[0]),
            ('FONTSIZE', start, stop, _HEADER_FONT[1]),
        ]

    def paragraph_style(self, row_index: int) -> 'ParagraphStyle':
        """Return the style a wrapped cell needs to look like the row's text."""
        is_header = row_index == 0
        font_name, font_size = _HEADER_FONT if is_header else _BODY_FONT
        return ParagraphStyle(
            'su_table_header' if is_header else 'su_table_body',
            fontName=font_name, fontSize=font_size, leading=font_size * 1.2,
            textColor=self.header_text if is_header else self.body_text,
            alignment=TA_CENTER,
        )


def _is_flowable_cell(cell: Any) -> bool:
    """True for cells ReportLab lays out itself: a flowable or a list of them."""
    if isinstance(cell, Flowable):
        return True
    return isinstance(cell, (list, tuple)) and bool(cell) and all(
        isinstance(item, Flowable) for item in cell
    )


@dataclass(frozen=True)
class _CellWidths:
    """Widths one cell needs, cell padding included."""

    natural: float  # everything on one line (flowables: at most the frame)
    whole_words: float  # the longest word or number, so nothing is broken
    unbreakable: float  # numbers are never split; text and flowables can be


def _cell_widths(cell: Any, font: tuple, avail_width: float) -> _CellWidths:
    """Measure a cell for column fitting."""
    if cell is None:
        return _CellWidths(_CELL_PADDING, _CELL_PADDING, _CELL_PADDING)
    if _is_flowable_cell(cell):
        natural = whole_words = 0.0
        for item in (cell if isinstance(cell, (list, tuple)) else [cell]):
            width, _ = item.wrapOn(None, avail_width, 1e6)
            line_widths = getattr(item, 'getActualLineWidths0', None)
            narrowest = width
            if line_widths is not None:
                # Text flowables: the longest line, and the longest word.
                width = max(line_widths(), default=0.0)
                narrowest = min(item.minWidth(), width)
            # Other flowables (images, drawings) keep their wrapped width; their
            # minWidth() may read attributes they do not have.
            natural = max(natural, width)
            whole_words = max(whole_words, narrowest)
        return _CellWidths(natural + _CELL_PADDING, whole_words + _CELL_PADDING, _CELL_PADDING)
    text = _cell_text(cell)
    natural = max(stringWidth(line, *font) for line in text.split('\n')) + _CELL_PADDING
    if isinstance(cell, Number) or _looks_numeric(text):
        # A wrapped cell is laid out in colWidth - padding; the slack keeps
        # float round-off in that subtraction from breaking the token.
        return _CellWidths(natural, natural + _WIDTH_SLACK, natural + _WIDTH_SLACK)
    words = text.split()
    whole_words = max((stringWidth(word, *font) for word in words), default=0.0)
    return _CellWidths(natural, whole_words + _CELL_PADDING + _WIDTH_SLACK, _CELL_PADDING)


def _looks_numeric(text: str) -> bool:
    """True for a formatted number, amount, percentage, date, phone or ZIP code.

    Such strings (``"1,234,567.89"``, ``"$12.50"``, ``"45.25%"``,
    ``"(1,234)"``, ``"2026-11-23"``, ``"512-555-0100"``) are kept whole like
    numbers, because breaking one inside makes it read as two values.
    """
    token = text.strip()
    return (
        0 < len(token) <= _MAX_NUMERIC_TOKEN
        and any(character.isdigit() for character in token)
        and set(token) <= _NUMERIC_CHARACTERS
    )


def _widths_at_least(floors: List[float], natural: List[float], avail_width: float) -> List[float]:
    """Fit columns into *avail_width* without going below *floors*.

    Every column gets ``min(max(level, floor), natural)`` for the largest
    level that fits, so columns needing less than the level keep their
    natural width and the wider ones share the rest equally. When the
    floors alone are wider than *avail_width*, the floors are returned.
    """
    if sum(floors) >= avail_width:
        return list(floors)
    low, high = 0.0, max(natural)
    for _ in range(60):
        level = (low + high) / 2
        total = sum(min(max(level, floor), need) for floor, need in zip(floors, natural))
        if total > avail_width:
            high = level
        else:
            low = level
    return [min(max(low, floor), need) for floor, need in zip(floors, natural)]


def _fit_column_widths(columns: List[List[_CellWidths]], avail_width: float) -> List[float]:
    """Choose column widths for a table wider than *avail_width*.

    First without breaking any word or number; if that cannot fit, text
    may break down to ``_MIN_COLUMN_WIDTH`` per column, but numbers are
    never split. The result can still be wider than *avail_width*.
    """
    natural = [max(cell.natural for cell in column) for column in columns]
    whole_words = [min(max(cell.whole_words for cell in column), need)
                   for column, need in zip(columns, natural)]
    widths = _widths_at_least(whole_words, natural, avail_width)
    if sum(widths) <= avail_width + 0.01:
        return widths
    unbreakable = [
        min(max(_MIN_COLUMN_WIDTH, max(cell.unbreakable for cell in column)), need)
        for column, need in zip(columns, natural)
    ]
    return _widths_at_least(unbreakable, natural, avail_width)


def _preformatted_cell(text: str, style: 'ParagraphStyle') -> 'XPreformatted':
    """Keep a multi-line plain string's lines exactly, as a splittable flowable."""
    return XPreformatted(_escape_paragraph(text.replace('\r\n', '\n')), style)


def _cell_text(value: Any) -> str:
    """The text a plain table cell shows: ``None`` empty, bytes decoded, else ``str``."""
    if value is None:
        return ''
    if isinstance(value, (bytes, bytearray)):
        return bytes(value).decode('utf-8', 'replace')
    return str(value)


def _cell_chunks(cell: Any, width: float, height: float, style: 'ParagraphStyle',
                 title: str, row: int, column: int) -> List[Any]:
    """Cut one cell of a too-tall row into pieces no taller than *height*.

    Plain values become preformatted text (lines kept, nothing dropped);
    flowables are split with their own ``split``. Every piece is a flowable,
    so ReportLab never has to split inside a row.

    Raises:
        TableRowTooTallError: If the cell is taller than *height* and cannot
            be split, or splitting stops making progress.
    """
    def too_tall(reason: str) -> TableRowTooTallError:
        return TableRowTooTallError(
            f"Table section {title!r}: row {row}, column {column} is taller than a page and "
            f"{reason}; shorten it or split it into several rows"
        )

    if isinstance(cell, (list, tuple)) and _is_flowable_cell(cell):
        total = sum(item.wrapOn(None, width, 1e6)[1] for item in cell)
        if total <= height:
            return [cell]
        raise too_tall("holds several flowables, which cannot be split")
    flowable = cell if isinstance(cell, Flowable) else _preformatted_cell(_cell_text(cell), style)
    chunks: List[Any] = []
    while True:
        _, current = flowable.wrapOn(None, width, 1e6)
        if current <= height:
            chunks.append(flowable)
            return chunks
        parts = flowable.splitOn(None, width, height)
        if len(parts) != 2:
            raise too_tall(f"its {type(flowable).__name__} cannot be split")
        first, rest = parts
        _, first_height = first.wrapOn(None, width, 1e6)
        _, rest_height = rest.wrapOn(None, width, 1e6)
        if first_height > height or rest_height >= current:
            raise too_tall(f"its {type(flowable).__name__} does not split into page-sized parts")
        chunks.append(first)
        flowable = rest


def _wrapped_cell(cell: Any, style: 'ParagraphStyle') -> 'Paragraph':
    """Wrap a plain value: escaped, ``None`` empty, bytes decoded, line breaks kept."""
    text = _escape_paragraph(_cell_text(cell))
    text = text.replace('\r\n', '\n').replace('\n', '<br/>')
    return Paragraph(text, style)


class ReportGenerator:
    """
    Main report generator that creates comprehensive reports.
    Integrates templates, charts, and data sources.
    """

    def __init__(self, client_name: str, output_dir: Optional[Path] = None,
                 branding_config: Optional[Dict[str, Any]] = None,
                 fetch_remote_assets: bool = False):
        """
        Initialize the report generator.

        Args:
            client_name: Name of the client for branding
            output_dir: Directory for output reports
            branding_config: Optional branding dictionary in the shape
                ``ClientBrandingManager`` stores (``colors``, ``fonts``,
                ``header``, ``footer``, ``page_margins``, ``logo``). It is
                copied and used for the charts, the tables and the page
                template, without registering a client profile. ``None``
                (the default) looks the branding up by ``client_name``; an
                empty dict gives an unbranded report even for a known client.
            fetch_remote_assets: Download ``http(s)`` logo URLs from the
                branding when building a PDF. Off by default, so PDF builds
                make no network calls: remote logos are left out (logged once
                per document) and local logo paths still work.

        Raises:
            TypeError: If ``branding_config`` is neither None nor a dict.
            BrandingColorError: If a ``colors`` entry the reports use
                (``primary``, ``secondary``, ``accent``, ``text_color``,
                ``header_footer_text_color``) is present but not a colour.
            BrandingConfigError: If a page-layout entry (``fonts``,
                ``header``, ``footer``, ``logo``, ``page_margins``) has the
                wrong shape.
        """
        self.client_name = client_name
        self.fetch_remote_assets = fetch_remote_assets
        self.output_dir = output_dir or Path.cwd() / "reports"
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.branding_manager = ClientBrandingManager()
        if branding_config is not None:
            if not isinstance(branding_config, dict):
                raise TypeError(
                    f"branding_config must be a dict or None, got {type(branding_config).__name__}"
                )
            self.branding_config = copy.deepcopy(branding_config)
        else:
            try:
                self.branding_config = self.branding_manager.get_client_branding(client_name)
            except ClientBrandingNotFoundError:
                log.warning(f"No branding configuration found for {client_name}, using defaults")
                self.branding_config = {}
        # Charts hand these colours to matplotlib/seaborn at once, so a bad
        # one is reported here, by name, rather than as a palette error; the
        # page-layout entries are checked here too, before any PDF is built.
        validate_brand_colors(self.branding_config)
        validate_branding_layout(self.branding_config)

        self.chart_generator = ChartGenerator(
            self.branding_config, output_dir=self.output_dir,
            max_chart_width=6.0, max_chart_height=8.5,
        )

    def create_analytics_report(self, title: str, charts: List[ImageType], 
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
                          table_data: Union[List[List], List[Dict[str, Any]], pd.DataFrame],
                          headers: List[str] = None, level: int = 1,
                          table_style: str = "default",
                          sort_by: Optional[Union[int, str]] = None,
                          sort_order: str = "asc") -> Dict[str, Any]:
        """
        Add a table section to the report.

        Args:
            report_content: Existing report content
            title: Section title
            table_data: Table data (rows, record dictionaries or DataFrame)
            headers: For record dictionaries, the record keys to show, in
                order; each must be a key of the records. For row lists and
                DataFrames, the column labels to display.
            level: Section level
            table_style: Table styling
            sort_by: Column index or header name to sort by.
                None preserves existing order.
            sort_order: ``'asc'`` or ``'desc'``.

        Returns:
            Updated report content
        """
        from siege_utilities.reporting.table_utils import sort_table_data

        # Record dictionaries are used by the reporting notebook and need
        # column-aligned values, rather than iteration over dictionary keys.
        if isinstance(table_data, list) and table_data and isinstance(table_data[0], dict):
            if not all(isinstance(row, dict) for row in table_data):
                raise ValueError("Table section records must all be dictionaries")
            if headers is not None:
                # headers select record keys; an unknown one would become a
                # column of missing values.
                record_keys = set().union(*table_data)
                missing = [header for header in headers if header not in record_keys]
                if missing:
                    raise ValueError(
                        f"Table headers {missing} are not keys of the table records"
                    )
            table_data = pd.DataFrame(table_data, columns=headers)

        # Convert DataFrame to list format if needed
        if hasattr(table_data, 'to_dict'):
            if headers is None:
                headers = table_data.columns.tolist()
            table_data = [headers] + table_data.values.tolist()
        elif headers and table_data:
            table_data = [headers] + table_data

        if sort_by is not None:
            table_data = sort_table_data(
                table_data, sort_by=sort_by, sort_order=sort_order
            )

        content = {
            'data': table_data,
            'headers': headers,
            'style': table_style
        }

        return self.add_section(report_content, 'table', title, content, level)

    def add_text_section(self, report_content: Dict[str, Any], title: str,
                         text_content: str, level: int = 1,
                         text_style: str = "body",
                         page_break_before: bool = False,
                         page_break_after: bool = False) -> Dict[str, Any]:
        """
        Add a text section to the report.

        Args:
            report_content: Existing report content
            title: Section title
            text_content: Text content
            level: Section level
            text_style: Text styling
            page_break_before: Start the section on a new page
            page_break_after: Start the next section on a new page

        Returns:
            Updated report content
        """
        return self.add_section(report_content, 'text', title, text_content, level,
                                page_break_before=page_break_before,
                                page_break_after=page_break_after)

    def add_chart_section(self, report_content: Dict[str, Any], title: str,
                          charts: List[ImageType], description: str = "",
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
        content = {
            'charts': charts,
            'description': description,
            'layout': layout
        }

        return self.add_section(report_content, 'charts', title, content, level)

    def add_map_section(self, report_content: Dict[str, Any], title: str,
                        maps: List[ImageType], map_type: str = "choropleth",
                        description: str = "", level: int = 1,
                        page_break_before: bool = False,
                        page_break_after: bool = False) -> Dict[str, Any]:
        """
        Add a map section to the report.

        Args:
            report_content: Existing report content
            title: Section title
            maps: List of map images
            map_type: Type of maps
            description: Section description
            level: Section level
            page_break_before: Start the section on a new page
            page_break_after: Start the next section on a new page

        Returns:
            Updated report content
        """
        content = {
            'maps': maps,
            'map_type': map_type,
            'description': description
        }

        return self.add_section(report_content, 'maps', title, content, level,
                                page_break_before=page_break_before,
                                page_break_after=page_break_after)

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
        return self.add_section(report_content, 'appendix', title, content, level)

    def _get_template(self, output_path: str, template_config: Optional[str] = None) -> 'BaseReportTemplate':
        """
        Create a report template for PDF generation.

        The template gets this generator's branding (headers, footers, page
        numbers, logos, margins and text colours) unless *template_config*
        names a branding YAML file, which then takes its place. Remote logos
        are downloaded only if this generator has ``fetch_remote_assets``.

        Args:
            output_path: Output PDF file path
            template_config: Optional path to template configuration file

        Returns:
            BaseReportTemplate instance
        """
        from .templates.base_template import BaseReportTemplate

        if template_config:
            return BaseReportTemplate(
                output_filename=output_path,
                branding_config_path=Path(template_config),
                fetch_remote_assets=self.fetch_remote_assets,
            )
        return BaseReportTemplate(
            output_filename=output_path,
            branding_config=self.branding_config,
            fetch_remote_assets=self.fetch_remote_assets,
        )

    def _table_palette(self) -> _TablePalette:
        """Return the table colours for this generator's branding.

        Without ``colors.primary`` the table keeps the 4.x look (grey header
        with whitesmoke text, beige body, black grid); ``colors.text_color``
        still colours the body text. With a primary colour the header takes
        it, the header text is whichever of whitesmoke and the brand text
        colour is readable on it (WCAG AA), the body is white and the grid
        is the primary colour when it shows on white (3:1), else the text
        colour.

        Raises:
            BrandingColorError: If a colour in the branding is not a colour.
        """
        brand_colours = (self.branding_config or {}).get('colors') or {}
        text_value = brand_colours.get('text_color')
        body_text = colors.black if text_value is None else brand_color(text_value, 'text_color')
        primary = brand_colours.get('primary')
        if primary is None:
            return _TablePalette(colors.grey, colors.whitesmoke, colors.beige, body_text, colors.black)
        header = brand_color(primary, 'primary')
        header_text = readable_text_color(
            header, preferred=[colors.whitesmoke, body_text], fallback=[colors.white, colors.black],
        )
        grid = header if contrast_ratio(header, colors.white) >= AA_GRAPHIC_CONTRAST else body_text
        return _TablePalette(header, header_text, colors.white, body_text, grid)

    def _build_table(self, table_data: List[List[Any]], repeat_rows: int,
                     title: str, template) -> 'Table':
        """Build a table that fits the page frame (#1993).

        A table whose cells fit on one line within the page margins is built
        exactly as before, and so is a table made only of flowables (as the
        facade reports build them), which ReportLab already sizes to the
        frame. Otherwise the columns get widths from their content: columns
        needing less than an equal share keep their natural width and the
        others share the rest; plain values in the narrowed columns are
        wrapped. Cells that are already flowables are never changed. When a
        row is taller than a page it may split across pages instead of
        failing.

        Raises:
            BrandingColorError: If a colour in the branding is not a colour.
        """
        palette = self._table_palette()
        style = TableStyle(palette.commands())
        avail_width = template.doc.width - _FRAME_PADDING
        avail_height = template.doc.height - _FRAME_PADDING

        flowable_cells = [[_is_flowable_cell(cell) for cell in row] for row in table_data]
        all_flowable = all(all(row) for row in flowable_cells)
        columns: List[List[_CellWidths]] = []
        if not all_flowable:
            fonts = [_HEADER_FONT] + [_BODY_FONT] * (len(table_data) - 1)
            columns = [[] for _ in range(max(len(row) for row in table_data))]
            for row, font in zip(table_data, fonts):
                for index, cell in enumerate(row):
                    columns[index].append(_cell_widths(cell, font, avail_width))
        natural = [max(cell.natural for cell in column) for column in columns]

        # Overflowing into the frame's own padding stays inside the margins,
        # so only a table wider than the margins is refitted.
        table = None
        if sum(natural) > template.doc.width + 0.01:
            table, cells = self._fitted_table(
                table_data, repeat_rows, title, columns, natural, flowable_cells,
                palette, style, avail_width, avail_height,
            )
            if table is not None:
                table_data = cells
        if table is None:
            table = Table(table_data, repeatRows=repeat_rows)
            table.setStyle(style)
        return self._allow_tall_rows(table, table_data, repeat_rows, palette, style,
                                     avail_width, avail_height, title)

    def _fitted_table(self, table_data: List[List[Any]], repeat_rows: int, title: str,
                      columns: List[List[_CellWidths]], natural: List[float],
                      flowable_cells: List[List[bool]], palette: _TablePalette,
                      style: 'TableStyle', avail_width: float, avail_height: float):
        """Return the table with content-sized columns and its cells, or ``(None, None)``.

        ``None`` means the wrapped header row would leave no room on a page
        for the body (a repeated header row cannot split), so the caller
        builds the table unfitted, as before, after a warning.
        """
        widths = _fit_column_widths(columns, avail_width)
        if sum(widths) > avail_width + 0.01:
            log.warning(
                "Table section %r has %d columns and cannot fit the %.0f pt frame "
                "without splitting numbers or narrowing text columns below %d pt; "
                "it is %.0f pt wide",
                title, len(columns), avail_width, _MIN_COLUMN_WIDTH, sum(widths),
            )
        narrowed = [width < need - 0.01 for width, need in zip(widths, natural)]
        cells = [
            [
                _wrapped_cell(cell, palette.paragraph_style(row_index))
                if narrowed[index] and not flowable_cells[row_index][index] else cell
                for index, cell in enumerate(row)
            ]
            for row_index, row in enumerate(table_data)
        ]
        table = Table(cells, colWidths=widths, repeatRows=repeat_rows)
        table.setStyle(style)
        if repeat_rows:
            table.wrap(avail_width, avail_height)
            header_height = sum(table._rowHeights[:repeat_rows])
            if header_height > avail_height - _MIN_BODY_HEIGHT:
                log.warning(
                    "Table section %r: its wrapped header row would be %.0f pt tall, "
                    "leaving no room for rows in the %.0f pt page frame; the table is "
                    "drawn without fitting its columns",
                    title, header_height, avail_height,
                )
                return None, None
        return table, cells

    def _allow_tall_rows(self, table: 'Table', table_data: List[List[Any]], repeat_rows: int,
                         palette: _TablePalette, style: 'TableStyle',
                         avail_width: float, avail_height: float, title: str = '') -> 'Table':
        """Split a row taller than a page into rows that each fit a page.

        Only flowables and multi-line text can make a row that tall, so other
        tables are returned untouched and paginate as before. Each cell of a
        too-tall row becomes a flowable (plain values are drawn as text, with
        their lines kept) and is cut at line boundaries into consecutive rows
        that fit under the repeated header on one page. The table then splits
        only between whole rows, so no cell content is dropped or drawn off
        the page; ReportLab's in-row splitting is never used.

        Raises:
            TableRowTooTallError: If such a row holds a cell that cannot be
                split (an image or several flowables taller than a page), or
                a resulting row would still not fit; no PDF is written then.
        """
        def multi_line(cell: Any) -> bool:
            # Any plain value whose shown text has several lines (str, bytes,
            # or an object such as an array whose str() spans lines).
            return not _is_flowable_cell(cell) and '\n' in _cell_text(cell)

        if not any(_is_flowable_cell(cell) or multi_line(cell) for row in table_data for cell in row):
            return table
        table.wrap(avail_width, avail_height)
        heights = list(table._rowHeights)
        header_height = sum(heights[:repeat_rows])
        if repeat_rows and header_height > avail_height - _MIN_BODY_HEIGHT:
            raise TableRowTooTallError(
                f"Table section {title!r}: its header row is {header_height:.0f} pt tall and is "
                f"repeated on every page, leaving no room for rows in the {avail_height:.0f} pt "
                f"page frame; shorten the column headers"
            )
        limit = avail_height - header_height
        tall_rows = {index for index in range(repeat_rows, len(heights)) if heights[index] > limit}
        if not tall_rows:
            return table

        widths = list(table._colWidths)
        rows: List[List[Any]] = []
        extra_commands: List[tuple] = []
        for index, row in enumerate(table_data):
            if index not in tall_rows:
                rows.append(list(row))
                continue
            padding = _BODY_ROW_PADDING + (_HEADER_EXTRA_PADDING if index == 0 else 0)
            piece_height = limit - padding - 1.0
            # Half-page pieces let the first one start below a heading on the
            # current page; every piece still fits a page under the header.
            if piece_height >= 2 * _MIN_BODY_HEIGHT:
                piece_height /= 2
            pieces = [
                _cell_chunks(cell, widths[column] - _CELL_PADDING, piece_height,
                             palette.paragraph_style(index), title, index, column)
                for column, cell in enumerate(row)
            ]
            first = len(rows)
            for part in range(max(len(piece) for piece in pieces)):
                rows.append([piece[part] if part < len(piece) else '' for piece in pieces])
            last = len(rows) - 1
            extra_commands.append(('VALIGN', (0, first), (-1, last), 'TOP'))
            if index == 0:
                extra_commands.extend(palette.header_commands(first, last))

        table = Table(rows, colWidths=widths, repeatRows=repeat_rows)
        table.setStyle(TableStyle(list(style.getCommands()) + extra_commands))
        table.wrap(avail_width, avail_height)
        tallest = max(table._rowHeights[repeat_rows:], default=0.0)
        if tallest > limit + 0.01:
            raise TableRowTooTallError(
                f"Table section {title!r}: a row is still {tallest:.0f} pt tall after splitting, "
                f"more than the {limit:.0f} pt a page leaves under the header"
            )
        return table

    def generate_pdf_report(self, report_content: Dict[str, Any],
                           output_path: str, template_config: str = None) -> None:
        """
        Generate a comprehensive PDF report with full document structure.

        Args:
            report_content: Report content structure
            output_path: Output PDF file path
            template_config: Template configuration file path

        Raises:
            OSError: If the output directory cannot be created or is not writable,
                or if the final rename fails.
        """
        final = Path(output_path)
        parent = final.parent if str(final.parent) else Path(".")
        parent.mkdir(parents=True, exist_ok=True)
        if not os.access(parent, os.W_OK):
            raise OSError(
                f"generate_pdf_report: output directory {parent} is not writable"
            )

        tmp_path = parent / f".{final.name}.{uuid.uuid4().hex[:8]}.part"

        try:
            template = self._get_template(str(tmp_path), template_config)

            story = []

            metadata = report_content.get('metadata', {})
            sections = report_content.get('sections', [])
            title = metadata.get('title') or report_content.get('title')
            if title and not any(section.get('type') == 'title_page' for section in sections):
                title_flowables = template.add_title_page(
                    title=title,
                    subtitle=metadata.get('subtitle', ''),
                    author=metadata.get('author', ''),
                    date=metadata.get('date', ''),
                    client=metadata.get('client', '')
                )
                story.extend(title_flowables)

            for section in sections:
                section_story = self._build_section_content(section, template)
                story.extend(section_story)

                if section.get('page_break_after', False):
                    story.append(PageBreak())

            if not any(hasattr(flowable, '_toc_entry') for flowable in story):
                for index, flowable in enumerate(story):
                    if isinstance(flowable, TableOfContents):
                        log.warning("Table of contents has no titled report sections")
                        story[index] = Paragraph("No sections.", template.styles['Normal'])

            template.build_document(story)

            try:
                os.replace(tmp_path, final)
            except OSError as exc:
                try:
                    if tmp_path.exists():
                        tmp_path.unlink()
                except OSError:
                    pass
                raise OSError(
                    f"generate_pdf_report: built {tmp_path} but could not "
                    f"rename to {final}: {exc}"
                ) from exc

        except BaseException:
            try:
                if tmp_path.exists():
                    tmp_path.unlink()
            except OSError:
                pass
            raise

        log.info(f"PDF report generated successfully: {output_path}")

    def _process_chart_list(self, charts: List[Any], width: float = 6,
                             height: float = 4, image_dpi: int = 200,
                             jpeg_quality: int = 85) -> List:
        """
        Process a list of charts in various formats into ReportLab Image objects.

        Supported formats:
        - File path (str or Path)
        - matplotlib Figure object
        - PIL Image object (downsampled and re-encoded, see ``_encode_pil_image``)
        - BytesIO object containing image data
        - ReportLab Flowable (passed through)

        Args:
            charts: List of chart objects in various formats
            width: Image width in inches
            height: Image height in inches
            image_dpi: Resolution PIL images are downsampled to for the
                ``width`` x ``height`` display box. Smaller images are not
                upsampled.
            jpeg_quality: JPEG quality used for photographic PIL images.

        Returns:
            List of ReportLab Image flowables
        """
        if not REPORTLAB_AVAILABLE:
            raise ImportError(
                "ReportLab is required to process charts. "
                "Install with: pip install reportlab"
            )

        import io

        result = []

        for chart in charts:
            try:
                # Handle ReportLab flowables (pass through)
                if hasattr(chart, 'drawOn'):
                    result.append(chart)
                    continue

                # Handle file paths
                if isinstance(chart, (str, Path)):
                    chart_path = Path(chart)
                    if chart_path.exists():
                        img = RLImage(str(chart_path), width=width*inch, height=height*inch)
                        result.append(img)
                    else:
                        log.warning("Chart image does not exist: %s", chart_path)
                    continue

                # Handle matplotlib Figure
                if hasattr(chart, 'savefig'):
                    # Always close the figure and the buffer, even on
                    # savefig() exceptions — long-running pipelines that
                    # raise mid-render were leaking the entire figure
                    # graph until interpreter exit.
                    buf = io.BytesIO()
                    try:
                        chart.savefig(buf, format='png', dpi=150, bbox_inches='tight')
                        buf.seek(0)
                        img = RLImage(buf, width=width*inch, height=height*inch)
                        result.append(img)
                    finally:
                        try:
                            import matplotlib.pyplot as plt
                            plt.close(chart)
                        except (ValueError, TypeError, AttributeError) as exc:
                            log.debug("Could not close matplotlib figure: %s", exc)
                        # The BytesIO is now referenced by the RLImage —
                        # ReportLab keeps a handle for the build pass and
                        # closes it itself. Nothing to do here.
                    continue

                # Handle PIL Image
                if hasattr(chart, 'save') and hasattr(chart, 'mode'):
                    if self._is_pil_image(chart):
                        # Store only the pixels the display box needs, as JPEG
                        # only for photographs (#2000).
                        buf = self._encode_pil_image(chart, width, height,
                                                     image_dpi, jpeg_quality)
                    else:
                        # Image-like object without PIL's API: embed as is.
                        buf = io.BytesIO()
                        chart.save(buf, format='PNG')
                        buf.seek(0)
                    img = RLImage(buf, width=width*inch, height=height*inch)
                    result.append(img)
                    continue

                # Handle BytesIO
                if isinstance(chart, io.BytesIO):
                    chart.seek(0)
                    img = RLImage(chart, width=width*inch, height=height*inch)
                    result.append(img)
                    continue

                # Handle dict with image_path
                if isinstance(chart, dict):
                    image_path = chart.get('image_path') or chart.get('path')
                    if image_path and Path(image_path).exists():
                        chart_width = chart.get('width', width)
                        chart_height = chart.get('height', height)
                        img = RLImage(str(image_path), width=chart_width*inch,
                                     height=chart_height*inch)
                        result.append(img)
                    else:
                        # Log the mapping's keys only, never its values.
                        log.warning("Chart mapping has no existing image path (keys: %s)",
                                    sorted(str(key) for key in chart))
                    continue

                log.warning(f"Unknown chart type: {type(chart)}")

            except (ValueError, TypeError, KeyError, IndexError, AttributeError, OSError) as e:
                log.error(f"Error processing chart: {e}")

        return result

    # Colour images with at most this many distinct colours (counted on the
    # original pixels) are flat-colour graphics: charts, logos, diagrams,
    # screenshots. They are always kept lossless.
    _FLAT_COLOUR_MAX_COLOURS = 256
    # Any other opaque image is stored as JPEG only when the JPEG is at most
    # this fraction of the lossless PNG of the same pixels.
    _JPEG_MAX_SIZE_RATIO = 1 / 3
    _ALPHA_MODES = ('RGBA', 'LA', 'PA', 'RGBa', 'La')
    _GREYSCALE_MODES = ('L', 'LA', 'La', 'I', 'F')

    @staticmethod
    def _is_pil_image(obj: Any) -> bool:
        """True for a real ``PIL.Image.Image``; False if Pillow is absent."""
        try:
            from PIL import Image as PILImage
        except ImportError:
            return False
        return isinstance(obj, PILImage.Image)

    @classmethod
    def _to_embeddable_mode(cls, image: Any, has_alpha: bool) -> Any:
        """Convert ``image`` to L, LA, RGB or RGBA without losing what it shows.

        Bilevel and palette images are converted *before* resampling because
        Pillow resizes modes ``1`` and ``P`` with nearest-neighbour whatever
        filter is requested, which drops thin lines. 16-bit greyscale is
        scaled to 8 bits; 32-bit integer and float greyscale (``I``, ``F``)
        are clipped to 0-255.
        """
        mode = image.mode
        if mode in ('L', 'LA', 'RGB', 'RGBA'):
            return image
        if mode == '1':
            return image.convert('L')
        if mode in ('P', 'PA'):
            return image.convert('RGBA' if has_alpha else 'RGB')
        if mode.startswith('I;16'):
            return image.convert('I').point(lambda v: v * (1 / 256)).convert('L')
        if mode in ('I', 'F'):
            return image.convert('L')
        if mode == 'La':
            return image.convert('LA')
        return image.convert('RGBA' if has_alpha else 'RGB')

    @classmethod
    def _encode_pil_image(cls, image: Any, width: float, height: float,
                          dpi: int, jpeg_quality: int) -> Any:
        """Encode a PIL image for embedding in a ``width`` x ``height`` inch box.

        The image is downsampled (never upsampled) with a uniform scale so it
        still covers the box at ``dpi``. The format is chosen as follows:

        - images with transparency, and colour images whose *original* pixels
          have at most ``_FLAT_COLOUR_MAX_COLOURS`` colours (including every
          bilevel and palette image), are stored as lossless PNG;
        - any other image (including greyscale) is stored as JPEG at
          ``jpeg_quality`` only if that JPEG is at most
          ``_JPEG_MAX_SIZE_RATIO`` of the size of the lossless PNG of the same
          pixels, and as PNG otherwise.

        The caller's image is not modified.

        Raises:
            ValueError: If the image has zero width or height.

        Returns:
            A BytesIO positioned at the start of the encoded image.
        """
        import io
        from PIL import Image as PILImage

        src_w, src_h = image.size
        if not src_w or not src_h:
            raise ValueError(f"cannot embed an empty image ({src_w}x{src_h})")

        # Classify on the original pixels: resampling creates new colours.
        mode = image.mode
        has_alpha = mode in cls._ALPHA_MODES or 'transparency' in image.info
        if mode in ('1', 'P', 'PA'):
            flat_colour = True
        elif mode.startswith('I;16') or mode in cls._GREYSCALE_MODES:
            flat_colour = False
        else:
            flat_colour = (image.getcolors(maxcolors=cls._FLAT_COLOUR_MAX_COLOURS)
                           is not None)

        image = cls._to_embeddable_mode(image, has_alpha)
        scale = min(1.0, max(width * dpi / src_w, height * dpi / src_h))
        if scale < 1.0:
            target = (max(1, round(src_w * scale)), max(1, round(src_h * scale)))
            image = image.resize(target, PILImage.Resampling.LANCZOS)

        png = io.BytesIO()
        image.save(png, format='PNG')
        png.seek(0)
        if has_alpha or flat_colour:
            return png

        jpeg = io.BytesIO()
        image.save(jpeg, format='JPEG', quality=jpeg_quality, optimize=True)
        if len(jpeg.getvalue()) <= len(png.getvalue()) * cls._JPEG_MAX_SIZE_RATIO:
            jpeg.seek(0)
            return jpeg
        return png

    def _build_section_content(self, section: Dict[str, Any],
                              template) -> List:
        """
        Build ReportLab content for a section.

        Args:
            section: Section dictionary
            template: Report template (BaseReportTemplate with styles)

        Returns:
            List of ReportLab flowables
        """
        if not REPORTLAB_AVAILABLE:
            raise ImportError(
                "ReportLab is required to build report sections. "
                "Install with: pip install reportlab"
            )

        story = []
        section_type = section.get('type', 'text')
        styles = template.styles
        content = section.get('content')
        text_types = {'text', 'executive_summary', 'methodology', 'data_summary', 'appendix'}
        supported_types = text_types | {
            'insights', 'recommendations', 'title_page', 'table_of_contents',
            'appendix_header', 'table', 'chart', 'charts', 'map', 'maps',
        }
        if section_type not in supported_types:
            raise ValueError(f"Unknown report section type: {section_type!r}")

        def invalid_content(expected):
            raise ValueError(f"Invalid content for {section_type!r} section: expected {expected}")

        # Add page break if requested
        if section.get('page_break_before', False) or section_type == 'appendix_header':
            story.append(PageBreak())

        if section_type == 'title_page':
            fields = ('title', 'subtitle', 'author', 'client', 'date')
            if content is not None or any(
                section.get(field) is not None and not isinstance(section[field], str)
                for field in fields
            ):
                invalid_content('title, subtitle, author, client and date strings on the section')
            if not (section.get('title') or '').strip():
                invalid_content('a nonempty title')
            story.extend(template.add_title_page(**{field: section.get(field) or '' for field in fields}))
            return story

        # Add section title
        title = section.get('title', '')
        level = section.get('level', 1)
        if title:
            # As in 4.0.0, the level only names a heading style: "2" or 2
            # selects Heading2, and any level without such a style (None,
            # "abc", 2.5) falls back to Heading1. The table-of-contents level
            # follows the style actually used, so no level value raises.
            heading_name = f'Heading{level}'
            if heading_name not in styles:
                heading_name = 'Heading1'
            heading_style = styles[heading_name]
            heading = Paragraph(_escape_paragraph(title), heading_style)
            if section_type != 'table_of_contents':
                number = re.fullmatch(r'Heading(\d+)', heading_name)
                toc_level = max(0, int(number.group(1)) - 1) if number else 0
                heading._toc_entry = (toc_level, _escape_paragraph(title))
            story.append(heading)
            story.append(Spacer(1, 12))

        # Handle different section types
        if section_type in text_types:
            text = content.get('text') if isinstance(content, dict) else content
            if not isinstance(text, str):
                invalid_content('a string or a mapping with a text string')
            if not text.strip():
                log.warning("Empty content for %s section %r", section_type, title)
            if text:
                # Split on newlines and create separate paragraphs to preserve formatting
                for line in text.split('\n'):
                    stripped = line.strip()
                    if not stripped:
                        story.append(Spacer(1, 6))
                    elif stripped.startswith('- ') or stripped.startswith('* '):
                        # Bullet point — escape user text before concatenating
                        # the literal ``&bull;`` entity. ReportLab's mini-HTML
                        # parser treats ``<`` and ``&`` as markup; raw user
                        # text containing ``<3`` or ``Q&A`` would otherwise
                        # raise a parse error mid-render.
                        bullet_text = _escape_paragraph(stripped[2:])
                        story.append(Paragraph(f'&bull; {bullet_text}', styles['Normal']))
                    else:
                        story.append(Paragraph(_escape_paragraph(stripped), styles['Normal']))
            story.append(Spacer(1, 12))

        elif section_type in {'insights', 'recommendations'}:
            if not isinstance(content, list) or not all(isinstance(item, str) and item.strip() for item in content):
                invalid_content('a list of nonempty strings')
            if not content:
                log.warning("Empty content for %s section %r", section_type, title)
            for item in content:
                story.append(Paragraph(_escape_paragraph(item), styles['Bullet'], bulletText='\u2022'))
            story.append(Spacer(1, 12))

        elif section_type == 'table_of_contents':
            if content is not None:
                invalid_content('automatically generated entries, without explicit content')
            story.extend([TableOfContents(), PageBreak()])

        elif section_type == 'appendix_header':
            if content is not None:
                invalid_content('an appendix divider without content')
            if not title:
                invalid_content('an appendix divider title')

        elif section_type == 'table':
            if not isinstance(content, dict):
                invalid_content('a mapping with table data')
            table_data = content.get('data')
            headers = content.get('headers')
            # 4.0.0 rendered tuple headers; accept them as a list.
            if isinstance(headers, tuple):
                headers = list(headers)
            if headers is not None and not isinstance(headers, list):
                invalid_content('a list or tuple of column headers')

            if isinstance(table_data, pd.DataFrame):
                headers = headers or table_data.columns.tolist()
                table_data = [headers] + table_data.values.tolist()
            else:
                if not isinstance(table_data, list) or not all(isinstance(row, (list, tuple)) for row in table_data):
                    invalid_content('a list of rows or a DataFrame')
                if headers and table_data and list(table_data[0]) != headers:
                    # add_table_section already prepends headers.
                    table_data = [headers] + table_data

            if table_data:
                story.append(self._build_table(table_data, 1 if headers else 0, title, template))
                story.append(Spacer(1, 12))
            else:
                log.warning("Empty content for table section %r", title)

        elif section_type in {'chart', 'charts', 'map', 'maps'}:
            key = 'maps' if section_type in {'map', 'maps'} else 'charts'
            description = ''
            if key == 'charts' and isinstance(content, (list, tuple)):
                charts = list(content)
            elif isinstance(content, dict):
                charts = content.get(key, [])
                # As in 4.0.0, None under the key means no images; the
                # heading and description still render.
                if charts is None:
                    charts = []
                # As in 4.0.0, a None description means no description.
                description = content.get('description')
                if description is None:
                    description = ''
                # 4.0.0 iterated any sequence of images; a str, bytes or
                # mapping is not a list of images, so it is rejected rather
                # than iterated.
                if not isinstance(charts, (list, tuple)):
                    invalid_content(f'a list, tuple or None under {key!r}')
                charts = list(charts)
                if key == 'charts' and content.get('image_path'):
                    charts = [content['image_path']] + charts
            else:
                invalid_content('a chart list or an image mapping' if key == 'charts' else 'a maps mapping')
            if not isinstance(description, str):
                invalid_content('a string description')

            if description:
                story.append(Paragraph(_escape_paragraph(description), styles['Normal']))
                story.append(Spacer(1, 8))

            chart_images = self._process_chart_list(charts)
            if not chart_images:
                log.warning("No renderable images for %s section %r", section_type, title)
            for chart_img in chart_images:
                story.append(chart_img)
                story.append(Spacer(1, 12))

        return story

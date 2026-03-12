"""
IDML (InDesign Markup Language) report export.

Provides ``IDMLExporter`` for programmatic creation of IDML files that
Adobe InDesign can open, plus a convenience ``export_report_idml()``
function that accepts the same *ga_data* dict used by the PDF/PPTX
generators.

IDML is a ZIP archive containing a set of XML files (designmap.xml,
Spreads/, Stories/, Resources/, etc.).  When the ``simpleidml`` library
is installed we delegate to it; otherwise we build the ZIP structure
manually so that **no** external dependency is required at runtime.
"""

from __future__ import annotations

import io
import logging
import os
import re
import uuid
import warnings
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from xml.etree import ElementTree as ET

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Lazy import of simpleidml
# ---------------------------------------------------------------------------
try:
    import simpleidml  # type: ignore[import-untyped]
    SIMPLEIDML_AVAILABLE = True
except ImportError:
    simpleidml = None  # type: ignore[assignment]
    SIMPLEIDML_AVAILABLE = False

# ---------------------------------------------------------------------------
# IDML XML namespace constants
# ---------------------------------------------------------------------------
_IDML_NS = "http://ns.adobe.com/AdobeInDesign/idml/1.0/packaging"
_IDPKG = "http://ns.adobe.com/AdobeInDesign/idpkg/1.0"

# Default page dimensions (US Letter in points: 612 x 792)
_PAGE_WIDTH = 612.0
_PAGE_HEIGHT = 792.0


def _uid() -> str:
    """Return a short unique hex id suitable for IDML element identifiers."""
    return uuid.uuid4().hex[:8]


# ============================================================================
# IDMLExporter
# ============================================================================

class IDMLExporter:
    """Build an IDML file programmatically.

    Parameters
    ----------
    template_path : str or Path, optional
        Path to an existing ``.idml`` template.  If provided **and**
        ``simpleidml`` is installed the template is loaded for
        modification.  Otherwise the exporter builds the IDML structure
        from scratch.
    page_width : float
        Page width in points (default 612 = US Letter).
    page_height : float
        Page height in points (default 792 = US Letter).
    """

    def __init__(
        self,
        template_path: Optional[str] = None,
        page_width: float = _PAGE_WIDTH,
        page_height: float = _PAGE_HEIGHT,
    ) -> None:
        self.template_path = Path(template_path) if template_path else None
        self.page_width = page_width
        self.page_height = page_height

        # Internal stores for content added via the public API
        self._text_frames: List[Dict[str, Any]] = []
        self._image_frames: List[Dict[str, Any]] = []
        self._tables: List[Dict[str, Any]] = []
        self._replacements: Dict[str, str] = {}

        # If a template + simpleidml are available, load it
        self._idml_package = None
        if self.template_path and SIMPLEIDML_AVAILABLE:
            try:
                self._idml_package = simpleidml.IDMLPackage(str(self.template_path))
                log.info("Loaded IDML template via simpleidml: %s", self.template_path)
            except Exception as exc:
                log.warning(
                    "Could not load template with simpleidml (%s); "
                    "falling back to manual ZIP builder.",
                    exc,
                )
                self._idml_package = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def add_text_frame(
        self,
        text: str,
        style_name: str = "NormalParagraphStyle",
        x: float = 72.0,
        y: float = 72.0,
        width: float = 468.0,
        height: float = 36.0,
    ) -> None:
        """Add a text frame to the document.

        Parameters
        ----------
        text : str
            Content of the text frame.
        style_name : str
            InDesign paragraph style name.
        x, y : float
            Top-left position in points.
        width, height : float
            Dimensions in points.
        """
        self._text_frames.append({
            "text": text,
            "style": style_name,
            "x": x,
            "y": y,
            "width": width,
            "height": height,
            "uid": _uid(),
        })

    def add_image_frame(
        self,
        image_path: str,
        x: float = 72.0,
        y: float = 72.0,
        width: float = 200.0,
        height: float = 200.0,
    ) -> None:
        """Add an image placeholder frame.

        Parameters
        ----------
        image_path : str
            Path to the image file (stored as a link reference).
        x, y : float
            Top-left position in points.
        width, height : float
            Dimensions in points.
        """
        self._image_frames.append({
            "image_path": str(image_path),
            "x": x,
            "y": y,
            "width": width,
            "height": height,
            "uid": _uid(),
        })

    def add_table(
        self,
        headers: List[str],
        rows: List[List[str]],
        x: float = 72.0,
        y: float = 72.0,
        width: float = 468.0,
        height: float = 200.0,
    ) -> None:
        """Add a table as a text frame with tab-separated content.

        Parameters
        ----------
        headers : list[str]
            Column headers.
        rows : list[list[str]]
            Row data — each inner list is one row.
        x, y : float
            Top-left position in points.
        width, height : float
            Dimensions in points.
        """
        self._tables.append({
            "headers": headers,
            "rows": rows,
            "x": x,
            "y": y,
            "width": width,
            "height": height,
            "uid": _uid(),
        })

    def replace_placeholder(self, placeholder: str, content: str) -> None:
        """Register a template placeholder substitution.

        When ``save()`` is called every occurrence of *placeholder* in
        story XML content is replaced with *content*.
        """
        self._replacements[placeholder] = content

    def save(self, output_path: str) -> str:
        """Write the IDML file to *output_path*.

        Returns the resolved output path.
        """
        output_path = str(output_path)
        if not output_path.lower().endswith(".idml"):
            output_path += ".idml"

        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)

        if self._idml_package is not None:
            return self._save_with_simpleidml(output_path)
        return self._save_manual(output_path)

    # ------------------------------------------------------------------
    # simpleidml path
    # ------------------------------------------------------------------

    def _save_with_simpleidml(self, output_path: str) -> str:
        """Use simpleidml to apply replacements and export."""
        pkg = self._idml_package
        # Apply placeholder substitutions
        for placeholder, content in self._replacements.items():
            try:
                pkg.set_tag(placeholder, content)
            except Exception:
                log.debug(
                    "simpleidml.set_tag failed for %r; doing raw XML substitution.",
                    placeholder,
                )
                # Fall through to raw XML sub in _apply_replacements_raw
                self._apply_replacements_raw_simpleidml(pkg, placeholder, content)
        pkg.export_to_file(output_path)
        log.info("Saved IDML (via simpleidml) → %s", output_path)
        return output_path

    @staticmethod
    def _apply_replacements_raw_simpleidml(pkg, placeholder: str, content: str) -> None:
        """Brute-force find/replace inside simpleidml story XML."""
        for story in pkg.stories:
            xml_bytes = pkg.read(story)
            if isinstance(xml_bytes, bytes):
                xml_str = xml_bytes.decode("utf-8", errors="replace")
            else:
                xml_str = str(xml_bytes)
            if placeholder in xml_str:
                xml_str = xml_str.replace(placeholder, content)
                pkg.writestr(story, xml_str.encode("utf-8"))

    # ------------------------------------------------------------------
    # Manual ZIP builder (fallback when simpleidml is absent)
    # ------------------------------------------------------------------

    def _save_manual(self, output_path: str) -> str:
        """Build a valid IDML ZIP archive from scratch."""
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            # 1. mimetype (stored, not deflated — like EPUB/ODF convention)
            zf.writestr("mimetype", "application/vnd.adobe.indesign-idml-package")

            # 2. META-INF/container.xml
            zf.writestr("META-INF/container.xml", self._build_container_xml())

            # 3. designmap.xml — master manifest
            story_ids, spread_id = self._collect_ids()
            zf.writestr("designmap.xml", self._build_designmap(story_ids, spread_id))

            # 4. Resources/Preferences.xml
            zf.writestr("Resources/Preferences.xml", self._build_preferences())

            # 5. Resources/Styles.xml
            zf.writestr("Resources/Styles.xml", self._build_styles())

            # 6. Resources/Graphic.xml
            zf.writestr("Resources/Graphic.xml", self._build_graphic())

            # 7. Spread
            zf.writestr(
                f"Spreads/Spread_{spread_id}.xml",
                self._build_spread(spread_id, story_ids),
            )

            # 8. Stories
            for sid, story_xml in self._build_stories(story_ids):
                zf.writestr(f"Stories/Story_{sid}.xml", story_xml)

            # 9. Resources/Fonts.xml (minimal)
            zf.writestr("Resources/Fonts.xml", self._build_fonts())

        Path(output_path).write_bytes(buf.getvalue())
        log.info("Saved IDML (manual ZIP) → %s", output_path)
        return output_path

    # -- id helpers --

    def _collect_ids(self) -> Tuple[List[str], str]:
        """Return (story_ids, spread_id) for all content items."""
        story_ids: List[str] = []
        for frame in self._text_frames:
            story_ids.append(f"story_{frame['uid']}")
        for table in self._tables:
            story_ids.append(f"story_{table['uid']}")
        for img in self._image_frames:
            story_ids.append(f"story_{img['uid']}")
        if not story_ids:
            # At least one empty story so the file is valid
            story_ids.append(f"story_{_uid()}")
        spread_id = _uid()
        return story_ids, spread_id

    # -- XML builders --

    def _build_container_xml(self) -> str:
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
            '<container xmlns="urn:oasis:names:tc:opendocument:xmlns:container">\n'
            '  <rootfiles>\n'
            '    <rootfile full-path="designmap.xml"/>\n'
            '  </rootfiles>\n'
            '</container>\n'
        )

    def _build_designmap(self, story_ids: List[str], spread_id: str) -> str:
        lines = [
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
            f'<Document xmlns:idPkg="{_IDPKG}" DOMVersion="19.0">',
            f'  <idPkg:Spread src="Spreads/Spread_{spread_id}.xml"/>',
        ]
        for sid in story_ids:
            lines.append(f'  <idPkg:Story src="Stories/Story_{sid}.xml"/>')
        lines.append('  <idPkg:Preferences src="Resources/Preferences.xml"/>')
        lines.append('  <idPkg:Styles src="Resources/Styles.xml"/>')
        lines.append('  <idPkg:Graphic src="Resources/Graphic.xml"/>')
        lines.append('  <idPkg:Fonts src="Resources/Fonts.xml"/>')
        lines.append('</Document>')
        return "\n".join(lines) + "\n"

    def _build_preferences(self) -> str:
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
            '<idPkg:Preferences xmlns:idPkg="' + _IDPKG + '" DOMVersion="19.0">\n'
            f'  <DocumentPreference PageWidth="{self.page_width}" '
            f'PageHeight="{self.page_height}" '
            f'PagesPerDocument="1" FacingPages="false"/>\n'
            '</idPkg:Preferences>\n'
        )

    def _build_styles(self) -> str:
        # Collect all unique style names used
        style_names = set()
        for frame in self._text_frames:
            style_names.add(frame["style"])
        style_names.add("NormalParagraphStyle")  # always include default

        style_elements = []
        for sn in sorted(style_names):
            style_elements.append(
                f'  <ParagraphStyle Self="ParagraphStyle/{sn}" Name="{sn}"'
                f' FontStyle="Regular" PointSize="12"/>'
            )
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
            f'<idPkg:Styles xmlns:idPkg="{_IDPKG}" DOMVersion="19.0">\n'
            '  <RootParagraphStyleGroup Self="rootParagraphStyleGroup">\n'
            + "\n".join(style_elements) + "\n"
            '  </RootParagraphStyleGroup>\n'
            '  <RootCharacterStyleGroup Self="rootCharacterStyleGroup"/>\n'
            '</idPkg:Styles>\n'
        )

    def _build_graphic(self) -> str:
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
            f'<idPkg:Graphic xmlns:idPkg="{_IDPKG}" DOMVersion="19.0">\n'
            '  <Color Self="Color/Black" ColorValue="0 0 0" Model="Process" Space="RGB"/>\n'
            '  <Color Self="Color/White" ColorValue="255 255 255" Model="Process" Space="RGB"/>\n'
            '</idPkg:Graphic>\n'
        )

    def _build_fonts(self) -> str:
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
            f'<idPkg:Fonts xmlns:idPkg="{_IDPKG}" DOMVersion="19.0"/>\n'
        )

    def _build_spread(self, spread_id: str, story_ids: List[str]) -> str:
        """Build Spread XML with text/image frames."""
        lines = [
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
            f'<idPkg:Spread xmlns:idPkg="{_IDPKG}" DOMVersion="19.0">',
            f'  <Spread Self="Spread_{spread_id}" PageCount="1">',
            f'    <Page Self="page_{_uid()}" '
            f'GeometricBounds="0 0 {self.page_height} {self.page_width}"/>',
        ]

        idx = 0
        for frame in self._text_frames:
            sid = story_ids[idx]; idx += 1
            bounds = self._geo_bounds(frame)
            lines.append(
                f'    <TextFrame Self="tf_{frame["uid"]}" '
                f'ParentStory="{sid}" '
                f'GeometricBounds="{bounds}"/>'
            )
        for table in self._tables:
            sid = story_ids[idx]; idx += 1
            bounds = self._geo_bounds(table)
            lines.append(
                f'    <TextFrame Self="tf_{table["uid"]}" '
                f'ParentStory="{sid}" '
                f'GeometricBounds="{bounds}"/>'
            )
        for img in self._image_frames:
            sid = story_ids[idx]; idx += 1
            bounds = self._geo_bounds(img)
            lines.append(
                f'    <Rectangle Self="rect_{img["uid"]}" '
                f'GeometricBounds="{bounds}">'
            )
            lines.append(
                f'      <Image Self="img_{img["uid"]}" '
                f'ImageTypeName="EPS">'
            )
            lines.append(
                f'        <Link Self="link_{img["uid"]}" '
                f'LinkResourceURI="file://{img["image_path"]}"/>'
            )
            lines.append('      </Image>')
            lines.append('    </Rectangle>')

        lines.append('  </Spread>')
        lines.append('</idPkg:Spread>')
        return "\n".join(lines) + "\n"

    @staticmethod
    def _geo_bounds(frame: Dict[str, Any]) -> str:
        """Return IDML GeometricBounds string 'top left bottom right'."""
        x = frame["x"]
        y = frame["y"]
        return f"{y} {x} {y + frame['height']} {x + frame['width']}"

    def _build_stories(self, story_ids: List[str]):
        """Yield (story_id, xml_string) for each story."""
        idx = 0
        for frame in self._text_frames:
            sid = story_ids[idx]; idx += 1
            text = self._apply_replacements(frame["text"])
            yield sid, self._story_xml(sid, text, frame["style"])

        for table in self._tables:
            sid = story_ids[idx]; idx += 1
            text = self._table_to_text(table)
            text = self._apply_replacements(text)
            yield sid, self._story_xml(sid, text, "NormalParagraphStyle")

        for img in self._image_frames:
            sid = story_ids[idx]; idx += 1
            yield sid, self._story_xml(sid, "", "NormalParagraphStyle")

        # If nothing was added, emit one empty story
        if idx == 0 and story_ids:
            sid = story_ids[0]
            yield sid, self._story_xml(sid, "", "NormalParagraphStyle")

    def _story_xml(self, story_id: str, text: str, style: str) -> str:
        # Escape XML special characters in content
        safe_text = (
            text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
        )
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
            f'<idPkg:Story xmlns:idPkg="{_IDPKG}" DOMVersion="19.0">\n'
            f'  <Story Self="{story_id}">\n'
            f'    <ParagraphStyleRange AppliedParagraphStyle='
            f'"ParagraphStyle/{style}">\n'
            f'      <CharacterStyleRange AppliedCharacterStyle='
            f'"CharacterStyle/$ID/[No character style]">\n'
            f'        <Content>{safe_text}</Content>\n'
            f'      </CharacterStyleRange>\n'
            f'    </ParagraphStyleRange>\n'
            f'  </Story>\n'
            f'</idPkg:Story>\n'
        )

    @staticmethod
    def _table_to_text(table: Dict[str, Any]) -> str:
        """Convert table headers + rows to tab-separated text."""
        lines = ["\t".join(str(h) for h in table["headers"])]
        for row in table["rows"]:
            lines.append("\t".join(str(c) for c in row))
        return "\n".join(lines)

    def _apply_replacements(self, text: str) -> str:
        for placeholder, content in self._replacements.items():
            text = text.replace(placeholder, content)
        return text


# ============================================================================
# Convenience function: export_report_idml
# ============================================================================

def export_report_idml(
    ga_data: Dict[str, Any],
    output_path: str,
    template_path: Optional[str] = None,
    title: str = "Google Analytics Report",
) -> str:
    """Export a GA-data report as an IDML file.

    Accepts the same ``ga_data`` dict produced by
    ``generate_sample_ga_data()`` / ``fetch_real_ga4_data()`` and writes
    an IDML file that Adobe InDesign can open.

    Parameters
    ----------
    ga_data : dict
        Google Analytics data dictionary (totals, traffic_sources,
        top_pages, devices, etc.).
    output_path : str
        Destination file path for the ``.idml`` output.
    template_path : str, optional
        Path to an IDML template with placeholders.
    title : str
        Report title.

    Returns
    -------
    str
        The resolved output file path.
    """
    exporter = IDMLExporter(template_path=template_path)

    # -- Title --
    date_range = ga_data.get("date_range", {})
    subtitle = ""
    if date_range:
        subtitle = f"{date_range.get('start', '')} to {date_range.get('end', '')}"
    exporter.add_text_frame(
        title, style_name="Title", x=72, y=72, width=468, height=36,
    )
    if subtitle:
        exporter.add_text_frame(
            subtitle, style_name="Subtitle", x=72, y=114, width=468, height=24,
        )

    # -- KPI summary --
    totals = ga_data.get("totals", {})
    changes = ga_data.get("changes", {})
    if totals:
        kpi_text = (
            f"Users: {totals.get('users', 'N/A'):,}  "
            f"Sessions: {totals.get('sessions', 'N/A'):,}  "
            f"Pageviews: {totals.get('pageviews', 'N/A'):,}  "
            f"Bounce Rate: {totals.get('avg_bounce_rate', 0):.1f}%"
        )
        exporter.add_text_frame(
            kpi_text, style_name="KPI", x=72, y=160, width=468, height=24,
        )

    # -- Traffic Sources table --
    sources = ga_data.get("traffic_sources", [])
    if sources:
        headers = ["Source", "Medium", "Sessions", "Users", "Bounce Rate"]
        rows = [
            [
                s.get("source", ""),
                s.get("medium", ""),
                str(s.get("sessions", "")),
                str(s.get("users", "")),
                f"{s.get('bounce_rate', 0):.1f}%",
            ]
            for s in sources
        ]
        exporter.add_table(
            headers, rows, x=72, y=210, width=468, height=120,
        )

    # -- Top Pages table --
    pages = ga_data.get("top_pages", [])
    if pages:
        headers = ["Page", "Pageviews", "Unique Views", "Avg Time", "Bounce Rate"]
        rows = [
            [
                p.get("page", ""),
                str(p.get("pageviews", "")),
                str(p.get("unique_views", "")),
                f"{p.get('avg_time', 0):.1f}s",
                f"{p.get('bounce_rate', 0):.1f}%",
            ]
            for p in pages
        ]
        exporter.add_table(
            headers, rows, x=72, y=360, width=468, height=120,
        )

    # -- Device breakdown table --
    devices = ga_data.get("devices", [])
    if devices:
        headers = ["Device", "Sessions", "Bounce Rate"]
        rows = [
            [
                d.get("device", ""),
                str(d.get("sessions", "")),
                f"{d.get('bounce_rate', 0):.1f}%",
            ]
            for d in devices
        ]
        exporter.add_table(
            headers, rows, x=72, y=510, width=468, height=80,
        )

    # -- Apply any template placeholders --
    exporter.replace_placeholder("{{TITLE}}", title)
    exporter.replace_placeholder("{{DATE_RANGE}}", subtitle)
    if totals:
        exporter.replace_placeholder("{{TOTAL_USERS}}", f"{totals.get('users', 'N/A'):,}")
        exporter.replace_placeholder("{{TOTAL_SESSIONS}}", f"{totals.get('sessions', 'N/A'):,}")

    return exporter.save(output_path)

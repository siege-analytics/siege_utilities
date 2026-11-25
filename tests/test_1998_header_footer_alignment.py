"""Regression tests for issue #1998.

``BaseReportTemplate._header_footer_on_page`` positioned right-aligned
header/footer text and the page number with ``Paragraph.wrapOn(...)[0]``.
``wrapOn`` returns the *available* width it was given, not the width of the
text, so right-aligned text was drawn at the left margin (on top of the left
text) and the page number was drawn at ``-rightMargin`` (off the page).

These tests render a real PDF and read back where each string was drawn.
"""

import pytest

pytest.importorskip("reportlab")
PyPDF2 = pytest.importorskip("PyPDF2")
yaml = pytest.importorskip("yaml")

from reportlab.lib.pagesizes import letter
from reportlab.pdfbase import pdfmetrics
from reportlab.platypus import Paragraph

from siege_utilities.reporting.templates.base_template import BaseReportTemplate

HEADER_LEFT = "Acme Field Services"
HEADER_RIGHT = "bonneau-market-2-carneros-deli"
FOOTER_LEFT = "Internal use only"
FOOTER_RIGHT = "Generated daily"
TOLERANCE = 2.0  # points


def _render(tmp_path, branding_overrides=None):
    branding = {
        "colors": {"text_color": "#000000"},
        "fonts": {},
        "header": {"left_text": HEADER_LEFT, "right_text": HEADER_RIGHT},
        "footer": {
            "left_text": FOOTER_LEFT,
            "right_text": FOOTER_RIGHT,
            "page_number_format": "Page %s",
        },
    }
    branding.update(branding_overrides or {})
    config = tmp_path / "branding.yaml"
    config.write_text(yaml.safe_dump(branding), encoding="utf-8")
    out = tmp_path / "out.pdf"
    template = BaseReportTemplate(str(out), branding_config_path=config)
    template.build_document([Paragraph("Body text.", template.styles["Normal"])])
    return template, out


def _drawn_strings(pdf_path):
    """Return {text: (x, y)} for every text run on page 1."""
    runs = {}

    def visitor(text, cm, tm, font_dict, font_size):
        text = text.strip()
        if text:
            # Paragraph.drawOn translates the CTM, then sets a text origin.
            x = cm[0] * tm[4] + cm[2] * tm[5] + cm[4]
            y = cm[1] * tm[4] + cm[3] * tm[5] + cm[5]
            runs.setdefault(text, (x, y))

    reader = PyPDF2.PdfReader(str(pdf_path))
    reader.pages[0].extract_text(visitor_text=visitor)
    return runs


def _width(template, text):
    style = template.styles["HeaderFooter"]
    return pdfmetrics.stringWidth(text, style.fontName, style.fontSize)


def test_right_header_text_is_flush_with_right_margin(tmp_path):
    template, out = _render(tmp_path)
    runs = _drawn_strings(out)
    page_width = letter[0]
    right_edge = page_width - template.doc.rightMargin

    x, _ = runs[HEADER_RIGHT]
    assert x + _width(template, HEADER_RIGHT) == pytest.approx(right_edge, abs=TOLERANCE)


def test_right_header_text_does_not_collide_with_left_text(tmp_path):
    template, out = _render(tmp_path)
    runs = _drawn_strings(out)
    left_x, _ = runs[HEADER_LEFT]
    right_x, _ = runs[HEADER_RIGHT]
    assert right_x > left_x + _width(template, HEADER_LEFT)


def test_right_footer_text_is_flush_with_right_margin(tmp_path):
    template, out = _render(tmp_path)
    runs = _drawn_strings(out)
    right_edge = letter[0] - template.doc.rightMargin

    x, _ = runs[FOOTER_RIGHT]
    assert x + _width(template, FOOTER_RIGHT) == pytest.approx(right_edge, abs=TOLERANCE)
    left_x, _ = runs[FOOTER_LEFT]
    assert x > left_x + _width(template, FOOTER_LEFT)


def test_page_number_is_on_page_at_right_margin(tmp_path):
    template, out = _render(tmp_path)
    runs = _drawn_strings(out)
    page_width = letter[0]

    x, y = runs["Page 1"]
    assert 0 <= x <= page_width
    assert 0 <= y <= letter[1]
    assert x + _width(template, "Page 1") == pytest.approx(
        page_width - template.doc.rightMargin, abs=TOLERANCE)


def test_overlong_right_text_wraps_inside_the_right_half(tmp_path):
    """Text wider than the right half wraps; every line stays on the page and
    clear of the page centre, flush against the right margin."""
    long_text = " ".join(["segment"] * 30)
    template, out = _render(tmp_path, {"header": {"right_text": long_text}})
    page_width = letter[0]
    right_edge = page_width - template.doc.rightMargin

    lines = []

    def visitor(text, cm, tm, font_dict, font_size):
        text = text.strip()
        if text.startswith("segment"):
            lines.append((cm[0] * tm[4] + cm[2] * tm[5] + cm[4], text))

    reader = PyPDF2.PdfReader(str(out))
    reader.pages[0].extract_text(visitor_text=visitor)

    assert len(lines) > 1  # it wrapped
    for x, text in lines:
        assert x >= page_width / 2 - TOLERANCE
        assert x + _width(template, text) == pytest.approx(right_edge, abs=TOLERANCE)


# --- vertical bands: header in the top margin, footer above the page number --

LONG_FOOTER = ("Confidential - prepared for Acme Field Services by Siege Analytics, "
               "November 2026. Do not distribute outside the client organisation "
               "without written consent. Figures are provisional and subject to "
               "revision after audit.")


def _render_recording(tmp_path, monkeypatch, header=None, footer=None):
    """Render and record (text, y_bottom, height) of every right-aligned block."""
    drawn = []
    original = BaseReportTemplate._draw_right_aligned.__func__

    def recording(cls, canvas, text, *args, **kwargs):
        y, height = original(cls, canvas, text, *args, **kwargs)
        drawn.append((text, y, height))
        return y, height

    monkeypatch.setattr(BaseReportTemplate, "_draw_right_aligned", classmethod(recording))
    template, out = _render(tmp_path, {"header": header or {}, "footer": footer or {}})
    return template, out, drawn


def _page_text(pdf_path):
    return PyPDF2.PdfReader(str(pdf_path)).pages[0].extract_text()


def _block(drawn, prefix):
    (block,) = [d for d in drawn if d[0].startswith(prefix)]
    return block


@pytest.mark.parametrize("chars", [40, 100, 157, len(LONG_FOOTER)])
def test_footer_right_text_never_overlaps_the_page_number(tmp_path, monkeypatch, chars):
    text = LONG_FOOTER[:chars].rstrip()
    template, out, drawn = _render_recording(
        tmp_path, monkeypatch,
        footer={"left_text": FOOTER_LEFT, "right_text": text, "page_number_format": "Page %s"})
    _, pn_y, pn_h = _block(drawn, "Page 1")
    _, f_y, f_h = _block(drawn, text[:20])
    gap = BaseReportTemplate._HEADER_FOOTER_GAP

    assert pn_y >= 0, "page number below the page edge"
    assert f_y >= pn_y + pn_h + gap - 0.01, "footer text box overlaps the page number"
    assert f_y + f_h <= template.doc.bottomMargin - gap + 0.01, "footer runs into the body frame"

    # Read back from the PDF: the page number's baseline is at least one
    # line below the footer's lowest baseline (both read the same way, so
    # any reader offset cancels).
    runs = _drawn_strings(out)
    words = set(text.split())
    footer_ys = [y for t, (x, y) in runs.items()
                 if y < template.doc.bottomMargin and t.split()[0] in words]
    assert min(footer_ys) - runs["Page 1"][1] >= template.styles["HeaderFooter"].fontSize


def test_overlong_footer_right_text_is_truncated_with_an_ellipsis(tmp_path, monkeypatch):
    text = " ".join([LONG_FOOTER] * 3)
    template, out, drawn = _render_recording(
        tmp_path, monkeypatch,
        footer={"right_text": text, "page_number_format": "Page %s"})
    _, pn_y, pn_h = _block(drawn, "Page 1")
    _, f_y, f_h = _block(drawn, text[:20])
    assert f_y >= pn_y + pn_h
    assert f_y + f_h <= template.doc.bottomMargin
    page = _page_text(out)
    assert "Confidential" in page and "…" in page
    assert "revision after audit. Confidential - prepared" not in page.replace("\n", " ")


def test_very_long_right_header_stays_in_the_top_margin(tmp_path, monkeypatch):
    text = " ".join(["segment"] * 120)  # about 960 characters
    template, out, drawn = _render_recording(tmp_path, monkeypatch, header={"right_text": text})
    _, y, h = _block(drawn, "segment")
    page_height = letter[1]
    assert y >= page_height - template.doc.topMargin, "header runs into the body frame"
    assert y + h <= page_height, "header runs off the top of the page"
    page = _page_text(out)
    assert "…" in page
    assert page.count("segment") < 120


def test_short_right_texts_keep_their_centred_positions(tmp_path, monkeypatch):
    """One-line right header/footer text stays centred where it always was."""
    template, _, drawn = _render_recording(
        tmp_path, monkeypatch,
        header={"right_text": HEADER_RIGHT},
        footer={"right_text": FOOTER_RIGHT, "page_number_format": "Page %s"})
    page_height = letter[1]
    _, hy, hh = _block(drawn, HEADER_RIGHT)
    _, fy, fh = _block(drawn, FOOTER_RIGHT)
    _, py, ph = _block(drawn, "Page 1")
    assert hy + hh / 2 == pytest.approx(page_height - template.doc.topMargin / 2)
    assert fy + fh / 2 == pytest.approx(template.doc.bottomMargin / 2)
    assert py + ph / 2 == pytest.approx(template.doc.bottomMargin / 2 - 0.2 * 72)
